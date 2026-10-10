# Downward ToF rangefinder + optical flow (sim twin)

The hardware plan (ultrahack2026 `compopnents.md`) has a Lightware **LW20/C** (down-facing ToF, 5 cm..100 m) and a **PMW3901**
optical-flow sensor. The flight controller reads both itself, so the twin feeds them to **PX4 SITL directly** — no ROS in the loop,
no ZED needed. Built 2026-10-09.

| | |
|---|---|
| Code | `sim/launcher/range_flow.py` — a Pegasus `Backend` next to `PX4MavlinkBackend`, wired in `launch.py:spawn_vehicle` |
| Scenario | `docker/sim/configs/single_iris_flow.yaml` (`sensors.tof`, `sensors.optical_flow`, no ZED) |
| PX4 params | `docker/sim/px4/ekf2_flow_range.params` — `EKF2_HGT_REF=2` (range), `EKF2_RNG_CTRL=2`, `EKF2_OF_CTRL=1`, `EKF2_GPS_CTRL=0` |
| Test | `tests/vio_flight.py` runs unchanged (it only needs MAVROS + the Pegasus ground truth) |
| Benchmark | `tests/range_flow_bench.py` (flight) + `tests/range_flow_eval.py` (accuracy from the PX4 log, `tests/ulog_lite.py`); see below |

## What each sensor does
- **ToF** → `DISTANCE_SENSOR` (orientation 25 = down), 50 Hz. A PhysX ray from the mount point along body −Z; the nearest hit that is not the
  vehicle's own colliders. Gaussian noise (`noise_std_m`); no hit / outside `[min_m, max_m]` → a reading just past max, which PX4 rejects.
- **Optical flow** → `HIL_OPTICAL_FLOW`, 50 Hz. **Analytic, not image-based**: integrated flow = ground-truth sensor velocity (body + ω×r) ÷ the ray
  length, plus the rotation, with noise. Quality 255 inside `[min_m, max_m]` (8 cm..5 m), 0 and "distance unknown" outside. Signs follow MAVLink
  (EKF2 negates them on the way in, `EKF2.cpp`). It does **not** model floor texture, lighting or motion blur: a featureless floor still "tracks".
  A rendered-camera flow would need a real flow algorithm on Isaac frames; not built.

## Run
```
SIM_SCENARIO=single_iris_flow ./bisg up headless      # ./bisg all headless also starts the ros container
docker exec bisg-ros bash -lc 'source /opt/ros/jazzy/setup.bash; python3 /workspace/tests/vio_flight.py --drone 1'
./bisg debug px4 listener distance_sensor -n 1        # also: sensor_optical_flow, estimator_status_flags (cs_rng_hgt, cs_opt_flow)
```
Result 2026-10-09 (RTX 4500 box): OFFBOARD takeoff, 3 m square, descent, land — max |est − truth| x 0.100, y 0.175, z 0.087 m (bound 0.3 m), PASS.

## Accuracy benchmark (2026-10-10)

Ground truth comes from the PX4 log. With `sensors.ground_truth.enabled`, `range_flow.py` sends the exact Pegasus state as
`HIL_STATE_QUATERNION` (100 Hz; world z encoded as alt − 100 m). PX4 logs it as `vehicle_*_groundtruth` on the **same clock** as
`distance_sensor` and `vehicle_optical_flow`, so no cross-clock alignment is needed. Pegasus has its own `send_ground_truth()`, but it
never calls it, and its lat/lon/alt only change at the GPS rate. PX4 does not fuse these topics. The ground-truth quantisation is 1.1 cm
horizontally, 1 mm vertically and 1 cm/s in velocity (MAVLink integer fields).

```
SIM_SCENARIO=single_iris_flow ./bisg all headless
docker exec bisg-ros bash -lc 'source /opt/ros/jazzy/setup.bash; python3 /workspace/tests/range_flow_bench.py --out /tmp/rf'
D=$ARCHIVE_DIR/range_flow/$(date +%Y%m%d-%H%M%S); mkdir -p $D
docker cp bisg-sim:$(docker exec bisg-sim bash -lc 'ls -t $(find /tmp -name "*.ulg") | head -1') $D/flight.ulg
docker cp bisg-ros:/tmp/rf/range.csv $D/; docker cp bisg-ros:/tmp/rf/gt.csv $D/
python3 tests/range_flow_eval.py --ulog $D/flight.ulg --ros-dir $D --out $D     # exit 0 = all gates pass
```
Profile: ground, then takeoff to 1 m, altitude steps 0.5 / 2 / 3.5 / 4.5 m, velocity legs at 1.5 m along x and y at 0.5 / 1 / 2 m/s, yaw in 90° steps,
a 3 m square at 2 m, an OFFBOARD descent and disarm. About 175 s of flight, 160 s wall on the RTX 4500 box.

Result 2026-10-10 (RTX 4500 box, `/opt/docker-archive/range_flow/20261010-025931`), all gates **PASS**:

| Quantity | Result | Gate (tests the twin, not the real sensors) |
|---|---|---|
| ToF (uORB, 50 Hz) − slant range | bias +0.2 mm, RMSE 10.3 mm, p95 20 mm, no outliers > 10 cm, flat over 0.06–4.5 m and 0–45° tilt, lag 0 ms | \|bias\| ≤ 1 cm, RMSE ≤ 2 × `noise_std_m` |
| ToF on ROS (`mavros/hrlv_ez4_pub`, 10 Hz) | bias −0.5 mm, RMSE 10.9 mm | reported only |
| Flow, gyro-compensated − (−v_y, v_x)/range | RMSE 0.0205 rad/s per axis, scale 0.999, corr 0.997, lag ≤ 10 ms | RMSE ≤ 2 × `noise_std_rad_s`, scale 0.95–1.05 |
| Flow gyro (delta_angle) − true rates | RMSE 0.009–0.011 rad/s | reported only |
| Flow as velocity (flow × range) | RMSE 0.039 m/s, growing with height: 0.01 m/s < 0.5 m, 0.045 m/s at 1–2 m, 0.12 m/s at 4–5 m (= flow noise × height) | reported only |
| Flow quality vs height | 0 below 8 cm (on the ground), 1.0 from 0.08 to 4.5 m | reported only |
| EKF2 fusion | flow fused 99.1 % of airborne samples (test ratio p95 0.011), range 100 % (p95 0.001); dead reckoning 1 % of airborne time | flow fused ≥ 90 %, p95 < 1 |
| EKF2 position vs truth | horizontal max 0.13 m, RMS 0.06 m, 0.10 % of the 58 m path; velocity RMSE 0.012 m/s | horizontal max ≤ 0.3 m |

Negative controls (all fail as expected): a floor 3 cm off, a wrong mount (−0.5 m) and a flow gate tighter than the configured noise.
So the passes are not vacuous.

Findings (not twin bugs, but they matter on the real drone):
1. **EKF2 height reads 5 cm high in the air** (bias −5.1 cm in NED, σ 0.8 cm, relative to the on-ground value), while its HAGL (`dist_bottom`) is
   unbiased (σ 3.7 cm). Cause not isolated (terrain/height split while range is the height reference). It is bounded and constant, and should be watched on hardware.
2. **`dist_bottom_valid` is never true** with `EKF2_HGT_REF=2`. PX4 v1.17 only marks the terrain valid when the range (or flow) is fused for
   *terrain* (`terrain_control.cpp`). Here the range is the height reference instead. Anything that waits for a valid HAGL will not get one in this config.
3. **0.44 m of drift during touchdown.** Below the flow's 8 cm minimum, EKF2 dead-reckons until the land detector fires about 1–2 s later
   (error 0.06 m at the last airborne sample, 0.44 m after landing). On hardware, mount the PMW3901 so it is ≥ 8 cm above the ground when landed, or accept it.
4. **PX4 truncates the range to whole cm when streaming `DISTANCE_SENSOR`** (`mavlink/streams/DISTANCE_SENSOR.hpp`). ROS consumers lose up to 1 cm
   per reading (`min_range` reads 0.04 instead of 0.05). On the ground, 36 % of the ROS readings are invalid: `100.0` (the twin's "no reading" when
   noise takes the range below 5 cm) or ≤ `min_range`. Treat `range >= max_range` as no data (contract).
5. The flow twin is analytic. These numbers check the kinematics, signs, timing and the PX4/EKF2 path, not texture, lighting or the PMW3901's real noise.
   The real sensors need the same benchmark against ZED VIO or motion capture.

## Notes
- **Mount height**: the Iris rests with its origin 6 cm above the floor, so the ToF/flow mount is `[0,0,0]`; at `-0.05` the sensor sat 1 cm up, inside `min_m`,
  and read "no data" on the ground. The flow is below its 8 cm minimum until takeoff, so `cs_opt_flow` is false on the ground (normal).
- **Arming**: with no GPS, Hold/Takeoff/Loiter refuse (global position required) — fly in OFFBOARD or Position, like `vio_flight.py`. `tests/hold_position.py` (AUTO.TAKEOFF/LOITER) does not work here.
- **Real drone**: the same `EKF2_*` values apply; the sensors need their PX4 drivers on the Pixracer (`SENS_EN_*` rangefinder serial, flow driver or `OPTICAL_FLOW_RAD` from the Jetson). The repo's ArduPilot names (`RNGFND1_*`, `FLOW_*`, `EK3_SRC1_*`) map to these.
- **ROS topic for the range (not the flow)**: `distance_sensor` is in the lean MAVROS allowlist (`docker/ros/mavros_lean.yaml`), so `/drone_N/mavros/hrlv_ez4_pub` (`sensor_msgs/Range`, ~10 Hz, BEST_EFFORT) carries PX4's `distance_sensor` (PX4's onboard MAVLink link streams it at 10 Hz). EKF2 does not need it — the FC reads the sensor itself; the topic is for the companion computer. Verified 2026-10-09 in `single_iris_flow`: ~2.0 m at 2 m altitude, 0.06-0.08 m on the ground. `MAVROS_PLUGINS=full` does NOT give it (the stock list denylists `distance_sensor`). The topic name and frame are MAVROS' stock placeholders (`hrlv_ez4_pub`, `hrlv_ez4_sonar`); the stock config also creates empty `lidarlite_pub`, `sonar_1_sub`, `laser_1_sub`. Optical flow has no MAVROS plugin in the lean list (`px4flow`) and no ROS topic.
- **Shared DDS domain**: a second machine on the LAN publishing `/drone_1/*` on domain 0 interleaved two drones in every ROS test (seen 2026-10-09). Fixed: `ROS_DOMAIN_ID=auto` (default) derives a per-machine domain from the hostname (`docs/configuration.md`).
