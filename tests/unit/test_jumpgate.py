"""Host-side unit tests for the ZED odometry jump gate (no ROS):  python3 -m unittest tests.unit.test_jumpgate -v

Synthetic flights: a circle at 0.6 m/s with the yaw following the heading, the flight controller's pose as the witness (100 Hz, a
little noise), the ZED stream at ~30 Hz with the irregular stamps of the real restamped stream (16-50 ms apart), and injected faults:
a permanent pose jump and a permanent yaw slip, as the sim's SDK produces them. The numbers behind the thresholds (clean flights
<= 0.15 m / 4.9 deg of disagreement, real events 0.45-0.51 m / 11-12.6 deg) come from the VIO campaigns: docs/vio.md."""
import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "docker", "zed"))

from zed_stack.bridge.jumpgate import IDENT_Q, JumpGate, angle_between, qmul, qrot  # noqa: E402

R_CIRCLE, W_CIRCLE = 2.0, 0.3                 # 0.6 m/s, turning at 17 deg/s


def yaw_q(rad):
    return (0.0, 0.0, math.sin(rad / 2), math.cos(rad / 2))


def truth(t):
    a = W_CIRCLE * t
    return (R_CIRCLE * math.cos(a), R_CIRCLE * math.sin(a), 1.2), yaw_q(a + math.pi / 2)


def fly(gate, secs=30.0, jump_at=None, jump=(0.0, 0.0, 0.0), slip_at=None, slip_deg=0.0, witness=True, seed=1, drop=None):
    """Run the gate over a flight; returns [(t, out_p, out_q, true_p, true_q, jumped)]."""
    rng = random.Random(seed)
    outs, t, tw = [], 0.0, 0.0
    slip0 = None
    while t < secs:
        t += rng.choice([0.0167, 0.025, 0.033, 0.05])                       # irregular, like the restamped stream
        if drop and drop[0] <= t < drop[1]:
            continue                                                         # the camera drops out
        while witness and tw <= t:                                           # the flight controller at 100 Hz, 1 cm noise
            p, q = truth(tw)
            gate.witness(tw, tuple(c + rng.gauss(0, 0.01) for c in p), q)
            tw += 0.01
        p, q = truth(t)
        p = tuple(c + rng.gauss(0, 0.01) for c in p)
        if slip_at is not None and t >= slip_at:
            if slip0 is None:
                slip0 = p
            rz = yaw_q(math.radians(slip_deg))
            p = tuple(a + b for a, b in zip(slip0, qrot(rz, tuple(x - y for x, y in zip(p, slip0)))))
            q = qmul(rz, q)
        if jump_at is not None and t >= jump_at:
            p = tuple(a + b for a, b in zip(p, jump))
        po, qo, j = gate.step(t, p, q)
        outs.append((t, po, qo, truth(t)[0], truth(t)[1], j))
    return outs


def err(o):
    return math.dist(o[1], o[3]), math.degrees(angle_between(o[2], o[4]))


class CleanFlight(unittest.TestCase):
    def test_a_clean_flight_with_jittery_stamps_is_untouched(self):
        g = JumpGate()
        outs = fly(g, secs=60.0)
        self.assertEqual(g.jumps, 0)
        self.assertEqual(g.correction(), (0.0, 0.0))
        self.assertTrue(all(o[5] is None for o in outs))

    def test_nothing_is_judged_without_a_witness(self):
        g = JumpGate()
        fly(g, jump_at=15.0, jump=(0.6, 0.0, 0.0), witness=False)            # a real jump, but nobody to compare with
        self.assertEqual(g.jumps, 0)

    def test_nothing_is_judged_during_the_warm_up(self):
        g = JumpGate(warmup_s=5.0)
        fly(g, secs=10.0, jump_at=2.0, jump=(0.6, 0.0, 0.0))
        self.assertEqual(g.jumps, 0)                                         # the jump fell inside the first 5 s

    def test_a_camera_dropout_is_not_a_jump(self):
        g = JumpGate()
        fly(g, secs=40.0, drop=(15.0, 17.0))                                 # 2 s without frames, the vehicle kept moving
        self.assertEqual(g.jumps, 0)


class PoseJump(unittest.TestCase):
    def test_a_pose_jump_is_removed_and_the_trajectory_stays_continuous(self):
        g = JumpGate()
        outs = fly(g, secs=40.0, jump_at=15.0, jump=(0.5, -0.2, 0.0))
        self.assertEqual(g.jumps, 1)
        self.assertAlmostEqual(g.removed_m, math.hypot(0.5, 0.2), delta=0.15)
        late = [err(o) for o in outs if o[0] > 20.0]
        self.assertLess(max(e[0] for e in late), 0.15)                       # the output follows the truth, not the shifted ZED
        steps = [math.dist(outs[i][1], outs[i - 1][1]) for i in range(1, len(outs))]
        self.assertLess(max(steps), 0.15)                                    # and never steps like the raw stream did

    def test_the_raw_stream_would_have_jumped(self):                         # the test above is only meaningful if the fault is real
        g = JumpGate(pos_thresh_m=1e9, rot_thresh_deg=1e9)                   # a gate that never fires
        outs = fly(g, secs=40.0, jump_at=15.0, jump=(0.5, -0.2, 0.0))
        self.assertGreater(max(err(o)[0] for o in outs if o[0] > 20.0), 0.45)


class YawSlip(unittest.TestCase):
    def test_a_yaw_slip_is_removed(self):
        g = JumpGate()
        outs = fly(g, secs=40.0, slip_at=15.0, slip_deg=12.0)
        self.assertEqual(g.jumps, 1)
        self.assertAlmostEqual(g.removed_deg, 12.0, delta=3.0)
        late = [err(o) for o in outs if o[0] > 20.0]
        self.assertLess(max(e[1] for e in late), 3.0)                        # heading back on the truth
        self.assertLess(max(e[0] for e in late), 0.3)                        # and so is the path

    def test_a_small_slip_below_the_threshold_is_left_alone(self):
        g = JumpGate()
        fly(g, secs=40.0, slip_at=15.0, slip_deg=4.0)                        # clean flights wobble this much
        self.assertEqual(g.jumps, 0)


class FailOpen(unittest.TestCase):
    def test_a_stream_that_keeps_disagreeing_bypasses_the_gate(self):
        g = JumpGate(max_jumps=3, bypass_s=100.0, warmup_s=1.0)
        t = 0.0
        for k in range(400):                                                 # the witness stands still, the ZED jumps 0.5 m every 0.5 s
            t += 0.033
            g.witness(t, (0.0, 0.0, 1.2), IDENT_Q)
            g.step(t, (0.5 * int(t / 0.5), 0.0, 1.2), IDENT_Q)
        self.assertTrue(g.bypassed or g.tripped)
        self.assertLessEqual(g.jumps, 4)                                     # it stopped intervening instead of chasing it forever

    def test_an_implausibly_large_correction_trips_the_gate_off(self):
        g = JumpGate(max_jumps=1000, max_total_m=0.8, warmup_s=1.0)
        t = 0.0
        for k in range(600):
            t += 0.033
            g.witness(t, (0.0, 0.0, 1.2), IDENT_Q)
            g.step(t, (0.4 * int(t / 0.5), 0.0, 1.2), IDENT_Q)
        self.assertTrue(g.tripped)
        self.assertTrue(g.bypassed)


class Quaternions(unittest.TestCase):
    def test_helpers(self):
        self.assertAlmostEqual(angle_between(yaw_q(math.radians(30)), yaw_q(math.radians(-10))), math.radians(40), places=6)
        x, y, _ = qrot(yaw_q(math.pi / 2), (1.0, 0.0, 0.0))
        self.assertAlmostEqual(x, 0.0, places=6)
        self.assertAlmostEqual(y, 1.0, places=6)


if __name__ == "__main__":
    unittest.main()
