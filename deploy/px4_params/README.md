# PX4 parameter files

One `.params` file per drone (`drone_1.params`, ...) plus `sim_default.params` for SITL. Loaded into
SITL by the launcher (`px4.params_file`, Phase 3) and onto the Pixracer with QGC (Phase 5) so EKF2
and failsafes behave identically. Names are checked against the pinned PX4 tag (`PX4_TAG` in `docker/.env`,
ADR-003). Format: QGC "param save" text (`# ` comments allowed).
