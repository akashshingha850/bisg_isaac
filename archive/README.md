# Archive

Finished experiments and superseded documents, kept for reference. Nothing here is used by the running stack
(`./bisg`, compose, tests). Raw run logs (7.4 GB) live **outside** the repo in `~/bisg-archive/logs-2026-10/`.

| Path | What | Why archived |
|---|---|---|
| `px4-link-study/` | MAVROS vs MAVSDK vs uXRCE-DDS on PX4 v1.17 SITL: report (`study-px4-link.md`), harness (`px4link_bench/`, `docker-bench/`), ZED SVO/cuVSLAM study scripts (`tests-study/`, `study_*.sh`, `study_zed.yaml`) | Decision made 2026-10-05: **keep MAVROS**, lean plugin list (`deploy/px4/mavros_lean.yaml`). Re-run on the Orin NX only if the gate in §7 of the report trips |
| `docs/migrate.md`, `migration-report.md`, `isaac-5.1-vs-6.0.md` | the Isaac Sim 5.1 → 6.0 plan, result and comparison | migration is done; the live gotchas stay in `docs/migration-errors.md`; rollback = git tag `isaac-5.1-baseline` |
| `docs/zed-features.md`, `zed-px4-bridge.md`, `video-qgc.md` | ZED feature table, bridge plan, QGC video notes | folded into `docs/zed-stack.md` (ADR-008). `zed-px4-bridge.md` is still the long-form plan for the unbuilt modules (DISTANCE_SENSOR, camera component, FOLLOW/LANDING_TARGET, GNSS) |
| `docs/todo-history-2026-10.md` | the old `docs/todo.md` with every dated "done" entry | `docs/todo.md` is now the live list only |

Docker images from these experiments (`bisg/px4link-bench`, `bisg/perception`, `zedspike/*`, `scratch/px4tmp`) are not deleted: `docker image ls`, then `docker image rm` what you do not need.
