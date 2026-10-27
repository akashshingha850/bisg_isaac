"""
OFFBOARD takeoff and landing over raw MAVLink (pymavlink), for the tests that talk to PX4 without MAVROS (smoke_takeoff.py,
hover_stability.py). Needs only a local position (LOCAL_POSITION_NED), so it works with GPS and GPS-denied alike; PX4's
AUTO.TAKEOFF / AUTO.LAND need a global position and refuse without GPS (the sim default is GPS-denied since 2026-10-15,
docker/sim/px4/raptor.params). Same sequence as tests/vio_flight.py over MAVROS:
  stream a setpoint -> OFFBOARD -> arm -> climb to `alt` above the start -> ... -> descend with a velocity setpoint (PX4's land
  detector only accepts ground contact while a descent is commanded) -> landed -> disarm.
All waits are wall-clock and scale with `patience`; the setpoint stream (20 Hz wall) is far above PX4's 2 Hz OFFBOARD minimum
at any real-time factor.
"""
import time

from pymavlink import mavutil

MAV = mavutil.mavlink
# SET_POSITION_TARGET_LOCAL_NED type_mask: which fields PX4 must IGNORE
POS_ONLY = 0b110111111000       # use x, y, z; ignore velocity, acceleration, yaw, yaw rate
VEL_ONLY = 0b110111000111       # use vx, vy, vz; ignore position, acceleration, yaw, yaw rate
PX4_MAIN_MODE_OFFBOARD = 6
DESCENT_M_S = 0.5


class Offboard:
    def __init__(self, m, tag, on_msg=None, patience=1.0):
        """m: a connected mavutil link with target_system/component set; on_msg(msg) sees every message (test-specific)."""
        self.m, self.tag, self.on_msg, self.patience = m, tag, on_msg, patience
        self.armed = False
        self.seen_hb = False       # an autopilot heartbeat arrived (armed is known)
        self.pos = None            # (x, y, z) NED, m
        self.start = None          # pre-flight pos
        self.landed_state = None   # MAV_LANDED_STATE_*
        self.sp = None             # (type_mask, x, y, z, vx, vy, vz)
        self._t_sp = 0.0

    def say(self, text):
        print(f"[{self.tag}] {text}", flush=True)

    def rel_alt(self):
        return 0.0 if self.pos is None or self.start is None else self.start[2] - self.pos[2]

    def pump(self, seconds):
        """Read messages for `seconds` (wall), streaming the current setpoint at 20 Hz."""
        end = time.time() + seconds
        while time.time() < end:
            now = time.time()
            if self.sp is not None and now - self._t_sp >= 0.05:
                mask, x, y, z, vx, vy, vz = self.sp
                self.m.mav.set_position_target_local_ned_send(0, self.m.target_system, self.m.target_component,
                                                              MAV.MAV_FRAME_LOCAL_NED, mask, x, y, z, vx, vy, vz,
                                                              0, 0, 0, 0, 0)
                self._t_sp = now
            msg = self.m.recv_match(blocking=True, timeout=0.05)
            if msg is None:
                continue
            t = msg.get_type()
            if (t == "HEARTBEAT" and msg.get_srcSystem() == self.m.target_system
                    and msg.get_srcComponent() == self.m.target_component and msg.autopilot != MAV.MAV_AUTOPILOT_INVALID):
                # only the autopilot's own heartbeat: MAVROS / onboard components share the system id and are never "armed"
                self.armed = bool(msg.base_mode & MAV.MAV_MODE_FLAG_SAFETY_ARMED)
                self.seen_hb = True
            elif t == "LOCAL_POSITION_NED":
                self.pos = (msg.x, msg.y, msg.z)
            elif t == "EXTENDED_SYS_STATE":
                self.landed_state = msg.landed_state
            elif t == "STATUSTEXT":
                self.say(f"px4: {msg.text}")
            if self.on_msg is not None:
                self.on_msg(msg)

    def wait(self, cond, seconds, what):
        end = time.time() + seconds * self.patience
        while time.time() < end:
            self.pump(0.2)
            if cond():
                return True
        self.say(f"TIMEOUT waiting for {what}")
        return False

    def cmd(self, command, *params):
        self.m.mav.command_long_send(self.m.target_system, self.m.target_component, command, 0,
                                     *([float(p) for p in params] + [0.0] * (7 - len(params))))

    def takeoff(self, alt, reach=0.95):
        """Arm in OFFBOARD and climb to `alt` m above the start position; True once rel_alt >= reach * alt."""
        if not self.wait(lambda: self.pos is not None, 120, "LOCAL_POSITION_NED (any EKF2 aiding source)"):
            return False
        self.pump(3.0)                                    # let EKF2 settle after boot
        self.start = self.pos
        x0, y0, z0 = self.start
        self.sp = (POS_ONLY, x0, y0, z0, 0, 0, 0)         # stream before switching: PX4 refuses OFFBOARD without a setpoint
        self.pump(1.0)
        self.cmd(MAV.MAV_CMD_DO_SET_MODE, MAV.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED, PX4_MAIN_MODE_OFFBOARD)
        self.pump(0.5)
        self.cmd(MAV.MAV_CMD_COMPONENT_ARM_DISARM, 1)
        if not self.wait(lambda: self.armed, 20, "armed (OFFBOARD; ./bisg debug px4 commander check)"):
            return False
        self.say("armed in OFFBOARD")
        self.sp = (POS_ONLY, x0, y0, z0 - alt, 0, 0, 0)
        if not self.wait(lambda: self.rel_alt() >= reach * alt, 60, f"altitude >= {reach * alt:.1f} m"):
            self.say(f"rel_alt={self.rel_alt():.2f}")
            return False
        return True

    def land(self):
        """Descend at DESCENT_M_S until PX4 detects ground contact, then disarm; True once disarmed."""
        self.sp = (VEL_ONLY, 0, 0, 0, 0, 0, DESCENT_M_S)
        if not self.wait(lambda: self.seen_hb, 10, "autopilot heartbeat"):
            return False
        if not self.wait(lambda: self.landed_state == MAV.MAV_LANDED_STATE_ON_GROUND or not self.armed, 90, "landed"):
            return False
        self.cmd(MAV.MAV_CMD_COMPONENT_ARM_DISARM, 0)     # PX4 would auto-disarm after COM_DISARM_LAND (2 s) anyway
        ok = self.wait(lambda: not self.armed, 30, "disarmed after landing")
        self.sp = None
        return ok
