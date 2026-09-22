# Skills

Two meanings, both covered here:

1. **Competencies** a person needs per phase (so you can plan what to learn or delegate).
2. **Claude Code skills** in `.claude/skills/` — reusable procedures Claude follows for this repo.

## 1. Competencies by phase

| Phase | Must know | Nice to have | Pointers |
|---|---|---|---|
| 0 | Markdown, git submodules, ADR habit | — | this repo |
| 1 | Docker + compose, nvidia-container-toolkit, X11 forwarding; Isaac Sim standalone Python (`SimulationApp`, USD stage basics); Pegasus API (`PegasusInterface`, `Multirotor`, `PX4MavlinkBackend`); PX4 SITL build + `px4-rc.*` startup scripts; QGroundControl | Omniverse Kit extension model, USD composition, Kit settings and Tracy profiling | Isaac Sim docs → "Python scripting / standalone"; [Sim Performance Optimization Handbook](https://docs.isaacsim.omniverse.nvidia.com/6.0.0/reference_material/sim_performance_optimization_handbook.html) (see `docs/performance.md`); Pegasus docs → "Examples"; PX4 dev guide → "Simulation" |
| 2 | ROS 2 Jazzy (packages, launch, QoS, `use_sim_time`), MAVROS 2 (plugins, `set_mode`, `cmd/arming`, setpoint topics, OFFBOARD rules), PX4 flight modes and failsafes, ENU↔NED conventions | pymavlink for quick probes, `ros2 bag` | MAVROS wiki; PX4 "Offboard mode"; REP-103/105 |
| 3 | Camera models/intrinsics, TF trees, stereo geometry, IMU conventions, PX4 EKF2 external-vision fusion (`EKF2_EV_*`, delay, innovations), ZED ROS 2 wrapper topics/frames (ZED Mini) | Isaac replicator/annotators | PX4 "VIO" and "EKF2 tuning"; zed-ros2-wrapper README |
| 4 | Vehicle modelling (mass/inertia measurement, thrust-curve fitting, Pegasus vehicle/thrust-curve classes, USD rigging), 3D reconstruction (3DGS via nerfstudio/Postshot, or photogrammetry), USD asset authoring, collision proxies/physics materials, geo-referencing (WGS84 ↔ local ENU) | NuRec in Isaac 5.x, Blender USD export, CAD export | Pegasus "Create a custom vehicle"; Isaac Sim "NuRec"/3DGS docs |
| 5 | JetPack 7 / L4T r38, Docker on Jetson (`nvidia-container-toolkit`, arm64 images), serial/UART wiring and udev, PX4 param management, ZED SDK 5 on Jetson, flight safety and bench testing | systemd units, `chrony`, `nvpmodel` | PX4 "Companion computer"; Stereolabs Jetson docs |
| 6 | Multi-instance PX4 (ports, sys IDs), ROS 2 namespaces + remapping, simple task allocation, geofencing, GPU/VRAM profiling (`nvidia-smi`, Isaac profiler) | behavior trees (py_trees / BehaviorTree.CPP), formation control basics | PX4 "Multi-vehicle simulation" |
| 7 | WiFi/DDS behaviour, zenoh-bridge-ros2dds, bandwidth budgeting, fleet ops and kill-switch procedures | mesh radios, RTK GPS | zenoh docs; PX4 "Safety" |
| 8 | pytest + JUnit, self-hosted CI runners with GPU, headless Isaac | Grafana for trend plots | GitHub Actions self-hosted docs |

## 2. Claude Code skills (this repo, `.claude/skills/`)

Invoke with `/name` or let Claude pick them by trigger. Each stub documents the procedure and
the checks Claude runs; they are filled with real commands as phases land.

| Skill | Trigger | What it does | Filled in |
|---|---|---|---|
| `sim-launch` | start/stop/restart the sim, GUI vs headless, sim logs, cache reset | run the right compose profile, tail Isaac/PX4 logs, diagnose boot hangs | Phase 1 |
| `px4-sitl` | PX4 SITL won't connect, port/instance math, params, flight-mode/failsafe errors | instance ↔ port table, `px4-rc.mavlink` reading, param file loading, `commander`/`ekf2 status` checks | Phase 1 |
| `mavros-ops` | launch MAVROS for drone N, OFFBOARD refused, frame/QoS questions, timesync | MAVROS launch wrapper, state-machine rules, topic cheat sheet, common rejections | Phase 2 |
| `zed-contract` | add/rename a sensor topic, verify sim vs real ZED, TF tree, intrinsics | edit `interface-contract.md` first, run `check_contract.py`, compare with zed wrapper | Phase 3 |
| `swarm-spawn` | add drone N, generate compose, fleet manager tasks | update scenario YAML, regenerate compose, port/namespace checks, VRAM budget update | Phase 6 |
| `jetson-deploy` | deploy to the Orin NX, flash Pixracer, bench checklist, serial issues | arm64 image pull, compose profile, params push, preflight and post-flight log pull | Phase 5 |
| `sim-regression` | run tests, add a scenario, CI failures | headless scenario runner, JUnit interpretation, flake triage | Phase 8 (basic version from Phase 1) |

Global skills already available that fit this project: `ros2-engineering` (ROS 2 code review,
launch/QoS), `graphify` (codebase questions once code exists), `humanizer` (docs prose).

## 3. Possible future skills (not created yet)

- `twin-assets` — Phase 4: vehicle measurement → USD + Pegasus preset; site capture → USD → collision proxies → geo-reference checklist (collider complexity and instancing rules from `docs/performance.md`).
- `px4-log-review` — pull `.ulg` from SITL/Pixracer, run `flight_review`-style checks on EKF innovations and EV delay.
- `fleet-ops` — Phase 7: pre-mission fleet checklist, kill-switch drill, per-drone health summary.
