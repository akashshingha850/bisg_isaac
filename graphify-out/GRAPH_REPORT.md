# Graph Report - bisg_isaac  (2026-11-02)

## Corpus Check
- 181 files · ~270,603 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 28 file(s) not represented in the graph (top: (none) 11, .params 4, .xml 2)

## Summary
- 1823 nodes · 3207 edges · 152 communities (108 shown, 44 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 187 edges (avg confidence: 0.84)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- VIO & Range-Flow Evaluation
- Docker Compose & Remote Access
- Shell Env & Isaac Ext Build
- Isaac 6.0 Migration & Performance
- ZED Benchmark
- VIO Campaign & Foxglove
- ZED Obstacle Sectors & Drift Report
- ZED Bridge Health & Obstacles
- VIO Eval/Report Tests
- Map Correction
- Offboard Controller & Flow Bench
- Drift Flight Test
- Jump Gate
- Manhattan Compass
- Sim Launcher
- bisg CLI (launch.sh)
- Jump Gate Tests
- Project Docs & Raptor Vehicle
- VIO Report & Export
- Range-Flow Backend
- MAVROS Sim-Time Tools
- Sim Scenarios & Perf Knobs
- ZED Config & Bench Settings
- Raptor USD Build Pipeline
- ZED SDK Check & Fake Bridge
- Community 25
- Community 26
- Community 27
- Community 28
- Community 29
- Community 30
- Community 31
- Community 32
- Community 33
- Community 34
- Community 35
- Community 36
- Community 37
- Community 38
- Community 39
- Community 40
- Community 41
- Community 42
- Community 43
- Community 44
- Community 45
- Community 46
- Community 47
- Community 48
- Community 49
- Community 50
- Community 51
- Community 52
- Community 53
- Community 54
- Community 55
- Community 56
- Community 57
- Community 58
- Community 59
- Community 60
- Community 61
- Community 62
- Community 63
- Community 64
- Community 65
- Community 66
- Community 67
- Community 68
- Community 69
- Community 70
- Community 71
- Community 72
- Community 73
- Community 74
- Community 75
- Community 76
- Community 77
- Community 78
- Community 79
- Community 80
- Community 81
- Community 82
- Community 83
- Community 84
- Community 85
- Community 86
- Community 87
- Community 88
- Community 89
- Community 90
- Community 91
- Community 92
- Community 93
- Community 94
- Community 95
- Community 96
- Community 97
- Community 98
- Community 99
- Community 100
- Community 101
- Community 102
- Community 103
- Community 104
- Community 105
- Community 106
- Community 107
- Community 108
- Community 109
- Community 110
- Community 111
- Community 112
- Community 113
- Community 114
- Community 115
- Community 116
- Community 117
- Community 118
- Community 119
- Community 120
- Community 121
- Community 122
- Community 123
- Community 124
- Community 125
- Community 126
- Community 127
- Community 128
- Community 129
- Community 130
- Community 131
- Community 132
- Community 133
- Community 134
- Community 135
- Community 136
- Community 137
- Community 138
- Community 140
- Community 141
- Community 142
- Community 143
- Community 144
- Community 145
- Community 146
- Community 147
- Community 148
- Community 149
- Community 150
- Community 151

## God Nodes (most connected - your core abstractions)
1. `JumpGate` - 26 edges
2. `Odometry2Px4` - 19 edges
3. `OffboardController` - 18 edges
4. `RangeFlowBackend` - 18 edges
5. `analyse()` - 18 edges
6. `launch.sh script` - 17 edges
7. `Flight` - 17 edges
8. `single_iris scenario` - 17 edges
9. `Rate` - 16 edges
10. `debug.sh script` - 16 edges

## Surprising Connections (you probably didn't know these)
- `write()` --indirect_call--> `f()`  [INFERRED]
  docker/ros/foxglove/make_layout.py → tests/zed_bench.py
- `Settings precedence (flag > env > docker/.env > bisg.conf > fallbacks)` --semantically_similar_to--> `Settings layering (bisg.conf, zed.yaml, docker/.env, scenario YAML)`  [INFERRED] [semantically similar]
  docs/configuration.md → CLAUDE.md
- `Isaac Sim + Pegasus + PX4 digital twin of Jetson/Pixracer/ZED drone` --semantically_similar_to--> `Isaac Sim 6.0 + Pegasus + PX4 v1.17.0 stack`  [INFERRED] [semantically similar]
  README.md → CLAUDE.md
- `load_scenario()` --indirect_call--> `f()`  [INFERRED]
  docker/sim/launcher/launch.py → tests/zed_bench.py
- `params()` --indirect_call--> `f()`  [INFERRED]
  docker/zed/zed_drone.launch.py → tests/zed_bench.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Raptor CAD to scenario vehicle build flow** — docker_sim_assets_readme_step_to_usd, docker_sim_tools_build_raptor, docker_sim_assets_vehicles_raptor_raptor, docker_sim_assets_readme_raptor_usd, docker_sim_assets_readme_raptor_summary_json, docker_sim_sim [EXTRACTED 1.00]
- **ZED stack: one YAML, one image, three services** — docs_zed_stack_zed_yaml, docs_decisions_adr_008_zed_stack_bisg_zed_image, docs_decisions_adr_008_zed_stack_zed_bridge_service, docs_decisions_adr_008_zed_stack_zed_video_service, docs_decisions_adr_008_zed_stack_zed_stack_compiler [EXTRACTED 0.95]
- **M8 simulation-speed investigation chain** — docs_migration_errors_m8, docs_migration_errors_pegasus_per_step_python, docs_migration_errors_pegasus_fast, docs_migration_errors_camera_bottleneck_update, docs_performance_camera_render_cost [EXTRACTED 1.00]
- **Camera render cost levers (chase cam rate, ZED fps, ZED off)** — docs_performance_chase_cam_rate, docs_performance_zed_twin_cost, docs_performance_zed_15fps_rejected, docs_performance_multi_tick_rendering [EXTRACTED 1.00]
- **Tailscale remote access stack (ADR, compose service, user docs)** — docs_decisions_adr_009_remote_access_tailscale, docker_compose_tailscale, docs_remote_access [EXTRACTED 1.00]
- **How EKF2 v1.17 handles an external-vision jump** — docs_research_research_notes_vio_drift_fixes_for_indoor_drones_ekf_fusion_of_corrections_ev_reset_counter, docs_research_research_notes_vio_drift_fixes_for_indoor_drones_ekf_fusion_of_corrections_evp_gate, docs_research_research_notes_vio_drift_fixes_for_indoor_drones_ekf_fusion_of_corrections_long_rejection_reset, docs_research_research_notes_vio_drift_fixes_for_indoor_drones_ekf_fusion_of_corrections_ev_pos_bias_estimator [EXTRACTED 1.00]
- **Compass/ZED fusion variants compared by horizontal error** — docs_figures_drift_error_no_compass_control, docs_figures_drift_error_compass_zed_position_fused, docs_figures_drift_error_compass_v2_zed_velocity, docs_figures_drift_error_compass_v3_zed_velocity_shipped [EXTRACTED 1.00]
- **Long-flight drift test configurations compared** — docs_figures_drift_paths_no_compass_zed_velocity_yaw, docs_figures_drift_paths_compass_zed_position_fused, docs_figures_drift_paths_compass_v2_zed_velocity, docs_figures_drift_paths_compass_v3_zed_velocity_shipped [EXTRACTED 1.00]
- **Kinetix explore EKF2 drift: before vs after compass + ZED velocity** — docs_figures_kinetix_explore_paths_before_no_compass_zed_position, docs_figures_kinetix_explore_paths_compass_zed_velocity, docs_figures_kinetix_explore_paths_ekf2_pose [INFERRED 0.85]
- **GPS-denied state estimation stack (ZED VIO + LW20 + PMW3901 + raptor.params)** — docker_zed_zed_positional_tracking, docker_sim_assets_vehicles_raptor_raptor_tof_sensor, docker_sim_assets_vehicles_raptor_raptor_optical_flow, docker_sim_px4_readme_raptor_params, docker_zed_zed_manhattan_compass [EXTRACTED 0.95]
- **ZED compose services sharing one image and zed.yaml** — docker_compose_zed, docker_compose_zed_bridge, docker_compose_zed_video, docker_compose_drone_zed, docker_zed_zed [EXTRACTED 0.95]
- **sim.yaml locator composes scenario, vehicle, world and PX4 params** — docker_sim_sim, docker_sim_sim_raptor_scenario, docker_sim_assets_vehicles_raptor_raptor, docker_sim_px4_readme_raptor_params, docker_sim_sim_warehouse_world [EXTRACTED 0.95]
- **PX4 bridge methods behind one px4-bridge service** — docs_px4_bridge_px4_bridge_service, docs_px4_bridge_mavros, docs_px4_bridge_mavsdk, docs_px4_bridge_xrce [EXTRACTED 0.95]
- **GPS-denied EKF2 sensor fusion (ZED VIO, LW20, PMW3901, baro, Manhattan compass)** — docs_vio_zed_to_ekf2_path, docs_range_flow_lw20_tof, docs_range_flow_pmw3901_flow, docs_range_flow_baro_height_reference, docs_vio_drift_manhattan_compass, docs_vio_drift_ev_ctrl_12 [INFERRED 0.85]
- **VIO campaign flow: config, fresh sim flight, eval, verdict** — tests_vio_bench, docs_vio_campaign_vio_campaign, docs_vio_campaign_fresh_sim_per_flight, docs_vio_campaign_flight_eval_metrics, docs_vio_campaign_verdict [EXTRACTED 0.95]

## Communities (152 total, 44 thin omitted)

### Community 0 - "VIO & Range-Flow Evaluation"
Cohesion: 0.06
Nodes (61): best_lag(), binned(), eval_ekf(), eval_flow(), err_at(), expected(), eval_ros(), err_at() (+53 more)

### Community 1 - "Docker Compose & Remote Access"
Cohesion: 0.05
Nodes (46): SIM_VIEW key (gui|headless|web|webrtc|both|auto), Tailscale remote access (ADR-009), compose service tailscale, SIM_VIEW and SIM_VIEW_ADDR, ADR-002 Docker-first including Isaac Sim, bisg/sim, bisg/ros, bisg/zed images, compose profiles sim, sim-headless, ros, jetson, network_mode host everywhere (+38 more)

### Community 2 - "Shell Env & Isaac Ext Build"
Cohesion: 0.07
Nodes (33): build_isaac_ext.sh script, stamp(), _BISG_ENV0, BISG_SRC, conf_default(), container_running(), die(), fail() (+25 more)

### Community 3 - "Isaac 6.0 Migration & Performance"
Cohesion: 0.05
Nodes (43): Isaac Sim 6.0 migration errors, bugs.md long-lived product bugs (B4, B9, B18), M8 update 2026-10-14: bottleneck moved to camera renders, headless_fast 132-137 steps/s vs 317 on 5.1, isaac-cache-kit volume (/isaac-sim/kit/cache), M1 PX4 v1.16.0 SITL build IndexError, M12 Deprecated APIs still in use, M19 Environment loading semantics changed (+35 more)

### Community 4 - "ZED Benchmark"
Cohesion: 0.09
Nodes (32): rosgraph_msgs_msg, rosidl_runtime_py_utilities, std_srvs_srv, Bench, cb(), build_phases(), chk_cloud(), chk_depth() (+24 more)

### Community 5 - "VIO Campaign & Foxglove"
Cohesion: 0.12
Nodes (35): base64, datetime, frame(), need(), What does a Foxglove client see on the foxglove_bridge, and does the data flow?…, shutil, socket, struct (+27 more)

### Community 6 - "ZED Obstacle Sectors & Drift Report"
Cohesion: 0.09
Nodes (24): Depth image -> 72 x 5 deg obstacle sectors. numpy only, so it is unit-testable…, json, numpy, os, statistics, tempfile, load(), main() (+16 more)

### Community 7 - "ZED Bridge Health & Obstacles"
Cohesion: 0.08
Nodes (9): Rate, Messages per second over a sliding window, and how long ago the last one came…, Health, ObstacleDistance, Image, MAVROS defaults the obstacle plugin to GLOBAL; ours is a body-frame (FRD) scan., Depth image (H x W, metres, float32) + pinhole intrinsics -> 72 ranges [m]: inf…, sectors_from_depth() (+1 more)

### Community 8 - "VIO Eval/Report Tests"
Cohesion: 0.10
Nodes (14): flight(), A yaw error rotates positions about the takeoff point; the old whole-flight fit…, w, x, y, z of R = Rz(psi) Ry(pitch) (FRD body -> NED)., A 60 s log as vio_eval reads it. Truth: rest 5 s, climb to 1 m, figure flown…, Synthetic, yaw_quat(), campaign(), dump() (+6 more)

### Community 9 - "Map Correction"
Cohesion: 0.14
Nodes (20): settled(), MapCorrection, qz(), Carry the ZED's map-frame corrections (loop closure, relocalisation) into the…, A map pose and an odom pose of the same camera frame (same stamp)., Heading-only target (the Manhattan compass): turn the correction to `yaw` about…, (m, deg) still to apply at the current odom position., The output pose for an odom sample at time t (s). (+12 more)

### Community 10 - "Offboard Controller & Flow Bench"
Cohesion: 0.18
Nodes (23): argparse, csv, dataclasses, OffboardController — fly drone N through MAVROS from Python (docs/interface-…, geometry_msgs_msg, math, mavros_msgs_msg, mavros_msgs_srv (+15 more)

### Community 11 - "Drift Flight Test"
Cohesion: 0.09
Nodes (10): Drift, main(), {src: (horizontal error m, yaw error deg)} of each source's displacement since…, Move the position setpoint from where it is to (x, y) (start-relative) at…, rot(), summarize(), wrap(), yaw_of() (+2 more)

### Community 12 - "Jump Gate"
Cohesion: 0.11
Nodes (19): collections, add3(), angle_between(), norm3(), qconj(), qmul(), qnorm(), qrot() (+11 more)

### Community 13 - "Manhattan Compass"
Cohesion: 0.14
Nodes (15): Compass, quat_to_R(), Manhattan compass: a drift-free heading from the walls of a box room, in the…, Fold an angle (rad) into [-pi/4, pi/4)., Room axis (rad, in [-pi/4, pi/4)) in the odometry frame from one depth image (H…, Room axis -> yaw drift of the odometry. The reference is the median axis of the…, meas = room_axis(...) result or None. Returns the drift estimate (rad) once the…, room_axis() (+7 more)

### Community 14 - "Sim Launcher"
Cohesion: 0.10
Nodes (23): apply_paths(), apply_px4_params(), drop_world_prims(), keep_only_world_prims(), phase(), Boot-phase timing: `[launch] INFO boot +NNs: <what>` (where the cold/warm boot…, bisg_isaac Pegasus launcher — YAML-driven Isaac Sim standalone app. /isaac-…, Deactivate every top-level prim of the world asset whose name matches none of… (+15 more)

### Community 15 - "bisg CLI (launch.sh)"
Cohesion: 0.19
Nodes (24): bag_close(), cmd_all(), cmd_build(), cmd_config(), cmd_down(), cmd_logs(), cmd_mavros(), cmd_restart() (+16 more)

### Community 16 - "Jump Gate Tests"
Cohesion: 0.17
Nodes (12): JumpGate, random, CleanFlight, err(), FailOpen, fly(), PoseJump, Host-side unit tests for the ZED odometry jump gate (no ROS): python3 -m… (+4 more)

### Community 17 - "Project Docs & Raptor Vehicle"
Cohesion: 0.10
Nodes (24): CLAUDE.md project instructions, GPS-denied sim default (LW20 + baro + ZED VIO + PMW3901), MAVROS is the PX4-ROS2 bridge (ADR-001), docker/sim/assets README, Onshape-to-FLU frame convention, Raptor USD build pipeline (STEP -> USD -> raptor.usd), Raptor 5in cinewhoop vehicle (Pegasus vehicle), docker/sim/tools/step_to_usd.py (CAD Converter) (+16 more)

### Community 18 - "VIO Report & Export"
Cohesion: 0.16
Nodes (23): glob, campaign(), clean(), flight_record(), main(), JSON-safe: NaN/inf -> None, floats rounded., world_of(), build() (+15 more)

### Community 19 - "Range-Flow Backend"
Cohesion: 0.11
Nodes (8): Backend, attach(), ned_to_latlon(), RangeFlowBackend, Range from `mount` (body FLU) straight down the body Z axis to the first…, Return a RangeFlowBackend for a scenario vehicle, or None when neither sensor…, Inverse of PX4's azimuthal-equidistant MapProjection, so PX4's ground-truth…, cfg: the vehicle's `sensors:` block (`tof:` and/or `optical_flow:`); px4: the…

### Community 20 - "MAVROS Sim-Time Tools"
Cohesion: 0.11
Nodes (15): main(), Switch every MAVROS plugin node to use_sim_time:=true (sim stack only,…, Context, Shared pieces of the bridge modules (rclpy only where a function needs a node)., What every module needs to know: namespaces and a way to reach the others., main(), python3 -m zed_stack.bridge — the px4_bridge service (compose `zed-bridge`).…, M2 — ZED depth image -> PX4's 72-sector obstacle map (MAVROS obstacle/send ->… (+7 more)

### Community 21 - "Sim Scenarios & Perf Knobs"
Cohesion: 0.10
Nodes (22): Gazebo-style follow camera, Iris thrust curve/airframe placeholder for raptor, Performance knobs (perf block), 120 Hz physics (= PX4 IMU rate), /clock sim time publication, single_iris scenario, single_iris_flow scenario, ekf2_flow_range.params overlay (+14 more)

### Community 22 - "ZED Config & Bench Settings"
Cohesion: 0.13
Nodes (22): Settings layering (bisg.conf, zed.yaml, docker/.env, scenario YAML), Raptor ZED mount and stream config, keep_only / drop world pruning, .bench.yaml (derived ZED bench config), Bench depth mode NEURAL_LIGHT, HD720 (vs NEURAL_PLUS HD1080 in zed.yaml), Derived bench config (python3 -m zed_stack derive; do not edit), zed.yaml (single ZED config), Depth module (NEURAL_PLUS) (+14 more)

### Community 23 - "Raptor USD Build Pipeline"
Cohesion: 0.10
Nodes (17): raptor_summary.json (CoM, inertia, mounts), raptor.usd, Raw CAD USD (docker/sim/tools/step_to_usd.py) -> Pegasus-ready vehicle USD.…, CAD-FLU point -> body frame (origin at the centre of mass)., rel(), CAD (STEP) -> raw USD with the Isaac CAD Converter (HOOPS), plus a part…, intrinsics(), Probe: can the real ZED SDK give depth for TELEPORTED views (Kinetix view… (+9 more)

### Community 24 - "ZED SDK Check & Fake Bridge"
Cohesion: 0.12
Nodes (15): M10 — ZED health -> one status topic + STATUSTEXT in QGroundControl. Publishes…, nav_msgs_msg, sensor_msgs_msg, std_msgs_msg, subprocess, px4_bridge against FAKE ZED + MAVROS topics — no camera, no sim, no PX4. Runs…, main(), ROS side of the ZED pool-depth probe (docker/sim/tools/zed_pool_probe.py):… (+7 more)

### Community 25 - "Community 25"
Cohesion: 0.18
Nodes (5): OffboardController, MAVROS connected and a local position estimate flowing; fixes the mission…, Stream a hover setpoint `alt` m above the origin, switch to OFFBOARD, arm, wait…, Fly to (x, y, z) m from the origin (z None = keep the current setpoint height);…, Result

### Community 26 - "Community 26"
Cohesion: 0.13
Nodes (20): drone_tf(), generate_launch_description(), inverse_pose(), params(), zed_wrapper for drone N, with the contract's topic names. Used by BOTH the sim…, The ros__parameters of the compiled params file ({} without one)., {launch arg: "true"|"false"} for the TF switches the params set; absent ones…, (t, q) of the inverse of the pose x y z + intrinsic ZYX roll pitch yaw: t =… (+12 more)

### Community 27 - "Community 27"
Cohesion: 0.18
Nodes (15): load(), sim=None: follow $ZED_STACK_SIM (1 = apply the `sim:` deltas) — the containers…, cmd_compile(), cmd_derive(), cmd_plan(), cmd_services(), cmd_set(), main() (+7 more)

### Community 28 - "Community 28"
Cohesion: 0.26
Nodes (18): cmd_clean_all(), cmd_clean_cache(), cmd_dds(), cmd_echo(), cmd_gpu(), cmd_hz(), cmd_kitlog(), cmd_mavlink() (+10 more)

### Community 29 - "Community 29"
Cohesion: 0.17
Nodes (10): importlib, pathlib, rclpy_time, Checker, main(), msg_class(), parse_contract(), parse_rate() (+2 more)

### Community 30 - "Community 30"
Cohesion: 0.13
Nodes (15): Docker-first, one compose file for workstation and Jetson (ADR-002), Sim and hardware obey docs/interface-contract.md, Real ZED SDK runs in the sim via zed-isaac-sim extension (ADR-011), ZED stack configured only by docker/zed/zed.yaml (ADR-008), config/bisg.conf (merged project settings), One key, one place rule, compose service drone-zed (real camera), compose service lichtblick (Foxglove web UI) (+7 more)

### Community 31 - "Community 31"
Cohesion: 0.15
Nodes (14): ext_folder(), Stdlib-only half of the ZED SDK mode (zed_sdk_rig.py): decisions that launch.py…, Folder holding the built extension (docker/zed/build_isaac_ext.sh). Checked…, stream_port(), attach_zed_sdk(), ZED Mini twin streamed into the REAL ZED SDK (scenario `sensors.zed.enabled`,…, Author one translate + one orient op (wxyz) so the body starts exactly where…, Orient the streamed Imu_Sensor prim by `rpy` (sensors.zed.stream_imu_rpy),… (+6 more)

### Community 32 - "Community 32"
Cohesion: 0.13
Nodes (17): BundleFusion, Colored ICP photometric term, Degeneracy detection via Hessian eigen-analysis, Research note: map-based depth localization against own map, ElasticFusion, FAST-LIO2, Frame-to-model / scan-to-map registration, KinectFusion (+9 more)

### Community 33 - "Community 33"
Cohesion: 0.23
Nodes (16): matplotlib, matplotlib_pyplot, drift_rows(), fig_drift_error(), fig_drift_paths(), fig_kinetix(), fig_kinetix_error(), kinetix_error() (+8 more)

### Community 34 - "Community 34"
Cohesion: 0.20
Nodes (12): pymavlink, encode(), load_params(), main(), Push PX4 EKF2/GPS params over MAVLink (Phase 3 — GPS-denied flight on ZED Mini…, PX4/MAVLink PARAM_SET always carries a float32 on the wire; non-REAL32 types…, sys, Position-hold test (GPS scenario, e.g. single_iris_nozed): arm -> takeoff to… (+4 more)

### Community 35 - "Community 35"
Cohesion: 0.32
Nodes (16): backend(), connected(), follow(), host_cmd(), host_field(), host_json(), host_mode(), host_operator() (+8 more)

### Community 36 - "Community 36"
Cohesion: 0.19
Nodes (3): bridge(), compose_service(), Px4BridgeCli

### Community 37 - "Community 37"
Cohesion: 0.17
Nodes (3): Flight, main(), Fly to (dx, dy) from the start point at `alt` m above it; hold `settle` seconds.

### Community 38 - "Community 38"
Cohesion: 0.13
Nodes (11): carb, Follow camera for the GUI viewport, in the spirit of Gazebo's "follow" mode:…, _wrap(), Per-step speed-ups for Pegasus on Isaac Sim 6.0 (docs/performance.md,…, Downward ToF rangefinder + optical-flow sensor for a vehicle, fed straight to…, install(), __init__(), Real-time factor (sim seconds per wall second) as one more line of Kit's own… (+3 more)

### Community 39 - "Community 39"
Cohesion: 0.16
Nodes (16): Isaac Sim 6.0 + Pegasus + PX4 v1.17.0 stack, Regression gate checks (smoke, vio_flight, zed_depth_box, zed test, vio check), Default world: emptied Warehouse for Kinetix photogrammetry, Isaac cache volumes (isaac-cache-kit shader cache), compose services sim / sim-headless, Version pins and source links, SCENES_DIR external scenes (Kinetix) mounted at /scenes, ADR-010 Pegasus from own fork (branch local) (+8 more)

### Community 40 - "Community 40"
Cohesion: 0.22
Nodes (14): grid(), image(), kinetix(), path_script(), plot(), raptor(), Writes the /drone_1 layouts for the Lichtblick web UI (Foxglove format) next to…, nav_msgs/Path of `src` (a PoseStamped in map), one point per 5 cm, restarted… (+6 more)

### Community 41 - "Community 41"
Cohesion: 0.22
Nodes (7): Module master switch. Modules without `enabled` (camera, video, sensors,…, The text of the `ros_params_override_path` file., Enabled px4_bridge modules -> their settings (empty when the bridge itself is…, Names of compose services `./bisg zed up` must run next to the wrapper., StackConfig, _suggest(), _type_ok()

### Community 42 - "Community 42"
Cohesion: 0.15
Nodes (16): /drone_<n> namespace = MAV_SYS_ID, Project plan (doc), ADR-001 MAVROS instead of uXRCE-DDS, ADR-002 Docker-first, Docker strategy: bisg/sim, bisg/ros, bisg/zed, Multi-vehicle ports/IDs/namespaces, NVIDIA driver 580 branch constraint (59x segfaults Isaac), Risk register R1-R10 (+8 more)

### Community 43 - "Community 43"
Cohesion: 0.21
Nodes (7): main(), Offboard, Descend at DESCENT_M_S until PX4 detects ground contact, then disarm; True once…, m: a connected mavutil link with target_system/component set; on_msg(msg) sees…, Read messages for `seconds` (wall), streaming the current setpoint at 20 Hz., Arm in OFFBOARD and climb to `alt` m above the start position; True once…, main()

### Community 44 - "Community 44"
Cohesion: 0.20
Nodes (15): px4-bridge single compose service (PX4_BRIDGE=mavros|mavsdk|xrce|none), compose service px4-bridge, compose service zed-bridge, mavros_plugins.yaml plugin groups, debug MAVROS plugin group (vibration, altitude, vfr_hud, esc_status, log_transfer), lean MAVROS plugin group, PMW3901 optical flow sensor, Lightware LW20 ToF rangefinder sensor (+7 more)

### Community 45 - "Community 45"
Cohesion: 0.13
Nodes (12): cv2, confidence_to_bgr(), depth_to_bgr(), label(), Image functions of the 2x2 QGC video (services.qgc_video, layout: grid). No…, Tile (w, h) for a mosaic `width` px wide: half of it, the source's aspect…, A sensor_msgs/Image of a colour encoding -> BGR uint8 resized to size=(w, h);…, A depth Image (32FC1 metres or 16UC1 mm) -> BGR colour map at size=(w, h). NaN… (+4 more)

### Community 46 - "Community 46"
Cohesion: 0.15
Nodes (5): Odometry2Px4, The wrapper stamps `pose` and `odom` of one grab alike: keep the last few to…, Manhattan compass: one depth image (at <= compass_rate_hz, while not turning)…, pose_source map: `out` (a copy of the odom message `src`) gets the slewed map-…, Run the jump gate on `out` (a copy of the source message, stamped t) in place.

### Community 47 - "Community 47"
Cohesion: 0.20
Nodes (5): main(), Image, Node, The tile of one source: re-decoded when a new frame arrived, a 'no signal'…, VideoStream

### Community 48 - "Community 48"
Cohesion: 0.19
Nodes (15): ADR-005 ROS 2 Jazzy everywhere, Version pins table, R9 wrapper crash: can't compare times with different time sources, Pinned upstream sources (doc), Local-branch-in-submodule workflow, Pegasus fork branch local (PR #144 + fixes), zed-isaac-sim v5.2.1 extension, zed-ros2-wrapper fork local 60f78bd (ADR-011) (+7 more)

### Community 49 - "Community 49"
Cohesion: 0.22
Nodes (11): circ_median(), compare(), main(), Compass comparison: the flight controller's magnetometer vs the ZED heading…, Yaw (ENU) of a body whose roll / pitch is in q, from the field m (base_link…, Median of angles (rad): the plain median around the circular mean, so a wrap at…, samples: {source: [yaw rad]} at common instants. -> {source: (offset deg,…, Rec (+3 more)

### Community 50 - "Community 50"
Cohesion: 0.14
Nodes (14): ZED wrapper topics (zed/zed_node/*), ZED 15 fps rejected (depth box -40 mm, VIO abort), ZED twin is ~2/3 of the RTF gap (two HD720 views), PX4 bridge (doc), Range + optical flow twin (doc), ROS 2 graph (doc), Jetson Orin NX deployment steps, Sim ZED high-rate IMU feed (ingest_imu patch, gen-2 streaming) (+6 more)

### Community 51 - "Community 51"
Cohesion: 0.16
Nodes (14): Range/flow accuracy benchmark with PX4-log ground truth, Dominant SDK event attribution, Per-flight evaluation metrics (vio_eval.py), Ground truth on PX4 clock (groundtruth topics), restamp_latency_ms calibration (scales with RTF), tests/drift_flight.py long-flight test, How corrections reach EKF2 (no reset_counter, no gradual EV offset), EKF2_EV_CTRL 12 (ZED velocity + yaw, no position) (+6 more)

### Community 52 - "Community 52"
Cohesion: 0.23
Nodes (14): Roadmap, Phase 1 Dockerized single-drone sim, Phase 2 ROS 2 + MAVROS control, Phase 3 Sensors, ZED Mini contract, VIO, Phase 4 Digital-twin assets, Phase 5 Hardware single drone, Phase 6 Swarm in sim, Phase 7 Hardware swarm (+6 more)

### Community 53 - "Community 53"
Cohesion: 0.22
Nodes (12): re, command(), load(), main(), Read / toggle docker/ros/bag.yaml (rosbag2 recording, ./bisg bag). ros_bag.py…, The YAML folds the long patterns over several lines: drop the whitespace., regex_of(), squash() (+4 more)

### Community 54 - "Community 54"
Cohesion: 0.19
Nodes (7): App, main(), resolve_vehicle_usd(), publish_imu(), Physically-simulated IMU on `{body_path}/zed_imu_link`, published on…, Feed the physics IMU to the streamed ZED at the physics rate (the extension…, StreamImuFeeder

### Community 55 - "Community 55"
Cohesion: 0.18
Nodes (13): chase/image third-person view (sim only), mavros/odometry/out (VIO to EKF2), /clock sim time, Sim-to-real parity rules, Data flows A-D (control, ZED-to-PX4, views, truth/time), Ground-truth /drone_N/state/* (tests only), ROS 2 node catalogue, ZED odom to EKF2 path (restamp, odometry/out, EV_POS lever arm) (+5 more)

### Community 56 - "Community 56"
Cohesion: 0.18
Nodes (13): Atlanta world (gravity + multiple horizontal headings), CPA-SLAM, Research note: structural regularity (Manhattan/planar) constraints, ICL-NUIM synthetic benchmark (optimistic), Globally optimal Manhattan frame estimation (Joo), Kaess infinite-plane SLAM parameterisation, Manhattan frame / Manhattan world rotation, ManhattanSLAM (Yunus 2021) (+5 more)

### Community 57 - "Community 57"
Cohesion: 0.23
Nodes (10): copy, difflib, ConfigError, deep_merge(), _flatten_params(), docker/zed/zed.yaml -> zed_wrapper parameters + the list of services to start.…, {section: {key: default}} from the wrapper's own YAML files (the model file…, _wrapper_dir() (+2 more)

### Community 58 - "Community 58"
Cohesion: 0.18
Nodes (10): cstdio, cstdlib, cxxabi, handler(), print_backtrace(), exception, execinfo, pthread (+2 more)

### Community 59 - "Community 59"
Cohesion: 0.26
Nodes (12): single_iris_vio scenario, depth_box test cuboid (1 m cube), ekf2_vision.params overlay, GPS-denied VIO scenario (EKF2 external vision), single_iris_vio_lowres scenario, 320x180 ZED low-res variant (fits default rmem_max), ZED odometry -> zed-bridge -> mavros/odometry/out, Known bugs register (+4 more)

### Community 60 - "Community 60"
Cohesion: 0.20
Nodes (9): ChaseCam, Chase camera of a vehicle as a ROS 2 image (scenario `sensors.chase_cam`,…, `dt`: sim seconds between two update() calls (the rendering step), for the…, Move the camera to this frame's chase pose (call once per rendered frame)., _wrap(), isaacsim_core_experimental_utils_app, omni_graph_core, omni_usd (+1 more)

### Community 61 - "Community 61"
Cohesion: 0.18
Nodes (12): EKF2 v1.17 step handling table (gate / 1 s reset / stop), Stage 0: confirm no loop-closure odom reset, EVA_NOISE as variance, Ramped correction layer between ZED odom and MAVROS, Research note: feeding vision drift corrections into PX4 EKF2, EKF2_EV_NOISE_MD noise floor semantics, v1.17 EKF2_EVA_NOISE unsquared yaw variance quirk, EKF2_EVP_GATE per-axis 5-sigma innovation gate, 1 s fusion-failing reset, 5 in-air resets then stop (+4 more)

### Community 62 - "Community 62"
Cohesion: 0.18
Nodes (12): EV height fusion and height bias estimator, EV position bias estimator (GNSS-only), EV quality field / EKF2_EV_QMIN, EV reset_counter (teleport signal in EKF2), EV velocity fusion (ev_vel_control.cpp), MAVLink ODOMETRY #331 message, MAVROS ROS 2 odom plugin (never sets reset_counter), PX4 issue #19830 offboard EKF reset handling (+4 more)

### Community 64 - "Community 64"
Cohesion: 0.24
Nodes (11): drift_error.png (horizontal error and heading error figure), 3 m abort threshold, Compass v2 + ZED velocity: landed, 358 m, Compass v3 + ZED velocity (shipped): landed, 359 m, Compass + ZED position fused: aborted in lap 5, 322 m, EKF2 heading error held near 0 by compass, Heading error vs sim time in shipped run (chart), Horizontal EKF2 error vs distance flown (chart) (+3 more)

### Community 65 - "Community 65"
Cohesion: 0.22
Nodes (11): B16 frame prefix gap, tests/check_contract.py parity checks, /sim/scenario topic (MRGCS Kinetix bridge), Per-drone TF tree (map-odom-zed_camera_link-base_link), Vehicle interface contract (sim = hardware), Digital twin goal: develop in sim, deploy unchanged, LW20/C down-facing ToF rangefinder, PMW3901 optical flow (analytic twin) (+3 more)

### Community 66 - "Community 66"
Cohesion: 0.20
Nodes (11): M20 performance.md is 5.1-era, Performance and profiling, Hover stability vs physics_dt (60 Hz wobbles, 120 Hz stable), Measuring: debug perf, debug gpu, boot time, kitlog, Tracy, NVIDIA Simulation Performance Optimization Handbook (upstream reference), perf: block knobs (limit_cpu_threads, skip_material_loading, min_frame_rate, physx_threads...), 120 Hz physics rationale, physics_dt also sets PX4 sensor and MAVLink rate (+3 more)

### Community 67 - "Community 67"
Cohesion: 0.18
Nodes (11): GPS-denied state estimation (VIO to EKF2 external vision), Baro as EKF2 height reference (range fails over furniture), EKF2_MIN_RNG 0.10 takeoff-offset fix, GPS-denied on ZED + LW20 + PMW3901 + baro, Runbook simulation stack, ./bisg CLI cheat sheet, Common failures, Launcher must be PID 1 (do not use python.sh) (+3 more)

### Community 68 - "Community 68"
Cohesion: 0.18
Nodes (11): Freeze survey map then localize, Map corrupted by its own drift, Scan Context place recognition, Jetson Orin compute figures for VSLAM, Survey-then-localize with saved map (.area / SaveMap), ZED area memory / .area relocalization, ZED positional tracking GEN_1 (dense VIO), ZED positional tracking GEN_3 (VSLAM, loop closure) (+3 more)

### Community 70 - "Community 70"
Cohesion: 0.22
Nodes (5): Serve the viewport as a still image over one TCP port. The WebRTC client needs…, Issue one viewport capture if the interval has elapsed. Never raises., WebView, do_GET(), _send()

### Community 71 - "Community 71"
Cohesion: 0.31
Nodes (10): Long-flight drift test figure (5 laps of 12x20 m at 2 m, 1 m/s, 360 deg sweep per lap), Compass (magnetic heading) aiding of EKF2 yaw to bound drift, Compass v2 + ZED velocity (landed, 358 m; EKF2 max 2.04 m, raw ZED max 36.0 m), Compass v3 + ZED velocity, shipped (landed, 359 m; EKF2 max 1.76 m, raw ZED max 40.7 m), Compass, ZED position fused (aborted in lap 5 at 322 m; EKF2 max 3.53 m, raw ZED max 33.8 m), EKF2 estimate (what the drone flew on) stays close to ground truth, Ground truth trajectory, No compass, ZED velocity + yaw (control, aborted after 36 m; EKF2 max 3.73 m, raw ZED max 4.4 m) (+2 more)

### Community 72 - "Community 72"
Cohesion: 0.22
Nodes (10): Basalt, cuVSLAM / isaac_ros_cuvslam, DROID-SLAM / DPV-SLAM / MAC-VO (learned), False loops from perceptual aliasing, Kimera-VIO / Kimera-RPGO, Odom continuous, corrections in map->odom, OpenVINS, ORB-SLAM3 (+2 more)

### Community 73 - "Community 73"
Cohesion: 0.24
Nodes (10): ZED VIO accuracy and calibration (doc), Ablation study 2026-10-15 (6 configs x 3 flights), VIO campaign (doc), Ablation configs (calibrated, no_yaw_limit, no_eva_fix, ...), Fresh sim per flight (B18, independence), Infra failure vs VIO failure, Campaign verdict (pipeline calibrated gate), VIO campaign (vio_campaign.py, vio bench/check) (+2 more)

### Community 74 - "Community 74"
Cohesion: 0.49
Nodes (9): current(), newest(), resolve(), ros_up(), running(), bag.sh script, start(), status() (+1 more)

### Community 75 - "Community 75"
Cohesion: 0.33
Nodes (6): each(), listening(), row(), info.sh script, sub(), ts_json()

### Community 76 - "Community 76"
Cohesion: 0.31
Nodes (7): mavros(), mavsdk(), entrypoint.sh script, xrce(), ext_setup_bash, ext_setup_zsh, host_ros_env.sh script

### Community 77 - "Community 77"
Cohesion: 0.22
Nodes (9): ADR-003 One PX4 tag for SITL and Pixracer, MAVROS 2.15.1, Pegasus PR #144 head fcb99c0, px4_fmu-v4_default Pixracer firmware (95.3% flash), PX4_TAG Dockerfile arg, Re-validation on Isaac Sim 6.0 (2026-10-02), Selection procedure (Phase 1), PX4 v1.16.0 fallback (+1 more)

### Community 78 - "Community 78"
Cohesion: 0.25
Nodes (9): Staged plan: layer, compass, wall offsets, loop closure, reset_counter, ICP, Doer & Trommer yaw-aided radar-inertial odometry, L-SLAM linear RGB-D SLAM for planar environments, LPVO low-drift VO decoupling rotation (Kim 2018), 90 degree MF ambiguity (45 deg rule), OPVO drift-free rotation VO (Kim 2017), Rotation drift is the main source of VO position error, Wall-relative position from plane offsets (L-SLAM style) (+1 more)

### Community 79 - "Community 79"
Cohesion: 0.44
Nodes (8): have_frames(), zed.sh script, start_services(), svc_name(), video_hint(), video_ip(), ZED_SIM_PORT, zexec()

### Community 80 - "Community 80"
Cohesion: 0.36
Nodes (3): Archive, archived(), The 2026-10-15 flights (docs/vio.md, archive/vio-2026-10-15/README.md).…

### Community 81 - "Community 81"
Cohesion: 0.22
Nodes (4): Fake, main(), Node, spin_for()

### Community 82 - "Community 82"
Cohesion: 0.36
Nodes (8): Scenario eight_iris_nozed, Scenario four_iris_nozed, Scenario single_iris_nozed (base), extends: single_iris.yaml, Isolate Isaac + Pegasus + PX4 from the sensor layer, ros2 pub_state true; pub_sensors/pub_graphical_sensors false, Iris vehicle 0, usd_path null, spawn z 0.07, sensors.zed.enabled false

### Community 83 - "Community 83"
Cohesion: 0.29
Nodes (5): Features, load_features(), Read the ZED switches from docker/zed/zed.yaml, the file the real zed_wrapper…, toggle(), run()

### Community 84 - "Community 84"
Cohesion: 0.29
Nodes (3): main(), spin(), wait()

### Community 85 - "Community 85"
Cohesion: 0.29
Nodes (5): skipIf, quat(), Unit tests for tests/compass_compare.py's math (needs rclpy for the import: run…, ZYX Euler (rad) -> (x, y, z, w)., TestCompassCompare

### Community 86 - "Community 86"
Cohesion: 0.33
Nodes (7): headless_fast.yaml scenario, app.render: false, world preset Default Environment, Iris vehicle id 0 (ros2 disabled), perf.skip_material_loading, app.stream: off, sensors.zed.enabled: false

### Community 87 - "Community 87"
Cohesion: 0.43
Nodes (6): apply(), apply_force(), apply_torque(), handle_propeller_visual(), _prim(), update()

### Community 88 - "Community 88"
Cohesion: 0.38
Nodes (3): pcompose(), px4-bridge.sh script, stop()

### Community 90 - "Community 90"
Cohesion: 0.47
Nodes (5): log(), main(), mission_square — Phase 2 exit test (docs/roadmap.md): take off, fly a square,…, use_sim_time_if_clock(), rclpy_utilities

### Community 91 - "Community 91"
Cohesion: 0.33
Nodes (5): expand_locator(), load_scenario(), merge(), The locator keys of docker/sim/sim.yaml (what the sim runs) -> the plain…, Read a scenario YAML. `extends: <file>` or a list of files (relative to this…

### Community 92 - "Community 92"
Cohesion: 0.33
Nodes (3): Publish /clock (sim time) once per physics step (docs/interface-contract.md).…, Latched /sim/scenario: which scenario and world this sim run loaded…, SimClock

### Community 94 - "Community 94"
Cohesion: 0.33
Nodes (6): PX4 shell without QGC (./bisg debug px4), rosbag2/MCAP recording profiles (flight, vision, all), Debugging symptom-to-command table, ADR-011: zed-ros2-wrapper pinned to upstream master / fork local branch, R9: wrapper abort 'can't compare times with different time sources', zed-ros2-wrapper fork branch 'local' (60f78bd = b19902d + PR #463)

### Community 95 - "Community 95"
Cohesion: 0.33
Nodes (6): ./bisg setup one-command setup, Workstation setup, Docker data-root on large disk, First run sequence (config, up, smoke, mavros), Host prerequisites (driver, Docker, nvidia-toolkit), bisg/sim builds from Pegasus submodule

### Community 96 - "Community 96"
Cohesion: 0.33
Nodes (6): ZED SDK in sim setup (fetch_sources, zed build, zed image), The real ZED SDK in the sim, ZED asset FixedJoint mount to vehicle body, SDK stereo-matched depth (NEURAL_LIGHT), IPC shared-memory stream (/dev/shm, port 30000+2*id), Stereolabs extension streaming ZED_M twin into SDK

### Community 97 - "Community 97"
Cohesion: 0.33
Nodes (6): ZED module test + benchmark, 16/16 phases pass (1 warning), zed-bridge container cost (0.31 cores), RAM is the real constraint on Orin NX, Second workstation split GPUs (SIM_GPU=0 ZED_GPU=1), Streaming server crashes wrapper in sim (B19)

### Community 98 - "Community 98"
Cohesion: 0.53
Nodes (5): Replay the ZED odometry jump gate (docker/zed/zed_stack/bridge/jumpgate.py) on…, replay(), yaw_err(), wrap(), yaw_of()

### Community 99 - "Community 99"
Cohesion: 0.33
Nodes (5): load_scenario(), merge(), main(), quat_xyzw_to_matrix(), Same `extends:` deep-merge as docker/sim/launcher/launch.py.

### Community 101 - "Community 101"
Cohesion: 0.50
Nodes (4): isaac_python_exec(), ROS_DISTRO, entrypoint.sh script, SIM_CONFIG

### Community 102 - "Community 102"
Cohesion: 0.70
Nodes (5): Kinetix explore paths figure (Warehouse, 28 views, ~5 min, top view, ground truth vs EKF2), Before: no compass, ZED position (two runs: EKF2 max 1.50 m / worst wall 2.41 m; EKF2 max 2.73 m / worst wall 4.11 m), Compass + ZED velocity (two runs: EKF2 max 0.98 m / worst wall 0.66 m; EKF2 max 0.62 m / worst wall 1.04 m), EKF2 pose (what Kinetix maps and flies on) vs ground truth, Warehouse walls (dashed boundary, about 19.5 x 30 m)

### Community 103 - "Community 103"
Cohesion: 0.60
Nodes (5): Report: Anchor heading to walls before closing loops, Absolute wall-derived yaw beats loop closure for exploration drones, Scan-to-map bounds drift only when revisiting, Research note: VIO/SLAM with loop closure for GPS-denied drone, Loop closure helps only on revisits

### Community 104 - "Community 104"
Cohesion: 0.70
Nodes (4): die(), pass(), check_env.sh script, wrn()

### Community 105 - "Community 105"
Cohesion: 0.50
Nodes (3): drone.sh script, ZED_STACK_SIM, zexec()

### Community 106 - "Community 106"
Cohesion: 0.50
Nodes (3): Params, Twin mount (raptor.yaml, FLU), EKF2 lever arm (raptor.params, FRD) and the…, read_params()

### Community 107 - "Community 107"
Cohesion: 0.67
Nodes (4): bag profile: all, rosbag2 recording config (bag.yaml), bag profile: flight, bag profile: vision

### Community 108 - "Community 108"
Cohesion: 0.50
Nodes (4): ROS GUI/debug tools config (tools.yaml), foxglove tool (bridge + web UI), rqt tool, rviz tool

### Community 109 - "Community 109"
Cohesion: 0.67
Nodes (4): Kinetix explore: EKF2 error over the flight (figure), Before: no compass, ZED position (EKF2 max 1.50 m and 2.73 m, worst wall 2.41 m and 4.11 m), Compass + ZED velocity (EKF2 max 0.98 m and 0.62 m, worst wall 0.66 m and 1.04 m), EKF2 horizontal error vs ground truth over wall-clock minutes (sim ~0.55x)

### Community 110 - "Community 110"
Cohesion: 0.50
Nodes (4): EKF2_EV_CTRL bits (pos, hgt, vel, yaw), Velocity + yaw only EV fusion (EKF2_EV_CTRL 12), vio_bench ablation EV_CTRL 12, PX4 VIO docs: use vision velocity when positions disagree

### Community 111 - "Community 111"
Cohesion: 0.67
Nodes (3): main(), pump(), wait()

### Community 115 - "Community 115"
Cohesion: 0.67
Nodes (3): High-rate IMU in stream (ingest_imu, gen-2 streaming), What differs from the real drone, bisg zed check / zed_sdk_check.py

## Ambiguous Edges - Review These
- `launch.py` → `B5 Pegasus state topics stamped with wall time`  [AMBIGUOUS]
  docs/bugs.md · relation: conceptually_related_to

## Knowledge Gaps
- **212 isolated node(s):** `entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO`, `ros_env.sh script`, `ROS_DOMAIN_ID` (+207 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 632 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **44 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What is the exact relationship between `launch.py` and `B5 Pegasus state topics stamped with wall time`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **Why does `single_iris scenario` connect `Sim Scenarios & Perf Knobs` to `Community 66`, `Sim Launcher`, `Project Docs & Raptor Vehicle`, `Community 86`, `ZED Config & Bench Settings`, `Community 59`, `Community 60`, `Community 31`?**
  _High betweenness centrality (0.109) - this node is a cross-community bridge._
- **Why does `Manhattan compass (zed-bridge heading from room walls)` connect `Community 51` to `Community 78`, `Community 55`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Why does `calibrated config (shipped GPS-denied mode)` connect `Community 51` to `Offboard Controller & Flow Bench`?**
  _High betweenness centrality (0.054) - this node is a cross-community bridge._
- **What connects `entrypoint.sh script`, `SIM_CONFIG`, `ROS_DISTRO` to the rest of the system?**
  _212 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `VIO & Range-Flow Evaluation` be split into smaller, more focused modules?**
  _Cohesion score 0.058823529411764705 - nodes in this community are weakly interconnected._
- **Should `Docker Compose & Remote Access` be split into smaller, more focused modules?**
  _Cohesion score 0.05410628019323672 - nodes in this community are weakly interconnected._