# Graph Report - bisg_isaac  (2026-09-22)

## Corpus Check
- Corpus is ~31,964 words - fits in a single context window. You may not need a graph.

## Summary
- 290 nodes · 502 edges · 26 communities (15 shown, 11 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.84)
- Token cost: 162,940 input · 0 output

## Community Hubs (Navigation)
- Config & Docs Overview
- Isaac Sim ROS Bridge
- Shared Bash Config Helpers
- Mock VIO ROS Node
- Debug CLI Commands
- Bisg Launch CLI
- PX4 Params & Smoke Test
- Hardware & Interface Contract
- MAVROS & ZED Skills
- Sim Web Stream Viewer
- PX4 SITL & Swarm Skills
- Sim Container Entrypoint
- DDS/CycloneDDS Decision
- Host Preflight Check
- ROS 2 Workspace Overview
- Third-Party Fetch Script
- Bisg CLI Entrypoint
- Sim Regression Test Skill
- ROS Container Entrypoint
- ZED Image Build Script
- Docker-First Decision
- Vehicle Package Setup
- Image Pull/Archive Script
- Workstation Setup Script
- Sim Worlds Overview

## God Nodes (most connected - your core abstractions)
1. `docs/plan.md (Project Plan)` - 29 edges
2. `launch.sh script` - 17 edges
3. `debug.sh script` - 16 edges
4. `CLAUDE.md Project Instructions` - 15 edges
5. `PX4 SITL / firmware` - 11 edges
6. `sim-launch Skill` - 10 edges
7. `ADR-005: ROS 2 Jazzy in all containers` - 10 edges
8. `cmd_report()` - 9 edges
9. `Isaac Sim 5.1` - 9 edges
10. `./bisg operator CLI` - 9 edges

## Surprising Connections (you probably didn't know these)
- `CLAUDE.md Project Instructions` --references--> `NVIDIA driver 595.91.07 (R590) Isaac Sim segfault incompatibility`  [AMBIGUOUS]
  CLAUDE.md → docs/plan.md
- `MAVROS Ops Procedure` --references--> `MAVROS Software Bridge`  [INFERRED]
  .claude/skills/mavros-ops/SKILL.md → docs/decisions/ADR-001-mavros.md
- `Jetson Deploy Compose Stack` --references--> `ZED SDK Docker Image`  [INFERRED]
  deploy/jetson/compose.yaml → docker/zed/README.md
- `vehicles/bisg_quad (Phase 4): USD of the real quad + Pegasus preset — mass, inertia, motor placement, thrust curve, ZED Mini mount` --references--> `Vehicle model measurements (Phase 4): mass/CG, arm length, thrust curve, inertia, sensor poses — feeds sim/assets/vehicles/bisg_quad`  [INFERRED]
  sim/assets/README.md → docs/hardware.md
- `jetson-deploy Skill` --references--> `MAVROS (PX4 <-> ROS 2 bridge)`  [INFERRED]
  .claude/skills/jetson-deploy/SKILL.md → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **MAVROS Bridge Pipeline (PX4 to ROS2)** — docs_decisions_adr_001_mavros_mavros_bridge, claude_skills_mavros_ops_skill_offboard_state_machine, claude_skills_mavros_ops_skill_bisg_bringup_mavros_launch, claude_skills_px4_sitl_skill_instance_math [INFERRED 0.85]
- **ZED Sensor Contract Chain (Sim to Hardware)** — claude_skills_zed_contract_skill_interface_contract_doc, deploy_jetson_zed_params_zed_overlay, docker_zed_readme_zed_sdk_image, claude_skills_zed_contract_skill_vio_mock [INFERRED 0.85]
- **bisg ROS 2 workspace packages (bisg_msgs, bisg_vehicle, bisg_fleet, bisg_bringup)** — readme_bisg_msgs_package, readme_bisg_vehicle_package, readme_bisg_fleet_package, readme_bisg_bringup_package [EXTRACTED 1.00]
- **Claude Code project skills for bisg_isaac** — claude_skills_jetson_deploy_skill_skill_doc, claude_skills_sim_launch_skill_skill_doc, docs_skills_mavros_ops, docs_skills_zed_contract, docs_skills_swarm_spawn, docs_skills_sim_regression, docs_plan_px4_sitl [EXTRACTED 1.00]
- **Architecture decision records governing version pins and bridge/runtime choices** — docs_decisions_adr_003_px4_version_adr003, docs_decisions_adr_005_ros2_jazzy_adr005, claude_adr_001_mavros, claude_adr_002_docker, docs_decisions_adr_005_ros2_jazzy_adr_004_dds [EXTRACTED 1.00]

## Communities (26 total, 11 thin omitted)

### Community 0 - "Config & Docs Overview"
Cohesion: 0.12
Nodes (40): ADR-001: MAVROS instead of uXRCE-DDS, ADR-002: Docker-first, Isaac Sim in a container, docs/interface-contract.md (vehicle interface contract), MAVROS (PX4 <-> ROS 2 bridge), CLAUDE.md Project Instructions, jetson-deploy Skill, sim-launch Skill, Merge of six numbered config files into config/bisg.conf (+32 more)

### Community 1 - "Isaac Sim ROS Bridge"
Cohesion: 0.06
Nodes (34): carb, isaacsim, isaacsim_core_utils, isaacsim_core_utils_extensions, isaacsim_core_utils_prims, isaacsim_ros2_bridge, isaacsim_sensors_camera_camera, isaacsim_sensors_physics (+26 more)

### Community 2 - "Shared Bash Config Helpers"
Cohesion: 0.09
Nodes (22): _BISG_ENV0, BISG_SRC, conf_default(), die(), fail(), FCU_URL, GCS_URL, gpu_preflight() (+14 more)

### Community 3 - "Mock VIO ROS Node"
Cohesion: 0.11
Nodes (14): collections, geometry_msgs_msg, nav_msgs_msg, Node, PoseStamped, random, rclpy, rclpy_node (+6 more)

### Community 4 - "Debug CLI Commands"
Cohesion: 0.26
Nodes (18): cmd_clean_all(), cmd_clean_cache(), cmd_dds(), cmd_echo(), cmd_gpu(), cmd_hz(), cmd_kitlog(), cmd_mavlink() (+10 more)

### Community 5 - "Bisg Launch CLI"
Cohesion: 0.25
Nodes (17): cmd_all(), cmd_config(), cmd_down(), cmd_logs(), cmd_mavros(), cmd_restart(), cmd_ros(), cmd_shell() (+9 more)

### Community 6 - "PX4 Params & Smoke Test"
Cohesion: 0.16
Nodes (13): argparse, pymavlink, encode(), load_params(), main(), Push PX4 EKF2/GPS params over MAVLink (Phase 3 — GPS-denied flight on ZED Mini…, PX4/MAVLink PARAM_SET always carries a float32 on the wire; non-REAL32 types…, struct (+5 more)

### Community 7 - "Hardware & Interface Contract"
Cohesion: 0.19
Nodes (16): Bench checklist (Phase 5, props OFF) — Pixracer flash, MAVROS heartbeat, ZED odom rate/TF, EV fusion healthy, offboard on bench, failsafe verified in SITL first, hardware.md — drone bill of materials, wiring, PX4 params, bench checklist, Jetson Orin NX (JetPack 7.2, L4T r38, Ubuntu 24.04, CUDA 13) companion computer, Pixracer flight controller (px4_fmu-v4, STM32F427), PX4 v1.17.0, flash at 95.3%, PX4 parameter table for EV/VIO fusion and GPS-denied flight — rationale per param (EKF2_EV_CTRL, EKF2_HGT_REF=Vision, EKF2_GPS_CTRL=0 indoor, offboard-loss failsafe), Vehicle model measurements (Phase 4): mass/CG, arm length, thrust curve, inertia, sensor poses — feeds sim/assets/vehicles/bisg_quad, vio_relay — republishes ZED SDK positional-tracking odom (zed/zed_node/odom) to mavros/odometry/out, ZED Mini stereo camera — USB 3.0, 63mm baseline, built-in IMU, ZED SDK 5.4.1 (+8 more)

### Community 8 - "MAVROS & ZED Skills"
Cohesion: 0.18
Nodes (13): bisg_bringup mavros.launch.py, MAVROS OFFBOARD State Machine, MAVROS Ops Procedure, tests/check_contract.py, docs/interface-contract.md (referenced), ZED Contract Procedure, vio_mock / vio_relay Nodes, Jetson Deploy Compose Stack (+5 more)

### Community 9 - "Sim Web Stream Viewer"
Cohesion: 0.22
Nodes (5): Serve the viewport as a still image over one TCP port. The WebRTC client needs…, Issue one viewport capture if the interval has elapsed. Never raises., WebView, do_GET(), _send()

### Community 10 - "PX4 SITL & Swarm Skills"
Cohesion: 0.33
Nodes (6): PX4 SITL Instance/Port Math, Pegasus px4_mavlink_backend.py, PX4 SITL Operations, scripts/gen_compose.py, Swarm Spawn Procedure, PX4 Parameter Files

### Community 11 - "Sim Container Entrypoint"
Cohesion: 0.50
Nodes (4): isaac_python_exec(), ROS_DISTRO, entrypoint.sh script, SIM_CONFIG

### Community 12 - "DDS/CycloneDDS Decision"
Cohesion: 0.50
Nodes (5): CycloneDDS (rmw_cyclonedds_cpp) chosen everywhere — rationale: reliable across container boundaries with network_mode:host, unlike FastDDS shared-memory transport which is fragile across containers and DDS multicast which is unreliable on WiFi, ADR-004: CycloneDDS everywhere, zenoh bridge across WiFi, FastDDS — rejected: shared-memory transport fragile across containers, ROS_DOMAIN_ID — one per fleet run, drones share it, namespaces separate them; zenoh bridge can map domains if per-drone isolation is ever needed, zenoh-bridge-ros2dds — bridges drone/ground-station traffic over WiFi; only vehicle/state, vehicle/cmd, /fleet/* and low-rate telemetry allowed across (allow-list)

### Community 13 - "Host Preflight Check"
Cohesion: 0.70
Nodes (4): die(), pass(), check_env.sh script, wrn()

### Community 14 - "ROS 2 Workspace Overview"
Cohesion: 0.67
Nodes (3): ros2_ws/src README, Shared ROS 2 Jazzy packages (Phase 2+): bisg_msgs, bisg_vehicle, bisg_fleet, bisg_bringup, Nodes in ros2_ws/src must not import isaacsim, pegasus or omni (parity rule, plan.md §8)

## Ambiguous Edges - Review These
- `CLAUDE.md Project Instructions` → `NVIDIA driver 595.91.07 (R590) Isaac Sim segfault incompatibility`  [AMBIGUOUS]
  CLAUDE.md · relation: references

## Knowledge Gaps
- **32 isolated node(s):** `entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO`, `build.sh script`, `BISG_SRC` (+27 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 106 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **11 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `CLAUDE.md Project Instructions` and `NVIDIA driver 595.91.07 (R590) Isaac Sim segfault incompatibility`?**
  _Edge tagged AMBIGUOUS (relation: references) - confidence is low._
- **Why does `WebView` connect `Sim Web Stream Viewer` to `Isaac Sim ROS Bridge`?**
  _High betweenness centrality (0.014) - this node is a cross-community bridge._
- **What connects `entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO` to the rest of the system?**
  _32 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Config & Docs Overview` be split into smaller, more focused modules?**
  _Cohesion score 0.12390572390572391 - nodes in this community are weakly interconnected._
- **Should `Isaac Sim ROS Bridge` be split into smaller, more focused modules?**
  _Cohesion score 0.059233449477351915 - nodes in this community are weakly interconnected._
- **Should `Shared Bash Config Helpers` be split into smaller, more focused modules?**
  _Cohesion score 0.0855614973262032 - nodes in this community are weakly interconnected._
- **Should `Mock VIO ROS Node` be split into smaller, more focused modules?**
  _Cohesion score 0.1111111111111111 - nodes in this community are weakly interconnected._