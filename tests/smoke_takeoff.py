#!/usr/bin/env python3
"""
Phase 1 smoke test: arm -> takeoff to ALT m -> land -> disarm, over MAVLink to PX4 SITL.

Run on the host (pymavlink) or inside the sim container while the sim is up:
    python3 tests/smoke_takeoff.py --instance 0 --alt 2.0 --timeout 300

Listens on the PX4 offboard link (remote port 14540+i, PX4 side 14580+i), so it
does not conflict with QGC on 14550. Exit code 0 = success.
"""
import argparse
import sys
import time

from pymavlink import mavutil

MAV_MODE_FLAG_SAFETY_ARMED = mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED


def wait_until(cond, timeout, what, poll=0.2):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if cond():
            return True
        time.sleep(poll)
    print(f"[smoke] TIMEOUT waiting for {what}", flush=True)
    return False


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

    deadline = time.time() + a.timeout
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

    state = {"armed": False, "rel_alt": 0.0, "pos_ok": False}

    def pump(seconds):
        t_end = time.time() + seconds
        while time.time() < t_end:
            msg = m.recv_match(blocking=True, timeout=0.2)
            if msg is None:
                continue
            t = msg.get_type()
            if t == "HEARTBEAT" and msg.get_srcSystem() == m.target_system:
                state["armed"] = bool(msg.base_mode & MAV_MODE_FLAG_SAFETY_ARMED)
            elif t == "LOCAL_POSITION_NED":
                # Source-agnostic position gate (GPS, VIO, optical flow, ...) — GLOBAL_POSITION_INT
                # needs a geodetic fix and never arrives under a GPS-denied EKF2 config (EKF2_GPS_CTRL=0).
                state["rel_alt"] = -msg.z  # NED down -> altitude up
                state["pos_ok"] = True
            elif t == "STATUSTEXT":
                print(f"[px4] {msg.text}", flush=True)
            elif t == "COMMAND_ACK":
                print(f"[smoke] ack cmd={msg.command} result={msg.result}", flush=True)

    def send_cmd(cmd, *params):
        m.mav.command_long_send(m.target_system, m.target_component, cmd, 0, *([float(p) for p in params] + [0.0] * (7 - len(params))))

    # 1. local position estimate available (any EKF2 aiding source: GPS, VIO, ...)
    if not wait_until(lambda: (pump(0.5), state["pos_ok"])[1], max(1, deadline - time.time()), "LOCAL_POSITION_NED"):
        return 2
    pump(3.0)  # let EKF settle after boot

    # 2. takeoff altitude param, then arm + takeoff
    m.mav.param_set_send(m.target_system, m.target_component, b"MIS_TAKEOFF_ALT", a.alt, mavutil.mavlink.MAV_PARAM_TYPE_REAL32)
    pump(0.5)
    send_cmd(mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 1)
    if not wait_until(lambda: (pump(0.5), state["armed"])[1], 20 * a.patience, "armed"):
        return 3
    print("[smoke] armed", flush=True)
    send_cmd(mavutil.mavlink.MAV_CMD_NAV_TAKEOFF, 0, 0, 0, float("nan"), float("nan"), float("nan"), float("nan"))
    target = 0.75 * a.alt
    if not wait_until(lambda: (pump(0.5), state["rel_alt"] >= target)[1], 60 * a.patience, f"rel_alt >= {target:.1f} m"):
        print(f"[smoke] rel_alt={state['rel_alt']:.2f}", flush=True)
        return 4
    print(f"[smoke] airborne rel_alt={state['rel_alt']:.2f} m", flush=True)
    pump(3.0)

    # 3. land + wait for disarm
    send_cmd(mavutil.mavlink.MAV_CMD_NAV_LAND)
    if not wait_until(lambda: (pump(0.5), not state["armed"])[1], 90 * a.patience, "disarm after landing"):
        return 5
    print("[smoke] landed and disarmed — PASS", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
