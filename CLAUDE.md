# bisg_isaac — project instructions for Claude Code

Isaac Sim + Pegasus + PX4 digital twin of a Jetson Orin NX / Pixracer / ZED Mini drone (swarm later), ROS 2 Jazzy in containers + MAVROS, Docker-first.
Read `docs/plan.md` for architecture, `docs/todo.md` for what is in progress. Update `docs/todo.md` when you finish work.

## Ground rules
- This is a **fresh start**. Do not pull code from `~/isaacsim` or `~/swarm_ws` (earlier, abandoned attempts). Ideas may be re-implemented; files are not copied.
- Build **gradually, phase by phase** (`docs/roadmap.md`). Do not start a later phase unless asked; do not widen scope.
- Sim and hardware obey `docs/interface-contract.md`. A new topic, frame or namespace is added there first.
- PX4 <-> ROS 2 bridge is **MAVROS** (ADR-001), not uXRCE-DDS.
- Every runtime component has a Dockerfile / compose service (ADR-002). Host installs are for debugging only.
- Version pins live in `docs/plan.md` §4 and are applied from the pins block of `config/bisg.conf`. Change a pin only with an ADR update.
- Settings layering (`docs/configuration.md`): `config/bisg.conf` = every project default, in topic comment blocks (view, sim, ros, drone, pins, links); `docker/.env` = this machine only; scenario YAML = world/vehicle content. A new knob goes in the matching block + `conf_default` in `scripts/_common.sh`, never hard-coded in a script. One key lives in exactly one place.
- One key, `SIM_VIEW`, decides window + remote view: `gui|headless|web|webrtc|both|auto`, combined with `+` (`gui+webrtc`); `./bisg up <value>` overrides it per run. `web` (still frames on one TCP port) survives a VS Code/SSH tunnel; `webrtc` needs UDP 47998, so LAN or VPN only (`docs/remote-access.md`).
- Containers are ROS 2 **Jazzy** (ADR-005). Host ROS Humble is debug-only; never make a script depend on it (the host moves to 24.04 later, `docs/plan.md` §12).
- Order: single-drone twin → assets/models → one real drone → swarm. Swarm work waits for Phase 6.
- Never `git submodule update --remote` in `third_party/` without checking the pin.

## Host facts (this workstation)
- Ubuntu 22.04 (24.04 migration planned), ROS 2 Humble on host (debug only), RTX 2080 Ti 11 GB, NVIDIA driver 580, Docker 29 with nvidia runtime, 62 GB RAM, 12 cores, 6 TB free on `/media/ubuntu/ssd`.
- Isaac Sim 5.1 is known to run on this GPU. It boots slowly (2–5 min cold). Use `timeout` and `PYTHONUNBUFFERED=1` when driving it from scripts; prefer headless for tests.

## Skills
Project skills in `.claude/skills/` (sim-launch, px4-sitl, mavros-ops, zed-contract, swarm-spawn, jetson-deploy, sim-regression). See `docs/skills.md`.
