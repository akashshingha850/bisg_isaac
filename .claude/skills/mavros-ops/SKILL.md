---
name: mavros-ops
description: Launch and operate MAVROS for drone N (namespace, fcu_url, tgt_system), OFFBOARD state machine, setpoint and odometry topics, QoS, timesync/use_sim_time. Use when writing or debugging anything that talks to PX4 through MAVROS.
---

# mavros-ops

## Launch (Phase 2 wrapper: `bisg_bringup/launch/mavros.launch.py`)
```
ros2 launch bisg_bringup mavros.launch.py drone_id:=1 fcu_url:=udp://:14540@127.0.0.1:14580   # sim
ros2 launch bisg_bringup mavros.launch.py drone_id:=1 fcu_url:=serial:///dev/px4:921600       # jetson
```
Wrapper sets `namespace:=/drone_<id>`, `tgt_system:=<id>`, `tgt_component:=1`, `use_sim_time` from env, plugin allow-list
(sys_status, command, setpoint_position, setpoint_raw, local_position, imu, odometry, global_position, param, sys_time).
Packages: `ros-jazzy-mavros`, `ros-jazzy-mavros-extras` (ADR-005).

## OFFBOARD state machine (what `offboard_controller` does)
1. Wait `mavros/state.connected`.
2. Publish setpoint at 20 Hz (current pose or hover) for ≥ 1 s.
3. `set_mode OFFBOARD` → check `state.mode == "OFFBOARD"` (PX4 ≥ 1.14 reports `OFFBOARD`; verify string at the pin).
4. `cmd/arming true` → check `state.armed`.
5. Takeoff = ramp setpoint z; goto = setpoint in `map` ENU; land = `set_mode AUTO.LAND`, wait disarm.
Each step returns a result object with the ACK/`success` so missions read top to bottom.

## Frames
- Setpoints and `local_position` are ENU, frame `map`. MAVROS converts to NED for PX4.
- `mavros/odometry/out`: ENU pose in `odom`, twist in `base_link` (child), header frame ids exactly `odom` / `base_link`; MAVROS maps them to MAV_FRAME_LOCAL_FRD/… internally. Wrong frame ids = silently ignored or mirrored VIO.

## QoS
- MAVROS publishes sensor topics best-effort → subscribe with `SensorDataQoS` or match with `ros2 topic info -v`.

## Time
- Sim: `use_sim_time:=true` for MAVROS and all our nodes; Isaac publishes `/clock`. Timesync plugin keeps PX4 ↔ ROS offset.
- Real: wall clock; chrony to GCS.

## Quick probes
```
ros2 topic echo /drone_1/mavros/state --once
ros2 topic hz /drone_1/mavros/local_position/pose
ros2 service call /drone_1/mavros/set_mode mavros_msgs/srv/SetMode "{custom_mode: 'OFFBOARD'}"
```
