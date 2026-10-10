#!/usr/bin/env python3
"""
ToF rangefinder + optical-flow benchmark flight (docs/range-flow.md). Needs SIM_SCENARIO=single_iris_flow.

Flies a profile that excites both sensors, in OFFBOARD like tests/vio_flight.py (whose Flight class it reuses):
  ground (ToF at rest) -> takeoff 1 m -> altitude steps 0.5 / 2 / 3.5 / 4.5 m -> velocity legs at 1.5 m along x and y at
  0.5 / 1 / 2 m/s (out and back) -> yaw 90 deg steps -> 3 m square at 2 m -> OFFBOARD descent, land, disarm.

It records the ROS side only: MAVROS `mavros/hrlv_ez4_pub` (sensor_msgs/Range, what a companion computer sees) and the
Pegasus ground truth `state/pose`, to <out>/range.csv and <out>/gt.csv. The sensor-level and EKF2-level analysis reads
PX4's own log (flow, 50 Hz ToF, innovations, *_groundtruth on one clock): tests/range_flow_eval.py.

    SIM_SCENARIO=single_iris_flow ./bisg all headless
    docker exec bisg-ros bash -lc 'source /opt/ros/jazzy/setup.bash; python3 /workspace/tests/range_flow_bench.py --out /tmp/rf'
Exit 0 = the profile was flown and the vehicle landed (accuracy is judged by range_flow_eval.py, not here).
"""
import argparse
import csv
import math
import os
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import ExtendedState, PositionTarget
from mavros_msgs.srv import CommandBool
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Range

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vio_flight import Abort, Flight  # noqa: E402


class Bench(Flight):
    def __init__(self, drone, tol, out):
        super().__init__(drone, tol, "")
        os.makedirs(out, exist_ok=True)
        ns = f"/drone_{drone}"
        self.vel = None             # (vx, vy) ENU m/s with z held at self.sp; None = position setpoint
        self.yaw = 0.0              # ENU yaw of the setpoint, rad
        self._rf = open(os.path.join(out, "range.csv"), "w", newline="")
        self._gf = open(os.path.join(out, "gt.csv"), "w", newline="")
        self.w_range, self.w_gt = csv.writer(self._rf), csv.writer(self._gf)
        self.w_range.writerow(["t_recv", "t_stamp", "range", "min_range", "max_range", "frame_id", "phase"])
        self.w_gt.writerow(["t_recv", "x", "y", "z", "qx", "qy", "qz", "qw"])
        self.n_range = 0
        self.node.create_subscription(Range, f"{ns}/mavros/hrlv_ez4_pub", self._on_range, qos_profile_sensor_data)
        self.node.create_subscription(PoseStamped, f"{ns}/state/pose", self._on_gt_row, qos_profile_sensor_data)

    def now(self):
        return self.node.get_clock().now().nanoseconds * 1e-9

    def _on_range(self, m):
        self.n_range += 1
        st = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
        self.w_range.writerow([f"{self.now():.4f}", f"{st:.4f}", f"{m.range:.4f}", f"{m.min_range:.3f}",
                               f"{m.max_range:.3f}", m.header.frame_id, self.phase])

    def _on_gt_row(self, m):
        p, q = m.pose.position, m.pose.orientation
        self.w_gt.writerow([f"{self.now():.4f}", f"{p.x:.4f}", f"{p.y:.4f}", f"{p.z:.4f}",
                            f"{q.x:.5f}", f"{q.y:.5f}", f"{q.z:.5f}", f"{q.w:.5f}"])

    def _stream(self):
        if self.streaming and self.vel is not None and self.descend is None:
            t = PositionTarget()
            t.header.stamp = self.node.get_clock().now().to_msg()
            t.coordinate_frame = PositionTarget.FRAME_LOCAL_NED      # MAVROS takes ENU values and converts
            t.type_mask = (PositionTarget.IGNORE_PX | PositionTarget.IGNORE_PY | PositionTarget.IGNORE_VZ
                           | PositionTarget.IGNORE_AFX | PositionTarget.IGNORE_AFY | PositionTarget.IGNORE_AFZ
                           | PositionTarget.IGNORE_YAW_RATE)
            t.position.z = self.sp.pose.position.z
            t.velocity.x, t.velocity.y = float(self.vel[0]), float(self.vel[1])
            t.yaw = self.yaw
            self.pub_raw.publish(t)
            return
        super()._stream()

    def set_yaw(self, yaw):
        self.yaw = yaw
        self.sp.pose.orientation.z, self.sp.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)

    def sim_sleep(self, seconds):
        end = self.now() + seconds
        while self.now() < end:
            self.spin()

    def leg(self, vx, vy, dist, phase):
        """Fly `dist` m at (vx, vy) ENU m/s (sim-time duration), then hold where it stopped."""
        self.phase = phase
        self.vel = (vx, vy)
        self.sim_sleep(dist / math.hypot(vx, vy))
        self.vel = None
        self.sp.pose.position.x, self.sp.pose.position.y = self.est[0], self.est[1]
        self.sim_sleep(2.0)
        print(f"[range_flow] {phase:10s} done est={[round(v, 2) for v in self.est]} "
              f"truth={[round(v, 2) for v in self.truth]} ranges={self.n_range}", flush=True)

    def close(self):
        self._rf.close()
        self._gf.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--out", default="/tmp/range_flow")
    ap.add_argument("--tol", type=float, default=0.5, help="abort when |est - truth| > 3*tol (vio_flight rule)")
    ap.add_argument("--speeds", default="0.5,1.0,2.0", help="velocity-leg speeds, m/s")
    ap.add_argument("--leg", type=float, default=3.0, help="velocity-leg length, m")
    ap.add_argument("--alts", default="0.5,2.0,3.5,4.5", help="altitude steps, m (flow works up to 5 m)")
    a = ap.parse_args()

    rclpy.init()
    f = Bench(a.drone, a.tol, a.out)
    t_start = time.time()
    try:
        if not f.wait_for(lambda: f.truth and f.est and f.state.connected, 60,
                          "ground truth + local_position + MAVROS connected"):
            return 2
        f.phase = "ground"
        f.sim_sleep(3.0)                                    # ToF at rest (PX4 does not log before arming)
        f.truth0, f.est0 = f.truth, f.est
        print(f"[range_flow] start est={[round(v, 2) for v in f.est0]} truth={[round(v, 2) for v in f.truth0]} "
              f"ranges so far={f.n_range}", flush=True)
        if f.n_range == 0:
            print("[range_flow] no mavros/hrlv_ez4_pub messages: is this single_iris_flow with the lean MAVROS list?",
                  flush=True)

        f.sp.pose.position.x, f.sp.pose.position.y, f.sp.pose.position.z = f.est0[0], f.est0[1], f.est0[2] + 1.0
        f.set_yaw(0.0)
        f.streaming = True
        f.spin_for(2.0)
        if not f.set_mode("OFFBOARD"):
            return 3
        r = f.call(f.cli_arm, CommandBool.Request(value=True))
        if not (r and r.success) or not f.wait_for(lambda: f.state.armed, 10, "armed"):
            return 3
        if not f.goto(0, 0, 1.0, 5, "takeoff"):
            return 4
        for alt in [float(v) for v in a.alts.split(",")]:
            if not f.goto(0, 0, alt, 6, f"alt-{alt:g}"):
                return 4
        if not f.goto(0, 0, 1.5, 3, "alt-1.5"):
            return 4
        for v in [float(s) for s in a.speeds.split(",")]:
            f.leg(v, 0, a.leg, f"x+{v:g}")
            f.leg(-v, 0, a.leg, f"x-{v:g}")
            f.leg(0, v, a.leg, f"y+{v:g}")
            f.leg(0, -v, a.leg, f"y-{v:g}")
        for k in (1, 2, 3, 4):
            f.set_yaw(k * math.pi / 2)
            f.phase = f"yaw-{90 * k}"
            f.sim_sleep(5.0)
        f.set_yaw(0.0)
        s = 3.0
        for dx, dy, name in [(s, 0, "sq-1"), (s, s, "sq-2"), (0, s, "sq-3"), (0, 0, "sq-4")]:
            if not f.goto(dx, dy, 2.0, 2, name):
                return 4

        f.phase = "land"
        f.descend = 0.5
        if not f.wait_for(lambda: f.ext.landed_state == ExtendedState.LANDED_STATE_ON_GROUND, 90, "on ground"):
            return 5
        f.call(f.cli_arm, CommandBool.Request(value=False))
        f.streaming = False
        if not f.wait_for(lambda: not f.state.armed, 60, "disarmed"):
            return 5
        f.phase = "landed"
        f.sim_sleep(2.0)
        print(f"[range_flow] landed. {f.n_range} Range messages, wall {time.time() - t_start:.0f} s, "
              f"files in {a.out}", flush=True)
        return 0
    except Abort as exc:
        f.kill(str(exc))
        return 10
    finally:
        f.close()
        f.node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    sys.exit(main())
