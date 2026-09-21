# Configuration

Three files, each answering a different question.

```
config/bisg.conf    the settings: what you see, which scenario, endpoints, pins, links
docker/.env         this machine only (DISPLAY, local overrides) — git-ignored
sim/configs/*.yaml  the scenario: world, vehicles, PX4 airframe, perf knobs
```

Rule of thumb: **which drone / which world / what I see** → `config/bisg.conf`; **what the world
contains** → the scenario YAML; **my machine is different** → `docker/.env`.

`config/bisg.conf` is plain `KEY=VALUE` because its two readers — bash and `docker compose`
interpolation — speak that and nothing else. Structure (vehicle lists, nested perf, tri-state nulls)
lives in the scenario YAML, which Python reads. Inside the file the old topic split survives as
comment blocks; it was six numbered files until the merge, which was more filing than twenty-odd
keys deserved.

Useful commands:

```
./bisg config                 # every key, its value, and where it came from
./bisg config --edit          # open config/bisg.conf in $EDITOR
./bisg config --path          # print the file's path
```

## Precedence

First one that sets a key wins:

1. command-line flag — `./bisg up headless -c headless_fast`
2. shell environment — `SIM_VIEW=headless ./bisg up`
3. `docker/.env`
4. `config/bisg.conf` — a key written twice keeps the **first** value
5. built-in fallbacks in `scripts/_common.sh` (kept in sync with `config/bisg.conf`)

`./bisg` exports the merged values before it calls `docker compose`, so compose interpolation
(`${ISAAC_TAG}`, `${SIM_CONFIG}`, …) sees them. A raw `docker compose -f docker/compose.yaml …`
call bypasses that and sees only `docker/.env` plus the `${VAR:-default}` fallbacks in the compose file.

New key? Put it in the block that owns the topic, add a `conf_default` line in `scripts/_common.sh`, pass
it to the service in `docker/compose.yaml` if a container needs it, and add it to a `show` group in
`cmd_config` so `./bisg config` lists it. `config/README.md` repeats this next to the file.

## What you see: `SIM_VIEW`

One key decides both whether there is a window and how a remote machine watches. Full guide to the
remote side, including tunnels and VPNs: [remote-access.md](remote-access.md).

```
SIM_VIEW=webrtc      # config/bisg.conf
```

| Value | Window | Served | Reaches you over |
|---|---|---|---|
| `gui` | Isaac window on `$DISPLAY` | — | the machine itself |
| `headless` | none | — | nothing — fastest, use it for tests, CI and timing |
| `web` | none | still frames on `SIM_WEB_PORT` | one TCP port, so a VS Code / SSH forward works |
| `webrtc` | none | interactive WebRTC | TCP 49100 + UDP 47998 — LAN or VPN only |
| `both` | none | `web` + `webrtc` together | both of the above |
| `auto` | `gui` if an X server is reachable, else `headless` | — | — |

`auto` checks for a reachable X socket (`/tmp/.X11-unix/X<n>`), so the same checkout runs windowed on
the workstation and windowless over SSH or in CI.

A window and a stream combine with `+`, for when you want the local window *and* a remote viewer:

```
SIM_VIEW=gui+webrtc
SIM_VIEW=gui+web
```

Override for one run — a bare word replaces only its half, so `./bisg up headless` keeps whatever
stream you configured:

```
./bisg up gui                 # force the window (fails fast if there is no X server)
./bisg up headless            # force no window
./bisg up web                 # headless + browser view
./bisg up webrtc              # headless + WebRTC
./bisg up gui+webrtc          # both halves at once
./bisg up --no-stream         # keep the configured window, serve nothing
SIM_VIEW=headless ./bisg up   # same, for one shell
```

`./bisg view` prints the URLs and addresses for whatever is running.

Two supporting keys: `SIM_VIEW_ADDR` (the address a remote viewer connects to — this host's LAN,
Tailscale or public IP; empty means local clients only, and WebRTC media never arrives without it
from another machine) and `SIM_WEB_PORT` / `SIM_WEB_INTERVAL` for the browser view.

There is no browser URL for `webrtc` — NVIDIA dropped the in-browser client after Isaac Sim 4.0 and
this image carries only the server extensions; `web` is the browser route. Both streams force
`render: true` and re-enable viewport updates, so a view costs sim speed (rtf 0.74 → 0.47 on the
warehouse scene): leave `SIM_VIEW=headless` for regression runs.

**How it reaches the container.** `SIM_VIEW` never enters one. `./bisg` resolves it into the two
values the stack already took: the compose profile (`gui` → service `sim`, `headless` → service
`sim-headless`, i.e. `SIM_HEADLESS=1`) and `SIM_STREAM=off|web|webrtc|both`, which `sim/launcher/launch.py`
reads. A raw `docker compose` call bypasses that resolution and falls back to `SIM_STREAM=off`; pass it
inline instead — `SIM_STREAM=web docker compose -f docker/compose.yaml --profile sim-headless up`. Do not
put `SIM_STREAM` in `docker/.env`: `./bisg` rejects the old keys there rather than half-honouring them.

**Migrating.** `SIM_VIEW` replaced `SIM_MODE` and `SIM_STREAM`; `SIM_VIEW_ADDR` replaced
`SIM_STREAM_ADDR`. A leftover old key in `config/bisg.conf` or `docker/.env` aborts with a message
instead of being silently ignored. `SIM_MODE=gui` + `SIM_STREAM=webrtc` becomes `SIM_VIEW=gui+webrtc`;
`SIM_MODE=headless` + `SIM_STREAM=web` becomes `SIM_VIEW=web`.

## Scenario

```
SIM_SCENARIO=single_iris    # config/bisg.conf: a file name in sim/configs/ (no .yaml), or an absolute path
```

`./bisg up -c headless_fast` overrides it for one run; `-c /abs/path/to/x.yaml` works too. The resolved
path is passed to the container as `SIM_CONFIG=/workspace/sim/configs/<file>.yaml`. Unknown names are
warned about before the container starts.

## Endpoints

| Key | Default | Used by |
|---|---|---|
| `DRONE_ID` | `1` | namespace `/drone_N`, `MAV_SYS_ID N`, PX4 SITL instance `N-1` |
| `FCU_URL` | empty → `udp://:14540+i@127.0.0.1:14580+i` | MAVROS (`docker/ros-entrypoint.sh`) |
| `GCS_URL` | empty → no second link | MAVROS `gcs_url:=` (QGroundControl, logger) |
| `MAVLINK_GCS_PORT` | `14550` | `./bisg debug mavlink` probe |
| `ROS_DOMAIN_ID` | `0` | every container |

Port math lives in `docs/interface-contract.md`; changing it is a contract change, not a config tweak.

## Pins and links

`ISAAC_TAG`, `PX4_TAG`, `PEGASUS_TAG`, `ZED_SDK`, `ISAAC_IMAGE`, `ROS_BASE_IMAGE` feed the image builds and
`scripts/pull_images.sh`; `PEGASUS_REPO`, `ZED_WRAPPER_REPO`, `PX4_REPO` feed `scripts/fetch_third_party.sh`.
Pins are an ADR decision (`docs/plan.md` §4, ADR-003/005) — change the file *and* the ADR, then
`./bisg setup --rebuild`.

## Adding a key

1. Add it to the block of `config/bisg.conf` that owns the topic, with a comment saying what reads it.
2. Add a `conf_default` line in `scripts/_common.sh` so scripts work without the file.
3. If a container needs it, add it to that service's `environment:` in `docker/compose.yaml`.
4. Add it to the right `show` group in `cmd_config` (`scripts/launch.sh`) so `./bisg config` lists it.
