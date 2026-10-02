# Perception backends: Isaac ROS vs traditional ROS 2

One switch (`PERCEPTION_BACKEND` in `config/bisg.conf`) decides what turns the ZED images + IMU into **odometry** and **depth** for
the vehicle. Three backends sit behind the same interface, so you can change your mind later without touching anything else.

| `PERCEPTION_BACKEND` | What runs | Needs |
|---|---|---|
| `mock` (default) | `vio_mock`: sim ground truth + noise, no images | nothing; what all existing tests assume |
| `isaac_ros` | **Isaac ROS 4.6**: cuVSLAM (visual or visual-inertial odometry) + VPI SGM stereo disparity, NITROS, on the GPU | `bisg/perception` image, NVIDIA runtime |
| `ros2` | **Traditional CPU ROS 2**: `rtabmap_odom` stereo odometry + `stereo_image_proc` (OpenCV SGBM) | `bisg/perception` image |

## 0. What is being compared (and what is not)

*Isaac Sim's ROS 2 bridge* is the **transport from the simulator**: it publishes the ZED rig's images, camera_info, IMU, clock and TF
as ordinary ROS 2 topics. It is used by **all** backends and is not an alternative to Isaac ROS. The real choice is what *consumes* those
topics: GPU-accelerated Isaac ROS packages or traditional CPU ROS 2 packages doing the same job. That is what `./bisg perception bench` compares,
on identical input, scored against the sim's ground truth. (Results: §6.)

## 1. Architecture

```
Isaac Sim ──(ROS 2 bridge: images, camera_info, IMU, TF)──►  /drone_N/zed/zed_node/{left,right}/…, imu/data, tf_static
                                                                        │
                       ┌────────────────────────────────────────────────┼────────────────────────────┐
                       │ bisg/perception container (one image, backend chosen by env)               │
                       │   isaac_ros : visual_slam_node (cuVSLAM) + DisparityNode (VPI SGM)          │
                       │   ros2      : stereo_odometry (rtabmap)  + DisparityNode (stereo_image_proc)│
                       │   tf_relay  : /drone_N/tf_static  ->  /tf_static  (tf2 listeners read the global topic)
                       │                       │ perception/odom        perception/disparity         │
                       │   vio_relay ◄─────────┘                                                      │
                       └──────┬──────────────────────────────────────────────────────────────────────┘
                              ├─► zed/zed_node/odom        (contract topic, drone_N/-prefixed frames)
                              ├─► mavros/odometry/out      (odom/base_link, reliable)  ── only if feed_mavros ──► PX4 EKF2
                              └─► tf drone_N/odom -> drone_N/base_link
```

Backend interface (both backends, under `/drone_<n>/`): `perception/odom` (`nav_msgs/Odometry`, `odom → base_link`) and
`perception/disparity` (`stereo_msgs/DisparityImage`). Everything downstream (`vio_relay`, the benchmark, future nodes) only knows these two.

## 2. Switching and running

```bash
./bisg config                              # shows PERCEPTION_BACKEND / _DEPTH / _IMU and where each value comes from
./bisg perception build                    # once: bisg/perception image (~14 GB: CUDA 13.2, Isaac ROS 4.6, CPU baselines)
./bisg ros build                           # once: colcon build of ros2_ws (bisg_vehicle, bisg_perception)

# 1) set it for good:   PERCEPTION_BACKEND=isaac_ros   in docker/.env (this machine) or config/bisg.conf (everyone)
SIM_SCENARIO=single_iris_vio_midres ./bisg all headless        # sim + MAVROS + the configured backend feeding PX4
# 2) or per run:
PERCEPTION_BACKEND=ros2 SIM_SCENARIO=single_iris_vio_midres ./bisg all headless
# 3) or swap a backend on a running sim:
./bisg perception up isaac_ros             # closed loop: its odometry feeds MAVROS (vio_mock is stopped, never two sources)
./bisg perception up ros2 --observer       # runs, publishes, but does NOT feed MAVROS (evaluate while vio_mock flies)
./bisg perception up mock                  # back to vio_mock
./bisg perception status | down
```

* `PERCEPTION_DEPTH=false` drops the disparity node; `PERCEPTION_IMU=true` runs cuVSLAM in visual-inertial mode (`tracking_mode: 1`).
* Scenario needs the ZED rig: `single_iris_vio*`. `single_iris_vio_lowres` (320×180) and `single_iris_vio_midres` (448×252) work on a stock host;
  HD720 needs the `rmem_max` sysctl (§5).
* The backend only reads the contract topics, so it works unchanged against the real ZED wrapper on the Jetson (`deploy/jetson`, see §7).
* Everything is one compose service (`perception`) selected by env, so the backend is a one-line change, never a different file.

## 3. Backends in detail

| | `isaac_ros` (GPU) | `ros2` (CPU) |
|---|---|---|
| Odometry | `isaac_ros_visual_slam::VisualSlamNode` (cuVSLAM 15), rectified stereo; optional IMU fusion | `rtabmap_odom/stereo_odometry` (frame-to-map, GFTT features) |
| Depth | `isaac_ros_stereo_image_proc::DisparityNode`, VPI SGM on CUDA, `max_disparity 64` | `stereo_image_proc::DisparityNode`, OpenCV SGBM, `disparity_range 64`, window 7 |
| Transport | NITROS type adaptation (GPU buffers between Isaac ROS nodes; one host→GPU copy at the edge) | plain ROS 2 messages |
| Container | `component_container_mt`, composable nodes | composable disparity + a standalone odometry node |
| Launch | `ros2 launch bisg_perception perception.launch.py backend:=isaac_ros` | `… backend:=ros2` |

Parameters live in `ros2_ws/src/bisg_perception/launch/perception.launch.py`. cuVSLAM specifics worth knowing:
`image_jitter_threshold_ms` is 80 (the sim's frame interval is 56 ms of **sim** time), TF is read from `/tf_static`
(hence `tf_relay`), `publish_odom_to_base_tf` is off (the relay publishes the TF).

## 4. Changes made to the sim for this

* `zed_rig.py`: the **right** camera's `camera_info` now carries the baseline, `P[0,3] = −fx·baseline`, as the real ZED wrapper does.
  Without it every stereo node saw a zero baseline. (Contract addendum in `interface-contract.md`.)
* `zed_rig.py`: images, depth and `camera_info` now share one rate gate, so they pair 1:1 (bugs.md B9). Stereo and VSLAM nodes need that.

## 5. Gotchas found while building it

1. **Isaac ROS `DisparityImage.t` is not the baseline.** It holds `−P[0,3]` (= fx·baseline, here 11.19), while `stereo_image_proc` stores the baseline
   in metres (0.063). `depth = f·T/d` is off by a factor of fx unless you divide: `T = t/f` when `t > 1`. The benchmark detects and records which convention it saw.
2. **Release lines.** Isaac ROS `release-4` = ROS 2 **Jazzy** (amd64 `noble` and arm64 `noble-jetpack`); `release-5` = **Lyrical** only. Our containers and the Jetson are Jazzy, so 4.6.
3. **The apt dependencies come from three repos:** Isaac ROS, NVIDIA CUDA (`cuda-toolkit-13-2`) and NVIDIA VPI (`repo.download.nvidia.com/jetson/x86_64/noble r38.4`). The Dockerfile adds all three.
4. **CUDA 13.2 userspace runs on the host's 580 driver** (verified: cuVSLAM and the CUDA disparity node run). Keep the driver on the 580 branch (CLAUDE.md).
5. **tf2 listeners read the global `/tf_static`**, the rig publishes per-drone `/drone_N/tf_static` → `tf_relay`.
6. **Resolution ceiling without `sudo`.** HD720 (1280×720) images never reach subscribers (bugs.md B2, host `net.core.rmem_max` 208 KB). Probed here: 448×252
   (389 KB/frame) gets through, 640×360 (691 KB) does not. To benchmark at HD720: `echo 'net.core.rmem_max=16777216' | sudo tee /etc/sysctl.d/60-bisg-dds.conf && sudo sysctl --system`, then
   `./bisg perception bench all -c single_iris_vio` (the bench warns while the sysctl is missing).
7. The container runs as root, so files it writes under `logs/` are root-owned; delete them with `docker run --rm -v $PWD/logs:/l alpine rm -rf /l/perception` if needed.
8. Image size: `bisg/perception` is 14.4 GB (mostly the CUDA toolkit). Build once; it is not rebuilt by `./bisg setup`.

## 6. Benchmark

`./bisg perception bench [isaac_ros|ros2|all] [-c scenario] [--tag name]` boots the sim, MAVROS and `vio_mock` (the mock **flies**), starts the backend in
observer mode and runs `tests/vio_flight.py` (takeoff, 3 m square at 2 m, land), so every backend sees an identical trajectory and none influences it. A collector
(`bisg_perception/bench`) listens during the flight; a host-side sampler records CPU/GPU every 2 s. `./bisg perception report` merges the JSON into one table.

| Metric | How |
|---|---|
| ATE RMSE | `perception/odom` vs Pegasus ground truth `state/pose`: rigid (Umeyama) alignment, plus origin-aligned RMSE / max / end-point drift and scale |
| Depth error | `perception/disparity` → depth vs the sim's exact `depth_registered`, matched by header stamp, pixels the sim sees at 0.5–6 m: coverage, MAE, median, RMSE, relative error |
| Rate | output frames per sim second |
| Latency | wall time from the input frame reaching the collector to the backend's output reaching it (excludes the sim, includes DDS) |
| Resources | backend container CPU % (100 = one core) and RAM; GPU memory held by the backend's processes; whole-GPU utilisation |

Ground truth is read only by the benchmark (parity rule, plan.md §8). Raw files: `logs/perception/` (git-ignored).

RESULTS_PLACEHOLDER

## 7. Jetson / real drone

The same two backends are meant to run against the real ZED wrapper: it publishes the same `zed/zed_node/...` topics and a correct right-camera `P`. Isaac ROS
`release-4` has `noble-jetpack` arm64 packages (checked 2026-10-03: ~239 Jazzy packages); **not tested on the Orin NX** — the image here is x86-only.
For the real drone use `vio_relay` with `in_topic:=zed/zed_node/odom publish_zed_odom:=false` (ZED SDK tracking), or `perception/odom` from cuVSLAM.

## 8. Adding a backend

Publish `perception/odom` (+ optionally `perception/disparity`) in `/drone_<n>`, add a branch in `perception.launch.py`, add the name to
`backend_ok` in `scripts/perception.sh` and to the comment in `config/bisg.conf`. Nothing else changes.
