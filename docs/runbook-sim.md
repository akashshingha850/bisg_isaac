# Runbook — simulation stack (Phase 1)

All commands from the repo root. The `./bisg` CLI wraps everything below (`./bisg help`); the raw
`docker compose` forms are kept here for when you need them. First time: `./bisg setup` (docs/setup.md).

## Cheat sheet (`./bisg`)
```
./bisg config [--edit]                            # settings — config/bisg.conf + docker/.env
./bisg view                                       # watch a headless run (browser URL / WebRTC client)
./bisg up [gui|headless|web|webrtc|both] [-c <scenario>]   ./bisg wait  ./bisg status  ./bisg logs -f
./bisg smoke            ./bisg mavros up|state|logs|down     ./bisg ros shell     ./bisg shell
./bisg px4-bridge plan|up|down|status|logs|params|build [mavros|mavsdk|xrce|none]   # the PX4 bridge: one service, PX4_BRIDGE in config/bisg.conf (docs/px4-bridge.md)
./bisg all headless     # sim + mavros + ros, wait, print mavros state
./bisg down | stop | restart
./bisg debug report|px4 <cmd>|mavlink|topics|hz T|echo T|perf|kitlog|ports|gpu|versions|dds|clean-cache
```

## Preflight
```
./bisg check                    # = scripts/check_env.sh: driver, nvidia runtime, compose, X11, disk, ports
xhost +local:                   # GUI profile only (container runs as uid 1234 `isaac-sim`, not root); ./bisg up does this
```

## Build (once, ~30–60 min: 20 GB Isaac pull + PX4 SITL build)
```
scripts/pull_images.sh --save   # optional: archive the Isaac image to the SSD
docker compose -f docker/compose.yaml build sim
docker compose -f docker/compose.yaml build ros
```

## Run
```
./bisg up                       # per SIM_VIEW in config/bisg.conf (auto = window when an X server is present)
./bisg up headless -c headless_fast              # override view + scenario for this run
```
Raw compose (no `config/bisg.conf`, only `docker/.env` + compose defaults):
```
docker compose -f docker/compose.yaml --profile sim up            # window on $DISPLAY
docker compose -f docker/compose.yaml --profile sim-headless up   # no window
SIM_CONFIG=/workspace/docker/sim/configs/<other>.yaml docker compose -f docker/compose.yaml --profile sim up
```
### Watching a headless run
```
./bisg up web                   # browser view on TCP 8899 — works through a VS Code / SSH tunnel
./bisg up webrtc                # interactive WebRTC — needs UDP 47998, so LAN or VPN only
./bisg up gui+webrtc            # local window and a remote viewer at the same time
./bisg view                     # URLs / client address for whatever is running
```
`web` serves still frames (`SIM_WEB_INTERVAL`, default 1 s) that any browser can show, including the
VS Code Simple Browser after forwarding port 8899. `webrtc` is the full interactive Isaac UI in the
Isaac Sim WebRTC Streaming Client (TCP 49100 + UDP 47998, both host ports); there is no browser URL for
it. Either forces rendering on, so do not use them for timing runs. Set the default in `SIM_VIEW`.
Details: [remote-access.md](remote-access.md).

Ready markers: launcher prints `[launch] sim ready`; PX4 prints `INFO  [commander] Ready for takeoff!`.
Boot ~4–5 min headless or GUI (measured; see below). QGroundControl on the host connects on UDP 14550 automatically.

## Smoke test (sim running)
```
python3 tests/smoke_takeoff.py --instance 0 --alt 2 --timeout 300      # host has pymavlink
docker compose -f docker/compose.yaml exec sim python3 tests/smoke_takeoff.py   # or inside the container
```

## MAVROS (Phase 2 preview)
```
docker compose -f docker/compose.yaml --profile ros up -d
docker compose -f docker/compose.yaml exec ros bash -lc "ros2 topic echo /drone_1/mavros/state --once"
```

## Stop / clean
```
docker compose -f docker/compose.yaml --profile sim down
pgrep -a px4 || true                       # no SITL should survive on the host
docker volume rm bisg_isaac-cache-main     # shader cache reset (last resort; slow next boot)
```

## Where things are inside the sim container
| What | Path |
|---|---|
| Isaac Sim | `/isaac-sim` (`python.sh`, `isaac-sim.sh`); image is Ubuntu 24.04, user `isaac-sim` uid 1234, no sudo |
| PX4 (tag `PX4_TAG`) | `/opt/PX4-Autopilot`, SITL binary `build/px4_sitl_default/bin/px4`, logs under the temp rootfs of each instance |
| Pegasus (tag `PEGASUS_TAG`) | `/opt/PegasusSimulator/extensions/pegasus.simulator` (editable install, `config/configs.yaml`) |
| Repo | `/workspace` (bind mount) |
| Kit text log (`kit_*.log`) | volume `isaac-kit-logs` → `/isaac-sim/kit/logs/Kit/Isaac-Sim Python/<version>/` (`./bisg debug kitlog`); `isaac-logs` only holds structured telemetry json |

## Verified on this workstation (2026-09-12)
- Headless boot to `[launch] sim ready`: ~4.3 min cold and warm alike (Kit startup + warehouse USD load dominate, not the shader cache); PX4 "Ready for takeoff" ~10 s later. `docker compose stop`: 1.4 s, exit 0, no stray PX4.
- `tests/smoke_takeoff.py`: PASS. MAVROS: `connected: true`, 155 topics, pose ~14 Hz, IMU ~24 Hz (default PX4 onboard stream rates).

## Real ZED SDK in the sim (`ZED_SOURCE=sdk`)

```
./bisg zed ext-build && ./bisg zed image          # once (docs/setup.md)
ZED_SOURCE=sdk ./bisg up headless && ./bisg wait  # the sim streams the ZED Mini twin
./bisg zed up && ./bisg zed check                 # real zed_wrapper + SDK checks; ./bisg zed status | logs | down
```
Start the wrapper after the sim and keep both alive together: the SDK connects once per sim run (B18), so after restarting either, restart both.
Full explanation, differences from the real drone and troubleshooting: `docs/zed-sdk-sim.md`.

## Common failures
- **`docker compose stop` takes the full grace period and exits 137**: the launcher must be PID 1. `/isaac-sim/python.sh` is a bash wrapper that runs Python as a child and ignores SIGTERM; `docker/sim/entrypoint.sh` therefore replicates its environment and `exec`s `/isaac-sim/kit/python/bin/python3` directly. Do not switch the entrypoint back to `python.sh`.
- **`rmw_create_node: failed to create domain` / "failed to increase socket receive buffer"**: a CycloneDDS profile asked for a buffer larger than `net.core.rmem_max`. Our `docker/cyclonedds.xml` sets no minimum; optionally `sudo sysctl -w net.core.rmem_max=10485760` for large point clouds later.
- **ZED `camera_info` publishes but the `left/color/rect/image` / `depth_registered` images never arrive**: host `net.core.rmem_max` too small for 2.7 MB images — see `docs/setup.md` (sysctl, required).
- **GPS-denied: estimate diverges / height runs away once airborne**: something ROS-side is on the wall clock. PX4 SITL runs on sim time; check `/clock` is published, `use_sim_time` on MAVROS plugin nodes and vio_mock (`docs/interface-contract.md` /clock row, mavros-ops skill), and that PX4's `vehicle_visual_odometry.timestamp_sample` differs from `timestamp`.
- **GPS-denied: arming refused in Hold / "global position invalid"**: expected with EV in FRD — arm and fly in OFFBOARD (`tests/vio_flight.py`).
- **`ros2 topic list` shows nothing although MAVROS runs**: stale ROS 2 daemon in the `ros` container; `ros2 daemon stop` then retry (or `--no-daemon`).
- **No window**: `DISPLAY` wrong, `xhost +local:` not run, Wayland without XWayland. Try the headless profile to separate GPU issues from display issues.
- **`Failed to create any GPU devices`**: nvidia runtime not active or driver < 570.
- **PX4 never says ready / Pegasus waits on TCP 4560**: a stale `px4` process holds the port (`pgrep -a px4`), or `px4.airframe` not found in the ROMFS (check `ls /opt/PX4-Autopilot/ROMFS/px4fmu_common/init.d-posix/airframes | grep iris`).
- **Assets download slowly on first world load**: Isaac fetches Nucleus assets from the cloud; the `isaac-data`/`isaac-cache-main` volumes keep them.
- **Smoke test times out on GLOBAL_POSITION_INT**: EKF has no GPS yet (Pegasus GPS sensor starts with the vehicle); wait longer or check the `[px4]` status lines.
