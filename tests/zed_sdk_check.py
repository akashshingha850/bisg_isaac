#!/usr/bin/env python3
"""
ZED SDK contract + health check — the same script for the sim (ZED_SOURCE=sdk) and the real Jetson.

Run inside the ZED container (it has rclpy and zed_msgs):
    ./bisg zed check                         # sim: also compares the SDK's odometry with Pegasus ground truth
    ./bisg zed check --seconds 30
    python3 tests/zed_sdk_check.py --drone 1 --no-gt      # on the Jetson: no ground truth exists

What it asserts over a sampling window (default 15 s), all under /drone_<n>/zed/zed_node/:
  streams   left/right colour image, depth_registered, point cloud, odom, imu/data are flowing at a usable rate
  geometry  camera_info is HD720 for a ZED Mini, the stereo baseline (right P[0,3] / fx) is 63 mm
  depth     32FC1 metres, mostly finite, inside the configured range
  health    the SDK's image-quality / depth-reliability / motion-sensor flags are clear
  tracking  PosTrackStatus is OK / INITIALIZING-free, odometry is finite and moves
  truth     (sim only) while the drone moves: path length and trajectory RMSE of the SDK odometry vs Pegasus state/pose

Exit code 0 = every check passed. The ground-truth comparison is skipped (not failed) while the drone sits still.
"""
import argparse
import math
import sys
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CameraInfo, Image, Imu, PointCloud2
from zed_msgs.msg import HealthStatusStamped, PosTrackStatus

BEST_EFFORT = QoSProfile(depth=5, reliability=ReliabilityPolicy.BEST_EFFORT)
ZED_MINI_HD720 = (1280, 720)
BASELINE_M = 0.063


class Probe(Node):
    def __init__(self, drone, gt):
        super().__init__("zed_sdk_check")
        r = f"/drone_{drone}/zed/zed_node/"
        self.t = {k: [] for k in ("left", "right", "depth", "cloud", "odom", "imu")}
        self.info = {}
        self.depth = None
        self.health = None
        self.track = None
        self.odom = []          # (t, x, y, z)
        self.gt = []            # (t, x, y, z)
        self.frames = None
        self.clock = []         # (wall, sim) from /clock — sim only
        mk = self.create_subscription
        mk(Image, r + "left/color/rect/image", lambda m: self.t["left"].append(time.time()), BEST_EFFORT)
        mk(Image, r + "right/color/rect/image", lambda m: self.t["right"].append(time.time()), BEST_EFFORT)
        mk(Image, r + "depth/depth_registered", self._on_depth, BEST_EFFORT)
        mk(PointCloud2, r + "point_cloud/cloud_registered", lambda m: self.t["cloud"].append(time.time()), BEST_EFFORT)
        mk(Odometry, r + "odom", self._on_odom, BEST_EFFORT)
        mk(Imu, r + "imu/data", lambda m: self.t["imu"].append(time.time()), BEST_EFFORT)
        mk(CameraInfo, r + "left/color/rect/camera_info", lambda m: self.info.__setitem__("left", m), BEST_EFFORT)
        mk(CameraInfo, r + "right/color/rect/camera_info", lambda m: self.info.__setitem__("right", m), BEST_EFFORT)
        mk(HealthStatusStamped, r + "status/health", lambda m: setattr(self, "health", m), BEST_EFFORT)
        mk(PosTrackStatus, r + "pose/status", lambda m: setattr(self, "track", m), BEST_EFFORT)
        mk(Clock, "/clock", lambda m: self.clock.append((time.time(), m.clock.sec + m.clock.nanosec * 1e-9)), BEST_EFFORT)
        if gt:
            mk(PoseStamped, f"/drone_{drone}/state/pose", self._on_gt, BEST_EFFORT)

    def _on_depth(self, m):
        self.t["depth"].append(time.time())
        if self.depth is None and m.encoding == "32FC1":
            self.depth = np.frombuffer(m.data, np.float32).reshape(m.height, m.width).copy()
        self.depth_encoding = m.encoding

    def _on_odom(self, m):
        now = time.time()
        self.t["odom"].append(now)
        p = m.pose.pose.position
        self.odom.append((now, p.x, p.y, p.z))
        self.frames = (m.header.frame_id, m.child_frame_id)

    def _on_gt(self, m):
        p = m.pose.position
        self.gt.append((time.time(), p.x, p.y, p.z))


def rate(ts, seconds):
    return len(ts) / seconds if seconds > 0 else 0.0


def path_length(samples):
    a = np.array([s[1:] for s in samples])
    return float(np.linalg.norm(np.diff(a, axis=0), axis=1).sum()) if len(a) > 1 else 0.0


def trajectory_rmse(odom, gt):
    """RMSE (m) of the SDK odometry against ground truth after the only alignment that is legitimate here: a yaw
    rotation and a translation (both frames are gravity-aligned, z up, and the odom origin is wherever the SDK
    started). Samples are paired by receive time: gt is interpolated onto the odom stamps. Returns (rmse_xyz,
    yaw_deg, final_error)."""
    to = np.array([o[0] for o in odom])
    tg = np.array([g[0] for g in gt])
    o = np.array([x[1:] for x in odom])
    g = np.array([x[1:] for x in gt])
    keep = (to >= tg[0]) & (to <= tg[-1])
    o, to = o[keep], to[keep]
    gi = np.stack([np.interp(to, tg, g[:, k]) for k in range(3)], axis=1)
    oc, gc = o - o.mean(axis=0), gi - gi.mean(axis=0)
    # 2-D Procrustes for the yaw: angle that rotates odom xy onto gt xy
    yaw = math.atan2((oc[:, 0] * gc[:, 1] - oc[:, 1] * gc[:, 0]).sum(), (oc[:, 0] * gc[:, 0] + oc[:, 1] * gc[:, 1]).sum())
    c, s_ = math.cos(yaw), math.sin(yaw)
    rot = np.array([[c, -s_, 0.0], [s_, c, 0.0], [0.0, 0.0, 1.0]])
    aligned = oc @ rot.T + gi.mean(axis=0)
    err = np.linalg.norm(aligned - gi, axis=1)
    return float(np.sqrt((err ** 2).mean())), math.degrees(yaw), float(err[-1])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--seconds", type=float, default=15.0)
    ap.add_argument("--no-gt", action="store_true", help="no ground truth available (real drone)")
    ap.add_argument("--min-image-hz", type=float, default=8.0)
    ap.add_argument("--min-depth-hz", type=float, default=4.0)
    ap.add_argument("--depth-range", type=float, nargs=2, default=(0.2, 20.0))
    ap.add_argument("--max-rmse", type=float, default=0.5, help="allowed trajectory RMSE after yaw+offset alignment, m (sim)")
    ap.add_argument("--scale-tol", type=float, default=0.25, help="allowed |odom path / truth path - 1| (sim)")
    args = ap.parse_args()

    rclpy.init()
    node = Probe(args.drone, gt=not args.no_gt)
    # The wrapper publishes clouds only while subscribed and the first frames take a moment: let it warm up.
    t_end = time.time() + 5.0
    while time.time() < t_end:
        rclpy.spin_once(node, timeout_sec=0.1)
    for v in node.t.values():
        v.clear()
    node.odom.clear()
    node.gt.clear()
    t0 = time.time()
    while time.time() - t0 < args.seconds:
        rclpy.spin_once(node, timeout_sec=0.05)
    dt = time.time() - t0

    results = []

    def check(name, ok, detail):
        results.append((name, ok, detail))

    # The sim runs slower than real time (Pegasus per-step Python, rtf ~0.3-0.5 on Isaac 6.0), and the streamed camera
    # ticks in SIM time: judge rates per simulated second. On the real drone there is no /clock, so rtf = 1.
    rtf = 1.0
    if len(node.clock) > 10:
        (w0, s0), (w1, s1) = node.clock[0], node.clock[-1]
        rtf = (s1 - s0) / (w1 - w0) if w1 > w0 else 1.0
    hz = {k: rate(v, dt) / rtf for k, v in node.t.items()}
    if rtf != 1.0:
        print(f"  [info] sim real-time factor {rtf:.2f}: rates below are per SIMULATED second (wall Hz / rtf)")
    check("stream left image", hz["left"] >= args.min_image_hz, f"{hz['left']:.1f} Hz (>= {args.min_image_hz})")
    check("stream right image", hz["right"] >= args.min_image_hz, f"{hz['right']:.1f} Hz (>= {args.min_image_hz})")
    check("stream depth", hz["depth"] >= args.min_depth_hz, f"{hz['depth']:.1f} Hz (>= {args.min_depth_hz})")
    check("stream point cloud", hz["cloud"] > 0.5, f"{hz['cloud']:.1f} Hz")
    check("stream odom", hz["odom"] >= 10.0, f"{hz['odom']:.1f} Hz (>= 10)")
    check("stream imu", hz["imu"] >= 30.0, f"{hz['imu']:.1f} Hz (>= 30; sim publishes it itself, docs/zed-sdk-sim.md)")

    left, right = node.info.get("left"), node.info.get("right")
    if left and right:
        check("camera_info size", (left.width, left.height) == ZED_MINI_HD720, f"{left.width}x{left.height} (ZED Mini HD720 = 1280x720)")
        fx = left.k[0]
        baseline = -right.p[3] / right.p[0] if right.p[0] else float("nan")
        check("camera_info fx", 400.0 < fx < 900.0, f"fx={fx:.1f} px (per-unit factory calibration; read camera_info, never hard-code)")
        check("stereo baseline", abs(baseline - BASELINE_M) < 0.003, f"{baseline * 1000:.1f} mm (ZED Mini 63 mm; right P[0,3]/P[0,0])")
    else:
        check("camera_info", False, "left/right color/rect/camera_info not received")

    d = node.depth
    if d is not None:
        finite = np.isfinite(d) & (d > 0)
        frac = float(finite.mean())
        lo, hi = (np.percentile(d[finite], [5, 95]) if finite.any() else (math.nan, math.nan))
        check("depth encoding", node.depth_encoding == "32FC1", node.depth_encoding)
        check("depth coverage", frac > 0.4, f"{frac * 100:.0f}% finite pixels (> 40%)")
        check("depth range", args.depth_range[0] <= lo and hi <= args.depth_range[1], f"5-95 percentile {lo:.2f}-{hi:.2f} m, allowed {args.depth_range}")
    else:
        check("depth", False, "no 32FC1 depth image received")

    h = node.health
    if h:
        flags = {k: getattr(h, k) for k in ("low_image_quality", "low_lighting", "low_depth_reliability", "low_motion_sensors_reliability")}
        check("health flags", not any(flags.values()), ", ".join(f"{k}={v}" for k, v in flags.items()))
    else:
        check("health flags", False, "status/health not received")
    tr = node.track
    if tr:
        check("tracking status", tr.odometry_status == PosTrackStatus.OK and tr.status != PosTrackStatus.LOST,
              f"odometry_status={tr.odometry_status} (0=OK) status={tr.status}")
    else:
        check("tracking status", False, "pose/status not received")

    if len(node.odom) > 2:
        a = np.array([s[1:] for s in node.odom])
        check("odom finite", bool(np.isfinite(a).all()), f"frames {node.frames[0]} -> {node.frames[1]}")
        od_len = path_length(node.odom)
        gt_len = path_length(node.gt) if node.gt else None
        if gt_len is None:
            check("odom moves", True, f"path {od_len:.2f} m in {dt:.0f} s (no ground truth)")
        elif gt_len < 0.5:
            check("odom still", od_len < 0.15, f"truth path {gt_len:.2f} m, odom path {od_len:.2f} m (drone is hovering/parked)")
        else:
            ratio = od_len / gt_len
            check("odom vs truth (path length)", abs(ratio - 1.0) <= args.scale_tol,
                  f"odom {od_len:.2f} m / truth {gt_len:.2f} m = {ratio:.2f} (|ratio-1| <= {args.scale_tol})")
            rmse, yaw, final = trajectory_rmse(node.odom, node.gt)
            check("odom vs truth (trajectory)", rmse <= args.max_rmse,
                  f"RMSE {rmse:.3f} m, end error {final:.3f} m, odom frame yawed {yaw:.1f} deg vs map (<= {args.max_rmse} m RMSE)")
    else:
        check("odom", False, "fewer than 3 odometry samples")

    width = max(len(n) for n, _, _ in results)
    ok_all = True
    for name, ok, detail in results:
        ok_all &= ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<{width}}  {detail}")
    print("ZED SDK CHECK:", "PASS" if ok_all else "FAIL")
    node.destroy_node()
    rclpy.shutdown()
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
