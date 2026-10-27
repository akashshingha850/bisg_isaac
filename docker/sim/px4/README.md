# PX4 parameter files

One file per vehicle, `NAME VALUE MAV_PARAM_TYPE` per line (6 = INT32, 9 = REAL32; not the 5-column QGC save format, `#`
comments allowed). Names and ranges are checked against the pinned PX4 tag (`PX4_TAG`, ADR-003).

**The drone has one file, `raptor.params`** (sim.yaml `px4_params: [raptor]`; the Pixracer loads the same file): collision prevention
**off** (`CP_DIST -1`), the **sim-only** rate gains that stop its takeoff shake (never load that block onto the Pixracer), the EKF2
lever arms, and the GPS-denied mode (baro height reference + LW20 + ZED VIO velocity + yaw + PMW3901, no GPS/mag; the yaw held by the
zed-bridge's Manhattan compass, `EKF2_EV_CTRL 12`; docs/range-flow.md, docs/vio-drift.md). A new vehicle-wide setting is a block
there, not a new file. Not yet on the Pixracer: the compass block (load `EKF2_EV_CTRL 13` there until the compass is checked on the
real camera).

Legacy Iris scenarios (GPS, `single_iris_*`) keep their own files: `iris.params` (collision prevention, fed by the ZED depth) + an
optional overlay, `ekf2_vision.params` (GPS-denied on the ZED VIO) or `ekf2_flow_range.params` (ToF + optical flow): `params: [iris, ekf2_vision]`
(later wins).

**SITL:** a scenario lists the files it wants, applied in order at PX4 boot (later wins, an override is logged):

```yaml
px4:
  params: [iris, ekf2_vision]   # bare name = docker/sim/px4/<name>.params; or a path
```

The launcher turns them into `PX4_PARAM_<name>` env vars, which PX4's rcS applies before EKF2 starts, so the
reboot-required EKF2 params take effect on the first boot. A scenario that `extends` another **replaces** the list.

**Pixracer:** the same files, loaded with QGC or `scripts/push_px4_params.py --file <name>` (repeatable), so sim and
hardware fly on one set. Per-drone identity (`MAV_SYS_ID`, TELEM2) is a `drone_<n>.params` file here.
