#!/usr/bin/env python3
"""px4_bridge against FAKE ZED + MAVROS topics — no camera, no sim, no PX4. Runs inside the ZED image:

    ./bisg zed test-bridge          # = docker run bisg/zed:desktop python3 /workspace/tests/zed_bridge_fake.py

Starts `python3 -m zed_stack.bridge` with every module on, publishes a synthetic wall at 2 m, odometry and tracking status as
the wrapper would, and checks what comes out on the MAVROS topics: obstacle sectors, odometry (frames, restamp, silence on lost
tracking, recovery), STATUSTEXT, and the status JSON. Exit 0 = PASS.
"""
import json
import os
import subprocess
import sys
import tempfile
import time

import numpy as np
import rclpy
import yaml
from mavros_msgs.msg import StatusText
from nav_msgs.msg import Odometry
from rcl_interfaces.srv import SetParameters
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data
from sensor_msgs.msg import CameraInfo, Image, LaserScan
from std_msgs.msg import String
from zed_msgs.msg import HealthStatusStamped, PosTrackStatus

DRONE = "9"
NS = f"/drone_{DRONE}"
ZED = f"{NS}/zed/zed_node"
W, H, FX = 320, 180, 265.0
RELIABLE = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)


class Fake(Node):
    def __init__(self):
        super().__init__("fake_zed_and_mavros")
        self.track = PosTrackStatus.OK
        self.n = 0
        mk = self.create_publisher
        self.p_depth = mk(Image, f"{ZED}/depth/depth_registered", qos_profile_sensor_data)
        self.p_info = mk(CameraInfo, f"{ZED}/left/color/rect/camera_info", qos_profile_sensor_data)
        self.p_odom = mk(Odometry, f"{ZED}/odom", qos_profile_sensor_data)
        self.p_track = mk(PosTrackStatus, f"{ZED}/pose/status", qos_profile_sensor_data)
        self.p_health = mk(HealthStatusStamped, f"{ZED}/status/health", qos_profile_sensor_data)
        self.create_service(SetParameters, f"{NS}/mavros/obstacle/set_parameters", self.on_set)
        self.scans, self.odoms, self.texts, self.status = [], [], [], None
        self.create_subscription(LaserScan, f"{NS}/mavros/obstacle/send", lambda m: self.scans.append(m), 10)
        self.create_subscription(Odometry, f"{NS}/mavros/odometry/out", lambda m: self.odoms.append((time.monotonic(), m)), RELIABLE)
        self.create_subscription(StatusText, f"{NS}/mavros/statustext/send", lambda m: self.texts.append(m.text), 10)
        self.create_subscription(String, f"{NS}/zed_stack/status", self.on_status, 1)
        self.create_timer(0.05, self.feed)

    def on_set(self, req, res):
        res.results = [__import__("rcl_interfaces.msg", fromlist=["SetParametersResult"]).SetParametersResult(successful=True)
                       for _ in req.parameters]
        return res

    def on_status(self, msg):
        self.status = json.loads(msg.data)

    def feed(self):
        self.n += 1
        now = self.get_clock().now().to_msg()
        info = CameraInfo()
        info.header.stamp, info.width, info.height = now, W, H
        info.k = [FX, 0.0, W / 2, 0.0, FX, H / 2, 0.0, 0.0, 1.0]
        self.p_info.publish(info)
        img = Image()
        img.header.stamp, img.header.frame_id = now, "zed_left_camera_optical_frame"
        img.height, img.width, img.encoding, img.step = H, W, "32FC1", W * 4
        img.data = np.full((H, W), 2.0, np.float32).tobytes()
        self.p_depth.publish(img)
        od = Odometry()
        od.header.stamp = rclpy.time.Time(seconds=1, nanoseconds=0).to_msg()      # a stamp that restamp must replace
        od.header.frame_id, od.child_frame_id = "zed_odom", "zed_camera_link"
        od.pose.pose.position.x = 0.01 * self.n
        od.pose.pose.orientation.w = 1.0
        self.p_odom.publish(od)
        st = PosTrackStatus()
        st.odometry_status = self.track
        self.p_track.publish(st)
        hs = HealthStatusStamped()
        hs.header.stamp = now
        self.p_health.publish(hs)


def spin_for(node, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        rclpy.spin_once(node, timeout_sec=0.02)


def main():
    cfg = yaml.safe_load(open(os.path.join(os.path.dirname(__file__), "..", "docker", "zed", "zed.yaml")))
    cfg.pop("sim", None)
    br = cfg["services"]["px4_bridge"]
    br.update(enabled=True)
    br["odometry"].update(enabled=True, restamp=True, min_rate_hz=5.0)
    br["obstacle_distance"].update(enabled=True, band=2.0, rate_hz=10.0)
    br["health"].update(enabled=True)
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
        yaml.safe_dump(cfg, f)
    env = dict(os.environ, DRONE_ID=DRONE, ZED_STACK_CONFIG=f.name, ZED_STACK_SIM="0")
    bridge = subprocess.Popen([sys.executable, "-m", "zed_stack.bridge"], env=env, cwd=os.path.join(os.path.dirname(__file__), "..", "docker", "zed"))
    rclpy.init()
    node = Fake()
    fails = []

    def check(cond, what):
        print(f"  {'PASS' if cond else 'FAIL'}  {what}")
        if not cond:
            fails.append(what)

    try:
        spin_for(node, 6.0)
        print("steady state")
        check(len(node.scans) >= 10, f"obstacle/send flowing ({len(node.scans)} scans)")
        if node.scans:
            s = node.scans[-1]
            check(len(s.ranges) == 72, "72 sectors")
            check(abs(s.ranges[36] - 2.0) < 0.1, f"wall at 2 m seen straight ahead (sector 36 = {s.ranges[36]:.2f} m)")
            check(np.isinf(s.ranges[0]), "sector behind the drone is unknown (inf)")
        check(len(node.odoms) >= 20, f"odometry/out flowing ({len(node.odoms)})")
        if node.odoms:
            o = node.odoms[-1][1]
            check((o.header.frame_id, o.child_frame_id) == ("odom", "base_link"), f"frames odom/base_link ({o.header.frame_id}/{o.child_frame_id})")
            check(abs(o.header.stamp.sec - time.time()) < 5, "restamp: stamp is the arrival time, not the source's 1 s")
        check(node.status is not None and node.status["components"].get("odometry", {}).get("state") == "ok",
              f"status JSON: odometry ok ({node.status and node.status['components'].get('odometry')})")
        check(node.status is not None and node.status["components"].get("obstacle_distance", {}).get("state") == "ok",
              "status JSON: obstacle_distance ok (mav_frame set through MAVROS)")

        print("tracking lost")
        node.track = PosTrackStatus.UNAVAILABLE
        spin_for(node, 1.0)
        mark, texts_before = time.monotonic(), len(node.texts)
        spin_for(node, 2.0)
        late = [t for t, _ in node.odoms if t > mark]
        check(not late, f"odometry/out silent while tracking is lost ({len(late)} msgs in 2 s)")
        check(any("tracking" in t and "LOST" in t for t in node.texts[texts_before:]) or any("tracking" in t and "LOST" in t for t in node.texts),
              f"STATUSTEXT announces it: {[t for t in node.texts if 'ZED' in t]}")
        check(node.status["components"]["tracking"]["state"] == "lost", "status JSON: tracking lost")

        print("tracking recovered")
        node.track = PosTrackStatus.OK
        mark = time.monotonic()
        spin_for(node, 3.0)
        check(len([1 for t, _ in node.odoms if t > mark]) > 10, "odometry/out resumes")
        check(any("tracking" in t and "OK" in t for t in node.texts), "STATUSTEXT announces the recovery")
    finally:
        bridge.terminate()
        try:
            bridge.wait(5)
        except subprocess.TimeoutExpired:
            bridge.kill()
        node.destroy_node()
        rclpy.shutdown()
        os.unlink(f.name)
    print("PASS" if not fails else f"FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
