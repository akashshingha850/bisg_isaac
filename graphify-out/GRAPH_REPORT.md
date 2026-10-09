# Graph Report - bisg_isaac  (2026-10-10)

## Corpus Check
- 120 files · ~87,417 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 21 file(s) not represented in the graph (top: (none) 10, .params 3, .xml 2)

## Summary
- 1105 nodes · 1756 edges · 90 communities (69 shown, 21 thin omitted)
- Extraction: 93% EXTRACTED · 6% INFERRED · 1% AMBIGUOUS · INFERRED: 112 edges (avg confidence: 0.82)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Config Compiler (zed.yaml)
- Depth to Obstacle Sectors
- ROS Bench & Service Clients
- Shell Scripts & Env Helpers
- Docker-First ADRs
- Build Scripts & Version Pins
- MAVROS vs MAVSDK Decision
- MAVROS Ops Skill
- Bridge Common & VIO Mock
- bisg CLI Launcher
- Known Bugs Register
- PX4 Bridge CLI Tests
- Sim Launcher Config
- Range/Flow Backend
- Interface Contract & ZED SDK
- Project Rules & Settings
- MAVROS/ZED Config Files
- Debug Commands
- Flight Test Helpers
- PX4 SITL Skill
- Video Mosaic Stream
- Isaac Sim Imports
- Deploy & Remote Skills
- Isaac Cache & bisg.conf
- ZED SDK Check Probe
- Health & Odometry Bridge
- Bridge Node Context
- Rate Meter
- Isaac Core Utils
- Fleet & Add-Drone Procedure
- single_iris Scenario
- ToF & Optical Flow Twin
- Bridge Module Base
- Debugging Docs
- Sim Performance & GPUs
- ZED Benchmarks (Orin NX)
- PX4 Bridge Multi-Vehicle
- Hardware Stack Pins
- Remote Views & Runbook
- Follow Camera
- Bridge Health Callbacks
- Tailscale ADR
- Pegasus Fast Path
- Sim Clock & PX4 Params
- Web Viewport Stream
- MAVROS Sim Time & Obstacle
- VIO Mock Node
- ZED Launch File
- tailscale.sh
- zed.sh
- Vehicle Spawn & ZED Features
- Push PX4 Params
- ROS Dev Tools
- headless_fast Scenario
- Roadmap Phases 0-2
- ZED Stack Components
- Phases 4-5 Assets & Hardware
- px4-bridge.sh
- Sim App & Boot Phases
- Propulsion Forces
- WebRTC View
- VIO Low-Res Scenario
- Phase 3 Sensors & Contract
- Swarm Phases 6-8
- Test Node Helpers
- Fake ZED Bridge Test
- px4-bridge entrypoint
- sim entrypoint
- Tailscale Policy
- drone.sh
- Subprocess Pumps A
- Subprocess Pumps B
- ros_env.sh
- fetch_sources.sh
- Stats Update
- Misc 75
- Misc 76
- Misc 77
- Misc 78
- Misc 79
- Misc 80
- Misc 81
- Misc 82
- Misc 83
- Misc 84
- Misc 85
- Misc 86
- Misc 88
- Misc 89

## God Nodes (most connected - your core abstractions)
1. `Real ZED SDK in the sim doc` - 18 edges
2. `launch.sh script` - 17 edges
3. `RangeFlowBackend` - 17 edges
4. `ZED Mini stack doc` - 17 edges
5. `Rate` - 16 edges
6. `debug.sh script` - 16 edges
7. `build_phases()` - 16 edges
8. `Health` - 15 edges
9. `Flight` - 15 edges
10. `CLAUDE.md project instructions` - 15 edges

## Surprising Connections (you probably didn't know these)
- `MAVROS launch wrapper (bisg_bringup mavros.launch.py)` --semantically_similar_to--> `MAVROS plugin_allowlist (lean variant)`  [INFERRED] [semantically similar]
  .claude/skills/mavros-ops/SKILL.md → docker/ros/mavros_lean.yaml
- `CycloneDDS Dockerfile.overlay` --semantically_similar_to--> `Cyclone DDS overlay for ZED L4T image`  [INFERRED] [semantically similar]
  docker/zed/README.md → .claude/skills/jetson-deploy/SKILL.md
- `PX4 instance/port/sys-id math` --shares_data_with--> `px4-bridge service`  [INFERRED]
  .claude/skills/px4-sitl/SKILL.md → docker/compose.yaml
- `SIM_VIEW values and resolution` --semantically_similar_to--> `SIM_VIEW key`  [INFERRED] [semantically similar]
  docs/configuration.md → CLAUDE.md
- `per-drone ZED Mini twin rig (320x180, mount 0.18)` --implements--> `Stereolabs zed-isaac-sim extension`  [INFERRED]
  docker/sim/configs/two_iris_vio_lowres.yaml → .claude/skills/zed-sdk/SKILL.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Pin-change regression gate** — claude_skills_sim_regression_skill_migration_gate, docker_sim_configs_four_iris_nozed, docker_sim_configs_eight_iris_nozed [INFERRED 0.75]
- **GPS-denied VIO configuration** — docker_sim_configs_single_iris_vio, docker_sim_px4_readme_ekf2_vision, docker_zed_zed_sim_block [EXTRACTED 0.95]
- **MAVROS plugin parameter and timing bugs** — docs_bugs_b3, docs_bugs_b6, docs_bugs_b8, docs_bugs_mavros_sim_time_py [EXTRACTED 1.00]
- **Selectable PX4 bridge options** — docs_decisions_adr_001_mavros_px4_bridge_selectable_service, docs_decisions_adr_001_mavros_mavros_bridge, docs_decisions_adr_001_mavros_mavsdk, docs_decisions_adr_001_mavros_uxrce_dds [EXTRACTED 1.00]
- **ZED stack: one YAML, one image, three services** — docs_decisions_adr_008_zed_stack_bisg_zed_image, docs_decisions_adr_008_zed_stack_zed_bridge_service, docs_decisions_adr_008_zed_stack_zed_video_service, docs_decisions_adr_008_zed_stack_zed_stack_compiler [EXTRACTED 0.95]
- **Isaac 6.0 sim-speed regression, cause, patch and docs** — docs_migration_errors_m8_sim_speed_regression, docs_migration_errors_m9_render_false, docs_migration_errors_m20_performance_doc_stale [INFERRED 0.85]
- **Sim real-time-factor levers and bottleneck** — docs_performance_python_bottleneck, sim_launcher_pegasus_fast, docs_performance_physics_dt, docs_performance_parallel_sims, docs_performance_render_cadence [INFERRED 0.85]
- **ZED SDK in sim pipeline** — docs_plan_zed_isaac_sim_ext, docs_plan_zed_ros2_wrapper, docs_bugs_bridge_odometry, docs_plan_px4_v1_17_0, docs_plan_mavros [INFERRED 0.85]
- **Interchangeable PX4 bridge backends** — docs_px4_bridge_px4_bridge_service, docs_plan_mavros, docs_px4_bridge_mavsdk_server, docs_px4_bridge_xrce_agent [EXTRACTED 1.00]
- **Remote sim viewing transports** — docs_remote_access_web_view, docs_remote_access_webrtc_view, docs_remote_access_tailscale_service, docs_remote_access_sim_view_addr [EXTRACTED 1.00]
- **HD720 image path needs rmem_max or low-res scenario** — docs_setup_rmem_max_sysctl, docs_setup_cyclonedds_xml, docker_sim_configs_single_iris_vio_lowres_resolution, docker_sim_configs_single_iris_zed_sensor [INFERRED 0.85]
- **ZED benchmark resource findings** — docs_zed_benchmark_base_pipeline_cost, docs_zed_benchmark_ram_constraint, docs_zed_benchmark_ai_startup, docs_zed_benchmark_bridge_container [EXTRACTED 1.00]
- **ZED config-to-PX4 pipeline** — docker_zed_zed, docs_zed_stack_compiler, docker_compose_zed_service, docker_compose_zed_bridge_service, docker_compose_zed_video_service [EXTRACTED 1.00]
- **ToF + optical flow twin feeding PX4 EKF2** — docker_sim_configs_single_iris_flow, docs_range_flow_range_flow_py, docs_range_flow_lw20c_tof, docs_range_flow_pmw3901_flow, docs_range_flow_ekf2_params [EXTRACTED 1.00]
- **Settings layering across config files** — claude_settings_layering, docs_configuration, docker_zed_zed, docs_configuration_precedence, docs_configuration_adding_a_key [INFERRED 0.85]

## Communities (90 total, 21 thin omitted)

### Community 0 - "Config Compiler (zed.yaml)"
Cohesion: 0.05
Nodes (44): difflib, ConfigError, deep_merge(), _flatten_params(), load(), docker/zed/zed.yaml -> zed_wrapper parameters + the list of services to start.…, {section: {key: default}} from the wrapper's own YAML files (the model file…, Module master switch. Modules without `enabled` (camera, video, sensors,… (+36 more)

### Community 1 - "Depth to Obstacle Sectors"
Cohesion: 0.05
Nodes (30): cv2, Image, Depth image -> 72 x 5 deg obstacle sectors. numpy only, so it is unit-testable…, Depth image (H x W, metres, float32) + pinhole intrinsics -> 72 ranges [m]: inf…, sectors_from_depth(), depth_to_bgr(), Flow, label() (+22 more)

### Community 2 - "ROS Bench & Service Clients"
Cohesion: 0.09
Nodes (32): rosidl_runtime_py_utilities, std_srvs_srv, Bench, build_phases(), toggle(), run(), chk_cloud(), chk_depth() (+24 more)

### Community 3 - "Shell Scripts & Env Helpers"
Cohesion: 0.08
Nodes (30): build_isaac_ext.sh script, stamp(), _BISG_ENV0, BISG_SRC, conf_default(), container_running(), die(), fail() (+22 more)

### Community 4 - "Docker-First ADRs"
Cohesion: 0.06
Nodes (40): ADR-002 Docker-first including Isaac Sim, bisg/sim, bisg/ros, bisg/zed images, network_mode host everywhere, ADR-004 CycloneDDS everywhere, zenoh bridge over WiFi, rmw_cyclonedds_cpp with committed cyclonedds.xml, zenoh-bridge-ros2dds with allow-list, ADR-005 ROS 2 Jazzy (Ubuntu 24.04) in all containers, Isaac Sim bundled Jazzy ROS 2 bridge (exts/isaacsim.ros2.core/jazzy) (+32 more)

### Community 5 - "Build Scripts & Version Pins"
Cohesion: 0.08
Nodes (27): build.sh script, src_stamp(), ADR-003 One PX4 tag for SITL and Pixracer, MAVROS 2.15.1, Pegasus PR #144 head fcb99c0, px4_fmu-v4_default Pixracer firmware (95.3% flash), PX4_TAG Dockerfile arg, Re-validation on Isaac Sim 6.0 (2026-10-02) (+19 more)

### Community 6 - "MAVROS vs MAVSDK Decision"
Cohesion: 0.09
Nodes (29): ADR-001 MAVROS as PX4-ROS 2 bridge, MAVROS 2.x PX4-ROS 2 bridge, MAVROS lean plugin list (mavros_lean.yaml), MAVSDK 4.x, One selectable px4-bridge service (PX4_BRIDGE), PX4-link study (archive/px4-link-study), uXRCE-DDS (rejected alternative), ADR-008 One YAML, one image, small services (+21 more)

### Community 7 - "MAVROS Ops Skill"
Cohesion: 0.09
Nodes (23): mavros-ops skill, MAVROS frames (ENU map, odom/base_link), GPS-denied EV yaw-align limitation (fly and land in OFFBOARD), MAVROS 2.15.1 plugin nodes ignore params files, OFFBOARD state machine (offboard_controller), Sim time and PX4 timesync (use_sim_time), sim-regression skill, Migration / pin-change gate (smoke, vio_flight, zed_depth_box) (+15 more)

### Community 8 - "Bridge Common & VIO Mock"
Cohesion: 0.13
Nodes (17): collections, csv, vio_mock — sim-only mock VIO source (docs/interface-contract.md, zed-contract…, Shared pieces of the bridge modules (rclpy only where a function needs a node)., geometry_msgs_msg, mavros_msgs_srv, random, rclpy (+9 more)

### Community 9 - "bisg CLI Launcher"
Cohesion: 0.21
Nodes (21): cmd_all(), cmd_build(), cmd_config(), cmd_down(), cmd_logs(), cmd_mavros(), cmd_restart(), cmd_ros() (+13 more)

### Community 10 - "Known Bugs Register"
Cohesion: 0.11
Nodes (21): Known bugs register, B1 No usable failsafe while GPS-denied, B15 Sim rig parameters duplicate wrapper config, B16 Contract TF frames drone_n prefixed but wrapper cannot prefix, B17 SDK odometry into PX4 accuracy outside bound, B18 SDK connects to sim stream once per run, B19 enable_streaming crashes wrapper in sim, B2 HD720 ZED images never reach subscriber (+13 more)

### Community 11 - "PX4 Bridge CLI Tests"
Cohesion: 0.15
Nodes (6): json, subprocess, bridge(), compose_service(), Px4BridgeCli, ./bisg px4-bridge: one compose service (px4-bridge), PX4_BRIDGE picks what its…

### Community 12 - "Sim Launcher Config"
Cohesion: 0.13
Nodes (14): argparse, carb, M14 smoke test --patience for low RTF, physics_dt (also PX4 IMU rate), single_iris.yaml profile, math, pymavlink, Real-time factor (sim seconds per wall second) as one more line of Kit's own… (+6 more)

### Community 13 - "Range/Flow Backend"
Cohesion: 0.13
Nodes (6): Backend, attach(), RangeFlowBackend, Range from `mount` (body FLU) straight down the body Z axis to the first…, Return a RangeFlowBackend for a scenario vehicle, or None when neither sensor…, cfg: the vehicle's `sensors:` block (`tof:` and/or `optical_flow:`); px4: the…

### Community 14 - "Interface Contract & ZED SDK"
Cohesion: 0.15
Nodes (20): Sim and hardware obey interface contract, Real ZED SDK runs in the sim, swarm-spawn skill, VRAM / resolution limits for multi-drone, ZED SDK per-drone mode (stream port 30000+2*id), Vehicle interface contract, Topics consumed by the vehicle, Frame prefix gap (B16) (+12 more)

### Community 15 - "Project Rules & Settings"
Cohesion: 0.11
Nodes (19): CLAUDE.md project instructions, ADR-002 every runtime component is a Docker service, Migration gate checks (smoke, vio_flight, zed_depth_box), Build phase by phase, no scope widening, Settings layering, SIM_VIEW key, Tailscale remote access (ADR-009), Host facts: Workstation A and B (+11 more)

### Community 16 - "MAVROS/ZED Config Files"
Cohesion: 0.20
Nodes (17): MAVROS launch wrapper (bisg_bringup mavros.launch.py), ZED stack (ADR-008), zed-video service, MAVROS plugin_allowlist (lean variant), services.px4_bridge, services.qgc_video, B17 SDK VIO closed-loop accuracy, Unbuilt bridge modules M5/M6/M7/M11 (+9 more)

### Community 17 - "Debug Commands"
Cohesion: 0.26
Nodes (18): cmd_clean_all(), cmd_clean_cache(), cmd_dds(), cmd_echo(), cmd_gpu(), cmd_hz(), cmd_kitlog(), cmd_mavlink() (+10 more)

### Community 18 - "Flight Test Helpers"
Cohesion: 0.16
Nodes (4): Exception, Abort, Flight, Fly to (dx, dy) from the start point at `alt` m above it; hold `settle` seconds.

### Community 19 - "PX4 SITL Skill"
Cohesion: 0.12
Nodes (17): px4-sitl skill, Common arming/offboard rejections, PX4 instance/port/sys-id math, Lockstep off in SITL, Sim frame-rate IMU: imu_fusion false, single_iris_vio scenario (GPS-denied), depth_box test cuboid, PX4 parameter files README (+9 more)

### Community 20 - "Video Mosaic Stream"
Cohesion: 0.18
Nodes (6): main(), Image, Node, The tile of one source: re-decoded when a new frame arrived, a 'no signal'…, The optical-flow tile as a bgr8 sensor_msgs/Image with its source's header,…, VideoStream

### Community 21 - "Isaac Sim Imports"
Cohesion: 0.13
Nodes (14): isaacsim, isaacsim_core_experimental_utils_app, isaacsim_core_rendering_manager, isaacsim_core_simulation_manager, omni_timeline, os, pegasus_simulator_logic_backends_px4_mavlink_backend, pegasus_simulator_logic_interface_pegasus_interface (+6 more)

### Community 22 - "Deploy & Remote Skills"
Cohesion: 0.14
Nodes (15): jetson-deploy skill, Cyclone DDS overlay for ZED L4T image, Pixracer flash and params, Preflight checklist (props on), sim-launch skill, web and webrtc remote views, zed-sdk skill, SDK connects once per sim run (B18) (+7 more)

### Community 23 - "Isaac Cache & bisg.conf"
Cohesion: 0.16
Nodes (13): Isaac 6.0 kit shader cache volume, Isaac Sim 6.0 + Pegasus PR #144 + PX4 v1.17.0 stack, config/bisg.conf (merged project settings), One key, one place rule, Isaac cache named volumes (isaac-cache-kit etc.), Compose profiles (sim, sim-headless, ros, tools, px4-bridge, zed, drone, tailscale), px4-bridge service, sim-headless service (+5 more)

### Community 24 - "ZED SDK Check Probe"
Cohesion: 0.17
Nodes (9): rosgraph_msgs_msg, main(), path_length(), Probe, Node, rate(), ZED SDK contract + health check — the same script for the sim and the real…, RMSE (m) of the SDK odometry against ground truth after the only alignment that… (+1 more)

### Community 25 - "Health & Odometry Bridge"
Cohesion: 0.19
Nodes (10): copy, M10 — ZED health -> one status topic + STATUSTEXT in QGroundControl. Publishes…, M1 — ZED positional tracking -> PX4 EKF2 external vision (MAVROS odometry/out).…, mavros_msgs_msg, nav_msgs_msg, std_msgs_msg, main(), px4_bridge against FAKE ZED + MAVROS topics — no camera, no sim, no PX4. Runs… (+2 more)

### Community 26 - "Bridge Node Context"
Cohesion: 0.20
Nodes (10): Context, What every module needs to know: namespaces and a way to reach the others., main(), python3 -m zed_stack.bridge — the px4_bridge service (compose `zed-bridge`).…, ROS 2 image topics -> RTP/H.264 over UDP, for QGroundControl's "UDP h.264 Video…, gi, gi_repository, rclpy_node (+2 more)

### Community 27 - "Rate Meter"
Cohesion: 0.18
Nodes (3): Rate, Messages per second over a sliding window, and how long ago the last one came…, Odometry2Px4

### Community 28 - "Isaac Core Utils"
Cohesion: 0.18
Nodes (13): isaacsim_core_utils, isaacsim_core_utils_extensions, isaacsim_core_utils_prims, omni_graph_core, omni_usd, pxr, Rotation, stream_port() (+5 more)

### Community 29 - "Fleet & Add-Drone Procedure"
Cohesion: 0.15
Nodes (13): ADR-001 MAVROS as PX4-ROS 2 bridge, PX4_BRIDGE selector (mavros|mavsdk|xrce|none), bisg_fleet fleet manager roster, scripts/gen_compose.py, Add/remove drone N procedure (Phase 6), Endpoints table (DRONE_ID, FCU_URL, GCS_URL...), Namespace /drone_<n>, Real ZED SDK in the sim (ZED_SOURCE=sdk) (+5 more)

### Community 30 - "single_iris Scenario"
Cohesion: 0.17
Nodes (13): single_iris.yaml scenario, follow_cam (sim/launcher/follow_cam.py), px4.enable_lockstep false, perf.pegasus_fast (sim/launcher/pegasus_fast.py), physics_dt 120 Hz, px4.params: [collision_prevention], Pegasus ROS2Backend ground truth state, app.ros_clock (/clock) (+5 more)

### Community 31 - "ToF & Optical Flow Twin"
Cohesion: 0.29
Nodes (13): single_iris_flow scenario, px4.params ekf2_flow_range, optical_flow sensor config (PMW3901), tof sensor config (LW20/C), mavros/hrlv_ez4_pub Range topic, Downward ToF + optical flow twin doc, Analytic (not image-based) flow, Sensors fed directly to PX4 SITL (+5 more)

### Community 32 - "Bridge Module Base"
Cohesion: 0.15
Nodes (4): Module, Base of a bridge module. `status()` is polled once a second by the health…, ObstacleDistance, MAVROS defaults the obstacle plugin to GLOBAL; ours is a body-frame (FRD) scan.

### Community 33 - "Debugging Docs"
Cohesion: 0.17
Nodes (13): Debugging (doc), debug clean-cache / clean-all / setup --rebuild, ./bisg debug dds, ./bisg debug gpu, ./bisg debug kitlog, ./bisg debug perf (rtf heartbeat), ./bisg debug ports / mavlink, ./bisg debug px4 (PX4 shell without QGC) (+5 more)

### Community 34 - "Sim Performance & GPUs"
Cohesion: 0.17
Nodes (13): asyncRendering flags hang boot, Isaac Sim 6.0 RTF measurements (RTX 4500), Two sims one per GPU for 8 drones, Single-thread Pegasus Python bottleneck (M8), isaac-cache-kit shader cache (190 s first boot), Workstation B 2x RTX 6000 Ada measurements, Project plan - bisg_isaac digital twin, config/bisg.conf pins block (+5 more)

### Community 35 - "ZED Benchmarks (Orin NX)"
Cohesion: 0.15
Nodes (13): ZED module test + benchmark doc, AI module slow first start (obj det 278 s), Base pipeline is the cost, products nearly free, data/zed_bench_2026-10-05.json, NEURAL_LIGHT depth mode, Plane detection via /clicked_point, RAM is the Orin NX constraint, Result: 16/16 phases pass (1 warning) (+5 more)

### Community 36 - "PX4 Bridge Multi-Vehicle"
Cohesion: 0.18
Nodes (11): PX4-link study, scripts/gen_compose.py, Multi-vehicle ports/IDs/namespaces model, The PX4 bridge, DRONE_ID = namespace = MAV_SYS_ID, mavros/mavsdk share one MAVLink port, mavsdk_server (gRPC 50051), Pixracer bridge parameters (TELEM2 921600) (+3 more)

### Community 37 - "Hardware Stack Pins"
Cohesion: 0.20
Nodes (11): ADR-001..005, ADR-009 decisions, bisg/ros image, Jetson Orin NX JetPack 7.2, MAVROS 2.15.1 bridge, Pixracer px4_fmu-v4, PX4 v1.17.0, Sim-to-real parity rules, GPS-denied state estimation path (VIO to EKF2) (+3 more)

### Community 38 - "Remote Views & Runbook"
Cohesion: 0.22
Nodes (11): Watching the sim from somewhere else, Cloudflare Tunnel (does not carry WebRTC), VS Code tunnel / Simple Browser path, SIM_VIEW=web (TCP 8899 still frames), Runbook - simulation stack, ./bisg CLI cheat sheet, headless_fast scenario run, MAVROS smoke connection (+3 more)

### Community 41 - "Tailscale ADR"
Cohesion: 0.20
Nodes (10): ADR-009 Remote access via Tailscale compose service, --accept-dns=false, ADR-002 Docker-first reproducibility, No auth keys decision, Own compose project bisg-tailscale, tailscale service (v1.102.5, host network, NET_ADMIN), SIM_VIEW_ADDR=tailscale, bisg-tailscale_tailscale-state volume (+2 more)

### Community 42 - "Pegasus Fast Path"
Cohesion: 0.22
Nodes (7): logging, pegasus_simulator_logic_backends_backend, scipy_spatial_transform, Follow camera for the GUI viewport, in the spirit of Gazebo's "follow" mode:…, _wrap(), Per-step speed-ups for Pegasus on Isaac Sim 6.0 (docs/performance.md,…, Downward ToF rangefinder + optical-flow sensor for a vehicle, fed straight to…

### Community 43 - "Sim Clock & PX4 Params"
Cohesion: 0.20
Nodes (7): apply_px4_params(), Static test objects from the scenario (`world.objects`), e.g. a box to check…, Hand PX4 parameter files (docker/sim/px4/*.params) to PX4 SITL at boot.…, Publish /clock (sim time) once per physics step (docs/interface-contract.md).…, resolve_world(), SimClock, spawn_objects()

### Community 44 - "Web Viewport Stream"
Cohesion: 0.22
Nodes (5): Serve the viewport as a still image over one TCP port. The WebRTC client needs…, Issue one viewport capture if the interval has elapsed. Never raises., WebView, do_GET(), _send()

### Community 45 - "MAVROS Sim Time & Obstacle"
Cohesion: 0.25
Nodes (6): main(), Switch every MAVROS plugin node to use_sim_time:=true (sim stack only,…, M2 — ZED depth image -> PX4's 72-sector obstacle map (MAVROS obstacle/send ->…, rcl_interfaces_msg, rcl_interfaces_srv, sensor_msgs_msg

### Community 46 - "VIO Mock Node"
Cohesion: 0.22
Nodes (5): main(), Node, VioMock, PoseStamped, TwistStamped

### Community 47 - "ZED Launch File"
Cohesion: 0.22
Nodes (7): zed_wrapper for drone N, with the contract's topic names. Used by BOTH the sim…, launch, launch_actions, launch_launch_description_sources, launch_ros_actions, launch_ros_substitutions, launch_substitutions

### Community 48 - "tailscale.sh"
Cohesion: 0.58
Nodes (8): backend(), connected(), login(), reach(), tailscale.sh script, start(), ts(), vcompose()

### Community 49 - "zed.sh"
Cohesion: 0.44
Nodes (8): have_frames(), zed.sh script, start_services(), svc_name(), video_hint(), video_ip(), ZED_SIM_PORT, zexec()

### Community 50 - "Vehicle Spawn & ZED Features"
Cohesion: 0.25
Nodes (6): resolve_vehicle_usd(), Features, load_features(), Read the ZED switches from docker/zed/zed.yaml, the file the real zed_wrapper…, publish_imu(), Physically-simulated IMU on `{body_path}/zed_imu_link`, published on…

### Community 51 - "Push PX4 Params"
Cohesion: 0.32
Nodes (7): B11 push_px4_params cannot finish on SITL, encode(), load_params(), main(), Push PX4 EKF2/GPS params over MAVLink (Phase 3 — GPS-denied flight on ZED Mini…, PX4/MAVLink PARAM_SET always carries a float32 on the wire; non-REAL32 types…, struct

### Community 52 - "ROS Dev Tools"
Cohesion: 0.29
Nodes (6): ros dev-shell service, foxglove bridge tool, rqt tool, rviz tool, ROS_DOMAIN_ID=auto per-hostname, Shared DDS domain incident

### Community 53 - "headless_fast Scenario"
Cohesion: 0.33
Nodes (7): headless_fast.yaml scenario, app.render: false, world preset Default Environment, Iris vehicle id 0 (ros2 disabled), perf.skip_material_loading, app.stream: off, sensors.zed.enabled: false

### Community 54 - "Roadmap Phases 0-2"
Cohesion: 0.29
Nodes (7): CycloneDDS + zenoh-bridge-ros2dds, network_mode host + ROS_DOMAIN_ID isolation, ROS 2 Jazzy, mission_square exit test, Phase 0 Foundations, Phase 1 Dockerized single-drone sim, Phase 2 ROS 2 + MAVROS control

### Community 55 - "ZED Stack Components"
Cohesion: 0.29
Nodes (7): Emulated ZED rig fallback (removed), bisg/zed image, Risk register R1-R10, zed-isaac-sim extension v5.2.1, ZED Mini camera, zed-ros2-wrapper, ZED SDK 5.4.1

### Community 56 - "Phases 4-5 Assets & Hardware"
Cohesion: 0.29
Nodes (7): bisg_quad vehicle model, compose drone profile (px4-bridge, drone-zed, zed-bridge, zed-video), Phase 4 Digital-twin assets and models, Phase 5 Hardware single drone, real_drone.launch.py and vio_relay, sim/worlds README, Site worlds (Phase 4): <site>/ with render asset (3DGS/NuRec/mesh, git-ignored), collision.usda proxies, spawn.yaml (spawn points, geofence, geo-origin)

### Community 57 - "px4-bridge.sh"
Cohesion: 0.38
Nodes (3): pcompose(), px4-bridge.sh script, stop()

### Community 58 - "Sim App & Boot Phases"
Cohesion: 0.33
Nodes (4): App, main(), phase(), Boot-phase timing: `[launch] INFO boot +NNs: <what>` (where the cold/warm boot…

### Community 59 - "Propulsion Forces"
Cohesion: 0.43
Nodes (6): apply(), apply_force(), apply_torque(), handle_propeller_visual(), _prim(), update()

### Community 60 - "WebRTC View"
Cohesion: 0.33
Nodes (6): app.stream webrtc, M4 WebRTC extension replaced in 6.0, SIM_VIEW_ADDR, View settings in config/bisg.conf, Isaac Sim WebRTC Streaming Client, SIM_VIEW=webrtc (TCP 49100 + UDP 47998)

### Community 61 - "VIO Low-Res Scenario"
Cohesion: 0.33
Nodes (6): single_iris_vio_lowres.yaml scenario, bugs.md B2 rmem_max, Isaac Sim 6.0 migration use, ZED resolution [320, 180], single_iris_vio.yaml (extends parent), sensors.zed 320x180 block

### Community 62 - "Phase 3 Sensors & Contract"
Cohesion: 0.40
Nodes (6): B13 No automated camera-view-unobstructed check, Fixed: ZED camera blocked/backwards/wrong FOV, tests/check_contract.py, Phase 3 Sensors, ZED Mini contract, VIO, bisg_vehicle/vio_mock (removed), ZED SDK in sim (ZED_SOURCE=sdk)

### Community 63 - "Swarm Phases 6-8"
Cohesion: 0.33
Nodes (6): bisg_fleet fleet manager, bisg_vehicle package, Phase 6 Swarm in sim, Phase 7 Hardware swarm, Phase 8 Task library + CI, zenoh-bridge-ros2dds hardware swarm network

### Community 64 - "Test Node Helpers"
Cohesion: 0.40
Nodes (3): main(), spin(), wait()

### Community 66 - "px4-bridge entrypoint"
Cohesion: 0.70
Nodes (4): mavros(), mavsdk(), entrypoint.sh script, xrce()

### Community 67 - "sim entrypoint"
Cohesion: 0.50
Nodes (4): isaac_python_exec(), ROS_DISTRO, entrypoint.sh script, SIM_CONFIG

### Community 68 - "Tailscale Policy"
Cohesion: 0.40
Nodes (5): DDS discovery does not cross tailnet, No Tailscale auth keys policy, GCS_URL for QGroundControl over tailnet, tailscale compose service, plain tailscaled instead of containerboot

### Community 69 - "drone.sh"
Cohesion: 0.50
Nodes (3): drone.sh script, ZED_STACK_SIM, zexec()

### Community 70 - "Subprocess Pumps A"
Cohesion: 0.67
Nodes (3): main(), pump(), wait()

### Community 71 - "Subprocess Pumps B"
Cohesion: 0.67
Nodes (3): main(), pump(), wait()

## Ambiguous Edges - Review These
- `B15 Sim rig parameters duplicate wrapper config` → `sim/launcher/zed_rig.py (emulated rig)`  [AMBIGUOUS]
  docs/bugs.md · relation: conceptually_related_to
- `B16 Contract TF frames drone_n prefixed but wrapper cannot prefix` → `sim/launcher/zed_rig.py (emulated rig)`  [AMBIGUOUS]
  docs/bugs.md · relation: conceptually_related_to
- `vio_mock (removed)` → `ZED bridge odometry module`  [AMBIGUOUS]
  docs/bugs.md · relation: conceptually_related_to
- `ZED Mini model table` → `vio_relay`  [AMBIGUOUS]
  docs/hardware.md · relation: conceptually_related_to
- `vio_relay` → `Bench checklist (Phase 5, props OFF)`  [AMBIGUOUS]
  docs/hardware.md · relation: conceptually_related_to
- `zed-isaac-sim extension v5.2.1` → `Emulated ZED rig fallback (removed)`  [AMBIGUOUS]
  docs/plan.md · relation: conceptually_related_to
- `zed-isaac-sim extension v5.2.1` → `vio_mock (older plan, removed)`  [AMBIGUOUS]
  docs/plan.md · relation: conceptually_related_to
- `bisg_vehicle/vio_mock (removed)` → `ZED SDK in sim (ZED_SOURCE=sdk)`  [AMBIGUOUS]
  docs/roadmap.md · relation: conceptually_related_to
- `zed-isaac-sim extension build` → `Emulated ZED rig (removed)`  [AMBIGUOUS]
  docs/setup.md · relation: conceptually_related_to

## Knowledge Gaps
- **159 isolated node(s):** `entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO`, `ros_env.sh script`, `ROS_DOMAIN_ID` (+154 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 406 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **21 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `B15 Sim rig parameters duplicate wrapper config` and `sim/launcher/zed_rig.py (emulated rig)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `B16 Contract TF frames drone_n prefixed but wrapper cannot prefix` and `sim/launcher/zed_rig.py (emulated rig)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `vio_mock (removed)` and `ZED bridge odometry module`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `ZED Mini model table` and `vio_relay`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `vio_relay` and `Bench checklist (Phase 5, props OFF)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `zed-isaac-sim extension v5.2.1` and `Emulated ZED rig fallback (removed)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `zed-isaac-sim extension v5.2.1` and `vio_mock (older plan, removed)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._