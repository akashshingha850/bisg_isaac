#!/usr/bin/env python3
"""ROS 2 image topics -> RTP/H.264 over UDP, for QGroundControl's "UDP h.264 Video Stream" source.

Minimal on purpose (docs/video-qgc.md): subscribers, one GStreamer pipeline
    appsrc ! videoconvert ! x264enc (or nvv4l2h264enc on a Jetson) ! rtph264pay ! udpsink
Two layouts (services.qgc_video.layout):
  grid    one 2x2 picture: left | right / depth | optical flow of the left image (zed_stack/mosaic.py). The four sources are
          sampled by a timer at `fps` (15 when 0), so a slow or dead topic only blanks its own tile. The two derived tiles are also
          published, while subscribed, as /drone_N/zed/video/optical_flow (bgr8, tile size). Depth is not republished: use the ZED's own depth/depth_registered.
  single  one raw sensor_msgs/Image topic as it comes (rgb8, bgr8, rgba8, bgra8, mono8): the ZED wrapper, a USB cam.

Settings: services.qgc_video in docker/zed/zed.yaml (layout, width, topic, host, port, bitrate, fps, encoder); the matching VIDEO_* env
variables (VIDEO_LAYOUT, VIDEO_TOPIC, VIDEO_HOST, VIDEO_PORT, VIDEO_BITRATE, VIDEO_FPS, VIDEO_ENCODER) override one run, e.g. `./bisg zed up --video-host IP`.
"""
import os
import signal
import sys
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from . import config, mosaic

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

# ROS encoding -> (GStreamer raw format, bytes per pixel)
FORMATS = {"rgb8": ("RGB", 3), "bgr8": ("BGR", 3), "rgba8": ("RGBA", 4), "bgra8": ("BGRA", 4), "mono8": ("GRAY8", 1)}


class VideoStream(Node):
    def __init__(self):
        super().__init__("video_stream")
        drone = os.environ.get("DRONE_ID", "1")
        cfg = config.load(sim=os.environ.get("ZED_STACK_SIM", "0") == "1").services()["qgc_video"]
        env = os.environ.get
        self.layout = env("VIDEO_LAYOUT") or cfg["layout"]
        base = f"/drone_{drone}/zed/zed_node/"
        self.topics = {"left": base + "left/color/rect/image", "right": base + "right/color/rect/image",
                       "depth": base + "depth/depth_registered"}
        self.topic = env("VIDEO_TOPIC") or cfg["topic"] or self.topics["left"]       # single layout only
        self.width = int(cfg["width"])
        self.host = env("VIDEO_HOST") or cfg["host"]
        self.port = int(env("VIDEO_PORT") or cfg["port"])
        self.bitrate = int(env("VIDEO_BITRATE") or cfg["bitrate"])
        self.cap = max(0.0, float(env("VIDEO_FPS") or cfg["fps"]))      # 0 = no limit: send every frame (grid: 15 per second)
        self.fps = self.cap or (15.0 if self.layout == "grid" else 30.0)   # nominal rate for caps and keyframe spacing
        self.encoder = env("VIDEO_ENCODER") or cfg["encoder"]
        self.pipeline = None
        self.src = None
        self.shape = None            # (width, height, ros encoding) the running pipeline was built for
        self.last_push = 0.0
        self.sent = 0
        Gst.init(None)
        if self.layout == "grid":
            self.flow = mosaic.Flow()
            self.latest = {}         # name -> [msg, arrival time, new since the last compose]
            self.tiles = {}          # name -> last decoded tile
            self.tile_wh = None
            for name, topic in self.topics.items():
                self.create_subscription(Image, topic, lambda m, n=name: self.on_source(n, m), qos_profile_sensor_data)
            # the optical-flow tile as a ROS image too (RViz): RELIABLE, so a BEST_EFFORT or RELIABLE subscriber both match
            self.pub = {"flow": self.create_publisher(Image, f"/drone_{drone}/zed/video/optical_flow", 2)}
            self.create_timer(1.0 / self.fps, self.compose)
            self.get_logger().info(f"2x2 {self.width}px (left|right / depth|flow of left) from {base} -> rtp/h264 udp://{self.host}:{self.port} "
                                   f"({self.bitrate} kbit/s, {self.fps:g} fps); QGC: Video > UDP h.264, port {self.port}")
        else:
            self.create_subscription(Image, self.topic, self.on_image, qos_profile_sensor_data)
            self.get_logger().info(f"{self.topic} -> rtp/h264 udp://{self.host}:{self.port} "
                                   f"({self.bitrate} kbit/s, {f"<= {self.cap:g} fps" if self.cap else "source rate"}); QGC: Video > UDP h.264, port {self.port}")
        self.create_timer(5.0, self.report)

    def encoder_chain(self):
        use_nv = self.encoder == "nvenc" or (self.encoder == "auto" and Gst.ElementFactory.find("nvv4l2h264enc"))
        if use_nv:   # Jetson hardware encoder
            return (f"nvvidconv ! video/x-raw(memory:NVMM),format=NV12 ! "
                    f"nvv4l2h264enc bitrate={self.bitrate * 1000} insert-sps-pps=true idrinterval={int(self.fps * 2)}")
        return (f"videoconvert ! video/x-raw,format=I420 ! x264enc tune=zerolatency speed-preset=ultrafast "
                f"bitrate={self.bitrate} key-int-max={int(self.fps * 2)} ! video/x-h264,profile=baseline")

    def build(self, width, height, encoding):
        self.stop_pipeline()
        fmt = FORMATS[encoding][0]
        desc = (f"appsrc name=src is-live=true format=time do-timestamp=true block=false max-buffers=2 leaky-type=2 "
                f"caps=video/x-raw,format={fmt},width={width},height={height},framerate={int(self.fps)}/1 ! "
                f"{self.encoder_chain()} ! rtph264pay config-interval=1 pt=96 ! "
                f"udpsink host={self.host} port={self.port} sync=false async=false")
        self.pipeline = Gst.parse_launch(desc)
        self.src = self.pipeline.get_by_name("src")
        self.pipeline.set_state(Gst.State.PLAYING)
        self.shape = (width, height, encoding)
        self.get_logger().info(f"pipeline up: {width}x{height} {encoding}")

    def stop_pipeline(self):
        if self.pipeline is not None:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = self.src = None

    def on_image(self, msg: Image):
        now = time.monotonic()
        if self.cap and now - self.last_push < 1.0 / self.cap:
            return
        if msg.encoding not in FORMATS:
            self.get_logger().error(f"unsupported encoding {msg.encoding!r} (need one of {sorted(FORMATS)})",
                                    throttle_duration_sec=10.0)
            return
        if self.shape != (msg.width, msg.height, msg.encoding):
            self.build(msg.width, msg.height, msg.encoding)
        bpp = FORMATS[msg.encoding][1]
        rows = np.frombuffer(msg.data, np.uint8).reshape(msg.height, msg.step)
        data = rows[:, :msg.width * bpp].tobytes()          # drop any row padding
        self.src.emit("push-buffer", Gst.Buffer.new_wrapped(data))
        self.last_push = now
        self.sent += 1

    # ---- grid layout
    def on_source(self, name, msg):
        self.latest[name] = [msg, time.monotonic(), True]

    def tile(self, name, decode, size, now):
        """The tile of one source: re-decoded when a new frame arrived, a 'no signal' blank when none came for 2 s."""
        entry = self.latest.get(name)
        if entry is None or now - entry[1] > 2.0:
            self.tiles.pop(name, None)
            return mosaic.blank(size)
        if entry[2] or name not in self.tiles:
            msg = entry[0]
            try:
                self.tiles[name] = decode(msg.data, msg.width, msg.height, msg.step, msg.encoding, size)
            except KeyError:
                self.get_logger().error(f"{name}: unsupported encoding {msg.encoding!r}", throttle_duration_sec=10.0)
                return mosaic.blank(size, f"encoding {msg.encoding}")
            entry[2] = False
            if name == "left":
                self.publish("flow", msg.header, self.flow.update(self.tiles["left"]))
        return self.tiles[name]

    def publish(self, name, header, bgr):
        """The optical-flow tile as a bgr8 sensor_msgs/Image with its source's header, only while somebody subscribes."""
        pub = self.pub[name]
        if pub.get_subscription_count() == 0:
            return
        out = Image()
        out.header = header
        out.height, out.width = bgr.shape[:2]
        out.encoding, out.step = "bgr8", out.width * 3
        out.data = np.ascontiguousarray(bgr).tobytes()
        pub.publish(out)

    def compose(self):
        now = time.monotonic()
        entry = self.latest.get("left")
        if entry is None:
            return                                   # the left image sets the tile aspect; report() warns while it is missing
        size = mosaic.tile_size(self.width, entry[0].width, entry[0].height)
        if size != self.tile_wh:
            self.tile_wh, self.tiles = size, {}
            self.flow = mosaic.Flow()
        left = self.tile("left", mosaic.to_bgr, size, now)
        right = self.tile("right", mosaic.to_bgr, size, now)
        depth = self.tile("depth", mosaic.depth_to_bgr, size, now)
        flow = self.flow.last if self.flow.last is not None and "left" in self.tiles else mosaic.blank(size)
        frame = np.ascontiguousarray(mosaic.grid(left, right, depth, flow))
        tw, th = size
        for text, x, y in (("left", 0, 0), ("right", tw, 0), (f"depth {mosaic.DEPTH_RANGE[0]:g}-{mosaic.DEPTH_RANGE[1]:g} m", 0, th), ("optical flow", tw, th)):
            mosaic.label(frame[y:y + th, x:x + tw], text)
        if self.shape != (2 * tw, 2 * th, "bgr8"):
            self.build(2 * tw, 2 * th, "bgr8")
        self.src.emit("push-buffer", Gst.Buffer.new_wrapped(frame.tobytes()))
        self.sent += 1

    def report(self):
        if self.layout == "grid":
            now = time.monotonic()
            live = [n for n, e in self.latest.items() if now - e[1] <= 2.0]
            dead = [n for n in self.topics if n not in live]
            if "left" not in live:
                self.get_logger().warn(f"no frames on {self.topics['left']} yet (is the sim/ZED publishing? ros2 topic hz ...)")
            else:
                note = f"; no signal: {', '.join(dead)} ({', '.join(self.topics[n] for n in dead)})" if dead else ""
                self.get_logger().info(f"streaming: {self.sent} frames in the last 5 s{note}")
        elif self.sent == 0:
            self.get_logger().warn(f"no frames on {self.topic} yet (is the sim/ZED publishing? ros2 topic hz {self.topic})")
        else:
            self.get_logger().info(f"streaming: {self.sent} frames in the last 5 s")
        self.sent = 0

    def destroy_node(self):
        self.stop_pipeline()
        super().destroy_node()


def main():
    rclpy.init()
    node = VideoStream()
    signal.signal(signal.SIGTERM, signal.default_int_handler)      # `compose stop` -> clean exit (PID 1)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
