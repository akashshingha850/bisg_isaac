"""2x2 QGC video image functions (docker/zed/zed_stack/mosaic.py). Needs OpenCV, which only the bisg/zed image has:
`./bisg zed test` runs this file there; on a host without cv2 it is skipped."""
import unittest

try:
    import cv2
    import numpy as np
    from zed_stack import mosaic
except ImportError:
    cv2 = None


@unittest.skipIf(cv2 is None, "OpenCV not installed (runs in the bisg/zed image)")
class MosaicTest(unittest.TestCase):
    def test_tile_size_is_even_and_keeps_aspect(self):
        self.assertEqual(mosaic.tile_size(1280, 1280, 720), (640, 360))
        self.assertEqual(mosaic.tile_size(1281, 672, 376), (640, 358))
        tw, th = mosaic.tile_size(900, 1920, 1080)
        self.assertEqual((tw % 2, th % 2), (0, 0))

    def test_to_bgr_encodings_and_row_padding(self):
        rgb = np.zeros((4, 6, 3), np.uint8)
        rgb[..., 0] = 200                                    # red in rgb8 is blue-last in BGR
        padded = np.zeros((4, 24), np.uint8)
        padded[:, :18] = rgb.reshape(4, 18)                  # step 24 > width*3: padding must be dropped
        out = mosaic.to_bgr(padded.tobytes(), 6, 4, 24, "rgb8", (6, 4))
        self.assertEqual(out.shape, (4, 6, 3))
        self.assertEqual(tuple(out[0, 0]), (0, 0, 200))
        bgra = np.zeros((4, 6, 4), np.uint8)
        bgra[..., 0] = 90
        out = mosaic.to_bgr(bgra.tobytes(), 6, 4, 24, "bgra8", (3, 2))
        self.assertEqual(out.shape, (2, 3, 3))
        self.assertEqual(tuple(out[0, 0]), (90, 0, 0))
        with self.assertRaises(KeyError):
            mosaic.to_bgr(b"", 1, 1, 1, "yuv422", (1, 1))

    def test_depth_colormap_near_far_and_no_data(self):
        d = np.array([[0.5, 9.5, np.nan, 0.0]], np.float32)
        out = mosaic.depth_to_bgr(d.tobytes(), 4, 1, 16, "32FC1", (4, 1))
        near, far = out[0, 0], out[0, 1]
        self.assertGreater(near[2], near[0])                 # near = red
        self.assertGreater(far[0], far[2])                   # far = blue
        self.assertEqual(tuple(out[0, 2]), (0, 0, 0))
        self.assertEqual(tuple(out[0, 3]), (0, 0, 0))
        mm = (d[:, :2] * 1000).astype(np.uint16)
        out16 = mosaic.depth_to_bgr(mm.tobytes(), 2, 1, 4, "16UC1", (2, 1))
        self.assertEqual(out16[0, 0].tolist(), near.tolist())

    def test_flow_view_signs_and_drawing(self):
        view = mosaic.FlowView()
        self.assertEqual(view.draw((64, 36)).shape, (36, 64, 3))                    # no message yet: "no flow" blank
        self.assertFalse(view.add(0.0, 0, 0.01, 0.0, 0.0, 0.0, 255, 1.0))           # empty span: ignored
        # MAVROS (FLU): 1 m/s forward at 2 m over 20 ms, plus a pitch rate of 0.3 rad/s: flow y = (-v/d - q) * dt, gyro y = -q * dt
        dt = 0.02
        self.assertTrue(view.add(1.0, 20000, 0.0, -(0.5 + 0.3) * dt, 0.0, -0.3 * dt, 255, 2.0))
        _, comp, raw, quality, distance = view.last
        np.testing.assert_allclose(comp, [0.0, 0.5], atol=1e-9)                    # (right, forward) rad/s, rotation removed
        np.testing.assert_allclose(raw, [0.0, 0.8], atol=1e-9)
        self.assertEqual((quality, distance), (255, 2.0))
        view.add(1.1, 20000, -1.0 * dt, 0.0, 0.0, 0.0, 255, 2.0)                    # FLU flow x < 0 = moving right
        np.testing.assert_allclose(view.last[1], [1.0, 0.0], atol=1e-9)
        img = view.draw((640, 360))
        self.assertEqual(img.shape, (360, 640, 3))
        green = (img[..., 1] > 180) & (img[..., 2] < 120)
        ys, xs = np.nonzero(green[:300])                                            # the arrow (text sits at the bottom)
        self.assertGreater(xs.min() + xs.max(), 2 * 360)                            # points right of the centre (1 rad/s = 0.71 r = 107 px)
        self.assertLess(np.ptp(ys), 50)                                             # and level (a vertical one spans 107 px)
        view.add(1.2, 20000, 0.0, 0.0, 0.0, 0.0, 0, -1.0)                           # quality 0: drawn red, distance unknown
        self.assertEqual(view.last[3:], (0, -1.0))
        self.assertEqual(len(view.trail), 3)
        view.add(5.0, 20000, 0.0, 0.0, 0.0, 0.0, 255, 1.0)                          # older than FLOW_TRAIL_S: dropped
        self.assertEqual(len(view.trail), 1)

    def test_grid_and_labels(self):
        tiles = [np.full((36, 64, 3), v, np.uint8) for v in (10, 20, 30, 40)]
        g = mosaic.grid(*tiles)
        self.assertEqual(g.shape, (72, 128, 3))
        self.assertEqual((g[0, 0, 0], g[0, 64, 0], g[36, 0, 0], g[36, 64, 0]), (10, 20, 30, 40))
        before = g.copy()
        mosaic.label(g[:36, :64], "left")
        self.assertFalse(np.array_equal(before[:36, :64], g[:36, :64]))
        self.assertTrue(np.array_equal(before[36:], g[36:]))


if __name__ == "__main__":
    unittest.main()
