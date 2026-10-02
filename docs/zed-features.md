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

## Sim GUI overlay (sim only)

Scenario `sensors.zed.view`: live point cloud and fused map drawn over the main viewport
(`point_cloud`, `fused_cloud`, `draw_color: depth|rgb`, point sizes, caps), plus the
`preview` window (left image | depth). It is drawn by `sim/launcher/zed_depth.py` /
`zed_preview.py`, and never appears in the ZED camera images.

## Checks

- `tests/zed_depth_box.py`: point cloud against the `depth_box` in `single_iris_vio` (front face ±mm).
- Fused map (2026-09-26, square flight, 5 cm voxels): box front face voxel centre 3.525 m (true face
  3.500), 0% of voxels below the floor, 83% on the floor plane. Disparity: f·T/d reproduces the depth
  (0.12–9.79 m).
