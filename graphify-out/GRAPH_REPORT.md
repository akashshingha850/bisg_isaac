# Graph Report - bisg_isaac  (2026-10-06)

## Corpus Check
- 34 files · ~84,707 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1006 nodes · 1688 edges · 91 communities (73 shown, 17 thin omitted)
- Extraction: 93% EXTRACTED · 7% INFERRED · 0% AMBIGUOUS · INFERRED: 122 edges (avg confidence: 0.85)
- Token cost: 174,476 input · 0 output

## Community Hubs (Navigation)
- ZED Config Compiler
- Shared Shell Helpers
- ZED Bench Harness
- ZED Bridge Module Base
- Drone Views & Depth Colormap
- MAVROS Fleet & Sim Time
- Project Ground Rules
- Isaac 6.0 Migration Errors
- Pegasus Simulator API
- ZED Health & Odometry Modules
- Known Bugs & Pegasus Pin
- PX4 Bridge CLI Tests
- ZED Stack ADR-008
- Flight Test Helpers
- Debug Commands
- Launch Commands
- ROS Flight Tests
- Compose Services
- Isaac Camera & Replicator APIs
- Obstacle Sectors & Video
- ZED SDK Extension Config
- Vehicle Interface Contract
- Hover & Position Tests
- Real ZED SDK in Sim (ADR-007)
- Follow Camera
- ZED SDK Check Probe
- single_iris Scenario
- ZED Rig & VIO Sources
- Workstation Setup
- Drone Views Window
- Docker & DDS Decisions
- Roadmap Phases
- Tailscale Remote Access
- ZED Image Build
- QGC Video Stream
- Hardware & Bench Checklist
- Remote View Modes
- Depth Sector Tests
- Browser Web View
- Pegasus Fast Path & RTF HUD
- MAVROS Sim Time & Obstacle
- vio_mock Node
- ZED Drone Launch
- vpn.sh Script
- ZED Feature Flags
- Jetson Deploy Skill
- MAVROS Ops Skill
- Regression & Swarm Scenarios
- Bridge Shared Pieces
- Bridge Node Context
- PX4 Bridge Choice (ADR-001)
- Debugging Guide
- Skills Overview
- Swarm & ZED SDK Skills
- Perf Knobs & headless_fast
- Driver Pin & Env Check
- Third-Eye Camera
- PX4 Param Push
- px4-bridge.sh Script
- zed.sh Script
- Pegasus Rotor Forces
- VIO Parity Rules
- PX4 SITL & Sim Launch Skills
- Scan Test Loop
- Config Layering
- ZED Contract Skill
- PX4 Bridge Entrypoint
- Sim Entrypoint
- drone.sh Script
- RTF Bottleneck
- Test Pump Helpers A
- Test Pump Helpers B
- Isaac Cache Volumes
- Source Fetch Script
- Scenario Loader
- bisg CLI
- ROS Entrypoint
- bisg_vehicle Package Setup
- ZED build.sh
- ZED Bridge Package
- Image Pull Script
- Setup Script
- Vehicle Assets (Phase 4)
- Site Worlds (Phase 4)
- Async Rendering Hang
- Orin NX RAM Constraint
- Isaac ROS2 Bridge Import
- Isaac Physics Sensors Import
- Legacy omni.isaac.core World
- Rotation Import

## God Nodes (most connected - your core abstractions)
1. `Known bugs` - 25 edges
2. `ZedDepthProducts` - 17 edges
3. `launch.sh script` - 17 edges
4. `CLAUDE.md project instructions` - 17 edges
5. `Rate` - 16 edges
6. `debug.sh script` - 16 edges
7. `The real ZED SDK in the sim` - 16 edges
8. `Health` - 15 edges
9. `Flight` - 15 edges
10. `Isaac Sim 6.0 migration errors and gotchas` - 15 edges

## Surprising Connections (you probably didn't know these)
- `ZED_SOURCE key (emulated|sdk)` --semantically_similar_to--> `ZED_SOURCE=sdk (real ZED SDK in sim)`  [INFERRED] [semantically similar]
  docs/configuration.md → CLAUDE.md
- `MAVROS launch wrapper (bisg_bringup mavros.launch.py)` --semantically_similar_to--> `MAVROS plugin_allowlist (17 plugins)`  [INFERRED] [semantically similar]
  .claude/skills/mavros-ops/SKILL.md → docker/ros/mavros_lean.yaml
- `vio_mock` --conceptually_related_to--> `vehicle service (vio_mock)`  [INFERRED]
  docs/bugs.md → docker/compose.yaml
- `sim service (GUI)` --references--> `isaac-cache-kit shader cache volume`  [INFERRED]
  docker/compose.yaml → CLAUDE.md
- `sim service (GUI)` --shares_data_with--> `SIM_STREAM derived value`  [INFERRED]
  docker/compose.yaml → docs/configuration.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Real ZED SDK in sim: extension, FixedJoint mount, shared-memory stream, unmodified wrapper** — docs_decisions_adr_007_zed_sdk_in_sim_zed_isaac_sim_extension, docs_decisions_adr_007_zed_sdk_in_sim_fixed_joint_mount, docs_zed_sdk_sim_stream_architecture, docs_zed_sdk_sim_imu_fusion_false, docs_zed_sdk_sim_sim_published_imu [EXTRACTED 0.95]
- **ZED stack: one YAML, one image, three services** — docs_zed_stack_zed_yaml, docs_decisions_adr_008_zed_stack_bisg_zed_image, docs_decisions_adr_008_zed_stack_zed_bridge_service, docs_decisions_adr_008_zed_stack_zed_video_service, docs_decisions_adr_008_zed_stack_zed_stack_compiler [EXTRACTED 0.95]
- **Scenario YAML inheritance chain rooted at single_iris** — docker_sim_configs_single_iris, docker_sim_configs_single_iris_nozed, docker_sim_configs_single_iris_vio, docker_sim_configs_single_iris_vio_lowres, docker_sim_configs_two_iris_nozed, docker_sim_configs_two_iris_vio_lowres [EXTRACTED 1.00]
- **Pin-change regression gate** — claude_skills_sim_regression_skill_migration_gate, docker_sim_configs_four_iris_nozed, docker_sim_configs_eight_iris_nozed [INFERRED 0.75]
- **Isaac 6.0 sim-speed regression, cause, patch and docs** — docs_migration_errors_m8_sim_speed_regression, docs_migration_errors_m9_render_false, docs_performance_render_cadence_fix, docs_migration_errors_m20_performance_doc_stale [INFERRED 0.85]
- **ZED stack services on one bisg/zed image** — docker_compose_zed, docker_compose_zed_bridge, docker_compose_zed_video, docker_compose_drone_zed, claude_zed_stack [EXTRACTED 1.00]
- **Selectable PX4 bridge options** — docs_decisions_adr_001_mavros_px4_bridge_selectable_service, docs_decisions_adr_001_mavros_mavros_bridge, docs_decisions_adr_001_mavros_mavsdk, docs_decisions_adr_001_mavros_uxrce_dds, docs_configuration_px4_bridge_key [EXTRACTED 1.00]
- **Remote access path (SIM_VIEW -> WebRTC -> Tailscale)** — claude_sim_view, docs_decisions_adr_009_remote_access_vpn_sim_view_addr_vpn, docs_decisions_adr_009_remote_access_vpn_webrtc_udp_47998, docs_decisions_adr_009_remote_access_vpn_tailscale_vpn_service, docker_compose_vpn [INFERRED 0.85]
- **Interchangeable PX4 bridge backends** — docs_px4_bridge_px4_bridge_service, docs_plan_mavros, docs_px4_bridge_mavsdk_server, docs_px4_bridge_xrce_agent [EXTRACTED 1.00]
- **ZED -> bridge -> MAVROS -> PX4 pipeline** — docs_zed_stack_zed_yaml, docs_zed_stack_zed_wrapper, docs_zed_stack_zed_bridge, docs_plan_mavros, docs_plan_vio_state_estimation [EXTRACTED 1.00]
- **Factors determining sim real-time factor** — docs_performance_rtf, docs_performance_pegasus_per_step_bottleneck, docs_performance_render_cadence_fix, docs_performance_physics_dt_px4_rate, docs_performance_pegasus_fast [INFERRED 0.85]

## Communities (91 total, 17 thin omitted)

### Community 0 - "ZED Config Compiler"
Cohesion: 0.06
Nodes (32): difflib, ConfigError, deep_merge(), _flatten_params(), load(), docker/zed/zed.yaml -> zed_wrapper parameters + the list of services to start.…, {section: {key: default}} from the wrapper's own YAML files (the model file…, Module master switch. Modules without `enabled` (camera, video, sensors,… (+24 more)

### Community 1 - "Shared Shell Helpers"
Cohesion: 0.08
Nodes (29): build_isaac_ext.sh script, _BISG_ENV0, BISG_SRC, conf_default(), container_running(), die(), fail(), FCU_URL (+21 more)

### Community 2 - "ZED Bench Harness"
Cohesion: 0.11
Nodes (29): Node, rosgraph_msgs_msg, Bench, build_phases(), chk_cloud(), chk_depth(), chk_depth_extras(), chk_images() (+21 more)

### Community 3 - "ZED Bridge Module Base"
Cohesion: 0.07
Nodes (8): Module, Rate, Messages per second over a sliding window, and how long ago the last one came…, Base of a bridge module. `status()` is polled once a second by the health…, Health, ObstacleDistance, MAVROS defaults the obstacle plugin to GLOBAL; ours is a body-frame (FRD) scan., Odometry2Px4

### Community 4 - "Drone Views & Depth Colormap"
Cohesion: 0.11
Nodes (12): bisect, Live drone views in the Isaac GUI: the ZED left camera image and its depth side…, Google Turbo colormap, 256 entries, as uint8 RGB (polynomial approximation)., _turbo_lut(), _pack_rgb(), _quat_wxyz_to_matrix(), Depth-derived ZED SDK products for the sim ZED Mini, each behind the…, Run whatever is due. Never raises. (+4 more)

### Community 5 - "MAVROS Fleet & Sim Time"
Cohesion: 0.09
Nodes (28): PX4-link study, bisg_fleet fleet manager, bisg_vehicle offboard controller, MAVROS 2.15.1, Multi-vehicle port/ID/namespace model, Sim time (use_sim_time + /clock), vio_mock (ground truth + noise), GPS-denied VIO state estimation path (+20 more)

### Community 6 - "Project Ground Rules"
Cohesion: 0.14
Nodes (23): CLAUDE.md project instructions, Docker data-root /opt/docker-data, isaac-cache-kit shader cache volume, Isaac Sim 6.0 stack, Migration gate checks (smoke, vio_flight, zed_depth_box), NVIDIA driver 580 branch pin, Phased build order (single drone -> assets -> real drone -> swarm), PX4 v1.17.0 (+15 more)

### Community 7 - "Isaac 6.0 Migration Errors"
Cohesion: 0.12
Nodes (22): Isaac 5.1->6.0 migration report, Topics provided by the vehicle, ZED wrapper 5.4.1 topic names, Isaac Sim 6.0 migration errors and gotchas, M12 deprecated APIs still in use, M14 smoke test --patience for low RTF, M19 changed Pegasus/launcher semantics, M1 PX4 v1.16.0 SITL build IndexError (+14 more)

### Community 8 - "Pegasus Simulator API"
Cohesion: 0.11
Nodes (17): isaacsim, isaacsim_core_simulation_manager, omni_timeline, pegasus_simulator_logic_backends_px4_mavlink_backend, pegasus_simulator_logic_interface_pegasus_interface, pegasus_simulator_logic_vehicles_multirotor, pegasus_simulator_params, apply_px4_params() (+9 more)

### Community 9 - "ZED Health & Odometry Modules"
Cohesion: 0.12
Nodes (13): copy, M10 — ZED health -> one status topic + STATUSTEXT in QGroundControl. Publishes…, M1 — ZED positional tracking -> PX4 EKF2 external vision (MAVROS odometry/out).…, json, nav_msgs_msg, sensor_msgs_msg, std_msgs_msg, Fake (+5 more)

### Community 10 - "Known Bugs & Pegasus Pin"
Cohesion: 0.14
Nodes (20): Pegasus Simulator PR #144 head, single_iris_vio_lowres.yaml scenario (320x180 ZED), Known bugs, B10 bisg/ros:arm64 old entrypoint, B11 push_px4_params.py can't finish on SITL, B12 GUI profile not re-verified, B16 Contract TF prefix vs real wrapper, B18 SDK connects once per sim run (+12 more)

### Community 11 - "PX4 Bridge CLI Tests"
Cohesion: 0.16
Nodes (6): subprocess, bridge(), compose_service(), Px4BridgeCli, ./bisg px4-bridge: one compose service (px4-bridge), PX4_BRIDGE picks what its…, unittest

### Community 12 - "ZED Stack ADR-008"
Cohesion: 0.12
Nodes (19): ADR-008 One YAML, one image, small services, bisg/zed single image, Shared compose.yaml profiles zed and drone, Bridge modules not yet built, zed-bridge service (ZED to PX4 via MAVROS), zed_stack compile/validate, zed-video service (QGC video), Isaac shader cache volume (isaac-cache-kit) (+11 more)

### Community 13 - "Flight Test Helpers"
Cohesion: 0.15
Nodes (5): Exception, Abort, Flight, main(), Fly to (dx, dy) from the start point at `alt` m above it; hold `settle` seconds.

### Community 14 - "Debug Commands"
Cohesion: 0.26
Nodes (18): cmd_clean_all(), cmd_clean_cache(), cmd_dds(), cmd_echo(), cmd_gpu(), cmd_hz(), cmd_kitlog(), cmd_mavlink() (+10 more)

### Community 15 - "Launch Commands"
Cohesion: 0.25
Nodes (17): cmd_all(), cmd_config(), cmd_down(), cmd_logs(), cmd_mavros(), cmd_restart(), cmd_ros(), cmd_shell() (+9 more)

### Community 16 - "ROS Flight Tests"
Cohesion: 0.16
Nodes (13): csv, geometry_msgs_msg, mavros_msgs_msg, mavros_msgs_srv, rclpy, rclpy_parameter, Collision-prevention test: ZED depth -> obstacle_distance node -> MAVROS -> PX4…, Phase 3 exit test (docs/roadmap.md): GPS-denied flight on mock VIO. OFFBOARD… (+5 more)

### Community 17 - "Compose Services"
Cohesion: 0.18
Nodes (17): drone-zed service, mavros service (per-drone), x-nvidia runtime anchor, px4-bridge service, ros dev shell service, x-ros-base anchor (bisg/ros:jazzy image), sim service (GUI), x-sim-base anchor (bisg/sim image) (+9 more)

### Community 18 - "Isaac Camera & Replicator APIs"
Cohesion: 0.14
Nodes (16): isaacsim_core_experimental_utils_app, isaacsim_core_rendering_manager, isaacsim_core_utils, isaacsim_ros2_core_impl_camera_info_utils, isaacsim_sensors_camera_camera, omni_replicator_core, omni_syntheticdata, attach_zed_mini() (+8 more)

### Community 19 - "Obstacle Sectors & Video"
Cohesion: 0.15
Nodes (12): Depth image -> 72 x 5 deg obstacle sectors. numpy only, so it is unit-testable…, ROS 2 image topic -> RTP/H.264 over UDP, for QGroundControl's "UDP h.264 Video…, gi, gi_repository, numpy, os, signal, tempfile (+4 more)

### Community 20 - "ZED SDK Extension Config"
Cohesion: 0.15
Nodes (15): isaacsim_core_utils_extensions, isaacsim_core_utils_prims, omni_graph_core, omni_usd, pxr, ext_folder(), Stdlib-only half of the ZED SDK mode (zed_sdk_rig.py): decisions that launch.py…, Folder holding the built extension (docker/zed/build_isaac_ext.sh). Checked… (+7 more)

### Community 21 - "Vehicle Interface Contract"
Cohesion: 0.13
Nodes (15): Vehicle interface contract, /clock sim time, Frame prefix gap (B16), /drone_<n> namespace = MAV_SYS_ID, Contract parity checks (check_contract.py), QoS policy, TF frame tree map-odom-base_link-zed frames, Topics consumed by the vehicle (+7 more)

### Community 22 - "Hover & Position Tests"
Cohesion: 0.19
Nodes (9): argparse, math, pymavlink, statistics, Position-hold test (GPS scenario, e.g. single_iris_nozed): arm -> takeoff to…, Hover-stability test: arm -> takeoff to ALT m -> settle -> record ATTITUDE for…, main(), Phase 1 smoke test: arm -> takeoff to ALT m -> land -> disarm, over MAVLink to… (+1 more)

### Community 23 - "Real ZED SDK in Sim (ADR-007)"
Cohesion: 0.20
Nodes (14): ADR-007 Real ZED SDK in the sim, ZED asset FixedJoint mount, One odometry source per run, Residual sim-vs-hardware ZED gap, Stereolabs zed-isaac-sim extension v5.2.1, ZED_SOURCE emulated|sdk switch, ZED SDK in sim one-time steps, zed-isaac-sim v5.2.1 529e538 (+6 more)

### Community 24 - "Follow Camera"
Cohesion: 0.29
Nodes (4): FollowCam, Follow camera for the GUI viewport, in the spirit of Gazebo's "follow" mode:…, Put the camera at `offset` in the drone's body frame, looking at it., _wrap()

### Community 25 - "ZED SDK Check Probe"
Cohesion: 0.19
Nodes (8): main(), path_length(), Probe, Node, rate(), ZED SDK contract + health check — the same script for the sim (ZED_SOURCE=sdk)…, RMSE (m) of the SDK odometry against ground truth after the only alignment that…, trajectory_rmse()

### Community 26 - "single_iris Scenario"
Cohesion: 0.23
Nodes (13): single_iris.yaml scenario, follow_cam (Gazebo-style follow camera), 120 Hz physics step (physics_dt), px4 block (airframe, lockstep, params_file), ros_clock (/clock sim time), third_eye camera, vehicle id numbering (PX4 instance = id, SYS_ID = id+1, ns /drone_{id+1}), single_iris_vio.yaml scenario (GPS-denied) (+5 more)

### Community 27 - "ZED Rig & VIO Sources"
Cohesion: 0.19
Nodes (13): Pegasus ROS2Backend state topics (pub_state), vio_mock odometry source, ZED Mini sim rig config (sensors.zed), ZED view overlay (accumulating depth map, FOV grid), same ZED image in sim (compose service zed), zed.yaml (single ZED stack config), AI/optional modules (object detection, body tracking, mapping, plane, global localization, streaming, recording), Camera + Depth sensing modules (HD720, NEURAL_LIGHT) (+5 more)

### Community 28 - "Workstation Setup"
Cohesion: 0.17
Nodes (13): M18 Pegasus pin only on PR ref, Workstation setup, ./bisg setup steps, Host prerequisites, Jetson Orin NX setup preview, net.core.rmem_max UDP buffer requirement, Pinned upstream sources, Local submodule branch workflow (+5 more)

### Community 29 - "Drone Views Window"
Cohesion: 0.18
Nodes (7): DroneViews, Refresh the window if the interval has elapsed. Never raises., App, main(), resolve_vehicle_usd(), `emulated` (Isaac cameras publish the contract topics, zed_rig.py) or `sdk`…, zed_source()

### Community 30 - "Docker & DDS Decisions"
Cohesion: 0.20
Nodes (12): ADR-002 Docker-first including Isaac Sim, compose profiles sim, sim-headless, ros, jetson, network_mode host everywhere, ADR-004 CycloneDDS everywhere, zenoh bridge over WiFi, zenoh-bridge-ros2dds with allow-list, CycloneDDS + zenoh-bridge-ros2dds, Docker image families (bisg/sim, bisg/ros, bisg/zed), Isaac Sim 6.0.0 (+4 more)

### Community 31 - "Roadmap Phases"
Cohesion: 0.29
Nodes (12): Roadmap, scripts/gen_compose.py per-drone services, Phase 0 Foundations, Phase 1 Dockerized single-drone sim, Phase 2 ROS 2 + MAVROS control, Phase 3 Sensors, ZED Mini contract, VIO, Phase 4 Digital-twin assets and models, Phase 5 Hardware single drone (+4 more)

### Community 32 - "Tailscale Remote Access"
Cohesion: 0.25
Nodes (11): Docker-first: every component a compose service (ADR-002), vpn service, ADR-009 Remote access via Tailscale, No auth keys; browser login (./bisg vpn login), Plain tailscaled instead of containerboot, SIM_VIEW_ADDR=vpn, Tailscale vpn compose service, WebRTC media on UDP 47998 (+3 more)

### Community 33 - "ZED Image Build"
Cohesion: 0.25
Nodes (11): docker/zed README (ZED SDK image), docker/zed/build.sh (desktop|jetson builds), CycloneDDS overlay (Dockerfile.overlay), bisg/zed images (desktop, l4t-r38), bisg/sim, bisg/ros, bisg/zed images, Pegasus pin (PR #144 head fcb99c0 for Isaac 6.0), rmw_cyclonedds_cpp with committed cyclonedds.xml, ADR-005 ROS 2 Jazzy (Ubuntu 24.04) in all containers (+3 more)

### Community 34 - "QGC Video Stream"
Cohesion: 0.25
Nodes (4): main(), Image, Node, VideoStream

### Community 35 - "Hardware & Bench Checklist"
Cohesion: 0.22
Nodes (11): B1 No usable failsafe while GPS-denied, B13 No camera view obstruction check, Hardware, Bench checklist (Phase 5), Jetson Orin NX (JetPack 7.2), Pixracer (px4_fmu-v4), PX4 parameters (config/px4/<drone_n>.params), TELEM2 UART wiring to /dev/px4 (+3 more)

### Community 36 - "Remote View Modes"
Cohesion: 0.18
Nodes (11): M4 WebRTC extension replaced in 6.0, Remote access to the sim, Cloudflare Tunnel (does not carry WebRTC UDP), SIM_VIEW setting, web view (still frames, TCP 8899), WebRTC livestream (TCP 49100 + UDP 47998), Runbook - simulation stack, ./bisg CLI (+3 more)

### Community 37 - "Depth Sector Tests"
Cohesion: 0.36
Nodes (4): Image, Depth image (H x W, metres, float32) + pinhole intrinsics -> 72 ranges [m]: inf…, sectors_from_depth(), SectorTests

### Community 38 - "Browser Web View"
Cohesion: 0.22
Nodes (5): Serve the viewport as a still image over one TCP port. The WebRTC client needs…, Issue one viewport capture if the interval has elapsed. Never raises., WebView, do_GET(), _send()

### Community 39 - "Pegasus Fast Path & RTF HUD"
Cohesion: 0.22
Nodes (5): carb, logging, Per-step speed-ups for Pegasus on Isaac Sim 6.0 (docs/performance.md,…, install(), Real-time factor (sim seconds per wall second) as one more line of Kit's own…

### Community 40 - "MAVROS Sim Time & Obstacle"
Cohesion: 0.28
Nodes (6): main(), Switch every MAVROS plugin node to use_sim_time:=true (sim stack only,…, M2 — ZED depth image -> PX4's 72-sector obstacle map (MAVROS obstacle/send ->…, rcl_interfaces_msg, rcl_interfaces_srv, time

### Community 41 - "vio_mock Node"
Cohesion: 0.22
Nodes (5): main(), Node, VioMock, PoseStamped, TwistStamped

### Community 42 - "ZED Drone Launch"
Cohesion: 0.22
Nodes (7): zed_wrapper for drone N, with the contract's topic names. Used by BOTH the sim…, launch, launch_actions, launch_launch_description_sources, launch_ros_actions, launch_ros_substitutions, launch_substitutions

### Community 43 - "vpn.sh Script"
Cohesion: 0.58
Nodes (8): backend(), connected(), login(), reach(), vpn.sh script, start(), ts(), vcompose()

### Community 44 - "ZED Feature Flags"
Cohesion: 0.31
Nodes (4): Features, load_features(), _merge(), ZED SDK feature switches for the emulated sim rig: the same docker/zed/zed.yaml…

### Community 45 - "Jetson Deploy Skill"
Cohesion: 0.25
Nodes (7): jetson-deploy skill, Bench and preflight checklists (props on safety), Jetson images (native build, L4T r38, JetPack 7.2), Pixracer flash and parameterise (px4_fmu-v4), ZED hardware parity check (zed_sdk_check --no-gt), Port ZED setup to the Jetson, PX4 parameter files (SITL and Pixracer)

### Community 46 - "MAVROS Ops Skill"
Cohesion: 0.25
Nodes (7): mavros-ops skill, MAVROS frames (ENU map, odom/base_link), MAVROS launch wrapper (bisg_bringup mavros.launch.py), MAVROS 2.15.1 plugin nodes ignore params files, OFFBOARD state machine (offboard_controller), Sim time and PX4 timesync (use_sim_time), MAVROS plugin_allowlist (17 plugins)

### Community 47 - "Regression & Swarm Scenarios"
Cohesion: 0.39
Nodes (8): PX4 instance / port / sys-id math (4560+i), sim-regression skill, Migration / pin-change gate (smoke, vio_flight, zed_depth_box), Regression scenario file format, Add/remove drone procedure (vehicles list, gen_compose.py), Scenario eight_iris_nozed, Scenario four_iris_nozed, single_iris_nozed.yaml scenario

### Community 48 - "Bridge Shared Pieces"
Cohesion: 0.29
Nodes (6): collections, Shared pieces of the bridge modules (rclpy only where a function needs a node)., random, rclpy_node, rclpy_qos, tf2_ros

### Community 49 - "Bridge Node Context"
Cohesion: 0.36
Nodes (5): Context, What every module needs to know: namespaces and a way to reach the others., main(), python3 -m zed_stack.bridge — the px4_bridge service (compose `zed-bridge`).…, sys

### Community 50 - "PX4 Bridge Choice (ADR-001)"
Cohesion: 0.46
Nodes (8): PX4_BRIDGE key, ADR-001 MAVROS as PX4-ROS 2 bridge, MAVROS 2.x PX4-ROS 2 bridge, MAVROS lean plugin list (mavros_lean.yaml), MAVSDK 4.x, One selectable px4-bridge service (PX4_BRIDGE), PX4-link study (archive/px4-link-study), uXRCE-DDS (rejected alternative)

### Community 51 - "Debugging Guide"
Cohesion: 0.25
Nodes (8): Debugging guide, Log locations, PX4 shell without QGC (bisg debug px4), Resetting (down, clean-cache, clean-all, setup --rebuild), ROS 2 graph debugging (bisg debug topics/hz/echo), ADR-003 One PX4 tag (v1.17.0) for SITL and Pixracer, Pixracer flash headroom (95.3% used), PX4 tag selection procedure

### Community 52 - "Skills Overview"
Cohesion: 0.25
Nodes (8): Skills (competencies and Claude Code skills), Competencies by phase, Skill jetson-deploy, Skill mavros-ops, Skill px4-sitl, Skill sim-regression, Skill swarm-spawn, Skill zed-sdk

### Community 53 - "Swarm & ZED SDK Skills"
Cohesion: 0.29
Nodes (7): swarm-spawn skill, Workstation VRAM limits for swarms, ZED SDK per drone (stream port 30000+2*id), zed-sdk skill, ZED asset FixedJoint to vehicle body rule, ZED SDK run procedure (ext-build, image, up, check), docker/zed/zed.yaml as the single ZED config switch

### Community 54 - "Perf Knobs & headless_fast"
Cohesion: 0.29
Nodes (7): headless_fast.yaml scenario, app.render false (physics-only stepping), perf.skip_material_loading, perf knobs block, NVML driver/library version mismatch fix, Sim slower than real time (rtf < 1.0 stretches PX4 sim time), Symptom to command table

### Community 55 - "Driver Pin & Env Check"
Cohesion: 0.43
Nodes (6): NVIDIA driver 580 pin / 59x guard, Workstation OS migration 22.04 -> 24.04, die(), pass(), check_env.sh script, wrn()

### Community 56 - "Third-Eye Camera"
Cohesion: 0.33
Nodes (6): scipy_spatial_transform, attach_third_eye(), Rotation, _quat_wxyz(), External trailing camera for a vehicle (no ROS topics)., Attach a camera behind and above the drone. Local coordinates use FLU axes.

### Community 57 - "PX4 Param Push"
Cohesion: 0.38
Nodes (6): encode(), load_params(), main(), Push PX4 EKF2/GPS params over MAVLink (Phase 3 — GPS-denied flight on ZED Mini…, PX4/MAVLink PARAM_SET always carries a float32 on the wire; non-REAL32 types…, struct

### Community 58 - "px4-bridge.sh Script"
Cohesion: 0.38
Nodes (3): pcompose(), px4-bridge.sh script, stop()

### Community 59 - "zed.sh Script"
Cohesion: 0.52
Nodes (6): have_frames(), zed.sh script, start_services(), svc_name(), ZED_SIM_PORT, zexec()

### Community 60 - "Pegasus Rotor Forces"
Cohesion: 0.43
Nodes (6): apply(), apply_force(), apply_torque(), handle_propeller_visual(), _prim(), update()

### Community 61 - "VIO Parity Rules"
Cohesion: 0.33
Nodes (5): GPS-denied EV yaw-align limitation (fly and land in OFFBOARD), VIO source per mode (vio_mock / SDK / vio_relay), SDK odometry to PX4 via bridge (restamp, B17 clock), Parity rule: nodes must not import isaacsim/pegasus/omni, Shared ROS 2 packages (bisg_msgs, bisg_vehicle, bisg_fleet, bisg_bringup)

### Community 62 - "PX4 SITL & Sim Launch Skills"
Cohesion: 0.40
Nodes (6): px4-sitl skill, Common PX4 rejections (offboard, arming, mag), Lockstep off in SITL, PX4 v1.16.0 vs v1.17.0 tag notes, sim-launch skill, Sim diagnosis checklist

### Community 63 - "Scan Test Loop"
Cohesion: 0.40
Nodes (3): main(), spin(), wait()

### Community 64 - "Config Layering"
Cohesion: 0.40
Nodes (4): Remote view (web / webrtc streaming), Sim start/stop procedure (bisg up|wait|down), config/bisg.conf (merged project settings), One key, one place rule

### Community 65 - "ZED Contract Skill"
Cohesion: 0.40
Nodes (5): zed-contract skill, Contract-first rule (interface-contract.md changes first), Isaac Sim 6.0 ZED rig notes (zed_rig.py), Matching the ZED wrapper topics/TF/baseline, ZED_SOURCE emulated vs sdk

### Community 66 - "PX4 Bridge Entrypoint"
Cohesion: 0.70
Nodes (4): mavros(), mavsdk(), entrypoint.sh script, xrce()

### Community 67 - "Sim Entrypoint"
Cohesion: 0.50
Nodes (4): isaac_python_exec(), ROS_DISTRO, entrypoint.sh script, SIM_CONFIG

### Community 68 - "drone.sh Script"
Cohesion: 0.50
Nodes (3): drone.sh script, ZED_STACK_SIM, zexec()

### Community 69 - "RTF Bottleneck"
Cohesion: 0.50
Nodes (4): pegasus_fast.py (cached prims, batched forces), Pegasus per-step Python bottleneck (M8), Render cadence fix (2026-09-13), Real-time factor (RTF) measurement

### Community 70 - "Test Pump Helpers A"
Cohesion: 0.67
Nodes (3): main(), pump(), wait()

### Community 71 - "Test Pump Helpers B"
Cohesion: 0.67
Nodes (3): main(), pump(), wait()

### Community 72 - "Isaac Cache Volumes"
Cohesion: 0.67
Nodes (3): RTX shader cache volume isaac-cache-kit, Regression triage (boot timeout, flaky position asserts), Isaac cache named volumes

## Knowledge Gaps
- **102 isolated node(s):** `mavros service (per-drone)`, `x-nvidia runtime anchor`, `ROS_DISTRO`, `SIM_CONFIG`, `pull_images.sh script` (+97 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 339 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Known bugs` connect `Known Bugs & Pegasus Pin` to `Hardware & Bench Checklist`, `MAVROS Fleet & Sim Time`, `ZED Stack ADR-008`, `ROS Flight Tests`, `Compose Services`, `ZED Rig & VIO Sources`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Why does `B17 SDK odometry accuracy outside bound` connect `Compose Services` to `ROS Flight Tests`, `Known Bugs & Pegasus Pin`, `ZED Rig & VIO Sources`, `Project Ground Rules`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `zed-bridge (px4_bridge service)` connect `MAVROS Fleet & Sim Time` to `ZED Health & Odometry Modules`, `PX4 Bridge Choice (ADR-001)`?**
  _High betweenness centrality (0.060) - this node is a cross-community bridge._
- **What connects `mavros service (per-drone)`, `x-nvidia runtime anchor`, `ROS_DISTRO` to the rest of the system?**
  _102 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `ZED Config Compiler` be split into smaller, more focused modules?**
  _Cohesion score 0.06265664160401002 - nodes in this community are weakly interconnected._
- **Should `Shared Shell Helpers` be split into smaller, more focused modules?**
  _Cohesion score 0.0782051282051282 - nodes in this community are weakly interconnected._
- **Should `ZED Bench Harness` be split into smaller, more focused modules?**
  _Cohesion score 0.10668563300142248 - nodes in this community are weakly interconnected._