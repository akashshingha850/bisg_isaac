"""Manhattan compass: a drift-free heading from the walls of a box room, in the ZED depth image (numpy, no ROS).

The dominant VIO error on the sim drone is a heading slip in in-place turns (docs/vio-drift.md: 2-8 deg per 90 deg turn at 2 m in the
Warehouse); with no magnetometer EKF2's heading is the ZED's, so every metre flown after a slip adds ~sin(slip) of cross-track error.
Man-made rooms give an absolute heading for free: their walls are vertical planes along two orthogonal directions (Manhattan world).
The room axis, seen from the camera and rotated into the odometry frame, stays put while the odometry yaw is right and turns with its
error when it is not, so (room axis now) - (room axis at take-off), folded into [-45, 45) deg, IS the odometry's yaw drift.

Method: the idea of Straub et al. ("Real-time Manhattan World Rotation Estimation in 3D", IROS 2015) reduced to yaw, because gravity
gives roll / pitch, and used as a heading aid like Doer & Trommer (ICINS 2021). Back-project a decimated depth image, rotate it into
the odometry frame with the camera's gravity-aligned orientation, keep the points 0.3-4 m above the camera (walls, columns: no floor),
project them on the horizontal plane and search the rotation that makes their x and y histograms sharpest (sum of squared bin
weights; walls collapse into single bins when the axes line up with them). Every point votes, so the stereo noise of a wall 10 m
away (residuals ~0.7 m) averages out; per-pixel surface normals do not survive it (tried first: 2-6 deg wandering on a still drone,
and depth edges posing as walls). Points are weighted by 1/z^2 (stereo depth error grows with z^2). One wall in view is enough.
`sharpness` (best score / median score over all angles) says how Manhattan the view is; a cluttered or round view is rejected.
"""
import math

import numpy as np

# zed optical frame (x right, y down, z forward) -> zed camera link frame (FLU)
R_LINK_OPT = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])


def quat_to_R(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def wrap90(a):
    """Fold an angle (rad) into [-pi/4, pi/4)."""
    return (a + math.pi / 4) % (math.pi / 2) - math.pi / 4


def _score(xy, w, th, bin_m):
    c, s = math.cos(th), math.sin(th)
    out = 0.0
    for p in (c * xy[:, 0] + s * xy[:, 1], -s * xy[:, 0] + c * xy[:, 1]):
        f = (p - p.min()) / bin_m
        i = np.floor(f).astype(np.int64)
        r = f - i                                   # linear (soft) binning: a hard histogram aliases by ~1 deg
        h = np.bincount(i, weights=w * (1 - r), minlength=i.max() + 2) + np.bincount(i + 1, weights=w * r, minlength=i.max() + 2)
        out += float(np.dot(h, h))
    return out


def room_axis(depth, fx, fy, cx, cy, q_odom_cam, step=4, z_range=(0.4, 12.0), z_band=(0.3, 4.0), bin_m=0.1, min_points=200):
    """Room axis (rad, in [-pi/4, pi/4)) in the odometry frame from one depth image (H x W float metres, optical frame) taken with
    the camera at orientation q_odom_cam (x, y, z, w of zed_camera_link in odom). Returns (axis, sharpness, n_points) or None."""
    d = np.asarray(depth, dtype=np.float64)[::step, ::step]
    H, W = d.shape
    v, u = np.mgrid[0:H, 0:W]
    u = u * step + step // 2
    v = v * step + step // 2
    P = np.stack([(u - cx) / fx * d, (v - cy) / fy * d, d], axis=-1)
    with np.errstate(invalid="ignore"):
        Pw = P @ (quat_to_R(q_odom_cam) @ R_LINK_OPT).T
        ok = np.isfinite(d) & (d > z_range[0]) & (d < z_range[1]) & (Pw[..., 2] > z_band[0]) & (Pw[..., 2] < z_band[1])
    if ok.sum() < min_points:
        return None
    xy, w = Pw[..., :2][ok], 1.0 / np.maximum(d[ok], 1.0) ** 2
    coarse = np.radians(np.arange(-45.0, 45.0, 1.0))
    sc = np.array([_score(xy, w, t, bin_m) for t in coarse])
    k = int(np.argmax(sc))
    fine = coarse[k] + np.radians(np.arange(-1.5, 1.51, 0.1))
    best = fine[int(np.argmax([_score(xy, w, t, bin_m) for t in fine]))]
    return wrap90(best), float(sc[k] / np.median(sc)), int(ok.sum())


class Compass:
    """Room axis -> yaw drift of the odometry. The reference is the median axis of the first `n_ref` accepted views (taken on the
    ground / at take-off, where the odometry has not drifted). `drift()` is the median of the last `n_avg` accepted measurements.
    A measurement only knows the drift modulo 90 deg, so each one is unwrapped against the current estimate: the drift is tracked
    through any total, as long as it moves less than 45 deg between two accepted views (the sim's worst slip so far: ~40 deg in a
    360 deg spin, with no view accepted during the spin). Folding against 0 instead flipped a -63 deg drift to +27 (2026-10-26)."""

    def __init__(self, min_points=500, min_sharpness=2.0, n_ref=10, n_avg=5):
        self.min_points, self.min_sharp = min_points, min_sharpness
        self.n_ref, self.n_avg = n_ref, n_avg
        self.ref_samples, self.ref = [], None
        self.recent = []
        self.accepted = self.rejected = 0

    def add(self, meas):
        """meas = room_axis(...) result or None. Returns the drift estimate (rad) once the reference exists, else None."""
        if meas is None or meas[2] < self.min_points or meas[1] < self.min_sharp:
            self.rejected += 1
            return None
        self.accepted += 1
        axis = meas[0]
        if self.ref is None:
            self.ref_samples.append(axis)
            if len(self.ref_samples) >= self.n_ref:
                c = self.ref_samples[0]                          # unwrap around the first sample, then the median
                self.ref = wrap90(c + float(np.median([wrap90(x - c) for x in self.ref_samples])))
            return None
        prev = float(np.median(self.recent)) if self.recent else 0.0
        self.recent = (self.recent + [prev + wrap90(axis - self.ref - prev)])[-self.n_avg:]
        return self.drift()

    def drift(self):
        if self.ref is None or len(self.recent) < self.n_avg:
            return None
        return float(np.median(self.recent))
