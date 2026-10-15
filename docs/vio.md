# ZED VIO in the GPS-denied default: accuracy, error sources, calibration

What EKF2 takes from the ZED in the sim default (`docker/sim/sim.yaml` `px4_params: [raptor, ekf2_vio_flow_range]`): horizontal
position, 3D velocity and yaw (`EKF2_EV_CTRL 13`). Height is baro + LW20, horizontal velocity also comes from the PMW3901
([range-flow.md](range-flow.md#gps-denied-on-all-sensors-zed--lw20--pmw3901--baro-2026-10-15)). Analysed 2026-10-15 on the RTX 4500 box,
raptor in Simple Room, RTF 0.55-0.58.

Path: `zed_wrapper` odom (pose of `zed_camera_link`, twist in the camera frame) -> zed-bridge (`restamp`, stamp = arrival - 85 ms) ->
MAVROS `odometry/out` (`MAV_FRAME_LOCAL_FRD` pose, `BODY_FRD` velocity) -> EKF2 (`EKF2_EV_POS_*` removes the camera lever arm).

## Tools
| | |
|---|---|
| `tests/vio_bench.py` | OFFBOARD profile that fits Simple Room: 20 s hover, altitude steps 0.6/2.0/1.2 m, x/y legs +-1.5 m at 0.5 and 1 m/s (x+ crosses the table edge), four 90 deg yaw steps, the x legs again yawed 90 deg, a 1.5 m square, 20 s hover, landing. ~250 s wall |
| `tests/unit/test_vio_eval.py` | numpy only, any PC: `python3 -m unittest tests.unit.test_vio_eval -v` (~2 s). Synthetic flights with injected faults (latency, lever arm, yaw slip, frame gap, tilt, no VIO) must be recovered; the archived flights must still show the findings below; the calibrated params must stay in the files |
| `tests/vio_eval.py` | From the PX4 log (`--ulog`) or an archived extract (`--npz`): `vehicle_visual_odometry` (what EKF2 got) vs the twin's `*_groundtruth` (`sensors.ground_truth`, now on in `raptor.yaml`), one clock. Latency, velocity scale/RMSE, yaw drift and per-yaw-step slip, position drift and short-term noise, lever-arm fit, frame gaps, EV frame tilt, EKF2 fusion stats and error; for a log without EV, whether EKF2 still called the position valid. `--save-npz` writes the fields it reads (for the archive). `--plot` needs matplotlib (the host's apt one is broken against numpy 2: use a venv) |

```
./bisg all                                             # fresh sim: the ZED connects once per run (B18), and its errors persist
docker exec bisg-ros bash -lc 'source /opt/ros/jazzy/setup.bash; python3 /workspace/tests/vio_bench.py --out /tmp/vio'
D=$ARCHIVE_DIR/vio/$(date +%Y%m%d-%H%M%S); mkdir -p $D
docker cp bisg-sim:$(docker exec bisg-sim bash -lc 'ls -t $(find /tmp -name "*.ulg") | head -1') $D/flight.ulg
python3 tests/vio_eval.py --ulog $D/flight.ulg --out $D        # exit 0 = gates pass; vio_eval.json (+ vio_eval.png with --plot)
```
Data of the runs below: [`archive/vio-2026-10-15/`](../archive/vio-2026-10-15/README.md) (log extracts, reports, plots: in git); the full `.ulg` files: `/opt/docker-archive/vio/` (Workstation A). Save a new run the same way: `--save-npz <dir>/topics.npz --plot`.

## Calibration + benchmark + ablation on any machine: `./bisg vio`

```
./bisg vio check                 # ~7 min: one calibrated flight on a fresh sim -> verdict "is the VIO right on this PC"
./bisg vio bench [--archive]     # ~2 h: every config x 3 flights (tests/vio_bench.yaml) -> results for the ablation study
./bisg vio bench --configs calibrated,no_flow --reps 5      # any subset / count;  --resume <dir> continues a stopped one
./bisg vio report <dir>          # rebuild summary + verdict;  ./bisg vio list   campaigns and verdicts;  ./bisg vio eval <ulg|npz>
```
`tests/vio_campaign.py` runs on the host (stdlib + PyYAML, else the ros image reads the YAML; numpy for the evaluation, else it runs in
`bisg-ros`). Per flight: `./bisg down` + `./bisg all <view>` (a fresh sim: the ZED connects once per sim run, B18, and keeps its tracking
errors), wait for the zed-bridge `odometry ok`, set the config's PX4 params live and read them back, wait until EKF2 fuses the ZED
(`cs_ev_vel`, `cs_ev_yaw`: never fly without VIO), fly `tests/vio_bench.py`, copy the PX4 log, run `tests/vio_eval.py`. A wrapper that
crashes (R9) or never connects, or EV that is never fused, is an infra failure: logged, retried on a fresh sim (`max_attempts`), and
reported under "Reliability", not counted against the VIO. Configs are interleaved per repetition.

Configs (`tests/vio_bench.yaml`): `calibrated` (the shipped params), `no_yaw_limit` (`MC_YAWRATE_MAX 200`), `no_eva_fix`
(`EKF2_EVA_NOISE 0.1`), `px4_defaults` (all three calibrations undone), `no_flow` (`EKF2_OF_CTRL 0`), `ev_no_position`
(`EKF2_EV_CTRL 12`: ZED velocity + yaw only).

Output `$ARCHIVE_DIR/vio_bench/<date>-<host>/` (`--archive` also copies it, without the `.ulg`, to `archive/vio-bench/`):
`summary.md` (verdict, experimental setup: machine, images, versions, RTF, design, profile, configs; results mean ± std (min-max) per
config; ablation deltas vs `calibrated`; pipeline calibration; reliability; per-flight table), `summary.json`, `summary.csv` (one row per
flight), `figures/*.svg` (bars per config with every flight as a dot; EKF2 horizontal and ZED yaw error over time), `machine.json`,
`campaign.yaml`, `campaign.log`, `runs/<config>-r<k>/` (`flight.ulg`, `topics.npz`, `vio_eval.json`, `series.csv`, `bench.log`, `run.json`).

Verdict (exit 0 = PASS, `verify:` in the YAML): over all flights the residual EV latency (|median| <= 20 ms), the ZED velocity scale
(±0.03) and the lever-arm fit (<= 3 cm, flights without a gap slip); over the `calibrated` flights the pass rate of vio_eval's gates
(>= 2/3) and the median EKF2 horizontal max (<= 0.3 m). When a pipeline quantity is off for this machine the report prints the
correction, e.g. a new `restamp_latency_ms` (it is wall latency x RTF, so it moves with the machine's sim speed).
Tests of the tools themselves (no sim): `python3 -m unittest tests.unit.test_vio_eval tests.unit.test_vio_report`.

## Results

| Run (fresh sim each) | yaw rate peak | ZED yaw error, end | EKF2 horizontal max / end | EKF2 z max | notes |
|---|---|---|---|---|---|
| `1-baseline`: defaults (`MC_YAWRATE_MAX` 200, `EKF2_EVA_NOISE` 0.1) | 325 deg/s | -8.3 deg | 0.41 / 0.11 m | 0.045 m | FAIL (0.3 m bound) |
| `3-yawrate60-eva001-live`: `MC_YAWRATE_MAX 60`, `EKF2_EVA_NOISE 0.01` (set live) | 99 deg/s | -1.7 deg | 0.11 / 0.05 m | 0.12 m | z: see 4. below |
| `4-confirm-fromfile`: same, from the params file at boot | 99 deg/s | +0.02 deg | 0.29 / 0.29 m | 0.03 m | frame gap at 0.85 m/s: see 3. below |

Same in every run (the ZED pipeline itself is calibrated):
- **Latency**: residual EV lag vs truth +10 ms after the bridge's 85 ms restamp (`restamp_latency_ms` holds at RTF 0.55-0.58; `EKF2_EV_DELAY 0` stays).
- **Velocity** (body, vs the camera's true velocity incl. w x r): scale 0.996-1.002, RMSE 0.023-0.032 m/s with slow yaw (0.04-0.06 with
  325 deg/s yaw), rare spikes up to 2 m/s during fast rotation (EKF2 rejects 0.1-0.6 %). Frames and signs are right.
- **Position** short-term noise 4-9 mm (10 mm in run 4, the slip step); drift during translation only (0-58 s of the profile) within 2 cm, table edge included.
- **Lever arm**: the yaw-correlated error fits a camera offset of <= 2.5 cm, so `EKF2_EV_POS_*` (raptor.params) is right (runs 1 and 3; in run 4 the gap slip happened while yawed and the fit absorbs it: 4.6 cm).
- **EKF2 follows the ZED**: EV position innovations 4-9 mm vs the assumed 0.1 m, flow fused 99.97 % but it cannot correct the ZED.
  EKF2's horizontal error is the ZED's error.

## Error sources (all four are the sim SDK tracking without its IMU: `sim.positional_tracking.imu_fusion: false`)
1. **Yaw slip on fast rotation (fixed by `MC_YAWRATE_MAX 60`).** A 90 deg yaw setpoint step spun the raptor at 325 deg/s (the PX4 default
   cap is 200; the sim's placeholder yaw tune overshoots it), ~11 deg per camera frame. Each step cost the ZED up to 3.6 deg of yaw, which
   then stays (-8.3 deg after four steps). With no magnetometer, EV yaw is EKF2's only heading reference, so its whole frame turns with it:
   the error grows with distance from takeoff (~0.14 m per m at 8 deg, 0.35 m at the far square corner). At 60 deg/s (99 deg/s peak in the
   sim): <= 1.1 deg per step.
2. **EKF2 heading lagging the ZED's (fixed by `EKF2_EVA_NOISE 0.01`).** PX4 v1.17 floors the EV yaw variance at
   `max(var, EKF2_EVA_NOISE, 1e-4)` (`ev_yaw_control.cpp:48`, a std used as a variance), so the default 0.1 means 0.32 rad (18 deg)
   instead of 0.1 rad. EKF2's heading took ~20 s to follow the ZED after each turn while the EV position kept arriving in the ZED's frame
   (final EKF2 heading error -10.3 deg vs the ZED's -8.3). With 0.01 (= 0.1 rad effective) it tracks within 0.1 deg. The ZED's yaw is
   steady to 0.1 deg in hover.
3. **Frame gaps while moving (open).** The ZED odometry had 4 gaps > 150 ms in ~400 s of flight (the bridge sees them; the sim's RTF shows no
   dip). Three in hover cost < 1 cm. One of 383 ms at 0.85 m/s made the SDK miss 0.22 m of the 0.27 m travelled **and tilt its world
   frame by 4.6 deg** (roll/pitch); both stay for the rest of the sim run. The tilt makes every climb leak into horizontal position
   (~9 cm per m: the gating `vio_flight` after it read x 0.11 m). Offline, fusing ZED velocity only (`EKF2_EV_CTRL 12`) is not clearly
   better (0.30 vs 0.36 m), so the position stays fused. Source of the gaps not found (sim render, wrapper grab or DDS).
4. **ZED vertical velocity during a yaw step (open, small).** In one run the raptor sank 15 cm during the 180 deg yaw step and the ZED's vz
   read 2-4 cm/s low for 2.5 s. EKF2 trusts EV velocity (sigma 0.1 m/s) far more than the baro (`EKF2_BARO_NOISE` default 3.5 m), and the
   LW20 change went into the terrain estimate, so the height read 8-12 cm high and recovered over ~50 s. vz is otherwise unbiased
   (RMSE 0.033 m/s, -2 cm integrated over the flight). Not changed: the sim baro is idealised; size `EKF2_BARO_NOISE` on the real drone.

The real ZED Mini fuses its 400 Hz IMU (`imu_fusion: true` outside `sim:`), which pins roll/pitch to gravity and bridges short frame gaps,
so 1, 3 and 4 should be much smaller there. Streaming a real-rate IMU from the Isaac extension would close the gap in the sim (not built).

## Arming without VIO (safety, open)
With the ZED down, PX4 still arms in OFFBOARD: at rest EKF2 always fuses a "valid fake position" (`fake_pos_control.cpp`), so
`xy_valid` is true, and "Ready for takeoff" never meant the ZED was fused. Seen live (run 2, the wrapper had not connected): EKF2 called the position valid for 157 s at rest while it drifted
0.69 m on quality-0 flow, then ran 1.5 m off at liftoff (flow is below its 8 cm minimum there) and the test aborted.
`EKF2_OF_QMIN_GND 1` (ekf2_vio_flow_range) stops the ground drift; it cannot stop the arming. The gate belongs in our stack: take off only
while the zed-bridge reports `odometry ok` (bridge status / `./bisg zed status`), e.g. in `bisg_vehicle` `offboard_controller.wait_ready`.
