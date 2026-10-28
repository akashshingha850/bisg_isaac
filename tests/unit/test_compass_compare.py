"""Unit tests for tests/compass_compare.py's math (needs rclpy for the import: run in the ros container):
    docker exec bisg-ros bash -lc 'source /opt/ros/jazzy/setup.bash; cd /workspace; python3 -m unittest tests.unit.test_compass_compare -v'
"""
import math
import os
import sys
import unittest

import numpy as np

try:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
    import compass_compare as cc
except ImportError:                 # no rclpy on the host
    cc = None


def quat(yaw, pitch, roll):
    """ZYX Euler (rad) -> (x, y, z, w)."""
    cy, sy, cp, sp, cr, sr = (f(a / 2) for a in (yaw, pitch, roll) for f in (math.cos, math.sin))
    return (sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy)


@unittest.skipIf(cc is None, "rclpy not importable")
class TestCompassCompare(unittest.TestCase):
    def test_tilt_compensated_heading_is_exact_at_any_tilt_and_heading(self):
        north = math.radians(30.0)
        field = np.array([20e-6 * math.cos(north), 20e-6 * math.sin(north), -40e-6])      # ENU, pointing down: inclination 63.4
        for yaw in np.radians(np.arange(-180, 180, 23)):
            for pitch, roll in ((0, 0), (-10, 15), (25, -20)):
                q = quat(yaw, math.radians(pitch), math.radians(roll))
                x, y, z, w = q
                R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                              [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                              [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
                h, incl = cc.tilt_comp_heading(q, R.T @ field)
                self.assertAlmostEqual(cc.wrap(h - (yaw - north)), 0.0, places=9)
                self.assertAlmostEqual(incl, math.degrees(math.atan2(40, 20)), places=6)

    def test_offset_survives_the_wrap_at_180(self):
        off, med, p90, mx = cc.compare({"a": [3.1, -3.1, 0.1], "b": [3.6, -2.6, 0.6]}, "a")["b"]
        self.assertAlmostEqual(off, math.degrees(0.5), places=6)
        self.assertAlmostEqual(mx, 0.0, places=6)


if __name__ == "__main__":
    unittest.main()
