# Isaac Sim 5.1 vs 6.0 — detailed comparison, with and without the ZED rig

Measured 2026-10-02 on this workstation (RTX 4500 Ada 24 GB, driver 580.178.04, 24 cores, 125 GB RAM), headless, **PX4 v1.17.0 in both**
(5.1: Pegasus v5.1.0; 6.0: Pegasus PR #144). Same method for all four runs: boot, 60 s settle on the ground, then 15 s `ros2 topic hz`
windows, 5 GPU samples, 3 `docker stats` samples, then the flight tests. One run per configuration (n = 1): treat differences under ~5 % as noise.
Background and everything else about the migration: [`migration-report.md`](migration-report.md), [`migration-errors.md`](migration-errors.md).

| | Scenario | ZED rig |
|---|---|---|
| **no ZED** | `single_iris_nozed` (GPS, no camera, no ROS graph) + MAVROS | none |
| **ZED** | `single_iris_vio` (GPS-denied, `vio_mock`) + MAVROS | stereo + depth + IMU + point cloud at **HD720** (the production setting) |

## 1. One-page answer

| | 5.1 no ZED | 6.0 no ZED | 5.1 ZED | 6.0 ZED |
|---|---:|---:|---:|---:|
| **Speed vs real time (RTF)** | **2.08×** | 0.47× | **1.16×** | 0.32× |
| Real-time capable (RTF ≥ 1)? | yes | **no** | yes | **no** |
| Warm boot → `sim ready` / PX4 ready | 74 s / 77 s | **33 s** / 40 s | 100 s / 103 s | **33 s** / 45 s |
| GPU memory used by the sim | 2.4 GB | **1.7 GB** | 3.4 GB | **2.5 GB** |
| Container RAM | 7.1 GiB | **4.2 GiB** | 8.5 GiB | **5.0 GiB** |
| Gate test passes | smoke ✔ | smoke ✔ | VIO flight ✔, depth box ✔ | VIO flight ✔, depth box ✔ |

* **For anything that must keep up with the wall clock (live demo, hardware-in-the-loop, interactive flying): 5.1.** It runs faster than real
  time with and without the ZED rig; 6.0 does not in either case.
* **For unattended / offline tests (regression, CI, data generation): both work.** 6.0 boots about 3× faster and uses ~30 % less GPU and ~40 % less
  RAM, but a test that takes 43 s on 5.1 takes 98 s on 6.0.
* **Accuracy and interface are identical.** Same topics, same frames, same flight accuracy, same depth accuracy.
* The whole speed gap is Pegasus's per-step Python (6.0 port), not Isaac Sim's renderer. It is fixable; see §6.

## 2. Speed

`/clock` is published once per physics step (nominal 250 Hz), so its rate is the simulation speed. RTF = `/clock` Hz ÷ 250.

| | 5.1 no ZED | 6.0 no ZED | 5.1 ZED | 6.0 ZED |
|---|---:|---:|---:|---:|
| `/clock` (physics steps per wall second) | 519 | 117 | 291 | 79 |
| RTF | 2.08 | 0.47 | 1.16 | 0.32 |
| Wall time per physics step | 1.93 ms | 8.53 ms | 3.44 ms | 12.66 ms |
| 6.0 ÷ 5.1 (slowdown) | | **4.4×** | | **3.7×** |
| Cost of adding the ZED rig (RTF drop) | | | −44 % | −33 % |
| Cost of the ZED rig per physics step | | | +1.5 ms | +4.1 ms |
| Wall time, `./bisg smoke` (arm → 2 m → land) | 15 s | 40 s | | |
| Wall time, `vio_flight.py` (takeoff, 3 m square, land) | | | 43 s | 98 s |

Reading it:
* Without the rig, 6.0 spends **4.4× more wall time per physics step**. With the rig, 3.7×.
* The ZED rig is *relatively* cheaper on 6.0 only because the base cost is already so high; in absolute terms it costs 2.7× more per step on 6.0
  (+4.1 ms vs +1.5 ms), which is the camera render + replicator + point-cloud work being a little heavier in 6.0.
* Real-world test time scales with the slowdown, not with simulated time: the same simulated flight took 2.3× (VIO) and 2.7× (smoke) longer on 6.0
  (the ratio is below 3.7–4.4× because some waits in the tests are fixed).
* Earlier launcher numbers (`perf … rtf=`) are not comparable: on 5.1 they counted loop iterations (bugs.md B4, fixed). All numbers here come from `/clock`.

### Multi-drone (6.0 only measured; no ZED)

| Drones | Physics Hz | RTF | GPU memory | Container CPU |
|---:|---:|---:|---:|---:|
| 1 | 117 | 0.47 | 1.7 GB | ~290 % |
| 2 | 73 | 0.29 | 2.1 GB | 266 % |
| 4 | 41 | 0.17 | 2.4 GB | 252 % |
| 8 | 23 | 0.09 | 2.4 GB | 231 % |

Total drone-steps per second is almost constant (117 → 184), i.e. one Python thread runs every vehicle. 5.1 was **not** measured with several
drones; with 1.93 ms per step per drone its ceiling should be roughly 4× higher, but that is an extrapolation, not a measurement.

## 3. Boot time

| | 5.1 no ZED | 6.0 no ZED | 5.1 ZED | 6.0 ZED |
|---|---:|---:|---:|---:|
| `./bisg up` / `all` wall time | 77 s | 40 s | 106 s | 48 s |
| `[launch] sim ready` | 74 s | 33 s | 100 s | 33 s |
| PX4 "Ready for takeoff" | 77 s | 40 s | 103 s | 45 s |

* Cold first boot on 6.0 is ~190 s (RTX shader compile), then 30 s warm once the new `isaac-cache-kit` volume is populated (error M6).
* On 5.1 the Kit start-up and warehouse load take 74–100 s; on 6.0 with warm shaders the same steps take 33 s (the 5.1 split was not profiled).
* A GUI boot on 6.0 needs its own shader set (195 s the first time).

## 4. Resources

| | 5.1 no ZED | 6.0 no ZED | 5.1 ZED | 6.0 ZED |
|---|---:|---:|---:|---:|
| GPU memory in use (whole GPU) | 2.87 GB | 2.12 GB | 3.84 GB | 2.93 GB |
| … minus idle desktop (~0.43 GB) = the sim | 2.4 GB | 1.7 GB | 3.4 GB | 2.5 GB |
| GPU utilisation (mean of 5) | 8 % | 23 % | 53 % | 37 % |
| Container CPU (mean of 3, 100 % = 1 core) | 353 % | 293 % | 385 % | 296 % |
| Container RAM | 7.1 GiB | 4.2 GiB | 8.5 GiB | 5.0 GiB |
| PX4 process CPU | 9.7 % | 4.5 % | 6.0 % | 3.6 % |
| Docker image `bisg/sim` / Isaac base image | 18.5 / 15.1 GB | 24.7 / 21.1 GB | same | same |

* **GPU utilisation is a speed artefact**: 5.1 pushes frames faster so its GPU is busier (53 % vs 37 % with the rig). Neither is close to saturated.
* 6.0 uses less VRAM and RAM for the same scene, but its image is 6 GB larger.
* CPU is the limiting resource on both: ~3–4 cores' worth, dominated by one Python thread.
* PX4 uses less CPU on 6.0 only because the sim feeds it fewer steps per second.

## 5. Interface, sensors and accuracy

All values are in **simulated** time (wall rate ÷ RTF), because wall rates differ with speed.

| Item (contract) | 5.1 no ZED | 6.0 no ZED | 5.1 ZED | 6.0 ZED |
|---|---:|---:|---:|---:|
| `mavros/local_position/pose` | 30.2 Hz | 30.1 Hz | 30.2 Hz | 30.6 Hz |
| `mavros/imu/data` | 50.3 Hz | 48.2 Hz | 51.0 Hz | 50.5 Hz |
| `zed/zed_node/imu/data` (contract 200 Hz) | – | – | 252 Hz | 257 Hz |
| `zed/zed_node/odom` (contract 30–60 Hz, `vio_mock`) | – | – | 255 Hz | 249 Hz |
| `zed/zed_node/left/camera_info` (contract 15–30 Hz) | – | – | 18.2 Hz | **30.7 Hz** |
| ZED images / depth at HD720 | – | – | not delivered | not delivered |
| ZED images / depth at 320×180 | – | – | ~36 Hz¹ | **31 Hz** (rate-gate fix) |
| Topic names, frames, namespaces | identical | identical | identical | identical |
| VIO flight max \|est − truth\| x / y / z (limit 0.3 m) | – | – | 0.051 / 0.062 / 0.030 m | 0.056 / 0.070 / 0.027 m |
| Depth box front-face error (limit 30 mm) | – | – | −0.1 mm | −0.2 mm |
| GPS position hold, 20 sim s drift | – | 0.03 m | not run | – |

¹ From the earlier recorded 5.1 flight (bugs.md B9, now fixed); not re-measured in this run.

* **HD720 images and depth reach no subscriber in either version.** That is the host `net.core.rmem_max` limit (bugs.md B2), independent of Isaac;
  the rendering cost is still paid, so the resource numbers include it. Delivery was proven on 6.0 at 320×180.
* Where 6.0 differs for the better: camera_info and images now run at 31 Hz sim (the 5.1 rig never gated the image writers; error M7).
* `odom` at ~250 Hz is over the contract's 30–60 Hz in both (pre-existing: `vio_mock` publishes per physics step).
* Flight accuracy differences (a few mm) are noise; 6.0 flies the same trajectory with the same estimator behaviour.

## 6. Where the 6.0 slowdown comes from

A 45 s cProfile of the 6.0 main loop (`app.profile_s`, run on the 320×180 ZED scenario; Pegasus's per-step code does not depend on the rig): the time is in Pegasus's vehicle code, once per physics step per vehicle.

| Cost (share of profiled time) | Why |
|---|---|
| `RigidPrim.apply_forces_and_torques_at_position` ≈ 27 % | 6 calls per step (4 rotors, body torque, drag) |
| warp array construction ≈ 18 % | every call builds `wp.array` objects |
| propeller animation `set_dof_velocities` ≈ 8–10 % | 4 calls per step, each with a prim lookup |
| state/IMU/magnetometer conversions ≈ 10 % | `get_velocities`, `get_world_poses`, scipy rotations |

* 5.1 used `dynamic_control` handles (cheap C++ calls); 6.0 has none, so Pegasus moved to `RigidPrim`/`Articulation` objects.
* **Not** the cause: rendering (halving the render rate gave only +14 % speed), ROS publishing, PX4, MAVROS, the ZED rig itself.
* Candidate fixes, none tried: one batched force/torque call per step; propeller animation only on rendered frames (or off headless); no per-call
  prim resolution. The three gate tests catch flight-dynamics regressions. 6.0 needs ≤ 4 ms per physics step (it is 12.7 ms with the rig, 8.5 ms without) to reach 1× real time.

## 7. Everything else that differs

| Topic | 5.1 | 6.0 |
|---|---|---|
| Python in Isaac | 3.11 | 3.12 |
| Physics/world API | `World`, `Robot`, `dynamic_control` | `SimulationManager`, `RenderingManager`, `RigidPrim`/`Articulation` |
| Main loop | `world.step(render=…)`, render every Nth step, can skip rendering | `simulation_app.update()` at the render dt; no physics-only mode (`headless_fast` 1.27× → 0.53×, M9) |
| Pegasus | v5.1.0 (release tag) | PR #144 head `fcb99c0` (no release; only reachable via a PR ref, M18) |
| Bundled ROS 2 libs | `exts/isaacsim.ros2.bridge/jazzy` | `exts/isaacsim.ros2.core/jazzy` (OmniGraph node names unchanged) |
| ZED IMU API | `isaacsim.sensors.physics.IMUSensor` | `isaacsim.sensors.experimental.physics` (old one does not load) |
| WebRTC | `omni.services.livestream.nvcf` | `omni.kit.livestream.app` (server verified, no real client yet) |
| Shader cache | under `~/.cache` | `/isaac-sim/kit/cache` → needs its own volume |
| Base image healthcheck | none | built in, wrong for our launcher → disabled |
| PX4 SITL build | v1.17 builds as-is | v1.16 needs NuttX tags (v1.17 fine in both) |
| Deprecated API still used by us | – | `isaacsim.sensors.camera`, `isaacsim.core.utils`, `isaacsim.ros2.bridge` shim (M12) |
| Views verified | web, WebRTC server, GUI | web ✔, WebRTC server ✔, GUI window with ZED preview + point-cloud overlay ✔ |

## 8. Recommendation

| Need | Use |
|---|---|
| Real-time or near-real-time (live demo, HIL, joystick/QGC flying, anything timed against the wall clock) | **5.1** (`git checkout isaac-5.1-baseline`, image still present) |
| CI / regression / long unattended runs where wall time is cheap | either; **6.0** boots faster and uses less memory |
| Multi-drone sim | **5.1** expected (not measured); 6.0 drops to 0.17× at 4 drones |
| Anything that needs Isaac Sim 6 features or the 6.x line (newer RTX sensors, Isaac ROS 4.6 path) | **6.0** — after the Pegasus fix |
| Long term | **6.0**: it is the supported line; spend the effort on the per-step cost (§6) instead of staying on 5.1 |

## 9. Limits of these measurements

* One run per configuration; 15 s rate windows; resource samples taken on the ground (not in flight).
* Headless only. GUI/stream rendering costs were not compared.
* HD720 image delivery is blocked on this host for both versions, so end-to-end image latency/throughput is untested.
* 5.1 multi-drone and 5.1 `headless_fast` were not re-measured; the 6.0 multi-drone numbers come from the earlier runs (§2).
* The 5.1 side was run from a git worktree of tag `isaac-5.1-baseline` using the existing `bisg/sim:5.1.0` image; the 6.0 side from the migration branch.

Raw data: `logs/migration/compare/` (git-ignored, local): `v51_nozed.txt`, `v51_zed.txt`, `v60_nozed.txt`, `v60_zed.txt`, plus boot, flight and depth logs.
