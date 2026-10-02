---
name: zed-contract
description: Add, rename or verify a sensor topic/frame in the vehicle interface contract; make the Isaac camera rig match the ZED ROS 2 wrapper; run the contract checker. Use for any change to topics, TF frames, camera_info, or when comparing sim vs real ZED output.
---

# zed-contract

## Rule
`docs/interface-contract.md` changes **first**, then sim publisher, then real launch, then `tests/check_contract.py` must pass on both.

## Procedure for a new/renamed topic
1. Edit the contract table (topic, type, rate, sim source, real source, notes).
2. Sim: update the Isaac rig config (`sim/configs/*.yaml` → `sensors.zed`) or the publisher node in `sim/nodes/`.
3. Real: confirm the zed-ros2-wrapper name/param that produces it (wrapper `common.yaml` / `zed*.yaml`); add a relay only if names cannot be made equal by remap.
4. Update the ZED model table in `docs/hardware.md` if intrinsics/rates change.
5. Run `python3 tests/check_contract.py --ns /drone_1` against sim (and real when available).

## Matching the ZED wrapper
- Topic root `zed/zed_node/…`; image encodings per wrapper; depth `32FC1` metres.
- TF: `zed_camera_link → zed_left_camera_frame → zed_left_camera_optical_frame` (+ right, + `zed_imu_link`). Optical frames are REP-103 optical (z forward).
- `camera_info` K from the ZED model table; Isaac camera focal/aperture set so that K matches at the chosen resolution.
- Stereo baseline = 0.063 m (ZED Mini); both cameras rigid on `zed_camera_link`; wrapper `camera_model: zedm`.
- IMU on `zed_imu_link` at 200 Hz.

## Isaac Sim 6.0 rig notes (`sim/launcher/zed_rig.py`)
- `read_camera_info` is `isaacsim.ros2.core.impl.camera_info_utils` (was `isaacsim.ros2.bridge`); OmniGraph node/writer names are unchanged (`isaacsim.ros2.bridge.ROS2Publish*`).
- IMU is `isaacsim.sensors.experimental.physics.IMU` + `IMUSensor` (the old `isaacsim.sensors.physics` ext does not load under the python kit). It has no `frequency`: it samples every physics step, and the graph publishes on `OnPhysicsStep`.
- Still on deprecated APIs that import fine in 6.0: `isaacsim.sensors.camera.Camera`, `isaacsim.core.utils.{stage,prims}`. Port them before a 6.1 step.
- Publish rate: every image/depth/camera_info writer has its own `…IsaacSimulationGate`; the rig sets all of them to `round(1/(render_dt*fps))` rendered frames (30 Hz sim at the default 1/60 s loop). Verify in **sim** time: `wall_hz / (clock_hz / 250)`.
- Verified on 6.0: topic set and names identical to 5.1; K = 177.7 px @ 320 wide (84° HFOV); depth `32FC1`, colour `rgb8`; static TF has 6 frames.

## VIO source
- Sim: `vio_mock` (ground truth + noise + latency) publishes `zed/zed_node/odom` AND relays to `mavros/odometry/out`.
- Real: wrapper publishes `odom`; `vio_relay` re-parents child frame to `base_link` and republishes to `mavros/odometry/out`.
- Any node other than these two that subscribes to Pegasus ground truth violates parity rule 2 (plan.md §8).
