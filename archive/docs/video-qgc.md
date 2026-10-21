# ZED video in QGroundControl

`./bisg video up` streams a ROS 2 image topic (default: the drone's ZED left image) to QGroundControl as
RTP/H.264 over UDP. Same command and image in the sim and on the Jetson.

## Use

```
./bisg up && ./bisg zed up          # or ZED_SOURCE=emulated: the sim publishes the same topic
./bisg video up                     # drone 1, /drone_1/zed/zed_node/left/color/rect/image -> udp://127.0.0.1:5600
```

One-time in QGC: **Application Settings → Video → Video Source = "UDP h.264 Video Stream", UDP Port = 5600**
(QGC remembers it). The video appears in the Fly view.

| Command | |
|---|---|
| `./bisg video up [--drone N] [--topic T] [--host IP] [--port P]` | start (any raw `sensor_msgs/Image`: rgb8, bgr8, rgba8, bgra8, mono8) |
| `./bisg video logs` | frames/s heartbeat every 5 s; warns when the topic is silent |
| `./bisg video test` | host-side GStreamer player on the port, to check the stream without QGC (close QGC's video first: one receiver per port) |
| `./bisg video down` | stop |

Settings (`config/bisg.conf`, "Video to QGroundControl"): `VIDEO_TOPIC`, `VIDEO_HOST`, `VIDEO_PORT`, `VIDEO_BITRATE`
(kbit/s), `VIDEO_FPS` (max, 0 = every frame). Remote QGC: `VIDEO_HOST=<laptop LAN/VPN IP>` (UDP, so not an SSH tunnel).
Second drone: `./bisg video up --drone 2 --port 5601`.

## What exists, and why this is a 100-line script

Looked at (2026-10):
- [maladzenkau/image2rtsp](https://github.com/maladzenkau/image2rtsp) (BSD-3, Humble only, C++ RTSP server, no Docker)
  and [mkassimi98/ros2_gst_video_bridge](https://github.com/mkassimi98/ros2_gst_video_bridge) (AGPL, Humble-validated only)
  do the same job but are not validated on Jazzy / Ubuntu 24.04 and bring a colcon build each.
- [mavlink-camera-manager](https://github.com/mavlink/mavlink-camera-manager) serves RTSP plus the MAVLink camera
  protocol (QGC auto-discovers the stream) but its sources are V4L2/RTSP/test patterns, not ROS topics.
- The ZED SDK / `zed_wrapper` has no QGC-compatible output (its streaming module is ZED-SDK-to-ZED-SDK only).

So `docker/ros/video_stream.py` is a minimal rclpy node: `appsrc ! x264enc ! rtph264pay ! udpsink`, in the existing
`bisg/ros` image (GStreamer added to `docker/ros/Dockerfile`). On a Jetson it picks `nvv4l2h264enc` automatically
(`VIDEO_ENCODER=auto|x264|nvenc`; the nvenc path is not hardware-tested yet).

## Limits / next step
- QGC must be told the source once (above). Auto-discovery needs the MAVLink camera protocol (CAMERA_INFORMATION +
  VIDEO_STREAM_INFORMATION from a camera component); not implemented.
- Colour image only. Depth would need colourising first.
- Latency is mostly the x264 `zerolatency` encode plus QGC's jitter buffer; expect a few hundred ms.

## Speed: what limits the frame rate (measured 2026-10-04, single_iris, HD720 rgb8)
- The sim camera publishes ~17 fps (render rate x real-time factor). The stream now carries all of it (was ~9-12 fps
  with a 15 fps cap, because the sim delivers frames in bursts and a minimum-gap limiter drops the second of a pair).
- x264 `ultrafast` at 2 Mbit/s costs ~15 % of one CPU core, so the encoder is not the bottleneck on the workstation;
  NVENC would only free that core and take GPU time from Isaac. Isaac ROS / NITROS zero-copy does not apply either:
  the frames come from Isaac Sim / the ZED wrapper as ordinary DDS `sensor_msgs/Image`.
- On the Jetson the hardware encoder (`nvv4l2h264enc`, picked automatically) is what keeps the Orin NX CPU free.
