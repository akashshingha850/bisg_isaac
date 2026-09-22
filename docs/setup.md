# Workstation setup

One command after the host prerequisites: `./bisg setup`. Everything else lives in containers.

## Host prerequisites (once)

| Need | Why | Check |
|---|---|---|
| Ubuntu 24.04, NVIDIA driver ≥ 570 | Isaac Sim 5.1 | `nvidia-smi` |
| Docker Engine ≥ 24 with Compose v2 | all runtime | `docker compose version` |
| nvidia-container-toolkit, `nvidia` runtime registered | GPU in containers | `docker info \| grep -i runtimes` |
| X11 session (or XWayland) and `xhost` | GUI profile only | `echo $DISPLAY`, `xhost` |
| ≥ 60 GB free on the Docker root disk | Isaac image 15 GB + sim image 18 GB + caches | `docker info \| grep "Docker Root Dir"` |
| Python 3 + `pymavlink` on the host (optional) | smoke test and `debug mavlink` from the host; otherwise they run inside the sim container | `python3 -c "import pymavlink"` |
| `third_party/PegasusSimulator` submodule initialized | `bisg/sim` builds **from** this submodule, not a fresh clone (`docker/sim/Dockerfile`) | `git submodule update --init third_party/PegasusSimulator` |

Install the toolkit if missing (Ubuntu):
```
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker
```
Optional but recommended for DDS with big messages later: `sudo sysctl -w net.core.rmem_max=10485760` (persist in `/etc/sysctl.d/`).

## `./bisg setup`

What it does, in order (idempotent, safe to re-run):

1. `scripts/check_env.sh` — driver, runtime, compose, X11, disk, ports. Stops on `[FAIL]`.
2. Writes `docker/.env` from `docker/.env.example` (this machine's `DISPLAY` and any local overrides). Project-wide settings live in `config/bisg.conf`; see [configuration.md](configuration.md), `./bisg config` and `./bisg config --edit`.
3. `xhost +local:` so the container user `isaac-sim` (uid 1234) may open a window.
4. Pulls `nvcr.io/nvidia/isaac-sim:5.1.0` (public, ~15 GB) and `ros:jazzy-ros-base`.
5. `--third-party`: clones Pegasus v5.1.0 and zed-ros2-wrapper v5.4.1 into `third_party/` if not already there (normally these are git submodules — `git submodule update --init --recursive` — this flag is a fallback for a fresh checkout). `bisg/sim` builds **from** the PegasusSimulator submodule; zed-ros2-wrapper is used directly by `docker/zed/build.sh`. See `third_party/README.md` for making local edits that survive an upstream update.
6. Builds `bisg/sim:5.1.0` (PX4 v1.17.0 SITL compiled in-image, Pegasus built from the submodule and installed into Isaac's Python) and `bisg/ros:jazzy` (MAVROS 2.15.1). `--arm64` also cross-builds `bisg/ros:arm64` for the Jetson (qemu, ~15 min). `--rebuild` forces `--no-cache`.
7. Sanity: PX4 binary + Pegasus present in the sim image, MAVROS + geoid data in the ros image.

Timing on this workstation: pull ~3 min, sim build ~4 min, ros build ~2 min, arm64 ~15 min.

## First run

```
./bisg config             # check the resolved settings first (mode, scenario, view, endpoints)
./bisg up                 # view from SIM_VIEW; force with ./bisg up gui | headless (boot ~4–5 min)
./bisg up web             # headless + a browser view on :8899 (docs/remote-access.md)
./bisg smoke              # arm → 2 m → land, exit 0
./bisg mavros up && ./bisg mavros state     # connected: true
./bisg down
```

## ZED SDK image (Phase 5, needs the camera or the Jetson)

```
./bisg setup --third-party
docker/zed/build.sh desktop     # x86_64: stereolabs/zed:5.4.1-devel-cuda12.8-ubuntu24.04 + wrapper (Jazzy)
docker/zed/build.sh jetson      # run on the Orin NX (JetPack 7.2 = L4T r38.4)
```
Details: `docker/zed/README.md`, `docs/hardware.md`.

## Jetson Orin NX (Phase 5 preview)

1. JetPack 7.2 flashed; `docker` + `nvidia-container-toolkit` from JetPack; `docker compose` v2.
2. Get `bisg/ros:arm64` onto the device: `docker save bisg/ros:arm64 | ssh jetson docker load`, or push to a registry.
3. Build `bisg/zed:l4t-r38` on the device (`docker/zed/build.sh jetson`).
4. udev rule for the Pixracer → `/dev/px4`; `deploy/jetson/compose.yaml --profile jetson up -d`.

## Uninstall / reset

`./bisg debug clean-cache` drops shader caches (next boot slower). `./bisg debug clean-all` removes every `bisg_*` volume including downloaded Isaac assets. Images: `docker rmi bisg/sim:5.1.0 bisg/ros:jazzy bisg/ros:arm64`.
