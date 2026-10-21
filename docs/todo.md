# TODO

Live list only: finished items move to `archive/docs/todo-history-2026-10.md`. Phases and exit tests: [roadmap.md](roadmap.md).
Defects with causes: [bugs.md](bugs.md).

**State (2026-10-19):** single-drone twin on Isaac Sim 6.0, raptor in the **Warehouse** (`docker/sim/sim.yaml`: lamps ×0.5 +
ambient 2), GPS-denied by default (ZED VIO + LW20 + PMW3901 + baro). `./bisg vio check` / `vio bench` PASS there
([vio-campaign.md](vio-campaign.md)); `restamp_latency_ms` 100 on Workstation A. Kinetix flies whole-room tours on it.

## Now — ZED VIO / localization ([vio.md](vio.md), [vio-campaign.md](vio-campaign.md))
- [x] **R9 wrapper crash** `can't compare times with different time sources` — **fixed 2026-10-21** (ADR-011). Throw site
  (`terminate_bt`, 2026-10-20, 2 s after spatial mapping started): `handleVideoDepthPublishing()` default-constructs
  `rclcpp::Time pub_ts` (RCL_SYSTEM_TIME), `publishVideoDepth()` leaves it unset on a repeated grab and, with
  `sensors_image_sync` on (sim), `pub_ts != TIMEZERO_ROS` throws. A wrapper bug, fixed upstream in PR #460 (`cd8bf73`), in no
  release yet: the wrapper is pinned to master `b19902d` (`ZED_WRAPPER_REF`), SDK stays 5.4.1. Gate on it: `./bisg smoke` PASS,
  `vio_flight --alt 1.2 --side -1.0` PASS (1.9 / 3.5 / 2.2 cm), `zed_depth_box` PASS (−22.9 mm, was −26), `./bisg zed test` OK.
- [ ] Back to a wrapper **tag** once Stereolabs releases one containing `cd8bf73` (v5.5.1+); rebuild the Jetson image from the pin
  (`docker/zed/build.sh jetson`) before the next hardware run.
- [ ] **Streamed ZED Mini IMU is 90 deg rolled in the SDK** (found 2026-10-21): at rest the wrapper's `imu/data` (frame
  `zed_imu_link`, from the stream) reads accel (0, +9.81, 0), rpy (90, 0, −90); the sim's own IMU (`drone_1/zed_imu_link`) reads
  (0, 0, +9.81). The extension's `Imu_Sensor` prim is z-up and its conversion (`OgnZEDSimCameraNode.cpp`, unchanged in v5.3.0) streams
  (0, −9.81, 0) = image-frame "level", so the extra roll is on the SDK side. Effect: with `set_gravity_as_origin` on, the spatial
  map (`mapping/fused_cloud`) was rolled 90 deg about x (floor as a vertical plane); the sim now sets it off (zed.yaml `sim:`),
  after which the fused floor is flat (tilt 0.17 deg, z −0.10 m). Tracking is unaffected (`imu_fusion` off). **Report upstream**
  (zed-isaac-sim / ZED SDK) with these numbers; blocks any sim IMU fusion
- [ ] Fused cloud vs TF clocks: `fused_cloud` is stamped wall-clock now, the wrapper's TF with the streamed frame time (falls behind
  at ~rtf: −20 s, growing ~0.5 s per s, measured ~20 s after the wrapper started). Harmless for the map frame in Foxglove; matters for anything that looks TF up at the cloud's stamp (B17)
- [ ] **VIO drift on long flights**: EKF2 horizontal error vs ground truth grows with distance (0.8 m RMS over 351 m, 2.4 m over
  416 m, height within 0.15 m; a 108 m Kinetix tour stays at 0.19 m RMS). `tests/vio_bench.py` flies ~26 m, so the bench never sees
  it: add a long profile. Data: Kinetix `runs/2026101[78]-*_warehouse_room_*` (frames.jsonl + MCAP bags)
- [ ] VIO loop closure: ZED GEN_3 `area_memory` (zed.yaml `pos_tracking`, off) bounds drift on revisits; the bridge must raise the EV
  `reset_counter` on LOOP_CLOSED jumps or EKF2 rejects them. Sim drift is pessimistic: the twin has no 400 Hz IMU (`sim:` imu_fusion off)
- [ ] EKF2 map origin vs spawn differs between boots: z −0.14 / +0.12 m (baro height origin), x −0.12 m (ZED odom origin ahead of the
  body). Kinetix measures it at start; anything else that assumes map = world − spawn should too
- [ ] **Yaw oscillation with `EKF2_EVA_NOISE 0.1`** (vio-campaign.md §4.5): 2 of 18 flights at 0.1, 0 of 36 at 0.01; mechanism not
  verified. `vio_eval.py` has no oscillation detector and blamed the SDK once: add one (|truth yaw rate| > 30 deg/s, no yaw command)
- [ ] **Arming without VIO** (safety, [vio.md](vio.md#arming-without-vio-safety-open)): PX4 arms in OFFBOARD with the ZED down (EKF2's
  at-rest fake position); seen live, 1.5 m off at liftoff. Gate takeoff on the zed-bridge `odometry ok` in
  `bisg_vehicle` `offboard_controller.wait_ready` and the tests
- [ ] ZED pose jump without a frame gap (0.42 m in one sample): EKF2 resets to it; consider `EKF2_EV_CTRL 12` on the drone if the
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
  checklist → feed numbers back to the vehicle model
- Phase 6 swarm in sim: `vehicles:` list (2/4/8 work), `scripts/gen_compose.py`, `bisg_fleet`, VRAM budget (one sim per GPU, boots
  staggered). Phases 7-8: hardware swarm (zenoh/DDS plan, kill switch), scenario runner + CI

## Parked
ArduPilot backend · Isaac Lab / RL for swarm policies · per-drone lidar if one is ever mounted · ZED `Sim2Real` post-process
(`applyZedSim2Real`) to narrow the render-vs-camera gap
