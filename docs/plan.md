# Project plan — bisg_isaac digital twin

Last updated: 2026-09-12 (Phase 0; hardware, ordering, PX4 and OS decisions recorded)

## 1. Goal

Build a **digital twin** of a small drone fleet so that a swarm task (survey, inspection,
search, formation flight, …) can be developed and validated in **Isaac Sim** and then
deployed **unchanged** to real drones built from a **Jetson + Pixracer (PX4) + ZED camera**.

"Unchanged" is the design driver. The thing that makes it a twin and not just a simulator is a
**vehicle interface contract** ([interface-contract.md](interface-contract.md)): a fixed set of ROS 2
topics, frames and namespaces that the sim drone and the real drone both expose. Mission,
perception and fleet code only ever talks to that contract.

Non-goals (for now): RL training, photoreal synthetic-data generation, ArduPilot support,
outdoor GPS-only missions without VIO. These can be added later without changing the architecture.

## 2. Starting point

This is a **fresh start**. Earlier attempts (a native Isaac Sim install with a uXRCE-DDS
launcher, and an ArduPilot/Gazebo swarm workspace) are not reused. Lessons carried over:

- A native Isaac install plus host ROS plus hand-started agents drifts fast and is not
  reproducible → everything goes in containers with pinned versions (ADR-002).
- Isaac Sim 5.1 runs on this RTX 2080 Ti (11 GB) but VRAM is the limiting resource → the
  swarm plan sizes cameras and worlds to fit (risk R1).
- Mixing bridges (uXRCE-DDS in sim, something else on hardware) breaks the twin idea → one
  bridge, MAVROS, on both sides (ADR-001).

What the host provides today: Ubuntu 22.04, ROS 2 Humble, Docker 29 with the nvidia runtime,
NVIDIA driver 580, RTX 2080 Ti, 62 GB RAM, 12 cores, 6 TB free SSD.

Hardware (confirmed 2026-09-12): **Jetson Orin NX on JetPack 7.2** (L4T r38, Ubuntu 24.04,
CUDA 13), **ZED Mini** (USB 3, 63 mm baseline, IMU), **Pixracer** (px4_fmu-v4). Drone count for
the swarm phase is still open; the swarm itself is a later migration of the single-drone twin.

Workstation OS: Ubuntu 22.04 today, **migration to 24.04 planned** (see §12). All runtime lives in
containers, so the migration touches only the host layer.

## 3. Target architecture

```
                         SIMULATION (workstation, Docker)                    HARDWARE (per drone, Docker on Jetson)
 ┌───────────────────────────────────────────────────────────┐    ┌──────────────────────────────────────────────┐
 │ isaac-sim container                                       │    │ Pixracer (PX4 vX.Y, px4_fmu-v4)               │
 │  Isaac Sim 5.1 + Pegasus ext                              │    │   ▲ MAVLink @921600 on TELEM2 ↔ Jetson UART   │
 │   ├─ world USD (warehouse preset / site twin, Phase 4)     │    │ ┌─┴──────────────────────────────────────────┐ │
 │   ├─ drone_1..N  (Iris/Pegasus body, sensors)             │    │ │ mavros container   (ns /drone_i)           │ │
 │   │    ├─ stereo cam + depth + IMU  ──► ZED-contract topics│    │ ├────────────────────────────────────────────┤ │
 │   │    └─ lidar (optional)                                │    │ │ zed container      (zed_wrapper, VIO, depth)│ │
 │   └─ Isaac ROS 2 bridge (Jazzy libs bundled)              │    │ ├────────────────────────────────────────────┤ │
 │  PX4 SITL instance i  ◄── MAVLink sim link (TCP 4560+i) ──┘    │ │ vehicle container  (bisg_vehicle: offboard, │ │
 │        │  MAVLink offboard UDP 14540+i / 14580+i           │    │ │   VIO→EKF2 relay, health)                  │ │
 └────────┼──────────────────────────────────────────────────┘    │ └────────────────────────────────────────────┘ │
          ▼                                                        └───────────────┬──────────────────────────────┘
 ┌───────────────────────────────────────────────────────────┐                    │ WiFi / DDS (zenoh bridge)
 │ ros container(s)                                          │                    ▼
 │  mavros  ×N  (ns /drone_i, tgt_system i+1)                │    ┌──────────────────────────────────────────────┐
 │  bisg_vehicle ×N  ─────── SAME CODE / IMAGE ──────────────┼───►│ ground station: bisg_fleet, QGC, RViz, logs  │
 │  bisg_fleet (fleet manager, task allocation)              │    └──────────────────────────────────────────────┘
 └───────────────────────────────────────────────────────────┘
                   ══════ shared: docs/interface-contract.md ══════
```

Key properties:

- **Same `mavros`, `bisg_vehicle`, `bisg_fleet` code and images on both sides.** Only the
  bottom layer differs: PX4 SITL + Isaac sensors in sim, Pixracer + ZED SDK on hardware.
- **PX4 is the flight controller in both worlds** (SITL vs Pixracer). Sim never bypasses PX4.
- **State estimation path is identical**: a VIO odometry stream → MAVROS `odometry/out` →
  PX4 EKF2 external vision. In sim the VIO source is first a mock (ground truth + noise),
  on hardware the ZED Mini's own positional tracking.
- **Fleet layer sees N identical vehicles** under `/drone_i` namespaces regardless of where they run.

## 4. Component choices and version pins

| Component | Pin | Why / notes | Decision |
|---|---|---|---|
| OS | workstation Ubuntu 22.04 → **24.04 planned** (§12); Jetson Orin NX **JetPack 7.2** (L4T r38, Ubuntu 24.04, CUDA 13) | host OS is irrelevant to containers except driver/toolkit/display | ADR-005 |
| ROS 2 | **Jazzy** (Ubuntu 24.04 containers) | JetPack 7 is 24.04 → ZED SDK images and wrapper are Jazzy; Isaac 5.x bundles a Jazzy bridge (verify for 5.1); LTS to 2029 | ADR-005 |
| Isaac Sim | **5.1.0** (`nvcr.io/nvidia/isaac-sim:5.1.0`) | known to run on the 2080 Ti; Pegasus has a matching release | ADR-002 |
| Pegasus Simulator | **v5.1.0** (the release for Isaac Sim 5.1.0; cloned in the sim image at build time) | fork only if a patch is unavoidable | — |
| PX4 | **v1.17.0** (newest stable on 2026-09-12; `gazebo-classic_iris` airframe and `px4_fmu-v4` board both present) — pending the ADR-003 flight check; same tag for SITL and Pixracer | firmware on the Pixracer and SITL in sim must be the same version so params/EKF2 behave identically | ADR-003 |
| PX4 ↔ ROS 2 bridge | **MAVROS 2.15.1** (apt `ros-jazzy-mavros` + extras, amd64 + arm64 verified) | user requirement; serial-friendly on Pixracer; uxrce_dds_client availability on fmu-v4 flash is uncertain | ADR-001 |
| DDS | **CycloneDDS** (`rmw_cyclonedds_cpp`) everywhere; zenoh-bridge-ros2dds across WiFi | reliable across containers with `network_mode: host`; multicast over WiFi is not | ADR-004 |
| ZED SDK | **5.4.1** (`stereolabs/zed:5.4.1-devel-l4t-r38.4` for JetPack 7, `5.4.1-devel-cuda12.8-ubuntu24.04` for x86) | images and wrapper `v5.4.1` verified to exist; built with Stereolabs' own docker scripts | — |
| ZED camera | **ZED Mini** | USB, no capture card; not covered by Stereolabs' Isaac streaming integration (ZED X only) → topic-contract approach | — |
| ZED ROS 2 wrapper | `zed-ros2-wrapper` matching SDK, Jazzy | its topic/frame names define our ZED contract | — |
| Docker | Compose v2, nvidia runtime | present on host | ADR-002 |
| GPU budget | RTX 2080 Ti 11 GB | below Isaac's recommended 3070; swarm tests run headless, 1 camera/drone, ≤1280×720 | risk R1 |

The values above are applied from the pins block of `config/bisg.conf` (`ISAAC_TAG`, `PX4_TAG`, `PEGASUS_TAG`, `ZED_SDK`);
sibling files hold run mode, scenario, view and MAVLink endpoints — see `docs/configuration.md`. Changing
a pin means editing this table, the ADR and `config/bisg.conf`, then `./bisg setup --rebuild`.

## 5. Docker strategy

Three image families, one `docker/compose.yaml` with profiles:

| Image | Base | Contains | Profiles |
|---|---|---|---|
| `bisg/sim` | `nvcr.io/nvidia/isaac-sim:5.1.0` (public pull, no NGC login; Ubuntu 24.04, non-root user `isaac-sim`) | PX4 `v1.17.0` cloned + `px4_sitl_default` built, Pegasus `v5.1.0` cloned + pip-installed into Isaac's python, internal **Jazzy** bridge + CycloneDDS selected by ENV; repo bind-mounted at `/workspace` | `sim`, `sim-headless` |
| `bisg/ros` | `ros:jazzy-ros-base` (Ubuntu 24.04, multi-arch: amd64 + arm64) | MAVROS + geographiclib datasets, CycloneDDS, `ros2_ws` built | `ros` (workstation), `jetson` |
| `bisg/zed` | built by `docker/zed/build.sh` from Stereolabs' scripts (`third_party/zed-ros2-wrapper`) | ZED SDK 5.4.1 + wrapper (Jazzy); `desktop` and `l4t-r38` variants | `jetson` |

Rules:
- `network_mode: host` for every service (DDS discovery and MAVLink UDP just work). Isolate
  runs with `ROS_DOMAIN_ID`, not Docker networks.
- Upstream sources (PX4, Pegasus) are cloned **inside the image build** at the pinned tags, so the
  repo has no large submodules to init before a build. `third_party/` holds optional read/patch clones
  (`scripts/fetch_third_party.sh`) and the ZED wrapper build scripts.
- Isaac caches (`kit`, `ov`, `pip`, `glcache`, `computecache`) are named volumes so a restart
  does not re-shader-compile for 10 minutes.
- GUI: X11 socket + `DISPLAY` passthrough (nvidia runtime + `/tmp/.X11-unix` mount). Headless is the
  default for tests; WebRTC livestream is the fallback for remote viewing.
- Per-drone services are generated, not hand-written: `scripts/gen_compose.py --drones 3`
  emits `mavros_1..3`, `vehicle_1..3` with the right ports/namespaces (Phase 6).
- The same `bisg/ros` image is built for arm64 with buildx and pulled on the Jetson (Phase 5).

## 6. Multi-vehicle model (ports, IDs, namespaces)

For Pegasus vehicle with `vehicle_id = i` (0-based, PX4 instance `-i i`):

| Thing | Value |
|---|---|
| Pegasus ↔ PX4 SITL sim link | TCP `4560 + i` |
| PX4 `MAV_SYS_ID` | `i + 1` |
| MAVROS `fcu_url` | `udp://:$((14540+i))@127.0.0.1:$((14580+i))` |
| MAVROS `tgt_system` | `i + 1` |
| ROS namespace | `/drone_<i+1>` (1-based, human-facing) |
| QGC / GCS MAVLink | `14550` (instance 0) — one QGC sees all if `MAV_0_BROADCAST`/ports are set; verify per PX4 version |

(Port formulas follow PX4's `px4-rc.mavlink`; verify against the pinned PX4 tag and Pegasus's
`px4_mavlink_backend.py` in Phase 1.)

On hardware the same namespace scheme applies; `fcu_url` becomes `serial:///dev/ttyTHS1:921600`
and `tgt_system` is whatever `MAV_SYS_ID` is flashed on that Pixracer (= drone number).

## 7. Data flows

**Control (offboard):** `bisg_vehicle` publishes `mavros/setpoint_position/local` or
`setpoint_raw/local` at ≥ 10 Hz, switches to OFFBOARD via `mavros/set_mode`, arms via
`mavros/cmd/arming`. The controller exposes a small blocking API (connect / wait_ready /
set_offboard / arm / takeoff / goto / land) where every call returns a result with the PX4 ACK,
so a mission reads top to bottom and failures are diagnosable.

**State estimation (GPS-denied):** VIO source → `nav_msgs/Odometry` on
`mavros/odometry/out` (frame `odom`, child `base_link`, ENU/FLU; MAVROS converts to NED/FRD) →
PX4 EKF2 with `EKF2_EV_CTRL` enabled, `EKF2_HGT_REF = vision`. In sim the source is
`vio_mock` (Pegasus ground truth + Gaussian noise + optional latency); on hardware it is the
ZED Mini positional tracking. (Running the ZED SDK against Isaac-rendered stereo is not planned:
Stereolabs' Isaac integration targets the ZED X family.)

**Perception:** Isaac cameras publish under the ZED contract names
(`/drone_i/zed/zed_node/left/image_rect_color`, `.../depth/depth_registered`, `.../imu/data`,
camera_info, TF `zed_camera_link` → optical frames). Downstream nodes (detection, mapping)
cannot tell sim from real.

**Fleet:** `bisg_fleet` publishes tasks on `/fleet/task` and consumes `/drone_i/vehicle/state`
(a compact health/pose/battery/mode message, `bisg_msgs/VehicleState`). Task allocation is
centralized on the ground station for the first version; decentralized later if needed.

**Time:** sim uses `use_sim_time: true` everywhere; Isaac publishes `/clock`. MAVROS
timesync handles PX4 ↔ ROS clock. Hardware uses wall clock; chrony on Jetsons to the GCS.

## 8. Sim-to-real parity rules

1. Any node that runs on a drone must have **no** import of `isaacsim`, `pegasus`, `omni`.
2. A node may *not* subscribe to ground truth (`/drone_i/state/pose` from Pegasus) except
   `vio_mock` and the test harness.
3. Launch files are split: `sim_drone.launch.py` (sensors from Isaac + mock VIO) vs
   `real_drone.launch.py` (ZED wrapper + relay). Everything above them is one launch file.
4. Sensor rates, resolutions and mount offsets in the sim config mirror the hardware BOM
   (`docs/hardware.md`) and are checked by a test.
5. PX4 parameters are stored as `.params` files in `deploy/px4_params/` and loaded into SITL too.

## 9. Risks and mitigations

| # | Risk | Mitigation |
|---|---|---|
| R1 | 11 GB VRAM: 3DGS world + N RTX cameras + ZED SDK does not fit | headless swarm tests; 1 camera/drone; 640×360 for >2 drones; measure per-drone VRAM in Phase 6 and publish a budget table; tuning knobs and the NVIDIA performance handbook in [performance.md](performance.md) |
| R2 | PX4 version drift between SITL and Pixracer | single pin, one `.params` set, CI check that `PX4_VERSION` matches |
| R3 | MAVROS + PX4 1.15/1.16 quirks (mode strings, `odometry/out` frame conventions) | Phase 2 exit test flies a square via MAVROS; VIO frame test in Phase 3 with known transforms |
| R4 | Isaac ROS 2 bridge across containers (FastDDS shared memory, bundled rmw) | CycloneDDS + host networking; smoke test topic echo from the `ros` container in Phase 1 |
| R5 | ZED Mini is not supported by Stereolabs' Isaac integration, so the sim cannot run the real SDK | ZED contract is defined by topic names; mock VIO in sim, real VIO on hardware; validate the gap in Phase 5 with a sim-vs-real trajectory overlay |
| R9 | Isaac Sim 5.1 Jazzy bridge or Pegasus ROS 2 backend misbehaves with Jazzy | check in Phase 1; fallback in ADR-005 |
| R10 | ZED SDK minor that supports JetPack 7.2 lags or changes topic names | pin in Phase 5; contract checker catches renames |
| R6 | WiFi DDS discovery storms with N Jetsons | zenoh-bridge-ros2dds per drone; drone-local traffic stays on the Jetson |
| R7 | Isaac Sim licence/NGC pull, 20+ GB image | pull once, `docker save` to the SSD; document offline restore |
| R8 | Lockstep off → non-deterministic tests | tests assert on tolerances not exact traces; revisit lockstep once sim FPS is known |

## 10. Open questions

Answered 2026-09-12: Jetson **Orin NX, JetPack 7.2**; camera **ZED Mini**; **swarm after** the
single-drone twin and assets; PX4 = **newest Pegasus-compatible stable** (ADR-003).

Still open (record in `hardware.md` when known):
- Orin NX RAM variant; exact L4T / CUDA versions from the device.
- Frame, motors, props, battery of the real quad (needed for the Phase 4 vehicle model).
- Which PX4 version is currently flashed on the Pixracer, if any.
- Number of drones for the first hardware swarm (Phase 7).
- Which real site is the primary deployment location (Phase 4 twin world)?
- Is one QGC instance for the whole swarm required, or only for safety override?

## 11. Decisions

- [ADR-001 MAVROS instead of uXRCE-DDS](decisions/ADR-001-mavros.md)
- [ADR-002 Docker-first, Isaac Sim in a container](decisions/ADR-002-docker.md)
- [ADR-003 One PX4 version for SITL and Pixracer](decisions/ADR-003-px4-version.md)
- [ADR-004 CycloneDDS + zenoh bridge for the fleet network](decisions/ADR-004-dds.md)
- [ADR-005 ROS 2 Jazzy in all containers](decisions/ADR-005-ros2-jazzy.md)

## 12. Workstation OS migration (22.04 → 24.04, planned)

Tracked here so nothing in the project silently depends on 22.04. Do the migration between phases,
ideally right after Phase 1 (only one image family to re-validate) or before Phase 5.

What changes on the host, and what to re-check:

| Host layer | 22.04 today | After 24.04 | Re-check |
|---|---|---|---|
| NVIDIA driver | 580 | reinstall (≥ 570 for Isaac 5.1) | `nvidia-smi`, `scripts/check_env.sh` |
| Container toolkit | nvidia runtime present | reinstall `nvidia-container-toolkit`, `nvidia-ctk runtime configure` | `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` |
| Display server | X11 session | 24.04 defaults to **Wayland** → Isaac GUI passthrough needs XWayland (`xhost +local:`) or an X11 session; livestream is the fallback | Phase 1 `sim` profile |
| Host ROS 2 | Humble (debug only) | Jazzy native (optional) — matches the containers | `ros2 topic list` against a running `ros` container |
| Docker | 29 | keep; compose v2 | `docker compose version` |
| Disk / SSD mounts | `/media/ubuntu/ssd` | same mount path so compose volume paths and cache volumes survive | `docker volume ls` |

Rules until then:
- No project script may assume host ROS Humble or any 22.04-only apt package.
- Cache volumes are named Docker volumes (not bind mounts under `/home`), so a reinstall keeps them if `/var/lib/docker` is preserved or moved to the SSD.
- Before migrating: `docker save` the `bisg/*` and `isaac-sim` images to the SSD; export the list of named volumes.
- After migrating: run the Phase 1 headless smoke test and the latest phase's exit test before continuing work.
