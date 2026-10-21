---
name: sim-regression
description: Run the headless sim regression (smoke takeoff, square mission, contract check, swarm scenarios), add a scenario, interpret JUnit output and triage flaky failures. Use when the user says run the tests, add a test, or CI is red.
---

# sim-regression

## Run
- Everything: `python3 tests/run.py --profile sim-headless --junit out/junit.xml` (Phase 8; Phase 1 has only `tests/smoke_takeoff.py`).
- One scenario: `python3 tests/run.py --scenario tests/scenarios/<name>.yaml`.
- Each scenario brings the stack up, waits for "ready", runs the mission node, asserts, tears down. Wall-clock budget per scenario: cold ≤ 8 min, warm ≤ 3 min.

## Migration / pin-change gate (no runner yet — run by hand)
After any Isaac / Pegasus / PX4 pin or launcher-API change, all three must pass (baseline numbers: `archive/docs/migration-report.md`):
1. `./bisg up headless -c single_iris_nozed && ./bisg smoke` (arm → ~1.6 m → land → disarm)
2. `./bisg all headless` (the default: raptor, GPS-denied on baro + LW20 + ZED + flow), then `docker exec bisg-ros bash -lc 'source /opt/ros/jazzy/setup.bash; python3 /workspace/tests/vio_flight.py --drone 1 --alt 1.2 --side -1.0'` (|est − truth| ≤ 0.3 m; 2026-10-15: 2.0 / 1.4 / 2.8 cm). `single_iris_vio` (ZED only, vision height) is no longer a gate: it fails on the sim ZED's z drift (0.85 m)
3. `docker exec bisg-ros python3 /workspace/tests/zed_depth_box.py` (front face within 30 mm; migration value < 1 mm)
Phase exit tests (by hand until the runner exists; `bisg-ros` needs `./bisg ros build` once for `bisg_vehicle`):
- Phase 2: on a fresh `single_iris` run (drone at the spawn: collision prevention stops a square that starts near a wall),
  `docker exec bisg-ros bash -c 'source /workspace/docker/ros/ros2_ws/install/setup.bash && ros2 run bisg_vehicle mission_square --ns /drone_1'`
  (5 m square at 2 m, OFFBOARD -> AUTO.LAND, exit 0; passed 2026-10-10).
- Phase 3 contract: `docker exec bisg-ros bash -c 'source /opt/ros/jazzy/setup.bash && python3 /workspace/tests/check_contract.py --drone 1'`
  (topics/types/rates from the contract table, TF chain, camera_info; 41 pass / 0 fail 2026-10-10). `--real` on the drone.
Position hold (GPS scenario only): `docker exec bisg-sim /isaac-sim/python.sh tests/hold_position.py --instance 0 --alt 2 --hold 20` (drift ≤ 0.3 m; measured 0.03 m).
Sim-level multi-drone: `-c two_iris_nozed` / `four_iris_nozed` / `eight_iris_nozed`, `two_iris_vio_lowres` (two ZED rigs), then `docker exec bisg-sim /isaac-sim/python.sh tests/smoke_takeoff.py --instance N`.
Use `single_iris_vio_lowres` when you need images/depth on a host without the `rmem_max` sysctl (bugs.md B2).

## Scenario file
```yaml
name: square_vio
sim_config: docker/sim/configs/single_iris_vio.yaml
mission: ros2 run bisg_vehicle mission_square --ns /drone_1 --side 5 --alt 2
asserts:
  - {type: mode_sequence, expect: [OFFBOARD, AUTO.LAND]}
  - {type: pose_error_max_m, topic: /drone_1/mavros/local_position/pose, truth: /drone_1/state/pose, max: 0.3}
  - {type: contract, ns: /drone_1}
timeout_s: 480
```

## Triage
- Timeout at boot → not a test failure; check cache volumes (`sim-launch`), rerun once. Scenarios should use `docker/sim/configs/headless_fast.yaml` (or their own `perf:` block) so boot stays inside the budget — see `docs/performance.md`.
- Position assert fails only sometimes → lockstep is off, tolerances must absorb FPS jitter; raise tolerance only with a note in the scenario.
- All scenarios fail after a pin change → PX4/MAVROS mode string or param rename; check ADR-003 notes.

## Adding a scenario
1. Copy an existing YAML; keep asserts machine-checkable.
2. Run it 3× locally; record wall time.
3. Add to `tests/scenarios/` and the table in `docs/roadmap.md` Phase 8 if it guards an exit criterion.
