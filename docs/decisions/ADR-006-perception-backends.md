# ADR-006 — Switchable perception backends (Isaac ROS 4.6 or traditional ROS 2)

Status: **accepted** (2026-10-03). Results and method: [`../perception.md`](../perception.md).

## Context
`vio_mock` (ground truth + noise) hides everything a real visual front end does: drift, scale error, latency, CPU/GPU cost. Before flying the
Jetson we want to see how a real stereo VIO and stereo depth behave on the sim's ZED stream, and to choose between NVIDIA's GPU-accelerated
**Isaac ROS** packages and ordinary CPU ROS 2 packages. The Isaac Sim ROS 2 bridge is the sim's transport and is common to both; it is not the alternative.

## Decision
- One config key, `PERCEPTION_BACKEND = mock | isaac_ros | ros2` (`config/bisg.conf`), one compose service `perception` selected by env, one image `bisg/perception`.
- Every backend publishes the same interface (`perception/odom`, `perception/disparity`); `vio_relay` maps it onto the vehicle contract
  (`zed/zed_node/odom`, `mavros/odometry/out`). Backends are therefore replaceable, including by the real ZED wrapper on hardware.
- Isaac ROS **release-4 (4.6, Jazzy)**: the only line that matches ROS 2 Jazzy (ADR-005). release-5 is Lyrical-only (verified against the apt repos, 2026-10-03).
- `mock` stays the default: it is deterministic, GPU-free and what the regression tests assume. A backend is an opt-in, never a silent replacement.
- A benchmark mode runs a backend as a passive observer on the same flight, so backends are compared on identical input without influencing it.

## Consequences
- New image (14.4 GB; CUDA 13.2 userspace, runs on the 580 driver), new ROS package `bisg_perception`, `vio_relay` in `bisg_vehicle`, CLI `./bisg perception`.
- The sim rig must publish a correct right-camera `P` and rate-gated, paired image/camera_info streams (done).
- Isaac ROS and the CUDA/VPI apt repos are external dependencies of the image build (three repos, `docker/perception/Dockerfile`).
- Closed-loop flight on a non-mock backend is only as good as that backend at the available resolution; at 320×180 and 448×252 it is not flight-grade (perception.md §6).
- Jetson (Orin NX, JetPack 7.2): `noble-jetpack` arm64 packages exist for release-4; not tested.
