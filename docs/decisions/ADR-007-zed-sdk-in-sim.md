# ADR-007 — Run the real ZED SDK in the sim (Stereolabs extension), keep the emulated rig as a fallback

Status: accepted (2026-10-03), verified on the workstation; hardware side to be verified in Phase 5

## Context
The ZED Mini is the drone's only exteroceptive sensor. Until now the sim faked it: Isaac cameras published the wrapper's topic names
and `vio_mock` produced odometry from ground truth. That keeps the *interface* identical but exercises none of the SDK: the depth
algorithm, its holes and range limits, positional tracking, the wrapper's TF and timing. plan.md R5 rated running the real SDK in
the sim impossible because Stereolabs' Isaac integration "targets ZED X only". Re-checking on 2026-10-03: that is true of the Isaac Sim
5.1 line (`isaac-sim/5.1`, Kit 107.3: ZED_X, ZED_XM, X One), but extension **v5.2.x for Isaac Sim 6.0** ships a ZED Mini twin (`ZED_M`).
The repo is already on 6.0.

## Decision
- `ZED_SOURCE=emulated|sdk` (config/bisg.conf, per-scenario override). `sdk`: Stereolabs' `zed-isaac-sim` **v5.2.1** (`529e538`) streams a `ZED_M`
  twin into the unmodified `zed_wrapper` in `bisg/zed:desktop`; `emulated` stays the default and the fallback (no SDK, no GPU image).
- The ZED asset is mounted with a `FixedJoint` (Stereolabs' own robot pattern), weightless; stream transport is IPC (shared memory), port
  `30000 + 2·id`.
- Sim and Jetson launch the wrapper with **one** file (`deploy/launch/zed_drone.launch.py`) and **one** params file (`deploy/jetson/zed_params.yaml`);
  the only sim deltas are `deploy/sim/zed_sim_overlay.yaml` (`imu_fusion: false`, `sensors_image_sync: true`). Each is a documented limitation of the
  streamed camera, not a tuning choice.
- Odometry has exactly one source per run: SDK tracking in `sdk` mode (never `vio_mock`).
- The extension is built in the `bisg/sim` image (`docker/zed/build_isaac_ext.sh`), pinned by commit; its Kit range is widened to match the 6.0.0 image.
- `bisg/zed` gets a one-line overlay (CycloneDDS) on top of Stereolabs' image so it obeys ADR-004.

## Consequences
- Verified 2026-10-03 (`./bisg zed check`, 4 m square flight): SDK health clean, depth 79 % valid (0.24-11 m), baseline 63.0 mm, tracking OK, odometry
  trajectory RMSE 0.088 m and end error 0.024 m against ground truth over a 21.6 m flight (path ratio 1.00). Details and limits: `docs/zed-sdk-sim.md`.
- Not covered by the twin, so still hardware-only: IMU-fused tracking (the stream carries a frame-rate IMU), the real unit's calibration and sensor noise,
  rolling-shutter and exposure behaviour. R5 is retired but a residual gap remains.
- SDK mode needs Isaac Sim 6.0 and ~15 GB more disk. Rates are per simulated second (rtf ~0.3).
- Open: SDK odometry into PX4 (clock stamps, `vio_relay` port: B17), the contract's TF frame prefix (B16), reconnecting a wrapper without restarting the sim (B18).
- Moving `ISAAC_TAG` to 6.0.1 (Kit 110.1.2, the extension's declared target) removes the Kit-range patch; re-test B18 then.
