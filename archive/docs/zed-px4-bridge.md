# ZED SDK → PX4 bridge (plan)

**Status: plan only.** The one prototype that exists is the obstacle-distance node (module M2, partly verified, below).
Goal: one container / one node that takes **every ZED SDK feature that PX4 can use** and delivers it to PX4 over MAVLink,
the same in the Isaac sim and on the Jetson. Implement and test module by module (order in §6).

## 1. Architecture decisions

| Decision | Choice | Why |
|---|---|---|
| Source of ZED data | the **zed_wrapper ROS 2 topics/services** (same in sim `ZED_SOURCE=sdk` and on the Jetson), not `pyzed` directly | one contract (`interface-contract.md`), no second process owning the camera, works unchanged in both worlds. `pyzed` only if a feature has no wrapper output (checked per module). |
| Path to PX4 | **through MAVROS, lean plugin list** (ADR-001 + [study-px4-link.md](study-px4-link.md): MAVSDK 4.x native is the gated alternative; DDS cannot carry landing/follow target, STATUSTEXT, params, camera protocol): typed plugin topics where a plugin exists; for any other MAVLink message the raw `/<ns>/mavlink_sink` topic (`mavros_msgs/Mavlink`, packed with pymavlink) | keeps one MAVLink link, one sysid/timesync, no second UDP/serial owner. |
| Packaging | one node `zed_px4_bridge` (rclpy), **plugin-style modules** switched in a YAML next to `deploy/jetson/zed_params.yaml`, one compose service `zed-px4` (profile `zed`) on the existing `bisg/ros` image (amd64 + arm64 Jetson) | the "every feature" bridge is a table of small independent modules; each can be off, tested alone, and fail alone. |
| Health | every module publishes a status; a module that loses its input **stops sending** (PX4 must see silence, not stale data) and reports via STATUSTEXT | PX4 failsafes key on message timeout. |
| Time | all stamps = sample capture time on the vehicle clock (sim time in sim); MAVROS timesync | already the contract for odometry. |
| Frames | ZED/ROS ENU-FLU in, MAVROS converts to NED/FRD; body-frame messages declare `MAV_FRAME_BODY_FRD` explicitly | the obstacle plugin defaults to GLOBAL — found the hard way, see M2. |

New ADR (ADR-006) when implementation starts: "ZED→PX4 bridge = one rclpy node over MAVROS, wrapper topics as input".

## 2. Feature map: ZED SDK feature → MAVLink → what PX4 does with it

PX4 v1.17 accepts (verified in `mavlink_receiver.cpp` of the pinned firmware): `ODOMETRY`, `VISION_POSITION_ESTIMATE`,
`ATT_POS_MOCAP`, `OBSTACLE_DISTANCE`, `DISTANCE_SENSOR`, `OPTICAL_FLOW_RAD`, `LANDING_TARGET`, `FOLLOW_TARGET`,
`ADSB_VEHICLE`, `SET_GPS_GLOBAL_ORIGIN`, `HIL_GPS`, `SET_POSITION_TARGET_*`, `ONBOARD_COMPUTER_STATUS`, `STATUSTEXT`,
`NAMED_VALUE_FLOAT/INT`, `DEBUG*`, `TUNNEL`. **Not** accepted: `GPS_INPUT` (ArduPilot only), `CAMERA_TRACKING_*` (that goes
to the GCS, not the autopilot). Sources: ZED SDK modules ([docs](https://docs.stereolabs.com/docs/development/zed-sdk/modules)),
PX4 [external position estimation](https://docs.px4.io/main/en/ros/external_position_estimation),
[collision prevention](https://docs.px4.io/main/en/computer_vision/collision_prevention),
[follow me](https://docs.px4.io/main/en/flight_modes_mc/follow_me), [MAVLink camera v2](https://docs.px4.io/main/en/camera/mavlink_v2_camera),
[landing target protocol](https://mavlink.io/en/services/landing_target.html).

| # | ZED feature (wrapper output) | MAVLink to PX4 | MAVROS route | PX4 consumer / params | Status |
|---|---|---|---|---|---|
| M1 | **Positional tracking** (`odom`, `pose_with_covariance`, tracking status) | `ODOMETRY` (+ `quality`, `reset_counter`, covariance) | `odometry/out` | EKF2 external vision: `EKF2_EV_CTRL`, `EKF2_HGT_REF=3`, `EKF2_EV_DELAY`, `EKF2_EV_NOISE_MD`, `EKF2_EV_POS_X/Y/Z` (lever arm) | **sim: `vio_mock`; real: `vio_relay` does not exist yet** (bugs.md). Add: quality from covariance, `reset_counter` on tracking reset / loop-closure jump, stop sending when tracking lost. |
| M2 | **Depth** (`depth_registered`) | `OBSTACLE_DISTANCE` (72 x 5° body-FRD sectors) | `obstacle/send` (LaserScan) + set plugin param `mav_frame=BODY_FRD` | collision prevention in Position mode: `CP_DIST`, `CP_DELAY`, `CP_GUIDE_ANG`, `CP_GO_NO_DATA`; PX4 streams the fused map back → **QGC proximity radar** | **prototype written** (`docker/ros/obstacle_distance.py`, `./bisg obstacle`) |
| M3 | **Depth / plane detection** (floor plane, `plane` service) | `DISTANCE_SENSOR` (height over ground, pitch/roll-compensated) | raw `mavlink_sink` (the `distance_sensor` plugin is denylisted in `px4_pluginlists.yaml` and is receive-oriented) | EKF2 range aid `EKF2_RNG_CTRL`, `EKF2_RNG_*`; landing detection, terrain hold | todo |
| M4 | **Spatial mapping** (`fused_cloud`, mesh) | — (no PX4 consumer) | stays in ROS | feeds a companion planner / 3D obstacle map later; optionally multi-height `OBSTACLE_DISTANCE` | out of scope for the MAVLink bridge; keep as ROS product |
| M5 | **Object detection + tracking** (`obj_det/objects`, 3D boxes, velocity) | `FOLLOW_TARGET` (target lat/lon/alt/vel) for Follow-Me; `LANDING_TARGET` for a detected pad class; optional `ADSB_VEHICLE` for aircraft | raw `mavlink_sink` (`FOLLOW_TARGET`), `landing_target/pose` | Follow-Me mode `NAV_FT_*`; precision landing `LTEST_*`, `PLD_*`; needs a global frame: camera ray x drone pose → needs GPS or a local-origin variant via offboard | todo |
| M6 | **Body tracking** (`body_trk/skeletons`) | `FOLLOW_TARGET` for a person; gestures → `COMMAND_LONG` (land / hold / follow) with an allow-list | raw `mavlink_sink` / `cmd/command` | Follow-Me; safety: only whitelisted commands, rate-limited, optional | todo |
| M7 | **Global localization / GNSS fusion** (`geo_pose`) | `SET_GPS_GLOBAL_ORIGIN` once; fused pose still goes as `ODOMETRY` (M1) | `global_position/set_gp_origin` | `EKF2_*` origin; **reverse direction**: PX4 GPS → ZED Fusion (`NavSatFix` from `mavros/global_position/raw/fix` into the wrapper's GNSS input) | todo (outdoor only) |
| M8 | **Optical flow from VIO** | `OPTICAL_FLOW_RAD` + `DISTANCE_SENSOR` | `px4flow/raw/send` | `EKF2_OF_CTRL`; only a fallback when external vision is rejected | low priority (EV velocity already fused) |
| M9 | **Sensors** (IMU, temperature; mag/baro absent on ZED Mini) | `NAMED_VALUE_FLOAT` telemetry; `ONBOARD_COMPUTER_STATUS` (Jetson CPU/GPU/temp/mem) | `debug_value/send`, `onboard_computer/status` | none (QGC / logs) | todo |
| M10 | **Camera health** (`health_status`, `odometry_status`, depth validity %, fps) | `STATUSTEXT`, `NAMED_VALUE_FLOAT` (`zed_track`, `zed_fps`, `zed_depth_ok`); quality into M1/M2 | `statustext/send`, `debug_value/send` | operator + `COM_ARM` style preflight gating by the bridge refusing to publish EV until healthy | todo |
| M11 | **Video + camera controls** (`left/image`, exposure/gain, SVO record) | `CAMERA_INFORMATION`, `VIDEO_STREAM_INFORMATION`, `CAMERA_TRACKING_IMAGE_STATUS` (draw M5 boxes in QGC), `MAV_CMD_VIDEO_START/STOP_CAPTURE` → `start_svo_rec` service, `MAV_CMD_REQUEST_CAMERA_*` replies | raw `mavlink_sink` as a camera **component** (`MAV_COMP_ID_CAMERA` 100) | none in PX4; QGC auto-detects the stream (today: set "UDP h.264" by hand) + shows tracked boxes | video itself **done** (`./bisg video`); component = todo |
| M12 | **Region of interest / depth confidence** | — | — | internal quality inputs to M2/M3 (mask the drone's own props, drop low-confidence pixels) | todo (sim: confidence not simulated) |
| M13 | **Streaming / SVO** | — | — | not PX4-related; SVO via M11 command | covered by M11 |

## 3. PX4 → bridge (the other direction)
GPS fix + `home_position` + `local_position` + `state` + `extended_state` (landed / in-air) → gate modules (no EV before armed-ready,
disable follow when not in the right mode), M7 GNSS ingest, M5 world-frame projection of detections.

## 4. Interfaces
- Config: `deploy/jetson/zed_px4.yaml` (modules on/off + per-module params), merged with a sim overlay like `zed_sim_overlay.yaml`.
- New topics only under `/<ns>/zed_px4/…` (status per module); documented in `interface-contract.md` before use.
- CLI: `./bisg zed-px4 up|down|logs|status` (the existing `./bisg obstacle` folds into it).
- Compose: `zed-px4` (workstation, profile `zed`) and the same service in `deploy/jetson/compose.yaml` (arm64).

## 5. Test approach (one per module, sim first)
Every module gets: a unit check on recorded rosbag input, a sim flight test in `tests/` with numeric PASS/FAIL (like
`tests/vio_flight.py`, `tests/hover_stability.py`), and a QGC/PX4-side observation (`./bisg debug px4 "listener …"`).
Sim reach: `ZED_SOURCE=sdk` runs the real SDK (depth, tracking, mapping, plane, **object/body detection if models + actors are in
the scene**); the emulated rig has depth + `vio_mock` only.

| Module | Sim test | PASS when |
|---|---|---|
| M1 | `tests/vio_flight.py` with the bridge instead of `vio_mock` (sdk mode) | trajectory RMSE ≤ 0.15 m, EKF2 EV fused, no `reset_counter` jumps; lost-tracking test: block the camera → bridge goes silent, PX4 falls back / failsafe as configured |
| M2 | `tests/collision_prevention.py` (written) | drone stops ≥ `CP_DIST` − slack from the wall with the stick held; `listener obstacle_distance_fused` populated; QGC radar draws sectors |
| M3 | hover at 1/2/3 m, tilt ±15° | `DISTANCE_SENSOR` height within 5 % of truth; EKF2 uses range (`ekf2 status`) |
| M5/M6 | people / vehicle actor walking in the scene (Pegasus people extension) | `FOLLOW_TARGET` position error ≤ 0.5 m; Follow-Me holds distance |
| M7 | outdoor world with GNSS from the sim (GPS scenario) | global pose within 1 m of truth |
| M9/M10/M11 | topic/stream presence checks; QGC shows stream without manual setup; STATUSTEXT on forced faults | as listed |

## 6. Order of work
1. **Skeleton + health (M10)**: node, YAML module switches, status topics, STATUSTEXT, compose/CLI/ADR-006, raw `mavlink_sink` helper (pack any message).
2. **M1** `vio_relay` inside the bridge (quality, reset counter, silence on loss) — needed for the real drone anyway.
3. **M2** finish: closed-loop test + QGC radar check (below), then fold the prototype into the bridge.
4. **M3** floor distance sensor.
5. **M11** camera component (QGC auto video, later tracking boxes).
6. **M5 / M6** detections → Follow-Me / landing target (needs sim actors and models first).
7. **M7** GNSS two-way, then M8/M9/M12 as needed.
8. Jetson arm64 parity pass for every module (`jetson-deploy` skill).

## 7. M2 prototype: what exists and what is verified (2026-10-04)
Files: `docker/ros/obstacle_distance.py`, compose service `obstacle`, `./bisg obstacle up|down|logs`,
`deploy/px4/collision_prevention.params` (`CP_DIST 1.5`, set as `px4.params_file` of `single_iris.yaml`),
`tests/collision_prevention.py`, config keys `OBST_*` in `config/bisg.conf`.
- Verified: node runs, sets the MAVROS obstacle plugin to `BODY_FRD`, PX4 receives `obstacle_distance` (frame 12, 5° increments,
  `angle_offset -180`, max 800 cm) and publishes `obstacle_distance_fused` (so the QGC radar has data to show; not yet looked at in QGC).
- **Not verified:** the closed-loop stop. `tests/collision_prevention.py` flies, enters Position mode and holds the stick via
  `mavros/manual_control/send`, but the drone did not move in 3 attempts: PX4's manual-control selector keeps another source
  (QGC's on-screen virtual joystick sends zeros) and, separately, mavros passes stick values unscaled (use −1000…1000).
  Next try: disable QGC's virtual joystick (or run without QGC), or use `COM_RC_IN_MODE`/offboard velocity; then rerun.
- Known limits: only the height band ±0.6 m around the camera is considered (floor not an obstacle once ≥ 1 m up; on the ground the floor reads as 0.3 m);
  FOV only ±45° so the rest is "no data" (`CP_GO_NO_DATA 0`); PX4 collision prevention acts in Position mode, not Auto/Offboard.
