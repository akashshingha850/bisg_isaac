# Debugging

Start with `./bisg status`, then `./bisg debug report` when you need to keep evidence (bundle in `logs/debug_<ts>.tar.gz`, git-ignored).

## Symptom → command

| Symptom | Run | What to look for |
|---|---|---|
| **Any GPU container refuses to start**: `failed to create shim task … failed to initialize NVML: Driver/library version mismatch` | `./bisg check`, or just `./bisg up` (it preflights the GPU and prints the fix) | The host driver was upgraded while the old kernel module is still loaded — compare `cat /sys/module/nvidia/version` (loaded) with `modinfo -F version nvidia` (on disk). Two fixes: **reboot** (`sudo reboot`; also picks up a pending kernel — check `dkms status` lists nvidia for the new kernel first), or **reload the modules without rebooting**, which keeps SSH/VS Code tunnels alive and only ends the local desktop session: `sudo systemctl stop gdm3` → `sudo rmmod nvidia_uvm nvidia_drm nvidia_modeset nvidia && sudo modprobe nvidia` → `nvidia-smi` → `sudo systemctl start gdm3` (optional). If `rmmod` says the module is in use, find the holder with `sudo fuser -v /dev/nvidia*` (NoMachine `nxnode`, a leftover container, another X session) and stop it. `./bisg check` also warns when `/var/run/reboot-required` exists. |
| Nothing happens after `./bisg up` | `./bisg wait` / `./bisg logs -f` | `[launch] sim ready` should appear in ~4–5 min; a `Traceback` means a launcher/Pegasus error |
| Container exits immediately | `./bisg logs`, `./bisg debug kitlog` | `Failed to create any GPU devices` → nvidia runtime; `Permission denied` on `/isaac-sim/...` → cache volume owned by root (recreate volumes) |
| Window never appears (GUI) | `./bisg check`, `echo $DISPLAY`, `xhost` | needs `xhost +local:`; Wayland session needs XWayland or an X11 login (plan.md §12) |
| Very slow boot | `./bisg debug kitlog` | shader compile lines → first boot after `clean-cache`; asset download lines → first world load |
| PX4 never "Ready for takeoff" | `./bisg debug ports`, `./bisg logs \| grep -i px4` | TCP 4560 held by a stale instance; `Unknown model` → `px4.airframe` not in the ROMFS at `PX4_TAG` |
| Smoke test: no heartbeat | `./bisg debug mavlink 14550`, `./bisg debug ports` | another process bound 14540 (only one listener allowed); PX4 not started. The test waits only for a real autopilot heartbeat (sysid not 0), so this failure always means no PX4. |
| Smoke test: arm denied / no position | `./bisg debug px4 commander status`, `./bisg debug px4 ekf2 status` | `no local position` → EKF2 has no GPS/EV; wait longer, check sensors with `px4 sensors status` |
| Offboard rejected (Phase 2) | `./bisg debug px4 commander status` | setpoint stream < 2 Hz before the mode switch (see `mavros-ops` skill) |
| MAVROS not connected | `./bisg mavros logs`, `./bisg debug ports` | `fcu_url` ports vs PX4 instance (14540+i / 14580+i); `tgt_system` = i+1 |
| `ros2 topic list` empty but nodes run | `./bisg debug dds` | restarts the ros2 daemon; check `ROS_DOMAIN_ID` and `RMW_IMPLEMENTATION` match in every container |
| `rmw_create_node: failed to create domain` | `./bisg debug dds` | CycloneDDS profile asks for more than `net.core.rmem_max`; our profile sets no minimum |
| Stop takes 60 s and exits 137 | `docker inspect -f '{{.Config.Entrypoint}}' bisg-sim` | entrypoint must exec Isaac's python (not `python.sh`), see runbook |
| GPU out of memory | `./bisg debug gpu` | close the GUI sim before headless tests; lower camera resolution (`perf.width/height`, see [performance.md](performance.md)) |
| Sim runs but slower than real time | `./bisg debug perf` | `rtf < 1.0` means PX4 gets stretched sim time. Try `sim/configs/headless_fast.yaml`, lower `perf.width/height`, or `perf.min_frame_rate`. Knobs and the NVIDIA handbook: [performance.md](performance.md) |
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
