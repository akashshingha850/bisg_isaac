# The real ZED SDK in the sim

Goal: the code that runs on the Jetson (`zed_wrapper` + ZED SDK 5.4.1, ZED Mini) runs **unchanged** against the
simulator, so a node written and tested in sim ports to the drone by changing a compose file, not the code.

The sim has one ZED source: the **real `zed_wrapper`**, fed by Isaac through Stereolabs' extension. Depth, point cloud,
odometry and every other SDK module come from the SDK and are switched in `docker/zed/zed.yaml`; the sim publishes no
ZED topics itself except `imu/data`. Needs Isaac Sim 6.0, `./bisg zed ext-build`, `bisg/zed:desktop`. (The old
`ZED_SOURCE=emulated` rig and `vio_mock` were removed 2026-10-07.)

Isaac Sim 5.1 cannot do `sdk`: Stereolabs' 5.1 line (`isaac-sim/5.1`, Kit 107.3) only ships ZED X cameras; the ZED Mini twin
(`ZED_M`) exists from extension v5.2 on, which targets Isaac Sim 6.0. That is why this lives on the 6.0 branch.

## Run it

```bash
./bisg zed ext-build                  # once: builds the Stereolabs extension into docker/zed/zed-isaac-sim (~1-4 min)
./bisg zed image                      # once: bisg/zed:desktop = Stereolabs' ZED SDK + wrapper image + CycloneDDS overlay (~15 GB)
./bisg up headless                    # sim with the ZED Mini twin streaming
./bisg zed up                         # zed_wrapper for drone 1 against the stream; waits for frames
./bisg zed check                      # contract + SDK checks, exit 0 = PASS (tests/zed_sdk_check.py)
./bisg zed status | logs | down
```

Start the wrapper **after** the sim (`./bisg wait` says ready). The SDK opens the stream once: if the wrapper container is
restarted, restart the sim too (`docs/zed-sdk-sim.md#troubleshooting`). `./bisg zed up` handles a missed first connect.

## How it works

```
 Isaac Sim 6.0 (bisg-sim)                                   zed container (bisg-zed-1)
 ┌──────────────────────────────────────────┐              ┌───────────────────────────────────────────┐
 │ Pegasus Iris  ──FixedJoint──► ZED_M asset │  shared mem  │ zed_wrapper  (same image, launch file and  │
 │   body            (mount_xyz_rpy)         │ /dev/shm/    │ params as the Jetson, + the `sim:` block of docker/zed/zed.yaml)│
 │ OmniGraph ZED_Camera node (sl.sensor.camera)├────────────►│  SDK: stereo-matches depth, tracks pose,   │
 │   stereo RGB + frame-rate IMU, port 30000+2·id│ sl_local_*  │  publishes /drone_1/zed/zed_node/*         │
 │ physics IMU ──► /drone_1/zed/zed_node/imu/data│             │                                            │
 └──────────────────────────────────────────┘              └───────────────────────────────────────────┘
```

- **Mount** (`sim/launcher/zed_sdk_rig.py`): the extension's `ZED_M` USD is a rigid body referenced at `/World/drone_<n>_zed` and
  held by a `FixedJoint` to the vehicle's `body` at `sensors.zed.mount_xyz_rpy`. This is Stereolabs' own robot-mount pattern. A
  plain nested reference does **not** follow a physics-driven parent: the camera stays at the spawn pose and the SDK sees a
  frozen scene (odometry stuck at 0.000). The asset is made weightless (1 g, no gravity) so it does not shift the vehicle's
  hover thrust. The mount must not sit inside any visible mesh (a camera inside the carrier cube streams black frames).
- **Stream**: OmniGraph node `sl.sensor.camera.ZED_Camera`, model `ZED_M`, HD720 @ 30 fps, transport `IPC` (shared memory:
  both containers need `ipc: host`). Port `30000 + 2·(vehicle id)` — even and unique per drone.
- **Wrapper**: `docker/zed/zed_drone.launch.py` wraps Stereolabs' launch in the `drone_<n>` namespace (so topics are
  `/drone_<n>/zed/zed_node/...` as the contract says). The same file is used by the `drone` profile of `docker/compose.yaml`. Params are
  `docker/zed/zed.yaml` (hardware) merged with the `sim:` block of `docker/zed/zed.yaml` (the only sim deltas).
- **Depth is the SDK's own**: it stereo-matches the rendered left/right images (`NEURAL_LIGHT`), with the real SDK's holes,
  range limits and noise characteristics. Stereolabs' extension offers a ground-truth `streamDepth` mode as well; we do not
  use it, because then the SDK's depth would not be exercised.

## What differs from the real drone (and why)

Every row is a deliberate deviation. Rows marked **hardware to-do** must be re-checked on the bench.

| Area | Sim (`sdk`) | Real drone | Where it is set / what to do |
|---|---|---|---|
| IMU in the stream | one sample per rendered frame (30 Hz sim time), orientation + acceleration only | 400 Hz gyro + accel | the SDK cannot fuse it: `pos_tracking.imu_fusion: false` and `sensors.sensors_image_sync: true` in the `sim:` block of `docker/zed/zed.yaml`. **Hardware to-do:** tracking quality with `imu_fusion: true` is only measurable on the camera |
| `zed/zed_node/imu/data` | published by the **sim** from a physics IMU on the vehicle body (250 Hz sim time) | published by the wrapper | the streamed ZED has no usable sensor channel (`getSensorsData: INVALID FUNCTION PARAMETERS`); same topic, frame and type |
| Tracking mode | `AUTO` (= GEN_3), visual-only | `AUTO` (= GEN_3), visual-inertial | `pos_tracking_mode: AUTO` in both. GEN_3 with the default IMU fusion aborts in sim: `HIGH FREQUENCY SENSORS DATA REQUIRED` then FATAL |
| Intrinsics | the extension's `ZED_M` lens: HD720 `fx` = 529.8 px, baseline 63.0 mm | your unit's factory calibration (the SDK downloads it by serial) | read `camera_info`; never hard-code `K`. **Hardware to-do:** record the real `K` in `docs/hardware.md` |
| Scene realism | RTX render: no sensor noise, no rolling shutter, perfect exposure, textured warehouse | all of that | the extension has an experimental `ZED Sim2Real` post-process (`applyZedSim2Real`), unused so far |
| Frame rate | the stream ticks in **sim time**; the sim runs at rtf ~0.35 here (Pegasus per-step Python, `migration-errors.md` M8), so wall-clock rates are ~0.35 x nominal | wall clock | `tests/zed_sdk_check.py` divides by the `/clock` rtf; on the drone rtf = 1 |
| TF frames | whatever the wrapper publishes (`odom → zed_camera_link`, camera frames unprefixed) | the same | the contract's `drone_<n>/` frame prefix is not something the wrapper can produce; **open**, see todo |
| Clock | wrapper stamps with the wall clock (`use_sim_time: false`) | wall clock | closing the loop into PX4 needs the stamps on PX4's (sim) clock; **open**, see todo |

## Verified (2026-10-03, workstation RTX 4500 Ada, driver 580.178.04)

`./bisg zed check` against `single_iris` (warehouse), `ZED_SOURCE=sdk`, drone hovering on the ground, 15 s window:

| Check | Result |
|---|---|
| left / right image, depth, point cloud (per simulated second) | 20.3 / 22.2 / 23.2 / 22.4 Hz (nominal 30; wall-clock ~7 Hz at rtf 0.34) |
| odometry, IMU | 30.0 Hz, 286 Hz |
| `camera_info` | 1280x720, `fx` 529.8 px, stereo baseline **63.0 mm** (from the right camera's `P[0,3]/fx`) |
| depth | `32FC1`, 79 % finite pixels, 5-95 percentile 0.24-11.10 m |
| SDK health | `low_image_quality`, `low_lighting`, `low_depth_reliability`, `low_motion_sensors_reliability` all `false` |
| tracking | `odometry_status` OK, drone parked: odom path 0.00 m |

Flight: OFFBOARD takeoff to 2 m, a 4 m square, landing (`tests/vio_flight.py`, PASS), with `./bisg zed check --seconds 330` sampling the whole time.
Two runs on the same sim:

| Check | Run 1 (420 s window) | Run 2 (330 s window) |
|---|---|---|
| images / depth / cloud, per simulated second (rtf 0.33 / 0.29) | 19.6-22.4 / 23.7 / 19.1 Hz | 19.3-22.2 / 23.3 / 21.2 Hz |
| odometry, IMU | 29.2 Hz, 280 Hz | 29.2 Hz, 280 Hz |
| depth | 78 % valid, 0.24-11.2 m | 79 % valid, 0.24-10.9 m |
| health flags, tracking status | all clear, OK | all clear, OK |
| SDK odometry path / truth path | 21.87 m / 21.64 m = 1.01 | 21.63 m / 21.59 m = 1.00 |
| **trajectory RMSE** after yaw + offset alignment (`trajectory_rmse` in the check) | (metric added after this run) | **0.088 m**, end error 0.024 m, odom frame yawed -0.3 deg vs map |

That is visual-only GEN_3 on a textured warehouse with a perfect render: it bounds what the SDK adds on top of the scene, not what the real camera,
with sensor noise and an IMU, achieves. The real-camera number comes from the bench (same script, `--no-gt`, plus a tape measure).

## Porting to the Jetson

1. Same image recipe: `docker/zed/build.sh jetson` (on the Jetson) builds Stereolabs' L4T image and the same CycloneDDS
   overlay (`docker/zed/Dockerfile.overlay`), tagged `bisg/zed:l4t-r38`.
2. the `drone-zed` service of `docker/compose.yaml` runs the same launch file (`docker/zed/zed_drone.launch.py`) with
   `docker/zed/zed.yaml` and **without** the overlay and `sim_mode`. Nothing else differs.
3. On the bench run the same check: `python3 tests/zed_sdk_check.py --drone 1 --no-gt` (no ground truth on a real drone; it
   then checks streams, geometry, depth, health and that odometry is finite and moving).
4. Re-check the hardware to-dos in the table above (IMU fusion, intrinsics, frame prefix, clock).

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `./bisg up` aborts with `ZED SDK mode needs the zed-isaac-sim extension` | build it: `./bisg zed ext-build` |
| Extension build: `Not enough free space ... /tmp/.cache/packman` | packman unpacks ~12 GB (CUDA, Kit SDK). The script mounts a host cache (`~/.cache/packman`, override `PACKMAN_CACHE`) so it is fetched once |
| Extension build: `ERROR: cannot verify ... certificate` (wget) | the sim image's `LD_LIBRARY_PATH` pulls Isaac's libcrypto into wget; the script clears it |
| Wrapper log stops after `Streaming ... receiving port 30000 is not available ... switching to port 30002` and no topics | the wrapper started before the stream was live, or a previous wrapper already used the stream. The SDK connects once per sim run: restart the sim, then `./bisg zed up` |
| Wrapper prints `CORRUPTED FRAME` + `Duplicate frame detected` on every grab, `low_image_quality: true` | the camera never moved or sees black: the ZED asset is not rigidly attached to the vehicle (nested reference instead of the `FixedJoint`), or it is inside a mesh. Check `[launch] zed sdk rig:` in `./bisg logs` and the frames (`rqt_image_view`) |
| Black images, odom exactly 0 | same as above |
| `Pos. Tracking not started: HIGH FREQUENCY SENSORS DATA REQUIRED`, FATAL | IMU fusion is on with the sim's frame-rate IMU: `imu_fusion: false` (the overlay does this) |
| `[publishSensorsData] sl::getSensorsData error: INVALID FUNCTION PARAMETERS` thousands of times | `sensors_image_sync: true` (the overlay does this) |
| `camera_info` and odom flow but images / depth / clouds do not | UDP receive buffer too small for CycloneDDS: `net.core.rmem_max` (docs/setup.md; `./bisg check` warns). Workaround without sudo: `ZED_RMW=rmw_fastrtps_cpp ./bisg zed up` (shared memory), then check from inside that container |
| `Invalid calibration file format ... LC_ALL=C` | harmless in sim (`Self Calibration Disabled`: a simulated camera has no per-unit calibration). `LC_ALL=C` changes nothing |
| Wrapper hangs at `Loading ZED node ... in container /zed/zed_container` | the namespace was pushed without the load-service remap; use `docker/zed/zed_drone.launch.py`, not `zed_camera.launch.py namespace:=drone_1` |
| Wrapper dies with `RMW implementation not installed (rmw_cyclonedds_cpp)` | the image is Stereolabs' upstream (Fast DDS only): rebuild with `./bisg zed image` (adds the CycloneDDS overlay) |

## Pins and sources

- Extension: `docker/zed/zed-isaac-sim` @ `v5.2.1` (`529e538`; a branch upstream, so the SHA is the pin), fetched by
  `scripts/fetch_sources.sh`, built by `docker/zed/build_isaac_ext.sh`. v5.2.x declares Kit 110.1.2 (Isaac Sim 6.0.1); our
  base image is 6.0.0 (Kit 110.1.1), so the build script widens the load gate to both. Moving `ISAAC_TAG` to 6.0.1 removes that patch.
- ZED SDK `5.4.1` (the extension needs >= 5.4.1 on the receiving side), `zed-ros2-wrapper` `v5.4.1`.
- Stereolabs docs: [Isaac Sim integration](https://docs.stereolabs.com/docs/integrations/isaac-sim/),
  [old extension (< 4.0)](https://docs.stereolabs.com/docs/integrations/isaac-sim/old-version-of-the-zed-extension-for-isaac-sim),
  [depth sensing](https://docs.stereolabs.com/docs/tutorials/depth-sensing),
  [Isaac Sim 5.1 camera/depth assets](https://docs.isaacsim.omniverse.nvidia.com/5.1.0/assets/usd_assets_camera_depth_sensors.html)
  (ZED X and ZED X Mini only; a different camera from the ZED Mini).
