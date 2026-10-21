#!/usr/bin/env python3
"""
Offline ZED SDK benchmark on a recorded SVO (the VO/perception study, docs/study-vo-perception.md).

Replays the SVO as fast as the SDK can process it (svo_real_time_mode = False) with one configuration and records, per frame,
the pose, the tracking state and the time grab() took, plus whole-run CPU / GPU / VRAM figures. Identical input for every
configuration, so differences are the settings, not the flight.

    python3 svo_bench.py --svo flight.svo2 --out res/g3_nl --tracking GEN_3 --depth NEURAL_LIGHT [--no-depth-compute]

Writes <out>/pose.csv (stamp_ns x y z qx qy qz qw state grab_ms), <out>/depth_s8.npz (every --depth-every frame, 1/8
sub-sampled depth, for the range-accuracy analysis), <out>/summary.json. Runs inside the ZED container (pyzed 5.4.1).
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--svo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tracking", default="GEN_3", choices=["GEN_1", "GEN_2", "GEN_3", "NONE"])
    ap.add_argument("--depth", default="NEURAL_LIGHT")
    ap.add_argument("--no-depth-compute", action="store_true", help="depth mode stays set (GEN_1 needs it) but grab() skips depth")
    ap.add_argument("--max-depth", type=float, default=15.0)
    ap.add_argument("--max-frames", type=int, default=0)
    ap.add_argument("--depth-every", type=int, default=30)
    ap.add_argument("--fps-cap", type=float, default=0.0, help="emulate a lower camera frame rate by seeking over SVO frames (30/fps-cap)")
    ap.add_argument("--imu-fusion", action="store_true")
    ap.add_argument("--area-memory", action="store_true", help="loop closure / relocalisation on revisits")
    ap.add_argument("--pose-smoothing", action="store_true")
    ap.add_argument("--depth-stab", type=int, default=-1, help="InitParameters.depth_stabilization 0-100 (-1 = SDK default)")
    ap.add_argument("--fill-mode", action="store_true", help="RuntimeParameters.enable_fill_mode")
    ap.add_argument("--no-image-enhancement", action="store_true")
    ap.add_argument("--confidence", type=int, default=-1, help="RuntimeParameters.confidence_threshold (-1 = default)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    zed = sl.Camera()
    init = sl.InitParameters()
    init.set_from_svo_file(a.svo)
    init.svo_real_time_mode = False
    init.depth_mode = getattr(sl.DEPTH_MODE, a.depth)
    init.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Z_UP_X_FWD
    init.coordinate_units = sl.UNIT.METER
    init.depth_maximum_distance = a.max_depth
    if a.depth_stab >= 0:
        init.depth_stabilization = a.depth_stab
    if a.no_image_enhancement:
        init.enable_image_enhancement = False
    mem0 = subprocess.run(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True).stdout
    t_open = time.time()
    err = zed.open(init)
    if err != sl.ERROR_CODE.SUCCESS:
        print("open failed:", err)
        return 2
    t_open = time.time() - t_open
    n_total = zed.get_svo_number_of_frames()
    if a.tracking != "NONE":
        tp = sl.PositionalTrackingParameters()
        tp.mode = getattr(sl.POSITIONAL_TRACKING_MODE, a.tracking)
        tp.enable_imu_fusion = a.imu_fusion
        tp.enable_area_memory = a.area_memory
        tp.enable_pose_smoothing = a.pose_smoothing
        e = zed.enable_positional_tracking(tp)
        if e != sl.ERROR_CODE.SUCCESS:
            print("enable_positional_tracking failed:", e)
            return 3
    rt = sl.RuntimeParameters()
    rt.enable_depth = (a.depth != "NONE") and not a.no_depth_compute
    rt.enable_fill_mode = a.fill_mode
    if a.confidence >= 0:
        rt.confidence_threshold = a.confidence
    pose, depth = sl.Pose(), sl.Mat()
    rows, depths, dstamps, grab_ms = [], [], [], []
    gpu, stop = [], threading.Event()
    th = threading.Thread(target=gpu_sample, args=(stop, gpu), daemon=True)
    th.start()
    step = max(1, int(round(30.0 / a.fps_cap))) if a.fps_cap else 1
    cpu0, wall0, n = time.process_time(), time.time(), 0
    while True:
        t0 = time.perf_counter()
        st = zed.grab(rt)
        dt = (time.perf_counter() - t0) * 1000.0
        if st == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:
            break
        if st != sl.ERROR_CODE.SUCCESS:
            continue
        ts = zed.get_timestamp(sl.TIME_REFERENCE.IMAGE).get_nanoseconds()
        state = zed.get_position(pose, sl.REFERENCE_FRAME.WORLD) if a.tracking != "NONE" else None
        tr = pose.get_translation(sl.Translation()).get()
        q = pose.get_orientation(sl.Orientation()).get()
        rows.append((ts, tr[0], tr[1], tr[2], q[0], q[1], q[2], q[3], str(state).split(".")[-1] if state is not None else "NA", dt))
        grab_ms.append(dt)
        if rt.enable_depth and n % a.depth_every == 0:
            zed.retrieve_measure(depth, sl.MEASURE.DEPTH)
            d = depth.get_data()[::8, ::8].astype(np.float32)
            depths.append(d)
            dstamps.append(ts)
        n += 1
        if a.max_frames and n >= a.max_frames:
            break
        if step > 1:     # the SDK must not see the skipped frames, or tracking is unaffected by the "lower frame rate"
            zed.set_svo_position(zed.get_svo_position() + step)
    wall = time.time() - wall0
    cpu = time.process_time() - cpu0
    stop.set()
    th.join(timeout=2)
    zed.disable_positional_tracking() if a.tracking != "NONE" else None
    zed.close()

    with open(os.path.join(a.out, "pose.csv"), "w") as f:
        f.write("stamp_ns,x,y,z,qx,qy,qz,qw,state,grab_ms\n")
        for r in rows:
            f.write(",".join(str(v) for v in r) + "\n")
    if depths:
        np.savez_compressed(os.path.join(a.out, "depth_s8.npz"), depth=np.stack(depths), stamp=np.array(dstamps))
    g = np.array(gpu) if gpu else np.zeros((1, 5))
    gm = np.array(grab_ms)
    ru = resource.getrusage(resource.RUSAGE_SELF)
    summary = {
        "config": {"tracking": a.tracking, "depth": a.depth, "depth_computed": rt.enable_depth, "imu_fusion": a.imu_fusion,
                   "max_depth": a.max_depth, "fps_cap": a.fps_cap, "area_memory": a.area_memory, "pose_smoothing": a.pose_smoothing,
                   "depth_stab": a.depth_stab, "fill_mode": a.fill_mode, "confidence": a.confidence,
                   "image_enhancement": not a.no_image_enhancement},
        "svo_frames": int(n_total), "frames_processed": n, "wall_s": wall, "fps_max": n / wall,
        "grab_ms_mean": float(gm.mean()), "grab_ms_p50": float(np.percentile(gm, 50)), "grab_ms_p95": float(np.percentile(gm, 95)),
        "grab_ms_max": float(gm.max()), "open_s": t_open,
        "cpu_s": cpu, "cpu_cores_avg": cpu / wall, "cpu_ms_per_frame": 1000 * cpu / max(n, 1),
        "gpu_util_mean": float(g[:, 1].mean()), "gpu_util_p95": float(np.percentile(g[:, 1], 95)),
        "gpu_mem_used_mib_max": float(g[:, 2].max()), "gpu_mem_baseline_mib": float(mem0.strip() or 0),
        "gpu_power_w_mean": float(g[:, 3].mean()), "gpu_sm_clock_mhz_mean": float(g[:, 4].mean()),
        "max_rss_mib": ru.ru_maxrss / 1024.0,
        "tracking_ok_frames": int(sum(1 for r in rows if r[8] in ("OK",))), "states": sorted({r[8] for r in rows}),
    }
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
