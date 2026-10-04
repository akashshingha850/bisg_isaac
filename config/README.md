# config/

One file: [`bisg.conf`](bisg.conf). Plain `KEY=VALUE`, loaded by `scripts/_common.sh`, exported so
`docker compose` interpolation (`${ISAAC_TAG}`, …) sees it. `./bisg config` prints the merged result
and where every value came from; `./bisg config --edit` opens the file.

It used to be six numbered files (`10-sim.conf` … `60-links.conf`). They were merged: twenty-odd
keys never needed six files, and the "first file to set a key wins" rule meant a key written twice
was silently ignored. The topics survive as comment blocks.

| Block | What lives there |
|---|---|
| What you see | `SIM_VIEW`, `SIM_VIEW_ADDR`, `SIM_WEB_PORT`, `SIM_WEB_INTERVAL` |
| Sim | `SIM_SCENARIO`, `SIM_WAIT_TIMEOUT` |
| ROS 2 / DDS | `ROS_DOMAIN_ID` |
| Drone identity and MAVLink | `DRONE_ID`, `FCU_URL`, `GCS_URL`, `MAVLINK_GCS_PORT` |
| Version pins | `ISAAC_TAG`, `PX4_TAG`, `PEGASUS_TAG`, `ZED_SDK`, base images (ADR territory) |
| Upstream sources | `PEGASUS_REPO`, `ZED_WRAPPER_REPO`, `PX4_REPO`, `ARCHIVE_DIR` |

Rules:

- **One key, one place.** A key written twice in the file keeps the first value. `./bisg config`
  shows the winner.
- Format: `KEY=VALUE`, no spaces around `=`, `#` starts a comment, values must not contain `#`.
- Machine-specific values (your `DISPLAY`, a local IP) belong in `docker/.env`, which is git-ignored
  and overrides this file.
- What the world *contains* — worlds, vehicles, perf knobs — is not here; that is the scenario YAML
  in `docker/sim/configs/`.
- Adding a key: put it in the matching block, add a `conf_default` line in `scripts/_common.sh`,
  pass it to the container in `docker/compose.yaml` if a service needs it, and add it to a `show`
  group in `cmd_config` so `./bisg config` lists it.

`SIM_MODE` and `SIM_STREAM` were merged into one `SIM_VIEW` key. A leftover `SIM_MODE=`,
`SIM_STREAM=` or `SIM_STREAM_ADDR=` in this file or in `docker/.env` is a hard error, not a silent
no-op — `./bisg` tells you what to write instead.

Full explanation, including precedence and every key: [`docs/configuration.md`](../docs/configuration.md).
