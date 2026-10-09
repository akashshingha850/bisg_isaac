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

## Notes
- **Mount height**: the Iris rests with its origin 6 cm above the floor, so the ToF/flow mount is `[0,0,0]`; at `-0.05` the sensor sat 1 cm up, inside `min_m`,
  and read "no data" on the ground. The flow is below its 8 cm minimum until takeoff, so `cs_opt_flow` is false on the ground (normal).
- **Arming**: with no GPS, Hold/Takeoff/Loiter refuse (global position required) — fly in OFFBOARD or Position, like `vio_flight.py`. `tests/hold_position.py` (AUTO.TAKEOFF/LOITER) does not work here.
- **Real drone**: the same `EKF2_*` values apply; the sensors need their PX4 drivers on the Pixracer (`SENS_EN_*` rangefinder serial, flow driver or `OPTICAL_FLOW_RAD` from the Jetson). The repo's ArduPilot names (`RNGFND1_*`, `FLOW_*`, `EK3_SRC1_*`) map to these.
- **ROS topic for the range (not the flow)**: `distance_sensor` is in the lean MAVROS allowlist (`docker/ros/mavros_lean.yaml`), so `/drone_N/mavros/hrlv_ez4_pub` (`sensor_msgs/Range`, ~10 Hz, BEST_EFFORT) carries PX4's `distance_sensor` (PX4's onboard MAVLink link streams it at 10 Hz). EKF2 does not need it — the FC reads the sensor itself; the topic is for the companion computer. Verified 2026-10-09 in `single_iris_flow`: ~2.0 m at 2 m altitude, 0.06-0.08 m on the ground. `MAVROS_PLUGINS=full` does NOT give it (the stock list denylists `distance_sensor`). The topic name and frame are MAVROS' stock placeholders (`hrlv_ez4_pub`, `hrlv_ez4_sonar`); the stock config also creates empty `lidarlite_pub`, `sonar_1_sub`, `laser_1_sub`. Optical flow has no MAVROS plugin in the lean list (`px4flow`) and no ROS topic.
- **Shared DDS domain**: a second machine on the LAN publishing `/drone_1/*` on domain 0 interleaved two drones in every ROS test (seen 2026-10-09). Fixed: `ROS_DOMAIN_ID=auto` (default) derives a per-machine domain from the hostname (`docs/configuration.md`).
