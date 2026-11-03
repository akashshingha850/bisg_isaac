# ZED module test + benchmark

`./bisg zed bench` (`tests/zed_bench.py`) switches every ZED SDK module on in turn, on **one** wrapper, and records for each: does it publish sane
data (function), at what rate, and what it costs. `./bisg zed bench --quick` skips the AI models; `--streaming` adds the streaming server (see B19).
Host-side micro-benchmarks of our own code: `python3 tests/zed_bench_offline.py`. Raw data: [data/zed_bench_2026-10-05.json](data/zed_bench_2026-10-05.json).

Measured before the default world became the Warehouse (2026-10-17); not re-run there.

**Setup (2026-10-05):** Isaac Sim 6.0 headless, `single_iris` (Simple Room), real ZED SDK 5.4.1 (`ZED_SOURCE=sdk`) on the Isaac ZED Mini twin, HD720 / 30 fps, `NEURAL_LIGHT`
depth, RTX 4500 Ada. The drone sits on the ground (static scene, nothing in view but the room). 20 s measured window per phase after a 6 s warm-up; each phase
subscribes only to its own module's topics. Every other `publish_*` switch is on (the wrapper only computes a product while it has a subscriber).

## Result: 16/16 phases pass (1 warning)

| phase | result | rate wall / sim Hz | wrapper CPU (cores) | wrapper RAM (GB) | GPU MB vs idle | sim RTF | what was checked |
|---|---|---|---|---|---|---|---|
| idle | PASS | - | 0.47 | 0.9 | +0 | 0.82 | baseline: wrapper running, nothing requested |
| video_left | PASS | 24 / 30 | 0.51 | 0.9 | +4 | 0.80 | 1280x720 |
| video_stereo | PASS | 24 / 30 | 0.55 | 0.9 | +5 | 0.79 | 1280x720 |
| video_variants | PASS | 23 / 30 | 0.68 | 0.9 | +5 | 0.78 | 1280x720 |
| depth | PASS | 24 / 30 | 0.50 | 1.0 | +5 | 0.80 | 63% valid, 1.57-5.11 m |
| point_cloud | PASS | 10 / 12 | 0.50 | 1.0 | +20 | 0.80 | 448x256 points, fields x,y,z,rgb |
| depth_extras | PASS | 23 / 30 | 0.62 | 1.0 | +20 | 0.78 | f*T/disparity vs depth = 1.000; confidence 0-100; depth_info 0.45-5.18 m |
| roi_mask | WARN | - | 0.49 | 1.0 | +20 | 0.81 | no mask published (automatic ROI needs the camera to see parts of the robot; the sim view is clear) |
| tracking | PASS | 24 / 30 | 0.51 | 1.1 | +21 | 0.81 | odometry_status=0, odom (0.002, 0.025, -0.005) frame odom->zed_camera_link |
| tracking_extras | PASS | 24 / 30 | 0.48 | 1.1 | +21 | 0.81 | cov diag x=3.00e-02 yaw=3.63e-03; path_odom 586 poses; path_map 586 poses; landmarks 3027 |
| imu | PASS | 121 / 150 | 0.47 | 1.1 | +21 | 0.81 | imu/data ok; imu/data_raw ok |
| spatial_mapping | PASS | 1 / 1 | 0.64 | 5.3 | +26 | 0.81 | 40159 points, frame map |
| plane_detection | PASS | - | 0.52 | 1.2 | +22 | 0.81 | normal (-0.83,-0.07,-0.56), 211 triangles |
| drone_core | PASS | 23 / 30 | 0.65 | 1.2 | +22 | 0.78 | stereo + depth + cloud + odometry + imu together |
| object_detection | PASS | 24 / 30 | 0.60 | 5.2 | +116 | 0.81 | 0 objects in view (the room has none; this proves the model runs, not accuracy) |
| body_tracking | PASS | 24 / 30 | 0.66 | 8.1 | +146 | 0.80 | 0 skeletons in view (none in the room: runs, accuracy untested) |

*Rates:* the sim runs at ~0.8x real time here (static drone, headless), so **sim Hz is the camera's rate** (30 fps grab; cloud 10 Hz as configured; IMU is the sim's own 150 Hz publisher),
wall Hz is what a consumer sees. *CPU* = the wrapper's processes only (`/proc`), in cores. *GPU MB* is the whole card minus the `idle` phase; *GPU %* is not tabulated
because `nvidia-smi` sees the sim and the SDK together and read 50-55 % in **every** phase, idle included.

## What the numbers say
- **The base pipeline is the cost, the products are nearly free.** With nothing subscribed the wrapper already burns 0.47 cores and ~51 % of the GPU (SDK grab, `NEURAL_LIGHT` depth, positional tracking
  run continuously); adding image, depth, cloud, disparity, confidence, odometry, paths or IMU topics moves CPU by about 0.2 cores at most and GPU memory by < 30 MB. The "typical drone load" (stereo + depth + cloud +
  odometry + IMU) is 0.65 cores, 1.2 GB RAM. Choose `depth_mode` and resolution/fps for cost; `publish_*` switches are free.
- **RAM is the real constraint on the Orin NX:** spatial mapping +4.2 GB (voxel map, 5 cm), object detection +4.1 GB, body tracking +7 GB while on (mapping's memory was released when switched off: the following phases were back at 1.2 GB; release after detection / body tracking was not observed because they ran last).
  Mapping, detection and body tracking therefore cannot all run on an 8 GB module next to the SDK base; measure on the Jetson before enabling them.
- **AI start-up is slow once:** object detection `enable_obj_det` took 278 s on first use (model download + TensorRT optimisation, cached in the `zed-resources` volume afterwards), body tracking 80 s,
  mapping 21 s. Enable them at boot or well before they are needed, not in flight.
- **Sim speed:** the SDK costs the sim nothing measurable: RTF stayed 0.77-0.82 in every phase (idle 0.82).
- **Depth quality in the sim:** 63 % valid pixels, 1.6-5.1 m in this small room; disparity agrees with depth exactly (f·T/disparity = 1.000), confidence spans 0-100, depth_info 0.45-5.2 m.
- **Tracking, stationary:** odometry stays within 3 cm of the start over the whole run, status OK, covariance finite (σ² x 3e-2, yaw 3.6e-3), 3,000 landmarks.

## Caveats and findings
- **Streaming server crashes the wrapper in the sim** (`enable_streaming` → "Cannot enable streaming: Err Code 3", then SIGSEGV): the twin is itself a stream input. Not a hardware finding; opt-in only (`--streaming`), see bugs.md B19.
- **ROI mask: WARN** — automatic ROI only masks parts of the robot that stay in the camera's view; the sim camera sees none, so no mask is published. Test it on the real drone.
- **Object / body detection run but are not accuracy-tested:** the room contains no people or vehicles, so 0 detections is the correct answer; this proves the models load and publish at the camera rate (24 / 30 Hz).
- **Plane detection** works from a clicked point in the `odom` frame (it needs a TF path to the camera; `publish_map_tf: false` means no `map` frame); the click topic is `/clicked_point`.
- `imu/data_raw` came at the camera frame rate (24 / 30 Hz) from the stream's frame-rate IMU, `imu/data` at 150 Hz from the sim's own publisher; the real 400 Hz sensor stream exists only on hardware (zed-sdk-sim.md).
- The GPU is shared with Isaac Sim, so absolute GPU load is an upper bound for the SDK alone; the Orin NX numbers are still to be taken on the bench (`docs/todo.md`).
- Static scene: tracking/mapping cost under motion (feature churn, map growth) is not covered.

## The bridge container (`./bisg zed bench` prints `docker stats` after the run)
`zed-bridge` with `health` + `obstacle_distance` on (odometry off, sim default): **0.31 cores, 59 MB** while the wrapper publishes depth at 24 Hz. The 1 ms of maths below is not the cost: it is
receiving and deserialising a 3.7 MB depth frame 24 times a second in Python (twice: both modules subscribe to depth). If that matters on the Orin NX, subscribe once and share the frame,
or lower `pub_frame_rate`/depth resolution. A second full run (`--quick`) reproduced every rate, RTF and CPU figure above to within a few percent.

## Our own code (host, 1 core, `tests/zed_bench_offline.py`)
| what | input | mean ms |
|---|---|---|
| config load + validate + compile (every wrapper start) | docker/zed/zed.yaml | 15.8 |
| bridge `obstacle_distance`: depth → 72 sectors | HD720 (1280x720) | 1.06 |
| | VGA (672x376) | 0.27 |
| | 320x180 | 0.07 |

The module runs at <= 10 Hz, i.e. ~1 % of one core at HD720 on this host (the Orin NX core is slower; still two orders of magnitude of headroom).


## Second workstation, split GPUs (2026-10-07, `ict-em018kc6`, 2x RTX 6000 Ada)

`SIM_GPU=0 ZED_GPU=1` (docker/.env): Isaac Sim on GPU 0, the ZED wrapper alone on GPU 1 (`NVIDIA_VISIBLE_DEVICES` per container, `docker/compose.yaml`). Same bench, HD720 / 30 fps,
`single_iris` on the Full Warehouse preset, `net.core.rmem_max=16 MB`. **16/16 phases pass (1 WARN: `roi_mask`, as before)**; raw data: [data/zed_bench_2026-10-07_ict-em018kc6.json](data/zed_bench_2026-10-07_ict-em018kc6.json).
- The Isaac python process sits on GPU 0 (about 4 GB, about 36 % busy); the wrapper's `component_container` on GPU 1 (1.7 GB for the base pipeline, 3.6 GB with every module on). The stream between them crosses via host shared memory, so the split needs no extra setup.
- Camera and depth publish at 21 Hz wall (30 Hz sim, sim RTF 0.70), cloud 10 Hz, wrapper about 1.2 cores. Because the bench runs inside the wrapper container, its GPU columns are the ZED GPU only (no sim noise).
- **Everything on at once** (video variants, depth extras, ROI, tracking extras, plane detection, spatial mapping, object detection, body tracking): wrapper 1.65 cores, 4.8 GB RAM, 3.6 GB GPU 1 at 3 % utilisation. Images 21 Hz, depth 21 Hz, cloud 10 Hz, odom 21 Hz, fused cloud 1 Hz. Objects / skeletons / plane publish only when something is in view (nothing is, so no messages).
- Not covered: `global_localization` (needs a GNSS fix) and `streaming` (conflicts with the sim stream, B19).

## Orin NX 16 GB, real ZED Mini (2026-11-03)

First numbers on the drone's own hardware (`bisg/zed:jetson`, SDK 5.4.1, L4T R39.2.1, power mode 40 W, nothing else on the GPU). One wrapper container,
positional tracking + spatial mapping (5 cm) + plane detection on, 30 fps grab, `tegrastats` averaged over 30 s. "Consumers" = `ros2 topic hz` on left image,
depth, confidence, cloud (10 Hz) and odom, run inside the container, so their own CPU is in the CPU column (an upper bound).

| config | consumers | rate (depth / image / odom) | GPU avg (max) | CPU avg | board power |
|---|---|---|---|---|---|
| HD1080, `NEURAL_PLUS` | none | not measured | 35 % (52) | 42 % | 12.0 W |
| HD1080, `NEURAL_PLUS` | 5 | 10 Hz | 85 % (99) | 56 % | 23.8 W |
| HD720, `NEURAL_PLUS` | none | not measured | 37 % (55) | 42 % | 11.7 W |
| HD720, `NEURAL_PLUS` | 5 | 12 Hz | 93 % (99) | 54 % | 25.2 W |
| HD720, `NEURAL` | none | not measured | 33 % (43) | 44 % | 11.0 W |
| HD720, `NEURAL` | 5 | 25 Hz | 68 % (98) | 52 % | 19.2 W |

- **Depth consumers, not the grab, drive the GPU:** 35 % with nothing subscribed against 85-93 % once depth is requested. (The Jetson's own desktop session
  - GNOME, Xorg, VS Code - sits at 21-28 % GPU and 19-28 % CPU with no ZED running, so most of that 35 % is the desktop.)
- **`NEURAL_PLUS` cannot hold 30 fps on an Orin NX:** the odometry rate falls with it (12 Hz), because tracking and depth share one grab loop. Stereolabs lists it at ~8 fps on an Orin NX 8 GB.
- **Resolution matters little** (10 -> 12 Hz from HD1080 to HD720): the depth network, not the pixel count, is the cost. `NEURAL` doubles the rate and saves ~6 W.
- Measured next (below): `NEURAL_LIGHT`, mapping off, the bridge and video containers on top, publish rate, spare GPU. Not measured: `pub_resolution: CUSTOM`
  (would change `camera_info` size, contract check 4), `grab_compute_capping_fps`, Cyclone shared memory.
- The first start of a depth mode optimises its TensorRT model for ~6 min (cached in the `zed-resources` volume); a measurement taken during it is meaningless (one run was discarded for that).

### Sweet spot for the Orin NX (2026-11-03, same day, later runs)

Method: HD720, wrapper alone, the five consumers of the table above run in a *separate* container on the same DDS domain (the wrapper's CPU is read from its
own cgroup, so the measuring tools are not in it), 30 s of `tegrastats`. Idle desktop for reference: 21 % GPU, 19 % CPU, 7.4 W.

| depth mode | mapping | rate | GPU avg (max) | wrapper cores | board power | RAM |
|---|---|---|---|---|---|---|
| `NEURAL_LIGHT` | on | 26 Hz | 36 % (72) | 1.11 | 13.9 W | 9.1 GB |
| `NEURAL_LIGHT` | off | 26 Hz | 34 % (71) | 1.09 | 13.8 W | 5.1 GB |
| `NEURAL` | on | 25 Hz | 47 % (98) | 1.19 | 18.8 W | 9.3 GB |
| `NEURAL` | off | 27.5 Hz | 60 % (98) | 1.11 | 19.1 W | 5.1 GB |
| `NEURAL_PLUS` | on | 12 Hz | 93 % (99) | - | 25 W | - |

- Depth mode moves the GPU, not the CPU (the wrapper is ~1.1 cores in every mode; publishing and tracking dominate). Mapping costs 4 GB of RAM - shared with the GPU - and no measurable CPU/GPU.
- No mode reaches the 30 Hz grab (best 27.5 Hz) with five Python consumers attached.

**Full stack** (wrapper + `zed-bridge` health + obstacle, bridge odometry off so nothing reaches EKF2, + `zed-video` grid + MAVROS), mapping off:

| depth mode | publish | GPU avg (max) | wrapper | bridge | video | MAVROS | host CPU | power |
|---|---|---|---|---|---|---|---|---|
| `NEURAL_LIGHT` | 30 Hz | 30 % (72) | 0.96 | 0.59 | 0.96 | 0.27 | 53 % | 14.7 W |
| `NEURAL` | 30 Hz | 58 % (98) | 1.05 | 0.57 | 0.98 | 0.28 | 53 % | 19.7 W |
| `NEURAL_LIGHT` | **15 Hz** | 31 % (83) | 0.86 | 0.40 | 0.84 | 0.27 | 46 % | 13.2 W |
| `NEURAL` | 15 Hz | 58 % (98) | 0.86 | 0.40 | 0.87 | 0.27 | 47 % | 18.8 W |

Cores are of 8. Publishing images + depth at 15 Hz is what the consumers use (obstacle map 10 Hz, QGC grid 15 fps) and cuts the bridge by a third; odometry stays at the grab rate (24-29 Hz).
The Python services (bridge + video) cost more than MAVROS (0.27) and about as much as the wrapper: the video's 0.85 core is image composition (the hardware `nvv4l2h264enc` is used), one tile of which, the chase view, never has a source on the drone.

**Spare GPU** (full stack at 15 Hz + a saturating FP32 CUDA job beside it; the job alone gets 1333 GFLOP/s):

| depth mode | CUDA job keeps | ZED odometry alone -> with job | ZED depth alone -> with job |
|---|---|---|---|
| `NEURAL_LIGHT` | 980 GFLOP/s (74 %) | 25.1 -> 24.6 Hz | 14.8 -> 14.7 Hz |
| `NEURAL` | 759 GFLOP/s (57 %) | 26.4 -> **20.1 Hz** | 14.6 -> 14.5 Hz |

`GR3D_FREQ` is relative to the current GPU clock, which is lower under `NEURAL_LIGHT`, so this table, not the percentages, is the headroom figure.
**Chosen for the drone: HD720, `NEURAL_LIGHT`, mapping off, publish 15 Hz** (`docker/zed/zed.yaml`; the `sim:` block keeps `NEURAL_PLUS`, mapping on, 30 Hz).
Caveats: `NEURAL_LIGHT`'s ideal range is 0.3-5 m (error < 8 % to 12 m, Stereolabs) while `obstacle_distance` reports to 8 m - not checked against real obstacles yet;
the desktop session (21-28 % GPU) is still on, headless would give that back.
