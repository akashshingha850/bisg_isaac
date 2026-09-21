# ADR-001 — MAVROS as the PX4 ↔ ROS 2 bridge

Status: accepted (2026-09-12)

## Context
PX4 offers two ROS 2 paths: **uXRCE-DDS** (PX4 uORB topics exposed as `/fmu/*` with `px4_msgs`,
version-locked to firmware) and **MAVROS** (MAVLink ↔ standard ROS messages, `mavros_msgs`).
The hardware is a **Pixracer** (px4_fmu-v4, 2 MB flash) talking to a Jetson over a UART.

## Decision
Use **MAVROS 2.x** on both sim and hardware. uXRCE-DDS is not used.

## Reasons
- Serial MAVLink on TELEM2 is the well-trodden companion path for Pixracer; `uxrce_dds_client`
  presence on flash-limited fmu-v4 builds is uncertain across PX4 versions.
- MAVROS uses standard ROS types (`PoseStamped`, `Odometry`, `Imu`), so mission and fleet code
  has no dependency on PX4-version-locked `px4_msgs`.
- MAVROS does the ENU/FLU ↔ NED/FRD conversion for `odometry/out` / `vision_pose`, which is
  exactly where a hand-written VIO bridge is easiest to get wrong.
- One bridge on both sides keeps the digital twin honest.

## Consequences
- Slightly higher latency and lower rates than uXRCE-DDS (fine for ≤ 30 Hz setpoints).
- Multi-vehicle needs one MAVROS process per drone with `tgt_system` and a namespace.
- Mode strings / plugin behaviour must be re-checked when the PX4 pin changes (see ADR-003).
- If a future FC (e.g. Pixhawk 6X) makes uXRCE-DDS attractive, it is an additive change behind
  `bisg_vehicle`, not a rewrite.
