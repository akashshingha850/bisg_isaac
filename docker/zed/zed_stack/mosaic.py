"""Image functions of the 2x2 QGC video (services.qgc_video, layout: grid). No ROS, no GStreamer: plain numpy + OpenCV, unit-tested.

    +--------+---------+
    |  left  |  right  |      left/right: the wrapper's rectified colour images
    +--------+---------+      depth:      depth_registered (metres) as a colour map, near = red, far = blue, no data = black
    | depth  |  flow   |      flow:       dense Farneback optical flow of the left image between two frames, hue = direction,
    +--------+---------+                  brightness = speed. Computed here, the ZED SDK has no flow module
"""
import cv2
import numpy as np

DEPTH_RANGE = (0.3, 10.0)       # m: colour-map span; closer than the start = red, beyond the end = blue
FLOW_WIDTH = 320                # flow is computed at this width (Farneback ~6 ms at 320x180) and scaled up to the tile
FLOW_FULL_SCALE = 4.0           # px/frame at FLOW_WIDTH that reads as full brightness
FLOW_DEADZONE = 0.05            # px/frame below which a pixel stays black (sensor noise of a hovering drone)

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


class Flow:
    """Dense optical flow between consecutive frames passed to update(), as a BGR colour image of the size they came in."""

    def __init__(self):
        self.prev = None
        self.last = None

    def update(self, bgr):
        h, w = bgr.shape[:2]
        fw, fh = FLOW_WIDTH, max(2, int(round(FLOW_WIDTH * h / w)))
        gray = cv2.cvtColor(cv2.resize(bgr, (fw, fh), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
        if self.prev is None or self.prev.shape != gray.shape:
            self.prev = gray
            self.last = np.zeros_like(bgr)
            return self.last
        flow = cv2.calcOpticalFlowFarneback(self.prev, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        self.prev = gray
        mag, ang = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        hsv = np.empty((fh, fw, 3), np.uint8)
        hsv[..., 0] = (ang * (90.0 / np.pi)).astype(np.uint8)                       # 0..2pi -> 0..179
        hsv[..., 1] = 255
        hsv[..., 2] = (np.clip((mag - FLOW_DEADZONE) / FLOW_FULL_SCALE, 0.0, 1.0) * 255).astype(np.uint8)
        self.last = cv2.resize(cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR), (w, h), interpolation=cv2.INTER_LINEAR)
        return self.last


def blank(size, text="no signal"):
    img = np.full((size[1], size[0], 3), 24, np.uint8)
    cv2.putText(img, text, (10, size[1] // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 160, 160), 1, cv2.LINE_AA)
    return img


def label(img, text):
    """Burn a small caption into the top-left corner (in place)."""
    cv2.putText(img, text, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def grid(left, right, depth, flow):
    return np.vstack([np.hstack([left, right]), np.hstack([depth, flow])])
