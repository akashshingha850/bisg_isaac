# ZED module test + benchmark

`./bisg zed bench` (`tests/zed_bench.py`) switches every ZED SDK module on in turn, on **one** wrapper, and records for each: does it publish sane
data (function), at what rate, and what it costs. `./bisg zed bench --quick` skips the AI models; `--streaming` adds the streaming server (see B19).
Host-side micro-benchmarks of our own code: `python3 tests/zed_bench_offline.py`. Raw data: [data/zed_bench_2026-10-05.json](data/zed_bench_2026-10-05.json).

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
