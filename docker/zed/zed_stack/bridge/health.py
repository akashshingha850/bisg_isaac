"""M10 — ZED health -> one status topic + STATUSTEXT in QGroundControl.

Publishes zed_stack/status (std_msgs/String, JSON, 1 Hz): the state of the camera, depth, tracking and every enabled bridge
module. On a state change it sends a STATUSTEXT (mavros/statustext/send) so the operator sees "ZED: tracking LOST" in QGC and
it lands in the PX4 log. The other modules go silent on their own when their input is lost; this one tells people why.
"""
import json
import time

import numpy as np
from sensor_msgs.msg import Image
from std_msgs.msg import String
from zed_msgs.msg import HealthStatusStamped, PosTrackStatus

from mavros_msgs.msg import StatusText

from .common import DEGRADED, LOST, OFF, OK, SENSOR_QOS, Module, Rate

SEVERITY = {OK: StatusText.INFO, DEGRADED: StatusText.WARNING, LOST: StatusText.WARNING}


class Health(Module):
    name = "health"

    def __init__(self, node, ctx, settings, cfg):
        super().__init__(node, ctx, settings)
        self.timeout = settings["timeout_s"]
        self.depth_min_valid = settings["depth_min_valid"]
        self.cfg = cfg
        self.tracking_on = cfg.enabled("positional_tracking")
        self.depth_on = cfg.enabled("depth")
        self.camera = {"low_image_quality": False, "low_lighting": False, "low_depth_reliability": False,
                       "low_motion_sensors_reliability": False}
        self.heartbeat = Rate()
        self.track_status = None
        self.depth_rate, self.depth_valid = Rate(), None
        self.last_state = {}
        self.pub = node.create_publisher(String, f"{ctx.ns}/zed_stack/status", 1)
        self.text_pub = node.create_publisher(StatusText, f"{ctx.mavros}/statustext/send", 10)
        node.create_subscription(HealthStatusStamped, f"{ctx.zed}/status/health", self.on_health, SENSOR_QOS)
        node.create_subscription(PosTrackStatus, f"{ctx.zed}/pose/status", self.on_track, SENSOR_QOS)
        if self.depth_on and self.depth_min_valid > 0:
            node.create_subscription(Image, f"{ctx.zed}/depth/depth_registered", self.on_depth, SENSOR_QOS)
        node.create_timer(1.0, self.tick)
        ctx.notify = self.notify
        self.log(f"-> {ctx.ns}/zed_stack/status, STATUSTEXT on {ctx.mavros}/statustext/send")

    def notify(self, severity, text):
        msg = StatusText()
        msg.severity, msg.text = severity, text[:50]
        self.text_pub.publish(msg)
        self.log(text)

    def on_health(self, msg):
        self.heartbeat.tick()
        for k in self.camera:
            self.camera[k] = bool(getattr(msg, k))

    def on_track(self, msg):
        self.track_status = msg.odometry_status

    def on_depth(self, msg):
        self.depth_rate.tick()
        if self.depth_rate.hz() > 3.0 or msg.encoding != "32FC1":    # sample, do not burn CPU on every frame
            return
        z = np.frombuffer(msg.data, np.float32).reshape(msg.height, msg.width)[::8, ::8]
        self.depth_valid = float(np.isfinite(z).mean())

    # ---- component states
    def camera_state(self):
        if self.heartbeat.age() > self.timeout:
            return {"state": LOST, "detail": "no status/health from the wrapper"}
        bad = [k for k, v in self.camera.items() if v]
        return {"state": DEGRADED, "detail": ", ".join(bad)} if bad else {"state": OK}

    def depth_state(self):
        if not self.depth_on:
            return {"state": OFF}
        if self.depth_valid is None:
            return {"state": DEGRADED, "detail": "no depth frame yet"} if self.depth_min_valid > 0 else {"state": OK}
        if self.depth_rate.age() > self.timeout:
            return {"state": LOST, "detail": "no depth frames"}
        if self.depth_valid < self.depth_min_valid:
            return {"state": DEGRADED, "detail": f"{self.depth_valid:.0%} valid pixels", "valid": round(self.depth_valid, 2)}
        return {"state": OK, "valid": round(self.depth_valid, 2)}

    def tracking_state(self):
        if not self.tracking_on:
            return {"state": OFF}
        if self.track_status is None:
            return {"state": LOST, "detail": "no pose/status"}
        return {"state": OK} if self.track_status == PosTrackStatus.OK else {"state": LOST, "detail": f"odometry_status={self.track_status}"}

    def tick(self):
        comps = {"camera": self.camera_state(), "depth": self.depth_state(), "tracking": self.tracking_state()}
        for name, mod in self.ctx.modules.items():
            if mod is not self:
                comps[name] = mod.status()
        for name, st in comps.items():
            prev = self.last_state.get(name)
            if prev is not None and st["state"] != prev and OFF not in (st["state"], prev) and name in ("camera", "depth", "tracking"):
                label = "OK" if st["state"] == OK else st["state"].upper()
                self.notify(SEVERITY.get(st["state"], StatusText.INFO), f"ZED {name}: {label}" + (f" ({st['detail']})" if st.get("detail") else ""))
            self.last_state[name] = st["state"]
        worst = max((s["state"] for s in comps.values()), key=[OFF, OK, DEGRADED, LOST].index)
        self.pub.publish(String(data=json.dumps({"t": round(time.time(), 1), "state": worst, "components": comps})))

    def status(self):
        return {"state": OK}
