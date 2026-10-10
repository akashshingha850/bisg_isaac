"""mission_square — Phase 2 exit test (docs/roadmap.md): take off, fly a square, land, through MAVROS only.

    ros2 run bisg_vehicle mission_square --ns /drone_1                    # 5 m square at 2 m, AUTO.LAND
    ros2 run bisg_vehicle mission_square --ns /drone_1 --land offboard    # GPS-denied: land in OFFBOARD (offboard_controller.py)

PASS (exit 0) = every leg reached, the drone landed and disarmed, and with `--land auto` mavros/state went OFFBOARD -> AUTO.LAND.
Sim time is switched on automatically when /clock has a publisher (the sim), so the same command runs on the drone.
Start from the spawn point (a fresh sim): the square is relative to the start, and `single_iris` loads PX4 collision
prevention (CP_DIST 1.5 m), which stops a leg short of the room's walls -> a leg timeout, not a controller fault.
"""
import argparse
import os
import sys
import time

import rclpy
from rclpy.parameter import Parameter
from rclpy.utilities import remove_ros_args

from bisg_vehicle.offboard_controller import OffboardController


def log(msg):
    print(f"[mission_square] {msg}", flush=True)


def use_sim_time_if_clock(node, wait_s=3.0):
    end = time.time() + wait_s
    while time.time() < end:
        if node.count_publishers("/clock"):
            node.set_parameters([Parameter("use_sim_time", value=True)])
            return True
        time.sleep(0.2)
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ns", default=f"/drone_{os.environ.get('DRONE_ID', '1')}")
    ap.add_argument("--side", type=float, default=5.0, help="square side, m")
    ap.add_argument("--alt", type=float, default=2.0, help="flight height above the start point, m")
    ap.add_argument("--land", choices=["auto", "offboard"], default="auto")
    ap.add_argument("--patience", type=float, default=1.0, help="multiply every wall-clock wait (slow sim)")
    a = ap.parse_args(remove_ros_args(sys.argv if argv is None else argv)[1:])

    rclpy.init(args=argv)
    node = rclpy.create_node("mission_square")
    log(f"{a.ns}: sim time {'on (/clock)' if use_sim_time_if_clock(node) else 'off'}; "
        f"{a.side:g} m square at {a.alt:g} m, land {a.land}")
    c = OffboardController(node, a.ns, patience=a.patience, log=log)
    s = a.side
    steps = [("ready", c.wait_ready), ("takeoff", lambda: c.takeoff(a.alt))]
    steps += [(f"leg {i + 1}", lambda x=x, y=y: c.goto(x, y)) for i, (x, y) in enumerate([(s, 0), (s, s), (0, s), (0, 0)])]
    steps += [("land", lambda: c.land(a.land))]
    try:
        for name, step in steps:
            r = step()
            if not r:
                log(f"FAIL at {name}: {r.what} (mode {c.state.mode}, armed {c.state.armed})")
                if c.state.armed and name != "land":
                    c.land(a.land)
                return 1
        # PX4 returns to the last user-chosen mode (OFFBOARD) after the AUTO.LAND disarm: check the transition, not the end
        if a.land == "auto" and ("OFFBOARD", "AUTO.LAND") not in zip(c.modes, c.modes[1:]):
            log(f"FAIL: mode sequence {c.modes}, expected OFFBOARD -> AUTO.LAND")
            return 1
        log(f"PASS: landed and disarmed; modes {' -> '.join(c.modes)}")
        return 0
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    sys.exit(main())
