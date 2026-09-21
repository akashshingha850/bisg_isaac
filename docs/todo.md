# TODO

Live checklist. Move items to **Done** with a date; keep **Now** short (≤ 10 items).
Phase definitions and exit tests are in [roadmap.md](roadmap.md).

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

## Tracked — workstation OS migration 22.04 → 24.04 (plan.md §12)

Do it between phases (best: right after Phase 1). Before/after steps:
- [ ] Before: `docker save` `isaac-sim` + `bisg/*` images to the SSD; `docker volume ls > docs/volumes-before-migration.txt`; note driver version
- [ ] Before: confirm no script depends on host ROS Humble or 22.04-only packages (`grep -r "humble\|/opt/ros" scripts sim docker`)
- [ ] After: NVIDIA driver ≥ 570, `nvidia-container-toolkit`, `nvidia-ctk runtime configure`, `docker run --gpus all ... nvidia-smi`
- [ ] After: display server — X11 session or XWayland with `xhost +local:`; `sim` profile GUI check
- [ ] After: (optional) native ROS 2 Jazzy for debugging; `ros2 topic list` sees a running `ros` container
- [ ] After: re-run the Phase 1 headless smoke test + the latest phase exit test; tick this list in `Done`

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
- [ ] `/clock` + `use_sim_time` verified in MAVROS and our nodes
- [ ] Cross-container topic smoke test (Isaac Jazzy bridge → ros container)

Phase 3 — Sensors, ZED Mini contract, VIO
- [x] Stereo (63 mm) + depth + IMU rig under ZED names; TF tree; camera_info (2026-09-21): `sim/launcher/zed_rig.py`,
  wired from `sim/configs/*.yaml` `sensors.zed`. Verified live: `/drone_1/zed/zed_node/{left,right}/image_rect_color`
  (rgb8), `.../depth/depth_registered` (32FC1), `.../{left,right}/camera_info`, `.../imu/data` (~17 Hz measured,
  target 200 Hz — rate not yet tuned, see below) all publishing real data; static TF `drone_1/base_link ->
  zed_camera_link -> {left,right}_camera_frame -> optical` + `zed_imu_link` on `/drone_1/tf_static`.
  Camera intrinsics are a placeholder pinhole model (84° HFOV, HD720) — replace with factory K once the real
  unit is measured (`docs/hardware.md` ZED Mini model table still has mount pose/K as TBD).
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
  `reboot_required` — pushing alone isn't enough, `MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN` is needed after (confirmed
  safe on SITL: params persist through it). With the full set applied + reboot, arms and accepts a takeoff
  command with GPS fully disabled (confirmed by binary-search: full param revert arms cleanly, so this really is
  the GPS-denied config working, not a leftover GPS path).
- [ ] **Known bug — height estimate diverges once airborne under `EKF2_HGT_REF=Vision`**: on the ground the
  estimate is healthy (`pos_horiz_accuracy` ~0.016 m, all `ESTIMATOR_STATUS` flags good) and arming/takeoff are
  accepted, but during the 2026-09-21 test flight `mavros/local_position/pose.z` diverged to ~-81 m while Isaac's
  own ground truth showed the vehicle actually climbing to ~9 m (target was 2 m) — the position controller,
  trusting the bad estimate, drove a runaway climb. Recovered by commanding `MAV_CMD_NAV_LAND` (estimate kept
  diverging, did not help) then a full `./bisg restart` (SITL/EKF2 state doesn't survive a container recreate,
  so this always returns to a clean slate — no separate "undo" needed). Root cause not yet found: prime suspects
  are `EKF2_EV_POS_Z` lever-arm handling once the vehicle actually moves off `z≈0`, or a hidden interaction with
  `EKF2_EV_DELAY` visible only once the vehicle has real dynamics (both looked fine sitting still, which is why
  ground testing alone didn't catch it). **Do not fly this GPS-denied config further** (sim or otherwise) until
  this is root-caused — arming clean does not mean the height estimate stays sane after takeoff.
  Current container is back on PX4 defaults (GPS-based) and confirmed flying clean.
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
- 2026-09-12 — Phase 0 documentation set created; hardware/ordering/PX4 policy decided
