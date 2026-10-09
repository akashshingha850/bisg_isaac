# Vehicle interface contract

The set of ROS 2 names every drone exposes, **identical in sim and on hardware**. Mission,
perception and fleet code depends only on this document. Change it here first, then in code,
then run `tests/check_contract.py` (Phase 3) against both a sim drone and a real drone.

Conventions: ROS 2 Jazzy, REP-103 units (SI, ENU, FLU body), REP-105 frames. Namespace per
vehicle is `/drone_<n>` with `n` = 1-based drone number = PX4 `MAV_SYS_ID`.

## Frames (per drone, prefixed `drone_<n>/` on TF)

```
map ─► odom ─► base_link ─► zed_camera_link ─► zed_left_camera_frame ─► zed_left_camera_optical_frame
                       │                    └► zed_right_camera_frame ─► zed_right_camera_optical_frame
                       │                    └► zed_imu_link
                       └► (optional) lidar_link
```

- `map`: EKF2 local origin (MAVROS `local_position`), shared per drone; fleet works in `map` with a
  known per-drone offset published by the fleet manager as `map` → `drone_<n>/map` static TF.
- `odom` → `base_link` is published by the VIO source (sim: `vio_mock`; real: ZED wrapper), never by MAVROS.
- Camera mount pose is a **parameter** (`sensors.zed.mount_xyz_rpy`) used by both the Isaac rig and the
  real `static_transform_publisher`. Values live in `docs/hardware.md`.

## Topics — provided by the vehicle

The `zed/zed_node/*` names are the ZED wrapper 5.4.1 names (`ZED_SOURCE=sdk` is that wrapper, unmodified; `ZED_SOURCE=emulated` copies them). Pull them
in the sim with the `emulated` rig or the real SDK (`docs/zed-sdk-sim.md`); on the drone it is `docker/zed/zed_drone.launch.py`.

| Topic (under `/drone_<n>/`) | Type | Rate | Source sim / real | Notes |
|---|---|---|---|---|
| `mavros/state` | `mavros_msgs/State` | 1–10 Hz | MAVROS / MAVROS | connected, armed, mode |
| `mavros/local_position/pose` | `geometry_msgs/PoseStamped` | 30 Hz | MAVROS | EKF2 pose, ENU, frame `map` |
| `mavros/local_position/odom` | `nav_msgs/Odometry` | 30 Hz | MAVROS | |
| `mavros/hrlv_ez4_pub` | `sensor_msgs/Range` | 10 Hz | MAVROS (`distance_sensor` plugin) | down-facing ToF (PX4 `distance_sensor` instance 0, LW20/C on the drone), frame `hrlv_ez4_sonar` (MAVROS' stock config name; rename = override the plugin's `config`). `range >= max_range` means no valid reading. BEST_EFFORT |
| `mavros/imu/data` | `sensor_msgs/Imu` | 50 Hz | MAVROS | FC IMU (not ZED IMU) |
| `mavros/battery` | `sensor_msgs/BatteryState` | 1 Hz | MAVROS | sim: SITL battery model |
| `mavros/global_position/global` | `sensor_msgs/NavSatFix` | 5 Hz | MAVROS | may be empty when GPS disabled |
| `zed/zed_node/left/color/rect/image` | `sensor_msgs/Image` | 15–30 Hz | Isaac cam / ZED wrapper | `bgra8`/`rgb8` per wrapper |
| `zed/zed_node/right/color/rect/image` | `sensor_msgs/Image` | same | Isaac cam / ZED wrapper | |
| `zed/zed_node/left/color/rect/camera_info` | `sensor_msgs/CameraInfo` | same | Isaac cam / ZED wrapper | intrinsics of the camera in use — read them, never hard-code `K` (sim `sdk`: the extension's `ZED_M` lens, HD720 `fx` 529.8 px; a real unit has its own factory calibration) |
| `zed/zed_node/right/color/rect/camera_info` | `sensor_msgs/CameraInfo` | same | Isaac cam / ZED wrapper | stereo baseline = `-P[0,3] / P[0,0]` (ZED Mini 63 mm); stereo consumers read it from here |
| `zed/zed_node/depth/depth_registered` | `sensor_msgs/Image` (`32FC1`, metres) | same | Isaac depth / ZED | |
| `zed/video/optical_flow` | `sensor_msgs/Image` (`bgr8`, same size) | ≤ 15 Hz | `zed-video` node | dense Farneback flow of the **left** image between consecutive frames: hue = direction, brightness = speed, black = still. Visualisation only (no metric flow); header of the left frame. Only while subscribed; RELIABLE; needs `services.qgc_video` on with `layout: grid` |
| `zed/zed_node/point_cloud/cloud_registered` | `sensor_msgs/PointCloud2` | ≤ 10 Hz | sim `zed_depth.py` / ZED wrapper | heavy: sim publishes only while subscribed. Organized, NaN = no depth; fields `x y z rgb` (float32, rgb PCL-packed); frame `zed_left_camera_frame` (x fwd); sim samples every 4th pixel |
| `zed/zed_node/disparity/disparity_image` | `stereo_msgs/DisparityImage` | ≤ 10 Hz | sim `zed_depth.py` / ZED wrapper | optional, `depth.publish_disparity`; left optical frame |
| `zed/zed_node/mapping/fused_cloud` | `sensor_msgs/PointCloud2` | ~1 Hz | sim `zed_depth.py` / ZED wrapper | optional, `mapping.mapping_enabled`; sim frame `odom`, wrapper `map` |
| `zed/zed_node/imu/data` | `sensor_msgs/Imu` | 200 Hz | Isaac physics IMU (both sim sources) / ZED wrapper | frame `zed_imu_link`. In sim `sdk` the streamed ZED has no usable sensor channel, so the sim publishes this topic itself (`docs/zed-sdk-sim.md`) |
| `zed/zed_node/odom` | `nav_msgs/Odometry` | 30–60 Hz | sim `emulated`: `vio_mock`; sim `sdk` and real: ZED positional tracking | `odom` → `base_link` (wrapper default `zed_camera_link`; relay re-parents to `base_link`). Only ONE source per run: never `vio_mock` and the wrapper on the same topic |
| `vehicle/state` | `bisg_msgs/VehicleState` | 2 Hz | `bisg_vehicle/health` | id, mode, armed, battery %, pose, vio_ok, last_error |
| `tf`, `tf_static` | | | | frames above |

## Topics — consumed by the vehicle

| Topic (under `/drone_<n>/`) | Type | Producer | Notes |
|---|---|---|---|
| `mavros/setpoint_position/local` | `geometry_msgs/PoseStamped` | `bisg_vehicle/offboard_controller` | ≥ 10 Hz while OFFBOARD |
| `mavros/setpoint_raw/local` | `mavros_msgs/PositionTarget` | same | velocity/accel setpoints |
| `mavros/odometry/out` | `nav_msgs/Odometry` | `vio_relay` (real) / `vio_mock` (sim) | ENU/FLU in; MAVROS converts to PX4 NED/FRD; frame ids `odom`/`base_link`; stamp = sample capture time on the vehicle clock (sim time in sim) — PX4 fuses the sample at that time, so a wrong clock is a wrong measurement |
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
3. TF chain `map → odom → base_link → zed_left_camera_optical_frame` resolvable.
4. `camera_info` width/height equal to the ZED model table in `hardware.md`; `K` is the camera's own (see the `camera_info` row), baseline `-P[0,3]/P[0,0]` = 63 mm.

`tests/zed_sdk_check.py` (`./bisg zed check`) already implements the ZED half of these checks for the real SDK, in sim and on the drone (`--no-gt`).

Known gap: the frame names above carry a `drone_<n>/` prefix, which the real wrapper cannot publish ([B16](bugs.md#b16)); in sim `sdk` the wrapper's own unprefixed frames are what you see.
