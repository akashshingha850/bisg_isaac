#!/usr/bin/env python3
"""
ZED VIO benchmark flight for the GPS-denied default (docs/vio.md): excites what EKF2 takes from the ZED (horizontal position,
3D velocity, yaw) in the default world, in OFFBOARD like tests/vio_flight.py (Flight / range_flow_bench.Bench are reused).

Profile (all relative to the start pose on the floor, facing +x; sized for Simple Room with >= 1 m to the walls, so it fits the
Warehouse default unchanged):
  ground -> takeoff 1.2 m + 20 s hover -> altitude steps 0.6 / 2.0 / 1.2 m -> velocity legs x and y +-1.5 m at 0.5 / 1.0 m/s
  -> yaw 90 deg steps -> the x legs again yawed 90 deg (camera looking sideways: body-frame velocity check) -> 1.5 m square
  -> 20 s hover -> OFFBOARD descent, land, disarm.
In Simple Room the x+ legs crossed the table edge (0.78 m step under the drone); the Warehouse floor is flat.

Analysis is offline from PX4's log (`vehicle_visual_odometry` + the twin's `*_groundtruth`, one clock): tests/vio_eval.py.

    ./bisg all headless                      # default sim.yaml: raptor, GPS-denied, sensors.ground_truth on
    docker exec bisg-ros bash -lc 'source /opt/ros/jazzy/setup.bash; python3 /workspace/tests/vio_bench.py --out /tmp/vio'
Exit 0 = the profile was flown and the vehicle landed (accuracy is judged by vio_eval.py, not here).
"""
import argparse
import math
import os
import sys
import time

import rclpy
from mavros_msgs.msg import ExtendedState
from mavros_msgs.srv import CommandBool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from range_flow_bench import Bench  # noqa: E402
from vio_flight import Abort  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--out", default="/tmp/vio_bench")
    ap.add_argument("--tol", type=float, default=0.5, help="abort when |est - truth| > 3*tol (vio_flight rule)")
    ap.add_argument("--alt", type=float, default=1.2)
    ap.add_argument("--leg", type=float, default=1.5, help="velocity-leg length, m")
    ap.add_argument("--speeds", default="0.5,1.0", help="velocity-leg speeds, m/s")
    ap.add_argument("--hover", type=float, default=20.0, help="hover seconds after takeoff and before landing")
    a = ap.parse_args()

    rclpy.init()
    f = Bench(a.drone, a.tol, a.out)
    t_start = time.time()
    try:
        if not f.wait_for(lambda: f.truth and f.est and f.state.connected, 60,
                          "ground truth + local_position + MAVROS connected"):
            return 2
        f.phase = "ground"
        f.sim_sleep(3.0)
        f.truth0, f.est0 = f.truth, f.est
        print(f"[vio_bench] start est={[round(v, 2) for v in f.est0]} truth={[round(v, 2) for v in f.truth0]}", flush=True)

        f.sp.pose.position.x, f.sp.pose.position.y, f.sp.pose.position.z = f.est0[0], f.est0[1], f.est0[2] + a.alt
        f.set_yaw(0.0)
        f.streaming = True
        f.spin_for(2.0)
        if not f.set_mode("OFFBOARD"):
            return 3
        r = f.call(f.cli_arm, CommandBool.Request(value=True))
        if not (r and r.success) or not f.wait_for(lambda: f.state.armed, 10, "armed"):
            return 3
        if not f.goto(0, 0, a.alt, a.hover, "takeoff"):
            return 4
        for alt in (0.6, 2.0, a.alt):
            if not f.goto(0, 0, alt, 4, f"alt-{alt:g}"):
                return 4
        for v in [float(s) for s in a.speeds.split(",")]:
            f.leg(v, 0, a.leg, f"x+{v:g}")
            f.leg(-v, 0, a.leg, f"x-{v:g}")
            f.leg(0, v, a.leg, f"y+{v:g}")
            f.leg(0, -v, a.leg, f"y-{v:g}")
        for k in (1, 2, 3, 4):
            f.set_yaw(k * math.pi / 2)
            f.phase = f"yaw-{90 * k}"
            f.sim_sleep(6.0)
        f.set_yaw(math.pi / 2)
        f.phase = "yaw-90"
        f.sim_sleep(4.0)
        v = float(a.speeds.split(",")[-1])
        f.leg(v, 0, a.leg, f"yawed-x+{v:g}")
        f.leg(-v, 0, a.leg, f"yawed-x-{v:g}")
        f.set_yaw(0.0)
        f.phase = "yaw-0"
        f.sim_sleep(4.0)
        s = a.leg
        for dx, dy, name in [(s, 0, "sq-1"), (s, s, "sq-2"), (0, s, "sq-3"), (0, 0, "sq-4")]:
            if not f.goto(dx, dy, a.alt, 2, name):
                return 4
        f.phase = "hover-end"
        f.sim_sleep(a.hover)

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
        err = [round(e, 3) for e in f.max_err]
        print(f"[vio_bench] landed. max|est - truth| xyz={err} m over {f.samples} airborne samples, "
              f"wall {time.time() - t_start:.0f} s, files in {a.out}", flush=True)
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
