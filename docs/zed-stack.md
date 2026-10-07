# The ZED Mini stack

Everything the ZED SDK can do on this drone is switched in **one file, `docker/zed/zed.yaml`**, and runs from **one image
(`bisg/zed`)** — in the Isaac sim and on the Jetson, same file, same launch, same services.

```
docker/zed/zed.yaml ──► python3 -m zed_stack compile ──► zed_wrapper (ZED SDK 5.4.1) ──► /drone_<n>/zed/zed_node/*   (images, depth, odom, AI, ...)
        │                                                                                      │
        └─► services:  zed-bridge  (health · odometry · obstacle_distance) ──► MAVROS ──► PX4  ◄┘
                       zed-video   (left image ──► RTP/H.264 ──► QGroundControl)
```

## Use

```bash
./bisg zed plan                              # what is on: SDK modules, the topics each publishes, the services that start
./bisg zed set object_detection.enabled=true # edit one key (comments kept, validated before it is written)
./bisg zed up                                # wrapper + every enabled service        (sim: ZED_SOURCE=sdk ./bisg all headless first)
./bisg zed services                          # after a `set` on a `services.*` key: restart only the side services
./bisg zed status | logs [wrapper|bridge|video] | check | down
./bisg zed test                              # unit tests + the bridge against fake topics — no camera, no sim
```

On the Jetson: `./bisg drone up`.

## docker/zed/zed.yaml

One block per [ZED SDK module](https://docs.stereolabs.com/docs/development/zed-sdk/modules). Inside a block the keys are the
**wrapper's own parameter names** (every one is documented in `docker/zed/zed-ros2-wrapper/zed_wrapper/config/common_stereo.yaml`);
`enabled` is the module's master switch. A key the wrapper does not know, a value of the wrong type or a bad enum
(`pos_tracking_mode: GEN_2`) is rejected by `./bisg zed plan` with a suggestion — before any container starts. The checks read the
wrapper's shipped YAML, so they follow the pinned wrapper version. A module that needs depth while `depth.enabled: false` is an error.

| Block | SDK module | Master switch | Topics (`/drone_<n>/zed/zed_node/…`) | Sim, `ZED_SOURCE=sdk` |
|---|---|---|---|---|
| `camera` | Camera | – | resolution, fps, flip, timeouts | verified |
| `video` | Camera / video + controls | `publish_*` | `left\|right/color/rect/image`, `…/camera_info`, `rgb/`, `*/raw/`, `*/gray/`, `stereo/` | verified (left/right) |
| `sensors` | Sensors | `publish_*` | `imu/data`, `imu/data_raw` (ZED Mini: IMU only, no mag/baro/temp) | `imu/data` published by the sim itself (the stream has no sensor channel) |
| `depth` | Depth sensing | `enabled` (false → `depth_mode: NONE`) | `depth/depth_registered`, `point_cloud/cloud_registered`, `disparity/…`, `confidence/…`, `depth/depth_info` | verified (all five; disparity = f·T/depth exactly) |
| `region_of_interest` | Region of interest | `enabled` | `roi_mask/image` | runs, publishes no mask (nothing of the robot is in the sim view); test on hardware |
| `positional_tracking` | Positional tracking | `enabled` | `odom`, `pose`, `pose/status`, `pose_with_covariance`, `path_*`, `pose/landmarks` | verified: all topics; RMSE 0.088 m over a takeoff + 4 m square + landing |
| `global_localization` | Global localization (GNSS fusion) | `enabled` | `geo_pose`, `pose/filtered`, `pose/fused_fix` | no (we fly GPS-denied) |
| `spatial_mapping` | Spatial mapping | `enabled` | `mapping/fused_cloud` | verified (40 k points; **+4 GB RAM**) |
| `plane_detection` | Plane detection | `enabled` | `plane`, `plane_marker` | verified (clicked point in the `odom` frame) |
| `object_detection` | Object detection + tracking (AI) | `enabled` | `obj_det/objects`; per-class switches under `classes:` | runs at the camera rate (model: 278 s first start, +4 GB RAM); accuracy untested: no people/vehicles in the scene |
| `body_tracking` | Body tracking (AI) | `enabled` | `body_trk/skeletons` | runs at the camera rate (80 s first start, **+7 GB RAM**); accuracy untested |
| `streaming` | Streaming | `enabled` | – (open the stream with the SDK elsewhere) | **crashes the wrapper in the sim** (B19); real camera only |
| `recording` | SVO recording | – | services `start_svo_rec` / `stop_svo_rec` | not meaningful in sim: record a rosbag |

`publish_*` keys only **advertise** a topic; the wrapper computes it while something subscribes, so leaving one on costs nothing.
Frame ids and rates follow [interface-contract.md](interface-contract.md). Heavy AI models and `NEURAL*` depth modes must be
measured on the Orin NX before they are relied on.

**Runtime toggles** (no restart): the wrapper exposes services `enable_depth`, `enable_mapping`, `enable_obj_det`,
`enable_body_trk`, `enable_streaming` (`std_srvs/SetBool`), `reset_odometry`, `reset_pos_tracking`, `set_pose`, `set_roi` / `reset_roi`,
`save_area_memory`, `start_svo_rec` / `stop_svo_rec`, under `/drone_<n>/zed/zed_node/`. `./bisg zed enable object_detection on|off` wraps the SetBool ones.

### `sim:` — the only sim-vs-Jetson differences
The `sim:` block at the bottom is merged over everything above **only** in the sim (`ZED_STACK_SIM=1`, set by the sim compose services and
the emulated rig). Today: `imu_fusion: false` (the stream has no 400 Hz IMU; GEN_3 refuses a low-rate one), `sensors_image_sync: true`,
and the bridge's `odometry` module off + `restamp` on. Anything else that differs between sim and hardware belongs in
[zed-sdk-sim.md](zed-sdk-sim.md), not in a script.

## Services

### `px4_bridge` (compose `zed-bridge`) — ZED → PX4 through MAVROS
One rclpy node (`docker/zed/zed_stack/bridge/`), one module per feature, each switched under `services.px4_bridge`. It talks to MAVROS over DDS
(ADR-001, lean plugin list `docker/ros/mavros_lean.yaml`); it needs MAVROS, not the other way round. Modules go **silent** when their
input is lost — PX4's own timeouts and failsafes then act, rather than acting on stale data.

| Module | In → out | Notes |
|---|---|---|
| `health` | `status/health`, `pose/status`, depth validity → `zed_stack/status` (JSON, 1 Hz) + STATUSTEXT in QGC | tells the operator *why* another module went silent: "ZED tracking: LOST (odometry_status=1)" |
| `odometry` | `odom` → `mavros/odometry/out` → EKF2 external vision | silent while `odometry_status != OK` or the source is slower than `min_rate_hz`; frames fixed to `odom`/`base_link` (what MAVROS matches); `restamp` stamps with the node clock (sim: PX4 runs on `/clock`, the wrapper on wall time — B17). Lever arm of the camera: `EKF2_EV_POS_X/Y/Z` |
| `obstacle_distance` | `depth_registered` → 72×5° sector map → `mavros/obstacle/send` → PX4 collision prevention (`CP_DIST`, `docker/sim/px4/collision_prevention.params`) + QGC proximity radar | height band ±`band` m around the camera; FOV ±45°, the rest "unknown" (`CP_GO_NO_DATA 0`); acts in Position mode only |

**Not built yet** (listed so nothing is assumed): `DISTANCE_SENSOR` height-over-ground (M3, plane/depth based), MAVLink camera component so QGC
finds the video itself (M11), `FOLLOW_TARGET` / `LANDING_TARGET` from object/body detection (M5/M6, needs actors in the sim and `zed_msgs` in
the bridge), PX4 GPS → ZED GNSS fusion (M7). The raw-MAVLink route for those is `mavros/mavlink_sink`; PX4 accepts
`ODOMETRY, OBSTACLE_DISTANCE, DISTANCE_SENSOR, LANDING_TARGET, FOLLOW_TARGET, OPTICAL_FLOW_RAD, ONBOARD_COMPUTER_STATUS, STATUSTEXT, NAMED_VALUE_*`
and not `GPS_INPUT`.

**Adding a module:** a class in `docker/zed/zed_stack/bridge/` (`Module` base in `common.py`: subscribe in `__init__`, return `{"state": ...}` from `status()`),
register it in `node.py:MODULES`, its defaults in `config.py:SERVICES`, its topics in `topics.py:BRIDGE`, a case in `tests/zed_bridge_fake.py`.

### `qgc_video` (compose `zed-video`) — video in QGroundControl
Left image → GStreamer → RTP/H.264 UDP (x264, or `nvv4l2h264enc` on the Jetson). Set `services.qgc_video.enabled: true`, `./bisg zed services`; in QGC:
**Application Settings → Video → Source "UDP h.264 Video Stream", port 5600**. `./bisg zed video` starts only this sender, whatever `enabled` says, and
works on the emulated rig too (no `zed_wrapper`). `--video-host H` (on `zed video` or `zed up`) streams to a remote QGC; H is an IP or a tailnet device
name (`./bisg tailscale status`). UDP: LAN or Tailscale, not an SSH tunnel. `./bisg zed video-test` plays it on the host without QGC (close QGC's video
first: one receiver per port). Black video while `zed logs video` says "no frames": the host's `net.core.rmem_max` is too small for CycloneDDS to
reassemble an image (`./bisg check`, `docs/setup.md`).

## Files

| | |
|---|---|
| `docker/zed/zed.yaml` | the one config |
| `docker/zed/zed_stack/config.py`, `__main__.py`, `topics.py` | load · validate · compile to wrapper params · `plan` / `compile` / `set` (pure Python + PyYAML; also imported by the sim launcher for the emulated rig) |
| `docker/zed/zed_stack/bridge/`, `docker/zed/zed_stack/video.py` | the two services |
| `docker/zed/` | `bisg/zed` = Stereolabs' image + CycloneDDS + `mavros_msgs` + GStreamer (`Dockerfile.overlay`); `build.sh desktop\|jetson`; `build_isaac_ext.sh` |
| `docker/zed/zed_drone.launch.py` | wrapper launch with the contract's topic names — shared by sim and Jetson |
| `docker/compose.yaml` | `zed` (sim twin) / `drone-zed` (real camera), `zed-bridge`, `zed-video`, `px4-bridge` (serial, via `./bisg px4-bridge up --hw`); profiles `zed` and `drone` |
| `scripts/zed.sh` | `./bisg zed …` |
| `tests/unit/`, `tests/zed_bridge_fake.py`, `tests/zed_sdk_check.py` | config + maths tests · bridge on fake topics · live SDK check (sim and Jetson, `--no-gt`) |

## Checks
- `./bisg zed bench` — tests every SDK module above on one wrapper and measures rate / CPU / RAM / GPU per module: **[zed-benchmark.md](zed-benchmark.md)** (16/16 phases pass in the sim).
- `./bisg zed test` — 15 unit tests (compile, validation, `set`, sector maths) and the bridge on fake topics (obstacle sectors, odometry frames/restamp/silence on lost tracking/recovery, STATUSTEXT, status JSON).
- `./bisg zed check` — the real SDK in the sim: streams, geometry (HD720, 63 mm baseline), depth, health flags, tracking vs ground truth.
- Emulated rig (`ZED_SOURCE=emulated`): `docker/zed/zed.yaml` still decides which products the sim publishes (`sim/launcher/zed_features.py` reads it through `zed_stack`); a switch that is on but not simulated is logged at startup.
