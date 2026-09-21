---
name: sim-regression
description: Run the headless sim regression (smoke takeoff, square mission, contract check, swarm scenarios), add a scenario, interpret JUnit output and triage flaky failures. Use when the user says run the tests, add a test, or CI is red.
---

# sim-regression

## Run
- Everything: `python3 tests/run.py --profile sim-headless --junit out/junit.xml` (Phase 8; Phase 1 has only `tests/smoke_takeoff.py`).
- One scenario: `python3 tests/run.py --scenario tests/scenarios/<name>.yaml`.
- Each scenario brings the stack up, waits for "ready", runs the mission node, asserts, tears down. Wall-clock budget per scenario: cold ≤ 8 min, warm ≤ 3 min.

## Scenario file
```yaml
name: square_vio
sim_config: sim/configs/single_iris_vio.yaml
mission: ros2 run bisg_vehicle mission_square --ns /drone_1 --side 5 --alt 2
asserts:
  - {type: mode_sequence, expect: [OFFBOARD, AUTO.LAND]}
  - {type: pose_error_max_m, topic: /drone_1/mavros/local_position/pose, truth: /drone_1/state/pose, max: 0.3}
  - {type: contract, ns: /drone_1}
timeout_s: 480
```

## Triage
- Timeout at boot → not a test failure; check cache volumes (`sim-launch`), rerun once. Scenarios should use `sim/configs/headless_fast.yaml` (or their own `perf:` block) so boot stays inside the budget — see `docs/performance.md`.
- Position assert fails only sometimes → lockstep is off, tolerances must absorb FPS jitter; raise tolerance only with a note in the scenario.
- All scenarios fail after a pin change → PX4/MAVROS mode string or param rename; check ADR-003 notes.

## Adding a scenario
1. Copy an existing YAML; keep asserts machine-checkable.
2. Run it 3× locally; record wall time.
3. Add to `tests/scenarios/` and the table in `docs/roadmap.md` Phase 8 if it guards an exit criterion.
