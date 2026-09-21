# third_party

Pinned upstream sources, fetched by `scripts/fetch_third_party.sh` (git-ignored until `git init`,
then added as submodules at the same tags).

| Repo | Tag | Used for |
|---|---|---|
| PegasusSimulator | `v5.1.0` (matches Isaac Sim 5.1.0) | reading the API; patches if unavoidable. The sim image clones it itself. |
| zed-ros2-wrapper | `v5.4.1` (ZED SDK 5.4.1) | its `docker/` build scripts produce our `bisg/zed` images |
| PX4-Autopilot (optional, `WITH_PX4=1`) | `v1.17.0` | reading `px4-rc.*`, param names, `px4_fmu-v4` build for the Pixracer |
