# PX4 parameter files

One topic per file, `NAME VALUE MAV_PARAM_TYPE` per line (6 = INT32, 9 = REAL32; not the 5-column QGC save format, `#`
comments allowed). Names and ranges are checked against the pinned PX4 tag (`PX4_TAG`, ADR-003).

| file | what it sets |
|---|---|
| `ekf2_vision.params` | GPS-denied flight on the ZED visual odometry: EKF2 external-vision fusion, GPS and magnetometer off |
| `collision_prevention.params` | PX4 collision prevention in Position mode (`CP_*`), fed by the ZED depth through `mavros/obstacle/send` |

A new topic (failsafes, geofence, tuning, ...) is a new file here, not another block in an existing one.

**SITL:** a scenario lists the files it wants, applied in order at PX4 boot (later wins, an override is logged):

```yaml
px4:
  params: [ekf2_vision, collision_prevention]   # bare name = docker/sim/px4/<name>.params; or a path
```

The launcher turns them into `PX4_PARAM_<name>` env vars, which PX4's rcS applies before EKF2 starts, so the
reboot-required EKF2 params take effect on the first boot. A scenario that `extends` another **replaces** the list.

**Pixracer:** the same files, loaded with QGC or `scripts/push_px4_params.py --file <name>` (repeatable), so sim and
hardware fly on one set. Per-drone identity (`MAV_SYS_ID`, TELEM2) is a `drone_<n>.params` file here.
