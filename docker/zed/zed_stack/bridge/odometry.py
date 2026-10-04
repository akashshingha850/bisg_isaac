"""M1 — ZED positional tracking -> PX4 EKF2 external vision (MAVROS odometry/out).

zed/zed_node/odom (nav_msgs/Odometry, ENU/FLU) goes out unchanged in content on mavros/odometry/out; MAVROS converts it to
NED/FRD and sends MAVLink ODOMETRY. Differences from a plain relay, all on purpose:
  * silent while tracking is not OK (PosTrackStatus.odometry_status != OK) or the source is slower than min_rate_hz:
    PX4 must see silence, not stale or lost-track data, so its own vision timeout / failsafe acts (docs/zed-stack.md);
  * frame ids are the strings MAVROS' odometry plugin matches ("odom" / "base_link"), whatever the wrapper calls them;
  * restamp: true stamps the sample with this node's clock on arrival (capture time on the vehicle clock). In the sim PX4
    runs on /clock time while the wrapper stamps with the wall clock, so a source stamp would be a wrong measurement time.
Pose lever arm of the camera on the airframe: EKF2_EV_POS_X/Y/Z on the PX4 side.
"""
import copy
import math

from nav_msgs.msg import Odometry
from zed_msgs.msg import PosTrackStatus

from .common import DEGRADED, LOST, OK, RELIABLE_QOS, SENSOR_QOS, Module, Rate

ODOM_FRAME, BASE_FRAME = "odom", "base_link"


class Odometry2Px4(Module):
    name = "odometry"

    def __init__(self, node, ctx, settings):
        super().__init__(node, ctx, settings)
        self.restamp = settings["restamp"]
        self.min_rate = settings["min_rate_hz"]
        self.src, self.out = Rate(), Rate()
        self.track_ok = None            # None = no PosTrackStatus seen yet
        self.track_state = None
        self.lost_events = 0
        self.last_pos = None
        self.pub = node.create_publisher(Odometry, f"{ctx.mavros}/odometry/out", RELIABLE_QOS)
        node.create_subscription(Odometry, f"{ctx.zed}/odom", self.on_odom, SENSOR_QOS)
        node.create_subscription(PosTrackStatus, f"{ctx.zed}/pose/status", self.on_track, SENSOR_QOS)
        self.log(f"{ctx.zed}/odom -> {ctx.mavros}/odometry/out (restamp={self.restamp}, min rate {self.min_rate} Hz)")

    def on_track(self, msg):
        ok = msg.odometry_status == PosTrackStatus.OK
        if self.track_ok and not ok:
            self.lost_events += 1
            self.warn(f"tracking lost (odometry_status={msg.odometry_status}): odometry/out goes silent")
        elif ok and self.track_ok is False:
            self.log("tracking recovered")
        self.track_ok, self.track_state = ok, msg.odometry_status

    def sending(self):
        return self.track_ok is not False and self.src.hz() >= self.min_rate

    def on_odom(self, msg):
        self.src.tick()
        if self.track_ok is False or self.src.hz() < self.min_rate:
            return
        p = msg.pose.pose.position
        if not all(math.isfinite(v) for v in (p.x, p.y, p.z)):
            return
        out = copy.copy(msg)
        out.header = copy.copy(msg.header)
        out.header.frame_id, out.child_frame_id = ODOM_FRAME, BASE_FRAME
        if self.restamp:
            now = self.node.get_clock().now()
            if now.nanoseconds == 0:            # use_sim_time and no /clock yet: a 0 stamp would reach PX4
                return
            out.header.stamp = now.to_msg()
        self.pub.publish(out)
        self.out.tick()
        self.last_pos = (p.x, p.y, p.z)

    def status(self):
        detail = {"rate_hz": round(self.out.hz(), 1), "lost_events": self.lost_events}
        if self.src.age() > 2.0:
            return {"state": LOST, "detail": "no odometry from the ZED", **detail}
        if self.track_ok is False:
            return {"state": LOST, "detail": f"tracking lost (odometry_status={self.track_state}), not sending", **detail}
        if self.src.hz() < self.min_rate:
            return {"state": DEGRADED, "detail": f"source {self.src.hz():.1f} Hz < {self.min_rate} Hz, not sending", **detail}
        if self.track_ok is None:
            return {"state": DEGRADED, "detail": "no PosTrackStatus yet (pose/status), sending ungated", **detail}
        return {"state": OK, **detail}
