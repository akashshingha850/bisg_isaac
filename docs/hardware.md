# Hardware

Confirmed 2026-09-12: **Jetson Orin NX, JetPack 7.2**, **ZED Mini**, Pixracer. Remaining TBD: frame/motors, drone count for Phase 7, site.

## Bill of materials (per drone)

| Part | Choice | Notes |
|---|---|---|
| Flight controller | Pixracer (px4_fmu-v4, STM32F427, 2 MB flash) | PX4 **v1.17.0** (ADR-003); `px4_fmu-v4_default` builds at **95.3 % flash** — no room for extra modules |
| Companion computer | **Jetson Orin NX** (8 or 16 GB — record which) | **JetPack 7.2** → L4T r38.x, **Ubuntu 24.04**, CUDA 13.x (record exact `cat /etc/nv_tegra_release` and `nvcc --version`) |
| Camera | **ZED Mini** (USB 3.0, 63 mm baseline, built-in IMU) | ZED SDK **5.4.1** (`stereolabs/zed:5.4.1-devel-l4t-r38.4` exists for JetPack 7 / L4T r38.4); wrapper `v5.4.1` |
| Telemetry | WiFi on Jetson (fleet) + optional 900 MHz/433 MHz radio to QGC (safety) | |
| RC | any PX4-supported RC for manual override (kill switch mandatory) | |
| GPS | optional; missions are VIO-first | |
| Frame/props/ESC/battery | **TBD** | measured in Phase 4 for the `bisg_quad` sim model (mass, inertia, arm length, thrust curve) |

Drone count for the first hardware swarm (Phase 7): **TBD** (swarm is a later migration).

## Wiring

```
Pixracer TELEM2 (UART, 3.3 V TTL)  ─────  Orin NX UART (40-pin header UART1 → /dev/ttyTHS1; TX↔RX crossed, GND)
                                          or a USB-TTL adapter → /dev/ttyUSB0 (simpler, slightly more latency)
ZED Mini (USB 3.0, Type-C)  ─────────────  Orin NX USB 3 port (powered hub if the port browns out under load)
Pixracer USB   ──────────────────────────  bench only (QGC on laptop)
```

Add a udev rule so the FC always appears as `/dev/px4`, and give the container user `dialout`.

## PX4 parameters (`deploy/px4_params/<drone_n>.params`)

| Param | Value | Why |
|---|---|---|
| `MAV_SYS_ID` | `n` (drone number) | matches `/drone_<n>` and MAVROS `tgt_system` |
| `MAV_1_CONFIG` | TELEM2 | companion link |
| `MAV_1_MODE` | Onboard | stream set suited to MAVROS |
| `MAV_1_RATE` | 0 (max) or 92160 B/s | |
| `SER_TEL2_BAUD` | 921600 | |
| `EKF2_EV_CTRL` | 15 (pos + vel + yaw + hgt) or 11 without vel | external vision fusion |
| `EKF2_HGT_REF` | Vision | VIO altitude |
| `EKF2_EV_DELAY` | 0 while odom is stamped at image capture time; else the capture→stamp lag (tune from log) | EKF2 subtracts it from the (timesync'd) sample stamp, so a correctly stamped sample plus a non-zero delay counts the latency twice |
| `EKF2_GPS_CTRL` | 0 (indoor) | GPS-denied |
| `EKF2_MAG_TYPE` | none, if yaw from EV | indoor mag is unreliable |
| `COM_RCL_EXCEPT` | 4 (offboard) if flying without RC link | only after RC kill switch is proven |
| `COM_OF_LOSS_T`, `COM_OBL_RC_ACT` | short timeout; action **TBD — not Land/Hold while GPS-denied** | offboard loss failsafe. EV arrives as `LOCAL_FRD`, so EKF2 has no global position: Hold/RTL won't engage and AUTO.LAND flies toward lat/lon 0,0 (sim, 2026-09-25). Candidates: Descend, or Land only once a global origin + north-aligned yaw exist. Must be proven in SITL before the bench checklist |
| `CBRK_*` | none disabled in flight | bench only |

Param names are checked against the pinned PX4 tag in Phase 1 (newer releases rename some). The same file is loaded into SITL (Phase 3) so sim and hardware EKF2 behave the same.

## Jetson software

- JetPack 7.2 (L4T r38.x, Ubuntu 24.04). Docker + `nvidia-container-toolkit` from JetPack; `docker compose` v2.
- Images: `bisg/ros:arm64` (ROS 2 **Jazzy**, ADR-005), `bisg/zed:l4t-r38` from `docker/zed/build.sh jetson` (Stereolabs scripts, SDK 5.4.1, L4T r38.4) — built on the Jetson or pushed from the workstation.
- `deploy/jetson/compose.yaml` profile `jetson`: `mavros` (serial), `zed` (wrapper), `vehicle` (offboard, `vio_relay`, health).
- Clock: chrony to the ground station; ROS wall time.
- Boot: a systemd unit starts the compose profile; a physical LED / `vehicle/state` shows readiness.
- Power mode: `nvpmodel` MAXN or 25 W; `jetson_clocks` for consistent VIO latency.

## ZED Mini model table (used by the Isaac rig and `check_contract.py`)

| Field | Value |
|---|---|
| Model | ZED Mini |
| Baseline | 0.063 m |
| Resolution / FPS used | HD720 (1280×720) @ 30 (60 possible; 30 keeps Jetson + Isaac load down) — decide in Phase 3 |
| Available modes | 2208×1242@15, 1920×1080@30, 1280×720@60, 672×376@100 |
| FOV (approx.) | 90° H × 60° V (per lens, HD720) — take exact K from the camera's factory calibration via the SDK and copy it here |
| Depth range | 0.1–15 m (ULTRA/NEURAL modes) |
| IMU | built-in, published at 200 Hz by the wrapper (`zed_imu_link`) |
| Mount pose `xyz_rpy` on `base_link` | TBD (measure on the frame in Phase 4). Sim uses `[0.18, 0.0, -0.02, 0, 0, 0]`: the lens must sit **ahead of the frame** and the props **outside the ~90° HFOV**; the old example `0.10` put the sim lens inside the Iris nose. Re-run the view check (bugs.md B13) for the real mount |
| Positional tracking | SDK VIO → `zed/zed_node/odom`; `vio_relay` republishes to `mavros/odometry/out` |

Limits worth knowing: ZED Mini is USB, so no GMSL capture card. Stereolabs' Isaac Sim streaming extension supports it from v5.2 on (Isaac Sim 6.0, asset `ZED_M`); the sim's intrinsics come from that twin (HD720 `fx` = 529.8 px, baseline 63.0 mm), **not** from your unit's factory calibration — code must read `camera_info`, never hard-code `K`. Copy the real unit's `K` here once it is on the bench (`docs/zed-sdk-sim.md`).

## Vehicle model measurements (Phase 4, for `sim/assets/vehicles/bisg_quad`)

- Total mass with battery + Jetson + ZED Mini; CG position.
- Arm length / motor positions relative to CG; prop diameter and pitch; rotation directions.
- Thrust vs PWM/throttle for one motor+prop on a bench scale (or manufacturer curve) at the battery voltage used.
- Inertia: bifilar pendulum or CAD estimate; note the method.
- Sensor poses: ZED Mini (above), Pixracer IMU offset (`EKF2_IMU_POS_*`).

## Bench checklist (Phase 5, props OFF)

1. Pixracer flashed with the pinned tag; params file loaded; `MAV_SYS_ID` matches.
2. `mavros/state.connected == true` within 5 s of container start.
3. ZED wrapper publishes `odom` at the expected rate; TF chain complete.
4. `vio_relay` → `mavros/odometry/out`; in QGC MAVLink console `ekf2 status` shows EV fused, innovations small; local position valid without GPS.
5. Move the drone by hand: `mavros/local_position/pose` tracks the ZED odom (< 5 cm drift over 1 m).
6. OFFBOARD accepted on the bench (`mission_square --dry-run`: mode switches, no arm).
7. RC kill switch and offboard-loss failsafe verified in SITL first, then on the bench.
