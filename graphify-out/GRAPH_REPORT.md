# Graph Report - bisg_isaac  (2026-10-07)

## Corpus Check
- 114 files · ~82,895 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 967 nodes · 1350 edges · 70 communities (50 shown, 18 thin omitted)
- Extraction: 92% EXTRACTED · 7% INFERRED · 1% AMBIGUOUS · INFERRED: 91 edges (avg confidence: 0.83)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Shared CLI Helpers
- Sim Launcher App
- Perf and Migration Notes
- Obstacle Sector Bridge
- ZED Launch and Debugging
- ZED Config Compiler
- Build Scripts and Common
- ZED Benchmark Harness
- Known Bugs Register
- Configuration Layering
- Pins and ADR-003
- Drone Endpoints and Hardware
- Interface Contract and Migration
- Todo and ZED Autostart
- MAVROS Operations
- Rig Bugs and Fixes
- launch.sh Commands
- Vehicle Interface Contract
- Debug Commands
- PX4 Bridge CLI Tests
- View Settings and Docker-first
- RTF and ZED SDK Check
- Follow Camera
- Clock, GPS-denied and px4-bridge
- vio_mock (removed)
- PX4 SITL and sim-launch Skills
- ZED SDK Skill and Swarm
- Remote Viewing Runbook
- ZED-only Sim Modules
- single_iris Scenario
- Tailscale ADR-009
- Project Instructions
- bisg.conf and Compose
- tailscale.sh
- zed.sh
- Jetson Deploy
- headless_fast Scenario
- PX4 Param Files
- push_px4_params
- px4-bridge.sh
- WebRTC View
- Low-res VIO Scenario
- Tailscale Service
- ZED Depth Box Test
- ROS Tools (rviz/rqt)
- px4-bridge Entrypoint
- sim Entrypoint
- Hover Stability Test
- drone.sh
- ros_tools.py
- MAVROS sim_time
- fetch_sources.sh
- Hold Position Test
- bisg Wrapper
- ros Entrypoint
- Bridge Package
- RTF Fix
- Driver Constraint
- Sim Container Paths
- Ready Markers
- Sim IMU
- AI Modules Bench
- Wrapper Toggles
- pull_images.sh
- setup.sh
- Sim Assets
- B10 Entrypoint Bug
- B12 GUI Profile

## God Nodes (most connected - your core abstractions)
1. `launch.sh script` - 17 edges
2. `Rate` - 16 edges
3. `debug.sh script` - 16 edges
4. `Health` - 15 edges
5. `Flight` - 15 edges
6. `Px4BridgeCli` - 14 edges
7. `build_phases()` - 14 edges
8. `TODO live list` - 14 edges
9. `single_iris.yaml scenario` - 14 edges
10. `StackConfig` - 13 edges

## Surprising Connections (you probably didn't know these)
- `MAVROS launch wrapper (bisg_bringup mavros.launch.py)` --semantically_similar_to--> `MAVROS plugin_allowlist (17 plugins)`  [INFERRED] [semantically similar]
  .claude/skills/mavros-ops/SKILL.md → docker/ros/mavros_lean.yaml
- `CycloneDDS Dockerfile.overlay` --semantically_similar_to--> `Cyclone DDS overlay for ZED L4T image`  [INFERRED] [semantically similar]
  docker/zed/README.md → .claude/skills/jetson-deploy/SKILL.md
- `web and webrtc remote views` --semantically_similar_to--> `SIM_VIEW setting`  [INFERRED] [semantically similar]
  .claude/skills/sim-launch/SKILL.md → CLAUDE.md
- `bugs.md B2 rmem_max` --conceptually_related_to--> `net.core.rmem_max UDP buffer sysctl`  [INFERRED]
  docker/sim/configs/single_iris_vio_lowres.yaml → docs/setup.md
- `headless_fast scenario run` --references--> `headless_fast.yaml scenario`  [EXTRACTED]
  docs/runbook-sim.md → docker/sim/configs/headless_fast.yaml

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pin-change regression gate** — claude_skills_sim_regression_skill_migration_gate, docker_sim_configs_four_iris_nozed, docker_sim_configs_eight_iris_nozed [INFERRED 0.75]
- **Selectable PX4 bridge options** — docs_decisions_adr_001_mavros_px4_bridge_selectable_service, docs_decisions_adr_001_mavros_mavros_bridge, docs_decisions_adr_001_mavros_mavsdk, docs_decisions_adr_001_mavros_uxrce_dds, docs_configuration_px4_bridge_key [EXTRACTED 1.00]
- **ZED stack: one YAML, one image, three services** — docs_zed_stack_zed_yaml, docs_decisions_adr_008_zed_stack_bisg_zed_image, docs_decisions_adr_008_zed_stack_zed_bridge_service, docs_decisions_adr_008_zed_stack_zed_video_service, docs_decisions_adr_008_zed_stack_zed_stack_compiler [EXTRACTED 0.95]
- **Isaac 6.0 sim-speed regression, cause, patch and docs** — docs_migration_errors_m8_sim_speed_regression, docs_migration_errors_m9_render_false, docs_migration_errors_m20_performance_doc_stale [INFERRED 0.85]
- **Interchangeable PX4 bridge backends** — docs_px4_bridge_px4_bridge_service, docs_plan_mavros, docs_px4_bridge_mavsdk_server, docs_px4_bridge_xrce_agent [EXTRACTED 1.00]
- **ZED SDK in sim: twin, wrapper, PX4 bridge** — _claude_skills_zed_sdk_skill_zed_isaac_sim_extension, docker_compose_zed_service, docker_compose_zed_bridge_service, docker_zed_zed [INFERRED 0.85]
- **GPS-denied VIO configuration** — docker_sim_configs_single_iris_vio, docker_sim_px4_readme_ekf2_vision, docker_zed_zed_sim_block, docker_zed_zed_services_px4_bridge [EXTRACTED 0.95]
- **ZED SDK in sim pipeline** — docs_plan_zed_isaac_sim_ext, docs_plan_zed_ros2_wrapper, docs_bugs_bridge_odometry, docs_plan_px4_v1_17_0, docs_plan_mavros [INFERRED 0.85]
- **MAVROS plugin parameter and timing bugs** — docs_bugs_b3, docs_bugs_b6, docs_bugs_b8, docs_bugs_mavros_sim_time_py [EXTRACTED 1.00]
- **Sim real-time-factor levers and bottleneck** — docs_performance_python_bottleneck, sim_launcher_pegasus_fast, docs_performance_physics_dt, docs_performance_parallel_sims, docs_performance_render_cadence [INFERRED 0.85]
- **ZED SDK in sim pipeline** — docs_zed_sdk_sim_zed_isaac_sim_extension, docs_zed_sdk_sim_fixedjoint_mount, docs_zed_sdk_sim_ipc_stream, docs_zed_sdk_sim_zed_wrapper [EXTRACTED 0.95]
- **ZED to PX4 bridge modules** — docs_zed_stack_health_module, docs_zed_stack_odometry_module, docs_zed_stack_obstacle_distance_module, docs_zed_stack_px4_bridge_service [EXTRACTED 0.95]
- **Settings layering files** — docs_configuration_bisg_conf, docs_configuration_docker_env, docs_configuration_scenario_yaml, docs_zed_stack_zed_yaml [EXTRACTED 0.95]
- **Remote sim viewing transports** — docs_remote_access_web_view, docs_remote_access_webrtc_view, docs_remote_access_tailscale_service, docs_remote_access_sim_view_addr [EXTRACTED 1.00]
- **HD720 image path needs rmem_max or low-res scenario** — docs_setup_rmem_max_sysctl, docs_setup_cyclonedds_xml, docker_sim_configs_single_iris_vio_lowres_resolution, docker_sim_configs_single_iris_zed_sensor [INFERRED 0.85]
- **ZED benchmark resource findings** — docs_zed_benchmark_base_pipeline_cost, docs_zed_benchmark_ram_constraint, docs_zed_benchmark_ai_startup, docs_zed_benchmark_bridge_container [EXTRACTED 1.00]

## Communities (70 total, 18 thin omitted)

### Community 0 - "Shared CLI Helpers"
Cohesion: 0.06
Nodes (16): Context, Module, Rate, Shared pieces of the bridge modules (rclpy only where a function needs a node)., Messages per second over a sliding window, and how long ago the last one came…, Base of a bridge module. `status()` is polled once a second by the health…, What every module needs to know: namespaces and a way to reach the others., Health (+8 more)

### Community 1 - "Sim Launcher App"
Cohesion: 0.06
Nodes (33): Rotation, App, apply_px4_params(), load_scenario(), main(), phase(), Serve the viewport as a still image over one TCP port. The WebRTC client needs…, bisg_isaac Pegasus launcher — YAML-driven Isaac Sim standalone app. /isaac-… (+25 more)

### Community 2 - "Perf and Migration Notes"
Cohesion: 0.05
Nodes (47): PX4-link study, asyncRendering flags hang boot, Isaac Sim 6.0 RTF measurements (RTX 4500), Two sims one per GPU for 8 drones, Single-thread Pegasus Python bottleneck (M8), isaac-cache-kit shader cache (190 s first boot), Workstation B 2x RTX 6000 Ada measurements, ADR-001..005, ADR-009 decisions (+39 more)

### Community 3 - "Obstacle Sector Bridge"
Cohesion: 0.07
Nodes (16): Image, Depth image -> 72 x 5 deg obstacle sectors. numpy only, so it is unit-testable…, Depth image (H x W, metres, float32) + pinhole intrinsics -> 72 ranges [m]: inf…, sectors_from_depth(), main(), Image, Node, ROS 2 image topic -> RTP/H.264 over UDP, for QGroundControl's "UDP h.264 Video… (+8 more)

### Community 4 - "ZED Launch and Debugging"
Cohesion: 0.05
Nodes (41): zed_wrapper for drone N, with the contract's topic names. Used by BOTH the sim…, ZED_RMW, Debugging (doc), debug clean-cache / clean-all / setup --rebuild, ./bisg debug dds, ./bisg debug gpu, ./bisg debug kitlog, ./bisg debug perf (rtf heartbeat) (+33 more)

### Community 5 - "ZED Config Compiler"
Cohesion: 0.09
Nodes (28): ConfigError, deep_merge(), _flatten_params(), load(), docker/zed/zed.yaml -> zed_wrapper parameters + the list of services to start.…, {section: {key: default}} from the wrapper's own YAML files (the model file…, Module master switch. Modules without `enabled` (camera, video, sensors,…, The text of the `ros_params_override_path` file. (+20 more)

### Community 6 - "Build Scripts and Common"
Cohesion: 0.08
Nodes (30): build_isaac_ext.sh script, stamp(), _BISG_ENV0, BISG_SRC, conf_default(), container_running(), die(), fail() (+22 more)

### Community 7 - "ZED Benchmark Harness"
Cohesion: 0.11
Nodes (28): Bench, build_phases(), chk_cloud(), chk_depth(), chk_depth_extras(), chk_images(), chk_imu(), chk_mapping() (+20 more)

### Community 8 - "Known Bugs Register"
Cohesion: 0.08
Nodes (23): Known bugs register, B1 No usable failsafe while GPS-denied, B17 SDK odometry into PX4 accuracy outside bound, B18 SDK connects to sim stream once per run, B19 enable_streaming crashes wrapper in sim, B2 HD720 ZED images never reach subscriber, B3 MAVROS plugin nodes ignore --params-file, B5 Pegasus state topics stamped with wall time (+15 more)

### Community 9 - "Configuration Layering"
Cohesion: 0.07
Nodes (36): Configuration (doc), Adding a key procedure, config/bisg.conf, cmd_config (./bisg config), scripts/_common.sh conf_default, docker/.env (machine-only), Version pins and repo links, Config precedence (+28 more)

### Community 10 - "Pins and ADR-003"
Cohesion: 0.08
Nodes (27): build.sh script, src_stamp(), ADR-003 One PX4 tag for SITL and Pixracer, MAVROS 2.15.1, Pegasus PR #144 head fcb99c0, px4_fmu-v4_default Pixracer firmware (95.3% flash), PX4_TAG Dockerfile arg, Re-validation on Isaac Sim 6.0 (2026-10-02) (+19 more)

### Community 11 - "Drone Endpoints and Hardware"
Cohesion: 0.08
Nodes (24): Endpoint keys (DRONE_ID, FCU_URL, GCS_URL, ROS_DOMAIN_ID), PX4_BRIDGE / MAVROS_PLUGINS / MAVSDK_PORT / XRCE_PORT, Bench checklist (Phase 5, props OFF), bisg_quad vehicle model measurements (Phase 4), EKF2_EV_CTRL / EKF2_HGT_REF vision fusion, EKF2_EV_DELAY, Offboard-loss failsafe (COM_OF_LOSS_T), PX4 parameter set (docker/sim/px4/<drone_n>.params) (+16 more)

### Community 12 - "Interface Contract and Migration"
Cohesion: 0.09
Nodes (24): Topics provided by the vehicle, ZED wrapper 5.4.1 topic names, Isaac Sim 6.0 migration errors and gotchas, M12 deprecated APIs still in use, M14 smoke test --patience for low RTF, M19 changed Pegasus/launcher semantics, M1 PX4 v1.16.0 SITL build IndexError, M20 performance.md is 5.1-era (+16 more)

### Community 13 - "Todo and ZED Autostart"
Cohesion: 0.08
Nodes (25): Real ZED SDK in the sim (ZED_SOURCE=sdk), TODO live list, ZED_AUTOSTART / ROS_TOOLS_AUTOSTART, B16 contract TF frame prefix, B18 SDK connects once per sim run, B19 streaming crashes wrapper in sim, Bench day (Orin NX + Pixracer + ZED Mini), SIM_GPU / ZED_GPU split (+17 more)

### Community 14 - "MAVROS Operations"
Cohesion: 0.09
Nodes (23): mavros-ops skill, MAVROS frames (ENU map, odom/base_link), GPS-denied EV yaw-align limitation (fly and land in OFFBOARD), MAVROS launch wrapper (bisg_bringup mavros.launch.py), MAVROS 2.15.1 plugin nodes ignore params files, OFFBOARD state machine (offboard_controller), Sim time and PX4 timesync (use_sim_time), sim-regression skill (+15 more)

### Community 15 - "Rig Bugs and Fixes"
Cohesion: 0.09
Nodes (25): B13 No automated camera-view-unobstructed check, B15 Sim rig parameters duplicate wrapper config, B16 Contract TF frames drone_n prefixed but wrapper cannot prefix, Fixed B9 ZED images ignored rate gate, Fixed: ZED camera blocked/backwards/wrong FOV, sim/launcher/zed_rig.py (emulated rig), docker/zed/zed.yaml, CycloneDDS + zenoh-bridge-ros2dds (+17 more)

### Community 16 - "launch.sh Commands"
Cohesion: 0.21
Nodes (21): cmd_all(), cmd_build(), cmd_config(), cmd_down(), cmd_logs(), cmd_mavros(), cmd_restart(), cmd_ros() (+13 more)

### Community 17 - "Vehicle Interface Contract"
Cohesion: 0.10
Nodes (21): Vehicle interface contract, /clock sim time, Frame prefix gap (B16), /drone_<n> namespace = MAV_SYS_ID, QoS policy, TF frame tree map-odom-base_link-zed frames, Topics consumed by the vehicle, Project plan - bisg_isaac digital twin (+13 more)

### Community 18 - "Debug Commands"
Cohesion: 0.26
Nodes (18): cmd_clean_all(), cmd_clean_cache(), cmd_dds(), cmd_echo(), cmd_gpu(), cmd_hz(), cmd_kitlog(), cmd_mavlink() (+10 more)

### Community 19 - "PX4 Bridge CLI Tests"
Cohesion: 0.21
Nodes (4): bridge(), compose_service(), Px4BridgeCli, ./bisg px4-bridge: one compose service (px4-bridge), PX4_BRIDGE picks what its…

### Community 20 - "View Settings and Docker-first"
Cohesion: 0.16
Nodes (16): SIM_MODE (replaced), SIM_STREAM (resolved value), SIM_VIEW, SIM_VIEW_ADDR / SIM_WEB_PORT, TAILSCALE_HOSTNAME / TAILSCALE_EXTRA_ARGS, ADR-002 Docker-first including Isaac Sim, bisg/sim, bisg/ros, bisg/zed images, compose profiles sim, sim-headless, ros, jetson (+8 more)

### Community 21 - "RTF and ZED SDK Check"
Cohesion: 0.19
Nodes (9): Sim rtf ~0.35 (Pegasus Python cost, M8), main(), path_length(), Probe, Node, rate(), ZED SDK contract + health check — the same script for the sim and the real…, RMSE (m) of the SDK odometry against ground truth after the only alignment that… (+1 more)

### Community 22 - "Follow Camera"
Cohesion: 0.29
Nodes (4): FollowCam, Follow camera for the GUI viewport, in the spirit of Gazebo's "follow" mode:…, Put the camera at `offset` in the drone's body frame, looking at it., _wrap()

### Community 23 - "Clock, GPS-denied and px4-bridge"
Cohesion: 0.17
Nodes (13): app.ros_clock (/clock), sensors.zed ZED Mini twin (zed_sdk_rig.py), GPS-denied divergence from wall clock, vio_flight OFFBOARD arming rule, px4-bridge compose service, PX4_BRIDGE variable (mavros|mavsdk|xrce|none), vio_mock (bisg_vehicle, removed), zed-bridge service (health, odometry, obstacle_distance) (+5 more)

### Community 24 - "vio_mock (removed)"
Cohesion: 0.20
Nodes (6): main(), Node, vio_mock — sim-only mock VIO source (docs/interface-contract.md, zed-contract…, VioMock, PoseStamped, TwistStamped

### Community 25 - "PX4 SITL and sim-launch Skills"
Cohesion: 0.18
Nodes (11): px4-sitl skill, Common arming/offboard rejections, PX4 instance/port/sys-id math, Lockstep off in SITL, sim-launch skill, Isaac 6.0 kit shader cache volume, web and webrtc remote views, ADR-001 MAVROS as PX4 bridge (+3 more)

### Community 26 - "ZED SDK Skill and Swarm"
Cohesion: 0.18
Nodes (11): zed-sdk skill, SDK connects once per sim run (B18), ZED asset FixedJoint to vehicle body, Stereolabs zed-isaac-sim extension, swarm-spawn skill, Workstation VRAM limits for swarms, ZED SDK per drone (stream port 30000+2*id), zed service (wrapper against sim twin) (+3 more)

### Community 27 - "Remote Viewing Runbook"
Cohesion: 0.22
Nodes (11): Watching the sim from somewhere else, Cloudflare Tunnel (does not carry WebRTC), VS Code tunnel / Simple Browser path, SIM_VIEW=web (TCP 8899 still frames), Runbook - simulation stack, ./bisg CLI cheat sheet, headless_fast scenario run, MAVROS smoke connection (+3 more)

### Community 28 - "ZED-only Sim Modules"
Cohesion: 0.22
Nodes (9): Sim frame-rate IMU: imu_fusion false, Real ZED SDK is the only ZED source in sim (emulated rig removed), zed-bridge service, camera module, depth module (NEURAL), object_detection module, odometry restamp (sim clock vs wall clock), services.px4_bridge (health, odometry, obstacle_distance) (+1 more)

### Community 29 - "single_iris Scenario"
Cohesion: 0.22
Nodes (10): single_iris.yaml scenario, follow_cam (sim/launcher/follow_cam.py), px4.enable_lockstep false, perf.pegasus_fast (sim/launcher/pegasus_fast.py), physics_dt 120 Hz, px4.params: [collision_prevention], Pegasus ROS2Backend ground truth state, Vehicle id / MAV_SYS_ID / MAVROS ns mapping (+2 more)

### Community 30 - "Tailscale ADR-009"
Cohesion: 0.20
Nodes (10): ADR-009 Remote access via Tailscale compose service, ADR-002 Docker-first reproducibility, TCP-only tunnels (SSH, Cloudflare, ngrok), ZeroTier (rejected), DDS discovery does not cross tailnet, No Tailscale auth keys policy, GCS_URL for QGroundControl over tailnet, tailscale compose service (+2 more)

### Community 31 - "Project Instructions"
Cohesion: 0.22
Nodes (9): ADR-002 every runtime component is containerized, bisg_isaac project instructions, Migration gating checks (smoke, vio_flight, zed_depth_box), Isaac Sim 6.0 stack (Pegasus PR 144, PX4 v1.17.0), Settings layering (bisg.conf, zed.yaml, .env, scenario YAML), Tailscale remote access (ADR-009), Workstation B GPU contention (vLLM vs Isaac), SIM_GPU / ZED_GPU split (+1 more)

### Community 32 - "bisg.conf and Compose"
Cohesion: 0.22
Nodes (7): config/bisg.conf (merged project settings), One key, one place rule, Compose profiles (sim, ros, zed, drone, tailscale), zed-video service, services.qgc_video, bisg_isaac README, bisg operator CLI

### Community 33 - "tailscale.sh"
Cohesion: 0.58
Nodes (8): backend(), connected(), login(), reach(), tailscale.sh script, start(), ts(), vcompose()

### Community 34 - "zed.sh"
Cohesion: 0.44
Nodes (8): have_frames(), zed.sh script, start_services(), svc_name(), video_hint(), video_ip(), ZED_SIM_PORT, zexec()

### Community 35 - "Jetson Deploy"
Cohesion: 0.29
Nodes (8): jetson-deploy skill, Cyclone DDS overlay for ZED L4T image, Pixracer flash and params, Preflight checklist (props on), drone-zed service (real camera), ZED SDK image README, docker/zed/build.sh (desktop / jetson), CycloneDDS Dockerfile.overlay

### Community 36 - "headless_fast Scenario"
Cohesion: 0.33
Nodes (7): headless_fast.yaml scenario, app.render: false, world preset Default Environment, Iris vehicle id 0 (ros2 disabled), perf.skip_material_loading, app.stream: off, sensors.zed.enabled: false

### Community 37 - "PX4 Param Files"
Cohesion: 0.33
Nodes (7): single_iris_vio scenario (GPS-denied), depth_box test cuboid, PX4 parameter files README, collision_prevention.params, ekf2_vision.params, PX4_PARAM_ env vars applied by rcS before EKF2, positional_tracking module

### Community 38 - "push_px4_params"
Cohesion: 0.38
Nodes (6): B11 push_px4_params cannot finish on SITL, encode(), load_params(), main(), Push PX4 EKF2/GPS params over MAVLink (Phase 3 — GPS-denied flight on ZED Mini…, PX4/MAVLink PARAM_SET always carries a float32 on the wire; non-REAL32 types…

### Community 39 - "px4-bridge.sh"
Cohesion: 0.38
Nodes (3): pcompose(), px4-bridge.sh script, stop()

### Community 40 - "WebRTC View"
Cohesion: 0.33
Nodes (6): app.stream webrtc, M4 WebRTC extension replaced in 6.0, SIM_VIEW_ADDR, View settings in config/bisg.conf, Isaac Sim WebRTC Streaming Client, SIM_VIEW=webrtc (TCP 49100 + UDP 47998)

### Community 41 - "Low-res VIO Scenario"
Cohesion: 0.33
Nodes (6): single_iris_vio_lowres.yaml scenario, bugs.md B2 rmem_max, Isaac Sim 6.0 migration use, ZED resolution [320, 180], single_iris_vio.yaml (extends parent), sensors.zed 320x180 block

### Community 42 - "Tailscale Service"
Cohesion: 0.33
Nodes (6): --accept-dns=false, No auth keys decision, Own compose project bisg-tailscale, tailscale service (v1.102.5, host network, NET_ADMIN), SIM_VIEW_ADDR=tailscale, bisg-tailscale_tailscale-state volume

### Community 43 - "ZED Depth Box Test"
Cohesion: 0.47
Nodes (5): load_scenario(), main(), quat_xyzw_to_matrix(), ZED depth check against a known box (scenario `world.objects`, e.g.…, Same `extends:` deep-merge as sim/launcher/launch.py.

### Community 44 - "ROS Tools (rviz/rqt)"
Cohesion: 0.40
Nodes (4): ros dev shell service (bisg-ros), ROS_TOOLS_AUTOSTART, foxglove bridge tool, rviz tool (enabled by default)

### Community 45 - "px4-bridge Entrypoint"
Cohesion: 0.70
Nodes (4): mavros(), mavsdk(), entrypoint.sh script, xrce()

### Community 46 - "sim Entrypoint"
Cohesion: 0.50
Nodes (4): isaac_python_exec(), ROS_DISTRO, entrypoint.sh script, SIM_CONFIG

### Community 47 - "Hover Stability Test"
Cohesion: 0.40
Nodes (3): physics_dt (also PX4 IMU rate), single_iris.yaml profile, Hover-stability test: arm -> takeoff to ALT m -> settle -> record ATTITUDE for…

### Community 48 - "drone.sh"
Cohesion: 0.50
Nodes (3): drone.sh script, ZED_STACK_SIM, zexec()

### Community 49 - "ros_tools.py"
Cohesion: 0.67
Nodes (3): load(), main(), Read / toggle docker/ros/tools.yaml (the ROS 2 tools bisg-ros runs on the host…

## Ambiguous Edges - Review These
- `B15 Sim rig parameters duplicate wrapper config` → `sim/launcher/zed_rig.py (emulated rig)`  [AMBIGUOUS]
  docs/bugs.md · relation: conceptually_related_to
- `B16 Contract TF frames drone_n prefixed but wrapper cannot prefix` → `sim/launcher/zed_rig.py (emulated rig)`  [AMBIGUOUS]
  docs/bugs.md · relation: conceptually_related_to
- `vio_mock (removed)` → `ZED bridge odometry module`  [AMBIGUOUS]
  docs/bugs.md · relation: conceptually_related_to
- `zed-isaac-sim extension v5.2.1` → `Emulated ZED rig fallback (removed)`  [AMBIGUOUS]
  docs/plan.md · relation: conceptually_related_to
- `zed-isaac-sim extension v5.2.1` → `vio_mock (older plan, removed)`  [AMBIGUOUS]
  docs/plan.md · relation: conceptually_related_to
- `bisg_vehicle/vio_mock (removed)` → `ZED SDK in sim (ZED_SOURCE=sdk)`  [AMBIGUOUS]
  docs/roadmap.md · relation: conceptually_related_to
- `The real ZED SDK in the sim (doc)` → `ZED_SOURCE=emulated rig and vio_mock (removed)`  [AMBIGUOUS]
  docs/zed-sdk-sim.md · relation: conceptually_related_to
- `docker/zed/zed.yaml` → `Emulated rig (zed_features.py)`  [AMBIGUOUS]
  docs/zed-stack.md · relation: conceptually_related_to
- `zed.yaml sim: block` → `Emulated rig (zed_features.py)`  [AMBIGUOUS]
  docs/zed-stack.md · relation: conceptually_related_to
- `ZED Mini model table` → `vio_relay`  [AMBIGUOUS]
  docs/hardware.md · relation: conceptually_related_to
- `vio_relay` → `Bench checklist (Phase 5, props OFF)`  [AMBIGUOUS]
  docs/hardware.md · relation: conceptually_related_to
- `zed-isaac-sim extension build` → `Emulated ZED rig (removed)`  [AMBIGUOUS]
  docs/setup.md · relation: conceptually_related_to
- `zed-bridge service (health, odometry, obstacle_distance)` → `vio_mock (bisg_vehicle, removed)`  [AMBIGUOUS]
  docs/todo.md · relation: conceptually_related_to
- `vio_mock (bisg_vehicle, removed)` → `GPS-denied divergence from wall clock`  [AMBIGUOUS]
  docs/runbook-sim.md · relation: conceptually_related_to

## Knowledge Gaps
- **179 isolated node(s):** `entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO`, `BISG_SRC`, `_BISG_ENV0` (+174 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 350 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `B15 Sim rig parameters duplicate wrapper config` and `sim/launcher/zed_rig.py (emulated rig)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `B16 Contract TF frames drone_n prefixed but wrapper cannot prefix` and `sim/launcher/zed_rig.py (emulated rig)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `vio_mock (removed)` and `ZED bridge odometry module`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `zed-isaac-sim extension v5.2.1` and `Emulated ZED rig fallback (removed)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `zed-isaac-sim extension v5.2.1` and `vio_mock (older plan, removed)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `bisg_vehicle/vio_mock (removed)` and `ZED SDK in sim (ZED_SOURCE=sdk)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `The real ZED SDK in the sim (doc)` and `ZED_SOURCE=emulated rig and vio_mock (removed)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._