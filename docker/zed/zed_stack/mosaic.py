"""Image functions of the 2x2 QGC video (services.qgc_video, layout: grid). No ROS, no GStreamer: plain numpy + OpenCV, unit-tested.

    +--------+------------+
    |  left  |   chase    |   left:       the wrapper's rectified colour image
    +--------+------------+   chase:      third-person view of the drone, /drone_N/chase/image (sim only; "no signal" on the real drone)
    | depth  | confidence |   depth:      depth_registered (metres) as a colour map, near = red, far = blue, no data = black
    +--------+------------+   confidence: confidence/confidence_map (0-100, higher = LESS confident) as a colour map, sure = blue,
                                          unsure = red: where depth has holes (pixels above depth.depth_confidence are dropped)
The same four views are the Foxglove Camera tab (docker/ros/foxglove/make_layout.py); the PMW3901 optical flow is plotted there from MAVROS.
"""
import cv2
import numpy as np

DEPTH_RANGE = (0.3, 10.0)       # m: colour-map span; closer than the start = red, beyond the end = blue

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


def confidence_to_bgr(data, width, height, step, encoding, size):
    """The ZED confidence map (32FC1, 0 = sure .. 100 = unsure) -> BGR colour map at size=(w, h): sure = blue, unsure = red, NaN = black."""
    if encoding != "32FC1":
        raise KeyError(encoding)
    c = np.frombuffer(data, np.float32).reshape(height, step // 4)[:, :width]
    c = cv2.resize(c, size, interpolation=cv2.INTER_NEAREST)
    norm = np.nan_to_num(np.clip(c / 100.0, 0.0, 1.0), nan=0.0, posinf=1.0, neginf=0.0)
    out = cv2.applyColorMap((norm * 255).astype(np.uint8), cv2.COLORMAP_TURBO)
    out[~np.isfinite(c)] = 0
    return out


def blank(size, text="no signal"):
    img = np.full((size[1], size[0], 3), 24, np.uint8)
    cv2.putText(img, text, (10, size[1] // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 160, 160), 1, cv2.LINE_AA)
    return img


def label(img, text):
    """Burn a small caption into the top-left corner (in place)."""
    cv2.putText(img, text, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(img, text, (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1, cv2.LINE_AA)
    return img


def grid(left, chase, depth, confidence):
    return np.vstack([np.hstack([left, chase]), np.hstack([depth, confidence])])
