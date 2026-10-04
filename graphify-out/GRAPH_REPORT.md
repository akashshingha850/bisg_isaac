# Graph Report - bisg_isaac  (2026-10-05)

## Corpus Check
- 102 files · ~72,548 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 884 nodes · 1495 edges · 78 communities (63 shown, 15 thin omitted)
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 118 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- ZED Stack Config Compiler
- Build and Common Scripts
- Bridge Module Base
- Drone Views Preview
- Pegasus and Isaac Launcher
- Bridge Health Module
- ADR-007 ZED in Sim
- Roadmap Phases
- VIO Flight Test
- Debug CLI
- Launch CLI
- Bridge Node Entry
- ADR-008 ZED Stack
- Interface Contract
- Isaac Rendering APIs
- Collision Prevention Test
- MAVROS Ops Skill
- Runbook and Setup
- Migration Errors
- Isaac USD Utilities
- Core ADRs
- ZED Docker Image
- Position Hold Test
- ZED SDK Check
- Scenario Configs
- Bugs Register
- Follow Camera
- RTF HUD
- Pegasus Fast Patch
- CLAUDE.md Rules
- ZED Rig and View Config
- Hardware Reference
- Bridge Common Helpers
- MAVROS Sim Time
- QGC Video Stream
- PX4 Params and Failsafe
- Compose and zed.yaml
- Obstacle Distance Module
- Debugging Guide
- Web View Stream
- Jetson Deploy Skill
- VIO Mock Node
- ZED Launch File
- Configuration Guide
- Docker Strategy and Pins
- VIO Source Modes
- Remote Viewing
- Third Eye Camera
- PX4 Param Push
- zed.sh Script
- Pegasus Force Patches
- Isaac 6.0 Stack Notes
- Multi-Vehicle Scenarios
- Odometry Module
- PX4 SITL Skill
- vio_mock Source
- Sim Entrypoint
- MAVROS Lean List
- Env Check Script
- drone.sh Script
- Compose ROS Services
- Compose Sim Services
- Vehicle Spawn
- Fetch Sources Script
- Scenario Loader
- bisg CLI
- ROS Entrypoint
- bisg_vehicle Setup
- ZED Build Script
- Bridge Package Init
- Pull Images Script
- Setup Script
- Site Worlds
- ROS2 Bridge Ext
- Physics Sensors Ext
- Legacy World API
- Rotation Util

## God Nodes (most connected - your core abstractions)
1. `Known bugs register` - 18 edges
2. `launch.sh script` - 17 edges
3. `ZedDepthProducts` - 17 edges
4. `Rate` - 16 edges
5. `debug.sh script` - 16 edges
6. `Health` - 15 edges
7. `Flight` - 15 edges
8. `CLAUDE.md (project instructions)` - 15 edges
9. `single_iris.yaml scenario` - 15 edges
10. `The real ZED SDK in the sim` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Migration / pin-change gate (smoke, vio_flight, zed_depth_box)` --semantically_similar_to--> `Three migration gating checks (smoke, vio_flight, zed_depth_box)`  [INFERRED] [semantically similar]
  .claude/skills/sim-regression/SKILL.md → CLAUDE.md
- `Isaac Sim + Pegasus + PX4 digital twin of Jetson/Pixracer/ZED drone` --semantically_similar_to--> `Ground rules (fresh start, phases, docker-first, contract)`  [INFERRED] [semantically similar]
  README.md → CLAUDE.md
- `MAVROS launch wrapper (bisg_bringup mavros.launch.py)` --semantically_similar_to--> `MAVROS plugin_allowlist (17 plugins)`  [INFERRED] [semantically similar]
  .claude/skills/mavros-ops/SKILL.md → docker/ros/mavros_lean.yaml
- `Quick start (bisg setup/up/smoke/zed)` --semantically_similar_to--> `Sim start/stop procedure (bisg up|wait|down)`  [INFERRED] [semantically similar]
  README.md → .claude/skills/sim-launch/SKILL.md
- `ZED_SOURCE emulated vs sdk` --semantically_similar_to--> `Real ZED SDK runs in the sim (ZED_SOURCE=sdk)`  [INFERRED] [semantically similar]
  .claude/skills/zed-sdk/SKILL.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **ZED stack services driven by docker/zed/zed.yaml** — docker_compose_service_zed, docker_compose_service_zed_bridge, docker_compose_service_zed_video, claude_skills_zed_sdk_skill_zed_yaml_single_switch [EXTRACTED 0.95]
- **Sim and real-drone service pairs sharing one image/launch file** — docker_compose_service_mavros, docker_compose_service_drone_mavros, docker_compose_service_zed, docker_compose_service_drone_zed, claude_skills_zed_sdk_skill_port_to_jetson [INFERRED 0.85]
- **Pin-change regression gate** — claude_skills_sim_regression_skill_migration_gate, claude_md_migration_gate_checks, docker_sim_configs_four_iris_nozed, docker_sim_configs_eight_iris_nozed [INFERRED 0.75]
- **Scenario YAML inheritance chain rooted at single_iris** — docker_sim_configs_single_iris, docker_sim_configs_single_iris_nozed, docker_sim_configs_single_iris_vio, docker_sim_configs_single_iris_vio_lowres, docker_sim_configs_two_iris_nozed, docker_sim_configs_two_iris_vio_lowres [EXTRACTED 1.00]
- **Four-layer configuration split (bisg.conf, zed.yaml, docker/.env, scenario YAML)** — docs_configuration_config_layers, docs_configuration_precedence, docker_zed_zed_yaml, docker_sim_configs_single_iris, docs_configuration_adding_a_key [EXTRACTED 1.00]
- **Core stack ADRs: Docker, MAVROS, PX4 pin, CycloneDDS, Jazzy** — docs_decisions_adr_001_mavros, docs_decisions_adr_002_docker, docs_decisions_adr_003_px4_version, docs_decisions_adr_004_dds, docs_decisions_adr_005_ros2_jazzy [INFERRED 0.95]
- **ZED stack: one YAML, one image, three services** — docs_zed_stack_zed_yaml, docs_decisions_adr_008_zed_stack_bisg_zed_image, docs_decisions_adr_008_zed_stack_zed_bridge_service, docs_decisions_adr_008_zed_stack_zed_video_service, docs_decisions_adr_008_zed_stack_zed_stack_compiler [EXTRACTED 0.95]
- **Real ZED SDK in sim: extension, FixedJoint mount, shared-memory stream, unmodified wrapper** — docs_decisions_adr_007_zed_sdk_in_sim_zed_isaac_sim_extension, docs_decisions_adr_007_zed_sdk_in_sim_fixed_joint_mount, docs_zed_sdk_sim_stream_architecture, docs_zed_sdk_sim_imu_fusion_false, docs_zed_sdk_sim_sim_published_imu [EXTRACTED 0.95]
- **Isaac 6.0 sim-speed regression, cause, patch and docs** — docs_migration_errors_m8_sim_speed_regression, docs_performance_pegasus_fast_patch, docs_migration_errors_m9_render_false, docs_performance_render_cadence_fix, docs_migration_errors_m20_performance_doc_stale [INFERRED 0.85]

## Communities (78 total, 15 thin omitted)

### Community 0 - "ZED Stack Config Compiler"
Cohesion: 0.06
Nodes (32): difflib, ConfigError, deep_merge(), _flatten_params(), load(), docker/zed/zed.yaml -> zed_wrapper parameters + the list of services to start.…, {section: {key: default}} from the wrapper's own YAML files (the model file…, Module master switch. Modules without `enabled` (camera, video, sensors,… (+24 more)

### Community 1 - "Build and Common Scripts"
Cohesion: 0.08
Nodes (25): build_isaac_ext.sh script, _BISG_ENV0, BISG_SRC, conf_default(), die(), fail(), FCU_URL, GCS_URL (+17 more)

### Community 2 - "Bridge Module Base"
Cohesion: 0.07
Nodes (8): Module, Rate, Messages per second over a sliding window, and how long ago the last one came…, Base of a bridge module. `status()` is polled once a second by the health…, Health, ObstacleDistance, MAVROS defaults the obstacle plugin to GLOBAL; ours is a body-frame (FRD) scan., Odometry2Px4

### Community 3 - "Drone Views Preview"
Cohesion: 0.09
Nodes (15): bisect, collections, DroneViews, Live drone views in the Isaac GUI: the ZED left camera image and its depth side…, Google Turbo colormap, 256 entries, as uint8 RGB (polynomial approximation)., Refresh the window if the interval has elapsed. Never raises., _turbo_lut(), _pack_rgb() (+7 more)

### Community 4 - "Pegasus and Isaac Launcher"
Cohesion: 0.10
Nodes (19): isaacsim, isaacsim_core_simulation_manager, omni_timeline, pegasus_simulator_logic_backends_px4_mavlink_backend, pegasus_simulator_logic_interface_pegasus_interface, pegasus_simulator_logic_vehicles_multirotor, pegasus_simulator_params, App (+11 more)

### Community 5 - "Bridge Health Module"
Cohesion: 0.14
Nodes (13): M10 — ZED health -> one status topic + STATUSTEXT in QGroundControl. Publishes…, json, mavros_msgs_msg, numpy, sensor_msgs_msg, std_msgs_msg, subprocess, Fake (+5 more)

### Community 6 - "ADR-007 ZED in Sim"
Cohesion: 0.14
Nodes (19): ADR-007 Real ZED SDK in the sim, ZED asset FixedJoint mount, One odometry source per run, Residual sim-vs-hardware ZED gap, Stereolabs zed-isaac-sim extension v5.2.1, ZED_SOURCE emulated|sdk switch, ZED wrapper 5.4.1 topic names, R5 ZED Mini not supported in Isaac (retired) (+11 more)

### Community 7 - "Roadmap Phases"
Cohesion: 0.15
Nodes (19): Phase 5 bench checklist (props off), NVIDIA Simulation Performance Optimization Handbook, Roadmap phases 0-8, Phase 1 Dockerized single-drone sim, Phase 2 ROS 2 + MAVROS control, Phase 3 Sensors, ZED contract, VIO, Phase 5 Hardware single drone, Phase 6 Swarm in sim (+11 more)

### Community 8 - "VIO Flight Test"
Cohesion: 0.15
Nodes (5): Exception, Abort, Flight, main(), Fly to (dx, dy) from the start point at `alt` m above it; hold `settle` seconds.

### Community 9 - "Debug CLI"
Cohesion: 0.26
Nodes (18): cmd_clean_all(), cmd_clean_cache(), cmd_dds(), cmd_echo(), cmd_gpu(), cmd_hz(), cmd_kitlog(), cmd_mavlink() (+10 more)

### Community 10 - "Launch CLI"
Cohesion: 0.25
Nodes (17): cmd_all(), cmd_config(), cmd_down(), cmd_logs(), cmd_mavros(), cmd_restart(), cmd_ros(), cmd_shell() (+9 more)

### Community 11 - "Bridge Node Entry"
Cohesion: 0.15
Nodes (12): Context, What every module needs to know: namespaces and a way to reach the others., main(), python3 -m zed_stack.bridge — the px4_bridge service (compose `zed-bridge`).…, ROS 2 image topic -> RTP/H.264 over UDP, for QGroundControl's "UDP h.264 Video…, gi, gi_repository, signal (+4 more)

### Community 12 - "ADR-008 ZED Stack"
Cohesion: 0.14
Nodes (18): ADR-008 One YAML, one image, small services, bisg/zed single image, Shared compose.yaml profiles zed and drone, docker/zed/zed.yaml single config, Bridge modules not yet built, zed-bridge service (ZED to PX4 via MAVROS), zed_stack compile/validate, zed-video service (QGC video) (+10 more)

### Community 13 - "Interface Contract"
Cohesion: 0.14
Nodes (18): ZED Mini model table, Vehicle interface contract, Frame prefix gap (B16), /drone_<n> namespace = MAV_SYS_ID, Contract parity checks (check_contract.py), QoS policy, TF frame tree map-odom-base_link-zed frames, Topics provided by the vehicle (+10 more)

### Community 14 - "Isaac Rendering APIs"
Cohesion: 0.14
Nodes (16): isaacsim_core_experimental_utils_app, isaacsim_core_rendering_manager, isaacsim_core_utils, isaacsim_ros2_core_impl_camera_info_utils, isaacsim_sensors_camera_camera, omni_replicator_core, omni_syntheticdata, attach_zed_mini() (+8 more)

### Community 15 - "Collision Prevention Test"
Cohesion: 0.16
Nodes (12): argparse, csv, geometry_msgs_msg, mavros_msgs_srv, rclpy_parameter, Collision-prevention test: ZED depth -> obstacle_distance node -> MAVROS -> PX4…, Phase 3 exit test (docs/roadmap.md): GPS-denied flight on mock VIO. OFFBOARD…, load_scenario() (+4 more)

### Community 16 - "MAVROS Ops Skill"
Cohesion: 0.15
Nodes (16): Three migration gating checks (smoke, vio_flight, zed_depth_box), mavros-ops skill, MAVROS frames (ENU map, odom/base_link), GPS-denied EV yaw-align limitation (fly and land in OFFBOARD), MAVROS launch wrapper (bisg_bringup mavros.launch.py), MAVROS 2.15.1 plugin nodes ignore params files, OFFBOARD state machine (offboard_controller), Sim time and PX4 timesync (use_sim_time) (+8 more)

### Community 17 - "Runbook and Setup"
Cohesion: 0.13
Nodes (17): /clock sim time, M14 smoke test --patience for low RTF, Workstation OS migration 22.04 to 24.04, Runbook simulation stack, ./bisg CLI cheat sheet, Common failures and fixes, Paths inside the sim container, Launcher must be PID 1 (entrypoint execs python directly) (+9 more)

### Community 18 - "Migration Errors"
Cohesion: 0.18
Nodes (17): Isaac Sim 6.0 migration errors and gotchas, M12 deprecated APIs still in use, M19 changed Pegasus/launcher semantics, M1 PX4 v1.16.0 SITL build IndexError, M20 performance.md is 5.1-era, M3 IMUSensor import moved to experimental.physics, M5 base image healthcheck can never pass, M6 persistent shader cache volume (+9 more)

### Community 19 - "Isaac USD Utilities"
Cohesion: 0.15
Nodes (15): isaacsim_core_utils_extensions, isaacsim_core_utils_prims, omni_graph_core, omni_usd, pxr, ext_folder(), Stdlib-only half of the ZED SDK mode (zed_sdk_rig.py): decisions that launch.py…, Folder holding the built extension (docker/zed/build_isaac_ext.sh). Checked… (+7 more)

### Community 20 - "Core ADRs"
Cohesion: 0.15
Nodes (14): ADR-001 MAVROS as PX4-ROS 2 bridge, ADR-002 Docker-first runtime, ADR-005 ROS 2 Jazzy on Ubuntu 24.04, Ground rules (fresh start, phases, docker-first, contract), Settings layering (bisg.conf, docker/.env, scenario YAML), Remote view (web / webrtc streaming), Sim start/stop procedure (bisg up|wait|down), ZED SDK run procedure (ext-build, image, up, check) (+6 more)

### Community 21 - "ZED Docker Image"
Cohesion: 0.23
Nodes (15): docker/zed README (ZED SDK image), docker/zed/build.sh (desktop|jetson builds), CycloneDDS overlay (Dockerfile.overlay), bisg/zed images (desktop, l4t-r38), ADR-002 Docker-first including Isaac Sim, bisg/sim, bisg/ros, bisg/zed images, network_mode host everywhere, ADR-004 CycloneDDS everywhere, zenoh bridge over WiFi (+7 more)

### Community 22 - "Position Hold Test"
Cohesion: 0.16
Nodes (11): math, pymavlink, statistics, main(), pump(), wait(), Position-hold test (GPS scenario, e.g. single_iris_nozed): arm -> takeoff to…, main() (+3 more)

### Community 23 - "ZED SDK Check"
Cohesion: 0.17
Nodes (9): rosgraph_msgs_msg, main(), path_length(), Probe, Node, rate(), ZED SDK contract + health check — the same script for the sim (ZED_SOURCE=sdk)…, RMSE (m) of the SDK odometry against ground truth after the only alignment that… (+1 more)

### Community 24 - "Scenario Configs"
Cohesion: 0.23
Nodes (14): headless_fast.yaml scenario, app.render false (physics-only stepping), perf.skip_material_loading, single_iris.yaml scenario, follow_cam (Gazebo-style follow camera), perf knobs block, 120 Hz physics step (physics_dt), px4 block (airframe, lockstep, params_file) (+6 more)

### Community 25 - "Bugs Register"
Cohesion: 0.21
Nodes (14): Known bugs register, B1 no usable failsafe while GPS-denied, B10 bisg/ros:arm64 old entrypoint, B11 push_px4_params.py cannot finish on SITL, B12 GUI profile not re-verified, B13 no automated camera-view obstruction check, B18 SDK connects to sim stream once per sim run, B2 HD720 ZED images never reach subscriber (+6 more)

### Community 26 - "Follow Camera"
Cohesion: 0.29
Nodes (4): FollowCam, Follow camera for the GUI viewport, in the spirit of Gazebo's "follow" mode:…, Put the camera at `offset` in the drone's body frame, looking at it., _wrap()

### Community 27 - "RTF HUD"
Cohesion: 0.17
Nodes (7): carb, install(), Real-time factor (sim seconds per wall second) as one more line of Kit's own…, main(), Phase 1 smoke test: arm -> takeoff to ALT m -> land -> disarm, over MAVLink to…, wait_until(), time

### Community 28 - "Pegasus Fast Patch"
Cohesion: 0.19
Nodes (7): logging, os, Per-step speed-ups for Pegasus on Isaac Sim 6.0 (docs/performance.md,…, Features, load_features(), _merge(), ZED SDK feature switches for the emulated sim rig: the same docker/zed/zed.yaml…

### Community 29 - "CLAUDE.md Rules"
Cohesion: 0.24
Nodes (12): CLAUDE.md (project instructions), Host facts (RTX 4500 Ada, driver 580, /opt/docker-data), Real ZED SDK runs in the sim (ZED_SOURCE=sdk), swarm-spawn skill, Workstation VRAM limits for swarms, ZED SDK per drone (stream port 30000+2*id), zed-contract skill, Contract-first rule (interface-contract.md changes first) (+4 more)

### Community 30 - "ZED Rig and View Config"
Cohesion: 0.24
Nodes (12): ZED Mini sim rig config (sensors.zed), ZED view overlay (accumulating depth map, FOV grid), zed.yaml (single ZED stack config), AI/optional modules (object detection, body tracking, mapping, plane, global localization, streaming, recording), Camera + Depth sensing modules (HD720, NEURAL_LIGHT), Positional tracking module (VIO, GEN_3/AUTO), services.px4_bridge (odometry, obstacle_distance, health), services.qgc_video (RTP H.264 to QGroundControl) (+4 more)

### Community 31 - "Hardware Reference"
Cohesion: 0.20
Nodes (12): Pixracer flash headroom (95.3% used), Hardware reference, Jetson Orin NX on JetPack 7.2, Pixracer flight controller (px4_fmu-v4), Vehicle model measurements (bisg_quad), Pixracer to Orin NX wiring, ZED Mini camera, Target architecture sim and hardware (+4 more)

### Community 32 - "Bridge Common Helpers"
Cohesion: 0.20
Nodes (8): copy, Shared pieces of the bridge modules (rclpy only where a function needs a node)., M1 — ZED positional tracking -> PX4 EKF2 external vision (MAVROS odometry/out).…, nav_msgs_msg, random, rclpy_node, rclpy_qos, tf2_ros

### Community 33 - "MAVROS Sim Time"
Cohesion: 0.20
Nodes (7): main(), Switch every MAVROS plugin node to use_sim_time:=true (sim stack only,…, M2 — ZED depth image -> PX4's 72-sector obstacle map (MAVROS obstacle/send ->…, Depth image -> 72 x 5 deg obstacle sectors. numpy only, so it is unit-testable…, rcl_interfaces_msg, rcl_interfaces_srv, rclpy

### Community 34 - "QGC Video Stream"
Cohesion: 0.25
Nodes (4): main(), Image, Node, VideoStream

### Community 35 - "PX4 Params and Failsafe"
Cohesion: 0.20
Nodes (11): EKF2_EV_DELAY rule, GPS-denied offboard-loss failsafe (open), PX4 parameter table, Topics consumed by the vehicle, physics_dt sets PX4 sensor rate (>=120 Hz), Scenario perf: block knobs, TODO live list, B17 SDK VIO closed-loop accuracy (+3 more)

### Community 36 - "Compose and zed.yaml"
Cohesion: 0.33
Nodes (9): docker/zed/zed.yaml as the single ZED config switch, Isaac cache named volumes, compose service drone-mavros (Pixracer serial), compose service drone-zed (real camera), compose service mavros, compose service sim / sim-headless (Isaac Sim + PX4 SITL), compose service zed (wrapper on sim twin), compose service zed-bridge (ZED to PX4 via MAVROS) (+1 more)

### Community 37 - "Obstacle Distance Module"
Cohesion: 0.36
Nodes (4): Image, Depth image (H x W, metres, float32) + pinhole intrinsics -> 72 ranges [m]: inf…, sectors_from_depth(), SectorTests

### Community 38 - "Debugging Guide"
Cohesion: 0.22
Nodes (10): B5 Pegasus state topics stamped with wall time, Version pins and source links, Debugging guide, Log locations, PX4 shell without QGC (bisg debug px4), Resetting (down, clean-cache, clean-all, setup --rebuild), ROS 2 graph debugging (bisg debug topics/hz/echo), ADR-003 One PX4 tag (v1.17.0) for SITL and Pixracer (+2 more)

### Community 39 - "Web View Stream"
Cohesion: 0.22
Nodes (5): Serve the viewport as a still image over one TCP port. The WebRTC client needs…, Issue one viewport capture if the interval has elapsed. Never raises., WebView, do_GET(), _send()

### Community 40 - "Jetson Deploy Skill"
Cohesion: 0.22
Nodes (8): jetson-deploy skill, Bench and preflight checklists (props on safety), Jetson images (native build, L4T r38, JetPack 7.2), Pixracer flash and parameterise (px4_fmu-v4), ZED hardware parity check (zed_sdk_check --no-gt), Port ZED setup to the Jetson, PX4 parameter files (SITL and Pixracer), Compose profiles (sim, sim-headless, ros, tools, zed, drone)

### Community 41 - "VIO Mock Node"
Cohesion: 0.22
Nodes (5): main(), Node, VioMock, PoseStamped, TwistStamped

### Community 42 - "ZED Launch File"
Cohesion: 0.22
Nodes (7): zed_wrapper for drone N, with the contract's topic names. Used by BOTH the sim…, launch, launch_actions, launch_launch_description_sources, launch_ros_actions, launch_ros_substitutions, launch_substitutions

### Community 43 - "Configuration Guide"
Cohesion: 0.22
Nodes (9): Configuration guide, Procedure for adding a config key, Config layers (bisg.conf, zed.yaml, docker/.env, scenario YAML), Setting precedence (flag > env > .env > bisg.conf > fallbacks), SIM_VIEW key (gui|headless|web|webrtc|both|auto), NVML driver/library version mismatch fix, Sim slower than real time (rtf < 1.0 stretches PX4 sim time), Symptom to command table (+1 more)

### Community 44 - "Docker Strategy and Pins"
Cohesion: 0.29
Nodes (8): M18 Pegasus pin only on PR ref, Docker strategy three image families, ./bisg setup steps, Pinned upstream sources, Local submodule branch workflow, PegasusSimulator PR #144 head fcb99c0, PX4-Autopilot source, zed-ros2-wrapper v5.4.1

### Community 45 - "VIO Source Modes"
Cohesion: 0.29
Nodes (6): VIO source per mode (vio_mock / SDK / vio_relay), SDK odometry to PX4 via bridge (restamp, B17 clock), compose service ros (dev shell), compose service vehicle (vio_mock), Parity rule: nodes must not import isaacsim/pegasus/omni, Shared ROS 2 packages (bisg_msgs, bisg_vehicle, bisg_fleet, bisg_bringup)

### Community 46 - "Remote Viewing"
Cohesion: 0.33
Nodes (7): M4 WebRTC extension replaced in 6.0, Watching the sim remotely, Cloudflare Tunnel cannot carry WebRTC UDP, SIM_VIEW settings keys, VPN (Tailscale) for UDP path, SIM_VIEW=web still-frame browser view, SIM_VIEW=webrtc interactive stream

### Community 47 - "Third Eye Camera"
Cohesion: 0.33
Nodes (6): scipy_spatial_transform, attach_third_eye(), Rotation, _quat_wxyz(), External trailing camera for a vehicle (no ROS topics)., Attach a camera behind and above the drone. Local coordinates use FLU axes.

### Community 48 - "PX4 Param Push"
Cohesion: 0.38
Nodes (6): encode(), load_params(), main(), Push PX4 EKF2/GPS params over MAVLink (Phase 3 — GPS-denied flight on ZED Mini…, PX4/MAVLink PARAM_SET always carries a float32 on the wire; non-REAL32 types…, struct

### Community 49 - "zed.sh Script"
Cohesion: 0.52
Nodes (6): have_frames(), zed.sh script, start_services(), svc_name(), ZED_SIM_PORT, zexec()

### Community 50 - "Pegasus Force Patches"
Cohesion: 0.43
Nodes (6): apply(), apply_force(), apply_torque(), handle_propeller_visual(), _prim(), update()

### Community 51 - "Isaac 6.0 Stack Notes"
Cohesion: 0.33
Nodes (6): Isaac Sim 6.0 stack (Pegasus PR #144, PX4 v1.17.0, Python 3.12), PX4 v1.16.0 vs v1.17.0 tag notes, RTX shader cache volume isaac-cache-kit, sim-regression skill, Regression triage (boot timeout, flaky position asserts), Isaac Sim 6.0 ZED rig notes (zed_rig.py)

### Community 52 - "Multi-Vehicle Scenarios"
Cohesion: 0.40
Nodes (6): vehicle id numbering (PX4 instance = id, SYS_ID = id+1, ns /drone_{id+1}), single_iris_vio_lowres.yaml scenario (320x180 ZED), two_iris_nozed.yaml scenario, two_iris_vio_lowres.yaml scenario, Endpoint keys (DRONE_ID, FCU_URL, GCS_URL, ROS_DOMAIN_ID), Re-validation on Isaac Sim 6.0 (v1.16.0 vs v1.17.0)

### Community 53 - "Odometry Module"
Cohesion: 0.40
Nodes (3): main(), spin(), wait()

### Community 54 - "PX4 SITL Skill"
Cohesion: 0.50
Nodes (5): px4-sitl skill, Common PX4 rejections (offboard, arming, mag), Lockstep off in SITL, sim-launch skill, Sim diagnosis checklist

### Community 55 - "vio_mock Source"
Cohesion: 0.40
Nodes (5): Pegasus ROS2Backend state topics (pub_state), vio_mock odometry source, same ZED image in sim (compose service zed), B7 vio_mock too optimistic (zero twist covariance, no drift), ZED_SOURCE key (emulated|sdk)

### Community 56 - "Sim Entrypoint"
Cohesion: 0.50
Nodes (4): isaac_python_exec(), ROS_DISTRO, entrypoint.sh script, SIM_CONFIG

### Community 57 - "MAVROS Lean List"
Cohesion: 0.70
Nodes (5): ADR-001 MAVROS as PX4-ROS 2 bridge, MAVROS lean plugin list (mavros_lean.yaml), MAVROS, MAVSDK (lighter alternative behind decision gate), uXRCE-DDS (rejected alternative)

### Community 58 - "Env Check Script"
Cohesion: 0.70
Nodes (4): die(), pass(), check_env.sh script, wrn()

### Community 59 - "drone.sh Script"
Cohesion: 0.50
Nodes (3): drone.sh script, ZED_STACK_SIM, zexec()

### Community 60 - "Compose ROS Services"
Cohesion: 0.50
Nodes (4): mavros service (per-drone), ros dev shell service, x-ros-base anchor (bisg/ros:jazzy image), vehicle service (vio_mock)

### Community 61 - "Compose Sim Services"
Cohesion: 0.50
Nodes (4): x-nvidia runtime anchor, sim service (GUI profile), x-sim-base anchor (bisg/sim image), sim-headless service

### Community 62 - "Vehicle Spawn"
Cohesion: 0.50
Nodes (3): resolve_vehicle_usd(), `emulated` (Isaac cameras publish the contract topics, zed_rig.py) or `sdk`…, zed_source()

## Ambiguous Edges - Review These
- `Workstation VRAM limits for swarms` → `Host facts (RTX 4500 Ada, driver 580, /opt/docker-data)`  [AMBIGUOUS]
  .claude/skills/swarm-spawn/SKILL.md · relation: conceptually_related_to

## Knowledge Gaps
- **61 isolated node(s):** `pull_images.sh script`, `x-nvidia runtime anchor`, `sim service (GUI profile)`, `sim-headless service`, `mavros service (per-drone)` (+56 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 282 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `Workstation VRAM limits for swarms` and `Host facts (RTX 4500 Ada, driver 580, /opt/docker-data)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `SIM_VIEW key (gui|headless|web|webrtc|both|auto)` connect `Configuration Guide` to `Core ADRs`, `CLAUDE.md Rules`?**
  _High betweenness centrality (0.044) - this node is a cross-community bridge._
- **Why does `CLAUDE.md (project instructions)` connect `CLAUDE.md Rules` to `Jetson Deploy Skill`, `Configuration Guide`, `MAVROS Ops Skill`, `Isaac 6.0 Stack Notes`, `Core ADRs`, `PX4 SITL Skill`?**
  _High betweenness centrality (0.042) - this node is a cross-community bridge._
- **Why does `Configuration guide` connect `Configuration Guide` to `Debugging Guide`, `Docker Strategy and Pins`, `Remote Viewing`, `Multi-Vehicle Scenarios`, `vio_mock Source`, `Scenario Configs`?**
  _High betweenness centrality (0.033) - this node is a cross-community bridge._
- **What connects `pull_images.sh script`, `x-nvidia runtime anchor`, `sim service (GUI profile)` to the rest of the system?**
  _61 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ZED Stack Config Compiler` be split into smaller, more focused modules?**
  _Cohesion score 0.06298701298701298 - nodes in this community are weakly interconnected._
- **Should `Build and Common Scripts` be split into smaller, more focused modules?**
  _Cohesion score 0.08108108108108109 - nodes in this community are weakly interconnected._