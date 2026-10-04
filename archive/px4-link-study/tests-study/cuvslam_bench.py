#!/usr/bin/env python3
"""
cuVSLAM (NVIDIA, pycuvslam 17) on the same SVO as the ZED SDK runs (the VO/perception study, docs/study-vo-perception.md).

Reads the rectified left/right frames from the SVO with pyzed, feeds them to cuvslam.Tracker as a stereo rig (no IMU: the
simulated ZED stream has none) and writes pose.csv / summary.json in the same format as svo_bench.py, so analyze.py scores
both the same way. Poses are converted from cuVSLAM's optical frame (x right, y down, z forward) to FLU (x forward, y left, z up).

    PYTHONPATH=logs/study/pylib python3 cuvslam_bench.py --svo flight.svo2 --out res/cu_stereo --mode Precision [--scale 0.5] [--slam]
"""
import argparse
import json
import os
import resource
import subprocess
import threading
import time

import numpy as np
import pyzed.sl as sl
import cuvslam

C_FLU_FROM_CV = np.array([[0, 0, 1], [-1, 0, 0], [0, -1, 0]], float)


def quat_to_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat_to_quat(R):
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        return np.array([(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, 0.25 * s])
    i = int(np.argmax(np.diag(R)))
    j, k = (i + 1) % 3, (i + 2) % 3
    s = np.sqrt(1.0 + R[i, i] - R[j, j] - R[k, k]) * 2
    q = np.zeros(4)
    q[i] = 0.25 * s
    q[3] = (R[k, j] - R[j, k]) / s
    q[j] = (R[j, i] + R[i, j]) / s
    q[k] = (R[k, i] + R[i, k]) / s
    return q


def gpu_sample(stop, out, period=0.1):
    while not stop.is_set():
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,power.draw,clocks.sm",
                                "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=2)
            u, m, p, c = [float(x) for x in r.stdout.strip().split(",")]
            out.append((time.time(), u, m, p, c))
        except Exception:  # noqa: BLE001
            pass
        stop.wait(period)


def pool(img, k):
    if k == 1:
        return img
    h, w = img.shape[0] // k * k, img.shape[1] // k * k
    return img[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3)).astype(np.uint8)


def degrade(img, a, rng):
    """Synthetic image degradation (the simulated frames are clean): gain, box blur, gaussian noise."""
    if a.gain == 1.0 and a.blur <= 1 and a.noise <= 0:
        return img
    x = img.astype(np.float32)
    if a.blur > 1:
        k = a.blur
        for ax in (0, 1):
            c = np.cumsum(np.pad(x, [(k // 2 + 1, k // 2) if i == ax else (0, 0) for i in range(2)], mode="edge"), axis=ax)
            x = (np.take(c, np.arange(k, c.shape[ax]), axis=ax) - np.take(c, np.arange(0, c.shape[ax] - k), axis=ax)) / k
    x = x * a.gain
    if a.noise > 0:
        x = x + rng.normal(0.0, a.noise, x.shape).astype(np.float32)
    return np.clip(x, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", default="Precision", choices=["Performance", "Moderate", "Precision"])
    ap.add_argument("--scale", type=int, default=1, help="integer down-scale factor (2 = 640x360)")
    ap.add_argument("--slam", action="store_true", help="enable SLAM (loop closure) next to odometry")
    ap.add_argument("--denoise", action="store_true")
    ap.add_argument("--no-gpu", action="store_true", help="odometry on the CPU")
    ap.add_argument("--fps-cap", type=float, default=0.0)
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--noise", type=float, default=0.0, help="gaussian pixel noise sigma (8-bit levels) added to both images")
    ap.add_argument("--blur", type=int, default=0, help="box blur width in pixels (motion-blur / defocus stand-in)")
    ap.add_argument("--gain", type=float, default=1.0, help="brightness gain (0.5 = half the light)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    zed = sl.Camera()
    init = sl.InitParameters()
    init.set_from_svo_file(a.svo)
    init.svo_real_time_mode = False
    init.depth_mode = sl.DEPTH_MODE.NONE
    init.coordinate_units = sl.UNIT.METER
    if zed.open(init) != sl.ERROR_CODE.SUCCESS:
        print("open failed")
        return 2
    cal = zed.get_camera_information().camera_configuration.calibration_parameters
    lc = cal.left_cam
    baseline = float(cal.get_camera_baseline())
    k = a.scale
    W, H = int(lc.image_size.width) // k, int(lc.image_size.height) // k
    rig = cuvslam.Rig()
    cams = []
    for i in range(2):
        c = cuvslam.Camera()
        c.size = (W, H)
        c.focal = (lc.fx / k, lc.fy / k)
        c.principal = (lc.cx / k, lc.cy / k)
        c.distortion = cuvslam.Distortion(cuvslam.Distortion.Model.Pinhole)
        c.rig_from_camera = cuvslam.Pose(rotation=[0, 0, 0, 1], translation=[baseline * i, 0, 0])
        cams.append(c)
    rig.cameras = cams
    cfg = cuvslam.Tracker.OdometryConfig(odometry_mode=cuvslam.Tracker.OdometryMode.Multicamera,
                                         multicam_mode=getattr(cuvslam.Tracker.MulticameraMode, a.mode),
                                         rectified_stereo_camera=True, use_gpu=not a.no_gpu, use_denoising=a.denoise,
                                         enable_observations_export=a.slam, enable_landmarks_export=a.slam,
                                         async_sba=True)
    slam_cfg = cuvslam.Tracker.SlamConfig(use_gpu=not a.no_gpu, sync_mode=True) if a.slam else None
    cuvslam.warm_up_gpu()
    mem0 = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout
    t_open = time.time()
    tracker = cuvslam.Tracker(rig, cfg, slam_cfg)
    t_open = time.time() - t_open

    left, right = sl.Mat(), sl.Mat()
    rows, ms, lost = [], [], 0
    gpu, stop = [], threading.Event()
    th = threading.Thread(target=gpu_sample, args=(stop, gpu), daemon=True)
    th.start()
    cpu0, wall0, last_ts, n = time.process_time(), time.time(), -1e18, 0
    rt = sl.RuntimeParameters()
    rt.enable_depth = False
    rng = np.random.default_rng(1)
    while True:
        st = zed.grab(rt)
        if st == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:
            break
        if st != sl.ERROR_CODE.SUCCESS:
            continue
        ts = zed.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_nanoseconds()
        if a.fps_cap and ts - last_ts < 1e9 / a.fps_cap - 5e6:
            continue
        last_ts = ts
        zed.retrieve_image(left, sl.VIEW.LEFT_GRAY)
        zed.retrieve_image(right, sl.VIEW.RIGHT_GRAY)
        li = np.ascontiguousarray(pool(left.get_data()[:, :, 0] if left.get_data().ndim == 3 else left.get_data(), k))
        ri = np.ascontiguousarray(pool(right.get_data()[:, :, 0] if right.get_data().ndim == 3 else right.get_data(), k))
        li, ri = degrade(li, a, rng), degrade(ri, a, rng)
        t0 = time.perf_counter()
        est, slam_pose = tracker.track(ts, [li, ri])
        dt = (time.perf_counter() - t0) * 1000.0
        ms.append(dt)
        w = est.world_from_rig
        pose = w.pose if w is not None else None
        if slam_pose is not None:
            pose = slam_pose
        if pose is None:
            lost += 1
        else:
            p = np.asarray(pose.translation, float)
            R = quat_to_mat(np.asarray(pose.rotation, float))
            pf = C_FLU_FROM_CV @ p
            qf = mat_to_quat(C_FLU_FROM_CV @ R @ C_FLU_FROM_CV.T)
            rows.append((ts, pf[0], pf[1], pf[2], qf[0], qf[1], qf[2], qf[3], "OK", dt))
        n += 1
        if a.max_frames and n >= a.max_frames:
            break
    wall = time.time() - wall0
    cpu = time.process_time() - cpu0
    stop.set()
    th.join(timeout=2)
    zed.close()
    with open(os.path.join(a.out, "pose.csv"), "w") as f:
        f.write("stamp_ns,x,y,z,qx,qy,qz,qw,state,grab_ms\n")
        for r in rows:
            f.write(",".join(str(v) for v in r) + "\n")
    g = np.array(gpu) if gpu else np.zeros((1, 5))
    gm = np.array(ms)
    ru = resource.getrusage(resource.RUSAGE_SELF)
    summary = {
        "config": {"tracking": "CUVSLAM", "depth": "NONE", "mode": a.mode, "scale": k, "slam": a.slam, "denoise": a.denoise,
                   "gpu": not a.no_gpu, "fps_cap": a.fps_cap, "noise": a.noise, "blur": a.blur, "gain": a.gain, "version": cuvslam.get_version()},
        "frames_processed": n, "lost_frames": lost, "wall_s": wall, "fps_max": n / wall,
        "grab_ms_mean": float(gm.mean()), "grab_ms_p50": float(np.percentile(gm, 50)), "grab_ms_p95": float(np.percentile(gm, 95)),
        "grab_ms_max": float(gm.max()), "open_s": t_open, "cpu_s": cpu, "cpu_cores_avg": cpu / wall, "cpu_ms_per_frame": 1000 * cpu / max(n, 1),
        "gpu_util_mean": float(g[:, 1].mean()), "gpu_util_p95": float(np.percentile(g[:, 1], 95)),
        "gpu_mem_used_mib_max": float(g[:, 2].max()), "gpu_mem_baseline_mib": float(mem0.strip() or 0),
        "gpu_power_w_mean": float(g[:, 3].mean()), "gpu_sm_clock_mhz_mean": float(g[:, 4].mean()), "max_rss_mib": ru.ru_maxrss / 1024.0,
        "tracking_ok_frames": len(rows), "states": ["OK"], "svo_frames": n,
    }
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
