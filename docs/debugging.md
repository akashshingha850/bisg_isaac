# Debugging

Start with `./bisg status`, then `./bisg debug report` when you need to keep evidence (bundle in `logs/debug_<ts>.tar.gz`, git-ignored).

## Symptom → command

| Symptom | Run | What to look for |
|---|---|---|
| **Any GPU container refuses to start**: `failed to create shim task … failed to initialize NVML: Driver/library version mismatch` | `./bisg check`, or just `./bisg up` (it preflights the GPU and prints the fix) | The host driver was upgraded while the old kernel module is still loaded — compare `cat /sys/module/nvidia/version` (loaded) with `modinfo -F version nvidia` (on disk). Two fixes: **reboot** (`sudo reboot`; also picks up a pending kernel — check `dkms status` lists nvidia for the new kernel first), or **reload the modules without rebooting**, which keeps SSH/VS Code tunnels alive and only ends the local desktop session: `sudo systemctl stop gdm3` → `sudo rmmod nvidia_uvm nvidia_drm nvidia_modeset nvidia && sudo modprobe nvidia` → `nvidia-smi` → `sudo systemctl start gdm3` (optional). If `rmmod` says the module is in use, find the holder with `sudo fuser -v /dev/nvidia*` (NoMachine `nxnode`, a leftover container, another X session) and stop it. `./bisg check` also warns when `/var/run/reboot-required` exists. |
| Nothing happens after `./bisg up` | `./bisg wait` / `./bisg logs -f` | `[launch] sim ready` should appear in ~1 min (~3 min first boot); a `Traceback` means a launcher/Pegasus error |
| Container exits immediately | `./bisg logs`, `./bisg debug kitlog` | `Failed to create any GPU devices` → nvidia runtime; `Permission denied` on `/isaac-sim/...` → cache volume owned by root (recreate volumes) |
| Window never appears (GUI) | `./bisg check`, `echo $DISPLAY`, `xhost` | needs `xhost +local:`; Wayland session needs XWayland or an X11 login (plan.md §12) |
| Very slow boot | `./bisg debug kitlog` | shader compile lines → first boot after `clean-cache`; asset download lines → first world load |
| PX4 never "Ready for takeoff" | `./bisg debug ports`, `./bisg logs \| grep -i px4` | TCP 4560 held by a stale instance; `Unknown model` → `px4.airframe` not in the ROMFS at `PX4_TAG` |
| Smoke test: no heartbeat | `./bisg debug mavlink 14550`, `./bisg debug ports` | another process bound 14540 (only one listener allowed); PX4 not started. The test waits only for a real autopilot heartbeat (sysid not 0), so this failure always means no PX4. |
| Smoke test: arm denied / no position | `./bisg debug px4 commander status`, `./bisg debug px4 ekf2 status` | `no local position` → EKF2 has no GPS/EV; wait longer, check sensors with `px4 sensors status` |
| Offboard rejected (Phase 2) | `./bisg debug px4 commander status` | setpoint stream < 2 Hz before the mode switch (see `mavros-ops` skill) |
| MAVROS not connected | `./bisg mavros logs`, `./bisg debug ports` | `fcu_url` ports vs PX4 instance (14540+i / 14580+i); `tgt_system` = i+1 |
| ZED topics stop mid-run, `zed status` shows the bridge `camera lost`, `bisg-zed-1` Exited | `docker logs bisg-zed-1 2>&1 \| tail -40` | `can't compare times with different time sources` = R9 ([ros-graph.md](ros-graph.md)); the lines starting `[terminate_bt]` are the throw-site stack: copy them into the R9 entry of [todo.md](todo.md). The SDK connects once per sim run (B18): `./bisg down && ./bisg all` to recover |
| `ros2 topic list` empty but nodes run | `./bisg debug dds` | restarts the ros2 daemon; check `ROS_DOMAIN_ID` and `RMW_IMPLEMENTATION` match in every container |
| `rmw_create_node: failed to create domain` | `./bisg debug dds` | CycloneDDS profile asks for more than `net.core.rmem_max`; our profile sets no minimum |
| Stop takes 60 s and exits 137 | `docker inspect -f '{{.Config.Entrypoint}}' bisg-sim` | entrypoint must exec Isaac's python (not `python.sh`), see runbook |
| GPU out of memory | `./bisg debug gpu` | close the GUI sim before headless tests; lower camera resolution (`perf.width/height`, see [performance.md](performance.md)) |
| Sim runs but slower than real time | `./bisg debug perf` | `rtf < 1.0` means PX4 gets stretched sim time. Try `docker/sim/configs/headless_fast.yaml`, lower `perf.width/height`, or `perf.min_frame_rate`. Knobs and the NVIDIA handbook: [performance.md](performance.md) |
| Boot or frame rate needs real tuning | [performance.md](performance.md) | NVIDIA "Simulation Performance Optimization Handbook" plus the knobs we expose in `perf:` |
| `volume "bisg_isaac-…" already exists but was not created by Docker Compose` | — | a `docker run -v` created it first; `docker volume rm <name>` and let `./bisg up` recreate it (these volumes hold caches and logs only) |

## PX4 shell without QGC

`./bisg debug px4 <module> <args>` runs the `px4-<module>` client against the running SITL, e.g.
```
./bisg debug px4 commander status
./bisg debug px4 ekf2 status
./bisg debug px4 param show EKF2_EV*
./bisg debug px4 listener vehicle_local_position
./bisg debug px4 mavlink status
```
Equivalent from a shell: `./bisg shell` then `cd /tmp && /opt/PX4-Autopilot/build/px4_sitl_default/bin/px4-commander status`.

## ROS 2 graph

`./bisg debug topics`, `./bisg debug hz /drone_1/mavros/local_position/pose`, `./bisg debug echo /drone_1/mavros/state`. All run inside the `ros` container (started on demand) so they see the same DDS domain as MAVROS.

## Recording a run (rosbag2)

`./bisg bag` records the live ROS graph to MCAP for later inspection (Foxglove, `ros2 bag play`, PlotJuggler). Topic sets and
the on/off switch live in `docker/ros/bag.yaml`; bags go to `BAG_DIR` (`config/bisg.conf`, default `$ARCHIVE_DIR/bags`).

| Command | What it does |
|---|---|
| `./bisg bag enable` / `disable` | record automatically from the moment the sim is ready (`./bisg up`/`all`/`wait`), every run |
| `./bisg bag start [PROFILE] [NAME]` / `stop` | record now / close the bag (SIGINT, so the MCAP is complete). `down`/`stop` close it too |
| `./bisg bag [status]` · `profiles` · `list` · `info [BAG]` | what is on, the topic sets, the bags, `ros2 bag info` (default: newest) |
| `./bisg bag play BAG` | `ros2 bag play --clock` in bisg-ros (stop the sim first) |

Profiles: `flight` (MAVROS/PX4 state, poses, setpoints, Pegasus ground truth, ZED odometry, zed_stack status, TF, `/rosout`:
~1.4 MB per 13 s sim), `vision` (+ ZED left image compressed + camera_info: ~5 MB/s), `all` (everything except raw images,
depth, clouds). Never record a raw 720p image or depth stream by accident: 3.7 MB a frame (a 40 s test was 4.2 GB). Bag
timestamps are sim time (`use_sim_time: true`); the ZED wrapper's header stamps inside the messages are wall clock.

Gotcha: `./bisg smoke` (and any pymavlink script on `udpin:14540`) shares MAVROS's UDP port, and the kernel hands PX4's
packets to one socket or the other, so MAVROS topics nearly stop while it runs (seen as ~1 Hz `local_position/pose` in a bag
during smoke; full 30 Hz otherwise). Not a recorder problem.

## Host ROS 2 (optional, debugging only)

The stack never needs it, but a native ROS 2 on the desktop is handy: `sudo scripts/install_host_ros.sh` (Jazzy desktop +
CycloneDDS + MCAP + mavros_msgs; `--base` for no GUI), then `source scripts/host_ros_env.sh` in a shell: same
`ROS_DOMAIN_ID` and DDS profile as the containers, so `ros2 topic list`, `rviz2 --ros-args -p use_sim_time:=true` and
`ros2 bag info /opt/docker-archive/bags/...` work directly. ZED custom messages (`zed_msgs`) are not in apt; echo those
from bisg-ros. No script may depend on host ROS (CLAUDE.md).

## Logs

| Log | Where |
|---|---|
| Launcher + PX4 console | `./bisg logs [-f]` (container stdout) |
| Isaac Kit log | volume `bisg_isaac-logs` → `./bisg debug kitlog [-f]` |
| PX4 `.ulg` flight logs | inside the SITL temp rootfs (`/tmp/tmp*/log/` in the sim container); copy out with `docker cp` before `down` |
| MAVROS | `./bisg mavros logs` |
| Performance heartbeat (`steps/s`, `rtf`) | `./bisg debug perf` (from the launcher log) |
| Everything, bundled | `./bisg debug report` |

## Resetting

- `./bisg down` — containers only; caches and downloaded assets stay.
- `./bisg debug clean-cache` — shader/compute caches (safe, next boot ~2 min slower).
- `./bisg debug clean-all` — every `bisg_*` volume (assets re-download on next run).
- `./bisg setup --rebuild` — rebuild images from scratch (after a pin change in `config/bisg.conf`).
