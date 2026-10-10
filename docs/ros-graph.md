# The ROS 2 graph: which node does what, how data flows, what is redundant

A map of every ROS 2 node in a normal sim run (`./bisg up`, scenario `single_iris`, ZED autostart, ROS tools on), measured on
the live graph on 2026-10-10 (workstation A). It is a reading guide. The **contract** that sim and hardware must obey stays in
[interface-contract.md](interface-contract.md), and each subsystem has its own doc ([zed-stack.md](zed-stack.md), [px4-bridge.md](px4-bridge.md),
[zed-sdk-sim.md](zed-sdk-sim.md), [range-flow.md](range-flow.md)). Raw dump: `ros2 node list` / `ros2 node info` / `ros2 topic info -v` in
`bisg-ros`; numbers from `ros2 topic hz|bw` (Python tools under-count large images, so treat image rates as lower bounds).

## 1. The picture

```
 ┌─ bisg-sim (Isaac Sim + Pegasus; not a ROS node except where marked) ────────────────────────────────────────────┐
 │  physics + Iris ── Pegasus PX4MavlinkBackend ══ MAVLink TCP 4560 ══► PX4 SITL (inside the same container)        │
 │  ZED_M twin ── sl.sensor.camera streamer ══ shared memory /dev/shm/sl_local_*_30000 ══╗                           │
 │  ROS: /bisg_sim_clock ─► /clock                                                       ║                           │
 │       /simulator_vehicle_1 ─► /drone_1/state/{pose,twist,twist_inertial,accel}  (ground truth, tests only)       │
 │       OmniGraph IMU ─► /drone_1/zed/zed_node/imu/data  (frame drone_1/zed_imu_link)                             │
 └───────────────────────────────────────────────────────────────────────────────────────║────────┬──────────────────┘
                                                                                          ║        │ MAVLink UDP (port from DRONE_ID)
 ┌─ bisg-zed-1 (zed_wrapper) ──────────────────┐   ┌─ bisg-mavros-1 (px4-bridge, PX4_BRIDGE=mavros) ▼──────────────────┐
 │ /drone_1/zed/zed_container (component host)  │   │ /drone_1/mavros_router  MAVLink endpoints  ◄─► /uas1/mavlink_*     │
 │   └ /drone_1/zed/zed_node  ◄═══ SDK reads ═══╝   │ /drone_1/mavros_node    plugin host                                │
 │       left/right rect image + camera_info    │   │   └ one node per plugin: sys, time, cmd, param, imu, local_position,│
 │       depth/depth_registered, confidence_map │   │     global_position, home_position, setpoint_{position,raw,velocity},│
 │       point_cloud/cloud_registered           │   │     odometry, vision_pose, obstacle, distance_sensor, landing_target,│
 │       odom, pose, pose/status, status/health │   │     onboard_computer, debug_value                                   │
 │       imu/data (frame zed_imu_link)          │   │ publishes /drone_1/mavros/* (state, imu/data, local_position/*, …)   │
 │       /tf: map→odom→zed_camera_link          │   │ subscribes setpoints, odometry/out, obstacle/send, statustext/send   │
 │ /drone_1/zed/zed_state_publisher (URDF tf)   │   │ /tf_static: map→map_ned, odom→odom_ned, base_link→base_link_frd      │
 │ /launch_ros_1 (the launch process)           │   └──────────────────────────────────────────────▲───────────────────────┘
 └───────┬──────────────────────────────────────┘                                                  │
         │ images · depth · health · pose/status · odom                                            │ obstacle/send (LaserScan)
         ▼                                                                                         │ statustext/send
 ┌─ bisg-zed-bridge-1: /zed_px4_bridge ────────────────────────────────────────────────────────────┘  odometry/out (VIO, off in sim)
 │  health (status/health, pose/status, depth) · obstacle_distance (depth + camera_info) · odometry (odom, pose/status)
 │  publishes /drone_1/zed_stack/status
 ├─ bisg-zed-video-1: /video_stream ─ left + chase + depth ─► 2x2 mosaic + Farneback flow ─► RTP/H.264 UDP 5600 ─► QGC
 │                                                        └─► /drone_1/zed/video/optical_flow
 └─ bisg-ros: /rviz (left, chase, depth, flow, point cloud, odom, path_odom, TF) · /rqt_gui_py_node_* · test scripts
```

**Five links do not use ROS.** Pegasus ↔ PX4 (MAVLink TCP 4560), PX4 ↔ MAVROS (MAVLink UDP, port derived from `DRONE_ID`), Isaac's ZED twin → SDK (shared memory, `ipc: host`),
video → QGC (RTP/UDP 5600), and MAVROS → QGC (MAVLink, when `GCS_URL` is set). The ToF/flow twin also bypasses ROS: it writes
`DISTANCE_SENSOR` / `HIL_OPTICAL_FLOW` straight to PX4 ([range-flow.md](range-flow.md)).

## 2. Node catalogue

| Node (as `ros2 node list` shows it) | Container / service | What it is for | Needed when |
|---|---|---|---|
| `/bisg_sim_clock` | `bisg-sim` (launcher `SimClock`) | publishes `/clock` so every node runs on sim time (PX4 SITL runs on sim time) | always in the sim; absent on the drone |
| *(OmniGraph chase-camera publisher; shows up as `_Render_PostProcess_SDGPipeline_Replicator_NodeWriterWriter` in `/drone_1`)* | `bisg-sim` (`sim/launcher/chase_cam.py`, scenario `sensors.chase_cam`) | the third-person view as `/drone_1/chase/image` (640x360 rgb8): its own USD camera follows the drone, turns with its heading, has its own render product (works headless). Sim only | for the QGC mosaic and RViz |
| `/simulator_vehicle_1` | `bisg-sim` (Pegasus ROS 2 backend, `ros2.pub_state`) | ground truth `/drone_1/state/*` at the physics rate | tests and benchmarks only (parity rule: vehicle code must not read it) |
| *(OmniGraph IMU node, not always listed)* | `bisg-sim` (`zed_sdk_rig.publish_imu`) | the ZED IMU the streamed twin cannot carry, on `zed/zed_node/imu/data` | only with a consumer of the ZED IMU (none today), see R1 |
| `/drone_1/mavros_router` | `bisg-mavros-1` | MAVROS 2 MAVLink router: FCU link (`fcu_url`) + optional GCS link, bridges to `/uas1/mavlink_*` | always (it is the PX4 link) |
| `/drone_1/mavros_node` + `/drone_1/mavros` | `bisg-mavros-1` | the UAS host: decodes MAVLink, owns `/drone_1/mavros/*`, `tf_static` NED helpers | always |
| `/drone_1/mavros/<plugin>` (20 nodes) | `bisg-mavros-1` | one ROS node per allow-listed plugin (`docker/ros/mavros_lean.yaml`) | per plugin, see §5 |
| `/drone_1/zed/zed_container` | `bisg-zed-1` | component container hosting the wrapper (intra-process capable, `enable_ipc`) | with the ZED |
| `/drone_1/zed/zed_node` | `bisg-zed-1` | **the real ZED SDK** (`zed_wrapper`): images, depth, confidence, cloud, VIO, health, TF | with the ZED; the only image/depth source |
| `/drone_1/zed/zed_state_publisher` | `bisg-zed-1` | `robot_state_publisher` for the ZED URDF: `zed_camera_link → center → left/right → optical` | with the ZED |
| `/launch_ros_1`, `transform_listener_impl_*` | ZED / MAVROS / RViz | the launch process and TF-listener helpers inside other nodes; no data of their own | infrastructure |
| `/zed_px4_bridge` | `bisg-zed-bridge-1` (`zed_stack.bridge`) | ZED → PX4 through MAVROS: **health** (STATUSTEXT to QGC), **obstacle_distance** (72 sectors → PX4 collision prevention), **odometry** (VIO → EKF2, GPS-denied only) | whenever PX4 should use the ZED |
| `/video_stream` | `bisg-zed-video-1` (`zed_stack.video`) | QGC video: 2x2 mosaic (left / chase / depth / flow) as H.264 RTP, and `zed/video/optical_flow` | only while someone watches QGC |
| `/rviz`, `/rqt_gui_py_node_*` | `bisg-ros` (`ROS_TOOLS_AUTOSTART`, `docker/ros/tools.yaml`) | operator views | only while someone looks at them |
| test scripts (`vio_flight_test`, `range_flow_bench`, …) | `bisg-ros` | flights and checks; they stream setpoints and read ground truth | during a test |

On the real drone (`./bisg drone up`) the set shrinks to MAVROS (serial `/dev/px4`), the ZED wrapper on the real camera, the bridge
and (optionally) the video sender. `/clock`, `/simulator_vehicle_1` and the OmniGraph IMU do not exist there.

## 3. Data flows

**A. Flight control (always).** test/mission code → `mavros/setpoint_position/local` (or `setpoint_raw/local`) at ≥ 10 Hz → MAVROS →
PX4 OFFBOARD. Feedback: `mavros/state` (1 Hz), `mavros/local_position/{pose,odom}` (EKF2, 30 Hz nominal, 19 Hz measured at RTF 0.65),
`mavros/imu/data` (FC IMU, 31 Hz measured). Modes and arming: `mavros/set_mode`, `mavros/cmd/arming`.

**B. ZED → PX4 (the bridge).**
`zed_node/depth/depth_registered` → bridge `obstacle_distance` → `mavros/obstacle/send` (LaserScan, 7 Hz measured) → PX4 `OBSTACLE_DISTANCE`.
`zed_node/status/health` + `pose/status` + depth valid fraction → bridge `health` → `mavros/statustext/send` + `zed_stack/status`.
`zed_node/odom` → bridge `odometry` → `mavros/odometry/out` → EKF2 external vision (GPS-denied scenarios only, `services.px4_bridge.odometry`).

**C. Operator views.** `zed_node` images, depth and point cloud → RViz. Images and depth → `video_stream` → QGC and `zed/video/optical_flow` → RViz.

**D. Truth and time (sim only).** `/clock` → every node with `use_sim_time`. `/drone_1/state/*` → tests.

## 4. TF tree (measured) vs the contract

```
map ──► odom ──► zed_camera_link ──► zed_camera_center ──► zed_left_camera_frame  ──► zed_left_camera_frame_optical
 │       │        (zed_node, 30 Hz)    (zed_state_publisher, static)  └► zed_right_camera_frame ──► zed_right_camera_frame_optical
 │       └► odom_ned  (MAVROS static)
 └► map_ned (MAVROS static)                      base_link ──► base_link_frd   (MAVROS static, NOT connected to anything)
```

The contract asks for `map → odom → base_link → zed_left_camera_optical_frame`. Today the tree has **two unconnected parts**:
`base_link` has no parent, the ZED treats `zed_camera_link` as the robot, and the optical frame is called
`zed_left_camera_frame_optical`. `map → odom` is published by the ZED wrapper, not by MAVROS/PX4 (finding R2). MAVROS publishes no
`map → base_link` (`local_position.tf.send: false`), so the EKF2 pose exists only as topics.

## 5. Load and redundancy

Measured with RViz and QGC video running:

| Stream | Rate | Inter-process traffic | Consumers |
|---|---|---|---|
| `left/color/rect/image` (1280x720) | ~19 Hz | ≈ 47 MB/s | rviz, video_stream |
| `/drone_1/chase/image` (640x360) | ~15–21 Hz | ≈ 10 MB/s | rviz, video_stream |
| `right/color/rect/image` | – | **0**: no subscriber since 2026-10-10 (the chase view replaced it in RViz and the mosaic), so the wrapper does not send it | – |
| `depth/depth_registered` (32FC1) | 9–19 Hz | ≈ 70 MB/s **per subscriber** | rviz, video_stream, bridge **×2** |
| `point_cloud/cloud_registered` | ~10 Hz | ≈ 20 MB/s | rviz only |
| `zed/video/optical_flow` | ~14 Hz | ≈ 10 MB/s | rviz only |
| `zed_node/imu/data` | 72 Hz combined | small | **none** (two publishers, R1) |
| `/clock` | 26 Hz | small | ~25 nodes |
| `/drone_1/state/pose` | 72 Hz | small | tests |

About **200 MB/s** of camera data crosses process boundaries (CycloneDDS over loopback), and almost all of it feeds the two operator
views. The wrapper computes depth, point cloud and images only while something subscribes, so with RViz and QGC closed the same graph
costs a few MB/s (the bridge's depth only).

### Findings (most important first)

| # | Finding | Effect | Recommended fix |
|---|---|---|---|
| **R1** | **Two publishers on `zed/zed_node/imu/data`**: the sim's OmniGraph IMU (`drone_1/zed_imu_link`, ~58 Hz) and the wrapper (`zed_imu_link`, ~14 Hz from the stream) | a future consumer gets an interleaved stream from two frames (no consumer today) | sim only: stop the wrapper's copy (`sensors.publish_imu` for the wrapper) and keep the sim's. Needs a separate key, because the sim reads the same `sensors.publish_imu` to decide its own publishing (`sim/launcher/zed_features.py`) |
| **R2** | **`zed.yaml` `publish_map_tf: false` is ignored.** The stock `zed_camera.launch.py` overrides `pos_tracking.publish_tf` / `publish_map_tf` / `sensors.publish_imu_tf` with its own launch arguments (default true); the live parameter is `True` | the wrapper publishes `map → odom`, a frame the yaml says MAVROS/PX4 owns. With MAVROS TF on, this would make two `map` authorities | `docker/zed/zed_drone.launch.py`: forward those three keys from the compiled params as launch arguments. RViz uses `odom` as its fixed frame, so it is unaffected |
| **R3** | **TF tree split; `base_link` not connected to the ZED; optical frame name differs from the contract** (related to B16) | the contract check (§Parity 3) cannot pass; Kinetix's `T_base_cam` from `tf_static` does not exist | publish the mount `base_link → zed_camera_link` (static, from the scenario's `mount_xyz_rpy` / hardware.md), decide the frame owner of `map → odom` (R2), and fix the optical-frame name in the contract or the URDF |
| R4 | **The bridge subscribes to depth twice** (`health` and `obstacle_distance` each own a subscription), so each depth frame is deserialised twice in Python | ~70 MB/s extra and ~0.3 core (already in todo) | one shared depth subscription in `bridge/node.py`, handed to both modules |
| R5 | **RViz's default config subscribes to everything heavy** (left, chase, depth, flow, point cloud) and starts on every sim run (`ROS_TOOLS_AUTOSTART=1`) | the point cloud is computed only for RViz; most of the 200 MB/s | keep the point cloud and right image displays disabled in `drone.rviz` (enable on demand); `path_odom` has no publisher (`publish_cam_path: false`), so drop or enable it |
| R6 | **`video_stream` runs by default** (`services.qgc_video.enabled: true`): 3 full-rate subscriptions + Farneback, ~0.5 core | costs CPU even when QGC is closed | enable it only when QGC is watched (`./bisg zed video`), or `enabled: false` by default |
| R7 | **MAVROS plugins with no consumer in today's flows**: `global_position` (GPS-denied scenarios), `home_position`, `setpoint_velocity`, `vision_pose` (the bridge uses `odometry`), `landing_target`, `debug_value`, `onboard_computer_status`; plus `distance_sensor`'s stock placeholders `lidarlite_pub`, `sonar_1_sub`, `laser_1_sub` | small (one node each, low-rate MAVLink), but 20 nodes and ~90 topics to read through | trim to what a flow uses, keep the ones planned (landing_target for M6). `MAVROS_PLUGINS=lean` stays the knob |
| R8 | **MAVROS router topics are global** (`/uas1/mavlink_source`, `/uas1/mavlink_sink`), not under `/drone_1` | with two drones both routers would use `/uas1` (not tested yet) | set a per-drone `uas_url` in `docker/px4-bridge/entrypoint.sh` before the swarm phase; `/clicked_point` (plane detection) is global for the same reason |
| R9 | **The wrapper crashes after ~20–30 min** in the sim (~27 min, then 22 min on 2026-10-10 16:17 UTC; the docker container stays `Up`): `terminate ... std::runtime_error: can't compare times with different time sources` (log `/opt/docker-archive/zed_wrapper_crash_20261010T0958Z.log`) | all ZED topics stop; the bridge reports `camera lost` | open: reproduce with a long run; the message points at a sim-time vs system-time stamp comparison inside the wrapper |
| R10 | `/clock` is published at ~26 Hz (wall) at RTF 0.65, not every physics step as the contract says | sim-time timers are quantised to ~25 ms | measure against the launcher; correct either the contract or the publisher |

**Not redundant** (looks like it, is not): `mavros_router` + `mavros_node` (MAVROS 2 always splits routing and plugins), the
`transform_listener_impl_*` nodes (TF buffers inside other nodes), `/launch_ros_1`, two IMU topics `mavros/imu/data` (flight
controller) vs `zed_node/imu/data` (camera, R1 aside), and the `state/*` ground truth (test-only by rule).

## 6. Minimal sets per job

| Job | Containers | Nodes that matter |
|---|---|---|
| Fly / PX4 tests (`./bisg smoke`, `vio_flight` on flow) | sim, mavros, ros | sim clock, mavros (sys, cmd, local_position, setpoint_*, imu), test script |
| GPS-denied on the ZED (`single_iris_vio`) | + zed, zed-bridge (`odometry.enabled`) | + zed_node, bridge `odometry` + `health` |
| Obstacle avoidance | + zed-bridge `obstacle_distance` | + mavros `obstacle` |
| Perception work / Kinetix T2 | zed (+ ros for scripts) | zed_node only; subscribe lazily (Kinetix `ros-pipeline.md`) |
| Watching | + video (QGC) or RViz | add only the displays you look at |
