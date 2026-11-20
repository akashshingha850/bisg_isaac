---
name: px4-sitl
description: PX4 SITL inside the sim container — instance/port/sys-id math, startup scripts, param files, commander and EKF2 status checks, offboard/failsafe rejections. Use when PX4 won't connect to Pegasus or MAVROS, or a mode/arming request is refused.
---

# px4-sitl

## Instance math (verify against pinned tag, see plan.md §6)
| vehicle_id i | sim TCP | MAVROS fcu_url | MAV_SYS_ID | namespace |
|---|---|---|---|---|
| 0 | 4560 | `udp://:14540@127.0.0.1:14580` | 1 | /drone_1 |
| 1 | 4561 | `udp://:14541@127.0.0.1:14581` | 2 | /drone_2 |
| i | 4560+i | `udp://:$((14540+i))@127.0.0.1:$((14580+i))` | i+1 | /drone_(i+1) |

Source of truth: `ROMFS/px4fmu_common/init.d-posix/px4-rc.mavlink` at the pinned tag, and
Pegasus `px4_mavlink_backend.py` (connection port = base 4560 + vehicle_id, `-i` = vehicle_id).

## Tag notes (Isaac Sim 6.0 migration)
- Both v1.16.0 and v1.17.0 fly under Isaac 6.0 + Pegasus PR #144 with the same port math, `gazebo-classic_iris` airframe and params file. Pin = v1.17.0 (must equal the Pixracer firmware, ADR-003).
- Building **v1.16.0** in the image needs `git -C platforms/nuttx/NuttX/nuttx fetch --depth 1 --tags` (shallow submodules have no `nuttx-X.Y.Z` tag → `IndexError` in `px_update_git_header.py`); the Dockerfile already does it.
- Check the running firmware without QGC: send `MAV_CMD_REQUEST_MESSAGE` 148 (AUTOPILOT_VERSION) to udp 14550 — `flight_sw_version` 0x011100ff = 1.17.0.

## Startup
- Pegasus autolaunches `build/px4_sitl_default/bin/px4 -i <i> -d <rootfs> -s etc/init.d-posix/rcS` with `PX4_SIM_MODEL`.
- Order matters: PX4 waits for the simulator TCP connection; Pegasus connects once the vehicle prim is spawned. Both sides must agree on `4560+i`.
- Lockstep: off by default in our config (render FPS is not stable and Isaac 6.0 runs at ~0.5-0.6x real time with the ZED twin). If PX4 seems frozen, check `PX4_SIM_SPEED_FACTOR` / lockstep setting.

## Params
- The scenario's `px4_params:` list picks files from `docker/sim/px4/`: the vehicle file first (`iris` | `raptor`), then overlays (`ekf2_vision`, `ekf2_flow_range`, `ekf2_vio_flow_range`); a later file wins. Default (`docker/sim/sim.yaml`): `[raptor, ekf2_vio_flow_range]` = GPS-denied on baro height + LW20 + ZED VIO + PMW3901 flow, no GPS/mag (`docs/range-flow.md`). After changing an EKF2 overlay, run `./bisg vio check`.
- Inspect live without QGC: `./bisg debug px4 commander status`, `./bisg debug px4 ekf2 status`, `./bisg debug px4 param show EKF2_EV*` (runs the `px4-<module>` client inside the sim container).

## Common rejections
- "Offboard rejected": setpoint stream < 2 Hz for > 0.5 s before the mode switch; stream ≥ 10 Hz first.
- "Arming denied: no local position" → EKF2 has no valid pose (GPS off and no EV). Check `ekf2 status` and `EKF2_EV_CTRL`.
- "Preflight fail: mag" indoors → `EKF2_MAG_TYPE` none when yaw comes from EV.
- GPS-denied (the default): AUTO.TAKEOFF / LOITER / RTL refuse and AUTO.LAND flies toward lat/lon 0,0 (no global position). Take off and land in OFFBOARD: `tests/mav_offboard.py` (raw MAVLink) or `tests/vio_flight.py` (MAVROS).
- Heartbeat but no telemetry in MAVROS → `MAV_1_MODE` / stream rates, or wrong `tgt_system`.

## Logs
- `.ulg` in `rootfs/log/<date>/`. Review EKF innovations, EV delay, mode changes. Never commit `.ulg`.
