#!/usr/bin/env python3
"""
ROS side of the ZED pool-depth probe (sim/tools/zed_pool_probe.py): record the wrapper's depth with the wall-clock
receive time, decimated, until --seconds pass or <out>/stop exists. Writes <out>/sdk_depth.npz + camera_info.json.

    docker exec bisg-ros bash -lc 'source /opt/ros/jazzy/setup.bash; python3 /workspace/tests/zed_pool_probe_collect.py --out /tmp/zprobe'
"""
import argparse
import json
import os
import time

import numpy as np
import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--out", default="/tmp/zprobe")
    ap.add_argument("--stride", type=int, default=4, help="keep every Nth pixel (memory)")
    ap.add_argument("--seconds", type=float, default=1800.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ns = f"/drone_{a.drone}/zed/zed_node"
    rclpy.init()
    node = rclpy.create_node("zed_pool_probe_collect")
    frames, t_recv, stamps, info = [], [], [], {}

    def on_depth(m):
        if m.encoding != "32FC1":
            return
        d = np.frombuffer(m.data, dtype=np.float32).reshape(m.height, m.step // 4)[:, :m.width]
        frames.append(d[::a.stride, ::a.stride].astype(np.float16))
        t_recv.append(time.time())
        stamps.append(m.header.stamp.sec + m.header.stamp.nanosec * 1e-9)
        if len(frames) % 100 == 0:
            print(f"[collect] {len(frames)} depth frames", flush=True)

    def on_info(m):
        if not info:
            info.update({"width": m.width, "height": m.height, "k": list(m.k), "p": list(m.p), "frame": m.header.frame_id})
            print(f"[collect] camera_info {info['width']}x{info['height']} fx={m.k[0]:.1f}", flush=True)

    node.create_subscription(Image, f"{ns}/depth/depth_registered", on_depth, qos_profile_sensor_data)
    node.create_subscription(CameraInfo, f"{ns}/left/color/rect/camera_info", on_info, qos_profile_sensor_data)
    print(f"[collect] recording {ns}/depth/depth_registered", flush=True)
    end = time.time() + a.seconds
    while time.time() < end and not os.path.exists(os.path.join(a.out, "stop")):
        rclpy.spin_once(node, timeout_sec=0.1)
    np.savez_compressed(os.path.join(a.out, "sdk_depth.npz"), depth=np.stack(frames) if frames else np.zeros((0, 1, 1)),
                        t_recv=np.array(t_recv), stamp=np.array(stamps), stride=a.stride)
    with open(os.path.join(a.out, "camera_info.json"), "w") as fh:
        json.dump(info, fh)
    print(f"[collect] saved {len(frames)} frames", flush=True)
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == "__main__":
    main()
