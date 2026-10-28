"""Host-side unit tests for the Manhattan compass (numpy, no ROS):  python3 -m unittest tests.unit.test_compass -v

Synthetic depth images of a box room (ray-cast against axis-aligned walls, floor and ceiling) from a camera at a known yaw, with the
odometry's orientation given a known yaw error: the compass must return that error (folded into +-45 deg), with one wall or two in
view, with depth noise, and reject a view with no wall."""
import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "docker", "zed"))

from zed_stack.bridge.compass import R_LINK_OPT, Compass, room_axis, wrap90  # noqa: E402

W, H, FX, FY, CX, CY = 1280, 720, 530.0, 530.0, 640.0, 360.0
ROOM = (-10.0, 10.0, -12.0, 18.0, 0.0, 9.0)       # x0 x1 y0 y1 z0 z1, the Warehouse's size


def yaw_q(a):
    return (0.0, 0.0, math.sin(a / 2), math.cos(a / 2))


def render(pos, yaw, room_yaw=0.0, noise=0.0, seed=0):
    """Depth (optical z) of the box room seen from pos with the camera level at `yaw`; the room turned by room_yaw."""
    v, u = np.mgrid[0:H, 0:W].astype(float)
    ray_opt = np.stack([(u - CX) / FX, (v - CY) / FY, np.ones_like(u)], axis=-1)
    c, s = math.cos(yaw - room_yaw), math.sin(yaw - room_yaw)
    Rz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    ray = ray_opt @ (Rz @ R_LINK_OPT).T                 # in the room frame
    t = np.full((H, W), np.inf)
    for ax, (lo, hi) in enumerate(((ROOM[0], ROOM[1]), (ROOM[2], ROOM[3]), (ROOM[4], ROOM[5]))):
        r = ray[..., ax]
        with np.errstate(divide="ignore", invalid="ignore"):
            for plane in (lo, hi):
                tt = (plane - pos[ax]) / r
                t = np.where((tt > 0) & (tt < t), tt, t)
    z = t * 1.0                                          # optical z of the ray direction is 1 by construction
    if noise:
        z = z * (1 + np.random.default_rng(seed).normal(0, noise, z.shape))
    return z.astype(np.float32)


class CompassTest(unittest.TestCase):
    def test_the_room_axis_is_the_odometry_yaw_error(self):
        for yaw in (0.0, 0.7, 2.0, -2.6):
            for err_deg in (0.0, 5.0, -12.0, 30.0):
                d = render((0.0, 0.0, 2.0), yaw)
                q = yaw_q(yaw + math.radians(err_deg))       # the odometry believes the camera is turned by err
                axis, conc, n = room_axis(d, FX, FY, CX, CY, q)
                self.assertAlmostEqual(math.degrees(axis), err_deg, delta=0.5, msg=f"yaw {yaw} err {err_deg}")
                self.assertGreater(conc, 2.0)

    def test_a_high_camera_uses_the_walls_below_it(self):
        """Kinetix scans fly 3.5-5 m up: the walls below the camera (down to 0.5 m over the floor) count, the floor does not."""
        d = render((0.0, 0.0, 4.5), 0.4)
        q = yaw_q(0.4 + math.radians(6.0))
        axis, conc, n = room_axis(d, FX, FY, CX, CY, q)
        _, _, n_above = room_axis(d, FX, FY, CX, CY, q, floor_clear=100.0)    # the band starting 0.3 m over the camera only
        self.assertAlmostEqual(math.degrees(axis), 6.0, delta=0.5)
        self.assertGreater(n, 1.5 * n_above)

    def test_one_wall_is_enough(self):
        d = render((0.0, 15.0, 2.0), math.pi / 2)           # facing the near north wall (3 m), nothing else but floor / ceiling
        axis, conc, n = room_axis(d, FX, FY, CX, CY, yaw_q(math.pi / 2 + math.radians(7.0)))
        self.assertAlmostEqual(math.degrees(axis), 7.0, delta=0.5)

    def test_depth_noise_of_a_stereo_camera(self):
        d = render((0.0, 0.0, 2.0), 0.4, noise=0.03)       # per-pixel iid, 3 % of range
        axis, conc, n = room_axis(d, FX, FY, CX, CY, yaw_q(0.4 + math.radians(-4.0)))
        self.assertAlmostEqual(math.degrees(axis), -4.0, delta=1.0)

    def test_a_view_too_noisy_to_trust_is_rejected_by_its_sharpness(self):
        c = Compass(n_ref=1, n_avg=1)
        d = render((0.0, 0.0, 2.0), 0.4, noise=0.2)
        meas = room_axis(d, FX, FY, CX, CY, yaw_q(0.4))
        self.assertLess(meas[1], c.min_sharp)
        self.assertIsNone(c.add(meas))
        self.assertEqual(c.rejected, 1)

    def test_a_view_of_the_floor_only_is_rejected(self):
        d = render((0.0, 0.0, 2.0), 0.0)
        d[:, :] = np.nan
        self.assertIsNone(room_axis(d, FX, FY, CX, CY, yaw_q(0.0)))

    def test_the_tracker_reports_drift_against_the_take_off_reference(self):
        c = Compass(n_ref=3, n_avg=3)
        for _ in range(3):
            self.assertIsNone(c.add((math.radians(10.0), 3.0, 1000)))        # reference: the room at 10 deg in odom
        out = [c.add((math.radians(10.0 - 6.0), 3.0, 1000)) for _ in range(3)]
        self.assertAlmostEqual(math.degrees(out[-1]), -6.0, places=6)
        self.assertIsNone(c.add((0.0, 1.2, 1000)))                            # not Manhattan enough
        self.assertEqual(c.rejected, 1)
        self.assertAlmostEqual(math.degrees(wrap90(math.radians(44.0) + math.radians(3.0))), -43.0, places=6)

    def test_a_drift_past_45_deg_is_tracked_not_folded(self):
        c = Compass(n_ref=1, n_avg=3)
        c.add((0.0, 3.0, 1000))
        out = None
        for total in (-10, -25, -44, -63, -63, -63, -63):              # two slips: -44 then -19 more (the 2026-10-26 flight)
            out = c.add((wrap90(math.radians(total)), 3.0, 1000))
        self.assertAlmostEqual(math.degrees(out), -63.0, places=6)


if __name__ == "__main__":
    unittest.main()
