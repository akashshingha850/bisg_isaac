"""Carry the ZED's map-frame corrections (loop closure, relocalisation) into the odometry PX4 EKF2 fuses, without a jump (pure python).

The wrapper publishes two poses of the same camera (REP 105): `odom`, a chain of frame-to-frame motion that is continuous and never
corrected, so it only drifts; and `pose`, the camera in the SDK's world (`map`) frame, which takes the corrections area memory / loop
closure make. Their difference is the map -> odom transform T = map o odom^-1; it is constant until the SDK corrects itself, then it
steps. The bridge used to send `odom`: EKF2 never got a correction. Sending `pose` instead would hand EKF2 the step, and EKF2 either
rejects it (innovation gate) or resets to it (it cannot be told it is a reset: MAVROS' odometry plugin always sends reset_counter 0).

So the output is out = C o odom, where C (yaw + translation; the SDK keeps gravity, so roll / pitch need no correction) follows T at a
bounded rate: the output position moves at most `max_mps` and its yaw at most `max_dps` faster than the odometry itself. EKF2 sees a
smooth, slightly fast motion, fuses it, and the flight controller flies the drone onto the corrected frame. A target step larger than
`max_step_m` / `max_step_deg` is treated as a false loop closure and ignored (counted). Quaternions are (x, y, z, w) as in ROS.
"""
import math

from .jumpgate import qmul


def yaw_of(q):
    x, y, z, w = q
    return math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def rz(yaw, v):
    c, s = math.cos(yaw), math.sin(yaw)
    return (c * v[0] - s * v[1], s * v[0] + c * v[1], v[2])


def qz(yaw):
    return (0.0, 0.0, math.sin(yaw / 2), math.cos(yaw / 2))


class MapCorrection:
    def __init__(self, max_mps=0.2, max_dps=3.0, max_step_m=3.0, max_step_deg=30.0):
        self.max_mps, self.max_dps = max_mps, max_dps
        self.max_step_m, self.max_step_deg = max_step_m, max_step_deg
        self.T = None               # target map -> odom: (yaw, t)
        self.C = None               # applied: (yaw, t)
        self.t_last = None
        self.targets = 0            # target changes over 2 cm / 0.2 deg (corrections the SDK made)
        self.rejected = 0
        self.applied_m = 0.0        # total output displacement added by the correction
        self.applied_deg = 0.0

    def target(self, map_p, map_q, odom_p, odom_q):
        """A map pose and an odom pose of the same camera frame (same stamp)."""
        yaw = wrap(yaw_of(map_q) - yaw_of(odom_q))
        r = rz(yaw, odom_p)
        T = (yaw, tuple(m - k for m, k in zip(map_p, r)))
        if self.T is None:
            self.T, self.C = T, T
            return
        # size of the step at the camera: where the new and the old target put the current odom pose
        old = tuple(a + b for a, b in zip(rz(self.T[0], odom_p), self.T[1]))
        new = tuple(a + b for a, b in zip(r, T[1]))
        step_m, step_deg = math.dist(old, new), abs(math.degrees(wrap(T[0] - self.T[0])))
        if step_m > self.max_step_m or step_deg > self.max_step_deg:
            self.rejected += 1
            return
        if step_m > 0.02 or step_deg > 0.2:
            self.targets += 1
        self.T = T

    def set_yaw(self, yaw, odom_p, deadband_deg=0.3):
        """Heading-only target (the Manhattan compass): turn the correction to `yaw` about the current point, so later motion is
        rotated right and the position does not move now. No step limit: the compass is an absolute reference with its own
        consistency checks, and a real slip can be ~40 deg. Changes under `deadband_deg` are ignored (compass noise on a still drone)."""
        if self.T is None:
            self.T = self.C = (0.0, (0.0, 0.0, 0.0))
        step_deg = abs(math.degrees(wrap(yaw - self.T[0])))
        if step_deg < deadband_deg:
            return
        self.targets += 1
        here = tuple(a + b for a, b in zip(rz(self.T[0], odom_p), self.T[1]))
        self.T = (yaw, tuple(a - b for a, b in zip(here, rz(yaw, odom_p))))

    def pending(self, odom_p):
        """(m, deg) still to apply at the current odom position."""
        if self.T is None:
            return 0.0, 0.0
        cur = tuple(a + b for a, b in zip(rz(self.C[0], odom_p), self.C[1]))
        tgt = tuple(a + b for a, b in zip(rz(self.T[0], odom_p), self.T[1]))
        return math.dist(cur, tgt), abs(math.degrees(wrap(self.T[0] - self.C[0])))

    def step(self, t, odom_p, odom_q):
        """The output pose for an odom sample at time t (s)."""
        if self.C is None:
            return tuple(odom_p), tuple(odom_q)
        dt = 0.0 if self.t_last is None else min(max(t - self.t_last, 0.0), 0.2)
        self.t_last = t
        cy, ct = self.C
        cur = tuple(a + b for a, b in zip(rz(cy, odom_p), ct))
        tgt = tuple(a + b for a, b in zip(rz(self.T[0], odom_p), self.T[1]))
        dyaw = wrap(self.T[0] - cy)
        lim = math.radians(self.max_dps) * dt
        dyaw = max(-lim, min(lim, dyaw))
        d = tuple(b - a for a, b in zip(cur, tgt))
        n = math.sqrt(sum(c * c for c in d))
        k = 1.0 if n <= self.max_mps * dt else self.max_mps * dt / n
        p = tuple(a + k * c for a, c in zip(cur, d))
        ny = wrap(cy + dyaw)
        self.C = (ny, tuple(a - b for a, b in zip(p, rz(ny, odom_p))))
        self.applied_m += k * n
        self.applied_deg += abs(math.degrees(dyaw))
        return p, qmul(qz(ny), tuple(odom_q))
