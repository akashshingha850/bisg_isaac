#!/usr/bin/env python3
"""
Does the sim ZED's heading slip when the yaw crosses +-180 deg? (docs/vio-drift.md)

The long drift flights (tests/drift_flight.py) lost 20-40 deg of ZED heading in single turns, each time as the true yaw crossed
+-180 deg. Hypothesis: a quaternion hemisphere flip (w = cos(yaw/2) changes sign at 180 deg) in the IMU orientation fed into the
stream. This flight separates the two: hover at --alt and turn through the same angles twice, first never crossing 180 deg
(0 -> 90 -> 170 -> 90 -> 0 -> -90 -> -170 -> -90 -> 0), then across it (170 <-> -170, 20 deg each way through 180), holding --hold s after each turn. Printed per turn: the ZED odom yaw error added (vs ground truth) and EKF2's.
Results also in <out>/turns.csv.

    docker exec bisg-ros bash -lc 'source /opt/ros/jazzy/setup.bash; python3 /workspace/tests/yaw_wrap_test.py --out /tmp/yawwrap'
"""
import argparse
import csv
import math
import os
import sys

import rclpy
from mavros_msgs.msg import ExtendedState
from mavros_msgs.srv import CommandBool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from drift_flight import Drift, wrap  # noqa: E402
from vio_flight import Abort  # noqa: E402

NO_CROSS = [90, 170, 90, 0, -90, -170, -90, 0]
CROSS = [90, 170, -170, 170, -170, 170, 90, 0, -90, -170, 170, -170, 170, -90, 0]   # 170 <-> -170 = 20 deg through 180


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--out", default="/tmp/yawwrap")
    ap.add_argument("--alt", type=float, default=2.0)
    ap.add_argument("--hold", type=float, default=4.0)
    a = ap.parse_args()
    rclpy.init()
    f = Drift(a.drone, 1.0, a.out)
    rows = []
    try:
        if not f.wait_for(lambda: f.truth and f.truth_q and f.est and f.state.connected and f.src["zed_odom"], 60, "ready"):
            return 2
        f.phase = "ground"
        f.sim_sleep(3.0)
        f.truth0, f.est0 = f.truth, f.est
        f.snapshot_ref()
        f.sp.pose.position.x, f.sp.pose.position.y, f.sp.pose.position.z = f.est0[0], f.est0[1], f.est0[2] + a.alt
        f.set_yaw(0.0)
        f.streaming = True
        f.spin_for(2.0)
        if not f.set_mode("OFFBOARD"):
            return 3
        r = f.call(f.cli_arm, CommandBool.Request(value=True))
        if not (r and r.success) or not f.wait_for(lambda: f.state.armed, 10, "armed"):
            return 3
        if not f.goto(0, 0, a.alt, 8, "takeoff"):
            return 4
        for block, seq in (("no-cross", NO_CROSS), ("cross", CROSS)):
            for target in seq:
                e0 = f.errors()
                prev = math.degrees(f.yaw)
                f.phase = f"{block}->{target}"
                f.turn_to(math.radians(target), settle=a.hold)
                e1 = f.errors()
                crossed = abs(target - prev) > 180 or (prev * target < 0 and abs(prev) > 90 and abs(target) > 90)
                row = {"block": block, "from": round(prev), "to": target, "crossed_180": crossed,
                       "zed_added_deg": round(e1["zed_odom"][1] - e0["zed_odom"][1], 2),
                       "ekf2_added_deg": round(e1["ekf2"][1] - e0["ekf2"][1], 2), "zed_total_deg": round(e1["zed_odom"][1], 2)}
                rows.append(row)
                print(f"[yawwrap] {block:8s} {row['from']:5d} -> {target:5d}  crossed180={crossed!s:5s}  zed +{row['zed_added_deg']:6.2f}  "
                      f"ekf2 +{row['ekf2_added_deg']:6.2f}  zed total {row['zed_total_deg']:6.2f} deg", flush=True)
        f.phase = "land"
        f.descend = 0.5
        if not f.wait_for(lambda: f.ext.landed_state == ExtendedState.LANDED_STATE_ON_GROUND, 90, "on ground"):
            return 5
        f.call(f.cli_arm, CommandBool.Request(value=False))
        f.streaming = False
        f.wait_for(lambda: not f.state.armed, 60, "disarmed")
        return 0
    except Abort as exc:
        f.kill(str(exc))
        return 10
    finally:
        if rows:
            with open(os.path.join(a.out, "turns.csv"), "w", newline="") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0]))
                w.writeheader()
                w.writerows(rows)
            for block in ("no-cross", "cross"):
                for c in (False, True):
                    v = [abs(r["zed_added_deg"]) for r in rows if r["block"] == block and r["crossed_180"] == c]
                    if v:
                        print(f"[yawwrap] {block} crossed180={c}: n={len(v)} mean |slip| {sum(v) / len(v):.2f} max {max(v):.2f} deg")
        f.close()
        f.node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    sys.exit(main())
