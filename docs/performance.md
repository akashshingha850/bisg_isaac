# Performance and profiling

Upstream reference: **NVIDIA, "Simulation Performance Optimization Handbook"** —
<https://docs.isaacsim.omniverse.nvidia.com/6.0.0/reference_material/sim_performance_optimization_handbook.html>
(written for 6.0; the settings below were checked against Isaac Sim 5.1.0 and the 6.0.0 migration, see
`migration-report.md`; Isaac 6.0 changes the loop cadence, so re-measure before trusting the old tables).

Why this matters here: the RTX 2080 Ti has 11 GB, which is below Isaac's recommended spec (risk R1 in
`plan.md`), and boot time sets the floor for the regression suite (Phase 8). Tune with numbers, not guesses:
measure, change one knob, measure again, and write the result into the table at the bottom.

## Measuring

| What | How |
|---|---|
| Real-time factor and step rate | `./bisg debug perf` — reads the `[launch] perf … steps/s rtf=…` heartbeat the launcher prints every `app.heartbeat_steps` steps. `rtf >= 1.0` means the sim keeps up with wall clock. |
| VRAM and GPU load | `./bisg debug gpu` (host `nvidia-smi` + the same inside the container) |
| Boot time | `./bisg up …` prints seconds to `[launch] sim ready` and to PX4 "Ready for takeoff" |
| Where the time goes at startup | `./bisg debug kitlog` — extension startup lines carry cumulative timestamps |
| Deep profiling | Tracy, per the handbook. Not wired up here; add it when a specific frame-time question needs it. |

## Knobs we expose

All live in the `perf:` block of a scenario file (`sim/configs/*.yaml`) and are passed to `SimulationApp`
or straight to Kit. Only non-null keys are sent, so an empty block keeps Isaac's defaults.

| Key | Effect | When to use |
|---|---|---|
| `disable_viewport_updates` | Skips viewport rendering work. Auto-enabled when headless. | Always, headless |
| `limit_cpu_threads` | Caps Kit threads (default 32; handbook suggests 16–32). Set to 16 here — the host has 12 cores. | Always |
| `skip_material_loading` | `--/app/renderer/skipMaterialLoading=true`. Large load-time win, scene is untextured. | Physics-only tests; **never** for camera/perception work |
| `width` / `height` | Render resolution. Directly drives VRAM per camera. | Swarm runs (Phase 6), risk R1 |
| `renderer` | `RaytracedLighting` (RTX real-time, default) or `PathTracing`. | Keep real-time; path tracing is for offline stills |
| `sync_loads` | Pause rendering until assets finish loading (default true). | Leave alone unless chasing pop-in |
| `active_gpu` / `multi_gpu` / `max_gpu_count` | GPU selection. Handbook: "add as many GPUs as cameras being rendered, but no more"; GPU physics uses one GPU only. | Single-GPU host: leave null |
| `min_frame_rate` | `--/persistent/simulation/minFrameRate`: PhysX catch-up clamp. Higher (60) favours frame rate, lower (15) favours sim-time accuracy. | If physics stalls under load |
| `physx_threads` | `--/persistent/physics/numThreads` (default 8, 0 = main thread). | Contention with PX4/ROS on 12 cores |
| `extra_args` | Raw Kit args for anything not listed. | One-off experiments |

Rates live in the `world:` block: `physics_dt`, `rendering_dt`, `physics_device` (`cpu` or `cuda`).
**`physics_dt` also sets the PX4 sensor and MAVLink rate** (Pegasus default 1/250 s), so changing it changes
flight behaviour, not just speed. Leave it null unless a scenario documents why.

Scene-side wins from the handbook that we will need later: primitive colliders beat convex meshes beat
complex meshes; scenegraph instancing for repeated geometry; disable self-collisions on articulations;
Mesh Merge Tool for imported assets. These apply to the Phase 4 vehicle and site assets — record decisions
in `sim/assets/README.md` when that work starts.

## Profiles

| Config | Purpose |
|---|---|
| `sim/configs/single_iris.yaml` | Default GUI/perception scenario. Simple Room, ZED + third-eye views; 60 Hz physics / 20 Hz rendering to target real-time operation. |
| `sim/configs/headless_fast.yaml` | Regression/flight-stack profile: headless, no render, no materials, tiny grid world, 640×360. Not valid for perception work. |

```
./bisg up headless -c sim/configs/headless_fast.yaml
./bisg debug perf
```

## Isaac Sim 6.0 (migration, 2026-10-02) — read this before the tables below

The tables below were measured on **Isaac Sim 5.1** with an iteration-counting metric and the old render-every-Nth-step loop. On 6.0 the loop is
one `simulation_app.update()` per `world.rendering_dt` with ~`rendering_dt/physics_dt` physics sub-steps inside it, and `perf … steps/s` now counts real
physics steps (= the `/clock` rate). Current numbers (RTX 4500 Ada, headless, PX4 v1.17.0):

| Scenario | Warm boot to `sim ready` | Physics Hz (nominal 250) | RTF |
|---|---:|---:|---:|
| `single_iris_nozed` | 30 s | 119 | 0.48 |
| `single_iris_vio` (ZED HD720) | 33 s | 83 | 0.33 |
| `headless_fast` | 30 s | 132–137 | 0.53 |
| 2 / 4 / 8 drones, no ZED | 30–34 s | 73 / 41 / 23 | 0.29 / 0.17 / 0.09 |

The bottleneck is Pegasus's per-step Python, not rendering (`migration-errors.md` M8); `app.profile_s: 45` in a scenario prints a cProfile of the loop.
First boot (or after `./bisg debug clean-cache`) takes ~190 s while RTX shaders compile into the `isaac-cache-kit` volume (M6). `app.render: false` no longer
skips the app update (M9). Full comparison with 5.1: `migration-report.md` §7.

## Measurements on this workstation (RTX 2080 Ti, 12 cores, driver 580.178.04)

Measured 2026-09-13 after the render-cadence fix (see below). Boot times are with warm asset and shader
caches; the very first warehouse run was ~249 s because it downloaded the assets.

| Profile | To `sim ready` | To PX4 ready | Steps/s | RTF | Notes |
|---|---|---|---|---|---|
| `single_iris.yaml` headless, no view | ~189 s | ~192 s | 186 | 0.74 | warehouse, textured |
| `single_iris.yaml` headless + `--both` views | ~200 s | ~205 s | 117 | 0.47 | browser view at 1 fps + WebRTC server |
| `headless_fast.yaml` headless, no view | ~186 s | ~192 s | 317 | **1.27** | grid world, `render: false` — the profile for tests |
| `single_iris.yaml` GUI | ~250 s | ~260 s | not measured | | window on `:0` |

`rtf >= 1.0` means the sim keeps up with wall clock. The 250 Hz full-rate ZED setup did not reach this
on the measured Isaac Sim 6 host, so `single_iris.yaml` now targets real time with 60 Hz physics and
20 Hz rendering. This lowers the PX4 sensor/MAVLink update rate; confirm flight stability for the task
before relying on this profile for control-fidelity work. `./bisg debug perf` reports the actual RTF.

### Render cadence (fixed 2026-09-13)

The launcher used to call `world.step(render=True)` on every physics step, which draws
`rendering_dt / physics_dt` times more often than the world settings ask for — 4x at the Pegasus
defaults (physics 1/250 s, rendering 1/60 s) — and starves the physics loop. Measured cost on the
warehouse scene:

| | before | after |
|---|---|---|
| headless, no view | 79 steps/s, rtf 0.32 | 186 steps/s, rtf 0.74 |
| headless + browser view | 29 steps/s, rtf 0.12 | 117 steps/s, rtf 0.47 |

`sim/launcher/launch.py` now renders one frame per `round(rendering_dt / physics_dt)` physics steps and
logs the cadence at startup (`[launch] render cadence: 1 frame per 4 physics steps`). To trade picture
for speed, raise `world.rendering_dt` in the scenario (0.1 = 10 fps); to trade the other way, lower it.

Re-measure after any pin change (`config/bisg.conf`) and keep this table current; Phase 8 uses it as the CI budget.
