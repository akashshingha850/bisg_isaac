#!/usr/bin/env python3
"""
Hover-stability test: arm -> takeoff to ALT m -> settle -> record ATTITUDE for --hold SIM seconds -> land.
Reports the spread of roll/pitch and of the body rates in the hover. A healthy Iris hovers with attitude std < ~1 deg
and rate std < ~10 deg/s; a rate-loop limit cycle (e.g. physics too slow for PX4's 250 Hz tuning) shows up as
tens of deg/s on the rates and a few degrees on attitude.

Time is PX4's own clock (time_boot_ms = sim time), so it is valid at any real-time factor.

    docker exec -i bisg-sim /isaac-sim/python.sh - --instance 0 --alt 2 --hold 15 < tests/hover_stability.py
    (or: docker exec bisg-sim /isaac-sim/python.sh /workspace/tests/hover_stability.py ...)
Exit 0 = PASS.
"""
import argparse
import math
import statistics as stats
import sys
import time

from pymavlink import mavutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", type=int, default=0)
    ap.add_argument("--alt", type=float, default=2.0)
    ap.add_argument("--hold", type=float, default=15.0, help="sim seconds to record")
    ap.add_argument("--max-att-std", type=float, default=2.0, help="deg, roll and pitch")
    ap.add_argument("--max-rate-std", type=float, default=20.0, help="deg/s, roll/pitch/yaw rate")
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
        print("[hover] TIMEOUT: no autopilot heartbeat")
        return 1
    m.target_system, m.target_component = hb.get_srcSystem(), hb.get_srcComponent()
    st = {"armed": False, "alt": 0.0, "t": 0.0}
    att = []
    recording = [False]

    def pump(sec):
        end = time.time() + sec
        while time.time() < end:
            msg = m.recv_match(blocking=True, timeout=0.2)
            if msg is None:
                continue
            t = msg.get_type()
            if t == "HEARTBEAT" and msg.get_srcSystem() == m.target_system:
                st["armed"] = bool(msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            elif t == "LOCAL_POSITION_NED":
                st["alt"], st["t"] = -msg.z, msg.time_boot_ms / 1000.0
            elif t == "ATTITUDE" and recording[0]:
                att.append(msg)

    def cmd(c, *p):
        m.mav.command_long_send(m.target_system, m.target_component, c, 0, *([float(x) for x in p] + [0.0] * (7 - len(p))))

    def wait(cond, timeout, what):
        end = time.time() + timeout * a.patience
        while time.time() < end:
            pump(0.5)
            if cond():
                return True
        print(f"[hover] TIMEOUT waiting for {what}")
        return False

    pump(5)
    if not st["armed"]:
        m.mav.param_set_send(m.target_system, m.target_component, b"MIS_TAKEOFF_ALT", a.alt, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
        pump(0.5)
        cmd(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1)
        if not wait(lambda: st["armed"], 20, "armed"):
            return 2
        cmd(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, float("nan"), float("nan"), float("nan"), float("nan"))
    if not wait(lambda: st["alt"] >= 0.95 * a.alt, 120, f"altitude >= {0.95 * a.alt:.1f} m"):
        return 3
    pump(5)  # settle after the climb
    recording[0] = True
    t_start = st["t"]
    end_wall = time.time() + a.hold / 0.05 + 60
    while st["t"] - t_start < a.hold and time.time() < end_wall:
        pump(0.5)
    recording[0] = False
    cmd(mavutil.mavlink.MAV_CMD_NAV_LAND)
    if len(att) < 20:
        print(f"[hover] FAIL: only {len(att)} ATTITUDE messages")
        return 4
    span = (att[-1].time_boot_ms - att[0].time_boot_ms) / 1000.0
    print(f"[hover] {len(att)} ATTITUDE msgs over {span:.1f} sim s ({len(att) / span:.0f} Hz) at alt {st['alt']:.2f} m")
    ok = True
    for name, limit, scale in (("roll", a.max_att_std, 1), ("pitch", a.max_att_std, 1),
                               ("rollspeed", a.max_rate_std, 1), ("pitchspeed", a.max_rate_std, 1),
                               ("yawspeed", a.max_rate_std, 1)):
        v = [math.degrees(getattr(x, name)) * scale for x in att]
        sd = stats.pstdev(v)
        good = sd <= limit
        ok &= good
        unit = "deg" if "speed" not in name else "deg/s"
        print(f"[hover] {name:10s} std {sd:6.2f} {unit}  (max |x| {max(abs(x) for x in v):6.1f}, limit {limit})  {'ok' if good else 'UNSTABLE'}")
    print("[hover] " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 5


if __name__ == "__main__":
    sys.exit(main())
