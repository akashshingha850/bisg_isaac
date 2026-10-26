# TODO

Live list only: finished items move to `archive/docs/todo-history-2026-10.md`. Phases and exit tests: [roadmap.md](roadmap.md).
Defects with causes: [bugs.md](bugs.md).

**State (2026-10-19):** single-drone twin on Isaac Sim 6.0, raptor in the **Warehouse** (`docker/sim/sim.yaml`: lamps ×0.5 +
ambient 2), GPS-denied by default (ZED VIO + LW20 + PMW3901 + baro). `./bisg vio check` / `vio bench` PASS there
([vio-campaign.md](vio-campaign.md)); `restamp_latency_ms` 100 on Workstation A. Kinetix flies whole-room tours on it.

## Done 2026-10-22
- [x] **Empty Warehouse**: new locator key `keep_only` (fnmatch globs over the world asset's top-level prims; the rest is
  deactivated, `launch.py` `keep_only_world_prims`). `sim.yaml` keeps floor + painted stripes, walls (+ corners, pilasters),
  ceiling, roof beams/pillars/brackets and the 2 lights: 173 prims kept, 118 deactivated (racks, pallets, bins, signs, wires,
  ceiling lamps). Lighting re-probed in the empty room (72 views x 25 settings): x0.5 + ambient 2 stays (on the optimum
  ridge, worse-of bright/dark texture 39.9 % vs best 41.9 % which loses the ZED view's brick texture; numbers in `sim.yaml`).
  New key `drop` (path globs inside the kept assets, `drop_world_prims`) removes the lattice trusses + knee braces hanging
  under the roof (`SM_PillarPartA_*/SM_PillarPartA_9M/Section1`, 10 meshes; the wall columns are Section0 and stay).
  `vio_flight --alt 1.2 --side -1.0` PASS: 6.5 / 2.2 / 9.7 cm before the truss drop, 10.2 / 6.4 / 9.3 cm after (one run
  each, the first empty-room run was 1.4 / 2.4 / 2.3). `./bisg vio check` in the final room **PASS**
  (`$ARCHIVE_DIR/vio_bench/20261022-113944-stallman2`): EV latency +0 ms, velocity scale 0.993 / 1.005, lever arm 1.8 cm,
  worst EKF2 horizontal 6.6 cm (full Warehouse: 7.3-9.1). The lighting probe ran with the trusses in place.

- [x] **Collision prevention off on the raptor** (`raptor.params` `CP_DIST -1`; PX4 reads −1 at boot): room scans fly close to
  the walls. PX4 v1.17 applies it only in Position mode and to stick nudges in Auto modes, not to Kinetix's OFFBOARD setpoints,
  so if a scan still stops short the cause is elsewhere. `iris.params` keeps 1.5 for `tests/collision_prevention.py`; the
  bridge's `obstacle_distance` stays on (QGC radar). Also applies to the Pixracer at its next `push_px4_params.py --file raptor`.

- [x] **Sim ZED fuses a high-rate IMU (2026-10-23): same tracking as the real camera** (AUTO = GEN_3 + `imu_fusion`; the
  zed.yaml `sim:` tracking deltas are gone). The extension's streamer library exports `ingest_imu` (timestamp + gyro + accel)
  but the extension never called it and streamed one orientation+accel sample per frame. `docker/zed/patches-isaac-ext/0001`
  (applied by `build_isaac_ext.sh`) adds a node input `imuSamples`, ingests each new sample before the next frame and switches to
  gen-2 streaming (`mode = 2`; mode 1 rejects ingested IMU); `zed_sdk_rig.py StreamImuFeeder` writes the physics IMU (every
  physics step, 120 Hz) into it. The SDK's gyro unit is deg/s: sent as rad/s the ZED frame tilted 12.9 deg in a `vio check`
  (0.13 deg after). `restamp_latency_ms` 165 -> 95. Route A/B (4.3 m, ~75 m, trusses removed), est-vs-GT median / max: GEN_3 +
  IMU 0.28-0.45 / 0.40-0.65 m over 4 runs, GEN_1 vision 0.24-0.29 / 0.68-0.71 (2), GEN_3 vision 0.72 / 1.01 (1). Gates: `vio check`
  PASS (`$ARCHIVE_DIR/vio_bench/20261023-034123-stallman2`: +0 ms, scale 1.003 / 1.005, EKF2 h max 7.8 cm), `smoke` PASS,
  `vio_flight` PASS (7.9 / 3.7 / 10.3 cm), `zed_depth_box` PASS (−25.5 mm), `zed test` OK. Open: the physics IMU is noiseless and
  bias-free at 120 Hz (the real ZED Mini: 800 Hz with noise) — add an IMU noise model and/or a faster physics rate before trusting
  sim-vs-real drift comparisons; `set_gravity_as_origin: true` in sim (now possible, not re-tested); report `ingest_imu` + mode 2
  to Stereolabs (zed-isaac-sim) so the patch can go
- [x] ~~superseded 2026-10-23 by the IMU feed above~~ **Sim ZED tracking GEN_1** (zed.yaml `sim:`; real camera unchanged: AUTO = GEN_3 + IMU). A Kinetix `roi_coverage` scan
  in the emptied Warehouse (roof trusses dropped) crashed into the south wall: GEN_3 visual-only drifted 2-4 m at 4.4 m height
  (frames' est vs GT), plus ~10 deg yaw jitter while hovering at plain walls. A/B on one route (scratch `high_route.py`: 4.3 m,
  1 m/s carrot, ~75 m, 30 s hover at the jitter spot), est-vs-GT horizontal median / p95 / max: GEN_3 + trusses 0.34 / 0.77 / 0.86,
  GEN_3 no trusses 0.72 / 0.83 / 1.01, GEN_1 + trusses 0.24 / 0.59 / 0.67, GEN_1 no trusses 0.29 / 0.64 / 0.71 m; GEN_1 + IMU
  fusion (Stereolabs' Isaac answer) 1.4 m off after 5 m, aborted at 3 m: the 90 deg rolled stream (below) blocks fusion. So
  trusses dropped again, GEN_1 in sim, `restamp_latency_ms` 100 -> 165 (GEN_1 is +65 ms); `./bisg vio check` PASS
  (`$ARCHIVE_DIR/vio_bench/20261022-153200-stallman2`: +0 ms, scale 0.992 / 0.983, lever 1.4 cm, worst EKF2 10.5 cm).
  One run per config: confirm with `./bisg vio bench` / a high profile before trusting the figures.

## Now — ZED VIO / localization ([vio.md](vio.md), [vio-campaign.md](vio-campaign.md))
- [x] **R9 wrapper crash** `can't compare times with different time sources` — **fixed 2026-10-21** (ADR-011). Throw site
  (`terminate_bt`, 2026-10-20, 2 s after spatial mapping started): `handleVideoDepthPublishing()` default-constructs
  `rclcpp::Time pub_ts` (RCL_SYSTEM_TIME), `publishVideoDepth()` leaves it unset on a repeated grab and, with
  `sensors_image_sync` on (sim), `pub_ts != TIMEZERO_ROS` throws. A wrapper bug, fixed upstream in PR #460 (`cd8bf73`), in no
  release yet: the wrapper is pinned to master `b19902d` (`ZED_WRAPPER_REF`), SDK stays 5.4.1. Gate on it: `./bisg smoke` PASS,
  `vio_flight --alt 1.2 --side -1.0` PASS (1.9 / 3.5 / 2.2 cm), `zed_depth_box` PASS (−22.9 mm, was −26), `./bisg zed test` OK.
- [ ] Back to a wrapper **tag** once Stereolabs releases one containing `cd8bf73` (v5.5.1+); rebuild the Jetson image from the pin
  (`docker/zed/build.sh jetson`) before the next hardware run.
- [x] **Streamed ZED Mini IMU 90 deg rolled — fixed 2026-10-22.** Cause: the ZED_M asset (extension v5.2.1, same in v5.3.0;
  ZED_2i too) authors `Imu_Sensor` at orient (w, x, y, z) = (0.5, 0.5, −0.5, −0.5), while the stream conversion expects it aligned
  with the camera body. `zed_sdk_rig.py` sets it body-aligned (`STREAM_IMU_RPY`, per-vehicle override `sensors.zed.stream_imu_rpy`):
  the wrapper's `imu/data` at rest reads accel (0, 0, +9.81), rpy (0, 0, 0), and in flight matches the physics IMU (median 0.00,
  p95 0.04 deg). (Fusion solved 2026-10-23 by the high-rate IMU feed, entry above; as of 10-22:) Sim IMU fusion was not usable (no high-rate IMU in the stream): GEN_1 + fusion diverges on the first
  acceleration; GEN_3 + fusion (SDK 5.4.1: orientation as rotation prior, returns the WARNING code SENSORS_DATA_REQUIRED that the
  wrapper treated as failure -> fixed by `60f78bd` on our wrapper fork's `local`, ADR-011 amendment 2026-10-23)
  keeps translation at 0, the open Stereolabs GEN_3 + IMU bug (forum thread 11361). Sim stays GEN_1 vision-only (route A/B after
  the fix 0.24 / 0.65 / 0.68 m). Still open: `set_gravity_as_origin: true` in sim (now possible, not re-tested); asset IMU orientation +
  fusion results reported upstream: stereolabs/zed-isaac-sim#62 (2026-10-23); a high-rate IMU in the extension is the only route to sim fusion
- [ ] **Wrapper fix upstream: stereolabs/zed-ros2-wrapper#463** (2026-10-23) = `60f78bd` on our fork's `local`; once merged, move
  `local` onto upstream (or back to a release tag) and drop the fork (ADR-011 amendment 2026-10-23)
- [ ] **Jetson image: rebuild from the fork's `local` (`60f78bd`)** (`git submodule sync && git submodule update`, then `docker/zed/build.sh jetson`); on the real camera (400 Hz IMU) GEN_3 + fusion
  returns SUCCESS, so the patch changes nothing there unless the SDK returns a warning code. Bench-check GEN_3 + IMU translation
  (the forum's stuck-at-0 bug was on real hardware, SDK 5.3) before trusting it in flight
- [ ] Fused cloud vs TF clocks: `fused_cloud` is stamped wall-clock now, the wrapper's TF with the streamed frame time (falls behind
  at ~rtf: −20 s, growing ~0.5 s per s, measured ~20 s after the wrapper started). Harmless for the map frame in Foxglove; matters for anything that looks TF up at the cloud's stamp (B17)
- [x] **VIO drift on long flights — cause found, heading fixed, sim default changed 2026-10-26** ([vio-drift.md](vio-drift.md),
  papers in [research/](research/reports/)). Long profile `tests/drift_flight.py` (5 laps, 359 m): the sim ZED loses its heading in
  in-place turns away from take-off (2-40 deg a slip, 115-209 deg over 320-360 m) and jumps its position with it; EKF2 followed (abort at
  3 m inside 26-36 m). Fix: zed-bridge Manhattan compass (`odometry.heading: manhattan`, heading from the room's walls in the ZED
  depth, slewed into the odometry) + ZED velocity/yaw only (`ev_compass.params`, `EKF2_EV_CTRL 12`): the 359 m flight landed at
  1.76 m max / 0.93 m RMS, Kinetix explore EKF2 max 0.62-0.98 m vs 1.50-2.73 m before. Sim only; real drone unchanged
- [ ] **Compass on the real camera** before `heading: manhattan` + `ev_compass` go on the drone (vio-drift.md "What ships")
- [ ] **Position from the walls** (vio-drift.md "Open" 1): after the sim ZED depth's ~10 % short reading at 8-15 m is understood
- [ ] **Why the sim ZED slips** in the south-west of the Warehouse (GEN_3 + streamed IMU; clean at take-off: tests/yaw_wrap_test.py) —
  report to Stereolabs with an SVO of a slipping turn
- [ ] VIO loop closure: ZED GEN_3 `area_memory` (zed.yaml `pos_tracking`, off) bounds drift on revisits. The bridge side is built
  (`odometry.pose_source: map`: the map-frame pose through a slewed correction, since MAVROS cannot send a `reset_counter`), not
  flown; needs the wrapper's `reset_odom_with_loop_closure: false` (default true: `odom` jumps to the origin at a loop closure) and
  is exclusive with the compass today (vio-drift.md "Open" 2)
- [ ] EKF2 map origin vs spawn differs between boots: z −0.14 / +0.12 m (baro height origin), x −0.12 m (ZED odom origin ahead of the
  body). Kinetix measures it at start; anything else that assumes map = world − spawn should too
- [ ] **Yaw oscillation with `EKF2_EVA_NOISE 0.1`** (vio-campaign.md §4.5): 2 of 18 flights at 0.1, 0 of 36 at 0.01; mechanism not
  verified. `vio_eval.py` has a detector since 2026-10-26 (`yaw_oscillation`, gated: true yaw rate swinging both ways past 30 deg/s for >= 8 s;
  finds exactly `px4_defaults-r1` 20261017 and `no_eva_fix-r3` 20261018 of 70 campaign flights). Open: the same limit cycle at 0.01 / EV_CTRL 12 in a
  3.7 h-old sim (drift flight 2026-10-26, 2.5 Hz, 9 -> 200 deg/s, EKF2 yaw within 1.5 deg of truth; fresh sim hovers clean): cause not found
- [ ] **Arming without VIO** (safety, [vio.md](vio.md#arming-without-vio-safety-open)): PX4 arms in OFFBOARD with the ZED down (EKF2's
  at-rest fake position); seen live, 1.5 m off at liftoff. Gate takeoff on the zed-bridge `odometry ok` in
  `bisg_vehicle` `offboard_controller.wait_ready` and the tests
- [ ] ZED pose jump without a frame gap (0.42 m in one sample): EKF2 resets to it; consider `EKF2_EV_CTRL 12` on the drone if the
  (2026-10-24: a jump gate was built and tested, `docs/vio.md#jump-gate`: quiet on clean logs and fixes real events offline, but harms flights in the sim
  because EKF2's yaw follows the vision yaw. Open: an independent gyro-integrated rotation witness.)
  real ZED shows jumps
- [ ] ZED odometry gaps > 150 ms (4 in ~400 s, Simple Room; none in the Warehouse campaigns): find the source (render, grab, DDS);
  a real-rate IMU from the Isaac extension would let the sim SDK fuse it
- [ ] Run `./bisg vio bench` on Workstation B (its RTF sets its own `restamp_latency_ms`)
- [ ] `single_iris_vio` (Iris, vision height, no ToF/flow) still fails `vio_flight` on z (B17); the default raptor scenario passes.
  Fix or retire the scenario
- [ ] Switch `GEN_3` IMU-fused tracking on for the hardware bench (`positional_tracking.imu_fusion` is already true outside `sim:`)

## Now — ZED stack ([zed-stack.md](zed-stack.md), ADR-008)
- [x] QGC grid and Foxglove Camera tab are the same 2x2, left | chase / depth | confidence (2026-10-21). The PMW3901 flow drawing
  (`mosaic.FlowView`, `/drone_N/optical_flow/image`, its RViz display) is removed: plot `mavros/px4flow/raw/optical_flow_rad` (Foxglove Sensors tab).
  The map is skewed (median 0.6, p95 32 in the Warehouse), so on the 0-100 scale most of the tile is turbo's darkest blue
- [ ] **Apply `bisg/ros` rebuild** (GStreamer removed from its Dockerfile): `docker compose -f docker/compose.yaml build ros`
- [ ] Bridge CPU: `health` and `obstacle_distance` each deserialise every 720p depth frame in Python (0.31 cores); share one
  depth subscription / decimate before the Orin NX bench
- [ ] Repeat `./bisg zed bench` on the Orin NX: RAM is the constraint (mapping +4 GB, detection +4 GB, body tracking +7 GB)
- [ ] Obstacle avoidance closed loop: `tests/collision_prevention.py` fails while QGC's virtual joystick holds PX4's manual-control
  source; run it with the joystick off, then confirm the QGC proximity radar
- [ ] Area memory (`.area` of the lab) and `floor_alignment` for Kinetix T3 flights: decide at Phase 5 / Kinetix K6
- [ ] ROS graph findings ([ros-graph.md](ros-graph.md)): R1 two publishers on `zed/zed_node/imu/data` in the sim; R5/R6 RViz + QGC
  video carry most of the camera traffic (point cloud / right image off by default, video on demand); R8 per-drone MAVROS
  `uas_url` before Phase 6; R10 `/clock` at ~26 Hz
- [ ] Bridge modules not built: M11 MAVLink camera component, M5/M6 `FOLLOW_TARGET`/`LANDING_TARGET`, M7 PX4 GPS → ZED GNSS
  (`archive/docs/zed-px4-bridge.md` §2); one module + one fake-topic test at a time
- [ ] QGC click-through of the video stream and the Jetson nvenc path: untested
- [ ] B16 contract TF frame prefix vs the wrapper's unprefixed frames: decide with the swarm phase
- [ ] B18 the SDK connects once per sim run (2-3 failed connects per 20 boots): retry on Isaac Sim 6.0.1
- [ ] Real drone: measure baro noise near the floor and size `EKF2_BARO_NOISE`; `MC_YAWRATE_MAX 60` also caps Position-mode stick yaw;
  the EVA quirk also applies to `ekf2_vision.params` (Iris, not changed); real PMW3901 mount + Pixracer driver params
  (`SENS_EN_PMW3901`, `SENS_FLOW_ROT`); measure the camera's forward/vertical offset (CAD + placeholder CoM today)
- [ ] MAVROS segfault ~3 s after connecting (once, 2026-10-15; the container now restarts): cause unknown

## Now — sim / host
- [ ] Not yet run in Isaac: `SIM_SCENARIO=single_iris ./bisg up gui` (window floating, chase pane, RTF with the chase camera)
- [ ] Not yet run after the autostart fix: a plain `./bisg all headless` that starts the wrapper + RViz by itself
- [ ] ZED twin at 15 fps (RTF 0.66) needs a depth fix before it can be the default (depth −40 mm FAIL); `launch.sh` claims an exported
  `SIM_CONFIG` wins but only `-c` does
- [ ] Delete by hand (root-owned, outside git): `docker/ros/ros2_ws/src/bisg_perception/`, `bisg_vehicle/__pycache__/`,
  `docker/ros/ros2_ws/*.stale/`
- [ ] Foxglove `kinetix.json` layout (2026-10-20; `FOXGLOVE_LAYOUT=kinetix`, `docker/ros/foxglove/README.md`): the user scripts pass
  `tsc --strict` and a Node run on fake events; not yet looked at in the browser during a Kinetix tour (path line style keys,
  `camera_info` frustum, plots of `/studio_script/*`)
- [ ] Foxglove `raptor.json` reworked 2026-10-20 (Flight: 3D + altitude + x/y only; Sensors: six plots with top legends; Debug: /rosout + MAVLink
  log; Graph tab; no status strip) and `spatial_mapping.enabled: true` in zed.yaml, with `mapping/fused_cloud` in the Flight 3D panel:
  not yet looked at in the browser. The ZED wrapper already connected once in the current sim run (B18): `./bisg restart`, then `zed up`,
  to see the fused cloud; check it builds up the room, and the +4 GB RAM and sim speed with mapping on
- [ ] `TAILSCALE_WITH_SIM=1` (2026-10-20): down/up cycle verified on Workstation A (stallman2, host daemon, operator set);
  Workstation B still needs `sudo tailscale set --operator=$USER` if it uses a host daemon (container mode needs nothing)
- [ ] Foxglove over a VS Code tunnel through the single port (`ws://<host>:8080/ws`, 2026-10-20): checked in headless Chromium on the
  host, not yet from the remote VS Code client
- [ ] Remote access: verify the WebRTC client + browser view from an off-site machine over Tailscale
- [ ] **`net.core.rmem_max`** (needs sudo) on Workstation B: until set, HD720 images do not cross containers over CycloneDDS
  (`ZED_RMW=rmw_fastrtps_cpp` is the fallback)
- [ ] Remaining answers → `hardware.md`: Orin NX RAM variant, L4T/CUDA, frame/motor/battery, Pixracer firmware, site
- [ ] **Bench day (Orin NX + Pixracer + ZED Mini)**: `docker/zed/build.sh jetson`; `tests/zed_sdk_check.py --drone 1 --no-gt`; the unit's
  real `K` into `hardware.md`; trajectory vs tape measure; MAVROS lean idle CPU / command RTT with the wrapper running
- [ ] Offboard-loss / RC-loss failsafe for GPS-denied flight (Land/Hold are unusable there, `bugs.md` B1): pick and prove one in SITL
- [ ] Manual: real QGroundControl session, real WebRTC client, `vehicle reset`
- [ ] PX4 bridge: the serial (`--hw`) path on a real Pixracer, `bisg/px4-bridge` built on arm64, per-drone `PX4_BRIDGE_DRONE_N`,
  one MAVSDK gRPC port per host; port the ZED bridge's output if MAVSDK or xrce ever becomes the default

## Next — Isaac Sim 6.0 follow-ups ([migration-errors.md](migration-errors.md))
- [ ] Pegasus per-step cost (M8): batch force/torque + propeller visuals on the submodule `local` branch; gate with smoke +
  `vio_flight` + `zed_depth_box`. The camera renders cost more than Pegasus now ([performance.md](performance.md))
- [ ] Decide what `headless_fast` means now (M9)
- [ ] Push `isaac-5.1-baseline` and `migrate/isaac-6.0` (your call) and merge
- [ ] Port the sensors off deprecated APIs (`isaacsim.sensors.camera`, `isaacsim.core.utils`, ros2 bridge shim) before 6.1 (M12)
- [ ] Re-test whether the NVIDIA 59x driver crash exists on 6.0 (keep the `check_env.sh` guard until then)
- [ ] Isaac ROS 4.6: not in `plan.md`; needs its own plan first

## Later — phases ([roadmap.md](roadmap.md))
- Phase 2: `bisg_msgs` (VehicleState/VehicleCmd/Task; `check_contract.py` reports `vehicle/state` PENDING until then),
  `bisg_bringup` launch; rebuild `bisg/ros:arm64`
- Phase 4 assets: weigh the raptor (masses/CoM are placeholders), real thrust-plane height, Pegasus thrust curve + PX4 airframe/gains
  for a 0.8 kg 5" whoop (the sim-only rate block in `raptor.params` is interim), `CA_ROTOR*` geometry, check the ZED mount against the
  camera image; site capture → `docker/sim/worlds/<site>`; scenario YAMLs `hover_check`, `square`, `survey_strip`, `inspect_structure`
- Phase 5 hardware: L4T/CUDA record, arm64 image pulls, udev `/dev/px4`, Pixracer flash + params, `real_drone.launch.py`, bench
  checklist → feed numbers back to the vehicle model. Our Orin NX is L4T **R39.2.1** (found by the 5.1-era Jetson commit 0f33b6f,
  merged into main 2026-10-21 with the 6.0 side kept): `docker/zed/build.sh jetson` now reads the L4T from the board and tags
  `bisg/zed:jetson` (untested on the Jetson). Not ported from 0f33b6f: FCU auto-detect (`/dev/px4` → USB PX4 → MAVLink UART,
  `scripts/fcu_probe.py`, `FCU_BAUD`) — the drone profile still needs `/dev/px4` or `DRONE_FCU_URL`
- Phase 6 swarm in sim: `vehicles:` list (2/4/8 work), `scripts/gen_compose.py`, `bisg_fleet`, VRAM budget (one sim per GPU, boots
  staggered). Phases 7-8: hardware swarm (zenoh/DDS plan, kill switch), scenario runner + CI

## Parked
ArduPilot backend · Isaac Lab / RL for swarm policies · per-drone lidar if one is ever mounted · ZED `Sim2Real` post-process
(`applyZedSim2Real`) to narrow the render-vs-camera gap
