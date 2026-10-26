# Graph Report - bisg_isaac  (2026-10-26)

## Corpus Check
- 71 files · ~266,405 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1831 nodes · 3098 edges · 153 communities (110 shown, 43 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 185 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Jump Gate
- ZED Stack Config
- ZED Benchmark
- Shell Scripts Common
- Roadmap and Remote Access Docs
- Manhattan Compass Bridge
- VIO Report and ROS Tools
- Scenarios and Known Bugs
- VIO Campaign Runner
- VIO Report Tests
- VIO Eval
- Range-Flow Eval and ULog
- ADRs and Architecture Decisions
- ZED Bridge Modules
- Map Correction
- Sim Launcher
- Flight Bench Helpers
- Flight Test Scripts
- Odometry and Obstacle Bridge
- Launch Script Commands
- Unit Test Suites
- Range-Flow Backend
- Offboard Controller
- ZED Drone Launch
- ZED SDK Rig
- ZED Node and Video
- Drift Correction Design
- Structural Regularity Research
- PX4 Bridge CLI
- Drift Analysis
- Manhattan Drift Results
- Debug Script
- Hover and Params Tests
- Isaac 6.0 Migration Errors
- ZED Tracking and Area Memory
- Optical Flow and ToF Twins
- Drift Plots
- Tailscale Script
- Foxglove Layouts
- Asset Pipeline Tools
- Offboard
- mosaic.py
- single_iris scenario
- VideoStream
- Frame-to-model / scan-to-map registratio
- vio_campaign.py (./bisg vio bench / chec
- px4_bridge service (zed-bridge)
- zed-ros2-wrapper fork local (60f78bd, up
- range_flow.py
- Component choices and version pins table
- terminate_bt.cpp
- zed_depth_box.py
- chase_cam.py
- FollowCam
- Horizontal EKF2 error vs distance flown 
- Performance and profiling
- zed-isaac-sim v5.2.1 extension (529e538)
- WebView
- Long-flight drift test figure (5 laps of
- Camera renders dominate sim cost
- M8 Sim speed fell 1.18x to 0.33x
- config calibrated (shipped GPS-denied mo
- bag.sh
- info.sh
- Vehicle interface contract (ROS 2 topics
- zed.yaml: single config for everything t
- px4-bridge/entrypoint.sh
- PX4 v1.17.0 pin
- Four error sources of the IMU-less sim S
- check_contract.py
- zed.sh
- Checker
- Archive
- Fake
- ADR-010 Pegasus fork
- ORB-SLAM3
- /drone_1/zed/zed_node (real ZED SDK wrap
- Sim ZED fuses high-rate IMU (ingest_imu 
- main()
- zed_sdk_check.py
- sim.yaml: the one file locating scenario
- mission_square.py
- Per-drone bill of materials (Pixracer, O
- headless_fast.yaml scenario
- App
- apply()
- RTX 2080 Ti measurements (2026-09-13)
- v1.17 EKF2_EVA_NOISE unsquared yaw varia
- Degeneracy detection via Hessian eigen-a
- docker/zed/zed.yaml single config (ADR-0
- px4-bridge.sh
- MosaicTest
- Topics provided by the vehicle (mavros/*
- load_scenario()
- ZED module test + benchmark
- SectorTests
- Probe
- TF frame tree (map, odom, zed_camera_lin
- Raptor USD build pipeline (STEP -> USD -
- sim/entrypoint.sh
- zed_sdk_cfg.py
- Kinetix explore paths figure (Warehouse,
- EKF2_EVP_GATE per-axis 5-sigma innovatio
- check_env.sh
- drone.sh
- Debugging symptom-to-command table
- rosbag2 recording config (bag.yaml)
- ROS GUI/debug tools config (tools.yaml)
- single_iris_flow scenario
- Kinetix explore: EKF2 error over the fli
- ~200 MB/s camera traffic, lazy computati
- main()
- config/bisg.conf (merged project setting
- Foxglove/Lichtblick layouts raptor.json 
- Shared ROS 2 packages (bisg_msgs, bisg_v
- .bench.yaml (derived ZED bench config)
- build.sh
- ros_env.sh
- install_host_ros.sh
- bisg
- Workstation A (RTX 4500 Ada) and B (2x R
- Tailscale remote access (ADR-009)
- ros/entrypoint.sh
- setup.py
- bridge/__init__.py
- 6.0 setup_ros_env.sh defaults to FastDDS
- Port to isaacsim.sensors.experimental.ph
- M14 smoke_takeoff fails at low RTF
- M18 Pegasus pin only on PR ref
- M4 WebRTC livestream.nvcf extension gone
- M7 ZED images publish at full render rat
- GOMSF decoupled VIO-to-global alignment
- /bisg_sim_clock publishing /clock
- Arming without VIO safety gate (open)
- Pool depth probe for teleported views
- pull_images.sh
- setup.sh
- vio.sh
- Image
- M10 Test box renders yellow, not orange
- M11 Second drone mavros/state shows CMOD
- M15 debug mavlink needs pymavlink on hos
- M16 Benign warnings that look like error
- M17 6.0.0 image reports a release-candid
- M2 UnboundLocalError 'omni' after World 
- M5 Sim container shows (unhealthy)
- ROS_DOMAIN_ID=auto per-machine domain
- Structure-SLAM / StructSLAM
- PX4-Autopilot pin via PX4_TAG
- Foxglove kinetix.json / raptor.json layo
- TAILSCALE_WITH_SIM=1 verification
- OpticalFlowRad

## God Nodes (most connected - your core abstractions)
1. `JumpGate` - 26 edges
2. `Known bugs (bugs.md)` - 20 edges
3. `RangeFlowBackend` - 18 edges
4. `OffboardController` - 18 edges
5. `Odometry2Px4` - 18 edges
6. `Flight` - 17 edges
7. `launch.sh script` - 17 edges
8. `sh()` - 16 edges
9. `build_phases()` - 16 edges
10. `debug.sh script` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Verdict gates (latency, velocity scale, lever arm, event-free error)` --semantically_similar_to--> `verify thresholds (latency 20 ms, scale 0.03, lever 3 cm, 0.25 m)`  [INFERRED] [semantically similar]
  docs/vio-campaign.md → tests/vio_bench.yaml
- `params()` --indirect_call--> `f()`  [INFERRED]
  docker/zed/zed_drone.launch.py → tests/zed_bench.py
- `load()` --indirect_call--> `f()`  [INFERRED]
  scripts/ros_bag.py → tests/zed_bench.py
- `load()` --indirect_call--> `f()`  [INFERRED]
  scripts/ros_tools.py → tests/zed_bench.py
- `Four config files, each answering a different question` --references--> `sim.yaml: the one file locating scenario, vehicle, world, PX4 params`  [INFERRED]
  docs/configuration.md → docker/sim/sim.yaml

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **ZED stack: one YAML, one image, three services** — docs_zed_stack_zed_yaml, docs_decisions_adr_008_zed_stack_bisg_zed_image, docs_decisions_adr_008_zed_stack_zed_bridge_service, docs_decisions_adr_008_zed_stack_zed_video_service, docs_decisions_adr_008_zed_stack_zed_stack_compiler [EXTRACTED 0.95]
- **M8 simulation-speed investigation chain** — docs_migration_errors_m8, docs_migration_errors_pegasus_per_step_python, docs_migration_errors_pegasus_fast, docs_migration_errors_camera_bottleneck_update, docs_performance_camera_render_cost [EXTRACTED 1.00]
- **Camera render cost levers (chase cam rate, ZED fps, ZED off)** — docs_performance_chase_cam_rate, docs_performance_zed_twin_cost, docs_performance_zed_15fps_rejected, docs_performance_multi_tick_rendering [EXTRACTED 1.00]
- **PX4 bridge options behind one service** — docs_px4_bridge_px4_bridge_service, docs_px4_bridge_mavros_bridge, docs_px4_bridge_mavsdk_bridge, docs_px4_bridge_xrce_bridge [EXTRACTED 1.00]
- **Selectable PX4 bridge options** — docs_decisions_adr_001_mavros_px4_bridge_selectable_service, docs_decisions_adr_001_mavros_mavros_bridge, docs_decisions_adr_001_mavros_mavsdk, docs_decisions_adr_001_mavros_uxrce_dds [EXTRACTED 1.00]
- **Raptor CAD to scenario vehicle build flow** — docker_sim_assets_readme_step_to_usd, docker_sim_tools_build_raptor, docker_sim_assets_readme_raptor_usd, docker_sim_assets_readme_raptor_summary_json [EXTRACTED 1.00]
- **Tailscale remote access stack (ADR, compose service, user docs)** — docs_decisions_adr_009_remote_access_tailscale, docs_remote_access [EXTRACTED 1.00]
- **ZED stack services sharing one image and zed.yaml** — docker_compose_zed_service, docker_compose_zed_bridge_service, docker_compose_zed_video_service, docker_compose_drone_zed_service, docker_zed_zed_yaml_config [EXTRACTED 1.00]
- **GPS-denied EKF2 configuration across sim.yaml, PX4 overlays and zed.yaml** — docker_sim_sim_scenario_locator, docker_sim_px4_readme_ekf2_vio_flow_range_overlay, docker_sim_px4_readme_ev_compass_overlay, docker_zed_zed_positional_tracking, claude_gps_denied_default [INFERRED 0.85]
- **Twin parity: contract, hardware table and parity checks** — docs_interface_contract_vehicle_interface_contract, docs_interface_contract_parity_checks, docs_hardware_zed_mini_model_table, docs_plan_digital_twin_goal [INFERRED 0.85]
- **Manhattan compass correction pipeline** — docs_vio_drift_manhattan_compass, docs_vio_drift_mapcorr, docs_vio_drift_ev_compass_params, docs_vio_drift_compass_histogram_search [EXTRACTED 1.00]
- **How EKF2 v1.17 handles an external-vision jump** — docs_research_research_notes_vio_drift_fixes_for_indoor_drones_ekf_fusion_of_corrections_ev_reset_counter, docs_research_research_notes_vio_drift_fixes_for_indoor_drones_ekf_fusion_of_corrections_evp_gate, docs_research_research_notes_vio_drift_fixes_for_indoor_drones_ekf_fusion_of_corrections_long_rejection_reset, docs_research_research_notes_vio_drift_fixes_for_indoor_drones_ekf_fusion_of_corrections_ev_pos_bias_estimator [EXTRACTED 1.00]
- **VIO campaign method** — docs_vio_campaign_campaign_tool, docs_vio_campaign_fresh_sim_per_flight, docs_vio_campaign_vio_eval, docs_vio_campaign_verdict_gates [EXTRACTED 1.00]
- **Compass/ZED fusion variants compared by horizontal error** — docs_figures_drift_error_no_compass_control, docs_figures_drift_error_compass_zed_position_fused, docs_figures_drift_error_compass_v2_zed_velocity, docs_figures_drift_error_compass_v3_zed_velocity_shipped [EXTRACTED 1.00]
- **Long-flight drift test configurations compared** — docs_figures_drift_paths_no_compass_zed_velocity_yaw, docs_figures_drift_paths_compass_zed_position_fused, docs_figures_drift_paths_compass_v2_zed_velocity, docs_figures_drift_paths_compass_v3_zed_velocity_shipped [EXTRACTED 1.00]
- **Kinetix explore EKF2 drift: before vs after compass + ZED velocity** — docs_figures_kinetix_explore_paths_before_no_compass_zed_position, docs_figures_kinetix_explore_paths_compass_zed_velocity, docs_figures_kinetix_explore_paths_ekf2_pose [INFERRED 0.85]

## Communities (153 total, 43 thin omitted)

### Community 0 - "Jump Gate"
Cohesion: 0.07
Nodes (34): collections, add3(), angle_between(), JumpGate, norm3(), qconj(), qmul(), qnorm() (+26 more)

### Community 1 - "ZED Stack Config"
Cohesion: 0.06
Nodes (31): copy, difflib, ConfigError, deep_merge(), _flatten_params(), load(), docker/zed/zed.yaml -> zed_wrapper parameters + the list of services to start.…, {section: {key: default}} from the wrapper's own YAML files (the model file… (+23 more)

### Community 2 - "ZED Benchmark"
Cohesion: 0.06
Nodes (40): Features, load_features(), Read the ZED switches from docker/zed/zed.yaml, the file the real zed_wrapper…, rosgraph_msgs_msg, rosidl_runtime_py_utilities, std_srvs_srv, Bench, build_phases() (+32 more)

### Community 3 - "Shell Scripts Common"
Cohesion: 0.07
Nodes (33): build_isaac_ext.sh script, stamp(), _BISG_ENV0, BISG_SRC, conf_default(), container_running(), die(), fail() (+25 more)

### Community 4 - "Roadmap and Remote Access Docs"
Cohesion: 0.06
Nodes (45): ADR-009 Remote access: Tailscale node as compose service, ROS 2 DDS discovery does not cross the tailnet, Amendment 2026-10-20: tailnet follows the sim (TAILSCALE_WITH_SIM), Host Tailscale daemon cannot coexist with container (TAILSCALE_MODE=auto), No auth keys, browser login only, tailscale compose service decision, Plain tailscaled, not containerboot, TCP-only tunnels cannot carry WebRTC UDP 47998 (+37 more)

### Community 5 - "Manhattan Compass Bridge"
Cohesion: 0.08
Nodes (21): Compass, quat_to_R(), Manhattan compass: a drift-free heading from the walls of a box room, in the…, Fold an angle (rad) into [-pi/4, pi/4)., Room axis (rad, in [-pi/4, pi/4)) in the odometry frame from one depth image (H…, Room axis -> yaw drift of the odometry. The reference is the median axis of the…, meas = room_axis(...) result or None. Returns the drift estimate (rad) once the…, room_axis() (+13 more)

### Community 6 - "VIO Report and ROS Tools"
Cohesion: 0.09
Nodes (37): datetime, glob, re, command(), load(), main(), Read / toggle docker/ros/bag.yaml (rosbag2 recording, ./bisg bag). ros_bag.py…, The YAML folds the long patterns over several lines: drop the whitespace. (+29 more)

### Community 7 - "Scenarios and Known Bugs"
Cohesion: 0.07
Nodes (37): main(), Switch every MAVROS plugin node to use_sim_time:=true (sim stack only,…, Scenario eight_iris_nozed, Scenario four_iris_nozed, Scenario single_iris_nozed (base), extends: single_iris.yaml, Isolate Isaac + Pegasus + PX4 from the sensor layer, ros2 pub_state true; pub_sensors/pub_graphical_sensors false (+29 more)

### Community 8 - "VIO Campaign Runner"
Cohesion: 0.13
Nodes (34): base64, frame(), need(), What does a Foxglove client see on the foxglove_bridge, and does the data flow?…, shutil, socket, struct, boot() (+26 more)

### Community 9 - "VIO Report Tests"
Cohesion: 0.10
Nodes (16): flight(), A yaw error rotates positions about the takeoff point; the old whole-flight fit…, w, x, y, z of R = Rz(psi) Ry(pitch) (FRD body -> NED)., A 60 s log as vio_eval reads it. Truth: rest 5 s, climb to 1 m, figure flown…, Synthetic, yaw_quat(), campaign(), dump() (+8 more)

### Community 10 - "VIO Eval"
Cohesion: 0.10
Nodes (32): rot(), analyse(), v_cam_body(), cols(), continuous(), ekf_section(), ev_pos_from_params(), _kept() (+24 more)

### Community 11 - "Range-Flow Eval and ULog"
Cohesion: 0.11
Nodes (30): best_lag(), binned(), eval_ekf(), eval_flow(), err_at(), expected(), eval_ros(), err_at() (+22 more)

### Community 12 - "ADRs and Architecture Decisions"
Cohesion: 0.08
Nodes (34): SIM_VIEW key (gui/headless/web/webrtc/both/auto), SIM_VIEW values and combination with +, ADR-001 MAVROS as PX4-ROS 2 bridge, MAVROS 2.x PX4-ROS 2 bridge, MAVROS lean plugin list (mavros_lean.yaml), MAVSDK 4.x, One selectable px4-bridge service (PX4_BRIDGE), PX4-link study (archive/px4-link-study) (+26 more)

### Community 13 - "ZED Bridge Modules"
Cohesion: 0.08
Nodes (8): Module, Rate, Messages per second over a sliding window, and how long ago the last one came…, Base of a bridge module. `status()` is polled once a second by the health…, Health, ObstacleDistance, Image, MAVROS defaults the obstacle plugin to GLOBAL; ours is a body-frame (FRD) scan.

### Community 14 - "Map Correction"
Cohesion: 0.14
Nodes (19): MapCorrection, qz(), Carry the ZED's map-frame corrections (loop closure, relocalisation) into the…, A map pose and an odom pose of the same camera frame (same stamp)., Heading-only target (the Manhattan compass): turn the correction to `yaw` about…, (m, deg) still to apply at the current odom position., The output pose for an odom sample at time t (s)., rz() (+11 more)

### Community 15 - "Sim Launcher"
Cohesion: 0.09
Nodes (23): apply_paths(), apply_px4_params(), drop_world_prims(), keep_only_world_prims(), bisg_isaac Pegasus launcher — YAML-driven Isaac Sim standalone app. /isaac-…, Deactivate every top-level prim of the world asset whose name matches none of…, Deactivate the prims of the world asset whose path below `root` matches one of…, Multiply the intensity of every UsdLux light in the world asset by `scale`… (+15 more)

### Community 16 - "Flight Bench Helpers"
Cohesion: 0.10
Nodes (5): Bench, Fly `dist` m at (vx, vy) ENU m/s (sim-time duration), then hold where it…, Flight, main(), Fly to (dx, dy) from the start point at `alt` m above it; hold `settle` seconds.

### Community 17 - "Flight Test Scripts"
Cohesion: 0.20
Nodes (20): argparse, csv, dataclasses, OffboardController — fly drone N through MAVROS from Python (docs/interface-…, geometry_msgs_msg, math, mavros_msgs_msg, mavros_msgs_srv (+12 more)

### Community 18 - "Odometry and Obstacle Bridge"
Cohesion: 0.12
Nodes (18): Shared pieces of the bridge modules (rclpy only where a function needs a node)., M10 — ZED health -> one status topic + STATUSTEXT in QGroundControl. Publishes…, M2 — ZED depth image -> PX4's 72-sector obstacle map (MAVROS obstacle/send ->…, M1 — ZED positional tracking -> PX4 EKF2 external vision (MAVROS odometry/out).…, Depth image -> 72 x 5 deg obstacle sectors. numpy only, so it is unit-testable…, Depth image (H x W, metres, float32) + pinhole intrinsics -> 72 ranges [m]: inf…, sectors_from_depth(), json (+10 more)

### Community 19 - "Launch Script Commands"
Cohesion: 0.19
Nodes (24): bag_close(), cmd_all(), cmd_build(), cmd_config(), cmd_down(), cmd_logs(), cmd_mavros(), cmd_restart() (+16 more)

### Community 20 - "Unit Test Suites"
Cohesion: 0.11
Nodes (17): os, tempfile, load(), main(), Tables of long-flight drift runs (tests/drift_flight.py output dirs) for…, 2x2 QGC video image functions (docker/zed/zed_stack/mosaic.py). Needs OpenCV,…, Params, VIO analysis + calibration tests, numpy only (no sim, ROS, GPU or containers):… (+9 more)

### Community 21 - "Range-Flow Backend"
Cohesion: 0.11
Nodes (8): Backend, attach(), ned_to_latlon(), RangeFlowBackend, Range from `mount` (body FLU) straight down the body Z axis to the first…, Return a RangeFlowBackend for a scenario vehicle, or None when neither sensor…, Inverse of PX4's azimuthal-equidistant MapProjection, so PX4's ground-truth…, cfg: the vehicle's `sensors:` block (`tof:` and/or `optical_flow:`); px4: the…

### Community 22 - "Offboard Controller"
Cohesion: 0.17
Nodes (5): OffboardController, MAVROS connected and a local position estimate flowing; fixes the mission…, Stream a hover setpoint `alt` m above the origin, switch to OFFBOARD, arm, wait…, Fly to (x, y, z) m from the origin (z None = keep the current setpoint height);…, Result

### Community 23 - "ZED Drone Launch"
Cohesion: 0.13
Nodes (20): drone_tf(), generate_launch_description(), inverse_pose(), params(), zed_wrapper for drone N, with the contract's topic names. Used by BOTH the sim…, The ros__parameters of the compiled params file ({} without one)., {launch arg: "true"|"false"} for the TF switches the params set; absent ones…, (t, q) of the inverse of the pose x y z + intrinsic ZYX roll pitch yaw: t =… (+12 more)

### Community 24 - "ZED SDK Rig"
Cohesion: 0.14
Nodes (15): resolve_vehicle_usd(), attach_zed_sdk(), publish_imu(), ZED Mini twin streamed into the REAL ZED SDK (scenario `sensors.zed.enabled`,…, Physically-simulated IMU on `{body_path}/zed_imu_link`, published on…, Feed the physics IMU to the streamed ZED at the physics rate (the extension…, Author one translate + one orient op (wxyz) so the body starts exactly where…, Orient the streamed Imu_Sensor prim by `rpy` (sensors.zed.stream_imu_rpy),… (+7 more)

### Community 25 - "ZED Node and Video"
Cohesion: 0.14
Nodes (14): Context, What every module needs to know: namespaces and a way to reach the others., main(), python3 -m zed_stack.bridge — the px4_bridge service (compose `zed-bridge`).…, ROS 2 image topics -> RTP/H.264 over UDP, for QGroundControl's "UDP h.264 Video…, gi, gi_repository, rclpy_node (+6 more)

### Community 26 - "Drift Correction Design"
Cohesion: 0.12
Nodes (20): Staged plan: layer, compass, wall offsets, loop closure, reset_counter, ICP, Ramped correction layer between ZED odom and MAVROS, Research note: feeding vision drift corrections into PX4 EKF2, EV height fusion and height bias estimator, EV position bias estimator (GNSS-only), EV quality field / EKF2_EV_QMIN, EV reset_counter (teleport signal in EKF2), EV velocity fusion (ev_vel_control.cpp) (+12 more)

### Community 27 - "Structural Regularity Research"
Cohesion: 0.12
Nodes (20): Atlanta world (gravity + multiple horizontal headings), CPA-SLAM, Research note: structural regularity (Manhattan/planar) constraints, Doer & Trommer yaw-aided radar-inertial odometry, ICL-NUIM synthetic benchmark (optimistic), Globally optimal Manhattan frame estimation (Joo), Kaess infinite-plane SLAM parameterisation, Manhattan frame / Manhattan world rotation (+12 more)

### Community 28 - "PX4 Bridge CLI"
Cohesion: 0.16
Nodes (5): subprocess, bridge(), compose_service(), Px4BridgeCli, ./bisg px4-bridge: one compose service (px4-bridge), PX4_BRIDGE picks what its…

### Community 29 - "Drift Analysis"
Cohesion: 0.13
Nodes (9): Bench, Drift, main(), {src: (horizontal error m, yaw error deg)} of each source's displacement since…, Move the position setpoint from where it is to (x, y) (start-relative) at…, summarize(), wrap(), yaw_of() (+1 more)

### Community 30 - "Manhattan Drift Results"
Cohesion: 0.12
Nodes (19): Conclusion: drift is an unobserved DoF, not missing back end, Open: Manhattan yaw accuracy from ZED stereo depth, L-SLAM linear RGB-D SLAM for planar environments, LPVO low-drift VO decoupling rotation (Kim 2018), OPVO drift-free rotation VO (Kim 2017), Rotation drift is the main source of VO position error, Open: validate compass on the real camera, TODO live list (+11 more)

### Community 31 - "Debug Script"
Cohesion: 0.26
Nodes (18): cmd_clean_all(), cmd_clean_cache(), cmd_dds(), cmd_echo(), cmd_gpu(), cmd_hz(), cmd_kitlog(), cmd_mavlink() (+10 more)

### Community 32 - "Hover and Params Tests"
Cohesion: 0.16
Nodes (12): Follow camera for the GUI viewport, in the spirit of Gazebo's "follow" mode:…, pymavlink, encode(), load_params(), main(), Push PX4 EKF2/GPS params over MAVLink (Phase 3 — GPS-denied flight on ZED Mini…, PX4/MAVLink PARAM_SET always carries a float32 on the wire; non-REAL32 types…, Position-hold test (GPS scenario, e.g. single_iris_nozed): arm -> takeoff to… (+4 more)

### Community 33 - "Isaac 6.0 Migration Errors"
Cohesion: 0.12
Nodes (18): Isaac Sim 6.0 migration errors, bugs.md long-lived product bugs (B4, B9, B18), headless_fast 132-137 steps/s vs 317 on 5.1, isaac-cache-kit volume (/isaac-sim/kit/cache), M1 PX4 v1.16.0 SITL build IndexError, M12 Deprecated APIs still in use, M19 Environment loading semantics changed, M6 Shader cache not persisted (190 s boot) (+10 more)

### Community 34 - "ZED Tracking and Area Memory"
Cohesion: 0.14
Nodes (18): Stage 0: confirm no loop-closure odom reset, EVA_NOISE as variance, REP 105 odom continuity / map->odom jumps, ZED wrapper reset_odom_with_loop_closure default true, Freeze survey map then localize, Map corrupted by its own drift, Scan Context place recognition, cuVSLAM / isaac_ros_cuvslam, Jetson Orin compute figures for VSLAM (+10 more)

### Community 35 - "Optical Flow and ToF Twins"
Cohesion: 0.13
Nodes (17): Baro as EKF2 height reference, dist_bottom_valid never true with EKF2_HGT_REF=2, Downward ToF rangefinder + optical flow (sim twin), ekf2_flow_range.params / ekf2_vio_flow_range, EKF2_MIN_RNG 0.10 fix for takeoff offset, GPS-denied mode: ZED + LW20 + PMW3901 + baro, Ground truth via HIL_STATE_QUATERNION on PX4 clock, LW20/C ToF rangefinder twin (DISTANCE_SENSOR) (+9 more)

### Community 36 - "Drift Plots"
Cohesion: 0.23
Nodes (16): matplotlib, matplotlib_pyplot, drift_rows(), fig_drift_error(), fig_drift_paths(), fig_kinetix(), fig_kinetix_error(), kinetix_error() (+8 more)

### Community 37 - "Tailscale Script"
Cohesion: 0.32
Nodes (16): backend(), connected(), follow(), host_cmd(), host_field(), host_json(), host_mode(), host_operator() (+8 more)

### Community 38 - "Foxglove Layouts"
Cohesion: 0.22
Nodes (13): grid(), image(), kinetix(), path_script(), plot(), raptor(), Writes the /drone_1 layouts for the Lichtblick web UI (Foxglove format) next to…, nav_msgs/Path of `src` (a PoseStamped in map), one point per 5 cm, restarted… (+5 more)

### Community 39 - "Asset Pipeline Tools"
Cohesion: 0.13
Nodes (12): CAD (STEP) -> raw USD with the Isaac CAD Converter (HOOPS), plus a part…, intrinsics(), Probe: can the real ZED SDK give depth for TELEPORTED views (Kinetix view…, The extension authors the ZED_M optics on the camera prims once it streams:…, isaacsim, isaacsim_core_utils_extensions, omni_converter_hoops, omni_replicator_core (+4 more)

### Community 40 - "Offboard"
Cohesion: 0.21
Nodes (7): main(), Offboard, Descend at DESCENT_M_S until PX4 detects ground contact, then disarm; True once…, m: a connected mavutil link with target_system/component set; on_msg(msg) sees…, Read messages for `seconds` (wall), streaming the current setpoint at 20 Hz., Arm in OFFBOARD and climb to `alt` m above the start position; True once…, main()

### Community 41 - "mosaic.py"
Cohesion: 0.13
Nodes (12): cv2, confidence_to_bgr(), depth_to_bgr(), label(), Image functions of the 2x2 QGC video (services.qgc_video, layout: grid). No…, Tile (w, h) for a mosaic `width` px wide: half of it, the source's aspect…, A sensor_msgs/Image of a colour encoding -> BGR uint8 resized to size=(w, h);…, A depth Image (32FC1 metres or 16UC1 mm) -> BGR colour map at size=(w, h). NaN… (+4 more)

### Community 42 - "single_iris scenario"
Cohesion: 0.14
Nodes (14): Gazebo-style follow camera, Iris thrust curve/airframe placeholder for raptor, Performance knobs (perf block), 120 Hz physics (= PX4 IMU rate), /clock sim time publication, single_iris scenario, Iris quadrotor scenario vehicle, 120 Hz physics (6 steps per 20 Hz render) (+6 more)

### Community 43 - "VideoStream"
Cohesion: 0.20
Nodes (5): main(), Node, The tile of one source: re-decoded when a new frame arrived, a 'no signal'…, VideoStream, Image

### Community 44 - "Frame-to-model / scan-to-map registratio"
Cohesion: 0.16
Nodes (15): Report: Anchor heading to walls before closing loops, Absolute wall-derived yaw beats loop closure for exploration drones, BundleFusion, Research note: map-based depth localization against own map, ElasticFusion, FAST-LIO2, Frame-to-model / scan-to-map registration, KinectFusion (+7 more)

### Community 45 - "vio_campaign.py (./bisg vio bench / chec"
Cohesion: 0.15
Nodes (15): tests/vio_eval.py reset_counter tally (always 0 on MAVROS), B18 SDK connects once per sim run, docs/data/vio_campaigns.json export, vio_campaign.py (./bisg vio bench / check), VIO campaign: purpose, method, results, vio_bench flight profile (26 m, ~133 s airborne), Fresh sim per flight (B18), Infra failures retried, not counted as VIO failures (+7 more)

### Community 46 - "px4_bridge service (zed-bridge)"
Cohesion: 0.14
Nodes (14): R4 bridge subscribes to depth twice, R8 global /uas1 router topics, Data flow A: flight control via setpoints, Data flow B: ZED to PX4 bridge, MAVROS lean plugin allowlist (mavros_lean.yaml), mavros_router + mavros_node + plugins, /zed_px4_bridge (health, obstacle_distance, odometry), Bridge CPU: shared depth subscription (+6 more)

### Community 47 - "zed-ros2-wrapper fork local (60f78bd, up"
Cohesion: 0.16
Nodes (14): ./bisg setup one-command setup, Workstation setup, Docker data-root on large disk, First run sequence (config, up, smoke, mavros), Host prerequisites (driver, Docker, nvidia-toolkit), bisg/sim builds from Pegasus submodule, Pinned upstream sources, Local edits on a local submodule branch, push to fork first (+6 more)

### Community 48 - "range_flow.py"
Cohesion: 0.15
Nodes (9): carb, Per-step speed-ups for Pegasus on Isaac Sim 6.0 (docs/performance.md,…, Downward ToF rangefinder + optical-flow sensor for a vehicle, fed straight to…, install(), __init__(), Real-time factor (sim seconds per wall second) as one more line of Kit's own…, logging, pegasus_simulator_logic_backends_backend (+1 more)

### Community 49 - "Component choices and version pins table"
Cohesion: 0.23
Nodes (12): Isaac Sim 6.0 stack (Python 3.12, Pegasus PR #144 fork, PX4 v1.17.0), Real ZED SDK runs in the sim via zed-isaac-sim extension, Migration gate checks (smoke, vio_flight, zed_depth_box, zed test, vio check), ZED SDK image build (desktop and jetson variants, CycloneDDS overlay), ADR-011: zed-ros2-wrapper pinned to upstream master / fork local branch, R9: wrapper abort 'can't compare times with different time sources', zed-ros2-wrapper fork branch 'local' (60f78bd = b19902d + PR #463), CycloneDDS everywhere, zenoh across WiFi (ADR-004) (+4 more)

### Community 50 - "terminate_bt.cpp"
Cohesion: 0.18
Nodes (10): cstdio, cstdlib, cxxabi, handler(), print_backtrace(), exception, execinfo, pthread (+2 more)

### Community 51 - "zed_depth_box.py"
Cohesion: 0.18
Nodes (9): raptor_summary.json (CoM, inertia, mounts), raptor.usd, Raw CAD USD (docker/sim/tools/step_to_usd.py) -> Pegasus-ready vehicle USD.…, CAD-FLU point -> body frame (origin at the centre of mass)., rel(), main(), quat_xyzw_to_matrix(), ZED depth check against a known box (scenario `world.objects`, e.g.… (+1 more)

### Community 52 - "chase_cam.py"
Cohesion: 0.20
Nodes (9): ChaseCam, Chase camera of a vehicle as a ROS 2 image (scenario `sensors.chase_cam`,…, `dt`: sim seconds between two update() calls (the rendering step), for the…, Move the camera to this frame's chase pose (call once per rendered frame)., _wrap(), isaacsim_core_experimental_utils_app, omni_graph_core, omni_usd (+1 more)

### Community 53 - "FollowCam"
Cohesion: 0.35
Nodes (3): FollowCam, Put the camera at `offset` in the drone's body frame, looking at it., _wrap()

### Community 54 - "Horizontal EKF2 error vs distance flown "
Cohesion: 0.24
Nodes (11): drift_error.png (horizontal error and heading error figure), 3 m abort threshold, Compass v2 + ZED velocity: landed, 358 m, Compass v3 + ZED velocity (shipped): landed, 359 m, Compass + ZED position fused: aborted in lap 5, 322 m, EKF2 heading error held near 0 by compass, Heading error vs sim time in shipped run (chart), Horizontal EKF2 error vs distance flown (chart) (+3 more)

### Community 55 - "Performance and profiling"
Cohesion: 0.20
Nodes (11): M20 performance.md is 5.1-era, Performance and profiling, Hover stability vs physics_dt (60 Hz wobbles, 120 Hz stable), Measuring: debug perf, debug gpu, boot time, kitlog, Tracy, NVIDIA Simulation Performance Optimization Handbook (upstream reference), perf: block knobs (limit_cpu_threads, skip_material_loading, min_frame_rate, physx_threads...), 120 Hz physics rationale, physics_dt also sets PX4 sensor and MAVLink rate (+3 more)

### Community 56 - "zed-isaac-sim v5.2.1 extension (529e538)"
Cohesion: 0.20
Nodes (11): Five links that do not use ROS, ZED SDK in sim setup (fetch_sources, zed build, zed image), zed-isaac-sim v5.2.1 extension (529e538), Open: why the sim ZED slips in the south-west, tests/yaw_wrap_test.py clean-hover reference, The real ZED SDK in the sim, ZED asset FixedJoint mount to vehicle body, Isaac 5.1 has no ZED Mini twin (+3 more)

### Community 57 - "WebView"
Cohesion: 0.22
Nodes (5): Serve the viewport as a still image over one TCP port. The WebRTC client needs…, Issue one viewport capture if the interval has elapsed. Never raises., WebView, do_GET(), _send()

### Community 58 - "Long-flight drift test figure (5 laps of"
Cohesion: 0.31
Nodes (10): Long-flight drift test figure (5 laps of 12x20 m at 2 m, 1 m/s, 360 deg sweep per lap), Compass (magnetic heading) aiding of EKF2 yaw to bound drift, Compass v2 + ZED velocity (landed, 358 m; EKF2 max 2.04 m, raw ZED max 36.0 m), Compass v3 + ZED velocity, shipped (landed, 359 m; EKF2 max 1.76 m, raw ZED max 40.7 m), Compass, ZED position fused (aborted in lap 5 at 322 m; EKF2 max 3.53 m, raw ZED max 33.8 m), EKF2 estimate (what the drone flew on) stays close to ground truth, Ground truth trajectory, No compass, ZED velocity + yaw (control, aborted after 36 m; EKF2 max 3.73 m, raw ZED max 4.4 m) (+2 more)

### Community 59 - "Camera renders dominate sim cost"
Cohesion: 0.20
Nodes (10): M8 update 2026-10-14: bottleneck moved to camera renders, Camera renders dominate sim cost, Chase cam rate_hz 10 Hz default (sensors.chase_cam.rate_hz), py-spy: 82% of main thread in simulation_app.update(), Pegasus ~10%, Multi-tick rendering (omni:sensor:tickRate), View mode (window, WebRTC) costs < 8%, headless+webrtc ~11%, Workstation A (RTX 4500) RTF table, Workstation B measurements (RTF 0.72 headless) (+2 more)

### Community 60 - "M8 Sim speed fell 1.18x to 0.33x"
Cohesion: 0.22
Nodes (10): M8 Sim speed fell 1.18x to 0.33x, pegasus_fast.py partial fix (RTF 0.44 to 0.54 GUI, 0.85 headless), Pegasus per-step Python: 6 RigidPrim calls, warp array construction, Online asset-root lookup delays boot (get_assets_root_path), Boot sims one at a time (concurrent Kit boot segfaulted/hung), Upstream IsaacSim issue #504 and Pegasus #111/#79, 8 drones as two sims, one per GPU: rtf 0.67 vs 0.40, pegasus_fast.py runtime patch (cached prims, batched force call) (+2 more)

### Community 61 - "config calibrated (shipped GPS-denied mo"
Cohesion: 0.27
Nodes (10): EKF2_EV_CTRL bits (pos, hgt, vel, yaw), Velocity + yaw only EV fusion (EKF2_EV_CTRL 12), vio_bench ablation EV_CTRL 12, PX4 VIO docs: use vision velocity when positions disagree, Velocity-only fusion as robust fallback, ev_compass.params (EKF2_EV_CTRL 12), config calibrated (shipped GPS-denied mode), config ev_position (EKF2_EV_CTRL 13) (+2 more)

### Community 62 - "bag.sh"
Cohesion: 0.49
Nodes (9): current(), newest(), resolve(), ros_up(), running(), bag.sh script, start(), status() (+1 more)

### Community 63 - "info.sh"
Cohesion: 0.33
Nodes (6): each(), listening(), row(), info.sh script, sub(), ts_json()

### Community 64 - "Vehicle interface contract (ROS 2 topics"
Cohesion: 0.28
Nodes (9): Docker-first: every runtime component has a Dockerfile/compose service (ADR-002), CLAUDE.md project instructions, Compose profiles (sim, sim-headless, ros, tools, px4-bridge, zed, drone, tailscale), Contract parity checks (tests/check_contract.py, zed_sdk_check.py), Vehicle interface contract (ROS 2 topics, frames, namespaces identical sim and hardware), Digital twin goal: develop in Isaac Sim, deploy unchanged to Jetson+Pixracer+ZED, Docker strategy (bisg/sim, bisg/ros, bisg/zed image families), Target architecture (sim container, ros containers, Jetson drone containers) (+1 more)

### Community 65 - "zed.yaml: single config for everything t"
Cohesion: 0.28
Nodes (9): Settings layering (bisg.conf, zed.yaml, docker/.env, scenario YAML), compose service drone-zed (ZED wrapper on real camera), compose services sim / sim-headless (Isaac Sim + PX4 SITL), compose service zed (ZED wrapper against sim twin), compose service zed-video (RTP/H.264 to QGroundControl), zed.yaml: single config for everything the ZED does, Four config files, each answering a different question, Settings precedence (flag, env, docker/.env, bisg.conf, fallbacks) (+1 more)

### Community 66 - "px4-bridge/entrypoint.sh"
Cohesion: 0.31
Nodes (7): mavros(), mavsdk(), entrypoint.sh script, xrce(), ext_setup_bash, ext_setup_zsh, host_ros_env.sh script

### Community 67 - "PX4 v1.17.0 pin"
Cohesion: 0.22
Nodes (9): ADR-003 One PX4 tag for SITL and Pixracer, MAVROS 2.15.1, Pegasus PR #144 head fcb99c0, px4_fmu-v4_default Pixracer firmware (95.3% flash), PX4_TAG Dockerfile arg, Re-validation on Isaac Sim 6.0 (2026-10-02), Selection procedure (Phase 1), PX4 v1.16.0 fallback (+1 more)

### Community 68 - "Four error sources of the IMU-less sim S"
Cohesion: 0.28
Nodes (9): Empty Warehouse keep_only / drop locator keys, Ablation study 2026-10-15 (6 configs x 3 flights), SDK tracking events (slip at gap, pose jump, yaw slip), Simple Room vs Warehouse SDK event rate (9/18 vs 1/36), Warehouse world, lamps x0.5 + ambient 2, Yaw rate drives yaw slips; MC_YAWRATE_MAX 60, Four error sources of the IMU-less sim SDK tracking, Frame gaps while moving tilt SDK world frame (+1 more)

### Community 69 - "check_contract.py"
Cohesion: 0.28
Nodes (8): importlib, pathlib, rclpy_time, main(), parse_contract(), parse_rate(), Phase 3 exit test (docs/roadmap.md): the live ROS graph of drone N against…, Rows of the 'provided by the vehicle' table: dicts topic, type, rate (lo, hi Hz…

### Community 70 - "zed.sh"
Cohesion: 0.44
Nodes (8): have_frames(), zed.sh script, start_services(), svc_name(), video_hint(), video_ip(), ZED_SIM_PORT, zexec()

### Community 72 - "Archive"
Cohesion: 0.36
Nodes (3): Archive, archived(), The 2026-10-15 flights (docs/vio.md, archive/vio-2026-10-15/README.md).…

### Community 73 - "Fake"
Cohesion: 0.22
Nodes (4): Fake, main(), Node, spin_for()

### Community 74 - "ADR-010 Pegasus fork"
Cohesion: 0.39
Nodes (7): ADR-010 Pegasus fork, Pegasus fork akashshingha850/PegasusSimulator branch local, Pegasus PR #144 (Isaac Sim 6.0 port), PEGASUS_TAG=local-<sha> pin form, Push to fork before superproject commit, clone(), fetch_sources.sh script

### Community 75 - "ORB-SLAM3"
Cohesion: 0.25
Nodes (8): Basalt, DROID-SLAM / DPV-SLAM / MAC-VO (learned), False loops from perceptual aliasing, Kimera-VIO / Kimera-RPGO, OpenVINS, ORB-SLAM3, PCM / robust pose-graph outlier rejection, VINS-Mono / VINS-Fusion

### Community 76 - "/drone_1/zed/zed_node (real ZED SDK wrap"
Cohesion: 0.25
Nodes (8): The ROS 2 graph: which node does what, R1 two publishers on zed imu/data, R2 publish_map_tf ignored by stock launch (fixed), R9 wrapper time-source crash (fixed 2026-10-21), Measured TF tree vs the contract, /video_stream QGC mosaic sender, /drone_1/zed/zed_node (real ZED SDK wrapper), qgc_video service 2x2 mosaic

### Community 77 - "Sim ZED fuses high-rate IMU (ingest_imu "
Cohesion: 0.29
Nodes (8): Sim ZED GEN_1 experiment (superseded), Sim ZED fuses high-rate IMU (ingest_imu patch, StreamImuFeeder), Streamed ZED Mini IMU 90 deg rolled (fixed, STREAM_IMU_RPY), High-rate IMU in stream (ingest_imu, gen-2 streaming), What differs from the real drone, bisg zed check / zed_sdk_check.py, sim: block - only sim vs Jetson deltas, zed test / check / bench checks

### Community 78 - "main()"
Cohesion: 0.29
Nodes (3): main(), spin(), wait()

### Community 79 - "zed_sdk_check.py"
Cohesion: 0.36
Nodes (6): main(), path_length(), rate(), ZED SDK contract + health check — the same script for the sim and the real…, RMSE (m) of the SDK odometry against ground truth after the only alignment that…, trajectory_rmse()

### Community 80 - "sim.yaml: the one file locating scenario"
Cohesion: 0.38
Nodes (7): GPS-denied sim default (baro + LW20 + ZED VIO + PMW3901), ekf2_vio_flow_range overlay (real drone GPS-denied mode), ev_compass overlay (ZED velocity + yaw from Manhattan compass), PX4 parameter files (vehicle files + mode overlays), sim.yaml: the one file locating scenario, vehicle, world, PX4 params, Offboard-loss failsafe open issue while GPS-denied, PX4 parameters for the real drone (EKF2 EV, GPS-denied, failsafes)

### Community 81 - "mission_square.py"
Cohesion: 0.38
Nodes (6): log(), main(), mission_square — Phase 2 exit test (docs/roadmap.md): take off, fly a square,…, use_sim_time_if_clock(), rclpy_parameter, rclpy_utilities

### Community 82 - "Per-drone bill of materials (Pixracer, O"
Cohesion: 0.29
Nodes (7): Raptor placeholder mass groups and inertia (build_raptor.py), Raptor sensor mounts (ZED twin, LW20 ToF), Raptor 5-inch cinewhoop vehicle definition, Per-drone bill of materials (Pixracer, Orin NX, ZED Mini, LW20), Wiring: Pixracer TELEM2 to Orin NX UART, ZED Mini USB 3, ZED Mini model table (baseline 63 mm, HD720, FOV, mount pose), PX4 v1.17.0 for SITL and Pixracer (ADR-003)

### Community 83 - "headless_fast.yaml scenario"
Cohesion: 0.33
Nodes (7): headless_fast.yaml scenario, app.render: false, world preset Default Environment, Iris vehicle id 0 (ros2 disabled), perf.skip_material_loading, app.stream: off, sensors.zed.enabled: false

### Community 84 - "App"
Cohesion: 0.33
Nodes (4): App, main(), phase(), Boot-phase timing: `[launch] INFO boot +NNs: <what>` (where the cold/warm boot…

### Community 85 - "apply()"
Cohesion: 0.43
Nodes (6): apply(), apply_force(), apply_torque(), handle_propeller_visual(), _prim(), update()

### Community 86 - "RTX 2080 Ti measurements (2026-09-13)"
Cohesion: 0.29
Nodes (7): Async rendering is not a lever, CPU governor powersave but intel_pstate EPP performance, Handbook flags tried: fabricUpdate off, numThreads=0, asyncRendering hang, Render cadence fix (2026-09-13): one frame per rendering_dt/physics_dt steps, RTF HUD in GUI (rtf_hud.py, app.viewport_hud), RTX 2080 Ti measurements (2026-09-13), A second GPU / NVENC is not a lever for one sim

### Community 87 - "v1.17 EKF2_EVA_NOISE unsquared yaw varia"
Cohesion: 0.29
Nodes (7): EKF2_EV_NOISE_MD noise floor semantics, v1.17 EKF2_EVA_NOISE unsquared yaw variance quirk, Yaw oscillation with EKF2_EVA_NOISE 0.1, EKF2_EVA_NOISE 0.01 calibration, Yaw oscillation with EVA_NOISE 0.1 (2/18 vs 0/36 flights), EKF2 heading lagging ZED (EVA_NOISE quirk), config no_eva_fix (EKF2_EVA_NOISE 0.1)

### Community 88 - "Degeneracy detection via Hessian eigen-a"
Cohesion: 0.33
Nodes (7): Colored ICP photometric term, Degeneracy detection via Hessian eigen-analysis, Hatleskog & Alexis probabilistic degeneracy detection, Stereo depth noise grows with z^2, Tuna et al. degeneracy mitigation field study, X-ICP localizability-aware registration, Zhang-Kaess-Singh degeneracy solution remapping

### Community 89 - "docker/zed/zed.yaml single config (ADR-0"
Cohesion: 0.33
Nodes (7): Jetson Orin NX deployment steps, Porting to the Jetson, zed_drone.launch.py shared by sim and Jetson, The ZED Mini stack, SDK module blocks (camera, depth, positional_tracking, ...), zed_stack compile/validate against wrapper YAML, docker/zed/zed.yaml single config (ADR-008)

### Community 90 - "px4-bridge.sh"
Cohesion: 0.38
Nodes (3): pcompose(), px4-bridge.sh script, stop()

### Community 92 - "Topics provided by the vehicle (mavros/*"
Cohesion: 0.40
Nodes (6): MAVROS as the PX4-ROS2 bridge (ADR-001), compose service px4-bridge (mavros|mavsdk|xrce|none), MAVROS lean plugin allowlist, zed.yaml depth block (NEURAL_PLUS, confidence map, point cloud), Topics provided by the vehicle (mavros/*, zed/zed_node/*, chase/image, vehicle/state), QoS conventions (SensorDataQoS, reliable transient-local)

### Community 93 - "load_scenario()"
Cohesion: 0.33
Nodes (5): expand_locator(), load_scenario(), merge(), The locator keys of docker/sim/sim.yaml (what the sim runs) -> the plain…, Read a scenario YAML. `extends: <file>` or a list of files (relative to this…

### Community 94 - "ZED module test + benchmark"
Cohesion: 0.33
Nodes (6): ZED module test + benchmark, 16/16 phases pass (1 warning), zed-bridge container cost (0.31 cores), RAM is the real constraint on Orin NX, Second workstation split GPUs (SIM_GPU=0 ZED_GPU=1), Streaming server crashes wrapper in sim (B19)

### Community 97 - "TF frame tree (map, odom, zed_camera_lin"
Cohesion: 0.40
Nodes (5): compose service zed-bridge (ZED output to PX4 via MAVROS), zed.yaml positional_tracking block (GEN_3 VIO, IMU fusion, odom TF), B16 gap: drone_<n>/ frame prefix the real wrapper cannot publish, mavros/odometry/out fed by zed-bridge odometry module into PX4 EKF2, TF frame tree (map, odom, zed_camera_link, base_link)

### Community 98 - "Raptor USD build pipeline (STEP -> USD -"
Cohesion: 0.40
Nodes (5): docker/sim/assets README, Onshape-to-FLU frame convention, Raptor USD build pipeline (STEP -> USD -> raptor.usd), Raptor 5in cinewhoop vehicle (Pegasus vehicle), docker/sim/tools/step_to_usd.py (CAD Converter)

### Community 99 - "sim/entrypoint.sh"
Cohesion: 0.50
Nodes (4): isaac_python_exec(), ROS_DISTRO, entrypoint.sh script, SIM_CONFIG

### Community 100 - "zed_sdk_cfg.py"
Cohesion: 0.40
Nodes (3): ext_folder(), Stdlib-only half of the ZED SDK mode (zed_sdk_rig.py): decisions that launch.py…, Folder holding the built extension (docker/zed/build_isaac_ext.sh). Checked…

### Community 101 - "Kinetix explore paths figure (Warehouse,"
Cohesion: 0.70
Nodes (5): Kinetix explore paths figure (Warehouse, 28 views, ~5 min, top view, ground truth vs EKF2), Before: no compass, ZED position (two runs: EKF2 max 1.50 m / worst wall 2.41 m; EKF2 max 2.73 m / worst wall 4.11 m), Compass + ZED velocity (two runs: EKF2 max 0.98 m / worst wall 0.66 m; EKF2 max 0.62 m / worst wall 1.04 m), EKF2 pose (what Kinetix maps and flies on) vs ground truth, Warehouse walls (dashed boundary, about 19.5 x 30 m)

### Community 102 - "EKF2_EVP_GATE per-axis 5-sigma innovatio"
Cohesion: 0.50
Nodes (5): EKF2 v1.17 step handling table (gate / 1 s reset / stop), EKF2_EVP_GATE per-axis 5-sigma innovation gate, 1 s fusion-failing reset, 5 in-air resets then stop, Chi-square / Mahalanobis gating and robust filters, Switchable constraints / robust pose-graph back ends

### Community 103 - "check_env.sh"
Cohesion: 0.70
Nodes (4): die(), pass(), check_env.sh script, wrn()

### Community 104 - "drone.sh"
Cohesion: 0.50
Nodes (3): drone.sh script, ZED_STACK_SIM, zexec()

### Community 105 - "Debugging symptom-to-command table"
Cohesion: 0.50
Nodes (4): compose service ros (dev shell, bag recording), PX4 shell without QGC (./bisg debug px4), rosbag2/MCAP recording profiles (flight, vision, all), Debugging symptom-to-command table

### Community 106 - "rosbag2 recording config (bag.yaml)"
Cohesion: 0.67
Nodes (4): bag profile: all, rosbag2 recording config (bag.yaml), bag profile: flight, bag profile: vision

### Community 107 - "ROS GUI/debug tools config (tools.yaml)"
Cohesion: 0.50
Nodes (4): ROS GUI/debug tools config (tools.yaml), foxglove tool (bridge + web UI), rqt tool, rviz tool

### Community 108 - "single_iris_flow scenario"
Cohesion: 0.67
Nodes (4): single_iris_flow scenario, ekf2_flow_range.params overlay, tests/flow_hold.py, GPS-denied on ToF + optical flow (no ZED)

### Community 109 - "Kinetix explore: EKF2 error over the fli"
Cohesion: 0.67
Nodes (4): Kinetix explore: EKF2 error over the flight (figure), Before: no compass, ZED position (EKF2 max 1.50 m and 2.73 m, worst wall 2.41 m and 4.11 m), Compass + ZED velocity (EKF2 max 0.98 m and 0.62 m, worst wall 0.66 m and 1.04 m), EKF2 horizontal error vs ground truth over wall-clock minutes (sim ~0.55x)

### Community 110 - "~200 MB/s camera traffic, lazy computati"
Cohesion: 0.50
Nodes (4): ~200 MB/s camera traffic, lazy computation, R5/R6 RViz and video load, net.core.rmem_max UDP buffer requirement for ZED topics, Troubleshooting: UDP rmem, port 30000, single connect

### Community 111 - "main()"
Cohesion: 0.67
Nodes (3): main(), pump(), wait()

### Community 113 - "Foxglove/Lichtblick layouts raptor.json "
Cohesion: 0.67
Nodes (3): compose service lichtblick (Foxglove-compatible web UI), Foxglove/Lichtblick layouts raptor.json and kinetix.json, Kinetix layout user scripts (path_ekf2, kinetix_track, kinetix_flight)

### Community 115 - ".bench.yaml (derived ZED bench config)"
Cohesion: 0.67
Nodes (3): .bench.yaml (derived ZED bench config), Bench depth mode NEURAL_LIGHT, HD720 (vs NEURAL_PLUS HD1080 in zed.yaml), Derived bench config (python3 -m zed_stack derive; do not edit)

## Knowledge Gaps
- **232 isolated node(s):** `ROS_DOMAIN_ID`, `ros_env.sh script`, `install_host_ros.sh script`, `entrypoint.sh script`, `pull_images.sh script` (+227 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 651 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **43 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Jump gate (experimental, off, fails closed-loop)` connect `Drift Correction Design` to `Jump Gate`?**
  _High betweenness centrality (0.137) - this node is a cross-community bridge._
- **Why does `single_iris scenario` connect `single_iris scenario` to `Scenarios and Known Bugs`, `single_iris_flow scenario`, `Sim Launcher`, `headless_fast.yaml scenario`, `chase_cam.py`, `Performance and profiling`, `ZED SDK Rig`?**
  _High betweenness centrality (0.127) - this node is a cross-community bridge._
- **Why does `mapcorr.py slewed correction (30 deg/s)` connect `Drift Correction Design` to `Manhattan Drift Results`?**
  _High betweenness centrality (0.077) - this node is a cross-community bridge._
- **What connects `ROS_DOMAIN_ID`, `ros_env.sh script`, `install_host_ros.sh script` to the rest of the system?**
  _232 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Jump Gate` be split into smaller, more focused modules?**
  _Cohesion score 0.07207792207792207 - nodes in this community are weakly interconnected._
- **Should `ZED Stack Config` be split into smaller, more focused modules?**
  _Cohesion score 0.06363636363636363 - nodes in this community are weakly interconnected._
- **Should `ZED Benchmark` be split into smaller, more focused modules?**
  _Cohesion score 0.0649895178197065 - nodes in this community are weakly interconnected._