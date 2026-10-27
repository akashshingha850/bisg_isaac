#!/usr/bin/env python3
"""
Long-flight drift test (docs/vio-drift.md): laps of a large rectangle in the Warehouse, so the VIO drift that the ~26 m
`vio_bench.py` profile never shows has time to grow, and so the drone revisits the same places (what loop closure needs).

Profile (relative to the start pose on the floor, facing +x; map = EKF2 local frame, ENU):
  takeoff to --alt, 10 s hover -> --laps x (a 360 deg yaw sweep at the first corner, then the rectangle --rect at --speed with
  the camera facing the direction of travel, a stop + 90 deg turn at each corner) -> 10 s hover -> OFFBOARD descent, land.
  The default rectangle (x -4..8, y -8..12 m from the start, 64 m per lap) keeps >= 2 m from the emptied Warehouse's walls.

Recorded at 10 Hz sim time (`samples.csv`): ground truth (Pegasus state/pose, test only), EKF2 (mavros local_position/pose), the
ZED's `odom` (frame-to-frame chain: what the bridge sends today) and the ZED's `pose` (its world frame, which takes the loop
closures when area memory is on), plus the bridge's output (mavros odometry/out) when present. Every source is compared as a
displacement from its pre-flight value with ground truth moved to the camera (lever arm EKF2_EV_POS, raptor.params) for the
ZED sources. `summary.json`: horizontal / yaw error per source at every lap end, max, final, distance and sim time.

    ./bisg restart                        # fresh sim: the ZED connects once per run (B18)
    docker exec bisg-ros bash -lc 'source /opt/ros/jazzy/setup.bash; python3 /workspace/tests/drift_flight.py --out /tmp/drift'
Exit 0 = flown and landed (accuracy is in summary.json). Aborts (force disarm) when EKF2 is off truth by > 3 * --tol.
"""
import argparse
import csv
import json
import math
import os
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from mavros_msgs.msg import ExtendedState
from mavros_msgs.srv import CommandBool
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from range_flow_bench import Bench  # noqa: E402
from vio_flight import Abort  # noqa: E402

LEVER = (0.1205, 0.0, 0.0397)          # zed_camera_link in the body, FLU (raptor.params EKF2_EV_POS_*, FRD there)
SOURCES = ("ekf2", "zed_odom", "zed_pose", "ev_out")


def yaw_of(q):
    x, y, z, w = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def rot(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    # v' = q v q*, expanded
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + y * tz - z * ty, vy + w * ty + z * tx - x * tz, vz + w * tz + x * ty - y * tx)


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


class Drift(Bench):
    def __init__(self, drone, tol, out):
        super().__init__(drone, tol, out)
        ns = f"/drone_{drone}"
        self.src = {k: None for k in SOURCES}            # latest (p, q) per source
        self.truth_q = None
        self.zed_status = None                             # (odometry_status, spatial_memory_status) when zed_msgs exists
        n = self.node
        n.create_subscription(PoseStamped, f"{ns}/mavros/local_position/pose", lambda m: self._pose("ekf2", m.pose), qos_profile_sensor_data)
        n.create_subscription(Odometry, f"{ns}/zed/zed_node/odom", lambda m: self._pose("zed_odom", m.pose.pose), qos_profile_sensor_data)
        n.create_subscription(PoseStamped, f"{ns}/zed/zed_node/pose", lambda m: self._pose("zed_pose", m.pose), qos_profile_sensor_data)
        n.create_subscription(Odometry, f"{ns}/mavros/odometry/out", lambda m: self._pose("ev_out", m.pose.pose), 10)
        n.create_subscription(PoseStamped, f"{ns}/state/pose", self._on_truth_q, qos_profile_sensor_data)
        try:
            from zed_msgs.msg import PosTrackStatus
            n.create_subscription(PosTrackStatus, f"{ns}/zed/zed_node/pose/status",
                                  lambda m: setattr(self, "zed_status", (m.odometry_status, m.spatial_memory_status)),
                                  qos_profile_sensor_data)
        except ImportError:
            pass
        self.bridge = None                                 # the zed-bridge odometry status (map correction / compass), 1 Hz
        n.create_subscription(String, f"{ns}/zed_stack/status", self._on_status, 1)
        self._bf = open(os.path.join(out, "bridge.jsonl"), "w")
        self.lap = 0
        self.dist = 0.0
        self._last_truth = None
        self.ref = None                                    # pre-flight (truth p, truth q, {src: (p, q)})
        self.rows = []
        self._sf = open(os.path.join(out, "samples.csv"), "w", newline="")
        self.w = csv.writer(self._sf)
        hdr = ["t", "phase", "lap", "dist", "tx", "ty", "tz", "tyaw"]
        for k in SOURCES:
            hdr += [f"{k}_x", f"{k}_y", f"{k}_z", f"{k}_yaw", f"{k}_eh", f"{k}_eyaw"]
        self.w.writerow(hdr + ["odom_status", "sm_status"])
        n.create_timer(0.1, self._record)

    def _pose(self, k, pose):
        p, o = pose.position, pose.orientation
        self.src[k] = ((p.x, p.y, p.z), (o.x, o.y, o.z, o.w))

    def _on_status(self, m):
        try:
            self.bridge = json.loads(m.data)["components"].get("odometry")
        except (ValueError, KeyError):
            return
        self._bf.write(json.dumps({"t": round(self.now(), 2), "phase": self.phase, **(self.bridge or {})}) + "\n")

    def _on_truth_q(self, m):
        o = m.pose.orientation
        self.truth_q = (o.x, o.y, o.z, o.w)

    def snapshot_ref(self):
        self.ref = (self.truth, self.truth_q, dict(self.src))

    def errors(self):
        """{src: (horizontal error m, yaw error deg)} of each source's displacement since the reference vs ground truth's."""
        if not self.ref or self.truth is None or self.truth_q is None:
            return {}
        t0p, t0q, s0 = self.ref
        out = {}
        for k in SOURCES:
            cur, ref = self.src.get(k), s0.get(k)
            if cur is None or ref is None:
                continue
            lever = LEVER if k.startswith("zed") or k == "ev_out" else (0.0, 0.0, 0.0)
            tc = [a + b for a, b in zip(self.truth, rot(self.truth_q, lever))]
            tr = [a + b for a, b in zip(t0p, rot(t0q, lever))]
            dt = [tc[i] - tr[i] for i in range(3)]
            ds = [cur[0][i] - ref[0][i] for i in range(3)]
            # the source's frame may start rotated against the world (its own yaw origin): rotate its displacement by that offset
            off = yaw_of(t0q) - yaw_of(ref[1])
            c, s = math.cos(off), math.sin(off)
            ds = [c * ds[0] - s * ds[1], s * ds[0] + c * ds[1], ds[2]]
            eh = math.hypot(ds[0] - dt[0], ds[1] - dt[1])
            eyaw = math.degrees(wrap((yaw_of(cur[1]) - yaw_of(ref[1])) - (yaw_of(self.truth_q) - yaw_of(t0q))))
            out[k] = (eh, eyaw, cur)
        return out

    def _record(self):
        if self.truth is None or self.truth_q is None:
            return
        if self._last_truth is not None and self.state.armed:
            self.dist += math.dist(self.truth[:2], self._last_truth[:2])
        self._last_truth = self.truth
        err = self.errors()
        row = [f"{self.now():.2f}", self.phase, self.lap, f"{self.dist:.2f}", *(f"{v:.3f}" for v in self.truth),
               f"{math.degrees(yaw_of(self.truth_q)):.2f}"]
        for k in SOURCES:
            if k in err:
                eh, eyaw, (p, q) = err[k]
                row += [f"{p[0]:.3f}", f"{p[1]:.3f}", f"{p[2]:.3f}", f"{math.degrees(yaw_of(q)):.2f}", f"{eh:.3f}", f"{eyaw:.2f}"]
            else:
                row += [""] * 6
        row += list(self.zed_status) if self.zed_status else ["", ""]
        self.w.writerow(row)
        if self.ref and self.state.armed:
            self.rows.append((self.now(), self.phase, self.lap, self.dist, {k: v[:2] for k, v in err.items()}))

    def carrot(self, x, y, alt, yaw, speed, phase):
        """Move the position setpoint from where it is to (x, y) (start-relative) at `speed`, heading `yaw`; wait until there."""
        self.phase = phase
        self.set_yaw(yaw)
        ax, ay = self.sp.pose.position.x, self.sp.pose.position.y
        bx, by = self.est0[0] + x, self.est0[1] + y
        L = math.hypot(bx - ax, by - ay)
        t0 = self.now()
        while True:
            s = min(1.0, speed * (self.now() - t0) / L) if L > 1e-6 else 1.0
            self.sp.pose.position.x, self.sp.pose.position.y = ax + (bx - ax) * s, ay + (by - ay) * s
            self.sp.pose.position.z = self.est0[2] + alt
            self.spin()
            if s >= 1.0 and math.hypot(self.est[0] - bx, self.est[1] - by) < 0.3:
                return
            if self.now() - t0 > L / speed + 30:
                raise Abort(f"{phase}: setpoint not reached")

    def turn_to(self, yaw, settle=1.0):
        turn = abs(wrap(yaw - self.yaw))
        self.set_yaw(yaw)
        self.sim_sleep(turn / math.radians(50) + settle)         # MC_YAWRATE_MAX 60

    def close(self):
        super().close()
        self._sf.close()
        self._bf.close()


def summarize(f, a, wall_s, landed):
    rows = f.rows
    out = {"args": vars(a), "landed": landed, "wall_s": round(wall_s), "distance_m": round(f.dist, 1),
           "sim_s": round(rows[-1][0] - rows[0][0], 1) if rows else 0, "laps": {}, "sources": {}}
    for k in SOURCES:
        eh = [r[4][k][0] for r in rows if k in r[4]]
        ey = [r[4][k][1] for r in rows if k in r[4]]
        if not eh:
            continue
        jumps = sum(1 for (r0, r1) in zip(rows, rows[1:]) if k in r0[4] and k in r1[4] and abs(r1[4][k][0] - r0[4][k][0]) > 0.15)
        out["sources"][k] = {"h_max_m": round(max(eh), 3), "h_final_m": round(eh[-1], 3),
                             "h_rms_m": round(math.sqrt(sum(e * e for e in eh) / len(eh)), 3),
                             "yaw_max_deg": round(max(abs(e) for e in ey), 2), "yaw_final_deg": round(ey[-1], 2),
                             "steps_over_15cm": jumps}
    for lap in sorted({r[2] for r in rows}):
        last = [r for r in rows if r[2] == lap][-1]
        out["laps"][str(lap)] = {"t": round(last[0] - rows[0][0], 1), "dist_m": round(last[3], 1),
                                 **{k: {"h_m": round(v[0], 3), "yaw_deg": round(v[1], 2)} for k, v in last[4].items()}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--out", default="/tmp/drift")
    ap.add_argument("--tol", type=float, default=1.0, help="abort when |EKF2 - truth| > 3*tol on an axis")
    ap.add_argument("--alt", type=float, default=2.0)
    ap.add_argument("--laps", type=int, default=5)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--rect", default="-4,-8,8,12", help="x0,y0,x1,y1 from the start, m")
    ap.add_argument("--no-spin", action="store_true", help="skip the 360 deg sweep at the start of each lap")
    a = ap.parse_args()
    x0, y0, x1, y1 = (float(v) for v in a.rect.split(","))

    rclpy.init()
    f = Drift(a.drone, a.tol, a.out)
    t_start = time.time()
    landed = False
    try:
        if not f.wait_for(lambda: f.truth and f.truth_q and f.est and f.state.connected and f.src["zed_odom"], 60,
                          "ground truth + local_position + ZED odom + MAVROS connected"):
            return 2
        f.phase = "ground"
        f.sim_sleep(3.0)
        f.truth0, f.est0 = f.truth, f.est
        f.snapshot_ref()
        print(f"[drift] start est={[round(v, 2) for v in f.est0]} truth={[round(v, 2) for v in f.truth0]} "
              f"zed_pose={'yes' if f.src['zed_pose'] else 'no'} ev_out={'yes' if f.src['ev_out'] else 'no'} "
              f"zed_status={'yes' if f.zed_status else 'n/a'}", flush=True)
        f.sp.pose.position.x, f.sp.pose.position.y, f.sp.pose.position.z = f.est0[0], f.est0[1], f.est0[2] + a.alt
        f.set_yaw(0.0)
        f.streaming = True
        f.spin_for(2.0)
        if not f.set_mode("OFFBOARD"):
            return 3
        r = f.call(f.cli_arm, CommandBool.Request(value=True))
        if not (r and r.success) or not f.wait_for(lambda: f.state.armed, 10, "armed"):
            return 3
        if not f.goto(0, 0, a.alt, 10, "takeoff"):
            return 4
        # start -> first corner (x0, y0), then the rectangle counter-clockwise: (x1,y0) (x1,y1) (x0,y1) (x0,y0)
        corners = [(x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        f.carrot(x0, 0, a.alt, math.pi, a.speed, "to-start")
        f.turn_to(-math.pi / 2)
        f.carrot(x0, y0, a.alt, -math.pi / 2, a.speed, "to-start")
        prev = (x0, y0)
        for lap in range(1, a.laps + 1):
            f.lap = lap
            if not a.no_spin:
                f.phase = f"lap{lap}-spin"
                for k in range(1, 5):
                    f.turn_to(wrap(-math.pi / 2 + k * math.pi / 2), settle=0.3)
            for i, (cx, cy) in enumerate(corners):
                yaw = math.atan2(cy - prev[1], cx - prev[0])
                f.turn_to(yaw)
                f.carrot(cx, cy, a.alt, yaw, a.speed, f"lap{lap}-leg{i + 1}")
                prev = (cx, cy)
            e = f.errors()
            print(f"[drift] lap {lap} done t={f.now() - f.rows[0][0]:.0f} s dist={f.dist:.0f} m  " +
                  "  ".join(f"{k} {v[0]:.2f} m {v[1]:+.1f} deg" for k, v in e.items()), flush=True)
        f.lap = a.laps + 1
        f.turn_to(math.pi / 2)
        f.carrot(x0, 0, a.alt, math.pi / 2, a.speed, "home")
        f.turn_to(0.0)
        f.carrot(0, 0, a.alt, 0.0, a.speed, "home")
        f.phase = "hover-end"
        f.sim_sleep(10.0)
        f.phase = "land"
        f.descend = 0.5
        if not f.wait_for(lambda: f.ext.landed_state == ExtendedState.LANDED_STATE_ON_GROUND, 90, "on ground"):
            return 5
        f.call(f.cli_arm, CommandBool.Request(value=False))
        f.streaming = False
        if not f.wait_for(lambda: not f.state.armed, 60, "disarmed"):
            return 5
        landed = True
        return 0
    except Abort as exc:
        f.kill(str(exc))
        return 10
    finally:
        s = summarize(f, a, time.time() - t_start, landed)
        with open(os.path.join(a.out, "summary.json"), "w") as fh:
            json.dump(s, fh, indent=1)
        print("[drift] " + json.dumps(s["sources"]), flush=True)
        f.close()
        f.node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    sys.exit(main())
