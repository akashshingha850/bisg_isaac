#!/usr/bin/env python3
"""
Collision-prevention test: ZED depth -> obstacle_distance node -> MAVROS -> PX4 (CP_DIST) -> the drone stops short of a wall.

Takes off to ALT m through MAVROS in OFFBOARD (works GPS-denied, the sim default since 2026-10-15; AUTO.TAKEOFF needs a global
position), switches to Position mode (POSCTL) and holds the forward stick (MANUAL_CONTROL
through mavros manual_control/send) for up to --push SIM seconds. Without collision prevention the drone would fly into
the wall; with CP_DIST = D it must stop about D metres short. Measures the nearest forward range from the scan the
obstacle_distance node publishes. PASS if the drone moved at least --min-move m, the stick was still held when it stopped
and the closest forward range stayed above CP_DIST - --slack. Lands in POSCTL with the throttle stick down (AUTO.LAND plans in
lat/lon and flew a GPS-denied drone into a wall, tests/vio_flight.py); PX4 disarms itself after landing (COM_DISARM_LAND).

Needs: sim up, `./bisg mavros up`, `./bisg zed up` (services.px4_bridge.obstacle_distance on), PX4 CP_DIST > 0 (scenario px4.params),
MAVROS' `manual_control` plugin (mavros_lean.yaml), and NO other stick source: a QGroundControl with its (virtual) joystick on
streams MANUAL_CONTROL on the GCS link first and PX4 keeps that source (manual_control_setpoint data_source 2), so our sticks are ignored.
    docker exec bisg-ros bash -lc 'source /opt/ros/jazzy/setup.bash; python3 /workspace/tests/collision_prevention.py --alt 1.5 --cp-dist 1.5'
Exit 0 = PASS.
"""
import argparse
import math
import sys
import time

import rclpy
from mavros_msgs.msg import ManualControl, State
from mavros_msgs.srv import CommandBool, SetMode
from geometry_msgs.msg import PoseStamped
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--alt", type=float, default=2.5, help="climb to this height above the start, m")
    ap.add_argument("--cp-dist", type=float, default=1.5, help="PX4 CP_DIST, m")
    ap.add_argument("--slack", type=float, default=0.5, help="allowed overshoot inside CP_DIST, m")
    ap.add_argument("--stick", type=float, default=0.4, help="forward stick, 0..1")
    ap.add_argument("--push", type=float, default=60.0, help="max sim seconds to hold the stick")
    ap.add_argument("--min-move", type=float, default=0.5, help="the drone must have moved at least this far, m")
    ap.add_argument("--patience", type=float, default=1.0, help="multiply wall-clock waits for a slow sim")
    a = ap.parse_args()

    ns = f"/drone_{a.drone}/mavros"
    rclpy.init()
    n = rclpy.create_node("cp_test", namespace="")
    st = {"armed": False, "mode": "", "pos": None, "q": None, "t": 0.0, "fwd": math.inf, "sp": None}

    n.create_subscription(State, f"{ns}/state", lambda m: st.update(armed=m.armed, mode=m.mode), 10)

    def on_pose(m):
        st["pos"] = (m.pose.position.x, m.pose.position.y, m.pose.position.z)
        st["q"] = m.pose.orientation
        st["t"] = m.header.stamp.sec + m.header.stamp.nanosec * 1e-9
    n.create_subscription(PoseStamped, f"{ns}/local_position/pose", on_pose, qos_profile_sensor_data)

    def on_scan(m):   # bins are FRD clockwise from START angle; forward +-20 deg
        near = math.inf
        for i, r in enumerate(m.ranges):
            ang = math.degrees(m.angle_min + i * m.angle_increment)
            if abs(ang) <= 20.0 and math.isfinite(r) and r <= m.range_max:
                near = min(near, r)
        st["fwd"] = near
    n.create_subscription(LaserScan, f"{ns}/obstacle/send", on_scan, 10)
    pub = n.create_publisher(ManualControl, f"{ns}/manual_control/send", 10)
    sp_pub = n.create_publisher(PoseStamped, f"{ns}/setpoint_position/local", 10)

    def stream_sp():   # OFFBOARD needs a steady setpoint stream (> 2 Hz); 20 Hz wall while st["sp"] is set
        if st["sp"] is None:
            return
        msg = PoseStamped()
        msg.header.stamp = n.get_clock().now().to_msg()
        msg.header.frame_id = "map"
        msg.pose.position.x, msg.pose.position.y, msg.pose.position.z = st["sp"]
        msg.pose.orientation = st["q0"]
        sp_pub.publish(msg)
    n.create_timer(0.05, stream_sp)

    def stick(z, x=0.0):
        m = ManualControl()
        m.header.stamp = n.get_clock().now().to_msg()
        m.x, m.y, m.z, m.r = x, 0.0, z, 0.0
        pub.publish(m)

    def spin(sec):
        end = time.time() + sec
        while time.time() < end:
            rclpy.spin_once(n, timeout_sec=0.05)

    def call(srv_type, name, req):
        cli = n.create_client(srv_type, f"{ns}/{name}")
        if not cli.wait_for_service(timeout_sec=20.0):
            print(f"[cp] TIMEOUT: service {name}")
            return None
        fut = cli.call_async(req)
        rclpy.spin_until_future_complete(n, fut, timeout_sec=20.0)
        return fut.result()

    def wait(cond, timeout, what):
        end = time.time() + timeout * a.patience
        while time.time() < end:
            spin(0.3)
            if cond():
                return True
        print(f"[cp] TIMEOUT waiting for {what}")
        return False

    spin(3)
    if not wait(lambda: st["pos"] is not None, 30, "pose"):
        return 1
    x0, y0, z0 = st["pos"]
    st["q0"] = st["q"]                                            # hold the start heading
    if not st["armed"]:
        st["sp"] = (x0, y0, z0)                                   # stream before switching: PX4 refuses OFFBOARD without one
        spin(1.0)
        r = call(SetMode, "set_mode", SetMode.Request(custom_mode="OFFBOARD"))
        if r is None or not r.mode_sent:
            print("[cp] FAIL: OFFBOARD refused")
            return 2
        r = call(CommandBool, "cmd/arming", CommandBool.Request(value=True))
        if r is None or not r.success:
            print("[cp] FAIL: arming refused")
            return 2
        st["sp"] = (x0, y0, z0 + a.alt)
    if not wait(lambda: st["pos"][2] - z0 >= 0.9 * a.alt, 90, f"altitude >= {0.9 * a.alt:.1f} m above the start"):
        return 3
    spin(4)
    for _ in range(10):                                           # centre the sticks before handing over to POSCTL
        stick(500.0)
        spin(0.05)
    r = call(SetMode, "set_mode", SetMode.Request(custom_mode="POSCTL"))
    if r is None or not r.mode_sent:
        print("[cp] FAIL: POSCTL refused")
        return 4
    st["sp"] = None
    p0, t0 = st["pos"], st["t"]
    print(f"[cp] POSCTL, start x={p0[0]:.2f} y={p0[1]:.2f} z={p0[2]:.2f}, forward range {st['fwd']:.2f} m, "
          f"holding stick {a.stick} up to {a.push:.0f} sim s", flush=True)
    nearest, moved, end_wall = math.inf, 0.0, time.time() + a.push / 0.05 + 30
    last_move_t, last_pos = st["t"], st["pos"]
    while st["t"] - t0 < a.push and time.time() < end_wall:
        stick(500.0, float(a.stick) * 1000.0)   # mavros does NOT scale: -1000..1000, z 0..1000 (500 = hold altitude)
        spin(0.02)       # 50 Hz: faster than a GCS virtual joystick (~25 Hz) so PX4's manual-control selector keeps us
        nearest = min(nearest, st["fwd"])
        moved = math.dist(st["pos"][:2], p0[:2])
        if math.dist(st["pos"][:2], last_pos[:2]) > 0.05:
            last_pos, last_move_t = st["pos"], st["t"]
        if st["t"] - last_move_t > 6.0 and moved > a.min_move:      # held still for 6 sim s with the stick forward
            break
    stopped_for = st["t"] - last_move_t
    held = st["t"] - t0
    print(f"[cp] moved {moved:.2f} m in {held:.1f} sim s, still for the last {stopped_for:.1f} s, "
          f"closest forward range {nearest:.2f} m (CP_DIST {a.cp_dist})", flush=True)
    end_wall = time.time() + 120 * a.patience                    # land: throttle stick down in POSCTL until PX4 disarms itself
    while st["armed"] and time.time() < end_wall:
        stick(150.0)
        spin(0.05)
    if st["armed"]:
        print("[cp] landing did not complete: disarm by hand (./bisg mavros state)")
    ok = moved >= a.min_move and stopped_for > 3.0 and nearest >= a.cp_dist - a.slack
    print("[cp] " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 5


if __name__ == "__main__":
    sys.exit(main())
