# Visual-inertial SLAM / VIO with loop closure or relocalization for bounding drift on an indoor GPS-denied drone (ZED Mini + PX4)

Research date: 2026-10-26. Scope: ZED SDK positional tracking (GEN_1/GEN_2/GEN_3), classical VIO/SLAM (ORB-SLAM3, VINS-Mono/Fusion, Kimera, Basalt, OpenVINS), learned / GPU systems (DROID-SLAM, DPV-SLAM, MAC-VO, cuVSLAM), PX4 integration, and how much loop closure helps in practice. Numbers are as reported by each paper's authors unless stated otherwise. Benchmark protocols differ between papers, so numbers from different tables are not directly comparable.

## 1. ZED SDK positional tracking (GEN_1 / GEN_2 / GEN_3), area memory, loop closure, status reporting, .area relocalization, ROS 2 parameters

### Takeaway
In SDK 5.x, GEN_3 is the default mode. It is feature-based VSLAM with loop closure, global optimization and `.area` relocalization. GEN_1 is dense, depth-driven VIO and was not designed for loop closure. GEN_2 is deprecated. On loop closure GEN_3 corrects the trajectory. In ROS 2 the correction shows up in the `map -> odom` TF, and by default odometry is also reset (`reset_odom_with_loop_closure: true`). Stereolabs does not document whether the pose jumps or is blended in. Release notes through 5.5.1 show that GEN_3's loop closure and its recovery from tracking loss are still being fixed, including false-positive loops in low texture and multi-meter drift after brief tracking loss.

### Cited Findings
**Modes (current docs, SDK 5.1.1 test conditions)**
- GEN_1 is "Dense VSLAM" that uses stereo depth rather than sparse keypoints. It is "optimized primarily for VIO", is not recommended for relocalization, and its architecture "was not designed with loop closure or area map relocalization in mind". Its compute is high and depends on the depth mode. On a ZED X: Neural Light 13% CPU / 77% GPU, Neural 8% / 80%, Neural Plus 4% / 94%. — [Stereolabs: Positional Tracking Modes](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/modes)
- GEN_1 accuracy, mean / max APE in m: indoor warehouse with reflective lights 0.8 / 1.8 (Neural Light), 0.8 / 1.78 (Neural), 0.62 / 1.47 (Neural Plus). Outdoor structured daytime: 2.45 to 3.9 mean. — [Stereolabs: Positional Tracking Modes](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/modes)
- GEN_2: "has been deprecated and will be removed in a future release". — [Stereolabs: Positional Tracking Modes](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/modes)
- GEN_3 is feature-based VSLAM with "strong loop closure and global optimization capabilities" and "fast and reliable relocalization". Stereolabs recommends it for "persistent mapping or multi-session relocalization", feature-rich indoor sites and warehouses. It works without depth input. Caveat: it "may be less robust in severely degraded visual conditions where very few features are available". — [Stereolabs: Positional Tracking Modes](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/modes)
- GEN_3 load on a Jetson Orin NX 16: up to 80 FPS, 13% CPU, 44% GPU. Accuracy (labelled "VIO", mean / max APE): indoor warehouse 0.56 / 1.2 m, outdoor structured 0.29 / 0.58 m. Test setup: SDK v5.1.1, ZED X camera, average sequence about 400 m long. — [Stereolabs: Positional Tracking Modes](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/modes)

**Area memory / spatial memory and loop closure**
- Area memory is enabled with `enable_area_memory`. The map is stored as an "Area map" containing "the keyframes and landmarks detected during the mapping session". Online mapping requires GEN_3 with `enable_area_memory` true. — [Stereolabs: Area Memory & VSLAM Mapping](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/vslam-mapping-tutorial)
- Spatial memory status sequence during mapping: `INITIALIZING`, then `MAP_UPDATE`. On a loop closure the status "briefly switches to `LOOP_CLOSED` before returning to `MAP_UPDATE`". After a loss it "may briefly switch to `LOST`", and "any accumulated drift is automatically corrected". When a loaded map is recognised, the status goes from `INITIALIZING` to `KNOWN_MAP` and stays there while the camera is in mapped regions. — [Stereolabs: Area Memory & VSLAM Mapping](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/vslam-mapping-tutorial)
- Loop closure "corrects accumulated drift to realign the trajectory with the original map". The page does not say whether the pose output jumps or is smoothed. — [Stereolabs: Area Memory & VSLAM Mapping](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/vslam-mapping-tutorial)
- Mapping guidance: "single-loop trajectories should not exceed roughly 20 m" (split large sites into sections). "Avoid pointing the camera downward". In featureless or repetitive environments, "doubling the number of loops". — [Stereolabs: Area Memory & VSLAM Mapping](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/vslam-mapping-tutorial)
- `.area` workflow from the sample tool:
  - Save during mapping: `--map -o map.area`
  - Build offline from an SVO: `--svo rec.svo2 --map -o map.area`
  - Relocalize: `-i map.area`
  - Lifelong extension: `-i map.area --map -o extended.area`

  The map's starting point is the default origin when the map is reloaded. If the camera starts elsewhere, "localization will still converge after some movement", but it may take longer. Outside mapped areas, "localization is no longer reliable and may accumulate drift". — [Stereolabs: Area Memory & VSLAM Mapping](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/vslam-mapping-tutorial)

**Status enums (ROS 2 `zed_msgs/PosTrackStatus`, published on `~/pose/status`)**
- `odometry_status`: OK (0), UNAVAILABLE (1), INSUFFICIENT_FEATURES (2). — [Stereolabs: ZED ROS 2 custom messages](https://docs.stereolabs.com/docs/integrations/ros-2/custom-msgs)
- `spatial_memory_status` values:
  - OK (0): **deprecated for GEN_3**
  - LOOP_CLOSED (1): "found a loop closure, relocalized within the area map or corrected after a sudden localization loss"
  - SEARCHING (2): **deprecated for GEN_3**
  - OFF (3)
  - INITIALIZING (4)
  - KNOWN_MAP (5)
  - MAP_UPDATE (6)
  - LOST (7): "signal to stop the robot"
  - NOT_ENOUGH_MEMORY_FOR_TRACKING (8)

  — [Stereolabs: ZED ROS 2 custom messages](https://docs.stereolabs.com/docs/integrations/ros-2/custom-msgs)
- `pose_confidence` (int32, 0 to 100, where 0 means tracking lost) is filled only in GEN_3. It stays at -1 until the first pose, and requires SDK >= 5.4 and zed_msgs v5.5. The old `status` field is deprecated. — [Stereolabs: ZED ROS 2 custom messages](https://docs.stereolabs.com/docs/integrations/ros-2/custom-msgs)
- The SDK 5.4.0 release added "per-pose confidence" for GEN_3. — [zed-sdk releases](https://github.com/stereolabs/zed-sdk/releases)

**zed-ros2-wrapper `pos_tracking` parameters (`common_stereo.yaml`, master)**
- `pos_tracking_mode: 'AUTO'`: uses the SDK default (GEN_3). Options are GEN_1 and GEN_3.
- `area_memory: true`: "enables loop closure detection".
- `area_file_path: ''`: the area file used for relocalization. The parameter is not named `area_memory_db_path`, which is an older name.
- `enable_localization_only: false`
- `save_area_memory_on_closing: false`
- `reset_odom_with_loop_closure: true`: resets odometry drift to the last valid pose on loop closure.
- `publish_tf: true`: publishes `odom -> camera_link`.
- `publish_map_tf: true`: publishes `map -> odom`.
- `imu_fusion: true`
- `set_gravity_as_origin: true`
- `two_d_mode: false`
- `compute_preference: AUTO`: requires SDK >= 5.5.
- `publish_pose_cov: false`

— [zed-ros2-wrapper common_stereo.yaml](https://github.com/stereolabs/zed-ros2-wrapper/blob/master/zed_wrapper/config/common_stereo.yaml)

**Release-note history of GEN_3 (dates are as printed on the GitHub releases page, without years; the order runs 5.1.x, 5.2.x in Feb/Mar, 5.3.0 on 29 Apr, 5.4.0 on 18 Jun, 5.4.1/5.5.x in Oct)**
- 5.0.1: "Improved Positional Tracking GEN_3 loop closure detection and map optimization." — [ZED SDK 5.0 release notes](https://docs.stereolabs.com/docs/development/zed-sdk/release-notes/5-x/5-0)
- 5.1.1 fixed GEN_3 stability, including race conditions, and a GPU stream sync issue with `DEPTH_MODE::NONE`. 5.1.2 "Fixed repeatability issues of GEN_3 SLAM module" and incorrect gravity alignment. — [zed-sdk releases](https://github.com/stereolabs/zed-sdk/releases)
- 5.2.0 / 5.2.1 made GEN_3 the global default, cut its memory by up to 80%, fixed a rare crash in `saveAreaMap()`, and fixed erroneous positions when Object Detection was enabled. — [zed-sdk releases](https://github.com/stereolabs/zed-sdk/releases)
- 5.3.0 "Fixed false positive loop closure issue that could occur in low-textured areas", improved low-texture accuracy, limited SLAM memory use, and changed GEN_3 `enable_localization_only` behaviour so pose and covariance update when the camera leaves the loaded map. — [zed-sdk releases](https://github.com/stereolabs/zed-sdk/releases)
- 5.4.1: "With Area Memory off, tracking now correctly runs as pure visual-inertial odometry (VIO)". It also fixed GEN_3 failing to start with IMU fusion enabled, and fixed excessive tracking compute that could push `grab()` to 300 to 400 ms. — [zed-sdk releases](https://github.com/stereolabs/zed-sdk/releases)
- 5.5.0 made GEN_3 faster per frame and added a GPU-usage limit. 5.5.1 roughly halved GEN_3 CPU on desktop (about 280 kB per keyframe with area memory on). It also "Improved loop closure accuracy": the map along a closed loop is refined without bending already-correct trajectory parts. — [ZED SDK 5.5.1 release](https://github.com/stereolabs/zed-sdk/releases/tag/5.5.1)
- 5.5.1 also "Fixed the POSITIONAL_TRACKING_MODE::GEN_3 trajectory occasionally drifting away by up to several meters after tracking was briefly lost", and fixed GEN_3 sometimes returning a less accurate pose with unfiltered moving objects while reporting OK (`dynamic_confidence` could be NaN). — [ZED SDK 5.5.1 release](https://github.com/stereolabs/zed-sdk/releases/tag/5.5.1)
- A third-party blog claims GEN_3 loop closure makes SVO2 replay nondeterministic. Stereolabs' own 5.1.2 notes mention repeatability fixes, but I could not confirm the blog's specific claim. — [industrialmonitordirect blog (low quality)](https://industrialmonitordirect.com/blogs/knowledgebase/resolving-zed-sdk-position-tracking-inconsistency-on-svo2)

### Inferences
- On ZED Mini, with GEN_3, `area_memory: true`, `publish_map_tf: true` and `reset_odom_with_loop_closure: true`, a loop closure probably shows up as a step in `map -> odom`, and possibly also as a step or reset in the odom-frame pose. Anything fed to PX4 should therefore treat `LOOP_CLOSED` as a discontinuity event; see Section 4 on `reset_counter`.
- Stereolabs' "VIO" number for GEN_3 is 0.56 m mean APE over sequences averaging about 400 m in a warehouse, on a ZED X. Over a 5 to 15 minute indoor flight of perhaps 200 to 1000 m, that suggests drift of tens of cm to about 1 m before loop closure. This is an extrapolation: the ZED Mini has a narrower baseline and a rolling shutter, unlike the ZED X's global shutter, and was not tested.
- The 20 m single-loop guidance and the "double the loops in repetitive environments" advice mean warehouse flights need deliberate revisit patterns for GEN_3 loop closure to fire reliably.
- Pin a recent SDK (5.5.1 or later). Several bugs that directly affect drift bounding (false loops, post-loss drift of several meters, grab() stalls) were fixed only in 2026 releases.

### Gaps
- Stereolabs does not document whether the GEN_3 pose is smoothed or jumps at `LOOP_CLOSED`, how big corrections typically are, or how `reset_odom_with_loop_closure` interacts with `publish_map_tf`. The Stereolabs community forum did not come up in searches, so forum reports of loop-closure jumps are not covered.
- I found no ZED Mini-specific GEN_3 accuracy numbers and no published GEN_3 vs ORB-SLAM3 / cuVSLAM comparison on EuRoC or TUM-VI.
- The release-page dates have no year. The order (5.2 in Feb, 5.3 in Apr, 5.4.0 in Jun, 5.5.x in Oct) points to 2026 but is not confirmed.

## 2. Open-source and learned VIO/SLAM: loop closure, output style, EuRoC / TUM-VI accuracy, Jetson compute, ROS 2, stereo+IMU

### Takeaway
On public benchmarks, ORB-SLAM3 stereo-inertial is still the accuracy reference among CPU systems: 3.5 cm EuRoC average ATE, and about 9 mm on TUM-VI rooms. Its loop closing and map reuse (Atlas) are the most complete. VINS-Fusion and Kimera add loop closure as a separate pose-graph module that runs beside VIO. OpenVINS has no loop closure in its core estimator. Learned systems (DROID-SLAM, DPV-SLAM, MAC-VO) are more accurate and robust on vision-only benchmarks, but they need desktop GPUs, use no IMU, and are not practical on a Jetson in real time. cuVSLAM is the only GPU-native option with stereo+IMU, loop closure, map save/load and official ROS 2 support that is measured on Jetson Orin.

### Cited Findings
**ORB-SLAM3** (Campos, Elvira, Gómez Rodríguez, Montiel, Tardós, IEEE T-RO 2021, arXiv 2007.11898)
- Stereo-inertial SLAM averages "3.5 cm in the EuRoC drone" and "9 mm under quick hand-held motions in the room of TUM-VI". — [ORB-SLAM3 paper](https://arxiv.org/abs/2007.11898)
- EuRoC RMS ATE averages, Table II (median of 10 runs, i7-7700 CPU only):

  | Configuration | Avg ATE | Notes |
  |---|---|---|
  | Stereo-inertial | 0.035 m | Scale error 0.6% |
  | Mono-inertial | 0.043 m | |
  | Stereo (visual only) | 0.084 m | V203 0.521 m |

  Same table, other stereo-inertial systems:

  | System | Avg ATE | Notes |
  |---|---|---|
  | VINS-Fusion | 0.138 m | Run by the ORB-SLAM3 authors with default config |
  | BASALT | 0.051 m | Keyframe trajectory; did not complete V203 |
  | Kimera | 0.119 m | |

  ORB-SLAM3 states it is "three to four times more accurate than Kimera and VINS-Fusion" in stereo-inertial. — [ORB-SLAM3 paper](https://arxiv.org/abs/2007.11898)
- TUM-VI, Table IV (ORB-SLAM3 room sequences, average RMS ATE):

  | Configuration | Avg ATE |
  |---|---|
  | Stereo-inertial | 0.009 m |
  | Mono-inertial | 0.011 m |
  | Stereo | 0.068 m |

  — [ORB-SLAM3 paper](https://arxiv.org/abs/2007.11898)
- TUM-VI, Table III (stereo-inertial ORB-SLAM3):

  | Sequences | Length | RMS ATE |
  |---|---|---|
  | Corridors | 114 to 322 m | 0.01 to 0.21 m |
  | Magistrale | 458 to 918 m | 0.16 to 1.86 m |
  | Outdoors | 928 to 2656 m | 4.6 to 54.8 m |

  Stereo-inertial BASALT: rooms 0.02 to 0.13 m, magistrale 0.60 to 3.23 m. — [ORB-SLAM3 paper](https://arxiv.org/abs/2007.11898)
- Mechanisms: DBoW2 place recognition; loop closing and map merging via Atlas (multi-map); relocalization. Multi-session EuRoC stereo-inertial ATE: 0.041 m (MH01-03), 0.047 m (MH01-05), 0.031 m (V101-103), 0.046 m (V201-203). The paper says ORB-SLAM3 is 2.6x more accurate than VINS-Mono in single-session and 3.2x in multi-session. — [ORB-SLAM3 paper](https://arxiv.org/abs/2007.11898)
- The paper describes VINS-Mono and BASALT as "essentially visual-inertial odometry systems with loop closures" that "miss mid-term data associations". — [ORB-SLAM3 paper](https://arxiv.org/abs/2007.11898)
- Jetson: a 2026 GPU port (Jetson-ORB-SLAM3, arXiv 2608.17874, Aug 2026, preprint) runs the ORB front end on GPU and TensorRT CosPlace loop closure on a 7 W Jetson Orin Nano. It reports:
  - 32 FPS mean in mono-inertial mode on EuRoC
  - EuRoC results within 0.10 cm mean ATE of the CPU reference
  - sub-centimetre accuracy on 5 of 6 TUM-VI rooms
  - 2.2 ms per place-recognition query

  — [Jetson-ORB-SLAM3](https://arxiv.org/abs/2608.17874)
- FastLoop (arXiv 2603.17201, 2026) parallelises ORB-SLAM3 loop closing on GPU on a Jetson Orin Nano. A search snippet reports average EuRoC loop-closing time falling from 56.9 to 39.8; units not confirmed, likely ms. — [FastLoop](https://arxiv.org/abs/2603.17201)

**VINS-Mono / VINS-Fusion** (Qin, Li, Shen, IEEE T-RO 2018; VINS-Fusion 2019 code)
- VINS-Fusion supports mono+IMU, stereo, and stereo+IMU. Loop closure runs as a separate optional `loop_fusion_node` using DBoW2. Visualisation shows the loop-corrected path (red) apart from the VIO path (green). KITTI results were evaluated without loop closure. Officially supported on ROS Kinetic/Melodic only (ROS 1). — [VINS-Fusion GitHub](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion)
- The loop-closure pose graph is 4-DoF (x, y, z, yaw), because roll and pitch are observable from gravity. VINS-Mono's handheld indoor test reports that VIO-only accumulates "significant drifts in x, y, z, and yaw", and that relocalization and loop closure "efficiently eliminate all these drifts". — [VINS-Mono paper](https://arxiv.org/abs/1708.03852)
- Kimera paper's EuRoC table: VINS-Mono VIO 0.08 to 0.32 m per sequence; VINS-LC (with loop closure) 0.06 to 0.21 m, except V2_3 at 1.39 m. — [Kimera paper](https://arxiv.org/abs/1910.02490)

**Kimera / Kimera-VIO / Kimera-RPGO** (Rosinol, Abate, Chang, Carlone, ICRA 2020)
- Stereo+IMU. Loop closure: DBoW2 candidates, geometric verification, then Kimera-RPGO robust pose graph (modified PCM plus GTSAM). The output is a "globally consistent keyframe trajectory", separate from the VIO state, which runs at IMU rate above 200 Hz. — [Kimera paper](https://arxiv.org/abs/1910.02490)
- EuRoC RMSE ATE:

  | Seq | Kimera-VIO fixed-lag | Kimera-RPGO |
  |---|---|---|
  | MH_1 | 0.11 | 0.08 |
  | MH_4 | 0.24 | 0.15 |
  | V1_2 | 0.08 | 0.11 |
  | V1_3 | 0.07 | 0.12 |
  | V2_3 | 0.21 | 0.19 |

  — [Kimera paper](https://arxiv.org/abs/1910.02490)
- Timing (desktop): vision front end about 4.5 ms per frame (about 45 ms at keyframes), VIO back end under 40 ms, RPGO about 55 ms average and growing with graph size. — [Kimera paper](https://arxiv.org/abs/1910.02490)
- Kimera2 (2024) adds GNC outlier rejection as an option in Kimera-RPGO. — [Kimera2](https://arxiv.org/abs/2401.06323)

**OpenVINS** (Geneva, Eckenhoff, Lee, Yang, Huang, ICRA 2020)
- MSCKF-based VIO with mono, synchronized stereo or binocular input, and IMU. Supports ROS 1 and ROS 2 (since Dec 2021); latest listed version is v2.7 (May 2023). No loop closure in the core. `ov_secondary` provides loosely coupled loop closure based on VINS-Fusion, but "no information is returned to the estimator". The README gives no accuracy numbers. — [OpenVINS GitHub](https://github.com/rpng/open_vins)

**Basalt** (Usenko, Demmel, Schubert, Stückler, Cremers, RA-L 2020)
- Stereo-inertial EuRoC 0.051 m average, keyframe trajectory, V203 not completed; TUM-VI numbers as above, both from the ORB-SLAM3 tables. — [ORB-SLAM3 paper](https://arxiv.org/abs/2007.11898)
- The GitLab page did not render its README, so I could not verify Basalt's own loop-closure or mapping mode or its ROS 2 status. — [Basalt GitLab](https://gitlab.com/VladyslavUsenko/basalt)

**Learned systems**
- DROID-SLAM (Teed and Deng, NeurIPS 2021):
  - EuRoC monocular average ATE 0.022 m with zero failures; 43% lower than ORB-SLAM3 on the sequences ORB-SLAM3 completes.
  - "with stereo input, we reduce error by 71% over ORB-SLAM3".
  - Real time needs 2 RTX 3090s (about 20 FPS on EuRoC at 320×512, skipping every other frame). The front end fits in 8 GB; the back end and loop closure use more memory.
  - No IMU.

  — [DROID-SLAM paper](https://proceedings.neurips.cc/paper/2021/file/89fcd07f20b6785b92134bd6c1d0fa42-Paper.pdf)
- DPV-SLAM (Lipson, Teed, Deng, ECCV 2024): accuracy comparable to DROID-SLAM on EuRoC and TartanAir, "2.5x faster", using a fraction of the memory. EuRoC error 4x lower than DPVO (0.105 to 0.024; monocular). — [DPV-SLAM](https://arxiv.org/abs/2408.01654)
- MAC-VO (arXiv 2409.09479 v2, Mar 2025): stereo VO with **no loop closure and no IMU**. EuRoC average relative error t_rel / r_rel:

  | Method | t_rel (m/frame) | r_rel (°/frame) |
  |---|---|---|
  | MAC-VO | 0.0024 | 0.0403 |
  | DROID-SLAM | 0.0024 | 0.0590 |
  | DPVO | 0.0027 | 0.0437 |
  | ORB-SLAM3 | 0.0092 | 0.1866 |

  Speed on an RTX 3090 Ti: 2 to 4 FPS, or 10.6 FPS in the "Fast" variant. — [MAC-VO](https://arxiv.org/html/2409.09479v2)

**cuVSLAM** (Korovko et al., NVIDIA, arXiv 2506.04359, Jun 2025, v3 Jul 2025; no venue listed). Details are in Section 3. Its own Table 2 includes ORB-SLAM3 baselines. — [cuVSLAM paper](https://arxiv.org/html/2506.04359)

**Older Jetson benchmark (2021, Xavier-era, loop closure disabled)**
- Jeon et al. (arXiv 2103.01655, 2021) compared VINS-Mono, VINS-Fusion (CPU, GPU and IMU variants), Kimera, ALVIO, S-MSCKF, ORB-SLAM2 stereo and ROVIO on TX2, Xavier NX and AGX Xavier. Setup: D435i at 30 Hz with a Pixhawk4 mini IMU, loop closure disabled. Findings:
  - On TX2, VINS-Fusion-imu could not run because of memory and CPU limits.
  - CPU-bound stereo methods degraded on weaker boards, while VINS-Fusion-gpu was board-insensitive.
  - Recommendation: Xavier NX for UAVs.

  This predates Orin. — [Jeon et al. 2021](https://arxiv.org/abs/2103.01655)

### Inferences
Summary comparison for the ZED Mini (stereo + IMU) + Jetson + ROS 2 use case:

| System | Loop closure | How correction is output | EuRoC stereo-inertial ATE (avg) | ROS 2 | Jetson Orin fit |
|---|---|---|---|---|---|
| ZED GEN_3 | Yes (area memory) | `map->odom` TF, plus odom reset by default | not published | Official wrapper | Orin NX: 13% CPU / 44% GPU |
| cuVSLAM / isaac_ros_cuvslam | Yes (async PGO) | Separate odom (`odom->base`) and SLAM (`map->base`) poses | 0.13 m SLAM / 0.19 m odom (own protocol) | Official | AGX Orin: 3.8 ms stereo-inertial |
| ORB-SLAM3 | Yes (DBoW2, Atlas, merging) | Pose tracked against the corrected map, so it jumps | 0.035 m | Community wrappers only (no source checked) | CPU-heavy; 2026 GPU port gives 32 FPS on Orin Nano (mono-inertial) |
| VINS-Fusion | Optional `loop_fusion` | Separate loop-corrected pose next to VIO odometry | 0.138 m (default config, run by ORB-SLAM3 authors) | ROS 1 officially | GPU fork exists (2021) |
| Kimera | Yes (RPGO + PCM/GNC) | Separate optimized keyframe trajectory | 0.119 m (Kimera's own table: 0.05 to 0.24 m per sequence) | Not checked | Not measured here |
| OpenVINS | No (ov_secondary is loose) | n/a | not in README | ROS 1 / ROS 2 | Not measured here |
| Basalt | Not verified | n/a | 0.051 m (keyframes, V203 failed) | Not verified | Not measured here |
| DROID / DPV-SLAM / MAC-VO | DROID and DPV yes; MAC-VO no | n/a | vision-only | Not official | Desktop GPU only |

- For a drone, "separate odometry plus a loop-corrected pose" (cuVSLAM, VINS-Fusion, Kimera, ZED map->odom) is easier to integrate safely than ORB-SLAM3's single map-relative pose. PX4 can take smooth odometry while loop corrections go to the planner or mission frame.
- Learned systems with the best robustness numbers (DROID, DPV, MAC-VO) are not practical on board an Orin for 15-minute flights. They are vision-only and run at about 2 to 20 FPS on desktop GPUs.

### Gaps
- No primary-source numbers were collected for DM-VIO (RA-L 2022), VINS-Fusion's own EuRoC table, or OpenVINS's ICRA 2020 table.
- No official ROS 2 port of ORB-SLAM3 or VINS-Fusion was verified (community ports exist but were not checked).
- I found no 2024 to 2026 independent benchmark running ORB-SLAM3, VINS-Fusion, OpenVINS, Basalt, cuVSLAM and ZED GEN_3 under one protocol on Jetson Orin.
- I could not verify Basalt's README (loop closure, ROS 2).

## 3. NVIDIA Isaac ROS Visual SLAM (cuVSLAM): accuracy, loop closure, saved-map localization, Jetson Orin performance, PX4 / Isaac Sim

### Takeaway
cuVSLAM is a GPU-accelerated stereo / stereo-inertial / multi-stereo (up to 16 stereo pairs) VO plus SLAM. Loop closure and pose-graph optimization run asynchronously. It publishes odometry (`odom->base`) and SLAM (`map->base`) poses separately, and supports SaveMap / LocalizeInMap. It is very cheap on Jetson Orin: 3.8 ms per stereo-inertial frame on AGX Orin. On EuRoC and TUM-VI APE, its own paper shows it slightly less accurate than ORB-SLAM3, with SLAM cutting odometry APE by about 30 to 60%. The ROS package was renamed `isaac_ros_cuvslam` on 2026-09-21.

### Cited Findings
- Paper: Korovko, Slepichev, Efitorov, Dzhumamuratova, Kuznetsov, Biswas, Rabeti, Pouya (NVIDIA), arXiv 2506.04359, Jun 2025 (v3 8 Jul 2025). No venue listed. — [cuVSLAM paper](https://arxiv.org/html/2506.04359)
- Track-call time (768×480):

  | Configuration | AGX Orin | RTX 4090 |
  |---|---|---|
  | Stereo | 1.8 ms | 0.4 ms |
  | Stereo-inertial | 3.8 ms | 1.3 ms |
  | 2-stereo | 2.0 ms | n/a |
  | 3-stereo | 2.3 ms | n/a |

  Jetson stereo-inertial net utilisation: 1.3% CPU / 2.2% GPU. — [cuVSLAM paper](https://arxiv.org/html/2506.04359)
- Mono-depth is the heavy mode: at 720p it averaged 37.7 ms on AGX Orin and skipped about half the frames. On an Orin Nano Super (25 W) it was stable only at 424×240. — [cuVSLAM paper](https://arxiv.org/html/2506.04359)
- Accuracy, Table 2 (RMSE APE; avgRTE %):

  | Mode / dataset | ORB-SLAM3 | cuVSLAM Odom | cuVSLAM SLAM | Other |
  |---|---|---|---|---|
  | Stereo EuRoC (APE) | 0.068 | 0.13 | 0.054 | DPVO 0.10 |
  | Stereo KITTI (APE) | 2.98 | 3.00 | 1.98 | |
  | Stereo-inertial EuRoC (APE) | 0.066 | 0.19 | 0.13 | |
  | Stereo-inertial TUM-VI Room (APE) | 0.077 | 0.18 | 0.12 | |
  | Stereo-inertial EuRoC (avgRTE %) | 5.70 | 0.39 | 0.29 | |

  — [cuVSLAM paper](https://arxiv.org/html/2506.04359)
- The paper claims about 40% better SLAM than odometry accuracy on the real multi-stereo R2B dataset: APE 0.28 to 0.18. It also notes that many benchmark sequences have no overlapping trajectory, so loop closure cannot fire. — [cuVSLAM paper](https://arxiv.org/html/2506.04359)
- Loop closure mechanism: keyframes, landmarks and image patches go into an asynchronous global map. Candidates come from a kd-tree search over poses within a fixed radius. Landmarks are filtered for visibility, a relative pose is estimated by reprojection, and pose-graph optimization follows. — [cuVSLAM paper](https://arxiv.org/html/2506.04359)
- Isaac ROS docs on output frames: "The odometry pose reported by cuVSLAM corresponds with the transform `odom_frame` -> `base_frame`", and "The SLAM pose … corresponds with the transform `map_frame` -> `base_frame`". Graph optimization "leads to the correction of the current odometry pose". — [Isaac ROS cuVSLAM concepts](https://nvidia-isaac-ros.github.io/concepts/visual_slam/cuvslam/index.html)
- Saved map: the `SaveMap` service stores landmarks and the pose graph. `LocalizeInMap` loads a map and "requires a map file path and a prior pose". Otherwise cuVSLAM keeps building a new map. Both calls "can take some time to complete". — [Isaac ROS cuVSLAM concepts](https://nvidia-isaac-ros.github.io/concepts/visual_slam/cuvslam/index.html)
- IMU use: cuVSLAM "automatically switches to IMU when VO is unable to estimate a pose", for example in dark lighting or facing long solid surfaces. The IMU integrator gives acceptable tracking for "about ~< 1 seconds", and the constant-velocity integrator for "~0.5 seconds". — [Isaac ROS cuVSLAM concepts](https://nvidia-isaac-ros.github.io/concepts/visual_slam/cuvslam/index.html)
- Package page:
  - Rename to `isaac_ros_cuvslam` on 2026-09-21.
  - KITTI 0.94% translation / 0.0019 deg/m at 0.007 s on Jetson AGX Xavier, versus ORB-SLAM2 1.15%.
  - Loop closure is tested "on sequences of over 1000 meters".
  - Platforms: Jetson Thor and Orin with JetPack 7.2.
  - Camera requirements: at least 30 Hz, ±2 ms jitter, ±100 µs stereo offset.
  - Changelog: multi-cam SLAM (2024-12-10), ROS 2 Jazzy with cuVSLAM 14 (2025-10-24), RGB-D (2026-02-02).

  — [Isaac ROS Visual SLAM package page](https://nvidia-isaac-ros.github.io/repositories_and_packages/isaac_ros_visual_slam/index.html)
- PX4 example (academic project, Aug 2024 to Jun 2025): a D435i on a Jetson Orin Nano (JetPack 6.2) running Isaac ROS VSLAM. `/visual_slam/tracking/vo_pose_covariance` is remapped to `mavros/vision_pose/pose_cov` and fused by PX4 EKF2, with mocap used only for validation. The same pipeline was tested in Isaac Sim. **No drift numbers were reported.** — [Bernas: GPS-Denied UAV with Visual SLAM](https://www.andrewbernas.com/docs/projects/robots/vslam)
- A third-party guide routes Isaac ROS VSLAM odometry to PX4 `/fmu/in/vehicle_visual_odometry` via a transform node and Micro-XRCE-DDS, with an ENU to NED/FRD conversion. This is a search-snippet summary only. — [xdynamics guide](https://www.xdynamics.com/documentation/configure-gps-denied-slam/)

### Inferences
- With the ZED Mini, cuVSLAM could run on the ZED's rectified stereo plus IMU instead of GEN_3. Two caveats: cuVSLAM expects ≥30 Hz, ±100 µs synchronized stereo (ZED stereo is hardware-synchronized), and it needs a calibrated camera-IMU extrinsic.
- Its separate odom and SLAM outputs map cleanly onto a "send odom to PX4, use map->odom for global goals" design.
- The cuVSLAM paper shows ORB-SLAM3 with lower APE on EuRoC and TUM-VI stereo-inertial. cuVSLAM's selling points are compute cost, multi-camera support and official ROS 2 / Isaac integration, not best-in-class ATE.

### Gaps
- The current docs do not specify how the SLAM-pose correction behaves over time (step vs smoothing), and parameter names (for example `enable_localization_n_mapping`, `publish_map_to_odom_tf`, `enable_imu_fusion`) could not be confirmed after the rename.
- I found no official NVIDIA PX4 example and no published flight with drift numbers for cuVSLAM to PX4.
- I found no independent reproduction of cuVSLAM's benchmark numbers; one review notes they are the authors' own claims.

## 4. Published drone examples: VIO + loop closure feeding PX4 / ArduPilot EKF, with drift numbers

### Takeaway
Many pipelines feed VIO to PX4 (VINS-Fusion, Isaac ROS VSLAM, ZED to MAVROS), but I found almost no peer-reviewed flight results with drift numbers. Integration guidance is clear on one point: loop-closure jumps confuse EKF2. MAVLink provides `reset_counter` for exactly this case, and PX4 developers recommend sending smooth odometry (or velocity) to the EKF.

### Cited Findings
- PX4 EKF2 external vision setup:
  - Configured through `EKF2_EV_CTRL` (horizontal position, vertical position, velocity, yaw), `EKF2_HGT_REF=Vision`, `EKF2_EV_DELAY` (tune empirically by minimising innovations) and `EKF2_EV_POS_X/Y/Z`.
  - Inputs are `VISION_POSITION_ESTIMATE` or `ODOMETRY` (MAV_FRAME_LOCAL_FRD), both mapped to `vehicle_visual_odometry`. Only `ODOMETRY` carries velocity.
  - Stream rate should be "between 30Hz (if containing covariances) and 50 Hz". If the rate is too low, EKF2 will not fuse the data.
  - MAVROS topics: `/mavros/vision_pose/pose` and `/mavros/odometry/out`.

  — [PX4: External position estimation](https://docs.px4.io/main/en/ros/external_position_estimation)
- PX4 VIO docs on combining vision position with GPS: "This is really difficult, because when they disagree it will confuse the EKF", and "From testing it is more reliable to just use vision velocity". The only named VIO camera is the T265. — [PX4: Visual inertial odometry](https://docs.px4.io/main/en/computer_vision/visual_inertial_odometry)
- MAVLink `VISION_POSITION_ESTIMATE.reset_counter`: "Estimate reset counter. This should be incremented when the estimate resets in any of the dimensions". The description goes on to cite an external SLAM loop closure, where the estimate jumps, as the intended use. `ODOMETRY` has the same field. — [MAVLink common messages](https://mavlink.io/en/messages/common.html#VISION_POSITION_ESTIMATE)
- A PX4 forum report says the EKF2 local estimate jumped to zero immediately when the external vision source dropped, causing large velocity commands. — [PX4 forum: EKF2 reset to zero when EV dropped](https://discuss.px4.io/t/ekf2-reset-to-zero-when-external-vision-source-dropped/35277)
- A PX4 forum report shows ZED 2i users converting ZED odometry to NED with a static transform, computing velocities manually, and fusing horizontal position plus yaw. One user crashed, with no clear diagnosis. — [PX4 forum: EKF2 VIO not working](https://discuss.px4.io/t/ekf2-vio-not-working-settings-and-code-not-correct/39289); [PX4 forum: Sending VISION_POSITION_ESTIMATE](https://discuss.px4.io/t/sending-vision-position-estimate-to-drone-but-not-work-correctly/46453)
- Community VINS-Fusion to PX4 projects (search snippets):
  - ENU to NED conversion, publishing on `/mavros/vision_pose/pose`, Position mode in Gazebo.
  - Initialization fails in empty worlds ("Not enough features or parallax").
  - An arming gate requires EKF and vision displacement under 0.05 m over 5 s, with `AID_MASK=8`, `HGT_MODE=3`, `EV_DELAY=175` (legacy PX4 parameter names).

  No drift numbers. — [yeslab-vins-px4-position-mode](https://github.com/MinQinyuan/yeslab-vins-px4-position-mode)
- Isaac ROS VSLAM to MAVROS `vision_pose/pose_cov` to PX4 EKF2 on an Orin Nano with a D435i (no drift numbers). See Section 3. — [Bernas: GPS-Denied UAV with Visual SLAM](https://www.andrewbernas.com/docs/projects/robots/vslam)
- Bednář, Petrlík, Vivaldini, Saska (ICUAS 2022, arXiv 2302.01867) evaluated several VIO methods on a UAV against RTK ground truth, under challenging illumination, used onboard for feedback control. The abstract gives no numbers and does not name the methods. — [Bednář et al.](https://arxiv.org/abs/2302.01867)
- Jeon et al. 2021 flew and recorded a D435i plus Pixhawk4 mini rig on Jetson boards (KAIST VIO dataset), with loop closure disabled. — [Jeon et al. 2021](https://arxiv.org/abs/2103.01655)

### Inferences
- Pattern for this stack, drawn from the sources above:
  - Send PX4 the continuous odometry (ZED odom frame, cuVSLAM `odom->base`, VINS VIO), via `/mavros/odometry/out` with body-frame velocity, at 30 to 50 Hz.
  - Handle loop closures in the `map->odom` layer used by the mission or planner.
  - If map-frame poses must go to PX4 directly, increment `reset_counter` on every `LOOP_CLOSED` or relocalization so EKF2 resets rather than fighting the step.
- Whether MAVROS's `vision_pose` / `odometry` plugins forward a `reset_counter` from ROS is not verified (see Gaps). A custom MAVLink sender or a PX4 uXRCE-DDS `VehicleOdometry` publisher (which has a `reset_counter` field) may be needed.

### Gaps
- I found no peer-reviewed indoor flight with VIO plus loop closure feeding PX4 or ArduPilot that reports drift or ATE before and after loop closure.
- Whether MAVROS propagates `reset_counter` from ROS messages, and how PX4 EKF2 handles a reset-counter change in current releases (v1.15 to v1.17), were not verified from source.
- I did not search for ArduPilot-specific examples (for example ArduPilot's T265 / VISION_POSITION_DELTA path).

## 5. How much drift reduction loop closure gives in practice, and its failure modes

### Takeaway
At room scale (≤150 m), good stereo-inertial VIO already reaches cm level. Loop closure and mid-term map reuse take ORB-SLAM3 to about 1 cm on TUM-VI rooms, but on short EuRoC/room sequences the gain is small and sometimes negative (Kimera V1_2 / V1_3). At hundreds of metres, loop closure matters more: cuVSLAM cuts APE by about 30 to 60%, and ORB-SLAM3 holds about 1 m over 900 m indoor corridors. The main failure modes are:
- false loops from perceptual aliasing, which are catastrophic without outlier rejection (1.59 m vs 0.049 m on V1_01)
- pose jumps that downstream estimators must absorb
- no loop at all when revisits come from the opposite viewpoint

### Cited Findings
- cuVSLAM, odometry vs SLAM RMSE APE:

  | Dataset | Odometry | SLAM | Reduction |
  |---|---|---|---|
  | EuRoC stereo | 0.13 | 0.054 | about 58% |
  | EuRoC stereo-inertial | 0.19 | 0.13 | about 32% |
  | TUM-VI Room stereo-inertial | 0.18 | 0.12 | about 33% |
  | KITTI stereo | 3.00 | 1.98 | about 34% |
  | R2B multi-stereo | 0.28 | 0.18 | |

  Short-horizon RPE (1 s segments) on TUM-VI rooms is essentially unchanged, for example room1 0.023 m odometry vs 0.025 m SLAM. — [cuVSLAM paper](https://arxiv.org/html/2506.04359)
- Kimera, VIO vs loop closure (RPGO) on EuRoC: improvements on Machine Hall (MH_4 0.24 to 0.15 m, MH_1 0.11 to 0.08 m), but worse on small Vicon rooms (V1_2 0.08 to 0.11 m, V1_3 0.07 to 0.12 m). — [Kimera paper](https://arxiv.org/abs/1910.02490)
- False loops: on V1_01, PGO without PCM outlier rejection gives 1.59 m RMSE versus 0.049 m with PCM. Kimera warns that loops can contain false matches from perceptual aliasing (for example "two identical rooms on different floors"), and handles them with a robust back end rather than conservative loop acceptance. — [Kimera paper](https://arxiv.org/abs/1910.02490)
- Kimera-Multi also notes that perceptual aliasing from similar-looking scenes often produces wrong data associations that break standard back ends. — [Kimera-Multi](https://ar5iv.labs.arxiv.org/html/2106.14386)
- ORB-SLAM3 on TUM-VI:
  - Rooms: below 1 cm stereo-inertial, "continuously revisiting and reusing previously mapped regions".
  - Magistrale (up to 900 m): "errors around 1 m except in one sequence that goes close to 5 m".
  - Outdoors: 10 to 70 m, from far features drifting scale and accelerometer bias.
  - Many TUM-VI sequences have no detectable loops, because start and end views face opposite directions.
  - Multi-session with the small room sequence "bringing all errors to centimeter level".

  — [ORB-SLAM3 paper](https://arxiv.org/abs/2007.11898)
- ORB-SLAM3 attributes much of its gain over VINS-Mono and BASALT to mid-term data association (map reuse) rather than loop closure alone. — [ORB-SLAM3 paper](https://arxiv.org/abs/2007.11898)
- VINS-Mono: relocalization and loop closure "efficiently eliminate" x, y, z and yaw drift in an indoor handheld test. — [VINS-Mono paper](https://arxiv.org/abs/1708.03852)
- ZED GEN_3 failure modes from vendor release notes:
  - False-positive loop closures in low-texture areas (fixed 5.3.0).
  - Trajectory drifting away "by up to several meters" after brief tracking loss (fixed 5.5.1).
  - Loop correction distorting already-correct trajectory parts (improved 5.5.1).
  - Less accurate poses with dynamic objects while reporting OK (fixed 5.5.1).

  — [ZED SDK 5.5.1 release](https://github.com/stereolabs/zed-sdk/releases/tag/5.5.1); [zed-sdk releases](https://github.com/stereolabs/zed-sdk/releases)
- ZED guidance for repetitive environments: double the number of loops, and keep single loops at about 20 m or less. — [Stereolabs: Area Memory & VSLAM Mapping](https://docs.stereolabs.com/docs/development/zed-sdk/modules/positional-tracking/vslam-mapping-tutorial)
- cuVSLAM's IMU-only fallback stays acceptable for only about 1 s, and constant velocity for about 0.5 s, so long visual dropouts (white walls, darkness) still cause drift that only a later loop or relocalization can remove. — [Isaac ROS cuVSLAM concepts](https://nvidia-isaac-ros.github.io/concepts/visual_slam/cuvslam/index.html)
- PX4: EKF2 gets "confused" when vision position disagrees with other position sources. Vision velocity is more reliable. — [PX4: Visual inertial odometry](https://docs.px4.io/main/en/computer_vision/visual_inertial_odometry)

### Inferences
- For 5 to 15 minute indoor flights in rooms, VIO drift is likely tens of cm. Loop closure's practical value is bounding drift and allowing return-to-known-pose, not improving local smoothness, which the cuVSLAM RPE table shows is unchanged.
- For warehouse-scale flights (hundreds of metres, repetitive racking), loop closure should reduce APE by about 30 to 60% (cuVSLAM figures), but it brings a real risk of false loops. Mitigations:
  - Robust back ends (PCM/GNC in Kimera-RPGO).
  - Vendor fixes (ZED ≥ 5.3.0 / 5.5.1).
  - Flight patterns that revisit areas from the same viewing direction (ORB-SLAM3's TUM-VI observation).
  - Gating `LOOP_CLOSED` events by correction magnitude before using them in navigation.
- Pre-building a `.area` map (ZED) or a cuVSLAM SaveMap, then flying in localization mode, turns online loop closure into relocalization against a fixed map. ORB-SLAM3's multi-session results suggest this is the strongest drift bound, provided the map was built well (closed loops ≤ 20 m for ZED).

### Gaps
- I found no published quantitative study of false-loop rates in warehouse-like repetitive interiors for ZED GEN_3, cuVSLAM or ORB-SLAM3.
- I found no published measurement of loop-closure jump magnitudes for ZED GEN_3, or of their effect on a PX4-controlled vehicle.
- There is no drone-specific "drift per minute with vs without loop closure" number for 5 to 15 minute indoor flights. Figures above come from handheld and benchmark datasets (EuRoC is MAV-recorded but flown manually, not under closed-loop VIO control).
