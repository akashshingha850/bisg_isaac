"""Host-side unit tests for zed_stack (no ROS, no containers):  python3 -m unittest discover -s tests/unit -v"""
import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "docker", "zed"))
import numpy as np  # noqa: E402

from zed_stack import config  # noqa: E402
from zed_stack.__main__ import set_value  # noqa: E402
from zed_stack.bridge.sectors import BINS, sectors_from_depth  # noqa: E402


def cfg_with(**blocks):
    base = config.load().data
    return config.StackConfig(config.deep_merge(base, blocks), "test")


class CompileTests(unittest.TestCase):
    def test_default_file_is_valid_and_compiles(self):
        p = config.load().wrapper_params()
        self.assertEqual(p["pos_tracking"]["pos_tracking_enabled"], True)
        self.assertEqual(p["depth"]["depth_mode"], "NEURAL_PLUS")
        self.assertEqual(p["object_detection"]["od_enabled"], False)
        self.assertEqual(p["object_detection"]["class"]["people"]["enabled"], True)

    def test_every_sdk_module_has_a_switch_in_the_file(self):
        data = config.load().data
        for name in config.MODULES:
            self.assertIn(name, data, f"{name} missing from docker/zed/zed.yaml")

    def test_sim_deltas_only_in_sim(self):
        self.assertTrue(config.load().wrapper_params()["pos_tracking"]["imu_fusion"])
        sim = config.load(sim=True)
        self.assertFalse(sim.wrapper_params()["pos_tracking"]["imu_fusion"])
        self.assertTrue(sim.wrapper_params()["sensors"]["sensors_image_sync"])
        self.assertNotIn("odometry", config.load(sim=True).bridge_modules())
        self.assertIn("odometry", config.load().bridge_modules())

    def test_unknown_key_is_rejected_with_a_suggestion(self):
        with self.assertRaisesRegex(config.ConfigError, "did you mean 'max_depth'"):
            cfg_with(depth={"max_dpth": 5}).wrapper_params()

    def test_wrong_type_and_enum(self):
        with self.assertRaisesRegex(config.ConfigError, "expected bool"):
            cfg_with(video={"publish_raw": "yes"}).wrapper_params()
        with self.assertRaisesRegex(config.ConfigError, "one of"):
            cfg_with(positional_tracking={"pos_tracking_mode": "GEN_2"}).wrapper_params()

    def test_depth_off_disables_dependants(self):
        with self.assertRaisesRegex(config.ConfigError, "needs the depth map"):
            cfg_with(depth={"enabled": False}).wrapper_params()
        c = cfg_with(depth={"enabled": False}, positional_tracking={"enabled": False})
        self.assertEqual(c.wrapper_params()["depth"]["depth_mode"], "NONE")

    def test_plane_detection_lands_in_mapping_and_needs_tracking(self):
        p = cfg_with(plane_detection={"enabled": True}).wrapper_params()
        self.assertTrue(p["mapping"]["publish_det_plane"])
        self.assertFalse(p["mapping"]["mapping_enabled"] if "mapping_enabled" in p["mapping"] else False)
        with self.assertRaisesRegex(config.ConfigError, "plane_detection needs positional_tracking"):
            cfg_with(plane_detection={"enabled": True}, positional_tracking={"enabled": False}).wrapper_params()

    def test_bad_object_class(self):
        with self.assertRaisesRegex(config.ConfigError, "classes.persn"):
            cfg_with(object_detection={"classes": {"persn": {"enabled": True}}}).wrapper_params()

    def test_services_plan(self):
        c = cfg_with(services={"px4_bridge": {"enabled": False}, "qgc_video": {"enabled": True}})
        self.assertEqual(c.plan_services(), ["zed-video"])
        self.assertEqual(config.load().plan_services()[:1], ["zed-bridge"])      # zed-video follows when qgc_video is enabled in zed.yaml
        with self.assertRaisesRegex(config.ConfigError, "services.px4_bridge.odometry.restmp"):
            cfg_with(services={"px4_bridge": {"odometry": {"restmp": True}}}).services()

    def test_set_keeps_comments(self):
        text = "a:\n  b: 1   # note\n  c:\n    d: x\n"
        self.assertEqual(set_value(text, "a.b", "2"), "a:\n  b: 2   # note\n  c:\n    d: x\n")
        self.assertEqual(set_value(text, "a.c.d", "y"), "a:\n  b: 1   # note\n  c:\n    d: y\n")
        with self.assertRaises(config.ConfigError):
            set_value(text, "a.zz", "1")

    def test_set_validates_before_writing(self):
        from zed_stack.__main__ import main
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "zed.yaml")
            with open(config.DEFAULT_CONFIG) as src, open(path, "w") as dst:
                dst.write(src.read())
            self.assertEqual(main(["set", "--config", path, "object_detection.enabled=true"]), 0)
            self.assertTrue(config.load(path).enabled("object_detection"))
            with open(path) as f:
                before = f.read()
            self.assertEqual(main(["set", "--config", path, "depth.depth_mode=FAST"]), 1)
            with open(path) as f:
                self.assertEqual(f.read(), before)


class SectorTests(unittest.TestCase):
    FX = FY = 530.0
    CX, CY = 640.0, 360.0

    def depth(self, h=720, w=1280, fill=np.nan):
        return np.full((h, w), fill, np.float32)

    def test_wall_straight_ahead_fills_forward_sectors(self):
        z = self.depth(fill=2.0)                                  # a flat wall 2 m ahead, everything in the height band
        r = sectors_from_depth(z, self.FX, self.FY, self.CX, self.CY, band=2.0, rmin=0.3, rmax=8.0)
        self.assertEqual(r.shape, (BINS,))
        fwd = r[36]                                               # bin 36 = azimuth 0 .. 5 deg
        self.assertAlmostEqual(float(fwd), 2.0, delta=0.05)
        self.assertTrue(math.isinf(r[0]))                         # behind the drone: unknown

    def test_nothing_in_range_is_free_not_unknown(self):
        r = sectors_from_depth(self.depth(fill=20.0), self.FX, self.FY, self.CX, self.CY, 2.0, 0.3, 8.0)
        self.assertAlmostEqual(float(r[36]), 8.01, places=2)

    def test_height_band_ignores_floor_and_ceiling(self):
        z = self.depth(fill=np.nan)
        z[:100, :] = 2.0                                          # rows 0-99 = 1 m ABOVE the camera at 2 m: outside band 0.6
        r = sectors_from_depth(z, self.FX, self.FY, self.CX, self.CY, band=0.6, rmin=0.3, rmax=8.0)
        self.assertGreater(float(r[36]), 8.0)
        r = sectors_from_depth(z, self.FX, self.FY, self.CX, self.CY, band=1.5, rmin=0.3, rmax=8.0)
        self.assertAlmostEqual(float(r[36]), 2.0, delta=0.05)

    def test_obstacle_on_the_right_lands_right_of_forward(self):
        z = self.depth(fill=np.nan)
        z[:, 1000:1100] = 1.5                                     # columns right of centre
        r = sectors_from_depth(z, self.FX, self.FY, self.CX, self.CY, band=5.0, rmin=0.3, rmax=8.0)
        near = np.where(r < 3.0)[0]
        self.assertTrue(len(near) > 0 and near.min() > 36)       # clockwise-positive azimuth


if __name__ == "__main__":
    unittest.main()
