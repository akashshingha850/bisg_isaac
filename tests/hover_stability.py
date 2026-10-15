#!/usr/bin/env python3
"""
Hover-stability test: arm -> takeoff to ALT m -> settle -> record ATTITUDE for --hold SIM seconds -> land. OFFBOARD
(tests/mav_offboard.py): works with GPS and GPS-denied alike.
Reports the spread of roll/pitch and of the body rates in the hover. A healthy Iris hovers with attitude std < ~1 deg
and rate std < ~10 deg/s; a rate-loop limit cycle (e.g. physics too slow for PX4's 250 Hz tuning) shows up as
tens of deg/s on the rates and a few degrees on attitude.

Time is PX4's own clock (time_boot_ms = sim time), so it is valid at any real-time factor.

    docker exec bisg-sim /isaac-sim/python.sh /workspace/tests/hover_stability.py --instance 0 --alt 2 --hold 15
Exit 0 = PASS.
"""
import argparse
import math
import os
import statistics as stats
import sys
import time

from pymavlink import mavutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mav_offboard import Offboard  # noqa: E402


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
    st = {"t": 0.0}
    att = []
    recording = [False]

    def on_msg(msg):
        t = msg.get_type()
        if t == "LOCAL_POSITION_NED":
            st["t"] = msg.time_boot_ms / 1000.0
        elif t == "ATTITUDE" and recording[0]:
            att.append(msg)

    ob = Offboard(m, "hover", on_msg=on_msg, patience=a.patience)
    if not ob.takeoff(a.alt, reach=0.95):
        return 2
    ob.pump(5)  # settle after the climb
    recording[0] = True
    t_start = st["t"]
    end_wall = time.time() + a.hold / 0.05 + 60
    while st["t"] - t_start < a.hold and time.time() < end_wall:
        ob.pump(0.5)
    recording[0] = False
    st["alt"] = ob.rel_alt()
    if not ob.land():
        print("[hover] landing did not complete (results below are still valid)")
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
