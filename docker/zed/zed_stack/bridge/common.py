"""Shared pieces of the bridge modules (rclpy only where a function needs a node)."""
import time
from collections import deque

from rclpy.qos import QoSProfile, ReliabilityPolicy, qos_profile_sensor_data

SENSOR_QOS = qos_profile_sensor_data
RELIABLE_QOS = QoSProfile(depth=10, reliability=ReliabilityPolicy.RELIABLE)   # MAVROS plugins subscribe reliable

# module states, worst last
OK, DEGRADED, LOST, OFF = "ok", "degraded", "lost", "off"


class Rate:
    """Messages per second over a sliding window, and how long ago the last one came (monotonic clock)."""

    def __init__(self, window=2.0):
        self.window = window
        self.stamps = deque()

    def tick(self):
        now = time.monotonic()
        self.stamps.append(now)
        self._trim(now)

    def _trim(self, now):
        while self.stamps and now - self.stamps[0] > self.window:
            self.stamps.popleft()

    def hz(self):
        now = time.monotonic()
        self._trim(now)
        return len(self.stamps) / self.window

    def age(self):
        return time.monotonic() - self.stamps[-1] if self.stamps else float("inf")


class Module:
    """Base of a bridge module. `status()` is polled once a second by the health module and published as JSON."""
    name = "module"

    def __init__(self, node, ctx, settings):
        self.node, self.ctx, self.cfg = node, ctx, settings

    def status(self):
        return {"state": OK}

    def log(self, msg):
        self.node.get_logger().info(f"[{self.name}] {msg}")

    def warn(self, msg):
        self.node.get_logger().warn(f"[{self.name}] {msg}")


class Context:
    """What every module needs to know: namespaces and a way to reach the others."""

    def __init__(self, drone_id, sim):
        self.drone_id = drone_id
        self.ns = f"/drone_{drone_id}"
        self.zed = f"{self.ns}/zed/zed_node"
        self.mavros = f"{self.ns}/mavros"
        self.sim = sim
        self.modules = {}
        self.notify = lambda severity, text: None       # set by the health module: STATUSTEXT to PX4/QGC
