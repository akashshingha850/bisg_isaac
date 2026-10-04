# Isaac Sim 6.0 migration — errors and gotchas

Everything that went wrong (or surprised us) during the 5.1 → 6.0 migration of 2026-10-02, kept for the next debugging
session or the 6.1 step. Context and results: [`archive/docs/migration-report.md`](../archive/docs/migration-report.md). Long-lived product bugs stay in
[`bugs.md`](bugs.md); an item here moves there if it is still open and still matters after the migration is merged.

Status: **Fixed** (change is in the branch) · **Open** (still true) · **Note** (no action needed, but it will cost you time if you don't know).
Evidence logs are in `logs/migration/` (git-ignored, local to the workstation).

| ID | Status | Area | Summary |
|---|---|---|---|
| [M1](#m1) | Fixed | PX4 build | PX4 v1.16.0 SITL build dies with `IndexError` in `px_update_git_header.py` |
| [M2](#m2) | Fixed | launcher | `UnboundLocalError: 'omni'` after the World port (my own regression) |
| [M3](#m3) | Fixed | ZED rig | `ImportError: cannot import name 'IMUSensor' from 'isaacsim.sensors.physics'` |
| [M4](#m4) | Fixed | views | WebRTC extension `omni.services.livestream.nvcf` no longer exists; launcher still printed "ready" |
| [M5](#m5) | Fixed | compose | Sim container reports `(unhealthy)` while working |
| [M6](#m6) | Fixed | boot time | Every boot recompiles RTX shaders (~190 s instead of ~30 s) |
| [M7](#m7) | Fixed | ZED rig | Image/depth publish at the full render rate, twice `camera_info` (= bugs.md B9) |
| [M8](#m8) | **Open** | performance | Simulation runs at 0.33× real time (was 1.18×): Pegasus per-step Python |
| [M9](#m9) | **Open** | launcher | `app.render: false` no longer gives a physics-only loop; `headless_fast` is 2.4× slower |
| [M10](#m10) | Open | cosmetic | Test box renders yellow, scenario asks for orange |
| [M11](#m11) | Note | MAVROS | Second drone's `mavros/state` shows `CMODE(50593792)` |
| [M12](#m12) | **Open** | API debt | ZED rig still on deprecated `isaacsim.sensors.camera` / `isaacsim.core.utils`; `isaacsim.ros2.bridge` is a shim |
| [M13](#m13) | Note | docs | `archive/docs/migrate.md` has wrong details (callback order, GPU, PX4 pin, "current" versions) |
| [M14](#m14) | Fixed | test | `smoke_takeoff.py` fails at low RTF with a misleading `There was an error running python` |
| [M15](#m15) | Note | host | `./bisg debug mavlink` needs `pymavlink` on the host (pre-existing) |
| [M16](#m16) | Note | logs | Benign warnings that look like errors |
| [M17](#m17) | Note | image | The `6.0.0` image reports a release-candidate version string |
| [M18](#m18) | **Open** | supply chain | Pegasus pin is only reachable via `refs/pull/144/head` |
| [M19](#m19) | Note | Pegasus | Environment loading and world setup semantics changed (async load, no `World.reset`) |
| [M20](#m20) | Note | docs/perf | `docs/performance.md` numbers and `rendering_dt` meaning are 5.1-era |

---

<a id="m1"></a>
## M1 — PX4 v1.16.0 SITL build fails with `IndexError`
**Fixed.** `docker/sim/Dockerfile`.

```
FAILED: src/lib/version/build_git_version.h
  File ".../px_update_git_header.py", line 132
    nuttx_git_tag = re.findall(r'nuttx-[0-9]+\.[0-9]+\.[0-9]+', nuttx_git_tags)[-1]...
IndexError: list index out of range
```

**Cause.** v1.16.0's version script reads `git tag` in `platforms/nuttx/NuttX/nuttx` and expects a `nuttx-X.Y.Z` tag, even for a
SITL build. We clone with `--shallow-submodules`, which leaves no tags. v1.17.0's script does not need it, which is why the old image
built fine.

**Fix.** After the clone: `git -C platforms/nuttx/NuttX/nuttx fetch --depth 1 --tags origin` (harmless on 1.17).
**Spot it:** the build stops at step ~17 of ~1068, ninja prints only `build stopped: subcommand failed`; the traceback is a few lines above.

---

<a id="m2"></a>
## M2 — `UnboundLocalError: cannot access local variable 'omni'`
**Fixed.** `sim/launcher/launch.py`. Introduced during the port: a `import omni.usd` inside `App.__init__` made `omni` a local name for
the whole function, so the earlier `omni.timeline.get_timeline_interface()` failed. Fix: import `omni.usd` at module level.
**Lesson:** the traceback appears only in `docker logs` after ~190 s of boot (then ~30 s warm); lint launcher edits with
`python3 -m py_compile` and look for function-local imports of module names.

---

<a id="m3"></a>
## M3 — `cannot import name 'IMUSensor' from 'isaacsim.sensors.physics' (unknown location)`
**Fixed.** `sim/launcher/zed_rig.py`.

**Cause.** `isaacsim.sensors.physics` moved to `extsDeprecated/` in 6.0. `apps/isaacsim.exp.base.python.kit` has that folder on the search
path, but the extension is not loaded and `enable_extension()` did not make the import resolve ("unknown location" = an empty
namespace package). Making the import lazy after `enable_extension` was not enough.

**Fix.** Port to `isaacsim.sensors.experimental.physics`: `IMUSensor(IMU.create(path, translations=[[x, y, z]]))`. It has no `frequency`
argument (it samples every physics step, which is what our `OnPhysicsStep` graph reads). The OmniGraph node
`isaacsim.sensors.physics.IsaacReadIMU` (extension `isaacsim.sensors.physics.nodes`) is unchanged and still works.
Keep a reference to the sensor object (it is returned in the rig dict) so it is not garbage-collected.

---

<a id="m4"></a>
## M4 — WebRTC: `No versions of omni.services.livestream.nvcf that satisfies …`
**Fixed.** `sim/launcher/launch.py`.

**Symptom.** `./bisg up webrtc|both` printed `livestream webrtc ready — connect … TCP 49100`, but nothing listened on 49100. The only hint
was an extension-manager "No versions of … satisfies" block in the log.
**Causes.** (1) 6.0 replaced `omni.services.livestream.nvcf` with `omni.kit.livestream.app` (+ `omni.kit.livestream.webrtc`).
(2) The launcher ignored the return value of `enable_extension`.
(3) The 5.1 settings `--/app/livestream/port|publicEndpointAddress` do not apply to the new extension; its settings are
`--/exts/omni.kit.livestream.app/primaryStream.{signalPort,streamPort,streamType,publicIp}`. The defaults live in
`isaacsim.exp.full.streaming.kit`, which the python kit does not load, so we set them explicitly.
**Fix.** New extension and settings; `raise SystemExit` if the extension cannot be enabled.
**Still unverified:** a real WebRTC client connection (TCP 49100 listens; UDP 47998 opens on negotiation).

---

<a id="m5"></a>
## M5 — Container shows `(unhealthy)` while the sim runs fine
**Fixed.** `docker/compose.yaml` (`healthcheck: disable: true`).
The 6.0 base image ships `HEALTHCHECK … grep -q AppReady` over `/isaac-sim/.nvidia-omniverse/logs/Kit/*/*/kit_*.log`. Our python-kit
launcher logs to `/isaac-sim/kit/logs/Kit/Isaac-Sim Python/6.0/`, so the check can never pass (the 5.1 image had none). It is cosmetic,
but anything that waits on `docker ps` health (scripts, orchestrators) would hang or restart the container.
Our readiness signal is `[launch] sim ready` + PX4 `Ready for takeoff` (`./bisg wait`).

---

<a id="m6"></a>
## M6 — Every boot takes ~190 s: shader cache is not persisted
**Fixed.** New named volume `isaac-cache-kit` → `/isaac-sim/kit/cache` (compose); the directory is created in the image so the volume is
user-owned; `./bisg debug clean-cache` removes it too.

**Symptom.** `[launch] sim ready after ~195 s` on every start, vs ~100 s on 5.1. The launcher's boot phases showed 184 of 191 s inside
`SimulationApp(...)`. The Kit log shows no activity for minutes except
`Waiting for RtPso async group async compilation: 60 seconds` and `Waiting for compilation of ray tracing shaders … finished after 82 seconds`.
**Cause.** Isaac 6.0's writable shader caches are `/isaac-sim/kit/cache/shadercache` and `…/nv_shadercache`
(log lines `shaderCachePath:` / `driverShaderCachePath:`), not under `~/.cache`. Compose only persisted `/isaac-sim/.cache` and
`/.nv/ComputeCache`, so the cache died with each container.
**Result.** First boot after the change 192 s (populates the volume); every later boot **30 s** to `sim ready`, 39 s to PX4 ready.
**Gotcha.** The 1.4 GB `…/extscache/omni.hydra.rtx.shadercache…/cache` inside the image is a read-only pre-shipped cache; do not mount over it.

---

<a id="m7"></a>
## M7 — ZED images/depth publish at the full render rate
**Fixed.** `sim/launcher/zed_rig.py` (this was already known as bugs.md **B9**).

`PostProcessDispatchIsaacSimulationGate` (what the 5.1 code set) only gates `camera_info`. Each image writer has its own
`<rendervar>IsaacSimulationGate` (`LdrColorSDIsaacSimulationGate`, `DistanceToImagePlaneSDIsaacSimulationGate`), left at step 1, so images
went out at the render rate (~60 Hz sim) against ~30 Hz `camera_info`. Now all gates get `round(1 / (render_dt × fps))`.
Measured on 6.0: images 12.05 Hz wall ÷ rtf 0.387 = **31 Hz sim**, `camera_info` 31 Hz.
**Gotcha:** the gate counts **rendered frames**, and in 6.0 one `simulation_app.update()` is one frame at `RenderingManager` dt, so the right
step depends on `world.rendering_dt`, not on a constant 60.

---

<a id="m8"></a>
## M8 — Simulation speed fell from 1.18× to 0.33× real time
**Open · the main thing to fix next.**

**Numbers.** `/clock` rate (physics steps per wall second; nominal 250):

| Scenario | 5.1 | 6.0 |
|---|---:|---:|
| `single_iris_vio` (ZED) | 296 Hz (rtf 1.18) | 80–97 Hz (rtf 0.32–0.39) |
| `single_iris_nozed` | 491 Hz (rtf 1.97) | 120 Hz (rtf 0.48) |
| 2 / 4 / 8 drones, no ZED | — | 73 / 41 / 23 Hz |

Total drone-steps per second is roughly constant (119 → 184 from 1 to 8 drones): one Python thread is the bottleneck, GPU use stays at 6–40 %.
**Not the cause:** rendering (60 → 30 Hz render gave 85 → 97 Hz), ROS publishing, PX4, MAVROS.
**Cause (profile).** `app.profile_s: 45` (cProfile of the loop) shows the Python Pegasus runs in every `PHYSICS_POST_STEP`:
`Multirotor.update` makes 6 `RigidPrim.apply_forces_and_torques_at_pos` calls per step (4 rotors, body torque, drag) and 4
`Articulation.set_dof_velocities` calls (propeller animation) each preceded by `get_all_matching_child_prims`; every call builds warp
arrays (`wp.array.__init__` ≈ 18 % of the profile). 5.1 used `dynamic_control` handles, which are cheap.
**Partly fixed 2026-10-04:** `sim/launcher/pegasus_fast.py` (runtime patch, `perf.pegasus_fast`) caches the RigidPrim wrappers, batches the 6 force/torque calls into 1 and writes propeller joints only on change: Python time per step -22 %, RTF 0.44 -> 0.54 in the GUI, hover test PASS; headless 0.85. See `performance.md` "Why it is not real time". **Candidates (still open):** one batched force/torque call per step; propeller visuals only on rendered
frames or off when headless; avoid per-call prim resolution; `physics_dt` is **not** a safe knob (it sets the PX4 sensor rate).
**Detect:** `./bisg debug perf` (now steps/s = real physics steps) or `ros2 topic hz /clock`.

---

<a id="m9"></a>
## M9 — `app.render: false` is not physics-only any more
**Open.** `World.step(render=False)` — physics without the Kit update — has no 6.0 equivalent we use; the loop always calls
`simulation_app.update()`. The launcher logs a warning. `docker/sim/configs/headless_fast.yaml` (the test profile) boots in 30 s and passes
the smoke test but runs at 132–137 steps/s (rtf 0.53) vs 317 steps/s (rtf 1.27) documented for 5.1.
**Possible fix:** a manual loop with `SimulationManager.step(steps=N)` + `RenderingManager.render()` — needs checking that the Pegasus
`PHYSICS_POST_STEP` callbacks fire for it (they register through `SimulationManager`, so probably yes, but untested).

---

<a id="m10"></a>
## M10 — Test box is yellow, not orange
**Open, cosmetic.** `world.objects` asks for `color: [1.0, 0.45, 0.0]`; the 6.0 `isaacsim.core.experimental.objects.Cube(colors=…)` renders
yellow. Probably an sRGB/linear conversion (5.1's `FixedCuboid(color=…)` rendered orange). Geometry and depth tests are unaffected.

---

<a id="m11"></a>
## M11 — `mavros/state` of the second drone reads `CMODE(50593792)`
**Note.** Drone 1 prints `AUTO.LOITER`; drone 2 (MAVROS started later, `--drone 2`) printed the raw custom mode `50593792 = 0x03040000` =
AUTO (4) / LOITER (3), i.e. correct mode, un-decoded string. Likely MAVROS decoded the heartbeat before it had identified the
autopilot. Not looked into; connection, topics (155) and `connected: true` are fine.

---

<a id="m12"></a>
## M12 — Deprecated APIs still in use (port before Isaac Sim 6.1)
**Open.** They import and work in 6.0, but live in `extsDeprecated/` or are shims:
* `sim/launcher/zed_rig.py`: `isaacsim.sensors.camera.camera.Camera`, `isaacsim.core.utils.stage`, `isaacsim.core.utils.prims.set_targets`.
* `enable_extension("isaacsim.ros2.bridge")` in `launch.py`, `zed_rig.py`, `zed_depth.py`: `isaacsim.ros2.bridge` is now a thin extension (version
  5.1.1) that just depends on `isaacsim.ros2.{core,nodes,ui,examples}`. OmniGraph node names are still `isaacsim.ros2.bridge.ROS2Publish*`, so
  those strings are correct. Enable `isaacsim.ros2.core` + `isaacsim.ros2.nodes` instead to skip loading the UI/examples.
* Search results for the `archive/docs/migrate.md` §43 patterns on our code: no `omni.isaac`, `dynamic_control`, `SimulationContext`, `World(`, `isaacsim.core.api`, `Python 3.11` left.

---

<a id="m13"></a>
## M13 — Corrections to `archive/docs/migrate.md`
**Note.** Things in the migration guide that did not match what we found:
* §15: `SimulationManager.register_callback(SimulationEvent.PHYSICS_POST_STEP, callback)` — the real signature is
  `register_callback(callback, event, *, order=0)`; `RenderingManager.register_callback(event, *, callback, order=0)` takes `callback` as a keyword.
  Callbacks get `(dt, context)`.
* §8/§28: asks for PX4 v1.16.0 as the target; ADR-003 needs SITL = Pixracer firmware (1.17.0) and 1.17.0 works → pin kept (migration-report D2).
* §6: `git push origin isaac-5.1-baseline` — not done (outward-facing; tag is local).
* §10: `docker compose build --no-cache sim` is unnecessary; the changed layers rebuild on their own.
* §40/§4: "RTX 5090 workstation" — this machine is an RTX 4500 Ada (24 GB), Ubuntu 24.04.
* §9: "Python 3.11 → 3.12" is true for the Isaac interpreter; our `bisg/ros` container Python is unaffected.
* §24: setting `ROS_DISTRO`/`RMW_IMPLEMENTATION`/`LD_LIBRARY_PATH` in the image is already how we do it; 6.0's `setup_ros_env.sh` defaults to **FastDDS**, so keep `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` set in the image (it is).
* §21: bundled ROS libraries moved from `exts/isaacsim.ros2.bridge/` to `exts/isaacsim.ros2.core/{humble,jazzy}`.
* §35: people simulation is not used here; not migrated.
* The guide's §32 sensor topic names (`/drone_1/zed/rgb/image_rect_color`, `…/depth/depth_registered`, `…/zed/imu/data`) are not our contract names;
  ours are `zed/zed_node/{left,right}/image_rect_color`, `zed/zed_node/depth/depth_registered`, `zed/zed_node/imu/data` (`interface-contract.md`).

---

<a id="m14"></a>
## M14 — `smoke_takeoff.py` fails at low RTF; message is misleading
**Fixed.** `tests/smoke_takeoff.py --patience N` multiplies the arm/climb/land waits (20/60/90 s of wall time; default 1).

**Symptom.** 8 drones: `[smoke] TIMEOUT waiting for rel_alt >= 1.5 m`, `rel_alt=0.99`, then `There was an error running python`.
The last line is only `python.sh` reporting a non-zero exit code, not a crash. The drones were flying; the sim runs at 0.09× real time
so a 60 s wall budget is ~5 s of simulated climb. With `--patience 5` instances 0 and 7 pass.
**Rule:** any wall-clock timeout in a test must be scaled by RTF now (0.3–0.5 for one drone).

---

<a id="m15"></a>
## M15 — `./bisg debug mavlink` needs pymavlink on the host
**Note, pre-existing.** `ModuleNotFoundError: No module named 'pymavlink'` — the host has no ROS and optionally no pymavlink
(`docs/setup.md`). Use the container instead:
`docker exec bisg-sim /isaac-sim/python.sh -c '…mavutil.mavlink_connection("udpin:0.0.0.0:14550")…'`.

---

<a id="m16"></a>
## M16 — Warnings that look like errors but are not
**Note.**
* `[carb.omniclient.plugin] OmniHub … Hub failed to launch … Trying to reconnect` — dozens of lines in the first ~10 s of every boot; no Nucleus/Hub is used.
* `[pegasus…ardupilot_mavlink_backend] Initialized with vehicle_id=0 … ardupilot_dir=/isaac-sim/ardupilot` — Pegasus 6 builds an ArduPilot backend config at import; unused for PX4.
* `PhysX warning: TriangleMesh: triangles are too big` — warehouse collision meshes.
* `GLFW initialization failed`, `failed to open the default display`, `CPU performance profile is set to powersave`, `IOMMU is enabled` — headless/host notes.
* `pxr.Semantics is deprecated`, `Failed to add '/isaac-sim/Documents'` — Isaac internals.
* `Waiting for first hearbeat` (sic) — Pegasus's MAVLink backend before PX4 connects; ends within a second.

---

<a id="m17"></a>
## M17 — The `6.0.0` image reports `6.0.0-rc.59+release.41464…`
**Note.** `/isaac-sim/VERSION` in `nvcr.io/nvidia/isaac-sim:6.0.0` (digest `sha256:68735a60…`, 21 GB) contains a release-candidate string.
Not a problem observed, but record the digest if you need to reproduce the exact runtime.

---

<a id="m18"></a>
## M18 — The Pegasus pin lives only on a GitHub pull-request ref
**Open.** `docker/sim/PegasusSimulator` points at `fcb99c0`, reachable upstream only as `refs/pull/144/head` (not a branch or tag).
A fresh `git submodule update --init` fetches by SHA, which GitHub allows today; if the PR is force-pushed, closed with a rewritten
history, or the author deletes the fork, the SHA can become unfetchable. Our own clone and every built image keep it.
`scripts/fetch_sources.sh` handles the `pr144-fcb99c0` pin. **Mitigation:** push the submodule's `local` branch to a fork, or
re-pin when Pegasus tags a 6.0 release. The PR is also based on `dev_6.0.1` two commits behind its tip (new drone model, simplified world); we did not take those.

---

<a id="m19"></a>
## M19 — Semantics that changed under the launcher (read before editing it)
**Note.**
* `PegasusInterface.load_environment()` schedules an `asyncio` future that only runs during `simulation_app.update()`; the launcher calls
  the synchronous `load_asset(usd, "/World/layout")` instead so physics never starts before the world exists.
* There is no `world.reset()`. Physics initialises on `timeline.play()`; vehicles create their `RigidPrim` in a `SIMULATION_STARTED`
  callback, so anything that needs the body (`vehicle.apply_force`, IMU sensors) must wait for that. `zed_rig` only creates prims, which is fine.
* `PegasusInterface()._world_settings` still drives `physics_dt`; `rendering_dt` now means the **app loop step** (`RenderingManager.set_dt`), one
  `update()` per `rendering_dt` and ~`rendering_dt / physics_dt` physics sub-steps inside it (the 5.1 "render every Nth step" code is gone).
* `omni.isaac.core.objects.GroundPlane` / `FixedCuboid` → `isaacsim.core.experimental.objects.{GroundPlane,Cube}` (+ `UsdPhysics.CollisionAPI.Apply` for a static collider).
* The experimental APIs take **wxyz** quaternions and `wp.array`/ndarray shapes `(N, …)`; ROS messages need `float64` (the PR already casts).
* `isaacsim.core.utils.viewports.set_camera_view` → `ViewportManager.set_camera_view("/OmniverseKit_Persp", eye=…, target=…)`.

---

<a id="m20"></a>
## M20 — `docs/performance.md` is 5.1-era
**Note / Open.** Its tables (boot 186 s, 317 steps/s, rtf 1.27, warehouse numbers) were measured on 5.1 with the iteration-based
metric (bugs.md B4, now fixed) and a different loop. Redo them on 6.0; the new baselines are in `archive/docs/migration-report.md` §4–§7.
