# TODO

Live list only (history: `archive/docs/todo-history-2026-10.md`). Phases and exit tests: [roadmap.md](roadmap.md). Defects with causes: [bugs.md](bugs.md).

## Now — ZED stack ([zed-stack.md](zed-stack.md), ADR-008)
Built 2026-10-05: `docker/zed/zed.yaml` (every SDK module), `zed_stack` compiler + validator, `./bisg zed plan|set|up|services|enable|status|test`, services `zed` / `zed-bridge`
(health, odometry, obstacle_distance) / `zed-video`, same `docker/compose.yaml` (profile `drone`, `./bisg drone`) on the Jetson. Verified: 15 unit tests + bridge on fake topics (`./bisg zed test`), live in the sim with
the real SDK (wrapper 21-25 Hz, bridge all modules `ok`, PX4 receives `OBSTACLE_DISTANCE`, QGC video stream 113 frames / 5 s).
- [ ] **Apply `bisg/ros` rebuild** (GStreamer removed from its Dockerfile): `docker compose -f docker/compose.yaml build ros`
- [x] Every SDK module exercised in the sim and benchmarked (2026-10-05, `./bisg zed bench`, [zed-benchmark.md](zed-benchmark.md)): 16/16 pass; open: object/body detection **accuracy** (needs people/vehicle actors in the scene), ROI mask (needs the real robot in view), streaming crashes the wrapper in the sim (B19)
- [ ] Bridge CPU: `health` and `obstacle_distance` each deserialise every 720p depth frame in Python (0.31 cores for the container); share one depth subscription / decimate before the Orin NX bench
- [ ] Repeat `./bisg zed bench` on the Orin NX: RAM is the constraint (mapping +4 GB, detection +4 GB, body tracking +7 GB) and the base pipeline is 0.5 cores / ~half of the workstation GPU
- [ ] Obstacle avoidance closed loop: `tests/collision_prevention.py` still fails (QGC's virtual joystick wins PX4's manual-control selection; mavros stick values must be −1000…1000). Fix the test, then confirm the QGC proximity radar
- [x] Downward ToF (LW20/C) + optical flow (PMW3901) twin 2026-10-09: `sim/launcher/range_flow.py` -> PX4 `DISTANCE_SENSOR`/`HIL_OPTICAL_FLOW`, scenario `single_iris_flow`, [range-flow.md](range-flow.md); `vio_flight.py` square max err 0.10/0.175/0.087 m. Open: flow is analytic (no floor texture), real-hardware driver params on the Pixracer, a `tests/` entry that runs it in the regression, (done: per-hostname `ROS_DOMAIN_ID=auto`)
- [ ] Bridge modules not built: M11 MAVLink camera component (QGC finds the video itself), M5/M6 `FOLLOW_TARGET`/`LANDING_TARGET` from detections, M7 PX4 GPS → ZED GNSS. Plan: `archive/docs/zed-px4-bridge.md` §2. One module + one fake-topic test at a time
- [ ] QGC click-through of the video stream (Video source = UDP h.264) and the Jetson nvenc path: untested
- [ ] **B17 — SDK VIO accuracy in closed loop**: works end to end (EKF2 fuses the SDK odometry through the bridge, `vio_flight` flies and lands) but max error 0.37/0.53/0.34 m vs the 0.3 m bound; check the camera lever arm `EKF2_EV_POS_*`, restamp latency, intrinsics (`bugs.md` B17)
- [ ] B16 — contract TF frame prefix vs the wrapper's unprefixed frames; decide with the swarm phase
- [ ] B18 — the SDK connects once per sim run (never `zed up` twice against one sim run); retry on Isaac Sim 6.0.1
- [ ] Switch `GEN_3` IMU-fused tracking on for the bench (`positional_tracking.imu_fusion` is already true outside the `sim:` block)

## Now — GUI views (2026-10-07)
**ZED is SDK-only (2026-10-07):** removed the emulated rig (`zed_rig.py`, `zed_depth.py`, `drone_views.py`, `third_eye.py`), `ZED_SOURCE`, `./bisg vehicle` and the `vio_mock` compose service. Depth/point cloud/mapping/odometry come from the real SDK via `docker/zed/zed.yaml`. Not yet run in Isaac (py_compile / bash -n only). `docker/ros/ros2_ws/src/bisg_vehicle` (vio_mock) is still on disk, to delete by hand. GPS-denied scenarios now need `services.px4_bridge.odometry.enabled` in zed.yaml.
- [x] `./bisg up` now also starts the PX4 bridge (`PX4_BRIDGE`, MAVROS by default); `--no-bridge` skips it. Syntax-checked only, not run
- [ ] **Not yet run in Isaac** (py_compile only): `SIM_SCENARIO=single_iris ./bisg up gui`, check the window opens floating, chase pane renders, RTF with the chase camera on

## Now — PX4 bridge ([px4-bridge.md](px4-bridge.md))
Built 2026-10-05: **one compose service, `px4-bridge`** (a container per drone and bridge) (image `bisg/px4-bridge` = `bisg/ros` + MAVSDK server + uXRCE-DDS agent, entrypoint `docker/px4-bridge/entrypoint.sh`, env only, no `command:`); the variable `PX4_BRIDGE=mavros|mavsdk|xrce|none` in `config/bisg.conf` picks which bridge the entrypoint runs; `./bisg px4-bridge plan|up|down|status|logs|params|build`; `./bisg all` and `./bisg drone up` start it (sim and drone differ only by env: `BRIDGE_DEVICE`, `FCU_URL`).
- [x] Verified on a standalone PX4 v1.17 SITL: all three values start through the one entrypoint (MAVROS connected, MAVSDK listening and discovering PX4, the agent exposing 65 `/fmu` topics), `none` exits 0 and stays down, `./bisg mavros up|state|down`; 10 unit tests (`python3 -m unittest tests.unit.test_px4_bridge_cli`). Not re-run on the full Isaac stack (`./bisg all`) since the refactor
- [ ] Not yet run: the serial (`--hw`) path on a real Pixracer, `bisg/px4-bridge` built natively on arm64
- [x] Several drones and several methods at once: one container per drone and bridge (`bisg-<bridge>-N`, own compose project), `PX4_BRIDGE=mavros,xrce`, `--drone N`; tried with two PX4 instances running mavros + xrce each. Open: per-drone defaults (`PX4_BRIDGE_DRONE_N`) for the swarm phase; MAVSDK's gRPC port is one per host (two mavsdk bridges need different `MAVSDK_PORT`)
- [ ] Port the ZED bridge's output (odometry / obstacle map / health) to another bridge if MAVSDK or xrce ever becomes the default

## Now — host / hardware
- [x] Second workstation `ict-em018kc6` (2x RTX 6000 Ada, shared) set up 2026-10-06: images built, `./bisg smoke` + MAVROS pass headless. Not yet run there: `vio_flight`, `zed_depth_box`
- [x] Benchmarked vs the RTX 4500 box (`performance.md`, "Workstation B"): one sim is the same speed or ~10-15 % slower (CPU-thread bound); two sims, one per GPU, run 8 drones at rtf 0.67 vs 0.40 in one, all 8 flown. Phase 6 input: one sim per GPU, boots staggered
- [ ] Remote access from another network: compose service `tailscale` (Tailscale, ADR-009, `SIM_VIEW_ADDR=tailscale`) built 2026-10-06; plain `tailscaled` (containerboot's 60 s login deadline kept rotating the URL), browser login only via `./bisg tailscale login` (no auth keys). 2026-10-06: renamed `vpn` → `tailscale` everywhere (command, service, container, volume `bisg-tailscale_tailscale-state`, `TAILSCALE_HOSTNAME`/`TAILSCALE_EXTRA_ARGS`, `SIM_VIEW_ADDR=tailscale`; `vpn` now errors with the new name); `ict-em018kc6` logged in (100.88.233.117), state copied over, old volume `bisg-vpn_vpn-state` left in place. To do: verify WebRTC client + browser view from an off-site machine
- [ ] `SIM_VIEW_ADDR=192.168.192.200` and `ARCHIVE_DIR=/media/ubuntu/ssd/...` in `config/bisg.conf` are machine-specific: move each to the owning machine's `docker/.env`
- [x] QGC video without the SDK: `./bisg zed video [--video-host IP|tailnet-name]` starts only `zed-video` (emulated rig works); verified 2026-10-06 on `ict-em018kc6` with `ZED_RMW=rmw_fastrtps_cpp` (720p ~10 fps to a local QGC)
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

## Done 2026-10-07 — ZED all-modules test + GPU split (ict-em018kc6)
- [x] `./bisg zed bench`: 16/16 pass on 2x RTX 6000 Ada; all modules on at once also stable (docs/zed-benchmark.md). Not covered: global_localization (GNSS), streaming (B19); object/body accuracy needs people/vehicles in view.
- [x] GPU split: `SIM_GPU` / `ZED_GPU` (config/bisg.conf, machine values in docker/.env, `NVIDIA_VISIBLE_DEVICES` per compose service). Sim on GPU 0, wrapper on GPU 1 verified with nvidia-smi.
- [x] ZED_AUTOSTART / ROS_TOOLS_AUTOSTART (`docker/ros/tools.yaml`), `./bisg build`, `./bisg ros rviz|tools|start|stop`; bench starts its sim with both autostarts off.
- [ ] Not yet run after the autostart fix: a plain `./bisg all headless` that starts the wrapper + RViz by itself.

## Done 2026-10-07 — PX4 params reorganised
- [x] `config/px4/` -> `docker/sim/px4/` (image config lives in its folder; `config/` is bisg.conf only). `sim_default.params` -> `ekf2_vision.params`. One topic per file (README table).
- [x] Scenario key `px4.params: [a, b]` (bare name = docker/sim/px4/<name>.params, applied in order, later wins, overrides logged); `params_file` still read as the old key. `single_iris_vio` = `[ekf2_vision, collision_prevention]` (before, it dropped the obstacle params). `scripts/push_px4_params.py --file` is repeatable. Checked: loader applies both files, bad name gives a clear error. Not yet run through a sim boot.
