"""M1 — ZED positional tracking -> PX4 EKF2 external vision (MAVROS odometry/out).

zed/zed_node/odom (nav_msgs/Odometry, ENU/FLU) goes out unchanged in content on mavros/odometry/out; MAVROS converts it to
NED/FRD and sends MAVLink ODOMETRY. Differences from a plain relay, all on purpose:
  * silent while tracking is not OK (PosTrackStatus.odometry_status != OK) or the source is slower than min_rate_hz:
    PX4 must see silence, not stale or lost-track data, so its own vision timeout / failsafe acts (docs/zed-stack.md);
  * frame ids are the strings MAVROS' odometry plugin matches ("odom" / "base_link"), whatever the wrapper calls them;
  * restamp: true stamps the sample with this node's clock on arrival, minus restamp_latency_ms (the camera->bridge latency), so
    the stamp is the capture time on the vehicle clock. In the sim PX4 runs on /clock time while the wrapper stamps with the
    wall clock, so a source stamp would be a wrong measurement time; without the latency EKF2 fuses every sample late (B17).
  * jump_gate: true removes the pose jumps and yaw slips the ZED produces in rare tracking events (jumpgate.py). Detection compares
    the ZED's relative motion over 0.4 s with the flight controller's own (mavros local_position/pose: EKF2, independent of the ZED
    over such a window); removal re-anchors the trajectory so EKF2 sees it continuous. Off by default: switch on per scenario in
    docker/zed/zed.yaml and check with `./bisg vio check` (docs/vio.md). Valid within the calibrated yaw-rate cap (MC_YAWRATE_MAX 60).
  * jump_inject_*: TEST ONLY. Adds a permanent pose jump / yaw slip to the ZED stream at a given time, as an SDK event would, so the
    gate can be checked end to end in the sim (docs/vio.md). Zero = off.
Pose lever arm of the camera on the airframe: EKF2_EV_POS_X/Y/Z on the PX4 side.
"""
import copy
import math

import rclpy.duration
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from zed_msgs.msg import PosTrackStatus

from .common import DEGRADED, LOST, OK, RELIABLE_QOS, SENSOR_QOS, Module, Rate
from .jumpgate import JumpGate, qmul, qrot

ODOM_FRAME, BASE_FRAME = "odom", "base_link"


class Odometry2Px4(Module):
    name = "odometry"

    def __init__(self, node, ctx, settings):
        super().__init__(node, ctx, settings)
        self.restamp = settings["restamp"]
        self.latency_ns = int(float(settings.get("restamp_latency_ms", 0.0)) * 1e6)   # restamp: arrival - camera->here latency
        self.min_rate = settings["min_rate_hz"]
        self.src, self.out = Rate(), Rate()
        self.track_ok = None            # None = no PosTrackStatus seen yet
        self.track_state = None
        self.lost_events = 0
        self.last_pos = None
        self.gate = None
        if settings.get("jump_gate"):
            self.gate = JumpGate(settings.get("jump_pos_thresh_m", 0.25), settings.get("jump_rot_thresh_deg", 7.5),
                                 window_s=settings.get("jump_window_s", 0.4))
            node.create_subscription(PoseStamped, f"{ctx.mavros}/local_position/pose", self.on_ekf_pose, SENSOR_QOS)
        self.inject = (float(settings.get("jump_inject_at_s", 0.0)), float(settings.get("jump_inject_m", 0.0)),
                       float(settings.get("jump_inject_yaw_deg", 0.0)))
        self.t_first, self.injected, self.inject_p0 = None, False, None
        self.pub = node.create_publisher(Odometry, f"{ctx.mavros}/odometry/out", RELIABLE_QOS)
        node.create_subscription(Odometry, f"{ctx.zed}/odom", self.on_odom, SENSOR_QOS)
        node.create_subscription(PosTrackStatus, f"{ctx.zed}/pose/status", self.on_track, SENSOR_QOS)
        self.log(f"{ctx.zed}/odom -> {ctx.mavros}/odometry/out (restamp={self.restamp}{f' -{self.latency_ns / 1e6:g} ms' if self.restamp and self.latency_ns else ''}, min rate {self.min_rate} Hz"
                 f"{', jump gate on' if self.gate else ''}{f', TEST: injecting {self.inject[1]} m / {self.inject[2]} deg at +{self.inject[0]:g} s' if self.inject[1] or self.inject[2] else ''})")

    def on_ekf_pose(self, msg):
        p, o = msg.pose.position, msg.pose.orientation
        self.gate.witness(msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9, (p.x, p.y, p.z), (o.x, o.y, o.z, o.w))

    def _inject(self, t, p, q):
        """TEST ONLY: from `jump_inject_at_s` after the first sample, a permanent x offset and yaw slip in the raw ZED pose."""
        at, dx, dyaw = self.inject
        if not (dx or dyaw):
            return p, q
        if self.t_first is None:
            self.t_first = t
        if not self.injected and t - self.t_first >= at:
            self.injected, self.inject_p0 = True, p
            self.warn(f"TEST: injecting a {dx} m jump and a {dyaw} deg yaw slip into the ZED odometry")
        if not self.injected:
            return p, q
        h = math.radians(dyaw) / 2
        rz = (0.0, 0.0, math.sin(h), math.cos(h))
        rel = qrot(rz, tuple(a - b for a, b in zip(p, self.inject_p0)))         # later motion is turned by the slip, as a real one does
        return tuple(b + r + (dx if k == 0 else 0.0) for k, (b, r) in enumerate(zip(self.inject_p0, rel))), qmul(rz, q)

    def gated(self, out, t):
        """Run the jump gate on `out` (a copy of the source message, stamped t) in place."""
        o, pp = out.pose.pose.orientation, out.pose.pose.position
        p, q, jump = self.gate.step(t, (pp.x, pp.y, pp.z), (o.x, o.y, o.z, o.w))
        out.pose = copy.deepcopy(out.pose)
        out.pose.pose.position.x, out.pose.pose.position.y, out.pose.pose.position.z = p
        out.pose.pose.orientation.x, out.pose.pose.orientation.y, out.pose.pose.orientation.z, out.pose.pose.orientation.w = q
        if jump:
            ev = self.gate.last_eval
            self.warn(f"pose jump removed: {jump['d']:.2f} m, {jump['deg']:.1f} deg (ZED vs flight controller over "
                      f"{self.gate.window_s:g} s: {ev[0]:.2f} m, {ev[1]:.1f} deg)")

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
            stamp = now - rclpy.duration.Duration(nanoseconds=self.latency_ns)
            out.header.stamp = stamp.to_msg()
            t = stamp.nanoseconds * 1e-9        # the same clock as the flight controller's stamps: what the gate compares against
        else:
            t = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        if self.inject[1] or self.inject[2]:
            o = out.pose.pose.orientation
            pi, qi = self._inject(t, (p.x, p.y, p.z), (o.x, o.y, o.z, o.w))
            out.pose = copy.deepcopy(out.pose)
            out.pose.pose.position.x, out.pose.pose.position.y, out.pose.pose.position.z = pi
            out.pose.pose.orientation.x, out.pose.pose.orientation.y, out.pose.pose.orientation.z, out.pose.pose.orientation.w = qi
        if self.gate:
            self.gated(out, t)
        self.pub.publish(out)
        self.out.tick()
        self.last_pos = (p.x, p.y, p.z)

    def status(self):
        detail = {"rate_hz": round(self.out.hz(), 1), "lost_events": self.lost_events}
        if self.gate:
            c_m, c_deg = self.gate.correction()
            detail["jump_gate"] = {"jumps": self.gate.jumps, "removed_m": round(self.gate.removed_m, 2),
                                   "removed_deg": round(self.gate.removed_deg, 1), "offset_m": round(c_m, 2),
                                   "offset_deg": round(c_deg, 1), "bypassed": self.gate.bypassed, "tripped": self.gate.tripped}
        if self.src.age() > 2.0:
            return {"state": LOST, "detail": "no odometry from the ZED", **detail}
        if self.track_ok is False:
            return {"state": LOST, "detail": f"tracking lost (odometry_status={self.track_state}), not sending", **detail}
        if self.src.hz() < self.min_rate:
            return {"state": DEGRADED, "detail": f"source {self.src.hz():.1f} Hz < {self.min_rate} Hz, not sending", **detail}
        if self.gate and self.gate.tripped:
            return {"state": DEGRADED, "detail": "jump gate tripped: its accumulated correction became implausible, it is off until restart", **detail}
        if self.gate and self.gate.bypassed:
            return {"state": DEGRADED, "detail": "jump gate fired too often: bypassed (the flight controller and the odometry disagree)", **detail}
        if self.track_ok is None:
            return {"state": DEGRADED, "detail": "no PosTrackStatus yet (pose/status), sending ungated", **detail}
        return {"state": OK, **detail}
