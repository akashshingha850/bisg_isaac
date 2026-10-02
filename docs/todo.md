# TODO

Live checklist. Move items to **Done** with a date; keep **Now** short (≤ 10 items).
Phase definitions and exit tests are in [roadmap.md](roadmap.md).
Known defects, with causes and candidate fixes, are in [bugs.md](bugs.md).

## Now — Phase 0: Foundations

- [x] Write plan / roadmap / todo / skills / contract / hardware / ADRs (2026-09-12)
- [x] Open questions answered (2026-09-12): Jetson Orin NX + JetPack 7.2, ZED Mini, swarm after the single-drone twin, PX4 newest Pegasus-compatible → ADR-003/005, `hardware.md`
- [ ] Remaining answers → `hardware.md`: Orin NX RAM variant, exact L4T/CUDA (`cat /etc/nv_tegra_release`), frame/motor/battery, current Pixracer firmware, deployment site
- [ ] `git init`, first commit — **user does this once the foundation runs** (build + smoke test green)
- [x] Skeleton dirs created with READMEs (2026-09-12)
- [ ] `scripts/fetch_third_party.sh` (Pegasus v5.1.0 + zed-ros2-wrapper v5.4.1 clones; PX4 optional) → submodules after `git init`
- [x] NGC access: `nvcr.io/nvidia/isaac-sim:5.1.0` manifest is public, no login needed (2026-09-12); `scripts/pull_images.sh --save` archives it (risk R7)
- [x] Isaac Sim 5.1 internal Jazzy bridge confirmed (`exts/isaacsim.ros2.bridge/jazzy`, Cyclone rmw bundled); selected via `ROS_DISTRO` + `LD_LIBRARY_PATH` in the image (2026-09-12)
- [x] Config layer: `config/*.conf` split by topic + `config/README.md`, `docker/.env` slimmed to per-machine values, `./bisg config` with provenance, `docs/configuration.md` (2026-09-13). **Merged 2026-09-21**: one `config/bisg.conf` (six numbered files were more filing than ~25 keys deserved), and `SIM_MODE` + `SIM_STREAM` collapsed into one `SIM_VIEW=gui|headless|web|webrtc|both|auto` (combine with `+`, e.g. `gui+webrtc`). `SIM_STREAM_ADDR` → `SIM_VIEW_ADDR`. Old keys in a config file or `docker/.env` now abort with a migration hint instead of being silently ignored; container env (`SIM_HEADLESS`, `SIM_STREAM`) is unchanged and derived by `./bisg`
- [x] Views for headless runs (`docs/remote-access.md`): `SIM_STREAM=off|web|webrtc|both`, `./bisg up --web|--stream|--both`, `./bisg view`; WebRTC enables `omni.services.livestream.nvcf` (TCP 49100 + UDP 47998), `web` serves captured frames on `SIM_WEB_PORT` so a VS Code/SSH tunnel can reach it (2026-09-13). **Verified live 2026-09-13**: `web` serves 1280x720 PNGs that update (page/frame/freshness checked over HTTP, TCP 8899 listening); `webrtc` reports ready with TCP 49100 listening (UDP 47998 opens on client negotiation — an actual client connection is still unverified, needs the NVIDIA app); smoke test passes with both views on
- [ ] Review the 7 Claude Code skill stubs in `.claude/skills/`; delete or merge any that feel redundant

## Done — Isaac Sim 5.1 → 6.0 migration — 2026-10-02

Report: [migration-report.md](migration-report.md) · every error: [migration-errors.md](migration-errors.md) · plan followed: [migrate.md](migrate.md).
Branch `migrate/isaac-6.0` (nothing pushed), rollback tag `isaac-5.1-baseline`. Isaac Sim 6.0.0 + Pegasus PR #144 + PX4 v1.17.0 (kept; 1.16.0 also validated).
Smoke, VIO flight (≤ 0.07 m) and depth box pass and match the 5.1 baseline; 2/4/8 drones boot and fly; `web` view works, WebRTC server starts.

Follow-ups (open):
- [ ] **Pegasus per-step cost (M8)**: sim runs 0.33× real time (was 1.18×). Batch the force/torque calls and the propeller visuals on the submodule `local` branch; gate with smoke + `vio_flight` + `zed_depth_box`
- [ ] Decide what `headless_fast` means now (M9: `app.render: false` is no longer physics-only, rtf 0.53 vs 1.27); redo `docs/performance.md` on 6.0
- [ ] Push `isaac-5.1-baseline` and `migrate/isaac-6.0` (your call), merge, then mirror Pegasus PR #144 to a fork or tag (M18)
- [ ] Finish the sensor port off deprecated APIs (`isaacsim.sensors.camera`, `isaacsim.core.utils`, `isaacsim.ros2.bridge` shim) before looking at Isaac Sim 6.1 (M12)
- [ ] Manual: real QGroundControl session, real WebRTC client, native `gui` window, `vehicle reset`, GPS-scenario position hold; run the ZED rig with 2 drones (unique topics / TF)
- [ ] Re-test whether the NVIDIA 59x driver crash still exists on Isaac Sim 6.0 (keep the guard in `scripts/check_env.sh` until then)
- [ ] Isaac ROS 4.6 integration: not in `plan.md` — needs its own plan before any work (`migrate.md` §38)
- [ ] Box colour (M10) and the `CMODE(...)` string for a late-started MAVROS (M11): cosmetic

## Done — workstation OS migration 22.04 → 24.04 (plan.md §12) — 2026-09-21/22

Done via a new PC, not an in-place upgrade, so no images/volumes carried over — rebuilt from
source instead. Skipped the "before" steps below for that reason (nothing to save from a machine
this session has no access to); everything else ran for real on the new host:
- [x] Before steps N/A (new physical machine, not a reinstall of the old one — no `docker save`/volume export to do)
- [x] Before: confirmed no script depends on host ROS Humble or 22.04-only packages — new host has no `/opt/ros` at all and setup/build/smoke all passed clean
- [x] After: host preflight — `nvidia-container-toolkit` installed fresh, `nvidia-ctk runtime configure --runtime=docker`, `docker-compose-v2` installed (Ubuntu's `docker.io` doesn't bundle it), `bisg` added to `docker` group, `docker run --gpus all ... nvidia-smi` passed
- [x] After: **driver gotcha found and fixed** — new PC shipped with NVIDIA driver 595.91.07 (R590 branch), confirmed 100%-reproducible crash: Isaac Sim 5.1 segfaults in `librtx.scenedb.plugin.so` ~0ms after `app ready` (known upstream bug, isaac-sim/IsaacSim#648/#619/#651/#537 — driver too new, not an Ada-support issue). Fixed by downgrading to **580.178.04** (same branch the old PC used). `scripts/check_env.sh` now hard-fails on any 59x driver so this can't silently regress
- [x] After: display server — still X11 (`DISPLAY=:0`), `xhost +local:` works; GUI profile not re-verified this round (headless only)
- [x] After: native host ROS 2 — skipped (optional); host intentionally has no ROS install
- [x] After: `docs/plan.md` §12 rewritten with what actually happened; `CLAUDE.md` Host facts updated; `config/bisg.conf` `ARCHIVE_DIR` comment + `docker/.env` override added for `/opt` (no `/media/ubuntu/ssd` on this box)
- [x] After: fresh build — `./bisg setup --third-party` pulled `nvcr.io/nvidia/isaac-sim:5.1.0` + `ros:jazzy-ros-base`, built `bisg/sim:5.1.0` and `bisg/ros:jazzy` clean; `third_party/PegasusSimulator` (v5.1.0) and `third_party/zed-ros2-wrapper` (v5.4.1) converted to real git submodules (repo has been `git init`'d since the last time these were plain clones) — staged, not yet committed
- [x] After: re-ran Phase 1 headless smoke test — `[launch] sim ready` 143s, PX4 ready 146s, `./bisg smoke` **PASS** (arm → 1.6 m → land → disarm); MAVROS `connected: true` on `/drone_1`; `./bisg down` clean in ~10s, no stray containers

## Next — Phase 1: Dockerized single-drone sim

- [x] `scripts/check_env.sh` — passes on this host (2026-09-12)
- [x] `docker/sim.Dockerfile` (Isaac 5.1.0 base = Ubuntu 24.04 non-root `isaac-sim`; PX4 v1.17.0 SITL built in-image, Pegasus v5.1.0 pip-installed, Jazzy bridge + Cyclone ENV, named cache volumes owned by the image user) (2026-09-12)
- [x] `docker/compose.yaml` profiles `sim`, `sim-headless`, `ros`, `tools`; `network_mode: host`; `runtime: nvidia` (2026-09-12)
- [x] PX4 tag selected: v1.17.0 (airframe + fmu-v4 board verified in the tree) — ADR-003 step 1–2 (SITL flight, fmu-v4 build) still pending
- [x] `sim/launcher/launch.py` + `sim/configs/single_iris.yaml` (written, not yet run) (2026-09-12)
- [x] Port math verified against Pegasus v5.1.0 `px4_mavlink_backend.py` (4560+id) and PX4 v1.17.0 `px4-rc.mavlink` (14540+i / 14580+i, MAV_SYS_ID i+1) (2026-09-12)
- [x] `tests/smoke_takeoff.py`, `docs/runbook-sim.md`, `sim-launch` skill updated (2026-09-12)
- [x] Operator CLI `./bisg` + `scripts/setup.sh`, `launch.sh`, `debug.sh`; `docs/setup.md`, `docs/debugging.md` (2026-09-12). Verified live: `up/wait/status/smoke/mavros up+state/debug px4|topics|hz|mavlink|report|versions|dds/restart/down`
- [x] Images built: `bisg/sim:5.1.0` (~4 min build after the pull), `bisg/ros:jazzy` 1.7 GB (2026-09-12)
- [x] First headless run: `[launch] sim ready` at ~5 min cold (asset download), PX4 "Ready for takeoff" (2026-09-12)
- [x] `tests/smoke_takeoff.py` PASS twice: arm → 2 m → land → disarm (2026-09-12)
- [x] Clean shutdown: entrypoint execs Isaac python as PID 1 → SIGTERM handled, `compose stop` 1.4 s, exit 0, no stray PX4 (2026-09-12)
- [x] Boot-time/perf knobs exposed: `perf:` block in scenario YAML (viewport updates, CPU threads, resolution, renderer, `skipMaterialLoading`, PhysX threads/minFrameRate, raw Kit args), `world.physics_dt/rendering_dt/physics_device`, RTF heartbeat, `./bisg debug perf`, `sim/configs/headless_fast.yaml`, `docs/performance.md` (2026-09-12)
- [x] Measured and filled `docs/performance.md`: `headless_fast` 186 s boot, 317 steps/s, **rtf 1.27**; warehouse headless 189 s, 186 steps/s, rtf 0.74; warehouse + both views 117 steps/s, rtf 0.47 (2026-09-13)
- [x] **Render cadence bug fixed** (2026-09-13): the launcher rendered on every physics step instead of honouring `rendering_dt`, costing ~4x sim speed — warehouse headless went 79 → 186 steps/s (rtf 0.32 → 0.74), with a view 29 → 117 (rtf 0.12 → 0.47). `[launch] render cadence:` line reports it at startup
- [x] `tests/smoke_takeoff.py` now requires a real autopilot heartbeat, so "no PX4" fails in seconds with a clear message instead of latching onto a stray sysid 0 packet (2026-09-12)
- [x] Host driver mismatch cleared by the reboot (2026-09-13): kernel 6.8.0-138, module and userspace both 580.178.04, `./bisg check` all green. `./bisg up` now preflights the GPU and prints both fixes (reboot / module reload) instead of a raw OCI error
- [x] GUI profile: Isaac window appears on `:0` via X11 (`xhost +local:`) (2026-09-12)
- [ ] Manual: QGroundControl on the host connects on 14550; takeoff/land from QGC in the GUI profile
- [ ] Raise MAVROS stream rates (`MAV_1_RATE`/`set_message_interval`) — Phase 2, interface-contract rates
- [x] ADR-003 accepted: `px4_fmu-v4_default` at v1.17.0 links, flash 95.3 % (2026-09-12)
- [x] MAVROS 2.15.1 (Jazzy) connected to SITL via CycloneDDS: `/drone_1/mavros/state connected: true`, pose 14 Hz, IMU 24 Hz (2026-09-12). Fixed: empty `gcs_url:=` arg; Cyclone `SocketReceiveBufferSize min` on small `rmem_max`

## Later — Phase 2+

Phase 2 — ROS 2 + MAVROS
- [x] `docker/ros.Dockerfile` (Jazzy, MAVROS 2.15.1, geographiclib datasets, CycloneDDS) + `mavros` compose service with port derivation from `DRONE_ID` (2026-09-12)
- [x] `bisg/ros:arm64` cross-built under qemu (`docker buildx build --platform linux/arm64 -f docker/ros.Dockerfile -t bisg/ros:arm64 --load .`, ~15 min); MAVROS + geoid verified inside (2026-09-12)
- [ ] `bisg_msgs`, `bisg_vehicle/offboard_controller` (+ Python API), `mission_square`
- [ ] MAVROS launch wrapper: `ns`, `fcu_url`, `tgt_system` from drone id
- [x] `/clock` + `use_sim_time` verified in MAVROS and our nodes (2026-09-25): launcher publishes `/clock` every physics step; MAVROS plugin nodes need a runtime param set (`docker/ros/mavros_sim_time.py`) — see Phase 3
- [ ] Cross-container topic smoke test (Isaac Jazzy bridge → ros container)

Phase 3 — Sensors, ZED Mini contract, VIO
- [x] Stereo (63 mm) + depth + IMU rig under ZED names; TF tree; camera_info (2026-09-21): `sim/launcher/zed_rig.py`,
  wired from `sim/configs/*.yaml` `sensors.zed`. Verified live: `/drone_1/zed/zed_node/{left,right}/image_rect_color`
  (rgb8), `.../depth/depth_registered` (32FC1), `.../{left,right}/camera_info`, `.../imu/data` all publishing
  real data (IMU rate fixed 2026-09-25, image delivery needs the host sysctl — see below); static TF `drone_1/base_link ->
  zed_camera_link -> {left,right}_camera_frame -> optical` + `zed_imu_link` on `/drone_1/tf_static`.
  Camera intrinsics are a placeholder pinhole model (84° HFOV, HD720) — replace with factory K once the real
  unit is measured (`docs/hardware.md` ZED Mini model table still has mount pose/K as TBD).
  **2026-09-25: the footage was unusable until now and nobody had looked at it.** Three rig bugs: the lens sat
  inside the Iris nose (mount x 0.10, body ends at 0.156) and saw only fuselage; the pose quaternion was passed
  in scipy (x,y,z,w) order to an API that wants (w,x,y,z), with a 180° yaw hack cancelling it; the focal length
  never reached the camera (camera_info fx 1527 @640 px = 24° HFOV). Fixed: mount x 0.18, `_quat_wxyz()`, USD
  focalLength/aperture. Checked frames on the ground, hovering and banked ~20° mid-square: clear forward view,
  no airframe/props/legs, 0 depth pixels < 0.5 m in flight, stereo parallax sign correct. `tests/vio_flight.py`
  still PASS (0.056 m). Captured at 480x270 — HD720 frames still need the host sysctl (bugs.md B2).
- [x] ZED depth checked in flight + GUI depth view (2026-09-26). Recorded flight (`logs/flight_20260926_vio/`:
  rosbags left/right/depth/state + `analysis/depth_per_frame.csv`): 1054 airborne depth frames, none with a pixel
  < 0.5 m at up to ±21° roll/pitch; floor rows at hover fit a camera pitch of −0.1..−0.2° vs truth +0.1°
  (depth metric + rig level); 32FC1 metres, left optical frame, +inf beyond 15 m, no NaN. GUI: scenario
  `sensors.zed.preview` opens a "ZED Mini /drone_N - left | depth" window (`sim/launcher/zed_preview.py`,
  reads the render products directly, so HD720 works without DDS).
- [x] ZED point cloud + depth test box (2026-09-26). `sim/launcher/zed_pointcloud.py` (now `zed_depth.py`): contract topic
  `zed/zed_node/point_cloud/cloud_registered` (organized 320x180, x y z rgb, `zed_left_camera_frame`, sim time,
  published only while subscribed) + live points over the GUI viewport (omni.ui.scene overlay — not
  debug_draw, which rendered the dots into the ZED camera images). Scenario `world.objects` (launcher
  `spawn_objects`): `single_iris_vio` has a 1 m orange `depth_box` at x=4. `tests/zed_depth_box.py` checks the
  cloud against it: parked front face −0.1 mm, width 1.000 m; hovering (`--min-alt 1.9`) front +0.2 mm, top
  +6.5 mm (pose/cloud pairing while climbing) — PASS. Floor from the hover cloud 1.98 m below the lens (2.04
  expected). GUI view aimed at the drone (`app.viewport_eye/target`), ZED window docked in the bottom panel.
- [x] ZED SDK feature switches (2026-09-26): `deploy/jetson/zed_params.yaml` now lists every wrapper feature with its
  switch (video, sensors, depth, ROI, pos tracking, GNSS, mapping, OD, body tracking, streaming) and is read by the
  sim too (`sim/launcher/zed_features.py`; scenario `sensors.zed.features` overrides; "NOT simulated" warning).
  Sim emulates images, IMU, depth, point cloud, disparity (verified f·T/d = depth) and spatial mapping
  (`mapping/fused_cloud` + GUI overlay; box face voxel 3.525 vs 3.500, 0% below floor after pairing each depth
  frame with the camera pose at its render time — pairing with the current pose had smeared 11% of the map).
  Reference table: `docs/zed-features.md`. Disabling switches in sim only checked in code, not boot-tested.
- [x] `vio_mock` → `mavros/odometry/out` (2026-09-21): `ros2_ws/src/bisg_vehicle` (new package), reads Pegasus
  ground-truth `state/pose`/`state/twist` (ROS2Backend `pub_state`, parity rule plan.md §8), adds Gaussian
  position noise + 30 ms latency, publishes `zed/zed_node/odom` (sensor QoS, `drone_1/`-prefixed frames per
  contract) and `mavros/odometry/out` (reliable QoS, **unprefixed** `odom`/`base_link` frames — MAVROS's odom
  plugin only recognises its own `fcu.odom_parent_id_des`/`odom_child_id_des` literal strings, `px4_config.yaml`;
  the contract-prefixed names silently broke horizontal position/velocity fusion until this was found and split
  into two differently-framed messages) + dynamic TF `drone_1/odom -> drone_1/base_link`. Pose covariance is now
  populated (was all-zero, a distinct bug from the frame-name one). `./bisg vehicle up|down|logs|restart`; wired
  into `./bisg all`. Verified live: MAVROS receiving at ~113 Hz, sub-ms clock sync confirmed via
  `mavros/time_reference`. Simplification: `odom` == `map` (no drift model) — documented in the node's docstring.
- [x] EV params file + push mechanism (2026-09-21): `deploy/px4_params/sim_default.params` +
  `scripts/push_px4_params.py` (MAVLink `PARAM_SET`, same offboard link as `tests/smoke_takeoff.py`; PX4 has no
  boot-time params-file hook, so this runs post-boot). Values read directly from the pinned firmware source
  (`/opt/PX4-Autopilot/src/modules/ekf2/{module,params_external_vision,params_gnss,params_magnetometer}.yaml`
  inside the sim container), not guessed: `EKF2_HGT_REF=3`(Vision) `EKF2_EV_CTRL=15`(pos+vel+yaw)
  `EKF2_EV_DELAY=30` `EKF2_GPS_CTRL=0` `EKF2_MAG_TYPE=5`(None). `EKF2_HGT_REF`/`EKF2_MAG_TYPE` are
  `reboot_required`. **Corrected 2026-09-25**: SITL refuses the reboot (COMMAND_ACK DENIED) and Pegasus runs PX4
  from a fresh temp dir, so pushed params never took full effect — EKF2 kept its GPS-anchored origin and yaw
  alignment, which is why it "armed and accepted takeoff". Now applied at boot instead (launcher
  `px4.params_file` → `PX4_PARAM_*` env, scenario `single_iris_vio`); `EKF2_EV_DELAY` 30 → 0 (samples are
  stamped at capture time, EKF2 subtracts the delay again).
- [x] **GPS-denied flight works in sim** (2026-09-25) — the 2026-09-21 height runaway is root-caused and fixed.
  `tests/vio_flight.py` (Phase 3 exit test: OFFBOARD takeoff, hover, 3 m square, land) PASS, max |estimate −
  ground truth| x 0.059 / y 0.076 / z 0.028 m (bound 0.3 m). Causes, all fixed:
  1. **Two clocks.** PX4 SITL runs on sim time (Pegasus stamps HIL_SENSOR; PX4 sets its clock from it) while
     Pegasus's `state/pose`, vio_mock and MAVROS stamped wall time. The offset drifts at (1 − rtf) s/s, so PX4
     timesync never converged: EV samples were stamped on arrival, or with a stale offset once it briefly
     "converged", and mistimed vision height in a climb diverged. Fix: `/clock` from the launcher's physics
     callback; `use_sim_time` on vio_mock and MAVROS (compose `USE_SIM_TIME=true`, Jetson default false);
     vio_mock stamps with its own clock. MAVROS 2.15.1 plugin nodes ignore `-p` and `--params-file`
     (`use_global_arguments(false)`), so `docker/ros/mavros_sim_time.py` sets it at runtime. Verified: observed
     offset constant (−8 ms), EV `timestamp_sample` 27–32 ms before arrival = the mock latency.
  2. **Params never applied** (see EV params item above) — the stale GPS origin also put local z at −90 m.
  3. **No global position GPS-denied**: MAVROS sends EV as `LOCAL_FRD`, EKF2 never yaw-aligns → Hold (boot
     mode) refuses to arm; AUTO.LAND engages but flew toward lat/lon 0,0 at ~6 m/s into a wall. Fly and land in
     OFFBOARD; landing needs a descent *velocity* setpoint (land detector). Setting a global origin does not
     help (tried, reverted).
- [ ] Offboard-loss / RC-loss failsafe action for GPS-denied flight (`docs/hardware.md`): Land/Hold are unusable
  (item above). Pick and prove one in SITL (Descend?) before any real VIO flight.
- [ ] **Host action (needs sudo): `net.core.rmem_max`** — at the Ubuntu default 208 KB no HD720 ZED image or
  depth frame is delivered (0 of them; 320x180 flows fine, so it is size, not the rig). `docs/setup.md` has the
  sysctl; Cyclone now requests 16 MB. Re-measure image rates after.
- [ ] Launcher RTF metric under-reports: `/clock` advances ~1.15x wall while `[launch] perf ... rtf=0.65`
  (render frames step physics more than once per loop iteration). `docs/performance.md` numbers need a redo.
- [ ] Rebuild `bisg/ros:arm64` — `docker/ros/entrypoint.sh` changed (MAVROS now `ros2 run mavros_node` with the
  same param files as `px4.launch`; hardware path unchanged otherwise, `USE_SIM_TIME` defaults to false)
- [ ] `tests/check_contract.py` — not written; `./bisg debug echo|hz` used for manual verification above

Phase 4 — Digital-twin assets and models
- [ ] Measure the real quad (hardware.md → "Vehicle model measurements"); build `sim/assets/vehicles/bisg_quad` USD + Pegasus preset + thrust curve
- [ ] Choose site capture route (3DGS/NuRec vs mesh); build `sim/worlds/<site>` with collision proxies; geo-reference; scale check
- [ ] Single-drone scenario YAMLs (`hover_check`, `square`, `survey_strip`, `inspect_structure`)

Phase 5 — Hardware single drone (Orin NX, JetPack 7.2, ZED Mini)
- [x] ZED SDK pinned 5.4.1; `docker/zed/build.sh` (Stereolabs scripts, desktop + l4t-r38 targets); `deploy/jetson/compose.yaml` skeleton with `mavros` (serial) + `zed` services and `zed_params.yaml` overlay (2026-09-12)
- [ ] Record L4T/CUDA on the device (`cat /etc/nv_tegra_release`); confirm `l4t-r38.4` matches JetPack 7.2; build `bisg/zed:l4t-r38` on the Jetson
- [ ] arm64 image pulls, `deploy/jetson/compose.yaml`, udev `/dev/px4`, Pixracer flash + params, `real_drone.launch.py`, `vio_relay`, bench checklist
- [ ] Feed bench numbers back into the Phase 4 vehicle model

Phase 6 — Swarm in sim (migration)
- [ ] `vehicles:` list in launcher; `scripts/gen_compose.py`; `bisg_fleet`; VRAM budget table

Phase 7 — Hardware swarm
- [ ] zenoh bridge / DDS plan, fleet on GCS, deployment script, kill-switch procedure

Phase 8 — Task library + CI
- [ ] Scenario runner, self-hosted CI, task-author guide

## Parked / ideas
- ArduPilot backend (Pegasus supports it) — not needed while all FCs are PX4
- WebRTC livestream instead of X11 for remote viewing
- Isaac Lab / RL for swarm policies
- Per-drone lidar (Isaac RTX lidar) if a real lidar is ever mounted
- ZED SDK on simulated stream — only if a ZED X is ever used (Stereolabs Isaac integration)

## Done
- 2026-09-25 — ZED feed analysis + GPS-denied VIO flight (Phase 3). ZED: IMU 43 Hz wall (render-cadence-bound)
  → 246 Hz sim via an OnPhysicsStep graph (contract 200 Hz); camera_info 17.8 Hz sim (15–30 ✓); all ZED/VIO/MAVROS
  stamps now on one clock (images were sim time, odom/MAVROS wall); HD720 images blocked by host rmem_max
  (open item). ROS workspace had never been built on the new PC (vio_mock crash-looped: `./bisg ros build`).
  VIO: see the Phase 3 "GPS-denied flight works in sim" item. Phase 1 smoke (GPS scenario) still PASS after the changes.
- 2026-09-12 — Phase 0 documentation set created; hardware/ordering/PX4 policy decided
- 2026-09-21/22 — Workstation migration 22.04 → 24.04 done via new PC; host prepped (docker group, nvidia-container-toolkit, docker-compose-v2), found+fixed a driver-595/R590 incompatibility with Isaac Sim 5.1 (downgraded to 580.178.04), rebuilt `bisg/sim`+`bisg/ros` images from scratch, converted `third_party/*` clones to git submodules, re-ran Phase 1 smoke test clean. See plan.md §12.
- 2026-09-22 — Dropped remaining Ubuntu 22.04 mentions from docs/scripts now that the workstation is settled on 24.04 (CLAUDE.md, ADR-005, `docs/setup.md`, `docs/plan.md` §4 pin table, `docs/skills.md`; `scripts/check_env.sh`'s GPU test image moved from `nvidia/cuda:...-ubuntu22.04` to the `...-ubuntu24.04` tag). Restructured `docker/`: one `docker/compose.yaml` with all profiles still, but each image's Dockerfile + entrypoint now live in their own folder (`docker/sim/`, `docker/ros/`) instead of flat `docker/sim.Dockerfile` / `docker/sim-entrypoint.sh` etc. Verified `docker compose -f docker/compose.yaml --profile <sim|sim-headless|ros|tools> config` resolves identically to before the move. Rebuilt `bisg/sim`+`bisg/ros` from the new Dockerfile paths (all expensive layers — apt, PX4 SITL build, Pegasus clone/install, rosdep — hit cache, only the entrypoint COPY layer re-ran); `./bisg up headless` booted clean (97s to `[launch] sim ready`, 100s to PX4 ready), `./bisg smoke` PASS (armed → airborne 1.63 m → landed/disarmed), `./bisg mavros up` connected (`connected: true`) against the running SITL; `./bisg down` left no stray containers.
- 2026-09-22 — Installed the `graphify` Claude Code skill (global, `~/.claude/skills/graphify/`) and ran it on this repo. It flagged a real inconsistency: CLAUDE.md's Host facts still listed the broken NVIDIA driver `595.91.07` (the one §12 downgraded away from) instead of the actual `580.178.04`; fixed, and refreshed the "known gaps" line since docker-group + nvidia-container-toolkit are both confirmed working now.
- 2026-09-22 — Local-edit workflow for `third_party/` submodules (no push access upstream, no fork wanted): both submodules moved off detached HEAD onto a `local` git branch at their pinned tag; edits go on that branch and get picked up on the next build, `fetch`+`rebase <new-tag>` to move to a new upstream release without losing them. `docker/sim/Dockerfile` now builds Pegasus **from** the `third_party/PegasusSimulator` submodule instead of re-cloning it (so local edits actually reach the image) — this makes `git submodule update --init` a real prerequisite for `docker compose build sim` now, documented in `docs/setup.md`/`docs/plan.md` §5. Dropped the now-unused `PEGASUS_TAG` Docker build arg. `docker/zed/build.sh` already built from the submodule, so it needed no changes. See `third_party/README.md`.
