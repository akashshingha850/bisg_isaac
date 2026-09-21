#!/usr/bin/env python3
"""
Push PX4 EKF2/GPS params over MAVLink (Phase 3 — GPS-denied flight on ZED Mini VIO).

Run once PX4 SITL is ready (same offboard link tests/smoke_takeoff.py uses, so it
coexists with MAVROS on the same port):
    python3 scripts/push_px4_params.py --instance 0

File format (deploy/px4_params/*.params): "NAME VALUE MAV_PARAM_TYPE" per line,
`#` comments allowed — NOT the 5-column QGC save format. See the file header for why.
EKF2_HGT_REF/EKF2_EV_CTRL/etc reboot_required:true params need a PX4 reboot (or
"param save" + power cycle on hardware) to take effect after being changed.
"""
import argparse
import struct
import sys
import time

from pymavlink import mavutil

MAV_PARAM_TYPE_REAL32 = mavutil.mavlink.MAV_PARAM_TYPE_REAL32


def encode(value: float, ptype: int) -> float:
    """PX4/MAVLink PARAM_SET always carries a float32 on the wire; non-REAL32 types
    are the raw int bit-pattern reinterpreted as float (matches pymavlink's mavparm)."""
    if ptype == MAV_PARAM_TYPE_REAL32:
        return float(value)
    packed = struct.pack(">i", int(value))
    return struct.unpack(">f", packed)[0]


def load_params(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            name, value, ptype = line.split()
            rows.append((name, float(value), int(ptype)))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", type=int, default=0)
    ap.add_argument("--file", default="deploy/px4_params/sim_default.params")
    ap.add_argument("--timeout", type=float, default=60.0)
    a = ap.parse_args()

    port = 14540 + a.instance
    print(f"[params] connecting udpin:0.0.0.0:{port} (PX4 instance {a.instance})", flush=True)
    m = mavutil.mavlink_connection(f"udpin:0.0.0.0:{port}", source_system=251)

    deadline = time.time() + a.timeout
    while True:
        hb = m.recv_match(type="HEARTBEAT", blocking=True, timeout=5)
        if hb is not None and hb.get_srcSystem() not in (0, 251) and hb.type != mavutil.mavlink.MAV_TYPE_GCS:
            m.target_system = hb.get_srcSystem()
            m.target_component = hb.get_srcComponent()
            break
        if time.time() > deadline:
            print(f"[params] TIMEOUT: no autopilot heartbeat on udp {port} "
                  f"(is the sim + PX4 up? ./bisg status)", flush=True)
            return 1
    print(f"[params] heartbeat from sysid {m.target_system} compid {m.target_component}", flush=True)

    rows = load_params(a.file)
    ok = True
    for name, value, ptype in rows:
        wire_value = encode(value, ptype)
        got_ack = False
        for _attempt in range(5):
            m.mav.param_set_send(m.target_system, m.target_component, name.encode(), wire_value, ptype)
            t0 = time.time()
            while time.time() - t0 < 1.0:
                ack = m.recv_match(type="PARAM_VALUE", blocking=False)
                if ack is not None and ack.param_id.rstrip("\x00") == name:
                    got_ack = True
                    print(f"[params] {name} <- {value:g}", flush=True)
                    break
                time.sleep(0.05)
            if got_ack:
                break
        if not got_ack:
            print(f"[params] FAILED to confirm {name}", flush=True)
            ok = False

    if ok:
        print("[params] all params confirmed — reboot_required params need PX4 to restart to take effect", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
