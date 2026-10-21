# Archive

Finished experiments and superseded documents, kept for reference. Nothing here is used by the running stack
(`./bisg`, compose); only `vio-2026-10-15/` is read, by a unit test. Raw run logs (7.4 GB) live **outside** the repo in `~/bisg-archive/logs-2026-10/`.

| Path | What | Why archived |
|---|---|---|
| `px4-link-study/` | MAVROS vs MAVSDK vs uXRCE-DDS on PX4 v1.17 SITL: report (`study-px4-link.md`), harness (`px4link_bench/`, `docker-bench/`), ZED SVO/cuVSLAM study scripts (`tests-study/`, `study_*.sh`, `study_zed.yaml`) | Decision made 2026-10-05: **keep MAVROS**, lean plugin list (`deploy/px4/mavros_lean.yaml`). Re-run on the Orin NX only if the gate in §7 of the report trips |
| `docs/migrate.md`, `migration-report.md`, `isaac-5.1-vs-6.0.md` | the Isaac Sim 5.1 → 6.0 plan, result and comparison | migration is done; the live gotchas stay in `docs/migration-errors.md`; rollback = git tag `isaac-5.1-baseline` |
| `docs/zed-features.md`, `zed-px4-bridge.md`, `video-qgc.md` | ZED feature table, bridge plan, QGC video notes | folded into `docs/zed-stack.md` (ADR-008). `zed-px4-bridge.md` is still the long-form plan for the unbuilt modules (DISTANCE_SENSOR, camera component, FOLLOW/LANDING_TARGET, GNSS) |
| `docs/todo-history-2026-10.md` | the old `docs/todo.md` with every dated "done" entry | `docs/todo.md` is now the live list only |
| `vio-2026-10-15/` | ZED VIO flights of the GPS-denied calibration: PX4-log extracts (`topics.npz`), `vio_eval` reports and plots per run | evidence for `docs/vio.md` and `ekf2_vio_flow_range.params`; **read by `tests/unit/test_vio_eval.py`** (keep it) |
| `vio-bench/<date>-<host>/` | `./bisg vio bench --archive` campaigns: summary (verdict, experimental setup, results, ablation, calibration, reliability), figures, per-flight reports + log extracts (the `.ulg` files stay in `$ARCHIVE_DIR/vio_bench/`) | results of the VIO calibration / ablation study per machine (`docs/vio.md`) |

Docker images from these experiments (`bisg/px4link-bench`, `bisg/perception`, `zedspike/*`, `scratch/px4tmp`) are not deleted: `docker image ls`, then `docker image rm` what you do not need.
