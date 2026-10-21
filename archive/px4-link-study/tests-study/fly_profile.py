#!/usr/bin/env python3
"""
Scripted, repeatable flight for the VO/perception study (docs/study-vo-perception.md).

OFFBOARD over a raw MAVLink link (UDP 14540, so MAVROS must NOT be running): arm, climb to 2 m, then follow a reference
trajectory generated on PX4's own clock (time_boot_ms = sim time), so the path is the same at any real-time factor:

  takeoff  1 m/s to 2 m, hover 3 s
  square   4 m legs at 1 m/s, heading fixed (camera forward = east): forward, left, back, right
  spin     one 360 deg turn at 30 deg/s in place
  dash     6 m forward at 2 m/s, hover 2 s, 6 m back at 2 m/s   (fast motion)
  land     0.5 m/s velocity descent, disarm

Prints "MARK <phase> sim=<s> wall=<s>" lines the analysis uses to cut the data into phases.
    docker exec -i bisg-sim /isaac-sim/python.sh - [--profile full|short] < tests/study/fly_profile.py
"""
import argparse
import math
import sys
import time

from pymavlink import mavutil


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="full", choices=["full", "short"])
    ap.add_argument("--alt", type=float, default=2.0)
    ap.add_argument("--scale", type=float, default=1.0, help="scale the horizontal legs (small rooms: 0.4)")
    a = ap.parse_args()

    m = mavutil.mavlink_connection("udpin:0.0.0.0:14540", source_system=250)
    hb = None
    while hb is None:
        h = m.recv_match(type="HEARTBEAT", blocking=True, timeout=30)
        if h is not None and h.get_srcSystem() not in (0, 250) and h.type != mavutil.mavlink.MAV_TYPE_GCS:
            hb = h
    m.target_system, m.target_component = hb.get_srcSystem(), hb.get_srcComponent()
    st = {"t": 0.0, "pos": (0.0, 0.0, 0.0), "armed": False}

    def pump(sec=0.0):
        end = time.time() + sec
        while True:
            msg = m.recv_match(blocking=sec > 0, timeout=0.05)
            if msg is not None:
                t = msg.get_type()
                if t == "LOCAL_POSITION_NED":
                    st["t"], st["pos"] = msg.time_boot_ms / 1000.0, (msg.x, msg.y, msg.z)
                elif t == "HEARTBEAT" and msg.get_srcSystem() == m.target_system:
                    st["armed"] = bool(msg.base_mode & 128)
            if sec <= 0 or time.time() >= end:
                return

    def sp(pos, vel=(0, 0, 0), yaw=None, yaw_rate=None, vel_only=False):
        mask = 0b0000_1111_1111_1111 & ~0
        # type_mask: ignore accel (bits 6-8), force (9); use pos (0-2) / vel (3-5) / yaw (10) / yaw_rate (11)
        mask = 0b110000000000 | 0b111000000   # ignore yaw & yaw_rate by default, ignore accel
        if yaw is not None:
            mask &= ~0b010000000000
        if yaw_rate is not None:
            mask &= ~0b100000000000
        if vel_only:
            mask |= 0b111
        m.mav.set_position_target_local_ned_send(
            0, m.target_system, m.target_component, mavutil.mavlink.MAV_FRAME_LOCAL_NED, mask,
            pos[0], pos[1], pos[2], vel[0], vel[1], vel[2], 0, 0, 0, 0.0 if yaw is None else yaw,
            0.0 if yaw_rate is None else yaw_rate)

    def mark(name):
        print(f"MARK {name} sim={st['t']:.2f} wall={time.time():.3f}", flush=True)

    # --- reference trajectory, NED metres from the start point; east (+y) is the camera's forward direction ---
    H = math.radians(90.0)                       # heading east
    legs = []                                    # (name, duration_s, fn(tau)->(pos, vel, yaw, yaw_rate))
    z = -a.alt

    def line(p0, p1, speed, name, yaw=H):
        d = math.dist(p0, p1)
        T = d / speed
        v = tuple((b - c) / T for b, c in zip(p1, p0))
        legs.append((name, T, lambda tau, p0=p0, v=v, yaw=yaw: (tuple(c + vv * tau for c, vv in zip(p0, v)), v, yaw, None)))
        return p1

    def hover(p, T, name, yaw=H):
        legs.append((name, T, lambda tau, p=p, yaw=yaw: (p, (0, 0, 0), yaw, None)))

    p = (0.0, 0.0, 0.0)
    p = line(p, (0.0, 0.0, z), 1.0, "takeoff")
    hover(p, 3.0, "hover")
    p = line(p, (0.0, 4.0 * a.scale, z), 1.0, "sq_fwd")
    p = line(p, (4.0 * a.scale, 4.0 * a.scale, z), 1.0, "sq_left")
    p = line(p, (4.0 * a.scale, 0.0, z), 1.0, "sq_back")
    p = line(p, (0.0, 0.0, z), 1.0, "sq_right")
    if a.profile == "full":
        w = math.radians(30.0)
        legs.append(("spin", 2 * math.pi / w, lambda tau, p=p, w=w: (p, (0, 0, 0), H + w * tau, w)))
        hover(p, 1.0, "hover2")
        p = line(p, (0.0, 6.0 * a.scale, z), 2.0, "dash_out")
        hover(p, 2.0, "dash_hover")
        p = line(p, (0.0, 0.0, z), 2.0, "dash_back")
        hover(p, 2.0, "hover3")

    # --- start: stream setpoints, OFFBOARD, arm ---
    pump(3.0)
    for _ in range(40):
        sp((0, 0, 0), yaw=H)
        pump(0.05)
    m.mav.command_long_send(m.target_system, m.target_component, mavutil.mavlink.MAV_CMD_DO_SET_MODE, 0, 1, 6, 0, 0, 0, 0, 0)
    pump(0.5)
    m.mav.command_long_send(m.target_system, m.target_component, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 1, 0, 0, 0, 0, 0, 0)
    t_end = time.time() + 60
    while not st["armed"] and time.time() < t_end:
        sp((0, 0, 0), yaw=H)
        pump(0.1)
    if not st["armed"]:
        print("FAIL: not armed")
        return 2
    mark("armed")
    for name, T, fn in legs:
        t0 = st["t"]
        mark(name)
        wall_stop = time.time() + T / 0.03 + 60
        while st["t"] - t0 < T and time.time() < wall_stop:
            tau = min(st["t"] - t0, T)
            pos, vel, yaw, yr = fn(tau)
            sp(pos, vel, yaw=yaw)
            pump(0.05)
    mark("land")
    t_end = time.time() + 240
    while time.time() < t_end:
        sp((0, 0, 0), (0, 0, 0.5), yaw=H, vel_only=True)
        pump(0.05)
        if -st["pos"][2] < 0.12 or not st["armed"]:
            break
    m.mav.command_long_send(m.target_system, m.target_component, mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM, 0, 0, 21196, 0, 0, 0, 0, 0)
    pump(1.0)
    mark("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
