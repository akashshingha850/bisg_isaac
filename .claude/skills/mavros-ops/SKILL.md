---
name: mavros-ops
description: Launch and operate MAVROS for drone N (namespace, fcu_url, tgt_system), OFFBOARD state machine, setpoint and odometry topics, QoS, timesync/use_sim_time. Use when writing or debugging anything that talks to PX4 through MAVROS.
---

# mavros-ops

## Launch (ADR-001: one compose service `px4-bridge`, `docs/px4-bridge.md`)
```
./bisg px4-bridge plan | up | status | logs | params     # PX4_BRIDGE in config/bisg.conf picks mavros|mavsdk|xrce|none (MAVROS = default)
./bisg mavros up|down|state|logs [--drone N]             # MAVROS shortcut; ./bisg all starts it with the sim
./bisg drone up                                          # real drone: same service on serial /dev/px4
```
`docker/px4-bridge/entrypoint.sh` runs `ros2 run mavros mavros_node` directly (not `px4.launch`, which cannot set
`use_sim_time`): `__ns:=/drone_<id>`, `tgt_system:=<id>`, `tgt_component:=1`, `fcu_url` from the instance math, one
container per drone and bridge (`bisg-<bridge>-N`). The plugin list is `docker/ros/mavros_lean.yaml`; `MAVROS_PLUGINS=full`
gives the stock list.
Packages: `ros-jazzy-mavros`, `ros-jazzy-mavros-extras` (ADR-005).

## OFFBOARD state machine (what `offboard_controller` does)
1. Wait `mavros/state.connected`.
2. Publish setpoint at 20 Hz (current pose or hover) for ≥ 1 s.
3. `set_mode OFFBOARD` → check `state.mode == "OFFBOARD"` (PX4 ≥ 1.14 reports `OFFBOARD`; verify string at the pin).
4. `cmd/arming true` → check `state.armed`.
5. Takeoff = ramp setpoint z; goto = setpoint in `map` ENU; land = descent velocity in OFFBOARD (`land("offboard")`, the GPS-denied default), or `set_mode AUTO.LAND` only in GPS scenarios (`mission_square --land auto`); wait for disarm.
Each step returns a result object with the ACK/`success` so missions read top to bottom.

## Frames
- Setpoints and `local_position` are ENU, frame `map`. MAVROS converts to NED for PX4.
- `mavros/odometry/out`: ENU pose in `odom`, twist in `base_link` (child), header frame ids exactly `odom` / `base_link`; MAVROS maps them to MAV_FRAME_LOCAL_FRD/… internally. Wrong frame ids = silently ignored or mirrored VIO.

## QoS
- MAVROS publishes sensor topics best-effort → subscribe with `SensorDataQoS` or match with `ros2 topic info -v`.

## Time
- Sim: `use_sim_time:=true` for MAVROS and all our nodes; the launcher publishes `/clock` every physics step.
  PX4 SITL runs on **sim time** (Pegasus stamps HIL_SENSOR, PX4 sets its clock from it), so anything on the wall
  clock drifts at (1 − rtf) s/s and PX4 timesync never converges → vision samples mis-stamped → EV height runaway.
- MAVROS 2.15.1 plugin nodes use `use_global_arguments(false)`: they ignore `-p` **and every `--params-file`**
  (so `px4_config.yaml` plugin sections are dead too, e.g. `timesync_rate` is 0). `docker/ros/mavros_sim_time.py`
  sets `use_sim_time` on them at runtime. Check: `ros2 param get /drone_1/mavros/time use_sim_time`.
- Timesync locked? `./bisg debug px4 listener timesync_status` (observed offset constant) and
  `listener vehicle_visual_odometry`: `timestamp_sample` ≠ `timestamp` (equal = PX4 is stamping on arrival).
- GPS-denied: MAVROS sends EV as `LOCAL_FRD` → EKF2 never yaw-aligns → no global position. Hold/Takeoff/RTL
  refuse; AUTO.LAND engages but flies toward lat/lon 0,0. Fly and land in OFFBOARD; land with a descent
  **velocity** setpoint (the land detector ignores position setpoints). `tests/vio_flight.py` is the reference.
- Real: wall clock; chrony to GCS.

## Quick probes
```
ros2 topic echo /drone_1/mavros/state --once
ros2 topic hz /drone_1/mavros/local_position/pose
ros2 service call /drone_1/mavros/set_mode mavros_msgs/srv/SetMode "{custom_mode: 'OFFBOARD'}"
```
