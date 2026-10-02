---
name: perception
description: Switch or debug the perception backend (vio_mock | Isaac ROS 4.6 cuVSLAM + VPI depth | traditional CPU rtabmap + stereo_image_proc), run the backend benchmark, read its results, rebuild the bisg/perception image. Use when the user asks about Isaac ROS, VSLAM/odometry from the sim cameras, stereo depth, GPU vs CPU perception, or PERCEPTION_BACKEND.
---

# perception

Design, interface and results: `docs/perception.md` (read it first). ADR-006.

## Switch
- Key: `PERCEPTION_BACKEND=mock|isaac_ros|ros2` (`./bisg config` shows where it is set). `mock` is the default and what tests assume.
- Per run: `PERCEPTION_BACKEND=isaac_ros SIM_SCENARIO=single_iris_vio_midres ./bisg all headless`.
- On a running sim: `./bisg perception up isaac_ros|ros2|mock [--observer]` (`--observer` = does not feed MAVROS), `./bisg perception status|down`.
- `PERCEPTION_IMU=true` = cuVSLAM visual-inertial mode, `PERCEPTION_DEPTH=false` = no disparity node.

## Prerequisites
1. `./bisg perception build` (image `bisg/perception:jazzy`, 14 GB, three apt repos) and `./bisg ros build` (colcon: `bisg_vehicle`, `bisg_perception`).
2. A scenario with the ZED rig. Without `sudo sysctl net.core.rmem_max=16777216` HD720 images do not arrive (bugs.md B2): use `single_iris_vio_midres` (448×252) or `_lowres` (320×180).

## Benchmark
`./bisg perception bench [isaac_ros|ros2|all] [-c scenario] [--tag t]`, then `./bisg perception report`. The mock flies, the backend observes; metrics = ATE vs ground truth, depth error vs the sim's depth, rate, wall latency, CPU/GPU. Set `PERCEPTION_IMU=true` and `--tag <scenario>_imu` for the VIO variant.

## Debug checklist
- No `perception/odom`: `docker logs bisg-perception-1`. cuVSLAM warns `Delta between current and previous frame … above threshold` → raise `image_jitter_threshold_ms` (sim frame interval is in sim time).
- Depth off by a factor ~fx: Isaac ROS `DisparityImage.t` = fx·baseline, stereo_image_proc `t` = baseline.
- Odometry/depth nonsense and zero baseline: right `camera_info.P[0,3]` must be `−fx·baseline` (`zed_rig.py`).
- Nodes cannot find TF: `tf_relay` must be running (the rig's static TF is per-drone, listeners read global `/tf_static`).
- `exec: perception: not found`: stale image entrypoint → `./bisg perception build`.
- Nothing arrives at HD720: rmem_max, see above. Real-time factor matters: nodes run on sim time; a slow sim means low wall rates.
- Never run two vision sources into MAVROS: `perception up <non-mock>` stops `vio_mock`.

## Never
- Do not make a backend the default without the ADR-006 trade-offs and a passing `tests/vio_flight.py` closed-loop run.
- Do not put Isaac ROS packages in `bisg_perception/package.xml` (they only exist in `bisg/perception`; `rosdep` in `bisg/ros` would fail).
