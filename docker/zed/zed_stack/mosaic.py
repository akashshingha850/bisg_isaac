"""Image functions of the 2x2 QGC video (services.qgc_video, layout: grid). No ROS, no GStreamer: plain numpy + OpenCV, unit-tested.

    +--------+---------+
    |  left  |  chase  |      left:       the wrapper's rectified colour image
    +--------+---------+      chase:      third-person view of the drone, /drone_N/chase/image (sim only; "no signal" on the real drone)
    | depth  |  flow   |      depth:      depth_registered (metres) as a colour map, near = red, far = blue, no data = black
    +--------+---------+      flow:       the down-facing PMW3901 as PX4 reports it (mavros/px4flow/raw/optical_flow_rad), drawn
                                          top-down by FlowView. Not from the ZED, and not a picture: the PMW3901 sends no image
"""
from collections import deque

import cv2
import numpy as np

DEPTH_RANGE = (0.3, 10.0)       # m: colour-map span; closer than the start = red, beyond the end = blue
FLOW_FULL_SCALE = 2.0           # rad/s of flow at the edge of the FlowView circle; radius ~ sqrt(flow), so the inner ring is 0.5 rad/s
                                # (0.4 m/s at 1.5 m reads at a third of the radius, the 1-2 rad/s just after takeoff still fit)
FLOW_TRAIL_S = 2.0              # s of past flow vectors drawn as dots

# ROS encoding -> (channels, OpenCV conversion to BGR or None)
COLOUR = {"bgr8": (3, None), "rgb8": (3, cv2.COLOR_RGB2BGR), "bgra8": (4, cv2.COLOR_BGRA2BGR),
          "rgba8": (4, cv2.COLOR_RGBA2BGR), "mono8": (1, cv2.COLOR_GRAY2BGR)}
DEPTH = {"32FC1": (np.float32, 1.0), "16UC1": (np.uint16, 0.001)}      # ROS depth encoding -> (dtype, scale to metres)


def tile_size(width, src_w, src_h):
    """Tile (w, h) for a mosaic `width` px wide: half of it, the source's aspect ratio, even numbers (H.264 4:2:0)."""
    tw = max(2, int(width) // 4 * 2)
    th = max(2, int(round(tw * src_h / src_w)) // 2 * 2)
    return tw, th


def to_bgr(data, width, height, step, encoding, size):
    """A sensor_msgs/Image of a colour encoding -> BGR uint8 resized to size=(w, h); the source's row padding is dropped."""
    channels, conv = COLOUR[encoding]
    img = np.frombuffer(data, np.uint8).reshape(height, step)[:, :width * channels].reshape(height, width, channels)
    img = cv2.resize(img, size, interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(img, conv) if conv is not None else img


def depth_to_bgr(data, width, height, step, encoding, size):
    """A depth Image (32FC1 metres or 16UC1 mm) -> BGR colour map at size=(w, h). NaN / inf / <= 0 = black."""
    dtype, scale = DEPTH[encoding]
    d = np.frombuffer(data, dtype).reshape(height, step // np.dtype(dtype).itemsize)[:, :width]
    d = cv2.resize(d, size, interpolation=cv2.INTER_NEAREST).astype(np.float32) * scale      # nearest: never blend a NaN into a neighbour
    near, far = DEPTH_RANGE
    norm = np.nan_to_num(np.clip((d - near) / (far - near), 0.0, 1.0), nan=1.0, posinf=1.0, neginf=1.0)
    out = cv2.applyColorMap(((1.0 - norm) * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    out[~np.isfinite(d) | (d <= 0)] = 0
    return out


class FlowView:
    """The PMW3901's flow (fields of mavros_msgs/OpticalFlowRad = PX4 OPTICAL_FLOW_RAD) drawn top-down, up = forward, right = right.

    Signs are MAVROS' (REP-103): the px4flow plugin turns PX4's FRD into base_link FLU (y and z flip), so flow and gyro are
    positive for a right-handed rotation about FLU x / y. Flow minus gyro is the translational part (v_left, -v_forward) / distance
    (checked against Pegasus ground truth in flight, 2026-10-14), so the arrow (v_right, v_forward) / distance points where the
    vehicle moves over the ground, in rad/s (radius ~ sqrt). Thin grey arrow = the raw flow (rotation included), dots = the last FLOW_TRAIL_S seconds.
    """

    def __init__(self):
        self.last = None           # (time, comp, raw, quality, distance), comp/raw = (right, forward) rad/s
        self.trail = deque()

    def add(self, t, integration_time_us, ix, iy, gx, gy, quality, distance):
        """One flow message at monotonic time t. Returns False when the integration span is empty (nothing to show)."""
        dt = integration_time_us * 1e-6
        if dt <= 0.0:
            return False
        raw = np.array([-ix, -iy]) / dt
        comp = np.array([-(ix - gx), -(iy - gy)]) / dt
        self.last = (t, comp, raw, int(quality), float(distance))
        self.trail.append((t, comp))
        while self.trail and t - self.trail[0][0] > FLOW_TRAIL_S:
            self.trail.popleft()
        return True

    def draw(self, size):
        if self.last is None:
            return blank(size, "no flow (mavros/px4flow)")
        w, h = size
        img = np.full((h, w, 3), 24, np.uint8)
        _, comp, raw, quality, distance = self.last
        c = np.array([w // 2, h // 2])
        r = int(0.42 * min(w, h))
        cv2.circle(img, tuple(c), r, (70, 70, 70), 1, cv2.LINE_AA)
        cv2.circle(img, tuple(c), r // 2, (50, 50, 50), 1, cv2.LINE_AA)
        cv2.line(img, (c[0] - r, c[1]), (c[0] + r, c[1]), (50, 50, 50), 1)
        cv2.line(img, (c[0], c[1] - r), (c[0], c[1] + r), (50, 50, 50), 1)
        for text, x, y in (("fwd", c[0] + 4, c[1] - r + 14), (f"{FLOW_FULL_SCALE / 4:g}", c[0] + r // 2 + 3, c[1] - 4),
                           (f"{FLOW_FULL_SCALE:g} rad/s", c[0] + r + 3, c[1] - 4)):
            cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (110, 110, 110), 1, cv2.LINE_AA)

        def px(v):                                  # (right, forward) rad/s -> pixel: radius ~ sqrt(|v|), clipped to the circle
            v = np.asarray(v, float) / FLOW_FULL_SCALE
            n = np.hypot(*v)
            v = v * (np.sqrt(min(n, 1.0)) / n) if n > 1e-9 else v
            return int(c[0] + v[0] * r), int(c[1] - v[1] * r)

        for _, v in self.trail:
            cv2.circle(img, px(v), 2, (90, 140, 90), -1, cv2.LINE_AA)
        cv2.arrowedLine(img, tuple(c), px(raw), (150, 150, 150), 1, cv2.LINE_AA, tipLength=0.15)
        colour = (80, 220, 80) if quality > 0 else (60, 60, 230)
        cv2.arrowedLine(img, tuple(c), px(comp), colour, 3, cv2.LINE_AA, tipLength=0.2)
        lines = [f"q {quality}  d {f'{distance:.2f} m' if distance > 0 else 'unknown'}",
                 f"flow fwd {comp[1]:+.2f} right {comp[0]:+.2f} rad/s"]
        if distance > 0:
            lines.append(f"~v fwd {comp[1] * distance:+.2f} right {comp[0] * distance:+.2f} m/s")
        for i, text in enumerate(reversed(lines)):
            y = h - 10 - 18 * i
            cv2.putText(img, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(img, text, (8, y), cv2.FONT_HERSHEY_SIMPLEX, 0.45, colour, 1, cv2.LINE_AA)
        return img


def blank(size, text="no signal"):
    img = np.full((size[1], size[0], 3), 24, np.uint8)
    cv2.putText(img, text, (10, size[1] // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 160, 160), 1, cv2.LINE_AA)
    return img


def label(img, text):
    """Burn a small caption into the top-left corner (in place)."""
    cv2.putText(img, text, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def grid(left, chase, depth, flow):
    return np.vstack([np.hstack([left, chase]), np.hstack([depth, flow])])
