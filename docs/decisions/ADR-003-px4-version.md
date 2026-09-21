# ADR-003 — One PX4 tag for SITL and Pixracer

Status: **accepted — PX4 v1.17.0** (2026-09-12). Step 1 SITL flight under Pegasus: pass. Step 2 `px4_fmu-v4_default` build: pass (flash 1,983,016 B of 2,032 KB = **95.3 %**, sram 16.8 %). Step 3 MAVROS 2.15.1 connects and reports firmware 1.17.0.

## Context
EKF2 behaviour, parameter names, MAVLink stream sets and offboard rules differ across PX4
releases. The twin is only valid if SITL and the flashed firmware match. The user wants the
**newest PX4 release for a quadcopter that Pegasus supports**.

## Decision
- Policy: pin the **newest PX4 stable tag** (`v1.17.0` on 2026-09-12; check the releases page) that passes the procedure below. Pegasus documents PX4 ≥ v1.14; newer tags
  generally work because Pegasus only relies on the simulator TCP link and standard `px4-rc.*` startup.
- The same tag is flashed to the Pixracer (`px4_fmu-v4_default`).
- Pegasus tag: the release matching Isaac Sim 5.1.0.
- The pin is recorded in `third_party/` submodule commits, `docker/sim.Dockerfile` (`PX4_TAG` arg),
  `deploy/px4_params/README.md`, and here.

## Selection procedure (Phase 1)
1. Check out the candidate tag; in `bisg/sim` build `px4_sitl_default` and fly the Phase 1 smoke test with Pegasus autolaunch
   (watch for: airframe/`PX4_SIM_MODEL` naming, `px4-rc.mavlink` port defaults, lockstep env vars).
2. Build `px4_fmu-v4_default` at the same tag; confirm it links within Pixracer flash. Do not flash yet.
3. (Phase 2) Run the MAVROS square mission; note mode strings and any renamed params (`EKF2_*`, `MAV_*`).
4. Record the tag here, set status to accepted with tag.

Tag chosen: **v1.17.0** (selected 2026-09-12: newest stable; verified `10015_gazebo-classic_iris` airframe present, `boards/px4/fmu-v4/default.px4board` present, `px4-rc.mavlink` port math unchanged). Step 1 passed 2026-09-12 (headless smoke: arm/takeoff/land). Step 2 passed the same day: `make px4_fmu-v4_default` with the apt `gcc-arm-none-eabi` 13.2.1 toolchain inside `bisg/sim` (as root, `git config --global --add safe.directory "*"` needed). Flash headroom on the Pixracer is only ~4.7 %, so any custom firmware module must be weighed against removing another; a future PX4 minor may not fit fmu-v4 at all.

## Consequences
- Upgrading PX4 is a project-level event: SITL, firmware, params file and this ADR change together.
- `scripts/check_env.sh` (Phase 5) compares the Pixracer's reported version with the pin.
- If the newest tag fails step 1 or 2, fall back one minor version and note why here.
- Pixracer flash is 95 % used at v1.17.0: before bumping PX4, rebuild `px4_fmu-v4_default` first.
