# Vehicle interface contract

The set of ROS 2 names every drone exposes, **identical in sim and on hardware**. Mission,
perception and fleet code depends only on this document. Change it here first, then in code,
then run `tests/check_contract.py` (Phase 3) against both a sim drone and a real drone.

Conventions: ROS 2 Jazzy, REP-103 units (SI, ENU, FLU body), REP-105 frames. Namespace per
vehicle is `/drone_<n>` with `n` = 1-based drone number = PX4 `MAV_SYS_ID`.

## Frames (per drone, prefixed `drone_<n>/` on TF)

```
map ─► odom ─► zed_camera_link ─► base_link                                   (TF tree as published)
                              └► zed_camera_center ─► zed_left_camera_frame ─► zed_left_camera_frame_optical
                                                  │                         └► zed_imu_link
                                                  └► zed_right_camera_frame ─► zed_right_camera_frame_optical
```

What consumers rely on is that every lookup resolves: `map → odom → base_link → zed_camera_link → zed_left_camera_frame_optical`
(`tests/check_contract.py` check 3). The tree is shaped by the ZED wrapper, whose base frame is hard-wired to `zed_camera_link`:
it publishes `odom → zed_camera_link` itself, so `base_link` hangs under the camera by the inverse of the mount (R3, 2026-10-10).

- `map`: EKF2 local origin (MAVROS `local_position`), shared per drone; fleet works in `map` with a
  known per-drone offset published by the fleet manager as `map` → `drone_<n>/map` static TF. `map → odom` is a static
  identity from `docker/zed/zed_drone.launch.py` (the wrapper's own map TF is off).
- `odom` motion comes from the VIO source (the ZED wrapper, in the sim and on the drone), never from MAVROS. Tracking starts with
  the camera at its mount pose, so `odom → base_link` is the identity at start.
- Camera mount pose base_link → zed_camera_link is ONE key, `positional_tracking.initial_base_pose` in `docker/zed/zed.yaml`;
  `zed_drone.launch.py` publishes its inverse `zed_camera_link → base_link` (static). The sim places its twin with the scenario's
  `sensors.zed.mount_xyz_rpy` (keep equal); the real drone's measured value goes in `docs/hardware.md`.
- Frame names are the wrapper's (5.4: `…_frame_optical`), unprefixed — see the B16 gap at the end.

## Topics — provided by the vehicle

The `zed/zed_node/*` names are the ZED wrapper 5.4.1 names: the unmodified wrapper, launched by `docker/zed/zed_drone.launch.py` in the sim (real SDK on
the streamed ZED Mini twin, `docs/zed-sdk-sim.md`) and on the drone. The emulated rig was removed 2026-10-07.

| Topic (under `/drone_<n>/`) | Type | Rate | Source sim / real | Notes |
|---|---|---|---|---|
| `mavros/state` | `mavros_msgs/State` | 1–10 Hz | MAVROS / MAVROS | connected, armed, mode |
| `mavros/local_position/pose` | `geometry_msgs/PoseStamped` | 30 Hz | MAVROS | EKF2 pose, ENU, frame `map` |
| `mavros/local_position/odom` | `nav_msgs/Odometry` | 30 Hz | MAVROS | |
| `mavros/hrlv_ez4_pub` | `sensor_msgs/Range` | 10 Hz | MAVROS (`distance_sensor` plugin) | may be empty: only with a ToF (sim scenario `single_iris_flow`; LW20/C on the drone). Down-facing ToF (PX4 `distance_sensor` instance 0, LW20/C on the drone), frame `hrlv_ez4_sonar` (MAVROS' stock config name; rename = override the plugin's `config`). `range >= max_range` means no valid reading. BEST_EFFORT |
| `mavros/px4flow/raw/optical_flow_rad` | `mavros_msgs/OpticalFlowRad` | 10 Hz | MAVROS (`px4flow` plugin) | may be empty: only with a flow sensor (sim: `sensors.optical_flow` of the raptor or `single_iris_flow`; Holybro PMW3901 on the Pixracer SPI). PX4's `vehicle_optical_flow` as `OPTICAL_FLOW_RAD`, turned into base_link FLU by MAVROS (y and z flip against PX4's FRD): `integrated_x/y` = flow (rad) over `integration_time_us`, positive = right-handed rotation about FLU x/y, so moving forward gives −y and moving left +x (checked against ground truth 2026-10-14); `integrated_*gyro` = the FC gyro over the same span (flow − gyro = the translational part); `quality` 0–255 (0 = below 8 cm / no tracking); `distance` m, −1 = unknown (PX4 takes it from the down ToF). Each message is one sensor sample (sim twin: ~20 ms); PX4's onboard link sends the newest at 10 Hz. Frame `px4flow`. The plugin also publishes `mavros/px4flow/ground_distance` (`sensor_msgs/Range`, the same distance) |
| `mavros/imu/data` | `sensor_msgs/Imu` | 50 Hz | MAVROS | FC IMU (not ZED IMU) |
| `mavros/battery` | `sensor_msgs/BatteryState` | 0.5 Hz | MAVROS | sim: SITL battery model |
| `mavros/global_position/global` | `sensor_msgs/NavSatFix` | 50 Hz | MAVROS | may be empty when GPS disabled |
| `zed/zed_node/left/color/rect/image` | `sensor_msgs/Image` | 15–30 Hz | Isaac cam / ZED wrapper | `bgra8`/`rgb8` per wrapper |
| `zed/zed_node/right/color/rect/image` | `sensor_msgs/Image` | same | Isaac cam / ZED wrapper | |
| `zed/zed_node/left/color/rect/camera_info` | `sensor_msgs/CameraInfo` | same | Isaac cam / ZED wrapper | intrinsics of the camera in use — read them, never hard-code `K` (sim `sdk`: the extension's `ZED_M` lens, HD720 `fx` 529.8 px; a real unit has its own factory calibration) |
| `zed/zed_node/right/color/rect/camera_info` | `sensor_msgs/CameraInfo` | same | Isaac cam / ZED wrapper | stereo baseline = `-P[0,3] / P[0,0]` (ZED Mini 63 mm); stereo consumers read it from here |
| `zed/zed_node/depth/depth_registered` | `sensor_msgs/Image` (`32FC1`, metres) | same | Isaac depth / ZED | |
| `zed/zed_node/confidence/confidence_map` | `sensor_msgs/Image` (`32FC1`, 0–100) | same as depth | ZED wrapper (`depth.publish_depth_confidence`) | per-pixel depth confidence, same grid and stamp as `depth_registered`. **Higher = less confident**; the wrapper already removes depth above `depth.depth_confidence` (95), so valid depth has ≤ 95 (median ~0.5 in the sim). Computed only while subscribed. Consumer: Kinetix `stereo_zed` (weight = 1 − c/100) |
| `optical_flow/image` | `sensor_msgs/Image` (`bgr8`, QGC tile size, 640x360 without the ZED) | 10 Hz (one per flow message) | `zed-video` node, drawn from `mavros/px4flow/raw/optical_flow_rad` (sim and real) | may be empty: only with a flow sensor (as `optical_flow_rad`). The down-facing PMW3901 as PX4 reports it, top-down (up = forward): arrow = gyro-compensated flow (rad/s, the motion over the ground), thin grey = raw flow, dots = the last 2 s; text = quality, distance, flow x distance as m/s. Visualisation only, the numbers are in `optical_flow_rad`. The PMW3901 has no camera picture: nothing here is a rendered image. Header of the flow message. Only while subscribed; RELIABLE; needs `services.qgc_video` on (either layout) |
| `chase/image` | `sensor_msgs/Image` (`rgb8`, 640x360) | 30 Hz (render rate) | Isaac chase camera (`sensors.chase_cam`, `docker/sim/launcher/chase_cam.py`) / **none on the real drone** | third-person view for humans: a camera 2 m behind and 1 m above the drone that turns with its heading, looking at it. Sim only, view only (no `camera_info`, no TF). Header stamp = sim time, `frame_id` `drone_<n>/chase_cam`. Sits in the QGC mosaic and RViz in place of the ZED right image; on hardware that tile reads "no signal" |
| `zed/zed_node/point_cloud/cloud_registered` | `sensor_msgs/PointCloud2` | ≤ 10 Hz wall | ZED wrapper | heavy: published only while subscribed. Organized, NaN = no depth; fields `x y z rgb` (float32, rgb PCL-packed); frame `zed_left_camera_frame` (x fwd) |
| `zed/zed_node/disparity/disparity_image` | `stereo_msgs/DisparityImage` | ≤ 10 Hz | ZED wrapper | optional, `depth.publish_disparity`; left optical frame |
| `zed/zed_node/mapping/fused_cloud` | `sensor_msgs/PointCloud2` | ~1 Hz | ZED wrapper | optional, `mapping.mapping_enabled`; frame `map` |
| `zed/zed_node/imu/data` | `sensor_msgs/Imu` | 200 Hz | Isaac physics IMU / ZED wrapper | frame `zed_imu_link`. In sim `sdk` the streamed ZED has no usable sensor channel, so the sim publishes this topic itself (`docs/zed-sdk-sim.md`) |
| `zed/zed_node/odom` | `nav_msgs/Odometry` | 30–60 Hz | ZED positional tracking (sim and real) | `odom` → `base_link` (wrapper default `zed_camera_link`; the bridge re-labels the frames to `odom`/`base_link`). One source per run |
| `vehicle/state` | `bisg_msgs/VehicleState` | 2 Hz | `bisg_vehicle/health` | id, mode, armed, battery %, pose, vio_ok, last_error |
| `tf`, `tf_static` | | | | frames above |

## Topics — consumed by the vehicle

| Topic (under `/drone_<n>/`) | Type | Producer | Notes |
|---|---|---|---|
| `mavros/setpoint_position/local` | `geometry_msgs/PoseStamped` | `bisg_vehicle/offboard_controller` | ≥ 10 Hz while OFFBOARD |
| `mavros/setpoint_raw/local` | `mavros_msgs/PositionTarget` | same | velocity/accel setpoints |
| `mavros/odometry/out` | `nav_msgs/Odometry` | `zed-bridge` odometry module (`zed_stack/bridge/odometry.py`, `services.px4_bridge.odometry` in zed.yaml), sim and real | ENU/FLU in; MAVROS converts to PX4 NED/FRD; frame ids `odom`/`base_link`; stamp = sample capture time on the vehicle clock (sim time in sim) — PX4 fuses the sample at that time, so a wrong clock is a wrong measurement |
| `vehicle/cmd` | `bisg_msgs/VehicleCmd` | fleet manager | takeoff / goto / land / rtl / hold / task-specific |

## Services (under `/drone_<n>/`)

`mavros/cmd/arming`, `mavros/set_mode`, `mavros/cmd/takeoff` (not used; we take off in OFFBOARD),
`mavros/param/set` (params are pushed from files, not at runtime, except for test toggles).

## Fleet-level topics (global, not namespaced)

| Topic | Type | Notes |
|---|---|---|
| `/fleet/task` | `bisg_msgs/Task` | task id, type, area/waypoints, assigned drone ids |
| `/fleet/status` | `bisg_msgs/FleetStatus` | aggregated `VehicleState` list |
| `/clock` | `rosgraph_msgs/Clock` | sim only, published every physics step by the launcher; all nodes `use_sim_time:=true` in sim — PX4 SITL runs on sim time, so this includes every MAVROS plugin node (`docker/ros/mavros_sim_time.py`) |

## QoS

- Sensor streams: `SensorDataQoS` (best effort, volatile, depth 5).
- State/mode/health: reliable, transient-local depth 1.
- MAVROS defaults are kept; our nodes match the publisher's QoS when subscribing to MAVROS.

## Parity checks (`tests/check_contract.py`, Phase 3)

1. Every "provided" topic exists with the listed type.
2. Measured rate within ±30 % of the listed rate.
2a. Rates are in sim time when `/clock` is published; a rate marked `wall` comes from a wall-clock timer (the wrapper's
    `point_cloud_freq`, the video node) and is measured in wall time.
3. TF chain `map → odom → base_link → zed_camera_link → zed_left_camera_frame_optical` resolvable.
4. `camera_info` width/height equal to the ZED model table in `hardware.md`; `K` is the camera's own (see the `camera_info` row), baseline `-P[0,3]/P[0,0]` = 63 mm.

`tests/zed_sdk_check.py` (`./bisg zed check`) already implements the ZED half of these checks for the real SDK, in sim and on the drone (`--no-gt`).

Known gap: the frame names above carry a `drone_<n>/` prefix, which the real wrapper cannot publish ([B16](bugs.md#b16)); in sim `sdk` the wrapper's own unprefixed frames are what you see.
