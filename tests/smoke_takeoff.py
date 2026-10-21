#!/usr/bin/env python3
"""
Phase 1 smoke test: arm -> takeoff to ALT m -> land -> disarm, over MAVLink to PX4 SITL. OFFBOARD (tests/mav_offboard.py), so it
works with GPS and GPS-denied alike (AUTO.TAKEOFF needs a global position; the sim default is GPS-denied since 2026-10-15).

Run on the host (pymavlink) or inside the sim container while the sim is up:
    python3 tests/smoke_takeoff.py --instance 0 --alt 2.0 --timeout 300

Listens on the PX4 offboard link (remote port 14540+i, PX4 side 14580+i), so it
does not conflict with QGC on 14550. Exit code 0 = success.
"""
import argparse
import os
import sys
import time

from pymavlink import mavutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mav_offboard import Offboard  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", type=int, default=0)
    ap.add_argument("--alt", type=float, default=2.0)
    ap.add_argument("--timeout", type=float, default=300.0, help="overall budget in seconds (cold sim boot included)")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--patience", type=float, default=1.0,
                    help="multiply the arm/climb/land waits (20/60/90 s wall) for a slow sim, e.g. 4 for 8 drones at rtf 0.09")
    a = ap.parse_args()

    port = 14540 + a.instance
    print(f"[smoke] connecting udpin:0.0.0.0:{port} (PX4 instance {a.instance})", flush=True)
    m = mavutil.mavlink_connection(f"udpin:0.0.0.0:{port}", source_system=250)

    # Wait for a real autopilot heartbeat. `wait_heartbeat()` alone can latch onto a stray
    # packet and report sysid 0, which makes a "no PX4 running" failure look like a connection.
    t0 = time.time()
    while True:
        hb = m.recv_match(type="HEARTBEAT", blocking=True, timeout=5)
        if hb is not None and hb.get_srcSystem() not in (0, 250) and hb.type != mavutil.mavlink.MAV_TYPE_GCS:
            m.target_system = hb.get_srcSystem()
            m.target_component = hb.get_srcComponent()
            break
        if time.time() - t0 > a.timeout:
            print(f"[smoke] TIMEOUT: no autopilot heartbeat on udp {port} after {a.timeout:.0f}s "
                  f"(is the sim up and PX4 started? ./bisg status)", flush=True)
            return 1
    print(f"[smoke] heartbeat from sysid {m.target_system} compid {m.target_component}", flush=True)

    ob = Offboard(m, "smoke", patience=a.patience)
    if not ob.takeoff(a.alt, reach=0.75):
        return 3
    ob.say(f"airborne rel_alt={ob.rel_alt():.2f} m")
    ob.pump(3.0)
    if not ob.land():
        return 5
    ob.say("landed and disarmed — PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
