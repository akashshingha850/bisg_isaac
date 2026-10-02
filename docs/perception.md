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

### 6.1 Results (Isaac Sim 5.1, headless, sim at 1.17× real time, 2026-10-03)

Same flight for every backend (`tests/vio_flight.py`, `vio_mock` flying, backend observing). **448×252 is the main benchmark** (the largest size that reaches subscribers without the
`rmem_max` sysctl): 2 repetitions per column, shown as `mean (min–max)`. 320×180 is a single-run reference. Both resolutions are far below the real ZED's HD720, see the limits below.

### single_iris_vio_lowres

| Metric | ros2 (CPU) | isaac_ros (GPU) | isaac_ros + IMU |
|---|---:|---:|---:|
| runs | 1 | 1 | 1 |
| sim real-time factor | 1.15× | 1.18× | 1.18× |
| **Odometry (vs sim ground truth)** |  |  |  |
| output rate (sim Hz) | 17.8 | 17.9 | 17.8 |
| ATE RMSE, rigid-aligned (m) | 0.77 | 0.74 | 0.99 |
| ATE RMSE, origin-aligned (m) | 1.07 | 1.18 | 1.54 |
| max error, origin-aligned (m) | 2.74 | 2.15 | 2.85 |
| end-point drift over an 18 m path (m) | 1.91 | 1.27 | 2.50 |
| scale (1 = metric) | 0.85 | 1.16 | 0.85 |
| latency p50 (wall ms) | 18.2 | 0.5 | 1.9 |
| latency p95 (wall ms) | 23.1 | 1.9 | 4.4 |
| **Stereo depth (vs sim depth, 0.5–6 m)** |  |  |  |
| output rate (sim Hz) | 17.9 | 17.9 | 17.8 |
| coverage of sim-valid pixels | 44 % | 61 % | 63 % |
| median |error| (m) | 1.55 | 3.29 | 3.39 |
| median relative error | 35 % | 131 % | 138 % |
| 0.5-1.5 m: coverage / bias est÷gt | 7 % / 11.52 | 33 % / 6.83 | 37 % / 7.27 |
| 1.5-3.0 m: coverage / bias est÷gt | 23 % / 4.00 | 40 % / 2.92 | 42 % / 3.16 |
| 3.0-6.0 m: coverage / bias est÷gt | 49 % / 1.32 | 61 % / 1.65 | 63 % / 1.67 |
| latency p50 / p95 (wall ms) | 5.1 / 5.7 | 0.9 / 1.8 | 0.9 / 1.7 |
| **Resources (backend container)** |  |  |  |
| CPU % mean (100 = 1 core) | 101 | 47 | 47 |
| RAM (MiB) | 356 | 484 | 484 |
| GPU memory held (MiB) | 618 | 938 | 938 |
| whole-GPU utilisation % (sim + backend) | 25 | 27 | 27 |
| CPU time per depth frame (ms) | 49 | 22 | 22 |

### single_iris_vio_midres

| Metric | ros2 (CPU) | isaac_ros (GPU) | isaac_ros + IMU |
|---|---:|---:|---:|
| runs | 2 | 2 | 2 |
| sim real-time factor | 1.16× (1.16–1.16) | 1.18× (1.18–1.18) | 1.16× (1.16–1.16) |
| **Odometry (vs sim ground truth)** |  |  |  |
| output rate (sim Hz) | 17.2 (17.0–17.3) | 17.5 (17.4–17.5) | 17.4 (17.4–17.5) |
| ATE RMSE, rigid-aligned (m) | 0.29 (0.26–0.33) | 0.59 (0.59–0.60) | 0.74 (0.73–0.76) |
| ATE RMSE, origin-aligned (m) | 0.46 (0.41–0.51) | 1.12 (1.09–1.14) | 1.31 (1.25–1.37) |
| max error, origin-aligned (m) | 0.97 (0.96–0.97) | 1.69 (1.63–1.76) | 2.15 (2.09–2.20) |
| end-point drift over an 18 m path (m) | 0.75 (0.67–0.84) | 1.36 (1.35–1.37) | 1.88 (1.81–1.96) |
| scale (1 = metric) | 0.96 (0.95–0.97) | 1.07 (1.06–1.08) | 1.04 (1.03–1.06) |
| latency p50 (wall ms) | 15.0 (14.9–15.1) | 0.5 (0.5–0.5) | 2.4 (2.4–2.4) |
| latency p95 (wall ms) | 19.6 (19.6–19.6) | 2.6 (2.5–2.6) | 4.5 (4.4–4.6) |
| **Stereo depth (vs sim depth, 0.5–6 m)** |  |  |  |
| output rate (sim Hz) | 17.3 (17.2–17.4) | 17.6 (17.6–17.6) | 17.5 (17.5–17.6) |
| coverage of sim-valid pixels | 50 % (49–50) | 67 % (67–68) | 68 % (67–68) |
| median |error| (m) | 1.16 (1.12–1.21) | 3.06 (2.95–3.17) | 3.01 (2.98–3.03) |
| median relative error | 26 % (25–27) | 128 % (126–130) | 125 % (124–126) |
| 0.5-1.5 m: coverage / bias est÷gt | 7 % (6–7) / 5.63 (5.41–5.85) | 29 % (29–30) / 5.48 (5.47–5.50) | 30 % (29–32) / 5.55 (5.40–5.71) |
| 1.5-3.0 m: coverage / bias est÷gt | 24 % (23–24) / 3.92 (3.74–4.09) | 43 % (43–44) / 3.30 (3.29–3.31) | 44 % (43–45) / 3.16 (3.07–3.26) |
| 3.0-6.0 m: coverage / bias est÷gt | 55 % (54–55) / 1.22 (1.21–1.23) | 69 % (68–69) / 1.77 (1.76–1.78) | 69 % (68–70) / 1.72 (1.71–1.73) |
| latency p50 / p95 (wall ms) | 10.5 (10.5–10.5) / 11.4 (11.4–11.4) | 1.2 (1.2–1.2) / 2.1 (2.1–2.1) | 1.1 (1.0–1.2) / 2.0 (2.0–2.1) |
| **Resources (backend container)** |  |  |  |
| CPU % mean (100 = 1 core) | 103 (102–104) | 46 (43–50) | 50 (50–50) |
| RAM (MiB) | 356 (356–357) | 493 (490–497) | 498 (497–499) |
| GPU memory held (MiB) | 0 (0–0) | 976 (976–976) | 976 (976–976) |
| whole-GPU utilisation % (sim + backend) | 28 (28–28) | 30 (30–30) | 30 (30–30) |
| CPU time per depth frame (ms) | 51 (50–52) | 22 (21–24) | 24 (24–25) |

**Reading the tables**

| | `ros2` (CPU) | `isaac_ros` (GPU) |
|---|---|---|
| Odometry accuracy (448×252) | **better**: 0.29 m ATE, 0.75 m end drift over 18 m (4 %) | 0.59 m ATE, 1.36 m drift (7.5 %); IMU fusion did not help (0.74 m) |
| Odometry latency | 15 ms | **0.5 ms** (30× lower; 2.4 ms with IMU) |
| Depth latency | 10.5 ms | **1.2 ms** (9× lower) |
| CPU of the backend container | 103 % (one full core) | **46 %**; 22 ms of CPU per depth frame vs 51 ms |
| GPU cost | none | 0.98 GB VRAM, ~+2 points of whole-GPU utilisation (the sim dominates the GPU) |
| Stereo depth accuracy | **better**: 26 % median relative error, 50 % of pixels valid | dense (67 % valid) but **biased**: 128 % median relative error |
| Closed loop (backend feeds PX4, `vio_flight`) | flew the whole square and landed, but 0.35 / 0.42 / 0.90 m max error, **FAIL** vs 0.3 m | **aborted at takeoff** (estimate 0.9 m low in height) |

Reference: `vio_mock` flies the same test at 0.05 / 0.07 / 0.03 m.

**What this does and does not show**
* Isaac ROS is clearly **cheaper per frame and far lower latency**, which is its selling point, and it scales with GPU headroom. Here that is not stressed: the sim only delivers ~17.5 frames per
  second at 448×252 and both backends keep up. The CPU pipeline already uses a full core at that size; at HD720 and 30 fps it would need several times that (**extrapolation, not measured**).
* On **accuracy** the traditional pipeline won in this scene. cuVSLAM under-estimates the height gained during the climb (about 0.7 m of 2 m) and its VIO mode did not fix it; the Isaac ROS SGM disparity is dense
  but systematically biased (est÷gt depth 5.5× at 0.5–1.5 m, 3.3× at 1.5–3 m, 1.8× at 3–6 m; the CPU SGBM is accurate at 3–6 m but rejects most near pixels). A sweep of `confidence_threshold`
  (60000 down to 2000) changed nothing, and the input is fed exactly as in NVIDIA's own Isaac Sim stereo launch file, so this is not a configuration slip we could find. Likely causes (untested): the sim's low-texture / repetitive-brick
  scene, the tiny disparities at this resolution (3 px at 3 m), and SGM smoothing. NVIDIA's DNN depth (ESS) would be the next thing to try; it needs a model download we did not do.
* **Resolution is the limit for both**: fx is 249 px (448×252) vs 710 px at HD720, so depth noise at 5 m is ~3× smaller at HD720 and VSLAM scale is far better observable. The headline accuracy
  conclusions above may reverse at HD720; **re-run after enabling the sysctl** (§5.6): `./bisg perception bench all -c single_iris_vio`.
* n = 2 (448×252) and 1 (320×180): the 448×252 repeats agree closely (the sim is deterministic enough), but 320×180 results swing between runs (earlier repeats of the same backend gave ATE 0.41 vs 0.74 m for `isaac_ros` and 1.17 vs 0.77 m for `ros2`). Treat 320×180 as indicative only.
* The ZED SDK's own tracking (what the real drone uses today) was not part of this comparison; it needs the real camera.

**Bottom line for the project:** keep `PERCEPTION_BACKEND=mock` as the default. The switch, both backends, the contract mapping and the benchmark now exist and work end to end, so the choice between
Isaac ROS and CPU ROS 2 can be made on HD720 numbers (and later on the Orin NX) without further plumbing. Do not fly either closed-loop on real hardware from these results.


## 7. Jetson / real drone

The same two backends are meant to run against the real ZED wrapper: it publishes the same `zed/zed_node/...` topics and a correct right-camera `P`. Isaac ROS
`release-4` has `noble-jetpack` arm64 packages (checked 2026-10-03: ~239 Jazzy packages); **not tested on the Orin NX** — the image here is x86-only.
For the real drone use `vio_relay` with `in_topic:=zed/zed_node/odom publish_zed_odom:=false` (ZED SDK tracking), or `perception/odom` from cuVSLAM.

## 8. Adding a backend

Publish `perception/odom` (+ optionally `perception/disparity`) in `/drone_<n>`, add a branch in `perception.launch.py`, add the name to
`backend_ok` in `scripts/perception.sh` and to the comment in `config/bisg.conf`. Nothing else changes.
