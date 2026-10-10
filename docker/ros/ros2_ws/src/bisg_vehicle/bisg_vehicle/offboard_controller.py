"""OffboardController — fly drone N through MAVROS from Python (docs/interface-contract.md, mavros-ops skill).

The OFFBOARD state machine as blocking calls, so a mission reads top to bottom and runs unchanged in the sim and on the drone:

    c = OffboardController(node, "/drone_1")
    c.wait_ready() and c.takeoff(2.0) and c.goto(5.0, 0.0) and c.land()

Positions are ENU metres relative to the pose at wait_ready() (setpoints in `map`; MAVROS converts to PX4's NED). Every call
returns a Result (truthy when it worked, `.what` says why not) and never raises on a refusal.

land("auto")     AUTO.LAND, then wait for the disarm. Needs a global position (GPS): GPS-denied, PX4 plans the landing in
                 lat/lon and flies off towards 0,0 (tests/vio_flight.py docstring).
land("offboard") stay in OFFBOARD and command a descent VELOCITY until the land detector reports ON_GROUND, then disarm. The only
                 safe landing GPS-denied; a position setpoint below the ground never triggers the land detector.

Time: in the sim the node must run on /clock (`use_sim_time`); wall-clock waits here are multiplied by `patience` for a slow sim.
"""
import math
import time
from dataclasses import dataclass

import rclpy
from geometry_msgs.msg import PoseStamped
from mavros_msgs.msg import ExtendedState, PositionTarget, State
from mavros_msgs.srv import CommandBool, SetMode
from rclpy.qos import qos_profile_sensor_data

SETPOINT_HZ = 20.0          # PX4 leaves OFFBOARD below ~2 Hz
REACHED_M = 0.25


@dataclass
class Result:
    ok: bool
    what: str = ""

    def __bool__(self):
        return self.ok


class OffboardController:
    def __init__(self, node, ns, patience=1.0, log=print):
        self.node, self.ns, self.patience, self.log = node, ns.rstrip("/"), patience, log
        self.state, self.ext, self.pose = State(), ExtendedState(), None
        self.origin = None                                  # ENU position at wait_ready()
        self.modes = []                                     # every mode PX4 reported, in order (missions check transitions)
        self.sp = PoseStamped()
        self.sp.header.frame_id = "map"
        self.sp.pose.orientation.w = 1.0
        self.descend = None                                 # m/s down: stream a velocity setpoint instead of self.sp
        self.streaming = False
        m = f"{self.ns}/mavros"
        node.create_subscription(State, f"{m}/state", self._on_state, 10)
        node.create_subscription(ExtendedState, f"{m}/extended_state", self._on_ext, 10)
        node.create_subscription(PoseStamped, f"{m}/local_position/pose", self._on_pose, qos_profile_sensor_data)
        self.pub_sp = node.create_publisher(PoseStamped, f"{m}/setpoint_position/local", 10)
        self.pub_raw = node.create_publisher(PositionTarget, f"{m}/setpoint_raw/local", 10)
        self.cli_mode = node.create_client(SetMode, f"{m}/set_mode")
        self.cli_arm = node.create_client(CommandBool, f"{m}/cmd/arming")
        node.create_timer(1.0 / SETPOINT_HZ, self._stream)

    # --- callbacks ------------------------------------------------------------------------------------------------
    def _on_state(self, m):
        if not self.modes or self.modes[-1] != m.mode:
            self.modes.append(m.mode)
        self.state = m

    def _on_ext(self, m):
        self.ext = m

    def _on_pose(self, m):
        p = m.pose.position
        self.pose = (p.x, p.y, p.z)

    def _stream(self):
        if not self.streaming:
            return
        stamp = self.node.get_clock().now().to_msg()
        if self.descend is None:
            self.sp.header.stamp = stamp
            self.pub_sp.publish(self.sp)
            return
        t = PositionTarget()
        t.header.stamp = stamp
        t.coordinate_frame = PositionTarget.FRAME_LOCAL_NED   # MAVROS takes ENU values and converts
        t.type_mask = (PositionTarget.IGNORE_PX | PositionTarget.IGNORE_PY | PositionTarget.IGNORE_PZ
                       | PositionTarget.IGNORE_AFX | PositionTarget.IGNORE_AFY | PositionTarget.IGNORE_AFZ
                       | PositionTarget.IGNORE_YAW_RATE)
        t.velocity.z = -self.descend
        self.pub_raw.publish(t)

    # --- plumbing -------------------------------------------------------------------------------------------------
    def spin_for(self, seconds):
        end = time.time() + seconds
        while time.time() < end:
            rclpy.spin_once(self.node, timeout_sec=0.05)

    def wait_for(self, cond, seconds, what):
        end = time.time() + seconds * self.patience
        while time.time() < end:
            rclpy.spin_once(self.node, timeout_sec=0.05)
            if cond():
                return Result(True, what)
        return Result(False, f"timeout waiting for {what}")

    def _call(self, cli, req, timeout=10.0):
        if not cli.wait_for_service(timeout_sec=timeout):
            return None
        fut = cli.call_async(req)
        rclpy.spin_until_future_complete(self.node, fut, timeout_sec=timeout)
        return fut.result()

    def _set_sp(self, x, y, z):
        o = self.origin
        self.sp.pose.position.x, self.sp.pose.position.y, self.sp.pose.position.z = o[0] + x, o[1] + y, o[2] + z

    # --- the API --------------------------------------------------------------------------------------------------
    def wait_ready(self, timeout=60.0):
        """MAVROS connected and a local position estimate flowing; fixes the mission origin."""
        r = self.wait_for(lambda: self.state.connected and self.pose is not None, timeout,
                          f"{self.ns}/mavros connected + local_position")
        if r:
            self.spin_for(1.0)
            self.origin = self.pose
            self.log(f"ready: origin {[round(v, 2) for v in self.origin]} mode {self.state.mode}")
        return r

    def set_mode(self, mode):
        r = self._call(self.cli_mode, SetMode.Request(custom_mode=mode))
        if not (r and r.mode_sent):
            return Result(False, f"set_mode {mode} not sent")
        return self.wait_for(lambda: self.state.mode == mode, 10.0, f"mode {mode}")

    def arm(self, value=True):
        r = self._call(self.cli_arm, CommandBool.Request(value=value))
        if not (r and r.success):
            return Result(False, f"{'arming' if value else 'disarming'} refused (result {getattr(r, 'result', None)})")
        return self.wait_for(lambda: self.state.armed == value, 10.0, "armed" if value else "disarmed")

    def takeoff(self, alt):
        """Stream a hover setpoint `alt` m above the origin, switch to OFFBOARD, arm, wait until there."""
        self._set_sp(0.0, 0.0, alt)
        self.descend, self.streaming = None, True
        self.spin_for(1.5)                                  # PX4 accepts OFFBOARD only once setpoints are flowing
        return self.set_mode("OFFBOARD") and self.arm(True) and self.goto(0.0, 0.0, alt, settle=2.0)

    def goto(self, x, y, z=None, settle=1.0, timeout=60.0):
        """Fly to (x, y, z) m from the origin (z None = keep the current setpoint height); done once the drone has stayed
        within REACHED_M of it for `settle` s (passing through it at speed does not count)."""
        o = self.origin
        self._set_sp(x, y, self.sp.pose.position.z - o[2] if z is None else z)
        target = (self.sp.pose.position.x, self.sp.pose.position.y, self.sp.pose.position.z)
        inside, closest = [None], [math.inf]                # wall time the drone entered the ball (None = outside), min distance

        def settled():
            d = math.inf if self.pose is None else math.dist(self.pose, target)
            closest[0] = min(closest[0], d)
            if d >= REACHED_M:
                inside[0] = None
                return False
            inside[0] = inside[0] or time.time()
            return time.time() - inside[0] >= settle

        r = self.wait_for(settled, timeout, f"setpoint ({x:.1f}, {y:.1f}, {self.sp.pose.position.z - o[2]:.1f})")
        if not r:
            r.what += f" (closest {closest[0]:.2f} m, last error {[round(p - t, 2) for p, t in zip(self.pose, target)]})"
        if r:
            self.log(f"reached ({x:.1f}, {y:.1f}) est {[round(v - b, 2) for v, b in zip(self.pose, o)]}")
        return r

    def land(self, mode="auto", timeout=90.0):
        if mode == "auto":
            r = self.set_mode("AUTO.LAND")
            self.streaming = False
            return r and self.wait_for(lambda: not self.state.armed, timeout, "disarm after AUTO.LAND")
        self.descend = 0.5
        r = self.wait_for(lambda: self.ext.landed_state == ExtendedState.LANDED_STATE_ON_GROUND, timeout,
                          "land detector ON_GROUND")
        r = r and self.arm(False)
        self.streaming = False
        return r
