# ZED VIO flights, 2026-10-15 (GPS-denied default, raptor in Simple Room)

The evidence behind [docs/vio.md](../../docs/vio.md) and the calibration in `docker/sim/px4/ekf2_vio_flow_range.params`.
Workstation A (RTX 4500 Ada), Isaac Sim 6.0, PX4 v1.17.0, ZED SDK 5.4.1, RTF 0.55-0.58. Runs are numbered in flight order.

| Run | What was flown | Params | Result (`vio_eval.json`) |
|---|---|---|---|
| `1-baseline` | `tests/vio_bench.py`, fresh sim | defaults: `MC_YAWRATE_MAX 200`, `EKF2_EVA_NOISE 0.1` | **FAIL**: 90 deg yaw steps at 325 deg/s slip the ZED's yaw up to 3.6 deg each, -8.3 deg at the end; EKF2 heading -10.3 deg; EKF2 horizontal max 0.41 m |
| `2-no-vio-aborted` | `vio_bench.py`, the wrapper never connected (no EV at all) | as 1 + `MC_YAWRATE_MAX 60`, `EKF2_EVA_NOISE 0.01` | aborted at liftoff (1.5 m off). EKF2 called the position valid at rest for 157 s (fake position + quality-0 flow), drifted 0.69 m, PX4 armed in OFFBOARD |
| `3-yawrate60-eva001-live` | `vio_bench.py`, fresh sim | `MC_YAWRATE_MAX 60`, `EKF2_EVA_NOISE 0.01`, `EKF2_OF_QMIN_GND 1`, set live | PASS: 100 deg/s peak, <= 1.1 deg per step, -1.7 deg end, EKF2 follows within 0.1 deg; EKF2 horizontal max 0.11 m; z 0.12 m (ZED vz low during a yaw-step dip) |
| `4-confirm-fromfile` | `vio_bench.py`, fresh sim | as 3, loaded from the params file at boot | PASS (0.29 m): yaw +0.08 deg end; a 383 ms EV gap at 0.85 m/s slipped the ZED 0.22 m and tilted its frame 4.4 deg |
| `5-vio-flight-gate` | `tests/vio_flight.py --alt 1.2 --side -1.0`, same sim run as 4 | as 4 | PASS (0.112 / 0.013 / 0.026 m); starts with the 4.5 deg tilt from run 4: the climb leaks ~9 cm sideways |
| `6-smoke-after` | `./bisg smoke`, same sim run as 4 | as 4 | PASS; tilt 4.6-4.9 deg still there |

Each run folder:
- `topics.npz`: the fields of the PX4 log that `tests/vio_eval.py` reads (`KEEP` there), compressed; ~1/30 of the `.ulg`.
  `python3 tests/vio_eval.py --npz <run>/topics.npz --out /tmp/r` gives the same `vio_eval.json` as the original log.
- `vio_eval.json`: the report (latency, velocity, yaw, yaw steps, position, lever arm, frame gaps, tilt, EKF2, no-VIO).
- `vio_eval.png`: position error (ZED and EKF2), yaw error with the true yaw, ZED velocity error, height (not for run 2: no EV).

`tests/unit/test_vio_eval.py` re-analyses these files and checks the findings above (`python3 -m unittest tests.unit.test_vio_eval`,
numpy only). The full `.ulg` logs are outside the repo (git ignores `*.ulg`): `/opt/docker-archive/vio/` on Workstation A.
