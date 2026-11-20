---
name: swarm-spawn
description: Add or remove drone N in a sim scenario — vehicles list, PX4 instance/port derivation, per-drone MAVROS/vehicle compose services via scripts/gen_compose.py, fleet manager registration, VRAM budget update. Use when the user wants more or fewer drones or a new swarm scenario.
---

# swarm-spawn

## Procedure (Phase 6+; swarm is a migration of the proven single-drone twin)
1. Scenario YAML `docker/sim/configs/<scenario>.yaml` → `vehicles:` list: `{id, model, spawn_xyz, spawn_yaw_deg, sensors: {zed: true, lidar: false, tof: {enabled}, optical_flow: {enabled}}}`. ids are 0-based and contiguous.
2. PX4 bridge per drone: the `px4-bridge` service already runs one container per drone and bridge (`bisg-<bridge>-N`, `./bisg px4-bridge plan` shows them; `fcu_url` from the instance math, `px4-sitl` skill). Per-drone `PX4_BRIDGE_DRONE_N` overrides are still a todo.
3. **Not built yet (Phase 6):** `scripts/gen_compose.py` and the `bisg_fleet` package do not exist. The plan: the fleet reads the roster from the same scenario YAML, so there is no separate list. Do not call them; build them only when Phase 6 starts.
4. Start today: `./bisg all headless -c <scenario>` (sim-level multi-drone scenarios: `two_iris_nozed`, `four_iris_nozed`, `eight_iris_nozed`, `two_iris_vio_lowres`).
5. Verify: `ros2 topic list | grep -c mavros/state` equals N; each `/drone_<n>/mavros/state.connected`.
6. Update the VRAM/FPS budget table in `docs/plan.md` (or `docs/budget.md` once it exists) with `nvidia-smi --query-gpu=memory.used --format=csv` at steady state.

## ZED SDK per drone (skill `zed-sdk`)
- Already per-drone in the launcher: drone `id` streams on port `30000 + 2·id` (`zed_sdk_cfg.stream_port`, even + unique), prim `/World/drone_<id+1>_zed`.
- One wrapper per drone: `./bisg zed up --drone N` (container `bisg-zed-N`, namespace `drone_N`, port derived from N). Each wrapper needs the GPU and the neural depth model: budget VRAM per drone before adding more.
- The wrapper's TF frames are unprefixed (`zed_camera_link`, B16): two drones on one TF tree need the per-drone `/drone_<n>/tf` namespacing, or a decision on B16, before any cross-drone TF consumer exists. **Untested with more than one drone.**

## Limits (check `hostname` / `nvidia-smi` first)
- Workstation A: 1x RTX 4500 Ada, 24 GB. Workstation B: 2x RTX 6000 Ada, 48 GB each, shared: stop `lc-chat` (vLLM, ~46 GB per GPU) before a run.
- Prefer headless; 1 camera per drone; use the `_lowres` scenarios beyond 2 ZED drones; disable depth/pointcloud unless the task needs it. Measure; never guess the VRAM per drone.
- Spawn poses ≥ 2 m apart and inside the world's collision bounds.

## Checks before declaring "works"
- All N PX4 instances print "Ready for takeoff"; no port collisions (`ss -ltnp | grep 456`).
- Fleet `collective arm → takeoff → land` completes; no drone stuck in a failsafe.
