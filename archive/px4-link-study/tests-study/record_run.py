#!/usr/bin/env python3
"""
Recorder for the VO/perception study: runs inside the ZED container next to the wrapper (rclpy + zed_msgs).

Writes, under --out:
  truth.csv      Pegasus ground truth (state/pose): stamp (wall), recv wall, x y z qx qy qz qw
  odom_live.csv  the wrapper's live odometry, same columns (+ frame ids in the header comment)
  clock.csv      (wall, sim time) pairs from /clock: truth is stamped with the wall clock, the SDK stamps with sim time + a
                 constant, so the analysis maps both onto sim time
  frames.csv     stamp of every left image (the SDK's grab times, wall clock) -> real frame rate
and, with --svo, records the camera to an SVO2 file (lossless) through the wrapper's start_svo_rec / stop_svo_rec services,
so every setting can later be replayed offline on identical pixels.

    docker exec -d bisg-zed-1 bash -lc 'source /sbin/ros_entrypoint.sh; python3 /workspace/tests/study/record_run.py --out /tmp/study/run1 --svo /tmp/study/run1/flight.svo2'
Stop with SIGINT / `touch <out>/STOP`.
"""
import argparse
import csv
import os
import signal
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Image
from zed_msgs.srv import StartSvoRec
from std_srvs.srv import Trigger

BE = QoSProfile(depth=50, reliability=ReliabilityPolicy.BEST_EFFORT)


class Rec(Node):
    def __init__(self, a):
        super().__init__("study_recorder")
        self.a = a
        os.makedirs(a.out, exist_ok=True)
        r = f"/drone_{a.drone}"
        self.truth, self.odom, self.frames, self.clock = [], [], [], []
        self.create_subscription(Clock, "/clock", self.on_clock, BE)
        self.create_subscription(PoseStamped, f"{r}/state/pose", self.on_truth, BE)
        self.create_subscription(Odometry, f"{r}/zed/zed_node/odom", self.on_odom, BE)
        self.create_subscription(Image, f"{r}/zed/zed_node/left/color/rect/image", self.on_frame, BE)
        self.t0 = time.time()
        if a.svo:
            self.start_svo()

    @staticmethod
    def st(h):
        return h.stamp.sec + h.stamp.nanosec * 1e-9

    def on_truth(self, m):
        p, q = m.pose.position, m.pose.orientation
        self.truth.append((self.st(m.header), time.time(), p.x, p.y, p.z, q.x, q.y, q.z, q.w))

    def on_odom(self, m):
        p, q = m.pose.pose.position, m.pose.pose.orientation
        self.odom.append((self.st(m.header), time.time(), p.x, p.y, p.z, q.x, q.y, q.z, q.w))
        self.odom_frames = (m.header.frame_id, m.child_frame_id)

    def on_clock(self, m):
        self.clock.append((time.time(), m.clock.sec + m.clock.nanosec * 1e-9))

    def on_frame(self, m):
        self.frames.append((self.st(m.header), time.time()))

    def start_svo(self):
        cli = self.create_client(StartSvoRec, f"/drone_{self.a.drone}/zed/zed_node/start_svo_rec")
        if not cli.wait_for_service(timeout_sec=20):
            self.get_logger().error("start_svo_rec not available")
            return
        req = StartSvoRec.Request()
        req.bitrate, req.compression_mode, req.target_framerate, req.input_transcode = 0, 0, 0, False
        req.svo_filename = self.a.svo
        fut = cli.call_async(req)
        rclpy.spin_until_future_complete(self, fut, timeout_sec=20)
        r = fut.result()
        self.get_logger().info(f"start_svo_rec: {r.success if r else None} {r.message if r else ''}")

    def stop_svo(self):
        cli = self.create_client(Trigger, f"/drone_{self.a.drone}/zed/zed_node/stop_svo_rec")
        if cli.wait_for_service(timeout_sec=5):
            fut = cli.call_async(Trigger.Request())
            rclpy.spin_until_future_complete(self, fut, timeout_sec=30)

    def save(self):
        hdr = ["stamp", "recv", "x", "y", "z", "qx", "qy", "qz", "qw"]
        for name, rows, h in (("truth.csv", self.truth, hdr), ("odom_live.csv", self.odom, hdr), ("frames.csv", self.frames, ["stamp", "recv"]),
                              ("clock.csv", self.clock, ["recv", "sim"])):
            with open(os.path.join(self.a.out, name), "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(h)
                w.writerows(rows)
        self.get_logger().info(f"saved truth {len(self.truth)}, odom {len(self.odom)}, frames {len(self.frames)} -> {self.a.out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--svo", default="")
    a = ap.parse_args()
    rclpy.init()
    n = Rec(a)
    stop = {"v": False}
    signal.signal(signal.SIGINT, lambda *_: stop.update(v=True))
    signal.signal(signal.SIGTERM, lambda *_: stop.update(v=True))
    flag = os.path.join(a.out, "STOP")
    while not stop["v"] and not os.path.exists(flag):
        rclpy.spin_once(n, timeout_sec=0.1)
    if a.svo:
        n.stop_svo()
    n.save()
    return 0


if __name__ == "__main__":
    sys.exit(main())
