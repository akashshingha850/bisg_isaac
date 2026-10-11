---
name: zed-contract
description: Add, rename or verify a sensor topic/frame in the vehicle interface contract; make the Isaac camera rig match the ZED ROS 2 wrapper; run the contract checker. Use for any change to topics, TF frames, camera_info, or when comparing sim vs real ZED output.
---

# zed-contract

## Rule
`docs/interface-contract.md` changes **first**, then sim publisher, then real launch, then `tests/check_contract.py` must pass on both.

## Procedure for a new/renamed topic
1. Edit the contract table (topic, type, rate, sim source, real source, notes).
2. Sim: the ZED topics come from the real wrapper on the streamed twin, so a ZED topic changes in `docker/zed/zed.yaml`; a sim-only topic
   (chase cam, ground truth) changes in its `docker/sim/launcher/` module and the scenario YAML.
3. Real: confirm the zed-ros2-wrapper name/param that produces it (wrapper `common.yaml` / `zed*.yaml`); add a relay only if names cannot be made equal by remap.
4. Update the ZED model table in `docs/hardware.md` if intrinsics/rates change.
5. Run `python3 tests/check_contract.py --ns /drone_1` against sim (and real when available).

## Matching the ZED wrapper
- Topic root `zed/zed_node/…` under `/drone_<n>/`; images are `left|right/color/rect/image` + `…/camera_info` (wrapper 5.4.1; the old `image_rect_color` names are gone, B14 fixed 2026-10-03); depth `32FC1` metres.
- One source in sim and on the drone: the real wrapper launched by `docker/zed/zed_drone.launch.py` (the emulated rig was removed
  2026-10-07). `tests/check_contract.py` reads the contract's topic table itself; `tests/zed_sdk_check.py` checks the ZED in depth.
- `K` is the camera's own: never assert the hard-coded model-table `K` in sim `sdk` (extension lens, HD720 `fx` 529.8) or on a real unit; baseline `-P[0,3]/P[0,0]` = 0.063.
- TF (R3, 2026-10-10): the wrapper's base frame is hard-wired to `zed_camera_link` and it publishes `odom → zed_camera_link`;
  `zed_drone.launch.py` adds static `zed_camera_link → base_link` (inverse of `positional_tracking.initial_base_pose` = the mount)
  and `map → odom`. Optical frames are `zed_left_camera_frame_optical` (wrapper 5.4 names), REP-103 optical (z forward).
- `camera_info` K from the ZED model table; Isaac camera focal/aperture set so that K matches at the chosen resolution.
- Stereo baseline = 0.063 m (ZED Mini); both cameras rigid on `zed_camera_link`; wrapper `camera_model: zedm`.
- IMU on `zed_imu_link` at 200 Hz.


## VIO source
- The wrapper's positional tracking (sim: visual-only, `imu_fusion: false`; real: IMU-fused) publishes `zed/zed_node/odom`;
  the `zed-bridge` odometry module relays it to `mavros/odometry/out` (`services.px4_bridge.odometry` in zed.yaml; off in the
  sim by default, closed loop accuracy B17).
- Any node other than tests that subscribes to Pegasus ground truth violates parity rule 2 (plan.md §8).
