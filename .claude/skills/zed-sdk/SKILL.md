---
name: zed-sdk
description: Run, check and debug the REAL ZED SDK + zed_wrapper against the sim's ZED Mini twin (ZED_SOURCE=sdk), build the Stereolabs Isaac extension, and port the same setup to the Jetson. Use when the user asks about the ZED SDK in Isaac Sim, depth/point cloud/odometry from the real SDK, "SDK vs emulated", ZED extension builds, or sim-to-hardware parity for the ZED Mini.
---

# zed-sdk

Full doc: `docs/zed-sdk-sim.md` (architecture, deviations from hardware, troubleshooting). This is the working checklist.

## What it is
`ZED_SOURCE=emulated` (default): Isaac cameras publish the ZED topics, `vio_mock` is odometry, no SDK. `ZED_SOURCE=sdk`: Stereolabs'
`zed-isaac-sim` extension (v5.2.x, **Isaac Sim 6.0 only**; the 5.1 line has ZED X only) streams a `ZED_M` twin into the unmodified
`zed_wrapper` (image `bisg/zed:desktop`, the Jetson's recipe), which publishes `/drone_<n>/zed/zed_node/*`.

## Run
1. Once: `scripts/fetch_third_party.sh`, `./bisg zed ext-build`, `./bisg zed image`. The sim image needs the extension's runtime libs (`docker/sim/Dockerfile`).
2. `ZED_SOURCE=sdk ./bisg up headless && ./bisg wait`
3. `./bisg zed up` (after the sim, never before; it waits for frames and retries a missed first connect once)
4. `./bisg zed check` (`--seconds N`, flags in `tests/zed_sdk_check.py`). To check motion: fly `tests/vio_flight.py` in `bisg-ros` while it samples (`--seconds` longer than the flight).
5. Restart rule: the SDK connects once per sim run (B18). Restart the sim whenever the wrapper restarts.

## Rules that bit us (do not re-learn them)
- The ZED asset is a rigid body: attach it with a **FixedJoint** to the vehicle `body` (`zed_sdk_rig.py`). Nested reference = camera never moves = identical frames = `Duplicate frame detected` -> `CORRUPTED FRAME`, odom 0.000.
- Never place the camera inside a visible mesh (black frames). Mount `x >= 0.18` on the Iris.
- Stream carries a **frame-rate IMU** only: sim overlay sets `imu_fusion: false` + `sensors_image_sync: true`; the sim publishes `imu/data` itself. GEN_3 with IMU fusion aborts (`HIGH FREQUENCY SENSORS DATA REQUIRED`).
- Wrapper `pos_tracking_mode` values: `AUTO | GEN_1 | GEN_3` (no GEN_2).
- Namespace: use `deploy/launch/zed_drone.launch.py` (gives `/drone_<n>/zed/zed_node/...`); `zed_camera.launch.py namespace:=drone_1` drops `zed_node`.
- ZED image is Fast DDS only; `docker/zed/Dockerfile.overlay` adds Cyclone. Big topics need `net.core.rmem_max >= 10 MB` (`./bisg check` warns); no-sudo fallback `ZED_RMW=rmw_fastrtps_cpp`.
- Rates: judge in **sim time** (sim rtf ~0.35 on 6.0); the check script divides by the `/clock` rtf.
- Intrinsics come from the extension's lens (HD720 `fx` 529.8), not the real unit: consumers read `camera_info`.
- One odometry source per run: with `sdk`, `./bisg vehicle up` refuses `vio_mock`. Feeding SDK odometry into PX4 is open (B17: clock stamps, no `vio_relay` on this branch).
- Disk: Docker's data-root is `/opt/docker-data` (1.3 TB free); packman needs ~12 GB (cache `~/.cache/packman` on `/`, override with `PACKMAN_CACHE`).

## Diagnose
`./bisg zed status` (rates + health), `./bisg zed logs`, `ls /dev/shm/sl_local_*` (stream exists only while the timeline plays), `./bisg logs | grep "zed sdk rig"`. Table in `docs/zed-sdk-sim.md#troubleshooting`.

## Port to the Jetson
Same launch file + `deploy/jetson/zed_params.yaml`, no overlay, no `sim_mode`; `docker/zed/build.sh jetson`; `python3 tests/zed_sdk_check.py --drone 1 --no-gt`. Re-check the hardware to-dos (IMU fusion on, real `K`, frame prefix B16, clock B17).
