---
name: jetson-deploy
description: Deploy the ROS/ZED/vehicle containers to a Jetson, flash and parameterise the Pixracer, run the bench and preflight checklists, pull logs after a flight. Use for anything that touches real hardware.
---

# jetson-deploy

Safety first: any step with props ON requires the RC kill switch verified that day and a second person.

## Images
- Build on the workstation: `docker buildx build --platform linux/arm64 -f docker/ros.Dockerfile -t <registry>/bisg/ros:arm64 --push .`
- Target: Jetson Orin NX, JetPack 7.2 (L4T r38, Ubuntu 24.04, CUDA 13). ZED image: base `stereolabs/zed:<sdk>-devel-l4t-r38.x` with a ZED SDK minor that lists JetPack 7.2 (see `docs/hardware.md`). Mismatch = SDK refuses to start.
- On the Jetson: `docker compose -f deploy/jetson/compose.yaml --profile jetson pull && up -d`.

## Pixracer
1. Build/flash `px4_fmu-v4_default` at the pinned tag (ADR-003) via QGC custom firmware or `make px4_fmu-v4_default upload`.
2. Load `deploy/px4_params/drone_<n>.params` (QGC → Parameters → Tools → Load). Reboot. Confirm `MAV_SYS_ID`.
3. Serial: TELEM2 ↔ Jetson UART, 921600; udev rule → `/dev/px4`.

## Bench checklist
Follow `docs/hardware.md` → "Bench checklist" in order; do not skip step 7 (failsafes).

## ZED Mini specifics
- USB 3 only; use a short, good cable; `lsusb` shows `Stereolabs`. Wrapper config `zedm.yaml`; `camera_model: zedm`.
- Positional tracking needs texture: warehouse-like scenes are fine, blank walls are not.

## Preflight (props on)
- Battery, props, kill switch, geofence loaded, `vehicle/state.vio_ok`, EKF2 local position valid, GCS link.
- First flight of a new build: manual hover on RC before any OFFBOARD.

## After flight
- Pull `.ulg` from the Pixracer (QGC or MAVLink FTP) and the Jetson container logs into `logs/<date>_<drone>/` (git-ignored).
- Note EV delay / innovation observations in `docs/hardware.md` tuning notes.
