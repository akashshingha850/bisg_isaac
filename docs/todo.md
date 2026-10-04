# TODO

Live list only (history: `archive/docs/todo-history-2026-10.md`). Phases and exit tests: [roadmap.md](roadmap.md). Defects with causes: [bugs.md](bugs.md).

## Now — ZED stack ([zed-stack.md](zed-stack.md), ADR-008)
Built 2026-10-05: `docker/zed/zed.yaml` (every SDK module), `zed_stack` compiler + validator, `./bisg zed plan|set|up|services|enable|status|test`, services `zed` / `zed-bridge`
(health, odometry, obstacle_distance) / `zed-video`, same `docker/compose.yaml` (profile `drone`, `./bisg drone`) on the Jetson. Verified: 15 unit tests + bridge on fake topics (`./bisg zed test`), live in the sim with
the real SDK (wrapper 21-25 Hz, bridge all modules `ok`, PX4 receives `OBSTACLE_DISTANCE`, QGC video stream 113 frames / 5 s).
- [ ] **Apply `bisg/ros` rebuild** (GStreamer removed from its Dockerfile): `docker compose -f docker/compose.yaml build ros`
- [ ] Exercise the SDK modules nobody has switched on yet (`./bisg zed set …` + `./bisg zed check`): disparity, confidence, ROI, spatial mapping, plane detection, object + body detection (needs people/vehicle actors in the scene) — `docs/zed-stack.md` marks each "not exercised"
- [ ] Obstacle avoidance closed loop: `tests/collision_prevention.py` still fails (QGC's virtual joystick wins PX4's manual-control selection; mavros stick values must be −1000…1000). Fix the test, then confirm the QGC proximity radar
- [ ] Bridge modules not built: M3 `DISTANCE_SENSOR` (height over ground), M11 MAVLink camera component (QGC finds the video itself), M5/M6 `FOLLOW_TARGET`/`LANDING_TARGET` from detections, M7 PX4 GPS → ZED GNSS. Plan: `archive/docs/zed-px4-bridge.md` §2. One module + one fake-topic test at a time
- [ ] QGC click-through of the video stream (Video source = UDP h.264) and the Jetson nvenc path: untested
- [ ] **B17 — SDK VIO accuracy in closed loop**: works end to end (EKF2 fuses the SDK odometry through the bridge, `vio_flight` flies and lands) but max error 0.37/0.53/0.34 m vs the 0.3 m bound; check the camera lever arm `EKF2_EV_POS_*`, restamp latency, intrinsics (`bugs.md` B17)
- [ ] B16 — contract TF frame prefix vs the wrapper's unprefixed frames; decide with the swarm phase
- [ ] B18 — the SDK connects once per sim run (never `zed up` twice against one sim run); retry on Isaac Sim 6.0.1
- [ ] Switch `GEN_3` IMU-fused tracking on for the bench (`positional_tracking.imu_fusion` is already true outside the `sim:` block)

## Now — host / hardware
- [ ] **Host (needs sudo): `net.core.rmem_max`** — until set, HD720 ZED images/depth/clouds do not cross containers over CycloneDDS (`docs/setup.md`); `ZED_RMW=rmw_fastrtps_cpp` is the no-sudo fallback
- [ ] Remaining answers → `hardware.md`: Orin NX RAM variant, exact L4T/CUDA (`cat /etc/nv_tegra_release`), frame/motor/battery, Pixracer firmware, deployment site
- [ ] **Bench day (Orin NX + Pixracer + ZED Mini)**: `docker/zed/build.sh jetson`; `python3 tests/zed_sdk_check.py --drone 1 --no-gt`; record the unit's real `K` in `hardware.md`; trajectory vs tape measure; MAVROS lean idle CPU / command RTT with the ZED wrapper running (gate for MAVSDK in `archive/px4-link-study/study-px4-link.md` §7); `uxrce_dds_client` RAM only if DDS is revisited
- [ ] Offboard-loss / RC-loss failsafe for GPS-denied flight (Land/Hold are unusable there, `bugs.md` B1): pick and prove one in SITL before any real VIO flight
- [ ] Manual: real QGroundControl session, real WebRTC client, `vehicle reset` (no launcher hook yet)

## Next — Isaac Sim 6.0 follow-ups (`docs/migration-errors.md`)
- [ ] Pegasus per-step cost (M8): sim runs 0.3-0.5x real time (0.85 headless with `pegasus_fast.py`); batch force/torque + propeller visuals on the submodule `local` branch; gate with smoke + `vio_flight` + `zed_depth_box`
- [ ] Decide what `headless_fast` means now (M9) and redo `docs/performance.md` on 6.0
- [ ] Push `isaac-5.1-baseline` and `migrate/isaac-6.0` (your call), merge, then mirror Pegasus PR #144 to a fork or tag (M18)
- [ ] Port the sensors off deprecated APIs (`isaacsim.sensors.camera`, `isaacsim.core.utils`, ros2 bridge shim) before Isaac Sim 6.1 (M12)
- [ ] Re-test whether the NVIDIA 59x driver crash exists on 6.0 (keep the `check_env.sh` guard until then)
- [ ] Isaac ROS 4.6: not in `plan.md`; needs its own plan first

## Later — phases ([roadmap.md](roadmap.md))
- Phase 2: `bisg_msgs`, `bisg_vehicle/offboard_controller`, `mission_square`; `tests/check_contract.py`; rebuild `bisg/ros:arm64` (entrypoint changed)
- Phase 4 assets: measure the real quad → `sim/assets/vehicles/bisg_quad` USD + Pegasus preset + thrust curve; site capture (3DGS/NuRec vs mesh) → `sim/worlds/<site>`; scenario YAMLs (`hover_check`, `square`, `survey_strip`, `inspect_structure`)
- Phase 5 hardware: L4T/CUDA record, arm64 image pulls, udev `/dev/px4`, Pixracer flash + params, `real_drone.launch.py`, bench checklist → feed numbers back to the vehicle model
- Phase 6 swarm in sim: `vehicles:` list (works for 2/4/8 in `docker/sim/configs`), `scripts/gen_compose.py`, `bisg_fleet`, VRAM budget table. Phases 7-8: hardware swarm (zenoh/DDS plan, kill switch), scenario runner + CI

## Parked
ArduPilot backend · Isaac Lab / RL for swarm policies · per-drone lidar if one is ever mounted · ZED `Sim2Real` post-process (`applyZedSim2Real`) to narrow the render-vs-camera gap
