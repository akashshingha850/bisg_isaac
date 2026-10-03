# ZED Mini — ZED SDK features and their switches

What the ZED SDK (5.4.1, via `zed_wrapper`) can do with our camera, where each feature is switched
on, and what the Isaac sim does with that switch.

**One file switches features for both the real drone and the sim:** `deploy/jetson/zed_params.yaml`
(the zed_wrapper overlay). The sim launcher reads it too (`sim/launcher/zed_features.py`). To try a
feature in one sim scenario only, override it in that scenario's `sensors.zed.features` (same
nesting). At startup the sim logs the simulated switches that are on, and warns about any switch
that is on but **not simulated**.

`publish_*` switches only *advertise* a topic. The wrapper (and the sim) publishes it only while
something subscribes, so a switch left on costs nothing until it's used. Topics are under
`/drone_<n>/zed/zed_node/`.

| Feature | What it gives you | Switch (`zed_params.yaml`) | Topic(s) | ZED Mini | Sim |
|---|---|---|---|---|---|
| Rectified stereo images | left/right colour images + intrinsics | `video.publish_left_right` | left/right image + camera_info | yes | **yes** (Isaac cameras) |
| RGB alias, raw, grey, side-by-side | same images under other names / formats | `video.publish_rgb`, `publish_raw`, `publish_gray`, `publish_stereo` | `rgb/…`, `…/raw/…`, `…/gray/…`, `stereo/…` | yes | no |
| IMU | 6-axis accel + gyro | `sensors.publish_imu` (`publish_imu_raw`) | `imu/data` (`imu/data_raw`) | yes | **yes** (one sample per physics step) |
| Magnetometer / barometer / temperature | — | `sensors.publish_mag/baro/temp` | — | **no hardware** (ZED 2/2i only) | — |
| Depth map | metric depth per pixel, aligned to left | `depth.publish_depth_map` | `depth/depth_registered` (32FC1 m) | yes | **yes** (exact geometry) |
| Depth mode | stereo network: quality vs Orin NX load | `depth.depth_mode` (NEURAL_LIGHT/NEURAL/NEURAL_PLUS) | — | yes | n/a (sim depth is exact) |
| Point cloud | 3D colour points of the view | `depth.publish_point_cloud`, `point_cloud_freq`, `point_cloud_res` | `point_cloud/cloud_registered` | yes | **yes** (COMPACT = every 4th px, REDUCED = 8th) |
| Disparity | stereo disparity (px), d = f·B/Z | `depth.publish_disparity` | `disparity/disparity_image` | yes | **yes** (from depth) |
| Depth confidence | per-pixel confidence | `depth.publish_depth_confidence` | `confidence/confidence_map` | yes | no (sim depth has no uncertainty) |
| Depth info | min/max depth per frame | `depth.publish_depth_info` | `depth/depth_info` (zed_msgs) | yes | no (no zed_msgs in the images) |
| Region of interest | mask the drone's own parts out of depth/VIO | `region_of_interest.automatic_roi` | `roi_mask/image` | yes | no (sim view is clear) |
| Positional tracking (VIO) | 6-DoF odometry → PX4 EKF2 external vision | `pos_tracking.pos_tracking_enabled`, `publish_odom_pose` | `odom`, `pose` | yes | **yes** — `vio_mock` (always on; the EKF needs it) |
| Pose covariance, paths, landmarks | pose+cov, trajectories, VIO landmarks | `pos_tracking.publish_pose_cov`, `publish_cam_path`, `publish_3d_landmarks` | `pose_with_covariance`, `path_odom`, `path_map`, landmarks | yes | no |
| Area memory | relocalise / loop-close in a saved site map | `pos_tracking.area_memory`, `area_file_path` | — | yes | no |
| Spatial mapping | fused colour point cloud of everything seen | `mapping.mapping_enabled`, `resolution`, `max_mapping_range`, `fused_pointcloud_freq` | `mapping/fused_cloud` | yes | **yes** (voxel map, frame `odom`, + GUI overlay) |
| Plane detection | plane at an RViz-clicked point | `mapping.publish_det_plane` | `plane`, `plane_marker` | yes | no |
| Object detection (AI) | 3D boxes + tracking: people, vehicles, animals, … | `object_detection.od_enabled`, `detection_model` | `obj_det/objects` | yes (NVIDIA GPU; heavy on Orin NX) | no |
| Body tracking (AI) | 3D human skeletons | `body_tracking.bt_enabled` | `body_trk/skeletons` | yes | no |
| GNSS fusion | GPS + VIO → global pose | `gnss_fusion.gnss_fusion_enabled` | `geo_pose`, … | yes | no (we fly GPS-denied) |
| Streaming | send the camera over the network (H.264/H.265) | `stream_server.stream_enabled` | — | yes | no |
| SVO recording | record raw stereo for replay without the camera | service `start_svo_rec` / `stop_svo_rec` | — | yes | no (record rosbags instead) |

"yes" under ZED Mini: the SDK supports the feature on this camera; confirm heavy AI models
(object detection, body tracking) on the Orin NX before relying on them.

## SDK mode (`ZED_SOURCE=sdk`): the features run in the real SDK

The **Sim** column above describes the `emulated` rig. With `ZED_SOURCE=sdk` (`docs/zed-sdk-sim.md`) the unmodified wrapper runs
against Isaac's streamed ZED Mini twin, so a switch in `deploy/jetson/zed_params.yaml` does what it does on the drone. Status of
what has actually been exercised (2026-10-03, `./bisg zed check` + a 4 m square flight):

| Feature | SDK mode | Notes |
|---|---|---|
| Rectified stereo images + camera_info | **verified** | 20-22 Hz per simulated second, 63.0 mm baseline |
| Depth map (`NEURAL_LIGHT`) | **verified** | the SDK's own stereo matching on the rendered pair: 78-79 % valid pixels, 0.24-11.2 m in the warehouse |
| Point cloud | **verified** | 19-22 Hz sim time |
| Positional tracking (GEN_3, visual-only) | **verified** | odometry path 21.87 m vs truth 21.64 m (1.01) over takeoff, 4 m square, landing; trajectory RMSE 0.088 m, end error 0.024 m |
| Health / tracking status topics | **verified** | all `low_*` flags false, `odometry_status` OK |
| IMU `imu/data` | sim-published | the stream has no usable sensor channel; the sim publishes the same topic (`zed_rig.publish_imu`). `imu_raw`, mag, baro, temperature: not available |
| Disparity, confidence, depth info, ROI mask | should work, **not yet exercised** | depth-derived, no extra sim input; switch on and run `./bisg zed check` + `ros2 topic hz` |
| Spatial mapping, plane detection, pose covariance, paths, area memory | should work, **not yet exercised** | need tracking + depth only |
| Object / body detection | should work, **not yet exercised** | model download + GPU load; heavy even on the workstation |
| Streaming server, SVO recording | not meaningful | the camera *is* a stream; record rosbags instead |
| IMU-fused tracking (`imu_fusion: true`) | **not possible in sim** | the stream carries a frame-rate IMU; only the real camera tests it |

## Sim GUI overlay (emulated rig only)

Scenario `sensors.zed.view`: live point cloud and fused map drawn over the main viewport
(`point_cloud`, `fused_cloud`, `draw_color: depth|rgb`, point sizes, caps), plus the
`preview` window (left image | depth). It is drawn by `sim/launcher/zed_depth.py` /
`zed_preview.py`, and never appears in the ZED camera images.

## Checks

- `tests/zed_depth_box.py`: point cloud against the `depth_box` in `single_iris_vio` (front face ±mm).
- Fused map (2026-09-26, square flight, 5 cm voxels): box front face voxel centre 3.525 m (true face
  3.500), 0% of voxels below the floor, 83% on the floor plane. Disparity: f·T/d reproduces the depth
  (0.12–9.79 m).
