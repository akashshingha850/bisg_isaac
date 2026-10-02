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
- Containers are ROS 2 **Jazzy** (ADR-005), Ubuntu 24.04 base. The host has no ROS install at all; never make a script depend on host ROS.
- Order: single-drone twin → assets/models → one real drone → swarm. Swarm work waits for Phase 6.
- Never `git submodule update --remote` in `third_party/` without checking the pin.

- **Perception backend is switchable** (ADR-006, `docs/perception.md`, skill `perception`): `PERCEPTION_BACKEND=mock|isaac_ros|ros2` in `config/bisg.conf`. `mock` (vio_mock) is the default and what the tests assume; `isaac_ros` = Isaac ROS 4.6 (release-4 = Jazzy; release-5 is Lyrical-only) in the `bisg/perception` image, `ros2` = CPU rtabmap + stereo_image_proc. Isaac Sim's ROS 2 *bridge* is the sim's transport for all of them, not an alternative. Backends publish `perception/odom` + `perception/disparity`; `vio_relay` maps them onto the contract. `./bisg perception up|down|status|bench|report`. Never two vision sources into MAVROS. HD720 images need the `rmem_max` sysctl (bugs.md B2); without it use `single_iris_vio_midres` (448×252).

## Host facts (this workstation)
- Ubuntu 24.04.5 LTS, no ROS install on host, RTX 4500 Ada Generation 24 GB VRAM, NVIDIA driver **580.178.04**, Docker 29.1.3, 125 GB RAM, 24 cores. Driver must stay on the 580 branch — the 595.x/R590 branch this GPU shipped with segfaults Isaac Sim 5.1's RTX renderer (`docs/plan.md` §12); `scripts/check_env.sh` hard-fails on any 59x driver.
- Bulk storage lives on `/opt` (1.9 TB ext4, ~1.4 TB free) — **not** `/media/ubuntu/ssd`, which does not exist on this box. `ARCHIVE_DIR` and any large-artifact paths must point under `/opt`.
- GPU access from containers works: user `bisg` is in the `docker` group and the NVIDIA Container Toolkit + `nvidia` runtime are installed and verified (`./bisg check`, `docker run --gpus all`).
- Isaac Sim 5.1 is known to run on this GPU. It boots slowly (~2 min warm, up to 5 min cold). Use `timeout` and `PYTHONUNBUFFERED=1` when driving it from scripts; prefer headless for tests.

## Skills
Project skills in `.claude/skills/` (sim-launch, px4-sitl, mavros-ops, zed-contract, swarm-spawn, jetson-deploy, sim-regression, perception). See `docs/skills.md`.
