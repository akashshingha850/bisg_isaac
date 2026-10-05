# The PX4 bridge: one service, three bridges, any number of drones

How the companion computer talks to the flight controller is **one compose service, `px4-bridge`** (`docker/compose.yaml`) started **once per drone and per bridge** (container `bisg-<mavros|mavsdk|xrce>-N`), with one image (`bisg/px4-bridge` = `bisg/ros` + the MAVSDK
server + the uXRCE-DDS agent) and **one entrypoint** (`docker/px4-bridge/entrypoint.sh`) that starts whichever bridge `PX4_BRIDGE` names. Everything is env; there is no `command:`.
Why each bridge is what it is, with measurements: `archive/px4-link-study/study-px4-link.md`.
(Not to be confused with `zed-bridge`, the ZED → PX4 module of `docs/zed-stack.md`; it feeds MAVROS.)

| `PX4_BRIDGE` | Starts | What the rest of the system sees | Pick it when |
|---|---|---|---|
| `mavros` (default) | MAVROS (`ros2 run mavros mavros_node`) | ROS 2 topics `/drone_N/mavros/*`; converts ENU/FLU ⇄ NED/FRD | ROS code, the ZED bridge, `vio_mock`, the tests — everything here talks to it |
| `mavsdk` | `mavsdk_server` | gRPC `localhost:50051` for any MAVSDK client, no ROS topics | non-ROS applications, scripting |
| `xrce` | Micro XRCE-DDS Agent | PX4's uORB as ROS 2 topics `/fmu/in|out/*` (`px4_msgs`); no landing/follow target, parameters or camera protocol | native uORB access, highest telemetry rates |
| `none` | nothing (exits 0, not restarted) | — | PX4 reached some other way |

## Choose

Set the variable in **`config/bisg.conf`** (section "PX4 bridge"); `docker/.env` overrides it for this machine, the shell for one run:
```
PX4_BRIDGE=mavros          # mavros | mavsdk | xrce | none — or several, comma separated: mavros,xrce
```
```
./bisg px4-bridge plan                    # what would run and what it connects to
./bisg px4-bridge up                      # start what PX4_BRIDGE names        ./bisg px4-bridge up xrce    start that one (and leave the others running)
./bisg px4-bridge status [--all] | logs [name] -f | down [name | --all] | params [name] | build
PX4_BRIDGE=xrce docker compose -f docker/compose.yaml --profile px4-bridge up -d      # raw compose: same variable, one bridge, default mavros
```
`./bisg all` and `./bisg drone up` start what `PX4_BRIDGE` names (with MAVROS among them, `./bisg all` still adds `vio_mock`); `./bisg mavros up|state|down` still works (it forces `mavros`).
Other settings in `config/bisg.conf`: `MAVROS_PLUGINS` (`lean` = 17 plugins, 9 % CPU / 144 MB; `full` = stock ~50, 28 % / 255 MB), `MAVSDK_PORT`, `XRCE_PORT` (sim), `XRCE_BAUD` (drone).
`--hw` (default on arm64) uses the serial port `/dev/px4` (`DRONE_FCU_URL`, default `serial:///dev/px4:921600`) instead of the sim's UDP.

## Several drones, several methods

Each container is its own compose project (`bisg-px4-<bridge>-<drone>`), so starting one never touches another. `--drone N` picks the drone (PX4 SITL instance N-1: MAVLink 14540+N-1, MAV_SYS_ID N):
```
./bisg px4-bridge up --drone 1                    # drone 1 on PX4_BRIDGE (MAVROS)
./bisg px4-bridge up xrce --drone 2               # drone 2 on the xrce agent: a different method per drone
PX4_BRIDGE=mavros,xrce ./bisg px4-bridge up --drone 3     # drone 3 with both, to compare them on the same flight
./bisg px4-bridge status --all                    # every drone's bridges
```
Tried with two PX4 instances at once: drone 2 and 3 each ran `mavros` + `xrce` side by side (both connected, 65 `/fmu` topics each). Rules: mavros and mavsdk on the same drone share one MAVLink port, so starting one stops the other
(`mavros,mavsdk` in `PX4_BRIDGE` is refused); on a real drone all bridges share the one serial port, so only one runs. The agent port is `XRCE_PORT` for every drone; in SITL each PX4 instance N > 0 publishes under `/px4_N/…`, so
several drones' `/fmu` topics do not collide. Per-drone defaults (e.g. "drone 2 is always xrce") are not in the config yet; give the name on the command line, or add a `PX4_BRIDGE_DRONE_N` lookup when the swarm phase needs it.

## Drone ID = namespace

Every drone has its own id (`DRONE_ID`: in `docker/.env` on each drone's computer, `--drone N` in the sim). It is the same number everywhere: the MAVLink `MAV_SYS_ID` flashed on that Pixracer, MAVROS `tgt_system`,
the PX4 SITL instance (N-1, which fixes the sim's ports), and the ROS namespace `/drone_<id>`:

| Bridge | Topics / endpoint for drone `<id>` | How the id gets there |
|---|---|---|
| `mavros` | `/drone_<id>/mavros/*` (and the ZED wrapper's `/drone_<id>/zed/*`) | `DRONE_ID` → namespace and `tgt_system`; PX4 `MAV_SYS_ID` must equal it |
| `mavsdk` | no ROS topics; gRPC on `MAVSDK_PORT`, MAVLink system id `<id>` | one server per host unless you give each its own `MAVSDK_PORT` |
| `xrce` | `/uav_<id>/fmu/in|out/*` on the Pixracer; in SITL `/px4_<N>/fmu/*` for instance N > 0 (none for instance 0) | PX4 sets it, not us: parameter `UXRCE_DDS_NS_IDX = <id>` (`./bisg px4-bridge params xrce`). PX4's client only offers `uav_<index>`, so xrce topics **cannot** be `/drone_<id>/…`; the contract's `/drone_<id>` namespace is MAVROS's and the ZED's |

If you want xrce under `/drone_<id>` as well, the options are a relay node that republishes `/uav_<id>/fmu/*` there (one more process, ~60 topics) or a PX4 build with a custom startup namespace; neither is built.

## Using them

- **mavros**: `ros2 topic echo /drone_1/mavros/local_position/pose`; plugin list `docker/ros/mavros_lean.yaml`.
- **mavsdk**: gRPC, with the `mavsdk_grpc` package (in the image, or `pip install mavsdk-grpc`):
  ```python
  import asyncio, mavsdk_grpc
  async def main():
      d = mavsdk_grpc.System(mavsdk_server_address="localhost", port=50051)
      await d.connect()
      async for a in d.telemetry.attitude_euler():
          print(a.roll_deg, a.pitch_deg, a.yaw_deg); break
  asyncio.run(main())
  ```
  The native binding (`import mavsdk`, no server) needs no container: point it at `udpin://0.0.0.0:14540` with `PX4_BRIDGE=none`. `Odometry(frame_id=MOCAP_NED)` gives PX4 a NaN position; use `LOCAL_FRD`.
- **xrce**: PX4 1.17 versions its topics (`/fmu/out/vehicle_status_v1`, `…/vehicle_local_position_v1`); `px4_msgs` is `release/1.17` in `/opt/px4_ws` and must match the firmware (`PX4_TAG`).
  The agent's domain is whatever PX4's `UXRCE_DDS_DOM_ID` says (SITL: the sim's `ROS_DOMAIN_ID`). Instances N > 0 publish under `/px4_N/…`; all use agent port 8888.

## Pixracer parameters (`./bisg px4-bridge params [name]`)

mavros / mavsdk: `MAV_1_CONFIG` TELEM 2, `MAV_1_MODE` Onboard, `SER_TEL2_BAUD` 921600, `UXRCE_DDS_CFG` Disabled. xrce: `UXRCE_DDS_CFG` TELEM 2, `SER_TEL2_BAUD` 921600, `MAV_1_CONFIG` Disabled
(QGC then needs USB or a radio), `UXRCE_DDS_DOM_ID` = `ROS_DOMAIN_ID`. Serial enum values are board-specific: confirm in QGC. Changing bridge on a drone = parameters + reboot.

## Needs MAVROS

`vio_mock`, `zed-bridge` (odometry, obstacle map, health), `tests/vio_flight.py`, `./bisg mavros …`. With another bridge, `./bisg px4-bridge up` warns. Porting the ZED bridge's output to another bridge is a todo.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `bisg/px4-bridge:jazzy is not built` | `./bisg px4-bridge build` (needs `bisg/ros:jazzy`; ~10 min for the agent, once per machine) |
| container exits at once, log says `PX4_BRIDGE=… is not mavros | mavsdk | xrce | none` | typo in the variable |
| xrce: agent runs, no `/fmu` topics | PX4's DDS domain ≠ `ROS_DOMAIN_ID`, or the client dials another port (`XRCE_PORT`; SITL 8888), or no PX4 runs; allow ~30 s after PX4 starts |
| xrce: `vehicle_status` empty | the topic is `…_v1` in PX4 1.17 |
| mavsdk: gRPC not listening | `./bisg px4-bridge logs mavsdk`: port taken, or `MAVSDK_URL` malformed |
| mavsdk connects, no data | another process owns the MAVLink port, or `--drone N` ≠ the PX4 instance (`14540 + N-1`) |
| drone: `/dev/px4 not found` | add the Pixracer udev rule (`docs/hardware.md`) |
