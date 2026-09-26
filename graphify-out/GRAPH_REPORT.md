# Graph Report - bisg_isaac  (2026-09-25)

## Corpus Check
- Corpus is ~32,534 words - fits in a single context window. You may not need a graph.

## Summary
- 336 nodes · 491 edges · 29 communities (17 shown, 12 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 29 edges (avg confidence: 0.84)
- Token cost: 84,222 input · 0 output

## Community Hubs (Navigation)
- Isaac Sim Launcher Imports
- Config & Skills Docs
- Compose Services & ADRs
- Shared Shell Helpers
- Project Rules & Host Facts
- VIO Mock Node
- Debug CLI Commands
- Launch CLI Commands
- PX4 Param Push & Smoke Test
- Hardware & Interface Contract
- MAVROS & ZED Skills
- Web Viewport Streaming
- Sim Compose Profiles
- PX4 SITL & Swarm Ports
- Sim Entrypoint
- DDS & Fleet Networking
- ROS 2 Package Layout
- Third-Party Fetch
- bisg CLI Wrapper
- Sim Regression Runner
- ROS Entrypoint
- Isaac Sim Base Image
- Python Package Setup
- Image Pull Script
- Host Setup Script
- Site Worlds
- Project Claude Skills
- Workstation Setup Guide

## God Nodes (most connected - your core abstractions)
1. `launch.sh script` - 17 edges
2. `debug.sh script` - 16 edges
3. `Isaac Sim 5.1.0` - 10 edges
4. `cmd_report()` - 9 edges
5. `./bisg operator CLI` - 8 edges
6. `VioMock` - 7 edges
7. `WebView` - 7 edges
8. `sim-launch Skill` - 7 edges
9. `hardware.md — drone bill of materials, wiring, PX4 params, bench checklist` - 7 edges
10. `bisg_isaac Claude Code Project Instructions` - 7 edges

## Surprising Connections (you probably didn't know these)
- `Host prerequisites (driver, Docker, nvidia-container-toolkit, X11)` --semantically_similar_to--> `Workstation Host Facts (RTX 4500 Ada, Ubuntu 24.04, /opt storage)`  [INFERRED] [semantically similar]
  docs/setup.md → CLAUDE.md
- `bisg_isaac Claude Code Project Instructions` --cites--> `ADR-001 MAVROS instead of uXRCE-DDS`  [EXTRACTED]
  CLAUDE.md → docs/plan.md
- `bisg_isaac Claude Code Project Instructions` --references--> `Project Plan — bisg_isaac digital twin`  [EXTRACTED]
  CLAUDE.md → docs/plan.md
- `x-sim-base anchor (bisg/sim image)` --implements--> `bisg/sim image`  [INFERRED]
  docker/compose.yaml → docs/plan.md
- `PegasusSimulator submodule (v5.1.0)` --implements--> `Pegasus Simulator v5.1.0`  [INFERRED]
  third_party/README.md → docs/plan.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **MAVROS Bridge Pipeline (PX4 to ROS2)** — docs_decisions_adr_001_mavros_mavros_bridge, claude_skills_mavros_ops_skill_offboard_state_machine, claude_skills_mavros_ops_skill_bisg_bringup_mavros_launch, claude_skills_px4_sitl_skill_instance_math [INFERRED 0.85]
- **ZED Sensor Contract Chain (Sim to Hardware)** — claude_skills_zed_contract_skill_interface_contract_doc, deploy_jetson_zed_params_zed_overlay, docker_zed_readme_zed_sdk_image, claude_skills_zed_contract_skill_vio_mock [INFERRED 0.85]
- **bisg ROS 2 workspace packages (bisg_msgs, bisg_vehicle, bisg_fleet, bisg_bringup)** — readme_bisg_msgs_package, readme_bisg_vehicle_package, readme_bisg_fleet_package, readme_bisg_bringup_package [EXTRACTED 1.00]
- **Claude Code project skills for bisg_isaac** — claude_skills_jetson_deploy_skill_skill_doc, claude_skills_sim_launch_skill_skill_doc, docs_skills_mavros_ops, docs_skills_zed_contract, docs_skills_swarm_spawn, docs_skills_sim_regression [EXTRACTED 1.00]
- **Simulation-side twin stack (Isaac + Pegasus + PX4 SITL + MAVROS)** — docs_plan_isaac_sim, docs_plan_pegasus_simulator, docs_plan_px4, docs_plan_mavros, docs_plan_bisg_sim_image, docs_plan_bisg_ros_image [EXTRACTED 1.00]
- **GPS-denied external-vision estimation pipeline** — docs_plan_vio_mock, docs_plan_ev_state_estimation, docs_todo_push_px4_params, docs_todo_mavros_odom_frame_split, docs_todo_ev_height_divergence_bug [INFERRED 0.85]
- **Architecture Decision Records ADR-001..005** — docs_plan_adr_001_mavros, docs_plan_adr_002_docker, docs_plan_adr_003_px4_version, docs_plan_adr_004_dds, docs_plan_adr_005_ros2_jazzy [EXTRACTED 1.00]

## Communities (29 total, 12 thin omitted)

### Community 0 - "Isaac Sim Launcher Imports"
Cohesion: 0.06
Nodes (34): carb, isaacsim, isaacsim_core_utils, isaacsim_core_utils_extensions, isaacsim_core_utils_prims, isaacsim_ros2_bridge, isaacsim_sensors_camera_camera, isaacsim_sensors_physics (+26 more)

### Community 1 - "Config & Skills Docs"
Cohesion: 0.12
Nodes (26): jetson-deploy Skill, sim-launch Skill, Merge of six numbered config files into config/bisg.conf, SIM_VIEW configuration key, SIM_MODE + SIM_STREAM merged into SIM_VIEW, ADR-003: One PX4 tag for SITL and Pixracer, ADR-005: ROS 2 Jazzy in all containers, ADR-004: CycloneDDS + zenoh bridge for the fleet network (+18 more)

### Community 2 - "Compose Services & ADRs"
Cohesion: 0.07
Nodes (34): Settings Layering (bisg.conf / docker/.env / scenario YAML), mavros service (per-drone), ros dev shell service, x-ros-base anchor (bisg/ros:jazzy image), vehicle service (vio_mock), ADR-001 MAVROS instead of uXRCE-DDS, ADR-003 One PX4 version for SITL and Pixracer, ADR-004 CycloneDDS + zenoh bridge for fleet network (+26 more)

### Community 3 - "Shared Shell Helpers"
Cohesion: 0.09
Nodes (22): _BISG_ENV0, BISG_SRC, conf_default(), die(), fail(), FCU_URL, GCS_URL, gpu_preflight() (+14 more)

### Community 4 - "Project Rules & Host Facts"
Cohesion: 0.10
Nodes (26): Fresh Start Rule (no code from ~/isaacsim or ~/swarm_ws), Workstation Host Facts (RTX 4500 Ada, Ubuntu 24.04, /opt storage), NVIDIA Driver 580 Branch Requirement, bisg_isaac Claude Code Project Instructions, bisg Docker Compose File, build.sh script, ADR-002 Docker-first, Isaac Sim in a container, ADR-005 ROS 2 Jazzy in all containers (+18 more)

### Community 5 - "VIO Mock Node"
Cohesion: 0.11
Nodes (14): collections, geometry_msgs_msg, nav_msgs_msg, Node, PoseStamped, random, rclpy, rclpy_node (+6 more)

### Community 6 - "Debug CLI Commands"
Cohesion: 0.26
Nodes (18): cmd_clean_all(), cmd_clean_cache(), cmd_dds(), cmd_echo(), cmd_gpu(), cmd_hz(), cmd_kitlog(), cmd_mavlink() (+10 more)

### Community 7 - "Launch CLI Commands"
Cohesion: 0.25
Nodes (17): cmd_all(), cmd_config(), cmd_down(), cmd_logs(), cmd_mavros(), cmd_restart(), cmd_ros(), cmd_shell() (+9 more)

### Community 8 - "PX4 Param Push & Smoke Test"
Cohesion: 0.16
Nodes (13): argparse, pymavlink, encode(), load_params(), main(), Push PX4 EKF2/GPS params over MAVLink (Phase 3 — GPS-denied flight on ZED Mini…, PX4/MAVLink PARAM_SET always carries a float32 on the wire; non-REAL32 types…, struct (+5 more)

### Community 9 - "Hardware & Interface Contract"
Cohesion: 0.19
Nodes (16): Bench checklist (Phase 5, props OFF) — Pixracer flash, MAVROS heartbeat, ZED odom rate/TF, EV fusion healthy, offboard on bench, failsafe verified in SITL first, hardware.md — drone bill of materials, wiring, PX4 params, bench checklist, Jetson Orin NX (JetPack 7.2, L4T r38, Ubuntu 24.04, CUDA 13) companion computer, Pixracer flight controller (px4_fmu-v4, STM32F427), PX4 v1.17.0, flash at 95.3%, PX4 parameter table for EV/VIO fusion and GPS-denied flight — rationale per param (EKF2_EV_CTRL, EKF2_HGT_REF=Vision, EKF2_GPS_CTRL=0 indoor, offboard-loss failsafe), Vehicle model measurements (Phase 4): mass/CG, arm length, thrust curve, inertia, sensor poses — feeds sim/assets/vehicles/bisg_quad, vio_relay — republishes ZED SDK positional-tracking odom (zed/zed_node/odom) to mavros/odometry/out, ZED Mini stereo camera — USB 3.0, 63mm baseline, built-in IMU, ZED SDK 5.4.1 (+8 more)

### Community 10 - "MAVROS & ZED Skills"
Cohesion: 0.18
Nodes (13): bisg_bringup mavros.launch.py, MAVROS OFFBOARD State Machine, MAVROS Ops Procedure, tests/check_contract.py, docs/interface-contract.md (referenced), ZED Contract Procedure, vio_mock / vio_relay Nodes, Jetson Deploy Compose Stack (+5 more)

### Community 11 - "Web Viewport Streaming"
Cohesion: 0.22
Nodes (5): Serve the viewport as a still image over one TCP port. The WebRTC client needs…, Issue one viewport capture if the interval has elapsed. Never raises., WebView, do_GET(), _send()

### Community 12 - "Sim Compose Profiles"
Cohesion: 0.38
Nodes (7): SIM_VIEW key (gui|headless|web|webrtc|both|auto), Isaac cache named volumes, x-nvidia runtime anchor, sim service (GUI profile), x-sim-base anchor (bisg/sim image), sim-headless service, Headless remote views (web / webrtc)

### Community 13 - "PX4 SITL & Swarm Ports"
Cohesion: 0.33
Nodes (6): PX4 SITL Instance/Port Math, Pegasus px4_mavlink_backend.py, PX4 SITL Operations, scripts/gen_compose.py, Swarm Spawn Procedure, PX4 Parameter Files

### Community 14 - "Sim Entrypoint"
Cohesion: 0.50
Nodes (4): isaac_python_exec(), ROS_DISTRO, entrypoint.sh script, SIM_CONFIG

### Community 15 - "DDS & Fleet Networking"
Cohesion: 0.50
Nodes (5): CycloneDDS (rmw_cyclonedds_cpp) chosen everywhere — rationale: reliable across container boundaries with network_mode:host, unlike FastDDS shared-memory transport which is fragile across containers and DDS multicast which is unreliable on WiFi, ADR-004: CycloneDDS everywhere, zenoh bridge across WiFi, FastDDS — rejected: shared-memory transport fragile across containers, ROS_DOMAIN_ID — one per fleet run, drones share it, namespaces separate them; zenoh bridge can map domains if per-drone isolation is ever needed, zenoh-bridge-ros2dds — bridges drone/ground-station traffic over WiFi; only vehicle/state, vehicle/cmd, /fleet/* and low-rate telemetry allowed across (allow-list)

### Community 16 - "ROS 2 Package Layout"
Cohesion: 0.67
Nodes (3): ros2_ws/src README, Shared ROS 2 Jazzy packages (Phase 2+): bisg_msgs, bisg_vehicle, bisg_fleet, bisg_bringup, Nodes in ros2_ws/src must not import isaacsim, pegasus or omni (parity rule, plan.md §8)

## Knowledge Gaps
- **45 isolated node(s):** `entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO`, `build.sh script`, `BISG_SRC` (+40 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 122 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **12 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `GPS-denied state estimation (VIO -> MAVROS odometry/out -> EKF2 EV)` connect `Compose Services & ADRs` to `Config & Skills Docs`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Why does `scripts/push_px4_params.py + sim_default.params` connect `Compose Services & ADRs` to `PX4 Param Push & Smoke Test`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Why does `ZED Mini camera` connect `Config & Skills Docs` to `Compose Services & ADRs`, `Project Rules & Host Facts`?**
  _High betweenness centrality (0.056) - this node is a cross-community bridge._
- **What connects `entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO` to the rest of the system?**
  _45 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Isaac Sim Launcher Imports` be split into smaller, more focused modules?**
  _Cohesion score 0.059233449477351915 - nodes in this community are weakly interconnected._
- **Should `Config & Skills Docs` be split into smaller, more focused modules?**
  _Cohesion score 0.12312312312312312 - nodes in this community are weakly interconnected._
- **Should `Compose Services & ADRs` be split into smaller, more focused modules?**
  _Cohesion score 0.07130124777183601 - nodes in this community are weakly interconnected._