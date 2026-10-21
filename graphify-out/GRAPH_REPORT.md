# Graph Report - bisg_isaac  (2026-10-20)

## Corpus Check
- 156 files · ~191,417 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 28 file(s) not represented in the graph (top: (none) 11, .params 5, .xml 2)

## Summary
- 1661 nodes · 2793 edges · 189 communities (96 shown, 93 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 156 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Range/Flow Evaluation
- Config Loader & ZED YAML
- ZED Benchmark Harness
- Shell Common & Build Scripts
- ROS Bag Recording
- ZED Bridge Health Monitoring
- VIO Accuracy Campaigns
- VIO Eval Synthetic Tests
- Raptor Asset & Obstacle Sectors
- Flight Bench Test Harness
- Sim Launcher
- VIO Campaign Runner
- PMW3901/LW20 Range-Flow Backend
- bisg CLI Launch Commands
- Foxglove Probe & PX4 Params
- Offboard Controller (ROS)
- Sim Scenario & Physics Config
- ZED Bridge Modules
- Flow/Depth Mosaic Viewer
- Offboard Controller Tests
- ZED Drone Launch & TF
- Project Plan & ADRs
- ZED Bench Config & Image
- ADR-008 ZED Stack
- Debug Commands
- QGC Video Stream
- Tailscale Script
- PX4 Bridge CLI Tests
- Foxglove Layouts
- Raptor USD Build Pipeline
- STEP-to-USD & ZED Pool Probe
- ZED Bridge Core
- Roadmap & Phases
- ADR-007 Real ZED SDK in Sim
- Raw MAVLink Offboard Tests
- Remote Access (Tailscale ADR-009)
- TODO Live List
- Config & Compose Services
- Known Bugs
- ZED SDK Rig & Extension
- Cluster 40
- Cluster 41
- Cluster 42
- Cluster 43
- Cluster 44
- Cluster 45
- Cluster 46
- Cluster 47
- Cluster 48
- Cluster 49
- Cluster 50
- Cluster 51
- Cluster 52
- Cluster 53
- Cluster 54
- Cluster 55
- Cluster 56
- Cluster 57
- Cluster 58
- Cluster 59
- Cluster 60
- Cluster 61
- Cluster 62
- Cluster 63
- Cluster 64
- Cluster 65
- Cluster 66
- Cluster 67
- Cluster 68
- Cluster 69
- Cluster 70
- Cluster 71
- Cluster 72
- Cluster 73
- Cluster 74
- Cluster 75
- Cluster 76
- Cluster 77
- Cluster 78
- Cluster 79
- Cluster 80
- Cluster 81
- Cluster 82
- Cluster 83
- Cluster 84
- Cluster 85
- Cluster 86
- Cluster 87
- Cluster 88
- Cluster 89
- Cluster 90
- Cluster 91
- Cluster 92
- Cluster 93
- Cluster 94
- Cluster 95
- Cluster 96
- Cluster 97
- Cluster 98
- Cluster 99
- Cluster 100
- Cluster 101
- Cluster 102
- Cluster 103
- Cluster 104
- Cluster 105
- Cluster 106
- Cluster 107
- Cluster 108
- Cluster 109
- Cluster 110
- Cluster 111
- Cluster 112
- Cluster 113
- Cluster 114
- Cluster 115
- Cluster 116
- Cluster 117
- Cluster 118
- Cluster 119
- Cluster 120
- Cluster 121
- Cluster 122
- Cluster 123
- Cluster 124
- Cluster 126
- Cluster 127
- Cluster 128
- Cluster 129
- Cluster 130
- Cluster 131
- Cluster 132
- Cluster 133
- Cluster 134
- Cluster 135
- Cluster 136
- Cluster 137
- Cluster 138
- Cluster 139
- Cluster 140
- Cluster 141
- Cluster 142
- Cluster 143
- Cluster 144
- Cluster 145
- Cluster 146
- Cluster 147
- Cluster 148
- Cluster 149
- Cluster 150
- Cluster 151
- Cluster 152
- Cluster 153
- Cluster 154
- Cluster 155
- Cluster 156
- Cluster 157
- Cluster 158
- Cluster 159
- Cluster 160
- Cluster 161
- Cluster 162
- Cluster 163
- Cluster 164
- Cluster 165
- Cluster 166
- Cluster 167
- Cluster 168
- Cluster 169
- Cluster 170
- Cluster 171
- Cluster 172
- Cluster 173
- Cluster 174
- Cluster 175
- Cluster 176
- Cluster 177
- Cluster 178
- Cluster 179
- Cluster 180
- Cluster 181
- Cluster 182
- Cluster 183
- Cluster 184
- Cluster 185
- Cluster 186
- Cluster 187
- Cluster 188

## God Nodes (most connected - your core abstractions)
1. `Known bugs (bugs.md)` - 23 edges
2. `zed.yaml (ZED stack config)` - 21 edges
3. `single_iris scenario` - 20 edges
4. `OffboardController` - 18 edges
5. `RangeFlowBackend` - 18 edges
6. `Doc reading order` - 18 edges
7. `launch.sh script` - 17 edges
8. `analyse()` - 17 edges
9. `Flight` - 17 edges
10. `Rate` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Foxglove over VS Code tunnel / tailnet` --semantically_similar_to--> `VS Code tunnel / SSH port forward for web view`  [INFERRED] [semantically similar]
  docker/ros/foxglove/README.md → docs/remote-access.md
- `write()` --indirect_call--> `f()`  [INFERRED]
  docker/ros/foxglove/make_layout.py → tests/zed_bench.py
- `Foxglove stream bandwidth (use /compressed remotely)` --conceptually_related_to--> `ADR-009 Remote access: Tailscale node as compose service`  [INFERRED]
  docker/ros/foxglove/README.md → docs/decisions/ADR-009-remote-access-tailscale.md
- `load_scenario()` --indirect_call--> `f()`  [INFERRED]
  docker/sim/launcher/launch.py → tests/zed_bench.py
- `params()` --indirect_call--> `f()`  [INFERRED]
  docker/zed/zed_drone.launch.py → tests/zed_bench.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Raptor CAD to scenario vehicle build flow** — docker_sim_assets_readme_step_to_usd, docker_sim_tools_build_raptor, docker_sim_assets_vehicles_raptor_raptor, docker_sim_assets_readme_raptor_usd, docker_sim_assets_readme_raptor_summary_json, docker_sim_sim [EXTRACTED 1.00]
- **Vehicle PX4 params + EKF2 mode overlays selected per scenario** — docker_sim_px4_readme_px4_param_files, docker_sim_px4_readme_raptor_params, docker_sim_px4_readme_iris_params, docker_sim_px4_readme_ekf2_vio_flow_range_params, docker_sim_sim, docker_sim_configs_single_iris_px4_params_list [EXTRACTED 1.00]
- **ZED SDK odometry to PX4 EKF2 in the sim** — docker_zed_zed_positional_tracking, docker_zed_zed_restamp_latency, docker_sim_configs_single_iris_vio_zed_bridge_odometry, docker_sim_configs_single_iris_vio_ekf2_vision_overlay [INFERRED 0.85]
- **Selectable PX4 bridge options** — docs_decisions_adr_001_mavros_px4_bridge_selectable_service, docs_decisions_adr_001_mavros_mavros_bridge, docs_decisions_adr_001_mavros_mavsdk, docs_decisions_adr_001_mavros_uxrce_dds [EXTRACTED 1.00]
- **ZED stack: one YAML, one image, three services** — docs_zed_stack_zed_yaml, docs_decisions_adr_008_zed_stack_bisg_zed_image, docs_decisions_adr_008_zed_stack_zed_bridge_service, docs_decisions_adr_008_zed_stack_zed_video_service, docs_decisions_adr_008_zed_stack_zed_stack_compiler [EXTRACTED 0.95]
- **ZED odom to PX4 EV path across contract, hardware and VIO docs** — docs_interface_contract_zed_odom, docs_hardware_vio_relay_bridge [INFERRED 0.85]
- **M8 simulation-speed investigation chain** — docs_migration_errors_m8, docs_migration_errors_pegasus_per_step_python, docs_migration_errors_pegasus_fast, docs_migration_errors_camera_bottleneck_update, docs_performance_camera_render_cost [EXTRACTED 1.00]
- **Camera render cost levers (chase cam rate, ZED fps, ZED off)** — docs_performance_chase_cam_rate, docs_performance_zed_twin_cost, docs_performance_zed_15fps_rejected, docs_performance_multi_tick_rendering [EXTRACTED 1.00]
- **PX4 bridge options behind one service** — docs_px4_bridge_px4_bridge_service, docs_px4_bridge_mavros_bridge, docs_px4_bridge_mavsdk_bridge, docs_px4_bridge_xrce_bridge [EXTRACTED 1.00]
- **GPS-denied EKF2 inputs: ZED VIO, LW20, PMW3901, baro** — docs_range_flow_tof_lw20, docs_range_flow_optical_flow_pmw3901, docs_range_flow_baro_height_reference, docs_range_flow_gps_denied_all_sensors [EXTRACTED 1.00]
- **Why ZED images need a larger UDP receive buffer** — docs_setup_udp_fragment_loss, docs_setup_rmem_max_sysctl, docs_setup_cyclonedds_xml, docs_debugging_dds_checks [INFERRED 0.85]
- **Three PX4 calibrations validated by ablation** — docs_vio_cfg_no_yaw_limit, docs_vio_cfg_no_eva_fix, docs_vio_cfg_px4_defaults, docs_vio_campaign_mc_yawrate_max_60, docs_vio_campaign_ekf2_eva_noise_001, docs_vio_campaign_ekf2_of_qmin_gnd_1 [EXTRACTED 1.00]
- **VIO campaign execution pipeline** — docs_vio_tool_vio_campaign, docs_vio_tool_vio_bench, docs_vio_tool_vio_eval, docs_vio_campaign_tool_vio_report, docs_vio_campaign_tool_vio_export [EXTRACTED 1.00]
- **Tailscale remote access stack (ADR, compose service, user docs)** — docs_decisions_adr_009_remote_access_tailscale, docker_compose_tailscale, docs_remote_access, claude_remote_access_tailscale [EXTRACTED 1.00]
- **ZED stack compose services on one image** — docker_compose_zed, docker_compose_zed_bridge, docker_compose_zed_video, docker_compose_drone_zed [EXTRACTED 1.00]
- **Foxglove layout pipeline (generator, layouts, Lichtblick service)** — docker_ros_foxglove_readme_make_layout, docker_ros_foxglove_readme_kinetix_layout, docker_ros_foxglove_readme_raptor_layout, docker_compose_lichtblick [EXTRACTED 1.00]

## Communities (189 total, 93 thin omitted)

### Community 0 - "Range/Flow Evaluation"
Cohesion: 0.06
Nodes (59): best_lag(), binned(), eval_ekf(), eval_flow(), err_at(), expected(), eval_ros(), err_at() (+51 more)

### Community 1 - "Config Loader & ZED YAML"
Cohesion: 0.05
Nodes (37): copy, difflib, ConfigError, deep_merge(), _flatten_params(), load(), docker/zed/zed.yaml -> zed_wrapper parameters + the list of services to start.…, {section: {key: default}} from the wrapper's own YAML files (the model file… (+29 more)

### Community 2 - "ZED Benchmark Harness"
Cohesion: 0.08
Nodes (33): rosgraph_msgs_msg, rosidl_runtime_py_utilities, std_srvs_srv, Bench, build_phases(), toggle(), run(), chk_cloud() (+25 more)

### Community 3 - "Shell Common & Build Scripts"
Cohesion: 0.07
Nodes (33): build_isaac_ext.sh script, stamp(), _BISG_ENV0, BISG_SRC, conf_default(), container_running(), die(), fail() (+25 more)

### Community 4 - "ROS Bag Recording"
Cohesion: 0.09
Nodes (37): datetime, glob, re, command(), load(), main(), Read / toggle docker/ros/bag.yaml (rosbag2 recording, ./bisg bag). ros_bag.py…, The YAML folds the long patterns over several lines: drop the whitespace. (+29 more)

### Community 5 - "ZED Bridge Health Monitoring"
Cohesion: 0.07
Nodes (10): Rate, Messages per second over a sliding window, and how long ago the last one came…, Health, ObstacleDistance, Image, MAVROS defaults the obstacle plugin to GLOBAL; ours is a body-frame (FRD) scan., Odometry2Px4, Depth image (H x W, metres, float32) + pinhole intrinsics -> 72 ranges [m]: inf… (+2 more)

### Community 6 - "VIO Accuracy Campaigns"
Cohesion: 0.06
Nodes (39): ZED VIO accuracy and calibration, VIO campaign doc, Accuracy per config, Warehouse 6 flights each (calibrated 0.070 +- 0.016 m), ./bisg vio check (~7 min), Campaigns run so far (12 campaigns, 2026-10-15 to 2026-10-18), Campaign conclusions (pipeline calibrated; accuracy set by SDK events), Dominant event attribution (pose jump, gap slip, gap yaw slip, rotation yaw slip), EKF2_OF_QMIN_GND 1 (+31 more)

### Community 7 - "VIO Eval Synthetic Tests"
Cohesion: 0.10
Nodes (16): flight(), A yaw error rotates positions about the takeoff point; the old whole-flight fit…, w, x, y, z of R = Rz(psi) Ry(pitch) (FRD body -> NED)., A 60 s log as vio_eval reads it. Truth: rest 5 s, climb to 1 m, figure flown…, Synthetic, yaw_quat(), campaign(), dump() (+8 more)

### Community 8 - "Raptor Asset & Obstacle Sectors"
Cohesion: 0.10
Nodes (24): raptor_summary.json (CoM, inertia, mounts), Raw CAD USD (docker/sim/tools/step_to_usd.py) -> Pegasus-ready vehicle USD.…, CAD-FLU point -> body frame (origin at the centre of mass)., rel(), Depth image -> 72 x 5 deg obstacle sectors. numpy only, so it is unit-testable…, json, numpy, os (+16 more)

### Community 9 - "Flight Bench Test Harness"
Cohesion: 0.09
Nodes (9): Bench, main(), Fly `dist` m at (vx, vy) ENU m/s (sim-time duration), then hold where it…, main(), Abort, Flight, main(), Exception (+1 more)

### Community 10 - "Sim Launcher"
Cohesion: 0.09
Nodes (23): App, apply_paths(), apply_px4_params(), main(), phase(), Boot-phase timing: `[launch] INFO boot +NNs: <what>` (where the cold/warm boot…, bisg_isaac Pegasus launcher — YAML-driven Isaac Sim standalone app. /isaac-…, Multiply the intensity of every UsdLux light in the world asset by `scale`… (+15 more)

### Community 11 - "VIO Campaign Runner"
Cohesion: 0.18
Nodes (28): shutil, boot(), evaluate(), first(), fly_once(), have(), Infra, load_yaml() (+20 more)

### Community 12 - "PMW3901/LW20 Range-Flow Backend"
Cohesion: 0.09
Nodes (12): Backend, PMW3901 optical flow sensor twin, Lightware LW20 down-facing ToF, attach(), ned_to_latlon(), RangeFlowBackend, Downward ToF rangefinder + optical-flow sensor for a vehicle, fed straight to…, Range from `mount` (body FLU) straight down the body Z axis to the first… (+4 more)

### Community 13 - "bisg CLI Launch Commands"
Cohesion: 0.19
Nodes (24): bag_close(), cmd_all(), cmd_build(), cmd_config(), cmd_down(), cmd_logs(), cmd_mavros(), cmd_restart() (+16 more)

### Community 14 - "Foxglove Probe & PX4 Params"
Cohesion: 0.13
Nodes (18): argparse, base64, pymavlink, frame(), need(), What does a Foxglove client see on the foxglove_bridge, and does the data flow?…, encode(), load_params() (+10 more)

### Community 15 - "Offboard Controller (ROS)"
Cohesion: 0.17
Nodes (5): OffboardController, MAVROS connected and a local position estimate flowing; fixes the mission…, Stream a hover setpoint `alt` m above the origin, switch to OFFBOARD, arm, wait…, Fly to (x, y, z) m from the origin (z None = keep the current setpoint height);…, Result

### Community 16 - "Sim Scenario & Physics Config"
Cohesion: 0.11
Nodes (21): Gazebo-style follow camera, Iris thrust curve/airframe placeholder for raptor, Performance knobs (perf block), 120 Hz physics (= PX4 IMU rate), /clock sim time publication, single_iris scenario, Iris quadrotor scenario vehicle, 120 Hz physics (6 steps per 20 Hz render) (+13 more)

### Community 17 - "ZED Bridge Modules"
Cohesion: 0.11
Nodes (14): Module, Base of a bridge module. `status()` is polled once a second by the health…, M10 — ZED health -> one status topic + STATUSTEXT in QGroundControl. Publishes…, M1 — ZED positional tracking -> PX4 EKF2 external vision (MAVROS odometry/out).…, nav_msgs_msg, rclpy_duration, std_msgs_msg, main() (+6 more)

### Community 18 - "Flow/Depth Mosaic Viewer"
Cohesion: 0.10
Nodes (15): collections, cv2, blank(), depth_to_bgr(), FlowView, label(), Image functions of the 2x2 QGC video (services.qgc_video, layout: grid). No…, Burn a small caption into the top-left corner (in place). (+7 more)

### Community 19 - "Offboard Controller Tests"
Cohesion: 0.20
Nodes (16): csv, dataclasses, OffboardController — fly drone N through MAVROS from Python (docs/interface-…, geometry_msgs_msg, math, mavros_msgs_msg, mavros_msgs_srv, rclpy (+8 more)

### Community 20 - "ZED Drone Launch & TF"
Cohesion: 0.13
Nodes (20): drone_tf(), generate_launch_description(), inverse_pose(), params(), zed_wrapper for drone N, with the contract's topic names. Used by BOTH the sim…, The ros__parameters of the compiled params file ({} without one)., {launch arg: "true"|"false"} for the TF switches the params set; absent ones…, (t, q) of the inverse of the pose x y z + intrinsic ZYX roll pitch yaw: t =… (+12 more)

### Community 21 - "Project Plan & ADRs"
Cohesion: 0.14
Nodes (21): Project plan (bisg_isaac digital twin), ADR-002 Docker-first, Isaac Sim in a container, ADR-003 One PX4 version for SITL and Pixracer, ADR-004 CycloneDDS + zenoh bridge, ADR-005 ROS 2 Jazzy in all containers, ADR-009 Remote access via Tailscale service, Docker strategy (three image families, one compose), Isaac Sim 6.0.0 (+13 more)

### Community 22 - "ZED Bench Config & Image"
Cohesion: 0.16
Nodes (19): .bench.yaml (derived ZED bench config), Bench depth mode NEURAL_LIGHT, HD720 (vs NEURAL_PLUS HD1080 in zed.yaml), Derived bench config (python3 -m zed_stack derive; do not edit), ZED SDK image README, docker/zed/build.sh (desktop / jetson), CycloneDDS Dockerfile.overlay, zed.yaml (ZED stack config), ./bisg zed plan|set|up (+11 more)

### Community 23 - "ADR-008 ZED Stack"
Cohesion: 0.13
Nodes (19): ADR-008 One YAML, one image, small services, bisg/zed single image, Shared compose.yaml profiles zed and drone, docker/zed/zed.yaml single config, Bridge modules not yet built, zed-bridge service (ZED to PX4 via MAVROS), zed_stack compile/validate, zed-video service (QGC video) (+11 more)

### Community 24 - "Debug Commands"
Cohesion: 0.26
Nodes (18): cmd_clean_all(), cmd_clean_cache(), cmd_dds(), cmd_echo(), cmd_gpu(), cmd_hz(), cmd_kitlog(), cmd_mavlink() (+10 more)

### Community 25 - "QGC Video Stream"
Cohesion: 0.16
Nodes (6): main(), Image, Node, The tile of one source: re-decoded when a new frame arrived, a 'no signal'…, VideoStream, OpticalFlowRad

### Community 26 - "Tailscale Script"
Cohesion: 0.32
Nodes (16): backend(), connected(), follow(), host_cmd(), host_field(), host_json(), host_mode(), host_operator() (+8 more)

### Community 27 - "PX4 Bridge CLI Tests"
Cohesion: 0.19
Nodes (3): bridge(), compose_service(), Px4BridgeCli

### Community 28 - "Foxglove Layouts"
Cohesion: 0.23
Nodes (14): grid(), image(), kinetix(), path_script(), plot(), raptor(), Writes the /drone_1 layouts for the Lichtblick web UI (Foxglove format) next to…, nav_msgs/Path of `src` (a PoseStamped in map), one point per 5 cm, restarted… (+6 more)

### Community 29 - "Raptor USD Build Pipeline"
Cohesion: 0.14
Nodes (16): docker/sim/assets README, Onshape-to-FLU frame convention, Raptor USD build pipeline (STEP -> USD -> raptor.usd), Raptor 5in cinewhoop vehicle (Pegasus vehicle), docker/sim/tools/step_to_usd.py (CAD Converter), raptor.yaml (vehicle build inputs + scenario vehicle), Chase camera (third-person image), Duct collision cylinders (+8 more)

### Community 30 - "STEP-to-USD & ZED Pool Probe"
Cohesion: 0.13
Nodes (12): CAD (STEP) -> raw USD with the Isaac CAD Converter (HOOPS), plus a part…, intrinsics(), Probe: can the real ZED SDK give depth for TELEPORTED views (Kinetix view…, The extension authors the ZED_M optics on the camera prims once it streams:…, isaacsim, isaacsim_core_utils_extensions, omni_converter_hoops, omni_replicator_core (+4 more)

### Community 31 - "ZED Bridge Core"
Cohesion: 0.17
Nodes (11): Context, Shared pieces of the bridge modules (rclpy only where a function needs a node)., What every module needs to know: namespaces and a way to reach the others., main(), python3 -m zed_stack.bridge — the px4_bridge service (compose `zed-bridge`).…, ROS 2 image topics -> RTP/H.264 over UDP, for QGroundControl's "UDP h.264 Video…, gi, gi_repository (+3 more)

### Community 32 - "Roadmap & Phases"
Cohesion: 0.20
Nodes (16): Architecture decision records (docs/decisions/), Roadmap, Phase 1 Dockerized single-drone sim, Phase 2 ROS 2 + MAVROS control, Phase 3 Sensors, ZED Mini contract, VIO, Phase 4 Digital-twin assets, Phase 5 Hardware single drone, Phase 6 Swarm in sim (+8 more)

### Community 33 - "ADR-007 Real ZED SDK in Sim"
Cohesion: 0.15
Nodes (16): ADR-007 Real ZED SDK in the sim, ZED asset FixedJoint mount, One odometry source per run, Residual sim-vs-hardware ZED gap, Stereolabs zed-isaac-sim extension v5.2.1, ZED_SOURCE emulated|sdk switch, Five links that do not use ROS, The real ZED SDK in the sim (+8 more)

### Community 34 - "Raw MAVLink Offboard Tests"
Cohesion: 0.21
Nodes (7): main(), Offboard, Descend at DESCENT_M_S until PX4 detects ground contact, then disarm; True once…, m: a connected mavutil link with target_system/component set; on_msg(msg) sees…, Read messages for `seconds` (wall), streaming the current setpoint at 20 Hz., Arm in OFFBOARD and climb to `alt` m above the start position; True once…, main()

### Community 35 - "Remote Access (Tailscale ADR-009)"
Cohesion: 0.17
Nodes (15): ADR-002 Every runtime component has a Dockerfile / compose service, Remote access via tailscale compose service (ADR-009), One compose file for x86_64 workstation and arm64 Jetson (profiles), tailscale service (tailscaled on host network), ADR-009 Remote access: Tailscale node as compose service, ROS 2 DDS discovery does not cross the tailnet, Amendment 2026-10-20: tailnet follows the sim (TAILSCALE_WITH_SIM), Host Tailscale daemon cannot coexist with container (TAILSCALE_MODE=auto) (+7 more)

### Community 36 - "TODO Live List"
Cohesion: 0.17
Nodes (15): GPS-denied sim default (VIO + LW20 + PMW3901 + baro), Real ZED SDK runs in the sim via zed-isaac-sim extension, Warehouse default world (Kinetix photogrammetry), ZED stack configured only by docker/zed/zed.yaml (ADR-008), terminate_bt.cpp LD_PRELOAD for R9 hunt, TODO live list, Arming without VIO safety issue, B18 SDK connects once per sim run (+7 more)

### Community 37 - "Config & Compose Services"
Cohesion: 0.21
Nodes (13): config/bisg.conf (merged project settings), One key, one place rule, drone-zed service (real camera), isaac-cache-kit shader cache volume, lichtblick service (Foxglove web UI), Compose profiles (sim, ros, zed, drone, tailscale, px4-bridge), px4-bridge service, ros dev shell service (+5 more)

### Community 38 - "Known Bugs"
Cohesion: 0.19
Nodes (15): 320x180 ZED low-res variant (fits default rmem_max), GPS-denied default since 2026-10-15, Known bugs (bugs.md), B1 No usable failsafe action while GPS-denied, B13 No automated check camera view unobstructed, B18 SDK connects to sim stream once per run, B19 enable_streaming crashes wrapper in sim, B2 HD720 ZED images never reach subscriber (rmem_max) (+7 more)

### Community 39 - "ZED SDK Rig & Extension"
Cohesion: 0.17
Nodes (13): ext_folder(), Stdlib-only half of the ZED SDK mode (zed_sdk_rig.py): decisions that launch.py…, Folder holding the built extension (docker/zed/build_isaac_ext.sh). Checked…, stream_port(), attach_zed_sdk(), ZED Mini twin streamed into the REAL ZED SDK (scenario `sensors.zed.enabled`,…, Author one translate + one orient op (wxyz) so the body starts exactly where…, Mount the ZED Mini twin on `vehicle` (Pegasus Multirotor) and start streaming… (+5 more)

### Community 40 - "Cluster 40"
Cohesion: 0.14
Nodes (14): Foxglove web UI and layouts README, Foxglove stream bandwidth (use /compressed remotely), Caddy proxy: UI and bridge websocket on one port 8080, depth_mm / confidence_u16 conversion scripts, foxglove_probe.py debugging tool, kinetix.json layout (Kinetix photogrammetry flights), Kinetix user scripts (path_*, kinetix_track, kinetix_flight), Lichtblick (Foxglove Studio fork) web UI (+6 more)

### Community 41 - "Cluster 41"
Cohesion: 0.15
Nodes (8): main(), Switch every MAVROS plugin node to use_sim_time:=true (sim stack only,…, M2 — ZED depth image -> PX4's 72-sector obstacle map (MAVROS obstacle/send ->…, rcl_interfaces_msg, rcl_interfaces_srv, sensor_msgs_msg, main(), ROS side of the ZED pool-depth probe (docker/sim/tools/zed_pool_probe.py):…

### Community 42 - "Cluster 42"
Cohesion: 0.15
Nodes (9): carb, Follow camera for the GUI viewport, in the spirit of Gazebo's "follow" mode:…, _wrap(), Per-step speed-ups for Pegasus on Isaac Sim 6.0 (docs/performance.md,…, install(), __init__(), Real-time factor (sim seconds per wall second) as one more line of Kit's own…, logging (+1 more)

### Community 43 - "Cluster 43"
Cohesion: 0.18
Nodes (13): CLAUDE.md project instructions, ADR-001 MAVROS as PX4 <-> ROS 2 bridge, GPU contention with vLLM server on Workstation B, Ground rules (fresh start, phase by phase, interface contract), Isaac Sim 6.0 stack (Pegasus PR #144 fork, PX4 v1.17.0, Python 3.12), Gating checks (smoke, vio_flight, zed_depth_box, zed test, vio check), NVIDIA driver 580 branch guard (check_env.sh), px4-bridge single compose service (PX4_BRIDGE=mavros|mavsdk|xrce|none) (+5 more)

### Community 44 - "Cluster 44"
Cohesion: 0.23
Nodes (13): GPS-denied state estimation (VIO -> EKF2), Sim-to-real parity rules, Vehicle interface contract, Downward ToF rangefinder + optical flow doc, Range/flow accuracy benchmark (2026-10-10), Baro as EKF2 height reference, EKF2_MIN_RNG fix, GPS-denied on all sensors (ZED + LW20 + PMW3901 + baro) (+5 more)

### Community 45 - "Cluster 45"
Cohesion: 0.19
Nodes (13): The ROS 2 graph doc, Load and redundancy (~200 MB/s camera data), R1 two publishers on zed imu/data, R4 bridge subscribes to depth twice, R9 ZED wrapper time-source crash, /video_stream node, /zed_px4_bridge node, ZED module test + benchmark (+5 more)

### Community 46 - "Cluster 46"
Cohesion: 0.18
Nodes (10): cstdio, cstdlib, cxxabi, handler(), print_backtrace(), exception, execinfo, pthread (+2 more)

### Community 47 - "Cluster 47"
Cohesion: 0.30
Nodes (12): single_iris_vio scenario, depth_box test cuboid (1 m cube), ekf2_vision.params overlay, GPS-denied VIO scenario (EKF2 external vision), ZED odometry -> zed-bridge -> mavros/odometry/out, docker/sim/px4 README (PX4 parameter files), ekf2_vio_flow_range.params (real drone GPS-denied mode), ekf2_vision.params (+4 more)

### Community 48 - "Cluster 48"
Cohesion: 0.22
Nodes (8): ChaseCam, Chase camera of a vehicle as a ROS 2 image (scenario `sensors.chase_cam`,…, `dt`: sim seconds between two update() calls (the rendering step), for the…, Move the camera to this frame's chase pose (call once per rendered frame)., _wrap(), isaacsim_core_experimental_utils_app, omni_usd, usdrt_sdf

### Community 50 - "Cluster 50"
Cohesion: 0.24
Nodes (11): Configuration guide, Procedure for adding a config key, config/bisg.conf, Endpoint keys (DRONE_ID, FCU_URL, PX4_BRIDGE, ROS_DOMAIN_ID...), Version pins and source links, Config precedence (flag > env > .env > bisg.conf > fallbacks), Settings layering (bisg.conf / zed.yaml / .env / scenario YAML), SIM_VIEW (gui|headless|web|webrtc|both|auto) (+3 more)

### Community 51 - "Cluster 51"
Cohesion: 0.18
Nodes (11): ./bisg bag enable/start/stop/list/info/play, Bag profiles: flight, vision, all (docker/ros/bag.yaml), GPU container refuses to start: NVML driver/library version mismatch, PX4 never Ready for takeoff (port 4560, unknown model), Recording a run (rosbag2/MCAP, ./bisg bag), Sim slower than real time: ./bisg debug perf, rtf < 1.0, Smoke test / pymavlink shares MAVROS UDP 14540 (MAVROS topics nearly stop), Compose volume 'already exists but was not created by Docker Compose' (+3 more)

### Community 52 - "Cluster 52"
Cohesion: 0.18
Nodes (11): Isaac Sim 6.0 migration errors, bugs.md long-lived product bugs (B4, B9, B18), M1 PX4 v1.16.0 SITL build IndexError, M12 Deprecated APIs still in use, M19 Environment loading semantics changed, archive/docs/migration-report.md (context and results), Fetch NuttX tags after shallow-submodule clone (PX4 v1.16 build), isaacsim.ros2.bridge is a thin shim over ros2.core/nodes/ui/examples (+3 more)

### Community 53 - "Cluster 53"
Cohesion: 0.20
Nodes (11): README bisg_isaac, ./bisg operator CLI, Same containers for sim drone and real drone (Docker everywhere), Hardware target: Jetson Orin NX (JetPack 7.2) + Pixracer + ZED Mini, Kinetix photogrammetry project flies capture tours on the twin, Quick start (./bisg setup/up/smoke/zed), Repo layout, Settings: config/bisg.conf + docker/.env (this machine) (+3 more)

### Community 54 - "Cluster 54"
Cohesion: 0.22
Nodes (5): Serve the viewport as a still image over one TCP port. The WebRTC client needs…, Issue one viewport capture if the interval has elapsed. Never raises., WebView, do_GET(), _send()

### Community 55 - "Cluster 55"
Cohesion: 0.29
Nodes (10): ADR-002 Docker-first including Isaac Sim, bisg/sim, bisg/ros, bisg/zed images, network_mode host everywhere, ADR-004 CycloneDDS everywhere, zenoh bridge over WiFi, rmw_cyclonedds_cpp with committed cyclonedds.xml, zenoh-bridge-ros2dds with allow-list, ADR-005 ROS 2 Jazzy (Ubuntu 24.04) in all containers, Isaac Sim bundled Jazzy ROS 2 bridge (exts/isaacsim.ros2.core/jazzy) (+2 more)

### Community 56 - "Cluster 56"
Cohesion: 0.20
Nodes (10): ADR-003 One PX4 tag for SITL and Pixracer, MAVROS 2.15.1, Pegasus PR #144 head fcb99c0, px4_fmu-v4_default Pixracer firmware (95.3% flash), PX4_TAG Dockerfile arg, Re-validation on Isaac Sim 6.0 (2026-10-02), Selection procedure (Phase 1), PX4 v1.16.0 fallback (+2 more)

### Community 57 - "Cluster 57"
Cohesion: 0.20
Nodes (10): M8 update 2026-10-14: bottleneck moved to camera renders, Camera renders dominate sim cost, Chase cam rate_hz 10 Hz default (sensors.chase_cam.rate_hz), py-spy: 82% of main thread in simulation_app.update(), Pegasus ~10%, Multi-tick rendering (omni:sensor:tickRate), View mode (window, WebRTC) costs < 8%, headless+webrtc ~11%, Workstation A (RTX 4500) RTF table, Workstation B measurements (RTF 0.72 headless) (+2 more)

### Community 58 - "Cluster 58"
Cohesion: 0.22
Nodes (10): M8 Sim speed fell 1.18x to 0.33x, pegasus_fast.py partial fix (RTF 0.44 to 0.54 GUI, 0.85 headless), Pegasus per-step Python: 6 RigidPrim calls, warp array construction, Online asset-root lookup delays boot (get_assets_root_path), Boot sims one at a time (concurrent Kit boot segfaulted/hung), Upstream IsaacSim issue #504 and Pegasus #111/#79, 8 drones as two sims, one per GPU: rtf 0.67 vs 0.40, pegasus_fast.py runtime patch (cached prims, batched force call) (+2 more)

### Community 59 - "Cluster 59"
Cohesion: 0.36
Nodes (10): ADR-001 MAVROS instead of uXRCE-DDS, MAVROS 2.15.1, Multi-vehicle model (ports, IDs, namespaces), The PX4 bridge doc, Drone ID = namespace, PX4_BRIDGE=mavros (default), PX4_BRIDGE=mavsdk, Components that need MAVROS (vio_mock, zed-bridge, vio_flight) (+2 more)

### Community 60 - "Cluster 60"
Cohesion: 0.49
Nodes (9): current(), newest(), resolve(), ros_up(), running(), bag.sh script, start(), status() (+1 more)

### Community 61 - "Cluster 61"
Cohesion: 0.33
Nodes (6): each(), listening(), row(), info.sh script, sub(), ts_json()

### Community 62 - "Cluster 62"
Cohesion: 0.31
Nodes (7): mavros(), mavsdk(), entrypoint.sh script, xrce(), ext_setup_bash, ext_setup_zsh, host_ros_env.sh script

### Community 63 - "Cluster 63"
Cohesion: 0.25
Nodes (9): raptor.usd, sim.yaml (scenario locator), launch.py expand_locator, Scenario locator (sim.yaml), Spawn pose override, Warehouse lighting tuning (light_scale 0.5, ambient 2), Warehouse world (Isaac 6.0 Simple_Warehouse), docker/sim/worlds README (+1 more)

### Community 64 - "Cluster 64"
Cohesion: 0.22
Nodes (9): single_iris_vio_lowres scenario, two_iris_nozed.yaml scenario, two_iris_vio_lowres scenario, Two-drone per-drone ZED topic/TF/IMU separation check, B16 Contract TF frames drone_n-prefixed; wrapper cannot prefix, Scenario extends: inheritance, ZED Mini mount pose xyz_rpy TBD (sim [0.18, 0, -0.02, 0, 0, 0]), Vehicle interface contract (+1 more)

### Community 65 - "Cluster 65"
Cohesion: 0.25
Nodes (6): resolve_vehicle_usd(), Features, load_features(), Read the ZED switches from docker/zed/zed.yaml, the file the real zed_wrapper…, publish_imu(), Physically-simulated IMU on `{body_path}/zed_imu_link`, published on…

### Community 66 - "Cluster 66"
Cohesion: 0.25
Nodes (9): ./bisg setup command, bisg/sim:6.0.0 image, scripts/check_env.sh preflight (driver, runtime, compose, X11, disk, ports), docker/.env (machine-local), Pull nvcr.io/nvidia/isaac-sim:6.0.0 and ros:jazzy-ros-base, PegasusSimulator submodule (PR #144 head), --third-party fallback clones Pegasus and zed-ros2-wrapper v5.4.1, Setup timing: pull ~3 min, sim build ~4, ros ~2, arm64 ~15 (+1 more)

### Community 67 - "Cluster 67"
Cohesion: 0.28
Nodes (8): importlib, pathlib, rclpy_time, main(), parse_contract(), parse_rate(), Phase 3 exit test (docs/roadmap.md): the live ROS graph of drone N against…, Rows of the 'provided by the vehicle' table: dicts topic, type, rate (lo, hi Hz…

### Community 68 - "Cluster 68"
Cohesion: 0.44
Nodes (8): have_frames(), zed.sh script, start_services(), svc_name(), video_hint(), video_ip(), ZED_SIM_PORT, zexec()

### Community 70 - "Cluster 70"
Cohesion: 0.36
Nodes (3): Archive, archived(), The 2026-10-15 flights (docs/vio.md, archive/vio-2026-10-15/README.md).…

### Community 71 - "Cluster 71"
Cohesion: 0.39
Nodes (8): SIM_VIEW window + remote view key, Watching the sim from somewhere else (remote access doc), ./bisg info access overview, SIM_VIEW_ADDR advertised address, VS Code tunnel / SSH port forward for web view, SIM_VIEW=web still-frame browser view (TCP 8899), SIM_VIEW=webrtc interactive Isaac UI (TCP 49100 + UDP 47998), What does not work (Cloudflare Tunnel, browser WebRTC, UDP over SSH)

### Community 72 - "Cluster 72"
Cohesion: 0.36
Nodes (8): Scenario eight_iris_nozed, Scenario four_iris_nozed, Scenario single_iris_nozed (base), extends: single_iris.yaml, Isolate Isaac + Pegasus + PX4 from the sensor layer, ros2 pub_state true; pub_sensors/pub_graphical_sensors false, Iris vehicle 0, usd_path null, spawn z 0.07, sensors.zed.enabled false

### Community 73 - "Cluster 73"
Cohesion: 0.32
Nodes (8): Resetting (clean-cache, volumes), M15 debug mavlink needs pymavlink on host, Workstation setup doc, bisg/ros:arm64 image, Jetson Orin NX (JetPack 7.2, L4T r38.4), Jetson steps: save/load arm64 image, build l4t-r38, udev /dev/px4, drone up, Uninstall / reset (clean-cache, clean-all, docker rmi), ZED SDK image: docker/zed/build.sh desktop|jetson (stereolabs 5.4.1 cuda12.8)

### Community 74 - "Cluster 74"
Cohesion: 0.39
Nodes (7): ADR-010 Pegasus fork, Pegasus fork akashshingha850/PegasusSimulator branch local, Pegasus PR #144 (Isaac Sim 6.0 port), PEGASUS_TAG=local-<sha> pin form, Push to fork before superproject commit, clone(), fetch_sources.sh script

### Community 75 - "Cluster 75"
Cohesion: 0.29
Nodes (3): main(), spin(), wait()

### Community 76 - "Cluster 76"
Cohesion: 0.32
Nodes (6): load_scenario(), merge(), main(), quat_xyzw_to_matrix(), ZED depth check against a known box (scenario `world.objects`, e.g.…, Same `extends:` deep-merge as docker/sim/launcher/launch.py.

### Community 77 - "Cluster 77"
Cohesion: 0.38
Nodes (6): log(), main(), mission_square — Phase 2 exit test (docs/roadmap.md): take off, fly a square,…, use_sim_time_if_clock(), rclpy_parameter, rclpy_utilities

### Community 78 - "Cluster 78"
Cohesion: 0.33
Nodes (7): headless_fast.yaml scenario, app.render: false, world preset Default Environment, Iris vehicle id 0 (ros2 disabled), perf.skip_material_loading, app.stream: off, sensors.zed.enabled: false

### Community 79 - "Cluster 79"
Cohesion: 0.43
Nodes (6): apply(), apply_force(), apply_torque(), handle_propeller_visual(), _prim(), update()

### Community 80 - "Cluster 80"
Cohesion: 0.33
Nodes (7): Debugging guide, ./bisg status then ./bisg debug report (logs/debug_<ts>.tar.gz), Host ROS 2 (optional, debugging only), Log locations (launcher, Kit log, .ulg, MAVROS, perf heartbeat), PX4 shell without QGC, ROS 2 graph commands (debug topics/hz/echo in the ros container), M5 Sim container shows (unhealthy)

### Community 81 - "Cluster 81"
Cohesion: 0.29
Nodes (7): DDS checks: ./bisg debug dds, ROS_DOMAIN_ID, RMW, rmem_max, docker/cyclonedds.xml, >= 60 GB free on Docker root disk (Isaac 21 GB + sim ~25 GB + ZED ~15 GB), Host prerequisites (driver, Docker, nvidia-container-toolkit), Install nvidia-container-toolkit (apt, nvidia-ctk runtime configure), net.core.rmem_max UDP buffer sysctl, HD720 image (2.7 MB, ~42 UDP fragments) never arrives at default 208 KB buffer

### Community 82 - "Cluster 82"
Cohesion: 0.57
Nodes (7): ADR-001 MAVROS as PX4-ROS 2 bridge, MAVROS 2.x PX4-ROS 2 bridge, MAVROS lean plugin list (mavros_lean.yaml), MAVSDK 4.x, One selectable px4-bridge service (PX4_BRIDGE), PX4-link study (archive/px4-link-study), uXRCE-DDS (rejected alternative)

### Community 83 - "Cluster 83"
Cohesion: 0.29
Nodes (7): headless_fast 132-137 steps/s vs 317 on 5.1, isaac-cache-kit volume (/isaac-sim/kit/cache), M6 Shader cache not persisted (190 s boot), M9 app.render false no longer physics-only, First boot ~190 s shader compile into isaac-cache-kit, Isaac 6.0 loop: one simulation_app.update() per rendering_dt, steps/s counts real physics steps, Isaac 6.0 migration table (nozed 0.48, vio 0.33, 2/4/8 drones)

### Community 84 - "Cluster 84"
Cohesion: 0.29
Nodes (7): Async rendering is not a lever, CPU governor powersave but intel_pstate EPP performance, Handbook flags tried: fabricUpdate off, numThreads=0, asyncRendering hang, Render cadence fix (2026-09-13): one frame per rendering_dt/physics_dt steps, RTF HUD in GUI (rtf_hud.py, app.viewport_hud), RTX 2080 Ti measurements (2026-09-13), A second GPU / NVENC is not a lever for one sim

### Community 85 - "Cluster 85"
Cohesion: 0.38
Nodes (3): pcompose(), px4-bridge.sh script, stop()

### Community 87 - "Cluster 87"
Cohesion: 0.33
Nodes (5): expand_locator(), load_scenario(), merge(), The locator keys of docker/sim/sim.yaml (what the sim runs) -> the plain…, Read a scenario YAML. `extends: <file>` or a list of files (relative to this…

### Community 88 - "Cluster 88"
Cohesion: 0.33
Nodes (6): Runbook simulation stack, ./bisg CLI cheat sheet, Launcher must be PID 1 (do not use python.sh), Real ZED SDK in the sim (runbook section), Smoke test (arm, takeoff, land), First run: config, up, up web, smoke, mavros, down

### Community 90 - "Cluster 90"
Cohesion: 0.60
Nodes (5): single_iris_flow scenario, ekf2_flow_range.params overlay, tests/flow_hold.py, GPS-denied on ToF + optical flow (no ZED), ekf2_flow_range.params

### Community 91 - "Cluster 91"
Cohesion: 0.50
Nodes (4): isaac_python_exec(), ROS_DISTRO, entrypoint.sh script, SIM_CONFIG

### Community 92 - "Cluster 92"
Cohesion: 0.40
Nodes (5): EKF2_EV_CTRL 15 (or 11 without vel) and EKF2_HGT_REF Vision, ZED velocity-only fusion (EKF2_EV_CTRL 12) robust fallback, config ev_no_position (EKF2_EV_CTRL 12), EKF2_EV_CTRL 13 (pos + vel + yaw from ZED), ZED velocity only (EKF2_EV_CTRL 12) is robust variant

### Community 93 - "Cluster 93"
Cohesion: 0.40
Nodes (5): Docker data-root relocation, Emulated ZED rig (removed), Sim image extra libs (libpng16, libjpeg-turbo8, libturbojpeg, libusb), zed-isaac-sim extension build, Real ZED SDK in the sim (ZED_SOURCE=sdk): fetch_sources, zed build, zed image

### Community 94 - "Cluster 94"
Cohesion: 0.70
Nodes (4): die(), pass(), check_env.sh script, wrn()

### Community 95 - "Cluster 95"
Cohesion: 0.50
Nodes (3): drone.sh script, ZED_STACK_SIM, zexec()

### Community 96 - "Cluster 96"
Cohesion: 0.50
Nodes (3): Params, Twin mount (raptor.yaml, FLU), EKF2 lever arm (raptor.params, FRD) and the…, read_params()

### Community 97 - "Cluster 97"
Cohesion: 0.67
Nodes (4): bag profile: all, rosbag2 recording config (bag.yaml), bag profile: flight, bag profile: vision

### Community 98 - "Cluster 98"
Cohesion: 0.50
Nodes (4): ROS GUI/debug tools config (tools.yaml), foxglove tool (bridge + web UI), rqt tool, rviz tool

### Community 99 - "Cluster 99"
Cohesion: 0.67
Nodes (3): main(), pump(), wait()

## Knowledge Gaps
- **250 isolated node(s):** `entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO`, `ros_env.sh script`, `ROS_DOMAIN_ID` (+245 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 606 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **93 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Doc reading order` connect `Roadmap & Phases` to `Cluster 64`, `ADR-007 Real ZED SDK in Sim`, `TODO Live List`, `VIO Accuracy Campaigns`, `Cluster 73`, `Cluster 45`, `Cluster 80`, `Sim Scenario & Physics Config`, `Cluster 53`, `Project Plan & ADRs`, `ADR-008 ZED Stack`, `Cluster 88`, `Cluster 59`, `Raptor USD Build Pipeline`?**
  _High betweenness centrality (0.226) - this node is a cross-community bridge._
- **Why does `VIO campaign doc` connect `VIO Accuracy Campaigns` to `Roadmap & Phases`, `Cluster 57`, `Offboard Controller Tests`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Why does `single_iris scenario` connect `Sim Scenario & Physics Config` to `Cluster 64`, `Known Bugs`, `ZED SDK Rig & Extension`, `Sim Launcher`, `Cluster 78`, `Cluster 47`, `Cluster 48`, `Cluster 50`, `Cluster 90`, `Raptor USD Build Pipeline`, `Cluster 63`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **What connects `entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO` to the rest of the system?**
  _250 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Range/Flow Evaluation` be split into smaller, more focused modules?**
  _Cohesion score 0.06105834464043419 - nodes in this community are weakly interconnected._
- **Should `Config Loader & ZED YAML` be split into smaller, more focused modules?**
  _Cohesion score 0.05174825174825175 - nodes in this community are weakly interconnected._
- **Should `ZED Benchmark Harness` be split into smaller, more focused modules?**
  _Cohesion score 0.08282828282828283 - nodes in this community are weakly interconnected._