"""Host-side unit tests for the map-frame correction of the ZED odometry (no ROS):  python3 -m unittest tests.unit.test_mapcorr -v

A drifting odometry (the ZED `odom` chain: a slow yaw drift and a position random walk) and the SDK's map pose, which equals the
odometry until a loop closure and the truth after it. The output must stay continuous (never step faster than the odometry by more
than the slew limits), reach the corrected pose, and ignore an implausible correction (a false loop closure)."""
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "docker", "zed"))

from zed_stack.bridge.mapcorr import MapCorrection, qz, rz, wrap, yaw_of  # noqa: E402

DT = 1 / 30


def truth(t):
    """A 2 m circle at 0.6 m/s, yaw along the heading."""
    a = 0.3 * t
    return (2.0 * math.cos(a), 2.0 * math.sin(a), 1.2), wrap(a + math.pi / 2)


def drifted(t, drift_deg_s=0.05, drift_mps=(0.004, -0.003)):
    """The odometry: the truth turned by a growing yaw error about the start, plus a translation drift."""
    (x, y, z), yaw = truth(t)
    e = math.radians(drift_deg_s * t)
    p = rz(e, (x, y, z))
    return (p[0] + drift_mps[0] * t, p[1] + drift_mps[1] * t, p[2]), wrap(yaw + e)


def run(mc, secs=60.0, close_at=30.0, false_step=None):
    """Feed odom + map poses; the map pose is the odometry before `close_at` and the truth after (a loop closure).
    `false_step`: a map pose this far off at `close_at` instead. Returns [(t, out_p, out_yaw, true_p, true_yaw)]."""
    rows = []
    t = 0.0
    while t < secs:
        op, oy = drifted(t)
        tp, ty = truth(t)
        if t < close_at:
            mp, my = op, oy
        elif false_step is not None:
            mp, my = (op[0] + false_step, op[1], op[2]), oy
        else:
            mp, my = tp, ty
        mc.target(mp, qz(my), op, qz(oy))
        p, q = mc.step(t, op, qz(oy))
        rows.append((t, p, yaw_of(q), tp, ty))
        t += DT
    return rows


class MapCorrectionTest(unittest.TestCase):
    def test_without_a_correction_the_output_is_the_odometry(self):
        rows = run(MapCorrection(), close_at=1e9)
        for t, p, yaw, _, _ in rows:
            op, oy = drifted(t)
            self.assertLess(math.dist(p, op), 1e-6)
            self.assertLess(abs(wrap(yaw - oy)), 1e-6)

    def test_a_loop_closure_is_applied_smoothly_and_reaches_the_corrected_pose(self):
        mc = MapCorrection(max_mps=0.2, max_dps=3.0)
        rows = run(mc, secs=60.0, close_at=30.0)
        before = math.dist(rows[int(29.9 / DT)][1], rows[int(29.9 / DT)][3])
        self.assertGreater(before, 0.15)                     # the odometry had drifted
        for (t0, p0, y0, _, _), (t1, p1, y1, _, _) in zip(rows, rows[1:]):
            o0, oy0 = drifted(t0)
            o1, oy1 = drifted(t1)
            extra = math.dist(p1, p0) - math.dist(o1, o0)
            self.assertLess(extra, 0.2 * DT + 0.03 * DT + 1e-6, f"step at {t1:.2f}")   # slew limit (+ the yaw part of the move)
            self.assertLess(abs(wrap((y1 - y0) - (oy1 - oy0))), math.radians(3.0) * DT + 1e-6)
        _, p, yaw, tp, ty = rows[-1]
        self.assertLess(math.dist(p, tp), 0.01)
        self.assertLess(abs(math.degrees(wrap(yaw - ty))), 0.05)
        self.assertEqual(mc.targets, 1)

    def test_a_false_loop_closure_is_ignored(self):
        mc = MapCorrection(max_step_m=3.0)
        rows = run(mc, secs=40.0, close_at=30.0, false_step=5.0)
        _, p, _, _, _ = rows[-1]
        self.assertLess(math.dist(p, drifted(rows[-1][0])[0]), 1e-6)
        self.assertGreater(mc.rejected, 0)

    def test_pending_reports_what_is_left(self):
        mc = MapCorrection(max_mps=0.1)
        mc.target((0, 0, 0), qz(0), (0, 0, 0), qz(0))
        mc.step(0.0, (0, 0, 0), qz(0))
        mc.target((1.0, 0, 0), qz(0), (0, 0, 0), qz(0))
        mc.step(0.1, (0, 0, 0), qz(0))
        m, deg = mc.pending((0, 0, 0))
        self.assertAlmostEqual(m, 0.99, places=6)
        self.assertEqual(deg, 0.0)

    def test_a_compass_heading_turns_later_motion_about_the_current_point(self):
        """The odometry heading slipped -30 deg at (5, 0): after set_yaw(+30 deg) the output does not jump there, and a 2 m leg the
        odometry reports along -30 deg comes out along 0 deg, as flown."""
        mc = MapCorrection(max_dps=10.0)
        here = (5.0, 0.0, 1.0)
        mc.set_yaw(0.0, here)                                  # starts the correction at identity
        mc.step(0.0, here, qz(math.radians(-30)))
        mc.set_yaw(math.radians(30.0), here)
        t, p = 0.0, None
        while t < 5.0:                                         # hover until the 30 deg are applied (3 s at 10 deg/s)
            t += DT
            p, q = mc.step(t, here, qz(math.radians(-30)))
        self.assertLess(math.dist(p, here), 1e-6)
        self.assertAlmostEqual(math.degrees(yaw_of(q)), 0.0, places=6)
        leg = rz(math.radians(-30), (2.0, 0.0, 0.0))
        p2, _ = mc.step(t + DT, tuple(a + b for a, b in zip(here, leg)), qz(math.radians(-30)))
        self.assertLess(math.dist(p2, (7.0, 0.0, 1.0)), 1e-6)


if __name__ == "__main__":
    unittest.main()
