# bisg_isaac — Isaac Sim digital twin for a PX4 / ZED drone swarm

Digital twin of a real drone fleet: **Isaac Sim + Pegasus Simulator + PX4** on the
simulation side, **Jetson + Pixracer (PX4) + ZED camera** on the hardware side, with
**ROS 2 Jazzy + MAVROS** as the one interface both sides share. Everything runs in
Docker so a sim drone and a real drone are driven by the *same* containers and code.

Status: single-drone twin runs end to end on Isaac Sim 6.0 (PX4 SITL, MAVROS, the real ZED SDK on a ZED Mini twin). Swarm, real-drone bench and assets are later phases (`docs/roadmap.md`).

Hardware target: Jetson Orin NX (JetPack 7.2) + Pixracer + ZED Mini. Single-drone twin first; the swarm is a later migration.

## Read in this order

| Doc | What it answers |
|---|---|
| [docs/plan.md](docs/plan.md) | What we are building, the architecture, version pins, risks |
| [docs/roadmap.md](docs/roadmap.md) | The phases, what each delivers, and the exit test for each |
| [docs/todo.md](docs/todo.md) | The live checklist. Start here when you sit down to work |
| [docs/skills.md](docs/skills.md) | Competencies you need per phase + the Claude Code skills in `.claude/skills/` |
| [docs/interface-contract.md](docs/interface-contract.md) | The ROS 2 topic / frame / namespace contract sim and hardware must both obey |
| [docs/zed-stack.md](docs/zed-stack.md) | **the ZED Mini stack**: every SDK module switched in `docker/zed/zed.yaml`, the PX4 bridge, QGC video |
| [docs/zed-sdk-sim.md](docs/zed-sdk-sim.md) | the real ZED SDK + `zed_wrapper` running against the sim's ZED Mini twin (`ZED_SOURCE=sdk`) |
| [docs/hardware.md](docs/hardware.md) | Jetson + Pixracer + ZED wiring, PX4 params, bench checklist |
| [docs/setup.md](docs/setup.md) | Host prerequisites and `./bisg setup` |
| [docs/runbook-sim.md](docs/runbook-sim.md) | Run, test and operate the sim stack (`./bisg` cheat sheet) |
| [docs/debugging.md](docs/debugging.md) | Symptom → command table, PX4 shell, logs, resets |
| [docs/performance.md](docs/performance.md) | Tuning and profiling: the `perf:` knobs, measured boot/FPS numbers, NVIDIA handbook |
| [docs/decisions/](docs/decisions/) | Architecture decision records (why MAVROS, why Docker, Jazzy, which versions) |

## Repo layout

```
bisg_isaac/
├── bisg                  # operator CLI (setup / up / zed / mavros / smoke / debug ...)      scripts/*.sh
├── config/               # bisg.conf (project settings) · px4/ (PX4 parameter files, SITL and Pixracer)
├── docker/               # compose.yaml + one folder per image with its config and code: sim/ (configs/ scenarios, PegasusSimulator submodule), ros/ (mavros_lean.yaml, ros2_ws/), zed/ (zed.yaml + zed_stack/: YAML compiler, PX4 bridge, QGC video)
├── sim/                  # Pegasus launcher code, worlds, assets (scenario YAMLs: docker/sim/configs/)
├── docker/ros/ros2_ws/src/          # ROS 2 packages shared by sim and hardware (bisg_vehicle: vio_mock)
├── tests/                # smoke / flight / ZED tests (+ unit/ for host-side tests)
├── docs/                 # plan, roadmap, todo, contract, ADRs, runbooks
├── archive/              # finished experiments and superseded docs (PX4-link study, 5.1->6.0 migration)
```

## Quick start (Phase 1 foundation)

```
./bisg setup                 # host check, config, pulls, builds (docs/setup.md)
./bisg config                # settings and where each value comes from (docs/configuration.md)
./bisg up                    # window or not per SIM_VIEW; force with: ./bisg up gui | headless
./bisg up web                # headless + a browser view (VS Code tunnel friendly); ./bisg view prints URLs
./bisg smoke                 # arm, 2 m takeoff, land → exit 0
./bisg mavros up && ./bisg mavros state    # connected: true
./bisg down

ZED_SOURCE=sdk ./bisg all headless && ./bisg zed up && ./bisg zed status   # the real ZED SDK + wrapper + PX4 bridge on the sim's ZED Mini twin
./bisg zed plan              # what the ZED does, from docker/zed/zed.yaml;  ./bisg zed set object_detection.enabled=true
```
`./bisg help` lists everything (status, logs, shell, debug report/px4/topics, …).
Details: [docs/setup.md](docs/setup.md), [docs/configuration.md](docs/configuration.md), [docs/remote-access.md](docs/remote-access.md), [docs/runbook-sim.md](docs/runbook-sim.md), [docs/debugging.md](docs/debugging.md).
Settings: `config/bisg.conf` + `docker/.env` (this machine). Pins: Isaac Sim 6.0.0, PX4 v1.17.0, Pegasus PR #144 (Isaac 6 port), ZED SDK 5.4.1 (+ `zed-isaac-sim` v5.2.1 for the SDK-in-sim path). Migration from 5.1: `archive/docs/migration-report.md`.
