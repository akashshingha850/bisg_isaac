#!/usr/bin/env python3
"""
Position-hold test (GPS scenario, e.g. single_iris_nozed): arm -> takeoff to ALT m -> let PX4 hold (AUTO.LOITER)
for --hold SIM seconds -> land -> disarm. PASS if the position stays within --tol of where the hold started.

Time is PX4's own clock (LOCAL_POSITION_NED.time_boot_ms = sim time), so the test is valid at any real-time factor;
only the wall-clock waits scale with --patience. Needs a global position, so NOT for single_iris_vio (bugs.md B1).

    docker exec bisg-sim /isaac-sim/python.sh tests/hold_position.py --instance 0 --alt 2 --hold 20
Exit 0 = PASS.
"""
import argparse
import math
import sys
import time

from pymavlink import mavutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", type=int, default=0)
    ap.add_argument("--alt", type=float, default=2.0)
    ap.add_argument("--hold", type=float, default=20.0, help="sim seconds to hold")
    ap.add_argument("--tol", type=float, default=0.3, help="max horizontal / vertical drift, m")
    ap.add_argument("--patience", type=float, default=1.0, help="multiply wall-clock waits for a slow sim")
    a = ap.parse_args()

    m = mavutil.mavlink_connection(f"udpin:0.0.0.0:{14540 + a.instance}", source_system=250)
    hb = None
    t0 = time.time()
    while hb is None and time.time() - t0 < 120:
        h = m.recv_match(type="HEARTBEAT", blocking=True, timeout=5)
        if h is not None and h.get_srcSystem() not in (0, 250) and h.type != mavutil.mavlink.MAV_TYPE_GCS:
            hb = h
    if hb is None:
        print("[hold] TIMEOUT: no autopilot heartbeat")
        return 1
    m.target_system, m.target_component = hb.get_srcSystem(), hb.get_srcComponent()
    st = {"armed": False, "pos": None, "t": 0.0, "mode": None}

    def pump(sec):
        end = time.time() + sec
        while time.time() < end:
            msg = m.recv_match(blocking=True, timeout=0.2)
            if msg is None:
                continue
            t = msg.get_type()
            if t == "HEARTBEAT" and msg.get_srcSystem() == m.target_system:
                st["armed"] = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
                st["mode"] = msg.custom_mode
            elif t == "LOCAL_POSITION_NED":
                st["pos"] = (msg.x, msg.y, -msg.z)
                st["t"] = msg.time_boot_ms / 1000.0

    def cmd(c, *p):
        m.mav.command_long_send(m.target_system, m.target_component, c, 0, *([float(x) for x in p] + [0.0] * (7 - len(p))))

    def wait(cond, timeout, what):
        end = time.time() + timeout * a.patience
        while time.time() < end:
            pump(0.5)
            if cond():
                return True
        print(f"[hold] TIMEOUT waiting for {what}")
        return False

    pump(5)
    m.mav.param_set_send(m.target_system, m.target_component, b"MIS_TAKEOFF_ALT", a.alt, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
    pump(0.5)
    cmd(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1)
    if not wait(lambda: st["armed"], 20, "armed"):
        return 2
    cmd(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, float("nan"), float("nan"), float("nan"), float("nan"))
    if not wait(lambda: st["pos"] and st["pos"][2] >= 0.95 * a.alt, 90, f"altitude >= {0.95 * a.alt:.1f} m"):
        return 3
    pump(5 * a.patience if a.patience < 2 else 5)  # settle after the climb
    p0, t_start = st["pos"], st["t"]
    print(f"[hold] hold starts at x={p0[0]:.2f} y={p0[1]:.2f} z={p0[2]:.2f} (sim t={t_start:.1f}s, custom_mode={st['mode']})")
    worst_h = worst_v = 0.0
    end_wall = time.time() + (a.hold / 0.05 + 60)  # hard stop, even at rtf 0.05
    while st["t"] - t_start < a.hold and time.time() < end_wall:
        pump(0.5)
        p = st["pos"]
        worst_h = max(worst_h, math.hypot(p[0] - p0[0], p[1] - p0[1]))
        worst_v = max(worst_v, abs(p[2] - p0[2]))
    held = st["t"] - t_start
    print(f"[hold] held {held:.1f} sim s: max horizontal drift {worst_h:.3f} m, max vertical drift {worst_v:.3f} m (tol {a.tol} m)")
    cmd(mavutil.mavlink.MAV_CMD_NAV_LAND)
    landed = wait(lambda: not st["armed"], 90, "disarm after landing")
    ok = landed and held >= a.hold and worst_h <= a.tol and worst_v <= a.tol
    print("[hold] " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 4


if __name__ == "__main__":
    sys.exit(main())
