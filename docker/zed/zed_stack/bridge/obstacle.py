"""M2 — ZED depth image -> PX4's 72-sector obstacle map (MAVROS obstacle/send -> MAVLink OBSTACLE_DISTANCE).

PX4 keeps a 72 x 5 deg obstacle map in the body frame. This fills it from the depth image:
  1. keep pixels whose height above/below the camera is within +-band metres (the drone's own height band),
  2. per image column take the nearest valid depth Z; horizontal distance = Z / cos(azimuth),
  3. bin by azimuth into 5 deg sectors, nearest wins; sectors inside the camera's FOV with nothing in range are "free"
     (max_range + 1 cm), sectors outside the FOV "unknown" (inf -> UINT16_MAX).
Sent as sensor_msgs/LaserScan on mavros/obstacle/send, clockwise from forward (FRD), with the plugin's `mav_frame` set to
BODY_FRD (MAVROS defaults it to GLOBAL). With CP_DIST > 0 PX4's collision prevention (Position mode) stops the drone short of
what the camera sees and streams the fused map to the GCS, where QGroundControl draws the proximity radar.
"""
import math
import time

import numpy as np
from rcl_interfaces.msg import Parameter, ParameterType, ParameterValue
from rcl_interfaces.srv import SetParameters
from sensor_msgs.msg import CameraInfo, Image, LaserScan

from .common import DEGRADED, LOST, OK, SENSOR_QOS, Module, Rate
from .sectors import BINS, INC_DEG, START_DEG, sectors_from_depth

class ObstacleDistance(Module):
    name = "obstacle_distance"

    def __init__(self, node, ctx, settings):
        super().__init__(node, ctx, settings)
        self.band, self.rmin, self.rmax = settings["band"], settings["min_range"], settings["max_range"]
        self.interval = 1.0 / max(settings["rate_hz"], 0.5)
        self.info = None
        self.last = 0.0
        self.out = Rate(5.0)
        self.nearest = math.inf
        self.frame_set = False
        self.pub = node.create_publisher(LaserScan, f"{ctx.mavros}/obstacle/send", 10)
        node.create_subscription(CameraInfo, f"{ctx.zed}/left/color/rect/camera_info", self.on_info, SENSOR_QOS)
        node.create_subscription(Image, f"{ctx.zed}/depth/depth_registered", self.on_depth, SENSOR_QOS)
        node.create_timer(2.0, self.set_frame)
        self.log(f"depth -> {ctx.mavros}/obstacle/send (band +-{self.band} m, {self.rmin}-{self.rmax} m, {settings['rate_hz']} Hz)")

    def on_info(self, msg):
        if self.info is None:
            self.info = (msg.k[0], msg.k[4], msg.k[2], msg.k[5])      # fx fy cx cy

    def set_frame(self):
        """MAVROS defaults the obstacle plugin to GLOBAL; ours is a body-frame (FRD) scan."""
        if self.frame_set:
            return
        cli = self.node.create_client(SetParameters, f"{self.ctx.mavros}/obstacle/set_parameters")
        if not cli.wait_for_service(timeout_sec=0.1):
            return
        p = Parameter(name="mav_frame", value=ParameterValue(type=ParameterType.PARAMETER_STRING, string_value="BODY_FRD"))

        def done(fut):
            r = fut.result()
            if r is not None and all(x.successful for x in r.results):
                self.frame_set = True
                self.log("MAVROS obstacle plugin: mav_frame = BODY_FRD")
        cli.call_async(SetParameters.Request(parameters=[p])).add_done_callback(done)

    def on_depth(self, msg: Image):
        now = time.monotonic()
        if self.info is None or now - self.last < self.interval or msg.encoding != "32FC1":
            return
        self.last = now
        z = np.frombuffer(msg.data, np.float32).reshape(msg.height, msg.width)
        ranges = sectors_from_depth(z, *self.info, self.band, self.rmin, self.rmax)
        scan = LaserScan()
        scan.header.stamp, scan.header.frame_id = msg.header.stamp, "base_link_frd"
        scan.angle_min = math.radians(START_DEG)
        scan.angle_increment = math.radians(INC_DEG)
        scan.angle_max = scan.angle_min + scan.angle_increment * (BINS - 1)
        scan.range_min, scan.range_max = self.rmin, self.rmax
        scan.ranges = ranges.tolist()
        self.pub.publish(scan)
        self.out.tick()
        self.nearest = float(min(self.nearest, np.min(ranges[ranges <= self.rmax], initial=np.inf)))

    def status(self):
        if self.out.age() > 3.0:
            return {"state": LOST, "detail": "no depth frames" if self.info else "no camera_info"}
        near = f"{self.nearest:.2f} m" if math.isfinite(self.nearest) else "none in range"
        self.nearest = math.inf
        if not self.frame_set:
            return {"state": DEGRADED, "detail": "mav_frame not set: is MAVROS up?", "rate_hz": round(self.out.hz(), 1)}
        return {"state": OK, "rate_hz": round(self.out.hz(), 1), "nearest": near}
