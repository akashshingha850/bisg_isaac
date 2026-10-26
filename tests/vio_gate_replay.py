#!/usr/bin/env python3
"""Replay the ZED odometry jump gate (docker/zed/zed_stack/bridge/jumpgate.py) on PX4 log extracts, OPEN LOOP.

    python3 tests/vio_gate_replay.py runs/calibrated-r1/topics.npz [more.npz ...]

Feeds vehicle_visual_odometry through the gate with EKF2's local position and attitude as the witness, and reports the firings and the
yaw error against ground truth, raw and gated. Open loop: the logged EV stream is what the ZED sent (gate off), so the gate's effect on
EKF2 (EKF2 follows the vision yaw: EKF2_EVA_NOISE) is invisible here. That is how v3 looked fine offline and failed in the sim
(docs/vio.md). Pitfall: in these extracts the *_groundtruth topics have timestamp_sample = 0; use their `timestamp`.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "docker", "zed"))
from zed_stack.bridge.jumpgate import JumpGate  # noqa: E402


def yaw_of(q):
    x, y, z, w = q.T
    return np.arctan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))


def wrap(a):
    return (a + np.pi) % (2 * np.pi) - np.pi


def replay(path, **kw):
    z = np.load(path, allow_pickle=True)
    g = lambda k: z[k]                                                                          # noqa: E731
    t = g("vehicle_visual_odometry|timestamp_sample").astype(float) * 1e-6
    p = np.stack([g(f"vehicle_visual_odometry|position[{i}]") for i in range(3)], 1).astype(float)
    q = np.stack([g(f"vehicle_visual_odometry|q[{i}]") for i in (1, 2, 3, 0)], 1).astype(float)  # PX4 wxyz -> xyzw
    tl = g("vehicle_local_position|timestamp_sample").astype(float) * 1e-6
    pl = np.stack([g(f"vehicle_local_position|{k}") for k in "xyz"], 1).astype(float)
    ta = g("vehicle_attitude|timestamp_sample").astype(float) * 1e-6
    qa = np.stack([g(f"vehicle_attitude|q[{i}]") for i in (1, 2, 3, 0)], 1).astype(float)
    gate, qo, jumps, wi = JumpGate(**kw), np.zeros_like(q), [], 0
    for i in range(len(t)):
        while wi < len(tl) and tl[wi] <= t[i]:
            gate.witness(tl[wi], tuple(pl[wi]), tuple(qa[np.clip(np.searchsorted(ta, tl[wi]), 0, len(ta) - 1)]))
            wi += 1
        _, qo[i], j = gate.step(t[i], tuple(p[i]), tuple(q[i]))
        if j:
            jumps.append((round(t[i] - t[0]), round(j["d"], 2), round(j["deg"], 1)))
    tg = g("vehicle_attitude_groundtruth|timestamp").astype(float) * 1e-6
    qg = np.stack([g(f"vehicle_attitude_groundtruth|q[{k}]") for k in (1, 2, 3, 0)], 1).astype(float)
    yg, k0 = np.interp(t, tg, np.unwrap(yaw_of(qg))), int(np.searchsorted(t, t[0] + 30))

    def yaw_err(qx):
        e = wrap(np.unwrap(yaw_of(qx)) - yg)
        e = np.degrees(np.abs(wrap(e - np.median(e[k0:k0 + 200]))))[k0:]
        return e.max(), e[-1]
    return jumps, yaw_err(q), yaw_err(qo)


if __name__ == "__main__":
    for f in sys.argv[1:]:
        jumps, raw, gated = replay(f)
        print(f"{f}: fired {len(jumps)}x {jumps[:4]} | yaw error max/end raw {raw[0]:.1f}/{raw[1]:.1f} deg, gated {gated[0]:.1f}/{gated[1]:.1f} deg")
