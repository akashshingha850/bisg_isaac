#!/usr/bin/env python3
"""
ZED depth check against a known box (scenario `world.objects`, e.g. single_iris_vio's depth_box).

Takes one zed/zed_node/point_cloud/cloud_registered (sim ZED depth -> 3D, zed_left_camera_frame) and the
drone's ground-truth pose, puts the points in the world frame, and compares the ones that land on the
box with its known faces: front face position (x), width (y) and height (z), and the top face when
seen from above. Sim depth is exact geometry, so errors should be millimetres; anything larger means a
wrong camera pose, intrinsics or frame.

    docker exec bisg-ros python3 /workspace/tests/zed_depth_box.py                 # parked: front face
    docker exec bisg-ros python3 /workspace/tests/vio_flight.py --hold 30 &        # or hovering at 2 m:
    docker exec bisg-ros python3 /workspace/tests/zed_depth_box.py --min-alt 1.9   #   front + top face
Exit 0 = PASS. Reading ground truth is test-only (parity rule, plan.md §8).
"""
import argparse
import os
import sys
import time

import numpy as np
import rclpy
import yaml
from geometry_msgs.msg import PoseStamped
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2


def load_scenario(path):
    """Same `extends:` deep-merge as sim/launcher/launch.py."""
    with open(path) as f:
        cfg = yaml.safe_load(f) or {}
    base = cfg.pop("extends", None)
    if not base:
        return cfg

    def merge(a, b):
        out = dict(a)
        for k, v in b.items():
            out[k] = merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
        return out
    return merge(load_scenario(os.path.join(os.path.dirname(path), base)), cfg)


def quat_xyzw_to_matrix(x, y, z, w):
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", default="single_iris_vio")
    ap.add_argument("--object", default="depth_box")
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--tol", type=float, default=0.03, help="max face error, metres")
    ap.add_argument("--timeout", type=float, default=60.0)
    ap.add_argument("--min-alt", type=float, default=None,
                    help="only use clouds taken with the drone at least this high (m), e.g. 1.8 for the hover")
    a = ap.parse_args()

    path = a.scenario if a.scenario.endswith(".yaml") else f"/workspace/sim/configs/{a.scenario}.yaml"
    cfg = load_scenario(path)
    box = next((o for o in (cfg.get("world", {}).get("objects") or []) if o.get("name") == a.object), None)
    if box is None:
        print(f"[depth_box] no world.objects entry named {a.object!r} in {path}")
        return 2
    c = np.array(box["position"], float)
    s = np.array(box["size"], float)
    lo, hi = c - s / 2, c + s / 2
    zed = cfg["vehicles"][a.drone - 1]["sensors"]["zed"]
    mount = np.array(zed.get("mount_xyz_rpy", [0.18, 0, -0.02, 0, 0, 0])[:3], float)
    if any(abs(float(r)) > 1e-6 for r in zed.get("mount_xyz_rpy", [0] * 6)[3:]):
        print("[depth_box] mount rotation not supported by this check (rpy must be 0)")
        return 2
    left_in_body = mount + np.array([0.0, float(zed.get("baseline", 0.063)) / 2, 0.0])

    rclpy.init()
    n = rclpy.create_node("zed_depth_box", parameter_overrides=[Parameter("use_sim_time", value=True)])
    ns = f"/drone_{a.drone}"
    st = {"cloud": None, "pose": None}
    def on_cloud(m):
        pose = st["pose"]
        if pose is not None and (a.min_alt is None or pose.pose.position.z >= a.min_alt):
            st["cloud"] = (m, pose)
    n.create_subscription(PointCloud2, f"{ns}/zed/zed_node/point_cloud/cloud_registered", on_cloud,
                          qos_profile_sensor_data)
    n.create_subscription(PoseStamped, f"{ns}/state/pose", lambda m: st.__setitem__("pose", m), qos_profile_sensor_data)
    end = time.time() + a.timeout
    while time.time() < end and not (st["cloud"] and st["cloud"][1]):
        rclpy.spin_once(n, timeout_sec=0.05)
    if not (st["cloud"] and st["cloud"][1]):
        print("[depth_box] no point cloud + pose (is point_cloud.enabled true? B2: the 0.9 MB clouds may drop)")
        return 3
    m, pose = st["cloud"]

    pts = np.frombuffer(m.data, np.float32).reshape(m.height, m.width, 4)[..., :3].reshape(-1, 3).astype(float)
    pts = pts[np.isfinite(pts).all(1)]
    q, p = pose.pose.orientation, pose.pose.position
    R = quat_xyzw_to_matrix(q.x, q.y, q.z, q.w)
    body = np.array([p.x, p.y, p.z])
    world = (pts + left_in_body) @ R.T + body  # mount rotation is identity: camera FLU = body FLU
    cam_world = R @ left_in_body + body

    margin = 0.05
    on = np.all((world > lo - margin) & (world < hi + margin), axis=1)
    b = world[on]
    print(f"[depth_box] {a.object}: x {lo[0]:.2f}..{hi[0]:.2f}  y {lo[1]:.2f}..{hi[1]:.2f}  z {lo[2]:.2f}..{hi[2]:.2f} m | "
          f"left camera at {cam_world.round(3).tolist()} | cloud {m.width}x{m.height}, {on.sum()} points on the box")
    if on.sum() < 50:
        print("[depth_box] FAIL: box not in view (or cloud frame/pose wrong)")
        return 4

    ok = True
    # Front face (the one facing the camera along -x): points near x = lo[0]
    front = b[np.abs(b[:, 0] - lo[0]) < 0.10]
    if len(front) > 20:
        fx_err = np.median(front[:, 0]) - lo[0]
        spread = np.percentile(front[:, 0], 95) - np.percentile(front[:, 0], 5)
        w_meas = front[:, 1].max() - front[:, 1].min()
        h_meas = front[:, 2].max() - front[:, 2].min()
        dist = lo[0] - cam_world[0]
        print(f"[depth_box] front face: {len(front)} pts, x error {fx_err * 1000:+.1f} mm (flatness p5-p95 "
              f"{spread * 1000:.1f} mm) at {dist:.2f} m from the lens | width {w_meas:.3f} m (true {s[1]:.3f}) "
              f"height {h_meas:.3f} m (true {s[2]:.3f}, lower edge may be hidden)")
        ok &= abs(fx_err) <= a.tol and abs(w_meas - s[1]) <= 2 * a.tol + 0.02
    else:
        print("[depth_box] front face not seen")
        ok = False
    # Top face: seen from above (camera higher than the box)
    top = b[np.abs(b[:, 2] - hi[2]) < 0.05]
    if cam_world[2] > hi[2] + 0.1 and len(top) > 20:
        tz_err = np.median(top[:, 2]) - hi[2]
        print(f"[depth_box] top face: {len(top)} pts, z error {tz_err * 1000:+.1f} mm")
        ok &= abs(tz_err) <= a.tol
    elif cam_world[2] > hi[2] + 0.1:
        print("[depth_box] top face expected (camera above the box) but not seen")
    print(f"[depth_box] {'PASS' if ok else 'FAIL'} (tol {a.tol * 1000:.0f} mm)")
    n.destroy_node()
    rclpy.try_shutdown()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
