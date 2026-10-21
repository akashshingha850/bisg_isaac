# ADR-008 — One YAML for the whole ZED SDK, one image, small services around the wrapper

Status: accepted (2026-10-05); sim side verified, hardware side to be verified in Phase 5

## Context
ZED features were scattered: `deploy/jetson/zed_params.yaml` (wrapper switches) + `deploy/sim/zed_sim_overlay.yaml` (sim deltas) +
`OBST_*` / `VIDEO_*` keys in `config/bisg.conf` + a depth→obstacle script baked into the `bisg/ros` image + a video script in the same image.
Turning a feature on meant knowing which of five places owned it, and nothing checked a misspelt wrapper key (the wrapper ignores it silently).
The "ZED → PX4 bridge" was a plan (`archive/docs/zed-px4-bridge.md`) with one prototype.

## Decision
- **`docker/zed/zed.yaml` is the only place** that says what the ZED does: a block per SDK module (camera, video, sensors, depth, region of interest,
  positional tracking, global localization, spatial mapping, plane detection, object detection, body tracking, streaming, recording), a `services:`
  block, and a `sim:` block for the sim-only deltas. Module keys are the wrapper's own names, validated against the wrapper's shipped YAML
  (unknown key / wrong type / bad enum / "needs depth" fail in `./bisg zed plan` before any container starts).
- `python3 -m zed_stack compile` turns it into the wrapper's `ros_params_override_path` file inside the container, so sim and Jetson run the same compile.
- **One image `bisg/zed`** (Stereolabs' + CycloneDDS + `mavros_msgs` + GStreamer) runs three compose services: `zed` (wrapper), `zed-bridge`
  (health / odometry / obstacle_distance → MAVROS → PX4, one rclpy node, one module per feature), `zed-video` (QGC). `./bisg zed up` starts the wrapper and
  exactly the services the YAML enables. MAVROS stays the PX4 link (ADR-001) with the lean plugin list; the bridge only needs its messages.
- Sim and real drone share **one** `docker/compose.yaml` (the former `deploy/jetson/compose.yaml` is gone): profile `zed` (sim twin) and `drone` (real camera + MAVROS on the Pixracer serial link) differ only in the camera source, `ZED_STACK_SIM` and the MAVROS link; the image tag follows the CPU architecture (`ZED_VARIANT`). `./bisg drone` operates it.
- Not in the bridge yet: DISTANCE_SENSOR, MAVLink camera component, FOLLOW/LANDING_TARGET, PX4 GPS → ZED. They need either raw MAVLink packing or `zed_msgs` and
  sim actors; each lands as a module with a fake-topic test, one at a time.

## Consequences
- `deploy/jetson/zed_params.yaml`, `deploy/sim/*`, `OBST_*`/`VIDEO_*` and the `./bisg video|obstacle` commands are gone; `bisg/ros` lost GStreamer.
- Changing a ZED switch = `./bisg zed set key=value` (or edit the file) + `./bisg zed up`; services only: `./bisg zed services`.
- The emulated rig (`ZED_SOURCE=emulated`) reads the same file through `zed_stack`, so "feature on but not simulated" is still reported.
- `bisg/zed` must be rebuilt (`./bisg zed image`, overlay layer only) on the Jetson too; the bridge then runs next to the wrapper.
