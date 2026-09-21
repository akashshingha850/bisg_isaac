# Graph Report - .  (2026-09-21)

## Corpus Check
- Corpus is ~27,613 words - fits in a single context window. You may not need a graph.

## Summary
- 242 nodes · 400 edges · 17 communities (11 shown, 6 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 18 edges (avg confidence: 0.84)
- Token cost: 0 input · 257,081 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Project Governance & ADRs|Project Governance & ADRs]]
- [[_COMMUNITY_Shell Config Helpers|Shell Config Helpers]]
- [[_COMMUNITY_Roadmap Phases|Roadmap Phases]]
- [[_COMMUNITY_Sim Performance & Remote Access|Sim Performance & Remote Access]]
- [[_COMMUNITY_DDS & ROS 2 Distro Choices|DDS & ROS 2 Distro Choices]]
- [[_COMMUNITY_Hardware & Interface Contract|Hardware & Interface Contract]]
- [[_COMMUNITY_Debug CLI Commands|Debug CLI Commands]]
- [[_COMMUNITY_Launch CLI Commands|Launch CLI Commands]]
- [[_COMMUNITY_Sim Launcher (Isaac App)|Sim Launcher (Isaac App)]]
- [[_COMMUNITY_Sim Container Entrypoint|Sim Container Entrypoint]]
- [[_COMMUNITY_Environment Check Script|Environment Check Script]]
- [[_COMMUNITY_Third-Party Fetch Script|Third-Party Fetch Script]]
- [[_COMMUNITY_Smoke Takeoff Test|Smoke Takeoff Test]]
- [[_COMMUNITY_ROS Container Entrypoint|ROS Container Entrypoint]]
- [[_COMMUNITY_ZED Build Script|ZED Build Script]]
- [[_COMMUNITY_Image Pull Script|Image Pull Script]]
- [[_COMMUNITY_Host Setup Script|Host Setup Script]]

## God Nodes (most connected - your core abstractions)
1. `debug.sh script` - 16 edges
2. `launch.sh script` - 16 edges
3. `bisg_isaac README Overview` - 14 edges
4. `bisg_isaac Project Instructions (CLAUDE.md)` - 13 edges
5. `roadmap.md — 8 sequential phases, each gated by an exit test` - 12 edges
6. `plan.md — bisg_isaac digital twin project plan` - 11 edges
7. `Settings Layering & Precedence` - 10 edges
8. `cmd_report()` - 9 edges
9. `ADR-003: One PX4 Tag for SITL and Pixracer (v1.17.0)` - 9 edges
10. `Jetson Deploy Procedure` - 8 edges

## Surprising Connections (you probably didn't know these)
- `MAVROS Ops Procedure` --references--> `MAVROS Software Bridge`  [INFERRED]
  .claude/skills/mavros-ops/SKILL.md → docs/decisions/ADR-001-mavros.md
- `ADR-002: Docker-first Architecture` --references--> `Pegasus Simulator`  [INFERRED]
  docs/decisions/ADR-002-docker.md → README.md
- `ADR-003: One PX4 Tag for SITL and Pixracer (v1.17.0)` --references--> `Pegasus px4_mavlink_backend.py`  [INFERRED]
  docs/decisions/ADR-003-px4-version.md → .claude/skills/px4-sitl/SKILL.md
- `sim/configs/headless_fast.yaml — fast headless profile for regression tests and MAVLink/MAVROS work (no window, no materials, 640x360, grid world)` --references--> `Phase 1 — Dockerized single-drone sim: Isaac + Pegasus + PX4 SITL, one drone flies via QGC`  [INFERRED]
  sim/configs/headless_fast.yaml → docs/roadmap.md
- `Jetson Deploy Compose Stack` --references--> `Jetson Deploy Procedure`  [INFERRED]
  deploy/jetson/compose.yaml → .claude/skills/jetson-deploy/SKILL.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **ADR Decisions Governing Project Architecture** — claude_project_instructions, decisions_adr_001_mavros_decision, decisions_adr_002_docker_decision, decisions_adr_003_px4_version_decision [INFERRED 0.85]
- **MAVROS Bridge Pipeline (PX4 to ROS2)** — decisions_adr_001_mavros_mavros_bridge, mavros_ops_skill_offboard_state_machine, mavros_ops_skill_bisg_bringup_mavros_launch, px4_sitl_skill_instance_math [INFERRED 0.85]
- **ZED Sensor Contract Chain (Sim to Hardware)** — zed_contract_skill_interface_contract_doc, jetson_zed_params_zed_overlay, zed_readme_zed_sdk_image, zed_contract_skill_vio_mock [INFERRED 0.85]
- **Roadmap: 8 sequential phases, each gated by an exit test** — docs_roadmap_phase0, docs_roadmap_phase1, docs_roadmap_phase2, docs_roadmap_phase3, docs_roadmap_phase4, docs_roadmap_phase5, docs_roadmap_phase6, docs_roadmap_phase7, docs_roadmap_phase8 [EXTRACTED 1.00]
- **Core container technology stack: CycloneDDS transport + ROS 2 Jazzy distro + Docker image/compose strategy** — decisions_adr_004_dds_cyclonedds, decisions_adr_005_ros2_jazzy_jazzy, docs_plan_docker_strategy [INFERRED 0.85]
- **GPS-denied VIO state-estimation pipeline: ZED Mini positional tracking -> vio_relay -> mavros/odometry/out -> PX4 EKF2 external vision** — docs_hardware_zed_mini, docs_hardware_vio_relay, docs_interface_contract_topics_consumed, docs_plan_data_flows [EXTRACTED 1.00]

## Communities (17 total, 6 thin omitted)

### Community 0 - "Project Governance & ADRs"
Cohesion: 0.08
Nodes (51): docs/plan.md (referenced), bisg_isaac Project Instructions (CLAUDE.md), docs/roadmap.md (referenced), scripts/_common.sh, Config Directory Layering, config/50-pins.conf, ADR-001: MAVROS as PX4↔ROS2 Bridge, MAVROS Software Bridge (+43 more)

### Community 1 - "Shell Config Helpers"
Cohesion: 0.09
Nodes (23): _common.sh script, _BISG_ENV0, BISG_SRC, conf_default(), die(), fail(), FCU_URL, GCS_URL (+15 more)

### Community 2 - "Roadmap Phases"
Cohesion: 0.13
Nodes (23): vehicles/bisg_quad (Phase 4): USD of the real quad + Pegasus preset — mass, inertia, motor placement, thrust curve, ZED Mini mount, sim/assets README, Vehicle model measurements (Phase 4): mass/CG, arm length, thrust curve, inertia, sensor poses — feeds sim/assets/vehicles/bisg_quad, Workstation OS migration 22.04 -> 24.04 plan (§12): driver, container toolkit, Wayland/XWayland, host ROS2 Jazzy, cache volume preservation, roadmap.md — 8 sequential phases, each gated by an exit test, Phase 0 — Foundations: docs set, repo skeleton, pins, open questions answered, Phase 1 — Dockerized single-drone sim: Isaac + Pegasus + PX4 SITL, one drone flies via QGC, Phase 2 — ROS 2 + MAVROS control: bisg/ros Jazzy image, MAVROS to SITL, offboard mission node, sim time (+15 more)

### Community 3 - "Sim Performance & Remote Access"
Cohesion: 0.13
Nodes (20): sim/configs/headless_fast.yaml — fast headless profile for regression tests and MAVLink/MAVROS work (no window, no materials, 640x360, grid world), sim/configs/single_iris.yaml — one Iris quadrotor, PX4 SITL, warehouse world scenario (default, textured), performance.md — sim profiling, tuning knobs and measurements, NVIDIA "Simulation Performance Optimization Handbook" (Isaac Sim 6.0 docs, checked against pinned 5.1.0), headless_fast.yaml profile — regression/flight-stack, grid world, 640x360, rtf 1.27 (the profile for tests), perf: block knobs — disable_viewport_updates, limit_cpu_threads, skip_material_loading, width/height, renderer, min_frame_rate, physx_threads, Render cadence bug fix (2026-09-13): launcher called world.step(render=True) every physics step instead of honoring rendering_dt, 4x over-render at Pegasus defaults, starving physics; fixed to render 1 frame per round(rendering_dt/physics_dt) steps — warehouse headless went 79->186 steps/s (rtf 0.32->0.74), single_iris.yaml profile — default, textured warehouse, headless rtf 0.74 (+12 more)

### Community 4 - "DDS & ROS 2 Distro Choices"
Cohesion: 0.13
Nodes (20): CycloneDDS (rmw_cyclonedds_cpp) chosen everywhere — rationale: reliable across container boundaries with network_mode:host, unlike FastDDS shared-memory transport which is fragile across containers and DDS multicast which is unreliable on WiFi, ADR-004: CycloneDDS everywhere, zenoh bridge across WiFi, FastDDS — rejected: shared-memory transport fragile across containers, ROS_DOMAIN_ID — one per fleet run, drones share it, namespaces separate them; zenoh bridge can map domains if per-drone isolation is ever needed, zenoh-bridge-ros2dds — bridges drone/ground-station traffic over WiFi; only vehicle/state, vehicle/cmd, /fleet/* and low-rate telemetry allowed across (allow-list), ADR-005: ROS 2 Jazzy (Ubuntu 24.04) in all containers, ROS 2 Humble — host-only debug distro on Ubuntu 22.04, not used to build project packages, Isaac Sim 5.1 bundled ROS 2 bridge — Jazzy library set (exts/isaacsim.ros2.bridge/jazzy) (+12 more)

### Community 5 - "Hardware & Interface Contract"
Cohesion: 0.16
Nodes (19): Bench checklist (Phase 5, props OFF) — Pixracer flash, MAVROS heartbeat, ZED odom rate/TF, EV fusion healthy, offboard on bench, failsafe verified in SITL first, hardware.md — drone bill of materials, wiring, PX4 params, bench checklist, Jetson Orin NX (JetPack 7.2, L4T r38, Ubuntu 24.04, CUDA 13) companion computer, Pixracer flight controller (px4_fmu-v4, STM32F427), PX4 v1.17.0, flash at 95.3%, PX4 parameter table for EV/VIO fusion and GPS-denied flight — rationale per param (EKF2_EV_CTRL, EKF2_HGT_REF=Vision, EKF2_GPS_CTRL=0 indoor, offboard-loss failsafe), vio_relay — republishes ZED SDK positional-tracking odom (zed/zed_node/odom) to mavros/odometry/out, ZED Mini stereo camera — USB 3.0, 63mm baseline, built-in IMU, ZED SDK 5.4.1, tests/check_contract.py — parity checker validating topics, rates, TF chain, camera_info against the contract (+11 more)

### Community 6 - "Debug CLI Commands"
Cohesion: 0.26
Nodes (18): debug.sh script, cmd_clean_all(), cmd_clean_cache(), cmd_dds(), cmd_echo(), cmd_gpu(), cmd_hz(), cmd_kitlog() (+10 more)

### Community 7 - "Launch CLI Commands"
Cohesion: 0.27
Nodes (16): launch.sh script, cmd_all(), cmd_config(), cmd_down(), cmd_logs(), cmd_mavros(), cmd_restart(), cmd_ros() (+8 more)

### Community 8 - "Sim Launcher (Isaac App)"
Cohesion: 0.19
Nodes (7): App, main(), Serve the viewport as a still image over one TCP port.      The WebRTC client ne, Issue one viewport capture if the interval has elapsed. Never raises., resolve_vehicle_usd(), resolve_world(), WebView

### Community 9 - "Sim Container Entrypoint"
Cohesion: 0.50
Nodes (4): isaac_python_exec(), ROS_DISTRO, SIM_CONFIG, sim-entrypoint.sh script

### Community 10 - "Environment Check Script"
Cohesion: 0.70
Nodes (4): check_env.sh script, die(), pass(), wrn()

## Knowledge Gaps
- **40 isolated node(s):** `ros-entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO`, `build.sh script`, `BISG_SRC` (+35 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **6 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `plan.md — bisg_isaac digital twin project plan` connect `DDS & ROS 2 Distro Choices` to `Roadmap Phases`, `Sim Performance & Remote Access`, `Hardware & Interface Contract`?**
  _High betweenness centrality (0.038) - this node is a cross-community bridge._
- **Why does `todo.md — live checklist, phases and status` connect `Roadmap Phases` to `Sim Performance & Remote Access`?**
  _High betweenness centrality (0.019) - this node is a cross-community bridge._
- **What connects `ros-entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO` to the rest of the system?**
  _42 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Project Governance & ADRs` be split into smaller, more focused modules?**
  _Cohesion score 0.07607843137254902 - nodes in this community are weakly interconnected._
- **Should `Shell Config Helpers` be split into smaller, more focused modules?**
  _Cohesion score 0.09247311827956989 - nodes in this community are weakly interconnected._
- **Should `Roadmap Phases` be split into smaller, more focused modules?**
  _Cohesion score 0.13043478260869565 - nodes in this community are weakly interconnected._
- **Should `Sim Performance & Remote Access` be split into smaller, more focused modules?**
  _Cohesion score 0.13157894736842105 - nodes in this community are weakly interconnected._