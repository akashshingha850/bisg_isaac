# ADR-011 — zed-ros2-wrapper pinned to an upstream master commit, not a release tag

Status: accepted (2026-10-21); to be revisited when a wrapper release contains `cd8bf73`

## Context
The wrapper was pinned to the tag matching the SDK (`v${ZED_SDK}` = `v5.4.1`). In the sim it aborts with R9 (`can't compare times
with different time sources`, exit -6, the `zed` container then stays down: B18). The `terminate_bt` throw-site stack (2026-10-20)
is `ZedCamera::handleVideoDepthPublishing()`: its `rclcpp::Time pub_ts` is default-constructed (`RCL_SYSTEM_TIME`), `publishVideoDepth()`
leaves it unset when the SDK returns the same grab timestamp twice, and with `sensors.sensors_image_sync` on a non-ZED model
(the sim sets it: zed.yaml `sim:`) the comparison with `TIMEZERO_ROS` throws. The sim at ~0.5x real time repeats grabs often;
spatial mapping makes it worse (the crash came 2 s after mapping started). A wrapper bug, not an SDK one.
Upstream fixed it in PR #460 (`cd8bf73`, merged 2026-10-07 as `b19902d`, master = `v5.5.1-dev`). No release has it: `v5.5.0`
(2026-09-18) still has the bug.

## Decision
- Pin the wrapper to master **`b19902d`** with a new key `ZED_WRAPPER_REF` (config/bisg.conf pins block: a tag or a SHA), so the wrapper
  no longer follows `ZED_SDK`. `scripts/fetch_sources.sh` clones and checks out the SHA on branch `local`; the superproject's
  submodule commit is the real pin.
- Keep **ZED SDK 5.4.1** (base images, Jetson L4T r38.4, Isaac extension v5.2.1 unchanged). The wrapper builds against SDK >= 4.2;
  its SDK 5.5 / `zed_msgs` 5.5 features (`pose_confidence`, `depth_precision`, `compute_preference`, ...) are compiled out or ignored.
- No local patches: `b19902d` is unmodified upstream.

## Consequences
- What changed between `v5.4.1` and `b19902d` that touches us: the sensors thread reads the IMU independently of `grab()` (v5.5.0;
  "SVO and simulation are unchanged"), `/pose/status` `status` now carries the tracking state (it was always 0), new optional params
  with defaults (`sdk_timestamp_clock`, `depth.publish_depth_image`, ...), the `urdf` folder moved to `zed_description` (already
  used by `v5.4.1`'s launch; `ros-jazzy-zed-description` comes from rosdep). zed.yaml is re-validated against the new YAML by
  `./bisg zed plan`.
- Re-validated 2026-10-21 on Workstation A: `./bisg smoke` PASS; `tests/vio_flight.py --alt 1.2 --side -1.0` PASS (max error 1.9 / 3.5 / 2.2 cm);
  `tests/zed_depth_box.py` (`single_iris_vio`) PASS, front face −22.9 mm (−26 mm on v5.4.1); `./bisg zed test` OK; no R9 with spatial mapping on.
- The Jetson image (`docker/zed/build.sh jetson`) must be rebuilt from the same commit.
- Back to a tag when Stereolabs releases one containing `cd8bf73` (v5.5.1+); moving to SDK 5.5 is a separate decision.
