# Isaac Sim 5.1 → 6.0 migration report

Date: 2026-10-02 · Branch `migrate/isaac-6.0` · Rollback tag `isaac-5.1-baseline` (local only, **not pushed**) ·
Plan followed: [`migrate.md`](migrate.md) · Every error hit along the way: [`migration-errors.md`](migration-errors.md)

## 1. Verdict

> Detailed 5.1 vs 6.0 numbers, with and without the ZED rig, measured in one matched run: [`isaac-5.1-vs-6.0.md`](isaac-5.1-vs-6.0.md).

The stack runs on **Isaac Sim 6.0.0** with the same ROS 2 interface as before. The three tests that gate the twin all
pass and match the 5.1 baseline: arm/takeoff/land smoke, GPS-denied VIO flight (position error 0.05–0.07 m vs 0.06–0.07 m
before) and the ZED depth-box check (front face −0.2 mm, identical). Topic names, frames and namespaces are unchanged;
MAVROS, `vio_mock` and the ROS container needed **no** changes.

Two regressions you should know about before relying on it:

| | 5.1 baseline | 6.0 | Status |
|---|---|---|---|
| Simulation speed, with ZED rig | **1.18×** | **0.33×** | **Open** — M8: Pegasus's per-step Python |
| Simulation speed, no ZED rig (re-measured on both) | **1.97×** (`/clock` 491 Hz) | **0.48×** (119 Hz) | **Open** — ~4× slower |
| Cold boot to `sim ready` | ~100 s warm | 190 s cold / **30 s warm** | Fixed — M6 (shader cache was not persisted) |

Not done: Isaac ROS 4.6 (not part of this repo's plan, §10), a real QGroundControl / WebRTC client session, and the
`vehicle reset` acceptance item (§5). A second test round the same day (§4.4) closed position hold, the native GUI window and the 2-drone ZED rig. Nothing was pushed to origin.

## 2. Final version pins

| Component | Before | After | Notes |
|---|---|---|---|
| Isaac Sim | 5.1.0 | **6.0.0** (Python 3.12) | image reports `6.0.0-rc.59+release…` internally (M17) |
| Pegasus | v5.1.0 | **PR #144 head `fcb99c0`** | no release tag exists; fetched with `refs/pull/144/head`; submodule branch `local` |
| PX4 | v1.17.0 | **v1.17.0 (kept)** | v1.16.0 also validated (§4); see decision D2 |
| ROS 2 / DDS | Jazzy / Cyclone | unchanged | bundled bridge moved to `exts/isaacsim.ros2.core/jazzy` |
| MAVROS, ZED SDK, base ROS image | — | unchanged | |

## 3. What was done, in order

Follows the staged order of `migrate.md` §5 (one thing changes at a time).

1. **Baseline frozen** on 5.1 (boot, smoke, topics, VIO flight, depth box). Committed the uncommitted ZED work first so the
   tag points at a reproducible state: `4a43502` = tag `isaac-5.1-baseline`.
2. **Runtime + Pegasus.** Pins to 6.0.0, `docker/sim/Dockerfile` for 6.0, Pegasus submodule moved to PR #144, launcher
   ported off `World`. First PX4 target was v1.16.0 as `migrate.md` asks.
3. **Stage A — no sensors** (`single_iris_nozed`): boot, PX4, smoke, MAVROS, `/clock`, battery.
4. **Stage B — ZED rig + VIO** (`single_iris_vio`): rig ported, VIO flight, depth box, image/depth delivery (low-res scenario).
5. **Views:** `web` and WebRTC (broken on 6.0, ported), full-UI render with ZED preview + depth overlay.
6. **Multi-drone:** 2, 4, 8 drones (sim level only).
7. **PX4 v1.17.0** re-tested on 6.0 (`migrate.md` §28 says "only after 1.16 passes"). Passed → pin kept.
8. **Performance work:** boot-time root cause (cache volume), throughput profiling.
9. **Final regression** on the final image, plus TF tree, `./bisg check`, `headless_fast`.

Commits on the branch: `4a43502` (baseline = tag), `15c7c35` (6.0 container, Pegasus, PX4, launcher port), `fefb4b9` (ZED rig, views,
boot/perf fixes, scenarios) and a docs commit. `migrate.md` §44 asks for a finer history; the work was done interactively and is grouped by stage instead.

## 4. Test results

Headless, same host (RTX 4500 Ada, driver 580.178.04). "Sim Hz" = wall rate ÷ (`/clock` Hz ÷ 250), i.e. rate in simulated time.

### 4.1 Gate tests

| Test | 5.1 baseline | 6.0 + PX4 1.16.0 | 6.0 + PX4 1.17.0 (final) |
|---|---|---|---|
| `./bisg smoke` (arm → ~1.6 m → land → disarm) | PASS 1.67 m | PASS 1.56 m | PASS 1.57 m |
| `tests/vio_flight.py` max \|est − truth\| x / y / z (bound 0.3 m) | 0.058 / 0.071 / 0.028 | 0.058 / 0.065 / 0.019 | 0.047 / 0.067 / 0.019 |
| `tests/zed_depth_box.py` front face (bound 30 mm) | −0.2 mm | −0.2 mm | −0.2 mm |
| GCS stream on udp 14550 | not run | heartbeat, firmware 1.16.0 | firmware 1.17.0 |
| 2 / 4 / 8 drones, smoke per instance | — | 2: both PASS; 4: all four PASS | 4: all four PASS (re-run, full logs); 8: instances 0 and 7 PASS with `--patience 5` |

### 4.2 Interface and sensor rates (ZED + MAVROS, `single_iris_vio`)

| Topic | 5.1 (sim Hz) | 6.0 (sim Hz) | Contract |
|---|---|---|---|
| `zed/zed_node/imu/data` | 250.7 | ~234 | 200 |
| `zed/zed_node/left/camera_info` | 18.4 | 29.4 | 15–30 |
| `zed/zed_node/{left,right}/image_rect_color`, `depth_registered` | not measurable (B2) | **31** (320×180) | 15–30 |
| `mavros/local_position/pose` | 30.5 | 29.5 | — |
| `mavros/imu/data` | 50.5 | 48.3 | — |
| `zed/zed_node/odom` (`vio_mock`) | — | ~245 | 30–60 (over-rate, pre-existing) |

HD720 images/depth still do not reach a subscriber on this host: that is the unrelated `net.core.rmem_max` limit (bugs.md B2).
Image delivery on 6.0 was therefore proven at 320×180 (`single_iris_vio_lowres`): rgb8 / 32FC1, K = 177.7 px (84° HFOV), correct frame ids.
Topic list is identical to 5.1; `/drone_1/tf_static` carries all 6 ZED frames
(`base_link → zed_camera_link → {left,right}_camera_frame → optical`, `zed_imu_link`).

### 4.3 Views

| View | Result |
|---|---|
| `web` (still frames, TCP 8899) | works: page 200, 1.8 MB PNG of the warehouse, Iris and test box |
| `webrtc` | server starts, TCP 49100 listening. Broken at first (M4), fixed. **No real client connected** (needs the NVIDIA app + UDP 47998) |
| ZED preview window + depth overlay (`omni.ui`) | created without errors under the full UI; not looked at on a screen |
| native `gui` window on `:0` | works (see §4.4) |

### 4.4 Second test round (same day)

| Test | Result |
|---|---|
| **Position hold** (new `tests/hold_position.py`, `single_iris_nozed`, GPS): take off to 2 m, hold 20 sim s in AUTO.LOITER | PASS — max drift 0.032 m horizontal, 0.026 m vertical (bound 0.3 m) |
| **Native GUI window** (`DISPLAY=:0 ./bisg up gui -c single_iris_vio_lowres`) | PASS — "Isaac Sim Python 6.0.0" window 1440×900, viewport renders, ZED left\|depth preview docked, live point-cloud overlay on the box (screenshot checked). First GUI boot 195 s (separate shader set). `docker/.env` has a stale `DISPLAY=:1`; the shell's `:0` wins |
| **ZED rig on 2 drones** (`two_iris_vio_lowres`) | PASS — `/drone_1/zed/…` and `/drone_2/zed/…` each at ~29 Hz sim (images, depth, camera_info) and ~230–240 Hz IMU; 12 static transforms, each namespace uses only its own `drone_N/` frames, no collisions |
| **5.1 vs 6.0 speed without the ZED rig**, same scenario, 5.1 run from a git worktree of the baseline tag | 5.1: `/clock` **491 Hz** (rtf 1.97), smoke PASS, 2.9 GB VRAM, 325 % CPU, boot 73 s · 6.0: 119 Hz (rtf 0.48) |

Still untested: vehicle reset (the launcher has no reset hook), real QGroundControl, real WebRTC client.

## 5. Acceptance criteria (`migrate.md` §41)

Ticked in `migrate.md` with the evidence next to each item. Summary of what is **not** ticked:

| Item | Why |
|---|---|
| vehicle reset works | not tested |
| QGroundControl connects | MAVLink stream on 14550 verified with pymavlink; QGC is not installed here |
| all five Isaac ROS items | out of scope (§10 item 8) |

Rotor geometry (§20) was verified indirectly: the 6.0 flights are as stable and as accurate as the 5.1 ones, so thrust, roll, pitch
and yaw directions behave the same. No per-rotor transform dump was made.

## 6. Capacity (`migrate.md` §40)

Scenarios `single_iris_nozed`, `two_/four_/eight_iris_nozed`, headless, no cameras. "Physics Hz" = physics steps per wall second
(`/clock` rate; nominal sim rate is 250 Hz).

| Drones | Physics Hz | RTF | GPU VRAM | GPU util | Container CPU | Sensor FPS |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 119 | 0.48 | 2.1 GB | 24 % | — | n/a |
| 2 | 73 | 0.29 | 2.1 GB | 12 % | 266 % | n/a |
| 4 | 41 | 0.17 | 2.4 GB | 9 % | 252 % | n/a |
| 8 | 23 | 0.09 | 2.4 GB | 6 % | 231 % | n/a |

* 2 and 4 drones: every instance armed, took off and landed independently (smoke on each). Sys IDs 1…4, PX4 instances 0…3,
  tcp 4560+i / udp 14540+i, namespaces `/drone_1…`. MAVROS for drone 2 connects (155 topics under `/drone_2/mavros`).
* 8 drones: boots (PX4 ready after 73 s warm), steady 23 Hz. Instances 0 and 7 fly independently, but only with the new
  `tests/smoke_takeoff.py --patience 5`: its fixed wall-clock waits (60 s climb) expire at 0.09× real time (M14). The other six
  instances were not individually flown.
* The capacity limit is **CPU, not GPU**: total drone-steps per second is 119, 146, 164, 184 for 1, 2, 4, 8 drones, i.e. roughly
  constant. One Python thread running every vehicle's callbacks is the bottleneck, so VRAM and GPU are nowhere near saturated.
  With one 1280×720 ZED pair per drone, VRAM will matter again (3.2 GB for one drone with a ZED).
* The `migrate.md` text talks about an RTX 5090; this workstation has an RTX 4500 Ada (24 GB).

## 7. Performance analysis

**Boot (fixed).** Every boot spent ~140 s recompiling RTX shaders (Kit log: `Waiting for RtPso async group` 60 s, then `ray
tracing shader compilation … finished after 82 seconds`). Isaac 6.0 writes the writable shader cache to `/isaac-sim/kit/cache`,
which compose did not mount (5.1 used `~/.cache`). New volume `isaac-cache-kit`. Result: 192 s (first boot) → **30 s** (`sim ready`),
39 s to PX4 ready; `single_iris` with the HD720 ZED boots in 73 s. The launcher now prints `boot +Ns: <phase>` lines.

**Throughput (open).** 6.0 simulates 0.33× real time with the ZED rig vs 1.18× on 5.1. Rendering is not the cause: halving the render
rate (60 → 30 Hz) only moved `/clock` from 85 to 97 Hz. A 45 s cProfile of the main loop (`app.profile_s: 45` in a scenario) shows the
time is in Pegasus's 6.0 vehicle code, run once per physics step per vehicle:

| Where (cumulative, 3166 steps) | Share |
|---|---|
| `RigidPrim.apply_forces_and_torques_at_position` — 6 calls/step (4 rotors, body torque, drag) | ~27 % |
| warp array construction (called from all of the above) | ~18 % |
| propeller visual `set_dof_velocities` — 4 calls/step, each with a prim lookup (`get_all_matching_child_prims`) | ~8–10 % |
| `get_velocities`/`get_world_poses` + IMU/magnetometer/state conversions | ~10 % |

Candidate fixes (none applied — they change flight-dynamics code, so they need the gate tests): apply the four rotor forces and the
torque in one batched call; update propeller visuals only on rendered frames or skip them headless; compute drag without a prim call.
These are local commits on the submodule's `local` branch (`third_party/README.md`).

`docs/performance.md` still holds the 5.1 numbers; they are iteration-based (bugs.md B4, now fixed) and must be re-measured.
`headless_fast` (the test profile) now runs at 0.53× instead of 1.27× because `app.render: false` can no longer skip the app update (M9).

## 8. Code and config changes

| Area | Change |
|---|---|
| `config/bisg.conf`, `scripts/_common.sh`, `docker/compose.yaml`, `docker/.env.example` | pins: Isaac 6.0.0, Pegasus `pr144-fcb99c0`, PX4 stays v1.17.0 |
| `docker/sim/Dockerfile` | 6.0 base; ROS libs path `isaacsim.ros2.core/jazzy/lib`; fetch NuttX tags (needed for PX4 1.16); create `/isaac-sim/kit/cache` |
| `docker/compose.yaml` | volume `isaac-cache-kit` (M6); healthcheck disabled (M5) |
| `third_party/PegasusSimulator` | submodule now at PR #144 head `fcb99c0` on branch `local` |
| `scripts/fetch_third_party.sh` | can clone a `pr<N>-<sha>` Pegasus pin |
| `sim/launcher/launch.py` | no `World`: `PegasusInterface.initialize_world`, `RenderingManager.set_dt`, `SimulationManager` callbacks/clock, `simulation_app.update()` loop counting physics steps; sync world load; experimental `Cube`/`GroundPlane`; `ViewportManager`; `omni.kit.livestream.app` with failure checks; boot-phase timing; `app.profile_s` |
| `sim/launcher/zed_rig.py` | `read_camera_info` from `isaacsim.ros2.core`; IMU on `isaacsim.sensors.experimental.physics`; all image/depth/info rate gates set from the render dt |
| `sim/launcher/zed_depth.py` | `enable_extension` import |
| new scenarios | `single_iris_nozed`, `single_iris_vio_lowres`, `two_/four_/eight_iris_nozed` |
| Docs / skills | `CLAUDE.md`, `plan.md` §4–5, ADR-002/003/004/005, README, setup, runbook, remote-access, `bugs.md` (B4, B9 fixed), `todo.md`, skills `sim-launch`, `sim-regression`, `px4-sitl`, `zed-contract` |

## 9. Decisions and deviations from `migrate.md`

* **D1 — Pegasus at PR head, not a tag.** The doc asks for the Isaac-6 branch; the PR is built on `dev_6.0.1`, which has two newer
  commits (new drone model, simplified world) that were left out because the PR was tested without them. Risk: the SHA is only
  reachable through `refs/pull/144/head` upstream; if the PR is rewritten, a fresh `submodule update` can fail (M19).
* **D2 — PX4 pin stays v1.17.0.** The doc's table says 1.16.0, but ADR-003 requires SITL = Pixracer firmware, and 1.17.0 passes every
  test on 6.0. Both were run in the doc's order (1.16 first, then 1.17). v1.16.0 is the documented fallback.
* **D3 — Used `simulation_app.update()` instead of manual stepping.** It is what the Pegasus PR's own examples do and keeps its
  callbacks working. Cost: no physics-only mode (M9).
* **D4 — Did not run `docker compose build --no-cache`.** Only the layers that changed were rebuilt.
* **D5 — Did not `git push origin isaac-5.1-baseline`.** Pushing is outward-facing and was not requested; the tag is local.
* **D6 — Multi-drone tested without Phase 6 tooling.** CLAUDE.md says swarm work waits for Phase 6; only the launcher's existing
  `vehicles:` list was used (no fleet manager, no per-drone services).
* **D7 — ZED sensor classes left on deprecated APIs** (`isaacsim.sensors.camera.Camera`, `isaacsim.core.utils`) because they import
  and work in 6.0 and `migrate.md` §31 says not to migrate the ZED layer and Pegasus together. Only the parts that broke were ported (M12).
* Doc errors found in `migrate.md` itself (callback argument order, RTX 5090) are listed in M13.

## 10. Recommended next steps

1. **Fix the Pegasus per-step cost (M8)** — biggest practical win; gate with the three tests.
2. Mirror Pegasus PR #144 into a fork or tag so the pin cannot disappear (M19).
3. Push the baseline tag and branch (your call), then merge.
4. Re-measure `docs/performance.md`; decide what `headless_fast` should mean now (M9).
5. Run once with a real QGroundControl, a WebRTC client and the `gui` window.
6. Finish the sensor port to `isaacsim.sensors.experimental.*` and `isaacsim.ros2.core/nodes` before looking at Isaac Sim 6.1 (M12).
7. Re-test whether the 59x NVIDIA driver crash from 5.1 still exists on 6.0; until then keep the guard in `scripts/check_env.sh`.
8. Isaac ROS: needs its own plan (it is not in `plan.md`); Isaac ROS 4.6 on Jazzy is the compatible line, 5.x needs ROS Lyrical.

## 11. Reproduce / roll back

```bash
git checkout migrate/isaac-6.0 && git submodule update --init third_party/PegasusSimulator
./bisg setup --rebuild                       # pulls isaac-sim:6.0.0, builds bisg/sim:6.0.0 (PX4 1.17.0)
./bisg up headless -c single_iris_nozed && ./bisg smoke
SIM_SCENARIO=single_iris_vio ./bisg all headless
docker exec bisg-ros python3 /workspace/tests/vio_flight.py --drone 1
docker exec bisg-ros python3 /workspace/tests/zed_depth_box.py

git checkout isaac-5.1-baseline              # rollback (also: git submodule update, ./bisg setup)
docker tag bisg/sim:6.0.0-px4-1.16 …         # PX4 1.16 image from the migration is still on this machine
```

The 5.1 image (`bisg/sim:5.1.0`, `nvcr.io/nvidia/isaac-sim:5.1.0`) is still present locally.
Raw evidence (boot logs, topic rates, flight logs, profile, 4/8-drone runs) is in `logs/migration/` — git-ignored, local only.
