"""Depth image -> 72 x 5 deg obstacle sectors. numpy only, so it is unit-testable without ROS (tests/unit)."""
import numpy as np

BINS, INC_DEG, START_DEG = 72, 5.0, -180.0       # bin 0 = FRD azimuth -180 deg (clockwise from forward)


def sectors_from_depth(z, fx, fy, cx, cy, band, rmin, rmax):
    """Depth image (H x W, metres, float32) + pinhole intrinsics -> 72 ranges [m]: inf = unknown, rmax+0.01 = free."""
    h, w = z.shape
    u = np.arange(0, w, 2)                                    # every 2nd column / row is plenty for 5 deg sectors
    v = np.arange(0, h, 2)
    az = np.arctan((u - cx) / fx)                             # clockwise (right) positive = FRD
    zz = z[np.ix_(v, u)]
    height = zz * ((v - cy) / fy)[:, None]                    # height of each point wrt the camera (down positive)
    ok = np.isfinite(zz) & (zz >= rmin) & (np.abs(height) <= band)
    nearest = np.where(ok, zz, np.inf).min(axis=0)            # per column
    dist = nearest / np.cos(az)                               # horizontal distance along the bearing
    idx = np.clip(np.floor((np.degrees(az) - START_DEG) / INC_DEG).astype(int), 0, BINS - 1)
    ranges = np.full(BINS, np.inf, np.float32)
    ranges[np.unique(idx)] = rmax + 0.01                      # inside the FOV and nothing in range = free
    np.minimum.at(ranges, idx, np.where(dist <= rmax, dist, rmax + 0.01).astype(np.float32))
    return ranges
