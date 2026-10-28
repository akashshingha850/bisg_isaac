#!/usr/bin/env python3
"""
Compass comparison: the flight controller's magnetometer vs the ZED heading (VIO + Manhattan compass, as EKF2 flies it),
against ground truth in the sim. Passive: it only listens; fly, carry or turn the drone while it records.

Headings compared (all ENU yaw, each with its own constant offset, which is the calibration):
  ekf    mavros/local_position/pose     what the drone flies with (raptor: ZED odometry + the bridge's wall compass)
  zed    zed/zed_node/odom              the ZED's own VIO, before the bridge corrects it
  mag    mavros/imu/mag                 tilt-compensated with the attitude's roll / pitch: the heading of magnetic north
  truth  state/pose                     sim only (Pegasus ground truth; test-only, plan.md §8)
Reference = truth when it is there, else ekf. Per source: the offset (circular median of source - reference) and the residual
after it (median / p90 / max |deg|). Magnetometer health without ground truth: the field strength and inclination must stay put
as the drone turns and moves; a hard-iron offset or a steel structure changes both.

The sim's magnetometer is Pegasus' ideal Earth-field model (WMM + noise, no motors, no steel): it is healthy by construction, so a
sim run checks this tool, not the Pixracer. The verdict that matters comes from the real drone, after the QGC compass calibration.
PX4 v1.17 EKF2 fuses magnetometer heading only while EV yaw is off (mag_control.cpp: `!ev_yaw`), so "both" means choosing one in
EKF2 or blending them before EKF2.

    docker exec bisg-ros python3 /workspace/tests/compass_compare.py --duration 120
Exit 0 = magnetometer healthy (residual p90 <= --max-p90 and field strength / inclination steady).
"""
import argparse
import math
import sys
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Imu, MagneticField


def yaw_of(q):
    x, y, z, w = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def tilt_comp_heading(q, m):
    """Yaw (ENU) of a body whose roll / pitch is in q, from the field m (base_link FLU): the heading with magnetic north as 0
    up to a constant (declination + frame), which the offset absorbs."""
    x, y, z, w = q
    R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    c, s = math.cos(yaw_of(q)), math.sin(yaw_of(q))
    lx, ly, lz = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]]) @ R @ np.asarray(m)   # the field in the level, yaw-free body frame
    return -math.atan2(ly, lx), math.degrees(math.atan2(-lz, math.hypot(lx, ly)))   # (heading, inclination: + = field points down)


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def circ_median(a):
    """Median of angles (rad): the plain median around the circular mean, so a wrap at +-180 does not split it."""
    c = math.atan2(np.mean(np.sin(a)), np.mean(np.cos(a)))
    return wrap(c + float(np.median(wrap(np.asarray(a) - c))))


def compare(samples, ref):
    """samples: {source: [yaw rad]} at common instants. -> {source: (offset deg, median, p90, max |residual| deg)}"""
    out = {}
    for k, v in samples.items():
        if k == ref:
            continue
        d = wrap(np.asarray(v) - np.asarray(samples[ref]))
        off = circ_median(d)
        r = np.degrees(np.abs(wrap(d - off)))
        out[k] = (math.degrees(off), float(np.median(r)), float(np.percentile(r, 90)), float(r.max()))
    return out


class Rec:
    def __init__(self, node, ns):
        self.last = {}                  # source -> latest yaw
        self.att = None
        self.rows, self.norm, self.incl = [], [], []
        sub = lambda t, topic, cb: node.create_subscription(t, f"{ns}/{topic}", cb, qos_profile_sensor_data)
        sub(PoseStamped, "mavros/local_position/pose", lambda m: self._pose("ekf", m.pose.orientation))
        sub(Odometry, "zed/zed_node/odom", lambda m: self._pose("zed", m.pose.pose.orientation))
        sub(PoseStamped, "state/pose", lambda m: self._pose("truth", m.pose.orientation))
        sub(Imu, "mavros/imu/data", lambda m: setattr(self, "att", (m.orientation.x, m.orientation.y, m.orientation.z, m.orientation.w)))
        sub(MagneticField, "mavros/imu/mag", self._mag)

    def _pose(self, k, o):
        self.last[k] = yaw_of((o.x, o.y, o.z, o.w))

    def _mag(self, m):
        f = (m.magnetic_field.x, m.magnetic_field.y, m.magnetic_field.z)
        if self.att is None or "ekf" not in self.last or not all(map(math.isfinite, f)):
            return
        h, incl = tilt_comp_heading(self.att, f)
        self.norm.append(math.sqrt(sum(v * v for v in f)) * 1e6)     # uT
        self.incl.append(incl)
        self.rows.append({**self.last, "mag": h, "t": time.time()})


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--drone", type=int, default=1)
    ap.add_argument("--duration", type=float, default=120.0, help="wall seconds to record")
    ap.add_argument("--max-rate", type=float, default=15.0, help="compare only while the heading turns slower than this, deg/s "
                    "(sources update at different instants: at 50 deg/s a 0.1 s gap is 5 deg)")
    ap.add_argument("--max-p90", type=float, default=5.0, help="magnetometer heading residual p90, deg")
    ap.add_argument("--max-norm-pct", type=float, default=5.0, help="field strength spread (std / mean), percent")
    ap.add_argument("--max-incl-deg", type=float, default=3.0, help="inclination spread (std), deg")
    a = ap.parse_args()

    rclpy.init()
    node = rclpy.create_node("compass_compare")
    rec = Rec(node, f"/drone_{a.drone}")
    t_end = time.time() + a.duration
    while time.time() < t_end:
        rclpy.spin_once(node, timeout_sec=0.1)
    node.destroy_node()
    rclpy.shutdown()

    keys = [k for k in ("ekf", "zed", "mag", "truth") if all(k in r for r in rec.rows)]
    if len(rec.rows) < 50 or "mag" not in keys:
        print(f"[compass] FAIL: {len(rec.rows)} samples (need 50 with mag + ekf); is MAVROS' imu plugin publishing mavros/imu/mag?")
        return 1
    ref = "truth" if "truth" in keys else "ekf"
    yaw = np.unwrap([r[ref] for r in rec.rows])
    t = np.array([r["t"] for r in rec.rows])
    j = np.searchsorted(t, t - 0.5)                         # over 0.5 s: the reference updates slower than the 250 Hz magnetometer
    rate = np.degrees(np.abs(yaw - yaw[j])) / np.maximum(t - t[j], 0.5)
    steady = [r for r, w in zip(rec.rows, rate) if w < a.max_rate]
    samples = {k: [r[k] for r in steady] for k in keys}
    span = math.degrees(np.ptp(yaw))
    print(f"[compass] {len(steady)} of {len(rec.rows)} samples turning < {a.max_rate:g} deg/s, heading swept {span:.0f} deg, reference = {ref}")
    print(f"  {'source':6s} {'offset':>8s} {'median':>7s} {'p90':>6s} {'max':>6s}   (deg vs {ref})")
    res = compare(samples, ref)
    for k, (off, med, p90, mx) in res.items():
        print(f"  {k:6s} {off:8.1f} {med:7.2f} {p90:6.2f} {mx:6.2f}")
    if ref == "truth":
        e = compare({k: samples[k] for k in ("ekf", "mag")}, "ekf")["mag"]
        print(f"  mag vs ekf: offset {e[0]:.1f}, residual {e[1]:.2f} / {e[2]:.2f} / {e[3]:.2f}  (what the drone can see without truth)")
    norm_pct = 100 * float(np.std(rec.norm) / np.mean(rec.norm))
    incl_std = float(np.std(rec.incl))
    print(f"  field {np.mean(rec.norm):.1f} uT +-{norm_pct:.1f} %, inclination {np.mean(rec.incl):.1f} +-{incl_std:.1f} deg")
    if span < 90:
        print("  note: turn the drone through at least 90 deg (better 360) or a hard-iron offset hides in the constant offset")
    bad = [s for s, ok in ((f"heading p90 {res['mag'][2]:.1f} > {a.max_p90}", res["mag"][2] <= a.max_p90),
                           (f"field spread {norm_pct:.1f} % > {a.max_norm_pct}", norm_pct <= a.max_norm_pct),
                           (f"inclination spread {incl_std:.1f} > {a.max_incl_deg}", incl_std <= a.max_incl_deg)) if not ok]
    print(f"[compass] magnetometer {'HEALTHY' if not bad else 'NOT HEALTHY: ' + '; '.join(bad)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
