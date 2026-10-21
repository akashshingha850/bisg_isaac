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

## Addendum 2026-10-04 — measured (archive/px4-link-study/study-px4-link.md)
- Still accepted. Measured on PX4 v1.17.0 SITL: MAVROS delivers the ENU/FLU external-vision pose to PX4 exactly (0 m / 0.0006° error); frame conversion is the reason to keep it.
- Corrects "uxrce_dds_client presence on fmu-v4 is uncertain": it **is** in `px4_fmu-v4_default` (v1.17.0) and the build still fits (95.3 % flash). RAM on the constrained-memory board is untested.
- **Use the lean plugin list** (`docker/ros/mavros_lean.yaml`, applied by `docker/px4-bridge/entrypoint.sh`; `distance_sensor`/`px4flow` get added when those bridge modules land): idle CPU 28 % -> 9 %, RSS 255 -> 144 MB; default MAVROS degrades badly under CPU contention (command RTT 4 -> 65 ms).
- **Decision 2026-10-05: keep MAVROS** (lean list in use). MAVSDK 4.x native is lighter and faster still; it stays behind the decision gate in the study's §7, measured on the Orin NX with the ZED wrapper running.

## Addendum 2026-10-05 — one bridge service, selectable
The PX4 bridge is one compose service (`px4-bridge`) whose entrypoint starts MAVROS, `mavsdk_server` or the uXRCE-DDS agent according to `PX4_BRIDGE` in `config/bisg.conf`; `./bisg px4-bridge` operates it. MAVROS remains the default and the decision above stands; the others exist to compare, to host non-ROS clients (MAVSDK) and for native uORB access (xrce). See `docs/px4-bridge.md`.
