---
name: swarm-spawn
description: Add or remove drone N in a sim scenario — vehicles list, PX4 instance/port derivation, per-drone MAVROS/vehicle compose services via scripts/gen_compose.py, fleet manager registration, VRAM budget update. Use when the user wants more or fewer drones or a new swarm scenario.
---

# swarm-spawn

## Procedure (Phase 6+; swarm is a migration of the proven single-drone twin)
1. Scenario YAML `docker/sim/configs/<scenario>.yaml` → `vehicles:` list: `{id, model, spawn_xyz, spawn_yaw_deg, sensors: {zed: true, lidar: false, tof: {enabled}, optical_flow: {enabled}}}`. ids are 0-based and contiguous.
2. Regenerate compose: `python3 scripts/gen_compose.py --scenario docker/sim/configs/<scenario>.yaml -o docker/compose.generated.yaml`
   → one `mavros_<n>` and `vehicle_<n>` service per drone with `fcu_url` from the instance math (`px4-sitl` skill).
3. Fleet: `bisg_fleet` reads the same YAML for the roster (`fleet.yaml` section) — no separate list.
4. Start: `docker compose -f docker/compose.yaml -f docker/compose.generated.yaml --profile sim-headless --profile ros up`.
5. Verify: `ros2 topic list | grep -c mavros/state` equals N; each `/drone_<n>/mavros/state.connected`.
6. Update the VRAM/FPS budget table in `docs/plan.md` (or `docs/budget.md` once it exists) with `nvidia-smi --query-gpu=memory.used --format=csv` at steady state.

## ZED SDK mode per drone (`ZED_SOURCE=sdk`, skill `zed-sdk`)
- Already per-drone in the launcher: drone `id` streams on port `30000 + 2·id` (`zed_sdk_cfg.stream_port`, even + unique), prim `/World/drone_<id+1>_zed`.
- One wrapper per drone: `./bisg zed up --drone N` (container `bisg-zed-N`, namespace `drone_N`, port derived from N). Each wrapper needs the GPU and the neural depth model: budget VRAM per drone before adding more.
- The wrapper's TF frames are unprefixed (`zed_camera_link`, B16): two drones on one TF tree need the per-drone `/drone_<n>/tf` namespacing, or a decision on B16, before any cross-drone TF consumer exists. **Untested with more than one drone.**

## Limits on this workstation (RTX 2080 Ti, 11 GB)
- Prefer headless; 1 camera per drone; drop to 640×360 beyond 2 drones; disable depth/pointcloud unless the task needs it.
- Spawn poses ≥ 2 m apart and inside the world's collision bounds.

## Checks before declaring "works"
- All N PX4 instances print "Ready for takeoff"; no port collisions (`ss -ltnp | grep 456`).
- Fleet `collective arm → takeoff → land` completes; no drone stuck in a failsafe.
