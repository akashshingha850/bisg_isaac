# Known bugs

Open bugs with what we know and how they could be fixed. `todo.md` tracks *work*; this file tracks
*defects*: things that behave wrong today. When one is fixed, move it to **Fixed** at the bottom with
the date and the commit/PR, and tick the matching `todo.md` item if there is one.

Severity: **S1** = unsafe to fly / blocks a phase exit test, **S2** = wrong data or misleading output,
**S3** = cosmetic or a trap for the next person.

| ID | Sev | Area | Summary |
|---|---|---|---|
| [B1](#b1) | S1 | failsafe | No usable failsafe action while GPS-denied (Land/Hold/RTL) |
| [B2](#b2) | S2 | DDS / ZED | HD720 ZED images and depth never reach a subscriber |
| [B3](#b3) | S2 | MAVROS | Plugin nodes ignore `--params-file`, so `px4_config.yaml` plugin settings are dead |
| [B5](#b5) | S2 | Pegasus | `state/*` topics are stamped with wall time, not sim time |
| [B6](#b6) | S2 | test | `tests/vio_flight.py` does not wait for PX4 timesync to lock |
| [B7](#b7) | S3 | vio_mock | Twist covariance is zero; no drift or orientation noise |
| [B8](#b8) | S3 | MAVROS | Plugins run on wall time for the first ~3 s; `/param` never switches |
| [B10](#b10) | S3 | images | `bisg/ros:arm64` still has the old entrypoint |
| [B11](#b11) | S3 | params | `push_px4_params.py` can't finish the job on SITL (reboot refused) |
| [B12](#b12) | S3 | GUI | `/clock` + OnPhysicsStep IMU changes not re-verified in the GUI profile (Isaac 6.0: full-UI path checked via `both`, native `gui` window not) |
| [B13](#b13) | S2 | ZED | No automated check that the camera view is unobstructed / pointing forward |
| [B15](#b15) | S3 | ZED | Sim rig resolution/fps/depth range are separate from `zed_params.yaml` (min depth 0.1 vs 0.2) |
| [B16](#b16) | S2 | ZED | Contract TF frames are `drone_<n>/`-prefixed; the real wrapper cannot publish a prefix |
| [B17](#b17) | S2 | ZED | SDK odometry now feeds EKF2 closed loop in the sim (bridge `odometry`, restamped); accuracy under flight is 0.37/0.53/0.34 m vs the 0.3 m bound |
| [B19](#b19) | S3 | ZED | Enabling the streaming server in the sim (`enable_streaming`) crashes the wrapper (SIGSEGV) |
| [B18](#b18) | S3 | ZED | The SDK connects to the sim's stream once per sim run (restart the sim to reconnect) |

---

<a id="b1"></a>
## B1 — No usable failsafe action while GPS-denied
**Sev S1 · blocks the first real VIO flight (Phase 5 bench checklist).**

**Symptom.** In the `single_iris_vio` scenario:
- Hold (the boot mode) refuses to arm with `global_position_invalid`.
- RTL and Takeoff won't engage.
- `AUTO.LAND` *does* engage, but on 2026-09-25 it flew the drone off at about 6 m/s toward (+x, −y) and into a
  warehouse wall. The estimate was still correct, so this was not an estimation fault.

**Cause.**
- MAVROS 2.15.1 always sends vision odometry as `MAV_FRAME_LOCAL_FRD` (`mavros_extras/src/plugins/odom.cpp:295`).
- EKF2 then clears `yaw_align` (`ev_yaw_control.cpp:181`), so it never publishes `vehicle_global_position`
  (`EKF2::PublishGlobalPosition` needs `yaw_align`).
- Navigator plans Land/Hold/RTL in lat/lon. `mode_requirements.cpp` only asks Land for a *local*
  position, so Land engages anyway and then steers toward a garbage lat/lon (0,0).

**Why it matters.** Today `COM_OBL_RC_ACT` / RC-loss / low-battery all fall back to one of these modes.
On the real drone, losing the offboard link would trigger Land, which would fly away.

**Possible fixes** (pick one, prove it in SITL, then update `docs/hardware.md` and the params file):
1. **Descend as the failsafe action.** Descend needs only attitude (`NAVIGATION_STATE_DESCEND`) and
   drifts slowly instead of navigating. Try `COM_OBL_RC_ACT` / `NAV_RCL_ACT` / `COM_LOW_BAT_ACT` values
   that resolve to Descend, and check `failsafe_flags` and the mode PX4 actually picks.
   Cheapest option, but horizontal drift is uncontrolled.
2. **Give EKF2 a north-aligned EV frame**, so there is a global position and Land/Hold work normally:
   - Send odometry as `MAV_FRAME_LOCAL_NED` instead of FRD. MAVROS can't: it's hard-coded. Options are a
     local patch of `odom.cpp` (MAVROS is apt-installed, so we'd need a source build), or publishing
     `ODOMETRY` ourselves with pymavlink/`mavros/mavlink/to`.
   - The EV frame must then really be north-aligned. That's true in sim (the Pegasus world is ENU). On
     the real ZED it needs a known start heading or the magnetometer.
   - Also set the global origin: `mavros/global_position/set_gp_origin`, **lat/lon only** (see the note under Fixed).
   - Most work, but gives full PX4 mode support.
3. **Onboard failsafe in our own stack.** `bisg_vehicle` watches link health and itself commands an
   OFFBOARD velocity descent. PX4's failsafe (Descend) stays as the last resort. This is needed
   anyway for the swarm; do it with option 1.

**Verify.** In SITL, kill the offboard stream mid-square (stop `tests/vio_flight.py` with Ctrl-C at
2 m altitude). The drone must come down within about 1 m of where it was, and must not translate.

---

<a id="b2"></a>
## B2 — HD720 ZED images and depth never reach a subscriber
**Sev S2 · blocks any real perception work and the contract checker's rate test.**

**Symptom.** `zed/zed_node/{left,right}/camera_info` and `imu/data` flow, but `left/right/image_rect_color`
and `depth/depth_registered` deliver **0** messages. There's no error anywhere.

**Cause (confirmed 2026-09-25).**
- Host `net.core.rmem_max` is the Ubuntu default, 212992 bytes.
- One 1280x720 rgb8 frame is 2.76 MB, about 42 UDP fragments; depth (32FC1) is 3.7 MB. Isaac publishes
  left, right and depth back to back, a ~9 MB burst per frame, and the socket buffer overflows.
- Evidence:
  - Booting the same rig at 320x180 delivered all three streams (42/42/47 Hz).
  - A plain ROS test publisher got about 40% of single HD720 frames through.

**Possible fixes.**
1. **Raise the kernel limit** (one command, `docs/setup.md`). `docker/cyclonedds.xml` already asks for 16 MB:
   ```
   echo 'net.core.rmem_max=16777216' | sudo tee /etc/sysctl.d/60-bisg-dds.conf && sudo sysctl --system
   ```
   Also consider raising `net.core.wmem_max` if the sender starts dropping.
2. If it still drops at 16 MB, **Cyclone shared memory (iceoryx)** for same-host traffic. The sim and ros
   containers already use `ipc: host`. Check first that Isaac's bundled Cyclone supports it.
3. Cut the bytes: publish `image_raw/compressed` (the ZED wrapper offers compressed topics too, so the
   contract stays the same), or lower the default resolution to VGA for sim runs that don't need HD.
4. Stagger the three writers, or put depth on a lower rate gate, so the bursts don't coincide.

The point cloud (0.92 MB per 320x180 cloud) is hit too: 5.5–7 Hz arrive of 10 Hz published.

**Verify.** After the fix, re-run the rate check (`ros2 topic hz` or the rates script) for all three
image topics at HD720, and for `point_cloud/cloud_registered`. Expect about 15–30 Hz sim time (the contract range). Then update the
`todo.md` ZED item.

---

<a id="b3"></a>
## B3 — MAVROS plugin nodes ignore `--params-file`
**Sev S2 · anything we configure in `px4_config.yaml` for a plugin is silently not applied.**

**Symptom.**
- `ros2 param get /drone_1/mavros/time timesync_rate` returns `0.0`; `px4_config.yaml` says `10.0`.
- `use_sim_time` passed with `-p` or `--params-file` reached `mavros_node` but no plugin node.

**Cause.**
- MAVROS 2.15.1 builds each plugin as its own node with `use_global_arguments(false)`
  (`mavros/src/lib/plugin.cpp:35`). The comment there says it avoids component-container remaps.
- Global `--ros-args` (including every params file) therefore never reaches plugins; they run on their
  declared defaults.
- Frame names still work only because the plugin defaults happen to be `odom` / `base_link`.

**Current workaround.** `docker/ros/mavros_sim_time.py` sets `use_sim_time` on every plugin node at runtime.
It does nothing for the other `px4_config.yaml` values.

**Possible fixes.**
1. **Generalise the helper.** After startup, read `px4_config.yaml`, match each `/**/<plugin>` block to
   `/drone_N/mavros/<plugin>`, and set those params at runtime. Small, and it keeps apt MAVROS. Every
   dynamic parameter would then work.
2. **Upstream.** Report or patch MAVROS so the UAS copies its parameter overrides into
   `NodeOptions::parameter_overrides` for each plugin, or re-enables global args with `__node`/`__ns`
   remaps filtered out. Pull the fix in once it lands in a Jazzy release.
3. **Pin a different MAVROS** that doesn't have this behaviour. That needs an ADR update (pins live in `plan.md` §4).

**Verify.** `ros2 param get /drone_1/mavros/time timesync_rate` returns 10.0, and
`ros2 param get /drone_1/mavros/odometry fcu.odom_parent_id_des` returns the value in the config file.

---

<a id="b5"></a>
## B5 — Pegasus `state/*` topics are stamped with wall time
**Sev S2 · a trap for any consumer that uses the stamp.**

**Symptom.** Pegasus's `ROS2Backend` stamps `state/pose`, `state/twist`, ... with
`node.get_clock().now()` on a node without `use_sim_time`, so they carry wall time. Everything else
in the sim now runs on sim time.

**Current workaround.** `vio_mock` ignores the incoming stamp and restamps on arrival with its own sim-time clock,
which is at most one physics step late. `tests/vio_flight.py` compares values, not stamps.

**Possible fixes.**
1. Local patch on the `docker/sim/PegasusSimulator` `local` branch (`docs/sources.md`): set
   `use_sim_time=True` on the backend node, or stamp from the physics time Pegasus already has
   (`_current_utime` / `world.current_time`). The patch reaches the image on the next `bisg/sim` build.
2. Or have the launcher pass sim time into the backend. Both need a small Pegasus change.

**Verify.** `ros2 topic echo /drone_1/state/pose --field header.stamp` is within 10 ms of `/clock`.

---

<a id="b6"></a>
## B6 — `tests/vio_flight.py` does not wait for timesync to lock
**Sev S2 · the test can fly on arrival-time stamps and still pass.**

**Symptom.** PX4 timesync needs 500 samples (about 50 s) after MAVROS starts before
`vehicle_visual_odometry.timestamp_sample` stops equalling `timestamp`. Before that, PX4 stamps EV
samples on arrival. It's roughly right with the 30 ms mock latency, but it isn't the configuration we
claim to test. Today the test starts as soon as MAVROS is connected.

**Possible fixes.**
1. Gate the test on lock. Enable MAVROS's own timesync by setting `timesync_rate` at runtime (see
   [B3](#b3)), then wait until `mavros/timesync_status` reports a stable offset. Or read PX4's
   `TIMESYNC` / `timesync_status` over MAVLink.
2. Or keep it simple: have `./bisg wait` (or the test) also wait until
   `./bisg debug px4 listener vehicle_visual_odometry` shows `timestamp_sample != timestamp`.

**Verify.** Start the test immediately after `./bisg all`. It must wait, print "timesync locked", then fly.

---

<a id="b7"></a>
## B7 — vio_mock is too optimistic
**Sev S3 · the sim flies better than the real ZED will.**

- `twist.covariance` is all zero, so PX4 sees `velocity_variance: 0` and falls back to the
  `EKF2_EVV_NOISE` lower bound.
- There is no drift model (`odom` == `map`), and no orientation noise; orientation covariance is a fixed 0.05.
- The 30 ms latency is fixed, with no jitter and no dropouts.

**Possible fixes.** Populate the twist covariance from a velocity-noise parameter. Add a random-walk drift
term plus yaw drift. Add latency jitter and occasional dropouts. Tune all of them to measured ZED Mini
behaviour once Phase 5 bench logs exist.

---

<a id="b8"></a>
## B8 — MAVROS plugin clock switch is late / incomplete
**Sev S3.**

- Plugin nodes run on wall time for the ~3 s before `mavros_sim_time.py` finishes. The first timesync
  samples then jump, and PX4 resets its filter once. That's harmless: lock comes about 50 s later anyway.
- `/drone_1/mavros/param` failed to switch on every run (its service was busy with the param fetch).
  It doesn't affect timing today.

**Possible fixes.** Retry failed nodes for longer with backoff. Longer term, remove the helper entirely once
[B3](#b3) is fixed upstream, because then `use_sim_time` can go in the params file.

---

<a id="b10"></a>
## B10 — `bisg/ros:arm64` has the old entrypoint
**Sev S3 · the Jetson would run the pre-2026-09-25 entrypoint.**

The fix is to rebuild: `docker buildx build --platform linux/arm64 -f docker/ros/Dockerfile -t bisg/ros:arm64 --load .`
(about 15 min under qemu). The hardware path should behave the same: `USE_SIM_TIME` defaults to false,
and MAVROS runs with the same param files as `px4.launch`. Confirm on the Jetson that MAVROS connects on
serial.

---

<a id="b11"></a>
## B11 — `push_px4_params.py` can't finish the job on SITL
**Sev S3.**

`EKF2_HGT_REF` and `EKF2_MAG_TYPE` are `reboot_required`, and SITL answers `MAV_CMD_PREFLIGHT_REBOOT_SHUTDOWN`
with DENIED. Pushed params therefore leave EKF2 on its old origin and yaw source; that is what caused the
2026-09-21 "−90 m" local z. The sim now applies params at boot (`px4.params`), so the script is only
correct for hardware.

**Possible fixes.** Have the script detect SITL (autopilot `HEARTBEAT` + `AUTOPILOT_VERSION` flags, or a
`--sitl` flag) and refuse with a pointer to `px4.params`, or warn loudly when a pushed param is
`reboot_required`.

---

<a id="b12"></a>
## B12 — GUI profile not re-verified
**Sev S3.**

The `/clock` physics callback, the `OnPhysicsStep` IMU graph, the `extends:` scenario loader and the
2026-09-25 ZED rig fixes (mount, quaternion order, intrinsics) were verified headless only. Run `./bisg up gui -c single_iris_vio` once, and check `/clock`, the IMU rate and
`tests/vio_flight.py`.

---

<a id="b13"></a>
## B13 — No automated check that the camera view is unobstructed
**Sev S2 · the ZED feed was unusable for weeks while every rate/topic check passed.**

Topic lists, rates and `camera_info` sizes all looked healthy while the camera stared into the
fuselage (see Fixed, 2026-09-25). Nothing in the pipeline *looks* at the pixels.

**Possible fixes.**
1. Add a view check to `tests/check_contract.py` (Phase 3) or to the sim-regression suite. On the ground
   and at hover, grab one `depth_registered` frame and fail if more than about 1% of pixels are under
   0.3 m outside the bottom floor band. The flight case is simpler: fail on *any* pixel under 0.5 m at
   2 m altitude. A capture script that already does this (PNGs plus near-field bbox) was used on
   2026-09-25 and can become the test (it writes PNGs with numpy+zlib; the ros image has no PIL/cv2).
2. Check parity 4 (`camera_info` K equal to the ZED model table) would have caught the 24° HFOV at once.
   Write that part of `check_contract.py` first.
3. Check stereo sanity: disparity of a near object must be positive (left x > right x). This catches a
   swapped or backwards pair.
4. Re-run the view check whenever `sensors.zed.mount_xyz_rpy`, the airframe USD (Phase 4
   `bisg_quad`) or the FOV changes. The real mount must also keep the lens ahead of the frame and the
   props outside the ~90° HFOV (`docs/hardware.md`).

---

<a id="b15"></a>
## B15 — Sim rig parameters are a second copy of the wrapper's
**Sev S3 · parity drift.**

Feature switches come from `docker/zed/zed.yaml`, but the sim rig still takes resolution,
fps and depth range from the scenario (`sensors.zed.resolution/fps/depth_range`). They already differ:
sim near limit 0.1 m, wrapper `depth.min_depth` 0.2 m.

**Possible fix.** Let `zed_rig.py` take `general.grab_resolution`, `general.grab_frame_rate` and
`depth.min_depth/max_depth` from the same file (map HD720 → 1280×720 etc.), and keep only the
sim-only values (mount, baseline, view) in the scenario.

<a id="b16"></a>
## B16 — Contract TF frames are `drone_<n>/`-prefixed; the real wrapper cannot publish a prefix
**Sev S2 · TF consumers written against the contract will not resolve the real drone's frames. Open.**

`docs/interface-contract.md` prefixes every frame with `drone_<n>/` (`drone_1/zed_camera_link`, ...). The emulated rig does
that. `zed_wrapper` 5.4.1 builds frame ids from its camera name only (`zed_camera_link`, `zed_left_camera_frame`, ...) plus the
`pos_tracking.odometry_frame` / `base_frame` parameters, and has no TF-prefix option; `camera_name` also forms the node
namespace, so putting `drone_1/` in it breaks node naming. In SDK mode (`ZED_SOURCE=sdk`) the sim therefore shows the real
wrapper's unprefixed frames — correct parity with the Jetson, wrong versus the contract text.
**Possible fixes.** (1) Contract: state that frames are unprefixed per vehicle and rely on the `/drone_<n>/tf` namespacing (each
drone has its own TF tree; the fleet manager re-parents). (2) A TF relay that republishes with prefixes. Decide with the swarm phase.

<a id="b17"></a>
## B17 — SDK odometry into PX4: works, accuracy not yet inside the bound
**Sev S2 · partly resolved 2026-10-05.**

`vio_mock` stamps with sim time because PX4 SITL runs on sim time and EKF2 fuses a vision sample at its (timesynced) stamp; the wrapper
stamps with the wall clock and the sim runs at rtf ~0.4, so a source stamp would drift from PX4's clock by (1 - rtf) s/s.
**Fixed:** the bridge's `odometry` module (`docker/zed/zed_stack/bridge/odometry.py`, `services.px4_bridge.odometry`, `restamp: true` in the `sim:` block of
`docker/zed/zed.yaml`) stamps with the node's `/clock` time on arrival, fixes the frame ids MAVROS matches and goes silent while tracking is not OK
(unit-tested on fake topics, `./bisg zed test`).
**Verified live (single_iris_vio, ZED_SOURCE=sdk, vio_mock off):** PX4 only becomes "Ready for takeoff" once the SDK odometry reaches EKF2 (136 s vs 37 s with GPS),
and `tests/vio_flight.py` flew OFFBOARD takeoff -> hover -> 3 m square -> land and disarmed on the SDK's VIO alone.
**Open:** the test **fails its 0.3 m bound** — max |EKF estimate - ground truth| x 0.373 / y 0.529 / z 0.338 m over 1170 airborne samples; the estimate reads
~7 % (x, y) and ~12 % (z, hover 1.98 m est vs 2.26-2.35 m truth) short, and the y error grows along the square (0.22 -> 0.50 m). The observer-mode check
(2026-10-03, GPS flight) had path ratio 1.01 and RMSE 0.088 m, so look first at: camera lever arm (`EKF2_EV_POS_X/Y/Z` is 0 but the twin sits 0.18 m ahead of the body),
`restamp` latency vs `EKF2_EV_DELAY`, visual-only GEN_3 under offboard accelerations, and the twin's intrinsics vs the rendered field of view.

<a id="b18"></a>
## B18 — The SDK connects to the sim's stream once per sim run
**Sev S3 · a trap: restarting only the wrapper leaves it with no frames. Open (upstream).**

After a wrapper has connected to the extension's stream and goes away, a new wrapper never receives frames (spike on 2026-10-03:
`CAMERA NOT INITIALIZED`; in the integrated stack a recreated wrapper published nothing at all, not even odometry or health, which are small
topics unaffected by [B2](#b2)). Same when the wrapper
starts before the stream exists. `./bisg zed up` retries once, which covers a missed first connect, not a reconnect.
**Workaround:** restart the sim, then `./bisg zed up`. Worth re-testing on extension > 5.2.1 / Isaac Sim 6.0.1.

---

## Fixed
- **2026-10-02 — B4: launcher RTF metric under-reported** (`sim/launcher/launch.py`, Isaac 6.0 migration). Cause confirmed:
  it counted loop iterations, and a render iteration ran more than one physics step. The 6.0 loop is
  `simulation_app.update()` and the heartbeat now counts `SimulationManager.get_num_physics_steps()`, so
  `perf … steps/s` equals the `/clock` rate (measured 82 vs 80, 97 vs 97 Hz). Old `docs/performance.md` numbers
  are still the iteration-based ones and need a redo.
- **2026-10-02 — B9: ZED images/depth ignored the rate gate** (`sim/launcher/zed_rig.py`). Only the
  `PostProcessDispatch…Gate` (camera_info) was set; each image writer has its own `<rendervar>IsaacSimulationGate`.
  All of them are now set from the render dt: images 12.05 Hz wall at rtf 0.387 = 31 Hz sim, camera_info 31 Hz.
- **2026-09-25 — ZED camera footage blocked / backwards / wrong FOV** (`sim/launcher/zed_rig.py`).
  - **Symptom:** frames were nearly black, and 90% of depth was under 0.2 m.
  - **Three stacked bugs:**
    1. The mount at x 0.10 m put the lens *inside* the Iris nose; the body mesh ends at x 0.156.
    2. `Camera.set_local_pose` takes quaternions scalar-first (w,x,y,z), but it was given scipy's
       (x,y,z,w), so identity read as a 180° yaw (camera facing backwards). A "180° yaw" copied from
       Pegasus's `MonocularCamera` compensated by accident; in that class, too, the order confusion is
       what makes its "180° roll" come out as identity.
    3. The focal length was never applied (a lens-distortion model was set with its own fx). K stayed at
       the USD default 50 mm: fx 1527 px at 640 wide, about 24° HFOV instead of 84°.
  - **Fixes:** mount x 0.18 (props outside the FOV: about 2.5 cm margin at 84° HFOV, still clear at 90°);
    `_quat_wxyz()`; USD `focalLength`/`horizontalAperture`/`verticalAperture` set directly.
  - **Verified** on the ground, at hover and mid-square banked about 20°: nothing in view, 0 near pixels
    in flight. A "which way does the lens point" log based on `ComputeLocalToWorldTransform` was tried
    and removed: it reads a stale pose before the first physics step, and reported −X both before and
    after the fix.

- **2026-09-25 — GPS-denied height estimate runaway (the 2026-09-21 "−81 m" flight).**
  - Causes: ROS side on wall time while PX4 SITL runs on sim time (timesync never locked); GPS-denied params
    not really applied; Hold/AUTO.LAND unusable without a global position.
  - Fixed by `/clock` + `use_sim_time` everywhere, boot-time params and flying OFFBOARD.
  - `tests/vio_flight.py` PASS: max error 0.076 m. Details in the `todo.md` Phase 3 entry.
- **2026-09-25 — ZED IMU at 43 Hz instead of 200 Hz.** Its OmniGraph ran on rendered frames only. It is now
  driven by `OnPhysicsStep`: 246 Hz sim time.
- **2026-09-25 — vio_mock crash-looping** ("Package 'bisg_vehicle' not found"). `ros2_ws` had never been built
  on the new PC. Fix: `./bisg ros build`. `install/` is git-ignored, so every fresh machine needs it; consider
  adding it to `./bisg setup`.
- *Note, not a bug:* setting the EKF2 global origin with an **altitude** moves local z by
  (new − baro-initialised altitude), because `Ekf::setAltOrigin` keeps global altitude constant. We saw 36 m.
  If an origin is ever needed ([B1](#b1) option 2), send lat/lon only: an out-of-range altitude (> 100 km)
  makes PX4 skip it.

- **2026-10-03 — B14 image topic names (fixed).** Contract and emulated rig renamed to the wrapper 5.4.1 names:
  `left|right/color/rect/image`, `left|right/color/rect/camera_info` (`zed_rig.py`, `interface-contract.md`, `plan.md`).
- **2026-10-03 — `docker/zed/zed.yaml` had `pos_tracking_mode: GEN_2`.** Not a valid value in wrapper 5.4.1
  (`AUTO`, `GEN_1`, `GEN_3`). Now `AUTO` (= GEN_3 on SDK 5.4). Found while bringing the real SDK up in the sim.
- **2026-10-03 — Jetson `zed` service would not start.** It set `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, but Stereolabs' image
  ships Fast DDS only. `docker/zed/Dockerfile.overlay` adds `ros-jazzy-rmw-cyclonedds-cpp`; `docker/zed/build.sh` applies it.
- **2026-10-03 — Jetson `zed` topic root.** `namespace:=drone_1` on the stock launch publishes `/drone_1/zed/...` (no `zed_node`);
  `docker/zed/zed_drone.launch.py` gives the contract's `/drone_<n>/zed/zed_node/...` and is used by sim and Jetson.
- **2026-10-03 — `scripts/fetch_sources.sh` re-cloned submodules.** It tested `-d dir/.git`; a submodule's `.git` is a file. Now `-e`.
- **2026-10-03 — "SDK tracking dead, frames corrupted" in the first ZED spike.** Harness bug, not the SDK: the ZED asset was
  nested under a kinematic body instead of fixed-jointed, so the camera never moved (identical frames -> `Duplicate frame
  detected` -> `CORRUPTED FRAME`, odometry exactly 0). With the `FixedJoint` mount: 0 corrupted frames, odometry tracks.

<a id="b19"></a>
## B19 — `enable_streaming` crashes the wrapper in the sim
**Sev S3 · found 2026-10-05 by `tests/zed_bench.py --streaming` · open.**
With `ZED_SOURCE=sdk` the camera is already an input stream (the Isaac ZED Mini twin), and asking the wrapper to serve a stream as well fails:
`[ZED][ERROR] [Streaming] Cannot enable streaming: Err Code 3` -> `Error starting the Streaming server` -> `component_container_isolated ... process has died ... exit code -11`.
After that the wrapper is gone and the sim must be restarted to reconnect (B18). `docker/zed/zed.yaml` `streaming.enabled: true` at start would crash it the same way.
**Workaround:** keep `streaming` off in the sim (the default); test it on the real camera. The bench only runs it with `--streaming`, last.
**To check:** whether the same call works with the real camera on USB (expected), and whether Stereolabs' extension can relay a stream (no).

