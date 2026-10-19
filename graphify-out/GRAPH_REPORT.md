# Graph Report - bisg_isaac  (2026-10-20)

## Corpus Check
- 163 files · ~187,239 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1656 nodes · 2752 edges · 187 communities (96 shown, 91 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 163 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- VIO & Range/Flow Evaluation
- ZED Stack Config & Tests
- ZED Bridge Common & Health
- ZED Bench Harness
- Shell Common & ZED Ext Build
- VIO Report & Bag Tools
- VIO Calibration & Campaign Docs
- VIO Campaign Runner
- MAVROS Sim-Time & Test Helpers
- Flight Test Benches
- VIO Eval Unit Tests
- Sim Launcher App
- Offboard & Pool Probe Collect
- launch.sh Commands
- Range/Flow Sensor Backend
- PX4 Params & Foxglove Probe
- Offboard Controller
- Video Mosaic Rendering
- ZED Drone Launch & TF
- PX4 Bridge CLI Tests
- Raptor CAD Build Pipeline
- ZED SDK in Sim (ADR-007)
- Project Plan & ADRs
- debug.sh Commands
- QGC Video Streams
- Configuration Guide
- Known Bugs & GPS-Denied Default
- Raptor Vehicle Asset
- Scenario Configs & Perf Knobs
- CAD to USD & Pool Probe
- Open Risks & Debug Notes
- ZED Stack (ADR-008)
- MAVLink Offboard Tests
- Follow Cam & RTF HUD
- Sim Regression Skill & Gate
- headless_fast Scenario
- ZED SDK Rig Config
- ZED Odometry Bridge & Bench Config
- Bridge Context & Node
- Roadmap Phases
- Tailscale Script
- ZED SDK Check
- Compose & Shader Cache
- MAVROS Ops Skill
- Remote Access Tooling
- ZED Crash Backtrace Hook (R9)
- Chase Camera
- Follow Camera
- Flow-Only Scenario
- Migration Errors & Known Bugs
- Performance Docs (Hover & physics_dt)
- Runbook & GPS-Denied Estimation
- README & Project Overview
- VIO Scenarios
- Web Viewport Streaming
- PX4 Bridge Choice
- Docker-First & DDS ADRs
- Build Pins & PX4 Version
- MAVROS over XRCE (ADR-001)
- ToF & Flow Benchmark
- bag.sh Recording
- info.sh Addresses
- Jetson Deploy Skill
- PX4 SITL Skill
- PX4 Bridge Entrypoint
- Scenario Variants
- Vehicle Spawn & ZED Features
- Bag Profiles & GPU Troubleshooting
- Resets & Debug Quirks
- Camera Render Cost (M8)
- Setup & Images
- Contract Checker Module
- zed.sh Script
- Contract Checker Class
- VIO Archive Regression Tests
- ZED Contract Skill
- Foxglove Layout Tooling
- Pegasus Fork (ADR-010)
- Bench Day & Benchmarks
- Collision Prevention Test
- Raptor Build & Depth Box Test
- Pegasus Force Application
- Debugging Guide
- DDS & Host Checks
- Isaac 6.0 Migration & Physics Rate
- Speed Levers Tried
- Tailscale Access (ADR-009)
- px4-bridge.sh
- Mosaic Tests
- Mission Square
- Scenario Locator Loader
- Boot Time Findings
- ROS Bag Profiles
- Sim Entrypoint
- EV Fusion Fallbacks
- M8 Sim Speed Investigation
- check_env.sh Preflight
- drone.sh
- Subprocess Helpers
- Config README
- build.sh Script
- ROS Env
- Host ROS Install
- bisg CLI
- ROS Entrypoint
- setuptools Stub
- ZED Bridge Package
- Optical Flow Topics
- ROS Env Defaults (M13)
- IMUSensor Port
- Low-RTF Test Timeouts
- Pegasus Pin (M18)
- WebRTC Livestream (M4)
- ZED Image Rate (M7)
- Ablation Results Data
- Ablation Configs
- Frame-Gap Error Source
- EKF2 Heading Lag
- Yaw Slip Source
- Lever-Arm & Calibration
- pull_images.sh
- setup.sh
- vio.sh
- Hardware Details (1)
- Hardware Details (2)
- Hardware Details (3)
- Hardware Details (4)
- Hardware Details (5)
- Hardware Details (6)
- Hardware Details (7)
- Hardware Details (8)
- Hardware Details (9)
- Hardware Details (10)
- Hardware Details (11)
- Hardware Details (12)
- Hardware Details (13)
- Hardware Details (14)
- Hardware Details (15)
- Hardware Details (16)
- Hardware Details (17)
- Hardware Details (18)
- Hardware Details (19)
- Hardware Details (20)
- Interface Contract Topics (1)
- Interface Contract Topics (2)
- Interface Contract Topics (3)
- Interface Contract Topics (4)
- Interface Contract Topics (5)
- Interface Contract Topics (6)
- Interface Contract Topics (7)
- Interface Contract Topics (8)
- Interface Contract Topics (9)
- Interface Contract Topics (10)
- Interface Contract Topics (11)
- Interface Contract Topics (12)
- Interface Contract Topics (13)
- Interface Contract Topics (14)
- Interface Contract Topics (15)
- Interface Contract Topics (16)
- Interface Contract Topics (17)
- Interface Contract Topics (18)
- Interface Contract Topics (19)
- Interface Contract Topics (20)
- Interface Contract Topics (21)
- Interface Contract Topics (22)
- Migration Error Notes (1)
- Migration Error Notes (2)
- Migration Error Notes (3)
- Migration Error Notes (4)
- Migration Error Notes (5)
- VIO Campaign Details (1)
- VIO Campaign Details (2)
- VIO Campaign Details (3)
- VIO Campaign Details (4)
- VIO Campaign Details (5)
- VIO Campaign Details (6)
- VIO Campaign Details (7)
- VIO Findings Details (1)
- VIO Findings Details (2)
- VIO Findings Details (3)
- VIO Findings Details (4)
- VIO Findings Details (5)
- VIO Findings Details (6)
- VIO Findings Details (7)
- VIO Findings Details (8)
- VIO Findings Details (9)

## God Nodes (most connected - your core abstractions)
1. `Known bugs (bugs.md)` - 23 edges
2. `zed.yaml (ZED stack config)` - 22 edges
3. `single_iris scenario` - 20 edges
4. `RangeFlowBackend` - 18 edges
5. `OffboardController` - 18 edges
6. `Doc reading order` - 18 edges
7. `Flight` - 17 edges
8. `analyse()` - 17 edges
9. `launch.sh script` - 17 edges
10. `Rate` - 16 edges

## Surprising Connections (you probably didn't know these)
- `MAVROS launch wrapper (bisg_bringup mavros.launch.py)` --semantically_similar_to--> `MAVROS lean plugin allowlist`  [INFERRED] [semantically similar]
  .claude/skills/mavros-ops/SKILL.md → docker/ros/mavros_lean.yaml
- `zed-sdk skill` --semantically_similar_to--> `Real ZED SDK running in sim via zed-isaac-sim extension`  [INFERRED] [semantically similar]
  .claude/skills/zed-sdk/SKILL.md → CLAUDE.md
- `Migration / pin-change gate` --semantically_similar_to--> `Three migration gate checks (smoke, vio_flight, zed_depth_box)`  [INFERRED] [semantically similar]
  .claude/skills/sim-regression/SKILL.md → CLAUDE.md
- `Contract changes first, then sim, then real` --semantically_similar_to--> `Interface contract first rule`  [INFERRED] [semantically similar]
  .claude/skills/zed-contract/SKILL.md → CLAUDE.md
- `docker/compose.yaml (single compose for workstation and Jetson)` --implements--> `Docker-first runtime components (ADR-002)`  [INFERRED]
  docker/compose.yaml → CLAUDE.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **ZED stack: one YAML, one image, three services** — docs_zed_stack_zed_yaml, docs_decisions_adr_008_zed_stack_bisg_zed_image, docs_decisions_adr_008_zed_stack_zed_bridge_service, docs_decisions_adr_008_zed_stack_zed_video_service, docs_decisions_adr_008_zed_stack_zed_stack_compiler [EXTRACTED 0.95]
- **Foxglove bridge, Lichtblick UI and layout tooling** — docker_ros_tools_foxglove_tool, docker_compose_lichtblick_service, docker_ros_foxglove_readme_raptor_layout [EXTRACTED 1.00]
- **GPS-denied EKF2 inputs: ZED VIO, LW20, PMW3901, baro** — docs_range_flow_tof_lw20, docs_range_flow_optical_flow_pmw3901, docs_range_flow_baro_height_reference, docs_range_flow_gps_denied_all_sensors [EXTRACTED 1.00]
- **M8 simulation-speed investigation chain** — docs_migration_errors_m8, docs_migration_errors_pegasus_per_step_python, docs_migration_errors_pegasus_fast, docs_migration_errors_camera_bottleneck_update, docs_performance_camera_render_cost [EXTRACTED 1.00]
- **Camera render cost levers (chase cam rate, ZED fps, ZED off)** — docs_performance_chase_cam_rate, docs_performance_zed_twin_cost, docs_performance_zed_15fps_rejected, docs_performance_multi_tick_rendering [EXTRACTED 1.00]
- **PX4 bridge via lean MAVROS plugins in one compose service** — claude_px4_bridge_mavros_adr_001, docker_compose_px4_bridge_service, docker_ros_mavros_lean_plugin_allowlist [EXTRACTED 1.00]
- **PX4 bridge options behind one service** — docs_px4_bridge_px4_bridge_service, docs_px4_bridge_mavros_bridge, docs_px4_bridge_mavsdk_bridge, docs_px4_bridge_xrce_bridge [EXTRACTED 1.00]
- **Selectable PX4 bridge options** — docs_decisions_adr_001_mavros_px4_bridge_selectable_service, docs_decisions_adr_001_mavros_mavros_bridge, docs_decisions_adr_001_mavros_mavsdk, docs_decisions_adr_001_mavros_uxrce_dds [EXTRACTED 1.00]
- **Vehicle PX4 params + EKF2 mode overlays selected per scenario** — docker_sim_px4_readme_px4_param_files, docker_sim_px4_readme_raptor_params, docker_sim_px4_readme_iris_params, docker_sim_px4_readme_ekf2_vio_flow_range_params, docker_sim_sim, docker_sim_configs_single_iris_px4_params_list [EXTRACTED 1.00]
- **Raptor CAD to scenario vehicle build flow** — docker_sim_assets_readme_step_to_usd, docker_sim_tools_build_raptor, docker_sim_assets_vehicles_raptor_raptor, docker_sim_assets_readme_raptor_usd, docker_sim_assets_readme_raptor_summary_json, docker_sim_sim [EXTRACTED 1.00]
- **Three PX4 calibrations validated by ablation** — docs_vio_cfg_no_yaw_limit, docs_vio_cfg_no_eva_fix, docs_vio_cfg_px4_defaults, docs_vio_campaign_mc_yawrate_max_60, docs_vio_campaign_ekf2_eva_noise_001, docs_vio_campaign_ekf2_of_qmin_gnd_1 [EXTRACTED 1.00]
- **VIO campaign execution pipeline** — docs_vio_tool_vio_campaign, docs_vio_tool_vio_bench, docs_vio_tool_vio_eval, docs_vio_campaign_tool_vio_report, docs_vio_campaign_tool_vio_export [EXTRACTED 1.00]
- **ZED stack services sharing one image and zed.yaml** — docker_compose_zed_service, docker_compose_zed_bridge_service, docker_compose_zed_video_service [EXTRACTED 1.00]
- **Why ZED images need a larger UDP receive buffer** — docs_setup_udp_fragment_loss, docs_setup_rmem_max_sysctl, docs_setup_cyclonedds_xml, docs_debugging_dds_checks [INFERRED 0.85]
- **ZED SDK odometry to PX4 EKF2 in the sim** — docker_zed_zed_positional_tracking, docker_zed_zed_restamp_latency, docker_sim_configs_single_iris_vio_zed_bridge_odometry, docker_sim_configs_single_iris_vio_ekf2_vision_overlay [INFERRED 0.85]
- **ZED odom to PX4 EV path across contract, hardware and VIO docs** — docs_interface_contract_zed_odom, docs_hardware_vio_relay_bridge [INFERRED 0.85]

## Communities (187 total, 91 thin omitted)

### Community 0 - "VIO & Range/Flow Evaluation"
Cohesion: 0.06
Nodes (59): best_lag(), binned(), eval_ekf(), eval_flow(), err_at(), expected(), eval_ros(), err_at() (+51 more)

### Community 1 - "ZED Stack Config & Tests"
Cohesion: 0.05
Nodes (37): copy, difflib, ConfigError, deep_merge(), _flatten_params(), load(), docker/zed/zed.yaml -> zed_wrapper parameters + the list of services to start.…, {section: {key: default}} from the wrapper's own YAML files (the model file… (+29 more)

### Community 2 - "ZED Bridge Common & Health"
Cohesion: 0.06
Nodes (12): Module, Rate, Messages per second over a sliding window, and how long ago the last one came…, Base of a bridge module. `status()` is polled once a second by the health…, Health, ObstacleDistance, Image, MAVROS defaults the obstacle plugin to GLOBAL; ours is a body-frame (FRD) scan. (+4 more)

### Community 3 - "ZED Bench Harness"
Cohesion: 0.08
Nodes (33): rosgraph_msgs_msg, rosidl_runtime_py_utilities, std_srvs_srv, Bench, build_phases(), toggle(), run(), chk_cloud() (+25 more)

### Community 4 - "Shell Common & ZED Ext Build"
Cohesion: 0.07
Nodes (32): build_isaac_ext.sh script, stamp(), _BISG_ENV0, BISG_SRC, conf_default(), container_running(), die(), fail() (+24 more)

### Community 5 - "VIO Report & Bag Tools"
Cohesion: 0.09
Nodes (37): datetime, glob, re, command(), load(), main(), Read / toggle docker/ros/bag.yaml (rosbag2 recording, ./bisg bag). ros_bag.py…, The YAML folds the long patterns over several lines: drop the whitespace. (+29 more)

### Community 6 - "VIO Calibration & Campaign Docs"
Cohesion: 0.06
Nodes (39): ZED VIO accuracy and calibration, VIO campaign doc, Accuracy per config, Warehouse 6 flights each (calibrated 0.070 +- 0.016 m), ./bisg vio check (~7 min), Campaigns run so far (12 campaigns, 2026-10-15 to 2026-10-18), Campaign conclusions (pipeline calibrated; accuracy set by SDK events), Dominant event attribution (pose jump, gap slip, gap yaw slip, rotation yaw slip), EKF2_OF_QMIN_GND 1 (+31 more)

### Community 7 - "VIO Campaign Runner"
Cohesion: 0.13
Nodes (34): base64, frame(), need(), What does a Foxglove client see on the foxglove_bridge, and does the data flow?…, shutil, socket, struct, boot() (+26 more)

### Community 8 - "MAVROS Sim-Time & Test Helpers"
Cohesion: 0.08
Nodes (22): csv, main(), Switch every MAVROS plugin node to use_sim_time:=true (sim stack only,…, M2 — ZED depth image -> PX4's 72-sector obstacle map (MAVROS obstacle/send ->…, Depth image -> 72 x 5 deg obstacle sectors. numpy only, so it is unit-testable…, numpy, rcl_interfaces_msg, rcl_interfaces_srv (+14 more)

### Community 9 - "Flight Test Benches"
Cohesion: 0.09
Nodes (9): Bench, main(), Fly `dist` m at (vx, vy) ENU m/s (sim-time duration), then hold where it…, main(), Abort, Flight, main(), Exception (+1 more)

### Community 10 - "VIO Eval Unit Tests"
Cohesion: 0.10
Nodes (14): flight(), A yaw error rotates positions about the takeoff point; the old whole-flight fit…, w, x, y, z of R = Rz(psi) Ry(pitch) (FRD body -> NED)., A 60 s log as vio_eval reads it. Truth: rest 5 s, climb to 1 m, figure flown…, Synthetic, yaw_quat(), campaign(), dump() (+6 more)

### Community 11 - "Sim Launcher App"
Cohesion: 0.09
Nodes (23): App, apply_paths(), apply_px4_params(), main(), phase(), Boot-phase timing: `[launch] INFO boot +NNs: <what>` (where the cold/warm boot…, bisg_isaac Pegasus launcher — YAML-driven Isaac Sim standalone app. /isaac-…, Multiply the intensity of every UsdLux light in the world asset by `scale`… (+15 more)

### Community 12 - "Offboard & Pool Probe Collect"
Cohesion: 0.11
Nodes (19): dataclasses, OffboardController — fly drone N through MAVROS from Python (docs/interface-…, Follow camera for the GUI viewport, in the spirit of Gazebo's "follow" mode:…, Shared pieces of the bridge modules (rclpy only where a function needs a node)., geometry_msgs_msg, math, mavros_msgs_srv, rclpy (+11 more)

### Community 13 - "launch.sh Commands"
Cohesion: 0.19
Nodes (23): bag_close(), cmd_all(), cmd_build(), cmd_config(), cmd_down(), cmd_logs(), cmd_mavros(), cmd_restart() (+15 more)

### Community 14 - "Range/Flow Sensor Backend"
Cohesion: 0.11
Nodes (8): Backend, attach(), ned_to_latlon(), RangeFlowBackend, Range from `mount` (body FLU) straight down the body Z axis to the first…, Return a RangeFlowBackend for a scenario vehicle, or None when neither sensor…, Inverse of PX4's azimuthal-equidistant MapProjection, so PX4's ground-truth…, cfg: the vehicle's `sensors:` block (`tof:` and/or `optical_flow:`); px4: the…

### Community 15 - "PX4 Params & Foxglove Probe"
Cohesion: 0.15
Nodes (16): argparse, os, pymavlink, encode(), load_params(), main(), Push PX4 EKF2/GPS params over MAVLink (Phase 3 — GPS-denied flight on ZED Mini…, PX4/MAVLink PARAM_SET always carries a float32 on the wire; non-REAL32 types… (+8 more)

### Community 16 - "Offboard Controller"
Cohesion: 0.17
Nodes (5): OffboardController, MAVROS connected and a local position estimate flowing; fixes the mission…, Stream a hover setpoint `alt` m above the origin, switch to OFFBOARD, arm, wait…, Fly to (x, y, z) m from the origin (z None = keep the current setpoint height);…, Result

### Community 17 - "Video Mosaic Rendering"
Cohesion: 0.10
Nodes (15): collections, cv2, blank(), depth_to_bgr(), FlowView, label(), Image functions of the 2x2 QGC video (services.qgc_video, layout: grid). No…, Burn a small caption into the top-left corner (in place). (+7 more)

### Community 18 - "ZED Drone Launch & TF"
Cohesion: 0.13
Nodes (20): drone_tf(), generate_launch_description(), inverse_pose(), params(), zed_wrapper for drone N, with the contract's topic names. Used by BOTH the sim…, The ros__parameters of the compiled params file ({} without one)., {launch arg: "true"|"false"} for the TF switches the params set; absent ones…, (t, q) of the inverse of the pose x y z + intrinsic ZYX roll pitch yaw: t =… (+12 more)

### Community 19 - "PX4 Bridge CLI Tests"
Cohesion: 0.16
Nodes (5): subprocess, bridge(), compose_service(), Px4BridgeCli, ./bisg px4-bridge: one compose service (px4-bridge), PX4_BRIDGE picks what its…

### Community 20 - "Raptor CAD Build Pipeline"
Cohesion: 0.14
Nodes (15): raptor_summary.json (CoM, inertia, mounts), Raw CAD USD (docker/sim/tools/step_to_usd.py) -> Pegasus-ready vehicle USD.…, CAD-FLU point -> body frame (origin at the centre of mass)., rel(), M10 — ZED health -> one status topic + STATUSTEXT in QGroundControl. Publishes…, M1 — ZED positional tracking -> PX4 EKF2 external vision (MAVROS odometry/out).…, json, mavros_msgs_msg (+7 more)

### Community 21 - "ZED SDK in Sim (ADR-007)"
Cohesion: 0.12
Nodes (19): ADR-007 Real ZED SDK in the sim, ZED asset FixedJoint mount, One odometry source per run, Residual sim-vs-hardware ZED gap, Stereolabs zed-isaac-sim extension v5.2.1, ZED_SOURCE emulated|sdk switch, Docker data-root relocation, Emulated ZED rig (removed) (+11 more)

### Community 22 - "Project Plan & ADRs"
Cohesion: 0.16
Nodes (19): Project plan (bisg_isaac digital twin), ADR-002 Docker-first, Isaac Sim in a container, ADR-003 One PX4 version for SITL and Pixracer, ADR-004 CycloneDDS + zenoh bridge, ADR-005 ROS 2 Jazzy in all containers, Docker strategy (three image families, one compose), Isaac Sim 6.0.0, NVIDIA driver 580 branch constraint (+11 more)

### Community 23 - "debug.sh Commands"
Cohesion: 0.26
Nodes (18): cmd_clean_all(), cmd_clean_cache(), cmd_dds(), cmd_echo(), cmd_gpu(), cmd_hz(), cmd_kitlog(), cmd_mavlink() (+10 more)

### Community 24 - "QGC Video Streams"
Cohesion: 0.16
Nodes (6): main(), Image, Node, The tile of one source: re-decoded when a new frame arrived, a 'no signal'…, VideoStream, OpticalFlowRad

### Community 25 - "Configuration Guide"
Cohesion: 0.16
Nodes (18): Configuration guide, Procedure for adding a config key, config/bisg.conf, Endpoint keys (DRONE_ID, FCU_URL, PX4_BRIDGE, ROS_DOMAIN_ID...), Version pins and source links, Config precedence (flag > env > .env > bisg.conf > fallbacks), Settings layering (bisg.conf / zed.yaml / .env / scenario YAML), SIM_VIEW (gui|headless|web|webrtc|both|auto) (+10 more)

### Community 26 - "Known Bugs & GPS-Denied Default"
Cohesion: 0.18
Nodes (17): 320x180 ZED low-res variant (fits default rmem_max), GPS-denied default since 2026-10-15, restamp + restamp_latency_ms, Known bugs (bugs.md), B1 No usable failsafe action while GPS-denied, B13 No automated check camera view unobstructed, B17 SDK odometry into PX4 accuracy beyond bound, B18 SDK connects to sim stream once per run (+9 more)

### Community 27 - "Raptor Vehicle Asset"
Cohesion: 0.14
Nodes (16): docker/sim/assets README, Onshape-to-FLU frame convention, Raptor USD build pipeline (STEP -> USD -> raptor.usd), Raptor 5in cinewhoop vehicle (Pegasus vehicle), docker/sim/tools/step_to_usd.py (CAD Converter), raptor.yaml (vehicle build inputs + scenario vehicle), Chase camera (third-person image), Duct collision cylinders (+8 more)

### Community 28 - "Scenario Configs & Perf Knobs"
Cohesion: 0.14
Nodes (15): Gazebo-style follow camera, Iris thrust curve/airframe placeholder for raptor, Performance knobs (perf block), 120 Hz physics (= PX4 IMU rate), /clock sim time publication, single_iris scenario, Iris quadrotor scenario vehicle, 120 Hz physics (6 steps per 20 Hz render) (+7 more)

### Community 29 - "CAD to USD & Pool Probe"
Cohesion: 0.13
Nodes (12): CAD (STEP) -> raw USD with the Isaac CAD Converter (HOOPS), plus a part…, intrinsics(), Probe: can the real ZED SDK give depth for TELEPORTED views (Kinetix view…, The extension authors the ZED_M optics on the camera prims once it streams:…, isaacsim, isaacsim_core_utils_extensions, omni_converter_hoops, omni_replicator_core (+4 more)

### Community 30 - "Open Risks & Debug Notes"
Cohesion: 0.17
Nodes (16): ZED topics stop mid-run: R9 time-source throw and terminate_bt stack, Architecture decision records (docs/decisions/), The ROS 2 graph doc, Load and redundancy (~200 MB/s camera data), R1 two publishers on zed imu/data, R4 bridge subscribes to depth twice, R9 ZED wrapper time-source crash, /video_stream node (+8 more)

### Community 31 - "ZED Stack (ADR-008)"
Cohesion: 0.17
Nodes (16): ADR-008 One YAML, one image, small services, Shared compose.yaml profiles zed and drone, docker/zed/zed.yaml single config, Bridge modules not yet built, zed_stack compile/validate, imu_fusion false in sim (frame-rate IMU), The ZED Mini stack, Adding a bridge module recipe (+8 more)

### Community 32 - "MAVLink Offboard Tests"
Cohesion: 0.21
Nodes (7): main(), Offboard, Descend at DESCENT_M_S until PX4 detects ground contact, then disarm; True once…, m: a connected mavutil link with target_system/component set; on_msg(msg) sees…, Read messages for `seconds` (wall), streaming the current setpoint at 20 Hz., Arm in OFFBOARD and climb to `alt` m above the start position; True once…, main()

### Community 33 - "Follow Cam & RTF HUD"
Cohesion: 0.13
Nodes (10): carb, PMW3901 optical flow sensor twin, Lightware LW20 down-facing ToF, Per-step speed-ups for Pegasus on Isaac Sim 6.0 (docs/performance.md,…, Downward ToF rangefinder + optical-flow sensor for a vehicle, fed straight to…, install(), Real-time factor (sim seconds per wall second) as one more line of Kit's own…, logging (+2 more)

### Community 34 - "Sim Regression Skill & Gate"
Cohesion: 0.18
Nodes (14): Migration / pin-change gate, Test scenario YAML format, sim-regression skill, Regression triage rules, Docker-first runtime components (ADR-002), GPS-denied sim default (baro+LW20+ZED VIO+flow), Workstation A and B host facts, Isaac Sim 6.0 + Pegasus + PX4 v1.17 stack (+6 more)

### Community 35 - "headless_fast Scenario"
Cohesion: 0.19
Nodes (14): Scenario eight_iris_nozed, Scenario four_iris_nozed, headless_fast.yaml scenario, app.render: false, world preset Default Environment, Iris vehicle id 0 (ros2 disabled), perf.skip_material_loading, app.stream: off (+6 more)

### Community 36 - "ZED SDK Rig Config"
Cohesion: 0.19
Nodes (12): ext_folder(), Stdlib-only half of the ZED SDK mode (zed_sdk_rig.py): decisions that launch.py…, Folder holding the built extension (docker/zed/build_isaac_ext.sh). Checked…, stream_port(), attach_zed_sdk(), ZED Mini twin streamed into the REAL ZED SDK (scenario `sensors.zed.enabled`,…, Author one translate + one orient op (wxyz) so the body starts exactly where…, Mount the ZED Mini twin on `vehicle` (Pegasus Multirotor) and start streaming… (+4 more)

### Community 37 - "ZED Odometry Bridge & Bench Config"
Cohesion: 0.21
Nodes (14): .bench.yaml (derived ZED bench config), Bench depth mode NEURAL_LIGHT, HD720 (vs NEURAL_PLUS HD1080 in zed.yaml), Derived bench config (python3 -m zed_stack derive; do not edit), zed.yaml (ZED stack config), ./bisg zed plan|set|up, Depth sensing (NEURAL_PLUS), imu_fusion off in sim (no 400 Hz IMU stream), Positional tracking (VIO) (+6 more)

### Community 38 - "Bridge Context & Node"
Cohesion: 0.20
Nodes (10): Context, What every module needs to know: namespaces and a way to reach the others., main(), python3 -m zed_stack.bridge — the px4_bridge service (compose `zed-bridge`).…, ROS 2 image topics -> RTP/H.264 over UDP, for QGroundControl's "UDP h.264 Video…, gi, gi_repository, rclpy_node (+2 more)

### Community 39 - "Roadmap Phases"
Cohesion: 0.23
Nodes (14): Roadmap, Phase 1 Dockerized single-drone sim, Phase 2 ROS 2 + MAVROS control, Phase 3 Sensors, ZED Mini contract, VIO, Phase 4 Digital-twin assets, Phase 5 Hardware single drone, Phase 6 Swarm in sim, Phase 7 Hardware swarm (+6 more)

### Community 40 - "Tailscale Script"
Cohesion: 0.36
Nodes (13): backend(), connected(), host_cmd(), host_field(), host_json(), host_mode(), login(), preflight() (+5 more)

### Community 41 - "ZED SDK Check"
Cohesion: 0.19
Nodes (8): main(), path_length(), Probe, Node, rate(), ZED SDK contract + health check — the same script for the sim and the real…, RMSE (m) of the SDK odometry against ground truth after the only alignment that…, trajectory_rmse()

### Community 42 - "Compose & Shader Cache"
Cohesion: 0.23
Nodes (12): Isaac 6.0 kit shader cache volume, scripts/gen_compose.py per-drone compose generation, swarm-spawn skill, VRAM/FPS budget limits, ZED SDK per drone (port 30000+2*id), docker/compose.yaml (single compose for workstation and Jetson), Isaac cache named volumes, Compose profiles (sim, sim-headless, ros, tools, px4-bridge, zed, drone, tailscale) (+4 more)

### Community 43 - "MAVROS Ops Skill"
Cohesion: 0.17
Nodes (11): VIO source: wrapper odom -> mavros/odometry/out, mavros-ops skill, MAVROS frames (ENU map, odom/base_link), GPS-denied EV yaw-align limitation (fly and land in OFFBOARD), MAVROS launch wrapper (bisg_bringup mavros.launch.py), MAVROS 2.15.1 plugin nodes ignore params files, OFFBOARD state machine (offboard_controller), Sim time and PX4 timesync (use_sim_time) (+3 more)

### Community 44 - "Remote Access Tooling"
Cohesion: 0.18
Nodes (12): Tailscale remote access (ADR-009), lichtblick service, tailscale service, Remote bandwidth: use compressed image topics, scripts/foxglove_probe.py debug probe, Foxglove/Lichtblick web UI and layouts, Lichtblick 1.28/1.29 quirks workarounds, raptor.json layout (generated by make_layout.py) (+4 more)

### Community 45 - "ZED Crash Backtrace Hook (R9)"
Cohesion: 0.18
Nodes (10): cstdio, cstdlib, cxxabi, handler(), print_backtrace(), exception, execinfo, pthread (+2 more)

### Community 46 - "Chase Camera"
Cohesion: 0.20
Nodes (9): ChaseCam, Chase camera of a vehicle as a ROS 2 image (scenario `sensors.chase_cam`,…, `dt`: sim seconds between two update() calls (the rendering step), for the…, Move the camera to this frame's chase pose (call once per rendered frame)., _wrap(), isaacsim_core_experimental_utils_app, omni_graph_core, omni_usd (+1 more)

### Community 47 - "Follow Camera"
Cohesion: 0.35
Nodes (3): FollowCam, Put the camera at `offset` in the drone's body frame, looking at it., _wrap()

### Community 48 - "Flow-Only Scenario"
Cohesion: 0.31
Nodes (11): single_iris_flow scenario, ekf2_flow_range.params overlay, tests/flow_hold.py, GPS-denied on ToF + optical flow (no ZED), docker/sim/px4 README (PX4 parameter files), ekf2_flow_range.params, ekf2_vio_flow_range.params (real drone GPS-denied mode), iris.params (+3 more)

### Community 49 - "Migration Errors & Known Bugs"
Cohesion: 0.18
Nodes (11): Isaac Sim 6.0 migration errors, bugs.md long-lived product bugs (B4, B9, B18), M1 PX4 v1.16.0 SITL build IndexError, M12 Deprecated APIs still in use, M19 Environment loading semantics changed, archive/docs/migration-report.md (context and results), Fetch NuttX tags after shallow-submodule clone (PX4 v1.16 build), isaacsim.ros2.bridge is a thin shim over ros2.core/nodes/ui/examples (+3 more)

### Community 50 - "Performance Docs (Hover & physics_dt)"
Cohesion: 0.20
Nodes (11): M20 performance.md is 5.1-era, Performance and profiling, Hover stability vs physics_dt (60 Hz wobbles, 120 Hz stable), Measuring: debug perf, debug gpu, boot time, kitlog, Tracy, NVIDIA Simulation Performance Optimization Handbook (upstream reference), perf: block knobs (limit_cpu_threads, skip_material_loading, min_frame_rate, physx_threads...), 120 Hz physics rationale, physics_dt also sets PX4 sensor and MAVLink rate (+3 more)

### Community 51 - "Runbook & GPS-Denied Estimation"
Cohesion: 0.18
Nodes (11): GPS-denied state estimation (VIO -> EKF2), Sim-to-real parity rules, Vehicle interface contract, TF tree measured vs contract (R2/R3), Runbook simulation stack, ./bisg CLI cheat sheet, Common failures, Launcher must be PID 1 (do not use python.sh) (+3 more)

### Community 52 - "README & Project Overview"
Cohesion: 0.20
Nodes (11): README bisg_isaac, ./bisg operator CLI, Same containers for sim drone and real drone (Docker everywhere), Hardware target: Jetson Orin NX (JetPack 7.2) + Pixracer + ZED Mini, Kinetix photogrammetry project flies capture tours on the twin, Quick start (./bisg setup/up/smoke/zed), Repo layout, Settings: config/bisg.conf + docker/.env (this machine) (+3 more)

### Community 53 - "VIO Scenarios"
Cohesion: 0.29
Nodes (10): single_iris_vio scenario, depth_box test cuboid (1 m cube), ekf2_vision.params overlay, GPS-denied VIO scenario (EKF2 external vision), single_iris_vio_lowres scenario, ZED odometry -> zed-bridge -> mavros/odometry/out, two_iris_nozed.yaml scenario, two_iris_vio_lowres scenario (+2 more)

### Community 54 - "Web Viewport Streaming"
Cohesion: 0.22
Nodes (5): Serve the viewport as a still image over one TCP port. The WebRTC client needs…, Issue one viewport capture if the interval has elapsed. Never raises., WebView, do_GET(), _send()

### Community 55 - "PX4 Bridge Choice"
Cohesion: 0.33
Nodes (10): ADR-001 MAVROS as PX4-ROS 2 bridge, MAVROS 2.x PX4-ROS 2 bridge, MAVROS lean plugin list (mavros_lean.yaml), MAVSDK 4.x, One selectable px4-bridge service (PX4_BRIDGE), PX4-link study (archive/px4-link-study), uXRCE-DDS (rejected alternative), bisg/zed single image (+2 more)

### Community 56 - "Docker-First & DDS ADRs"
Cohesion: 0.29
Nodes (10): ADR-002 Docker-first including Isaac Sim, bisg/sim, bisg/ros, bisg/zed images, network_mode host everywhere, ADR-004 CycloneDDS everywhere, zenoh bridge over WiFi, rmw_cyclonedds_cpp with committed cyclonedds.xml, zenoh-bridge-ros2dds with allow-list, ADR-005 ROS 2 Jazzy (Ubuntu 24.04) in all containers, Isaac Sim bundled Jazzy ROS 2 bridge (exts/isaacsim.ros2.core/jazzy) (+2 more)

### Community 57 - "Build Pins & PX4 Version"
Cohesion: 0.20
Nodes (10): ADR-003 One PX4 tag for SITL and Pixracer, MAVROS 2.15.1, Pegasus PR #144 head fcb99c0, px4_fmu-v4_default Pixracer firmware (95.3% flash), PX4_TAG Dockerfile arg, Re-validation on Isaac Sim 6.0 (2026-10-02), Selection procedure (Phase 1), PX4 v1.16.0 fallback (+2 more)

### Community 58 - "MAVROS over XRCE (ADR-001)"
Cohesion: 0.36
Nodes (10): ADR-001 MAVROS instead of uXRCE-DDS, MAVROS 2.15.1, Multi-vehicle model (ports, IDs, namespaces), The PX4 bridge doc, Drone ID = namespace, PX4_BRIDGE=mavros (default), PX4_BRIDGE=mavsdk, Components that need MAVROS (vio_mock, zed-bridge, vio_flight) (+2 more)

### Community 59 - "ToF & Flow Benchmark"
Cohesion: 0.33
Nodes (10): Downward ToF rangefinder + optical flow doc, Range/flow accuracy benchmark (2026-10-10), Baro as EKF2 height reference, EKF2_MIN_RNG fix, GPS-denied on all sensors (ZED + LW20 + PMW3901 + baro), PMW3901 optical flow twin, range_flow.py Pegasus Backend, LW20/C ToF rangefinder twin (+2 more)

### Community 60 - "bag.sh Recording"
Cohesion: 0.49
Nodes (9): current(), newest(), resolve(), ros_up(), running(), bag.sh script, start(), status() (+1 more)

### Community 61 - "info.sh Addresses"
Cohesion: 0.33
Nodes (6): each(), listening(), row(), info.sh script, sub(), ts_json()

### Community 62 - "Jetson Deploy Skill"
Cohesion: 0.25
Nodes (9): jetson-deploy skill, Cyclone DDS overlay for ZED L4T image, Pixracer flash and params, Preflight checklist (props on), Port to the Jetson, drone-zed service, ZED SDK image README, docker/zed/build.sh (desktop / jetson) (+1 more)

### Community 63 - "PX4 SITL Skill"
Cohesion: 0.25
Nodes (9): px4-sitl skill, Common arming/offboard rejections, PX4 instance/port/sys-id math, Lockstep off in SITL, sim-launch skill, web and webrtc remote views, PX4 bridge decision: MAVROS (ADR-001), px4-bridge service (+1 more)

### Community 64 - "PX4 Bridge Entrypoint"
Cohesion: 0.31
Nodes (7): mavros(), mavsdk(), entrypoint.sh script, xrce(), ext_setup_bash, ext_setup_zsh, host_ros_env.sh script

### Community 65 - "Scenario Variants"
Cohesion: 0.25
Nodes (9): raptor.usd, sim.yaml (scenario locator), launch.py expand_locator, Scenario locator (sim.yaml), Spawn pose override, Warehouse lighting tuning (light_scale 0.5, ambient 2), Warehouse world (Isaac 6.0 Simple_Warehouse), docker/sim/worlds README (+1 more)

### Community 66 - "Vehicle Spawn & ZED Features"
Cohesion: 0.25
Nodes (6): resolve_vehicle_usd(), Features, load_features(), Read the ZED switches from docker/zed/zed.yaml, the file the real zed_wrapper…, publish_imu(), Physically-simulated IMU on `{body_path}/zed_imu_link`, published on…

### Community 67 - "Bag Profiles & GPU Troubleshooting"
Cohesion: 0.22
Nodes (9): ./bisg bag enable/start/stop/list/info/play, Bag profiles: flight, vision, all (docker/ros/bag.yaml), GPU container refuses to start: NVML driver/library version mismatch, PX4 never Ready for takeoff (port 4560, unknown model), Recording a run (rosbag2/MCAP, ./bisg bag), Sim slower than real time: ./bisg debug perf, rtf < 1.0, Smoke test / pymavlink shares MAVROS UDP 14540 (MAVROS topics nearly stop), Stop takes 60 s and exits 137 (entrypoint must exec Isaac python) (+1 more)

### Community 68 - "Resets & Debug Quirks"
Cohesion: 0.28
Nodes (9): Resetting (clean-cache, volumes), Compose volume 'already exists but was not created by Docker Compose', M15 debug mavlink needs pymavlink on host, Workstation setup doc, bisg/ros:arm64 image, Jetson Orin NX (JetPack 7.2, L4T r38.4), Jetson steps: save/load arm64 image, build l4t-r38, udev /dev/px4, drone up, Uninstall / reset (clean-cache, clean-all, docker rmi) (+1 more)

### Community 69 - "Camera Render Cost (M8)"
Cohesion: 0.22
Nodes (9): Camera renders dominate sim cost, Chase cam rate_hz 10 Hz default (sensors.chase_cam.rate_hz), py-spy: 82% of main thread in simulation_app.update(), Pegasus ~10%, Multi-tick rendering (omni:sensor:tickRate), View mode (window, WebRTC) costs < 8%, headless+webrtc ~11%, Workstation A (RTX 4500) RTF table, Workstation B measurements (RTF 0.72 headless), ZED 15 fps rejected (depth box -40 mm, VIO abort) (+1 more)

### Community 70 - "Setup & Images"
Cohesion: 0.25
Nodes (9): ./bisg setup command, bisg/sim:6.0.0 image, scripts/check_env.sh preflight (driver, runtime, compose, X11, disk, ports), docker/.env (machine-local), Pull nvcr.io/nvidia/isaac-sim:6.0.0 and ros:jazzy-ros-base, PegasusSimulator submodule (PR #144 head), --third-party fallback clones Pegasus and zed-ros2-wrapper v5.4.1, Setup timing: pull ~3 min, sim build ~4, ros ~2, arm64 ~15 (+1 more)

### Community 71 - "Contract Checker Module"
Cohesion: 0.28
Nodes (8): importlib, pathlib, rclpy_time, main(), parse_contract(), parse_rate(), Phase 3 exit test (docs/roadmap.md): the live ROS graph of drone N against…, Rows of the 'provided by the vehicle' table: dicts topic, type, rate (lo, hi Hz…

### Community 72 - "zed.sh Script"
Cohesion: 0.44
Nodes (8): have_frames(), zed.sh script, start_services(), svc_name(), video_hint(), video_ip(), ZED_SIM_PORT, zexec()

### Community 74 - "VIO Archive Regression Tests"
Cohesion: 0.36
Nodes (3): Archive, archived(), The 2026-10-15 flights (docs/vio.md, archive/vio-2026-10-15/README.md).…

### Community 75 - "ZED Contract Skill"
Cohesion: 0.29
Nodes (8): Contract changes first, then sim, then real, Matching the ZED wrapper (topics, TF, camera_info), zed-contract skill, Rules that bit us (FixedJoint, frame-rate IMU, connect-once B18), ZED SDK run procedure, zed-sdk skill, Interface contract first rule, ZED stack configured only by zed.yaml (ADR-008)

### Community 77 - "Pegasus Fork (ADR-010)"
Cohesion: 0.39
Nodes (7): ADR-010 Pegasus fork, Pegasus fork akashshingha850/PegasusSimulator branch local, Pegasus PR #144 (Isaac Sim 6.0 port), PEGASUS_TAG=local-<sha> pin form, Push to fork before superproject commit, clone(), fetch_sources.sh script

### Community 78 - "Bench Day & Benchmarks"
Cohesion: 0.25
Nodes (8): Bench day Orin NX + Pixracer + ZED Mini, ZED module test + benchmark, 16/16 phases pass (1 warning), zed-bridge container cost (0.31 cores), RAM is the real constraint on Orin NX, Second workstation split GPUs (SIM_GPU=0 ZED_GPU=1), Streaming server crashes wrapper in sim (B19), Porting to the Jetson

### Community 79 - "Collision Prevention Test"
Cohesion: 0.29
Nodes (3): main(), spin(), wait()

### Community 80 - "Raptor Build & Depth Box Test"
Cohesion: 0.32
Nodes (5): load_scenario(), main(), quat_xyzw_to_matrix(), ZED depth check against a known box (scenario `world.objects`, e.g.…, Same `extends:` deep-merge as docker/sim/launcher/launch.py.

### Community 81 - "Pegasus Force Application"
Cohesion: 0.43
Nodes (6): apply(), apply_force(), apply_torque(), handle_propeller_visual(), _prim(), update()

### Community 82 - "Debugging Guide"
Cohesion: 0.33
Nodes (7): Debugging guide, ./bisg status then ./bisg debug report (logs/debug_<ts>.tar.gz), Host ROS 2 (optional, debugging only), Log locations (launcher, Kit log, .ulg, MAVROS, perf heartbeat), PX4 shell without QGC, ROS 2 graph commands (debug topics/hz/echo in the ros container), M5 Sim container shows (unhealthy)

### Community 83 - "DDS & Host Checks"
Cohesion: 0.29
Nodes (7): DDS checks: ./bisg debug dds, ROS_DOMAIN_ID, RMW, rmem_max, docker/cyclonedds.xml, >= 60 GB free on Docker root disk (Isaac 21 GB + sim ~25 GB + ZED ~15 GB), Host prerequisites (driver, Docker, nvidia-container-toolkit), Install nvidia-container-toolkit (apt, nvidia-ctk runtime configure), net.core.rmem_max UDP buffer sysctl, HD720 image (2.7 MB, ~42 UDP fragments) never arrives at default 208 KB buffer

### Community 84 - "Isaac 6.0 Migration & Physics Rate"
Cohesion: 0.29
Nodes (7): headless_fast 132-137 steps/s vs 317 on 5.1, isaac-cache-kit volume (/isaac-sim/kit/cache), M6 Shader cache not persisted (190 s boot), M9 app.render false no longer physics-only, First boot ~190 s shader compile into isaac-cache-kit, Isaac 6.0 loop: one simulation_app.update() per rendering_dt, steps/s counts real physics steps, Isaac 6.0 migration table (nozed 0.48, vio 0.33, 2/4/8 drones)

### Community 85 - "Speed Levers Tried"
Cohesion: 0.29
Nodes (7): Async rendering is not a lever, CPU governor powersave but intel_pstate EPP performance, Handbook flags tried: fabricUpdate off, numThreads=0, asyncRendering hang, Render cadence fix (2026-09-13): one frame per rendering_dt/physics_dt steps, RTF HUD in GUI (rtf_hud.py, app.viewport_hud), RTX 2080 Ti measurements (2026-09-13), A second GPU / NVENC is not a lever for one sim

### Community 86 - "Tailscale Access (ADR-009)"
Cohesion: 0.48
Nodes (7): ADR-009 Remote access via Tailscale service, Tailscale v1.102.5, Watching the sim from somewhere else, Cloudflare tunnel cannot carry WebRTC UDP, SIM_VIEW=web (still frames, one TCP port), SIM_VIEW=webrtc (interactive UI), tailscale compose service

### Community 87 - "px4-bridge.sh"
Cohesion: 0.38
Nodes (3): pcompose(), px4-bridge.sh script, stop()

### Community 89 - "Mission Square"
Cohesion: 0.47
Nodes (5): log(), main(), mission_square — Phase 2 exit test (docs/roadmap.md): take off, fly a square,…, use_sim_time_if_clock(), rclpy_utilities

### Community 90 - "Scenario Locator Loader"
Cohesion: 0.33
Nodes (4): expand_locator(), load_scenario(), The locator keys of docker/sim/sim.yaml (what the sim runs) -> the plain…, Read a scenario YAML. `extends: <file>` or a list of files (relative to this…

### Community 91 - "Boot Time Findings"
Cohesion: 0.33
Nodes (6): Online asset-root lookup delays boot (get_assets_root_path), Boot sims one at a time (concurrent Kit boot segfaulted/hung), Upstream IsaacSim issue #504 and Pegasus #111/#79, 8 drones as two sims, one per GPU: rtf 0.67 vs 0.40, One sim is single-thread bound: speed follows CPU not GPU, Workstation B 2x RTX 6000 Ada table (2026-10-06)

### Community 92 - "ROS Bag Profiles"
Cohesion: 0.50
Nodes (5): ros service (bisg-ros), bag profile: all, rosbag2 recording config (bag.yaml), bag profile: flight, bag profile: vision

### Community 93 - "Sim Entrypoint"
Cohesion: 0.50
Nodes (4): isaac_python_exec(), ROS_DISTRO, entrypoint.sh script, SIM_CONFIG

### Community 94 - "EV Fusion Fallbacks"
Cohesion: 0.40
Nodes (5): EKF2_EV_CTRL 15 (or 11 without vel) and EKF2_HGT_REF Vision, ZED velocity-only fusion (EKF2_EV_CTRL 12) robust fallback, config ev_no_position (EKF2_EV_CTRL 12), EKF2_EV_CTRL 13 (pos + vel + yaw from ZED), ZED velocity only (EKF2_EV_CTRL 12) is robust variant

### Community 95 - "M8 Sim Speed Investigation"
Cohesion: 0.50
Nodes (5): M8 update 2026-10-14: bottleneck moved to camera renders, M8 Sim speed fell 1.18x to 0.33x, pegasus_fast.py partial fix (RTF 0.44 to 0.54 GUI, 0.85 headless), Pegasus per-step Python: 6 RigidPrim calls, warp array construction, pegasus_fast.py runtime patch (cached prims, batched force call)

### Community 96 - "check_env.sh Preflight"
Cohesion: 0.70
Nodes (4): die(), pass(), check_env.sh script, wrn()

### Community 97 - "drone.sh"
Cohesion: 0.50
Nodes (3): drone.sh script, ZED_STACK_SIM, zexec()

### Community 98 - "Subprocess Helpers"
Cohesion: 0.67
Nodes (3): main(), pump(), wait()

## Knowledge Gaps
- **252 isolated node(s):** `ROS_DISTRO`, `SIM_CONFIG`, `ZED_STACK_SIM`, `ROS_DOMAIN_ID`, `ros_env.sh script` (+247 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 622 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **91 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Doc reading order` connect `Open Risks & Debug Notes` to `Resets & Debug Quirks`, `VIO Calibration & Campaign Docs`, `Roadmap Phases`, `Performance Docs (Hover & physics_dt)`, `Debugging Guide`, `README & Project Overview`, `Runbook & GPS-Denied Estimation`, `Project Plan & ADRs`, `ZED SDK in Sim (ADR-007)`, `MAVROS over XRCE (ADR-001)`, `Raptor Vehicle Asset`, `Scenario Configs & Perf Knobs`, `ZED Stack (ADR-008)`?**
  _High betweenness centrality (0.160) - this node is a cross-community bridge._
- **Why does `VIO campaign doc` connect `VIO Calibration & Campaign Docs` to `Offboard & Pool Probe Collect`, `Camera Render Cost (M8)`, `Open Risks & Debug Notes`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Why does `single_iris scenario` connect `Scenario Configs & Perf Knobs` to `Scenario Variants`, `headless_fast Scenario`, `ZED SDK Rig Config`, `Sim Launcher App`, `Chase Camera`, `Flow-Only Scenario`, `Performance Docs (Hover & physics_dt)`, `VIO Scenarios`, `Configuration Guide`, `Known Bugs & GPS-Denied Default`, `Raptor Vehicle Asset`?**
  _High betweenness centrality (0.099) - this node is a cross-community bridge._
- **What connects `ROS_DISTRO`, `SIM_CONFIG`, `ZED_STACK_SIM` to the rest of the system?**
  _252 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `VIO & Range/Flow Evaluation` be split into smaller, more focused modules?**
  _Cohesion score 0.06105834464043419 - nodes in this community are weakly interconnected._
- **Should `ZED Stack Config & Tests` be split into smaller, more focused modules?**
  _Cohesion score 0.05174825174825175 - nodes in this community are weakly interconnected._
- **Should `ZED Bridge Common & Health` be split into smaller, more focused modules?**
  _Cohesion score 0.05920444033302498 - nodes in this community are weakly interconnected._