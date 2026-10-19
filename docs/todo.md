# TODO

Live list only: finished items move to `archive/docs/todo-history-2026-10.md`. Phases and exit tests: [roadmap.md](roadmap.md).
Defects with causes: [bugs.md](bugs.md).

**State (2026-10-19):** single-drone twin on Isaac Sim 6.0, raptor in the **Warehouse** (`docker/sim/sim.yaml`: lamps ×0.5 +
ambient 2), GPS-denied by default (ZED VIO + LW20 + PMW3901 + baro). `./bisg vio check` / `vio bench` PASS there
([vio-campaign.md](vio-campaign.md)); `restamp_latency_ms` 100 on Workstation A. Kinetix flies whole-room tours on it.

## Now — ZED VIO / localization ([vio.md](vio.md), [vio-campaign.md](vio-campaign.md))
- [ ] **R9 wrapper crash** `can't compare times with different time sources` (exit -6, the `zed` container then stays down: B18).
  Seen 2026-10-10 (22 and 27 min), 2026-10-15 (17 s after tracking started, `publish_map_tf` off, so R2 did not fix it) and
  2026-10-17 (~24 min into a Kinetix room flight: no EV, EKF2 held position on flow + range, `xy_valid` 1, eph +2.5 cm/s).
  Every Time comparison in the wrapper's own code is on RCL_ROS_TIME and the IMU path is ROS-clock, so the throw is probably in a
  library (tf2_ros / image_transport / diagnostics). **Armed:** the `zed` service builds `docker/zed/debug/terminate_bt.cpp` and
  LD_PRELOADs it; the next crash prints the throw-site stack (`docker logs bisg-zed-1 | grep terminate_bt`). Not in `drone-zed` yet
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
