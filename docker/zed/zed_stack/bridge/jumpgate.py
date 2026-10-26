"""Remove pose discontinuities from the ZED odometry before PX4 EKF2 sees them (pure python, no ROS).

The campaign data (docs/vio.md, vio-campaign.md) shows the ZED odometry error is not smooth noise: it is rare, sudden events, a
pose jump (0.4-0.54 m in one sample) or a yaw slip (8-12 deg) at a camera frame gap, and EKF2 resets to them. Averaging more IMU data
cannot remove those; they have to be detected and taken out.

Detection: relative motion consistency. Over a window (0.4 s) the ZED's displacement and rotation are compared with the flight
controller's own over the same window (EKF2's pose from mavros/local_position/pose: gyro, accelerometer, flow, rangefinder; over 0.4 s
it is independent of what the ZED did a moment ago). Measured on the VIO campaigns (docs/vio.md): clean flights disagree by at most 0.15 m
and 4.9 deg, the real events by 0.45-0.51 m and 11-12.6 deg, so a jump is >= 0.25 m or >= 7.5 deg of disagreement. (An earlier test that
bounded the ZED's step by the peak speed or rate seen fired ~30 times per clean flight: the restamped samples are irregular, 16-50 ms,
and the orientation advances in lumps, so per-sample 'rates' reach 360 deg/s on a vehicle that never exceeds 100. Disagreement over a
window does not care.)

Removal: re-anchoring, not dropping the sample (a slip is a permanent offset, every later sample would carry it): the output is
out = C o zed with a rigid correction C re-solved at the jump so the output continues the previous output by the flight controller's own
displacement and rotation since then. EKF2 sees a continuous trajectory.

Fail-open: if the gate fires `max_jumps` times within `bypass_window_s` it stops intervening for `bypass_s` and reports it (the witness
and the odometry disagree systematically: a wrong frame, a bad latency). Quaternions are (x, y, z, w) as in ROS.
"""
import math
from collections import deque

IDENT_Q = (0.0, 0.0, 0.0, 1.0)


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def qconj(q):
    return (-q[0], -q[1], -q[2], q[3])


def qnorm(q):
    n = math.sqrt(sum(c * c for c in q)) or 1.0
    return tuple(c / n for c in q)


def qrot(q, v):
    """Rotate vector v by unit quaternion q."""
    x, y, z = v
    t = (2 * (q[1] * z - q[2] * y), 2 * (q[2] * x - q[0] * z), 2 * (q[0] * y - q[1] * x))
    return (x + q[3] * t[0] + q[1] * t[2] - q[2] * t[1],
            y + q[3] * t[1] + q[2] * t[0] - q[0] * t[2],
            z + q[3] * t[2] + q[0] * t[1] - q[1] * t[0])


def angle_between(a, b):
    """Rotation angle (rad) between two unit quaternions."""
    d = abs(sum(x * y for x, y in zip(a, b)))
    return 2.0 * math.acos(min(1.0, d))


def norm3(v):
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def sub3(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def add3(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


class JumpGate:
    def __init__(self, pos_thresh_m=0.25, rot_thresh_deg=7.5, rot_rel=0.0, window_s=0.4, warmup_s=5.0, max_jumps=5, bypass_s=10.0,
                 bypass_window_s=2.0, witness_tol_s=0.08, max_total_m=1.0, max_total_deg=15.0):
        self.pos_thresh = pos_thresh_m
        self.rot_thresh = math.radians(rot_thresh_deg)
        self.rot_rel = rot_rel                                    # 0: tested, a relative term hides the real slips (they happen in turns)
        self.max_total_m, self.max_total_deg = max_total_m, math.radians(max_total_deg)
        self.tripped = False                                      # the accumulated correction got implausibly large: off until restart
        self.window_s, self.warmup_s, self.witness_tol_s = window_s, warmup_s, witness_tol_s
        self.max_jumps, self.bypass_s, self.bypass_window_s = max_jumps, bypass_s, bypass_window_s
        self.corr_q, self.corr_p = IDENT_Q, (0.0, 0.0, 0.0)      # out = corr o zed
        self.prev = None                                          # (t, p_out, q_out) of the previous output
        self.t_first = None
        self.hist = deque()                                       # raw ZED samples since the last jump: (t, p, q)
        self.wit = deque()                                        # the flight controller's pose: (t, p, q)
        self.recent = deque()                                     # times of recent jumps
        self.bypass_until = -1.0
        self.jumps = 0
        self.removed_m = 0.0                                      # sum of removed translation
        self.removed_deg = 0.0
        self.last_eval = None                                     # (position disagreement m, rotation disagreement deg) of the last test

    def witness(self, t, p, q):
        """The flight controller's pose at stamp t (same clock as the odometry stamps). Keep ~4 s."""
        self.wit.append((t, p, qnorm(q)))
        while self.wit and t - self.wit[0][0] > 4.0:
            self.wit.popleft()

    def _wit_at(self, t):
        best = None
        for w in reversed(self.wit):                              # newest first: stop once we are past t
            if best is None or abs(w[0] - t) < abs(best[0] - t):
                best = w
            if w[0] < t:
                break
        return best if best is not None and abs(best[0] - t) <= self.witness_tol_s else None

    def apply(self, p, q):
        return add3(self.corr_p, qrot(self.corr_q, p)), qnorm(qmul(self.corr_q, q))

    @property
    def bypassed(self):                                           # intervening is off (fail-open window, or tripped)
        return self.prev is not None and self.prev[0] < self.bypass_until

    def correction(self):
        """Current accumulated correction: (translation m, rotation deg)."""
        return norm3(self.corr_p), math.degrees(angle_between(self.corr_q, IDENT_Q))

    def step(self, t, p, q):
        """One odometry sample: stamp t (s), position p, orientation q (raw ZED). Returns (p_out, q_out, jump) where jump is None or
        {"d": metres removed, "deg": degrees removed}."""
        q = qnorm(q)
        p_out, q_out = self.apply(p, q)
        if self.prev is None:
            self.prev, self.t_first = (t, p_out, q_out), t
            self.hist.append((t, p, q))
            return p_out, q_out, None
        if t <= self.prev[0]:                                     # duplicate / out-of-order stamp: pass through corrected
            return p_out, q_out, None
        self.hist.append((t, p, q))
        ref = None                                                # the newest sample at least window_s back
        for h in self.hist:
            if t - h[0] >= self.window_s:
                ref = h
            else:
                break
        while len(self.hist) > 1 and t - self.hist[1][0] >= self.window_s:
            self.hist.popleft()
        wn, wr = self._wit_at(t), (self._wit_at(ref[0]) if ref else None)
        jump = False
        if ref is not None and wn is not None and wr is not None and t - self.t_first >= self.warmup_s and t >= self.bypass_until:
            dpos = norm3(sub3(sub3(p, ref[1]), sub3(wn[1], wr[1])))                     # |ZED displacement - FC displacement|
            a_fc = angle_between(wn[2], wr[2])
            drot = abs(angle_between(q, ref[2]) - a_fc)                                 # |ZED rotation angle - FC rotation angle|
            self.last_eval = (dpos, math.degrees(drot))
            # a fast turn makes the two yaw estimates disagree by rate x latency, which is not a jump: the rotation threshold
            # grows with the rotation the flight controller saw
            jump = dpos >= self.pos_thresh or drot >= self.rot_thresh + self.rot_rel * a_fc
        if not jump:
            self.prev = (t, p_out, q_out)
            return p_out, q_out, None

        # re-anchor: continue the previous output by what the flight controller says the vehicle did since then
        t0, p0, q0 = self.prev
        wp = self._wit_at(t0)
        if wp is not None and wn is not None:
            p_pred = add3(p0, sub3(wn[1], wp[1]))
            q_pred = qnorm(qmul(q0, qmul(qconj(wp[2]), wn[2])))                         # body-frame rotation increment
        else:
            p_pred, q_pred = p0, q0
        self.corr_q = qnorm(qmul(q_pred, qconj(q)))
        self.corr_p = sub3(p_pred, qrot(self.corr_q, p))
        info = {"d": norm3(sub3(p_out, p_pred)), "deg": math.degrees(angle_between(q_out, q_pred))}
        self.jumps += 1
        self.removed_m += info["d"]
        self.removed_deg += info["deg"]
        self.recent.append(t)
        while self.recent and t - self.recent[0] > self.bypass_window_s:
            self.recent.popleft()
        if len(self.recent) >= self.max_jumps:
            self.bypass_until = t + self.bypass_s
            self.recent.clear()
        if norm3(self.corr_p) > self.max_total_m or angle_between(self.corr_q, IDENT_Q) > self.max_total_deg:
            self.tripped = True                                   # a gate that has moved the odometry this far is wrong, not the ZED
            self.bypass_until = float("inf")
        self.hist.clear()                                         # judge the next samples against the post-jump pose
        self.hist.append((t, p, q))
        self.prev = (t, p_pred, q_pred)
        return p_pred, q_pred, info
