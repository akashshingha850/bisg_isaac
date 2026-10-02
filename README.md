# bisg_isaac — Isaac Sim digital twin for a PX4 / ZED drone swarm

Digital twin of a real drone fleet: **Isaac Sim + Pegasus Simulator + PX4** on the
simulation side, **Jetson + Pixracer (PX4) + ZED camera** on the hardware side, with
**ROS 2 Jazzy + MAVROS** as the one interface both sides share. Everything runs in
Docker so a sim drone and a real drone are driven by the *same* containers and code.

Status: **Phase 0 — documentation and repo skeleton.** Fresh start; nothing runs yet.

Hardware target: Jetson Orin NX (JetPack 7.2) + Pixracer + ZED Mini. Single-drone twin first; the swarm is a later migration.

## Read in this order

| Doc | What it answers |
|---|---|
| [docs/plan.md](docs/plan.md) | What we are building, the architecture, version pins, risks |
| [docs/roadmap.md](docs/roadmap.md) | The phases, what each delivers, and the exit test for each |
| [docs/todo.md](docs/todo.md) | The live checklist. Start here when you sit down to work |
| [docs/skills.md](docs/skills.md) | Competencies you need per phase + the Claude Code skills in `.claude/skills/` |
| [docs/interface-contract.md](docs/interface-contract.md) | The ROS 2 topic / frame / namespace contract sim and hardware must both obey |
| [docs/hardware.md](docs/hardware.md) | Jetson + Pixracer + ZED wiring, PX4 params, bench checklist |
| [docs/setup.md](docs/setup.md) | Host prerequisites and `./bisg setup` |
| [docs/runbook-sim.md](docs/runbook-sim.md) | Run, test and operate the sim stack (`./bisg` cheat sheet) |
| [docs/debugging.md](docs/debugging.md) | Symptom → command table, PX4 shell, logs, resets |
| [docs/performance.md](docs/performance.md) | Tuning and profiling: the `perf:` knobs, measured boot/FPS numbers, NVIDIA handbook |
| [docs/decisions/](docs/decisions/) | Architecture decision records (why MAVROS, why Docker, Jazzy, which versions) |

## Repo layout (grows with the phases)

```
bisg_isaac/
├── docker/            # one compose.yaml with profiles; each image's Dockerfile in its own folder (sim/, ros/) [Phase 1]
├── sim/               # Pegasus launcher, YAML scenario configs, worlds, sim-side nodes [Phase 1]
├── ros2_ws/src/       # ROS 2 packages shared by sim and hardware                     [Phase 2]
│   ├── bisg_msgs/     #   fleet / vehicle-state messages
│   ├── bisg_vehicle/  #   per-drone: MAVROS offboard controller, VIO relay, health
│   ├── bisg_fleet/    #   swarm: fleet manager, task allocation, formation
│   └── bisg_bringup/  #   launch files: sim_drone / real_drone / fleet
├── sim/assets/        # vehicle USD models (bisg_quad), site worlds                    [Phase 4]
├── deploy/            # Jetson compose profiles, udev rules, PX4 param files          [Phase 5]
├── tests/             # headless regression scenarios                                [Phase 8]
├── third_party/       # git submodules: PegasusSimulator, PX4-Autopilot (pinned)
├── config/            # bisg.conf — one settings file (view, scenario, endpoints, pins, links)
├── bisg               # operator CLI: setup / config / up / wait / smoke / mavros / debug ...
├── scripts/           # setup.sh, launch.sh, debug.sh, check_env.sh, pull/fetch helpers
└── docs/
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
```
`./bisg help` lists everything (status, logs, shell, debug report/px4/topics, …).
Details: [docs/setup.md](docs/setup.md), [docs/configuration.md](docs/configuration.md), [docs/remote-access.md](docs/remote-access.md), [docs/runbook-sim.md](docs/runbook-sim.md), [docs/debugging.md](docs/debugging.md).
Settings: `config/bisg.conf` + `docker/.env` (this machine). Pins: Isaac Sim 6.0.0, PX4 v1.17.0, Pegasus PR #144 (Isaac 6 port), ZED SDK 5.4.1. Migration from 5.1: `docs/migration-report.md`.
