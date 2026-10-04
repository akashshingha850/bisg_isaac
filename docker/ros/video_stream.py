#!/usr/bin/env python3
"""ROS 2 image topic -> RTP/H.264 over UDP, for QGroundControl's "UDP h.264 Video Stream" source.

Minimal on purpose (docs/video-qgc.md): one subscriber, one GStreamer pipeline
    appsrc ! videoconvert ! x264enc (or nvv4l2h264enc on a Jetson) ! rtph264pay ! udpsink
Works for any raw sensor_msgs/Image (rgb8, bgr8, rgba8, bgra8, mono8): the ZED wrapper, the sim's ZED rig, a USB cam.

Settings (env, set from config/bisg.conf by compose): VIDEO_TOPIC, VIDEO_HOST, VIDEO_PORT, VIDEO_BITRATE (kbit/s),
VIDEO_FPS (max rate, 0 = pass every frame), VIDEO_ENCODER (auto | x264 | nvenc).
"""
import os
import sys
import time

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

# ROS encoding -> (GStreamer raw format, bytes per pixel)
FORMATS = {"rgb8": ("RGB", 3), "bgr8": ("BGR", 3), "rgba8": ("RGBA", 4), "bgra8": ("BGRA", 4), "mono8": ("GRAY8", 1)}


class VideoStream(Node):
    def __init__(self):
        super().__init__("video_stream")
        drone = os.environ.get("DRONE_ID", "1")
        self.topic = os.environ.get("VIDEO_TOPIC") or f"/drone_{drone}/zed/zed_node/left/color/rect/image"
        self.host = os.environ.get("VIDEO_HOST", "127.0.0.1")
        self.port = int(os.environ.get("VIDEO_PORT", "5600"))
        self.bitrate = int(os.environ.get("VIDEO_BITRATE", "2000"))
        self.cap = max(0.0, float(os.environ.get("VIDEO_FPS", "0")))   # 0 = no limit: send every frame
        self.fps = self.cap or 30.0          # nominal rate for caps and keyframe spacing
        self.encoder = os.environ.get("VIDEO_ENCODER", "auto")
        self.pipeline = None
        self.src = None
        self.shape = None            # (width, height, ros encoding) the running pipeline was built for
        self.last_push = 0.0
        self.sent = 0
        Gst.init(None)
        self.create_subscription(Image, self.topic, self.on_image, qos_profile_sensor_data)
        self.create_timer(5.0, self.report)
        self.get_logger().info(f"{self.topic} -> rtp/h264 udp://{self.host}:{self.port} "
                               f"({self.bitrate} kbit/s, {f"<= {self.cap:g} fps" if self.cap else "source rate"}); QGC: Video > UDP h.264, port {self.port}")

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

    def report(self):
        if self.sent == 0:
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
