# PX4 parameter files

One file per vehicle plus mode overlays, `NAME VALUE MAV_PARAM_TYPE` per line (6 = INT32, 9 = REAL32; not the 5-column QGC save format, `#`
comments allowed). Names and ranges are checked against the pinned PX4 tag (`PX4_TAG`, ADR-003).

| file | what it sets |
|---|---|
| `iris.params` | **vehicle file**, the Iris: collision prevention (`CP_*`, fed by the ZED depth through `mavros/obstacle/send`); rate gains are the airframe defaults |
| `raptor.params` | **vehicle file**, the raptor twin: collision prevention **off** (`CP_DIST -1`, room scans fly close to walls; the other `CP_*` kept for turning it back on) + **sim-only** rate gains that stop its takeoff shake (never load that block onto the Pixracer) |
| `ekf2_vision.params` | overlay: GPS-denied flight on the ZED visual odometry (EKF2 external vision, GPS and magnetometer off) |
| `ekf2_flow_range.params` | overlay: GPS-denied flight on the downward ToF + optical flow (docs/range-flow.md) |
| `ekf2_vio_flow_range.params` | overlay: **the real drone's GPS-denied mode**: baro height reference + LW20 + ZED VIO + PMW3901, no GPS/mag (docs/range-flow.md "GPS-denied on all sensors"). Needs the vehicle's lever arms and `EKF2_MIN_RNG` (raptor.params) |
| `ev_compass.params` | overlay on `ekf2_vio_flow_range`, **sim default since 2026-10-26**: ZED velocity + yaw only (`EKF2_EV_CTRL 12`), the yaw held by the zed-bridge's Manhattan compass (zed.yaml `heading: manhattan`, docs/vio-drift.md). Only together with the compass; not on the Pixracer yet |

A scenario lists **its vehicle's file first, then any overlays** (later wins): `px4.params: [iris]`, `[iris, ekf2_vision]`,
`[raptor]`. Everything a vehicle always flies with goes in its vehicle file; only a sensing mode that switches EKF2 sources
is an overlay. A new vehicle-wide setting (failsafes, geofence, tuning, ...) is a block in each vehicle file, not a new file.

**SITL:** a scenario lists the files it wants, applied in order at PX4 boot (later wins, an override is logged):

```yaml
px4:
  params: [iris, ekf2_vision]   # bare name = docker/sim/px4/<name>.params; or a path
```

The launcher turns them into `PX4_PARAM_<name>` env vars, which PX4's rcS applies before EKF2 starts, so the
reboot-required EKF2 params take effect on the first boot. A scenario that `extends` another **replaces** the list.

**Pixracer:** the same files, loaded with QGC or `scripts/push_px4_params.py --file <name>` (repeatable), so sim and
hardware fly on one set. Per-drone identity (`MAV_SYS_ID`, TELEM2) is a `drone_<n>.params` file here.
