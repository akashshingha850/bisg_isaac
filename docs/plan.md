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

What the host provided at project start (old PC): Ubuntu 22.04, ROS 2 Humble, Docker 29 with the
nvidia runtime, NVIDIA driver 580, RTX 2080 Ti, 62 GB RAM, 12 cores, 6 TB free SSD.

What the host provides now (new PC, migrated 2026-09-21, see §12): Ubuntu 24.04.5, no host ROS,
Docker 29.1.3 with the nvidia runtime, NVIDIA driver **580.178.04** (see §12 note — the 595.x/R590
branch this GPU shipped with does not work), RTX 4500 Ada Generation 24 GB VRAM, 125 GB RAM,
24 cores, bulk storage on `/opt` (not `/media/ubuntu/ssd`).

Hardware (confirmed 2026-09-12): **Jetson Orin NX on JetPack 7.2** (L4T r38, Ubuntu 24.04,
CUDA 13), **ZED Mini** (USB 3, 63 mm baseline, IMU), **Pixracer** (px4_fmu-v4). Drone count for
the swarm phase is still open; the swarm itself is a later migration of the single-drone twin.

Workstation OS: migration to 24.04 is **done** (§12) — completed by moving to a new PC rather than
an in-place upgrade. All runtime lives in containers, so the migration touched only the host layer;
no image or volume state carried over (rebuilt from source on the new machine).

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
| OS | workstation **Ubuntu 24.04.5**; Jetson Orin NX **JetPack 7.2** (L4T r38, Ubuntu 24.04, CUDA 13) | host OS is irrelevant to containers except driver/toolkit/display | ADR-005 |
| ROS 2 | **Jazzy** (Ubuntu 24.04 containers) | JetPack 7 is 24.04 → ZED SDK images and wrapper are Jazzy; Isaac 5.x and 6.0 bundle a Jazzy bridge (verified on 5.1 and 6.0); LTS to 2029 | ADR-005 |
| Isaac Sim | **6.0.0** (`nvcr.io/nvidia/isaac-sim:6.0.0`, Python 3.12) — migrated from 5.1.0 on 2026-10-02 (rollback: git tag `isaac-5.1-baseline`) | Pegasus Isaac-6 port exists (PR #144) and was tested on 6.0.0; 6.1 is a separate later step (`docs/migrate.md` §3). Report: `docs/migration-report.md` | ADR-002 |
| Pegasus Simulator | **PR #144 head `fcb99c0`** (Isaac Sim 6.0 port, not a release tag; was `v5.1.0` for Isaac 5.1; built from the `third_party/PegasusSimulator` submodule) | local edits on a `local` git branch in the submodule, rebased onto new tags — no fork, no push (`third_party/README.md`) | — |
| PX4 | **v1.17.0** (newest stable on 2026-09-12; `gazebo-classic_iris` airframe and `px4_fmu-v4` board both present) — re-validated on Isaac Sim 6.0 (smoke, VIO flight, depth); v1.16.0 (the Pegasus PR's own test version) also passes and is the fallback; same tag for SITL and Pixracer | firmware on the Pixracer and SITL in sim must be the same version so params/EKF2 behave identically | ADR-003 |
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

Three image families, one `docker/compose.yaml` with profiles. Each image's Dockerfile and
entrypoint live together in their own folder (`docker/sim/`, `docker/ros/`); the single root
compose file's services just point their `build:` at that folder:

| Image | Base | Contains | Profiles |
|---|---|---|---|
| `bisg/sim` | `nvcr.io/nvidia/isaac-sim:6.0.0` (public pull, no NGC login; Ubuntu 24.04, non-root user `isaac-sim`, Python 3.12) | PX4 `v1.17.0` cloned + `px4_sitl_default` built, Pegasus (PR #144 head) built from the `third_party/PegasusSimulator` submodule + pip-installed into Isaac's python, internal **Jazzy** bridge + CycloneDDS selected by ENV; repo bind-mounted at `/workspace` | `sim`, `sim-headless` |
| `bisg/ros` | `ros:jazzy-ros-base` (Ubuntu 24.04, multi-arch: amd64 + arm64) | MAVROS + geographiclib datasets, CycloneDDS, `ros2_ws` built | `ros` (workstation), `jetson` |
| `bisg/zed` | built by `docker/zed/build.sh` from Stereolabs' scripts (`third_party/zed-ros2-wrapper`) | ZED SDK 5.4.1 + wrapper (Jazzy); `desktop` and `l4t-r38` variants | `jetson` |

Rules:
- `network_mode: host` for every service (DDS discovery and MAVLink UDP just work). Isolate
  runs with `ROS_DOMAIN_ID`, not Docker networks.
- PX4 is cloned **inside the image build** at the pinned tag, so `bisg/sim` never needs a
  submodule init just for PX4. Pegasus is different: `bisg/sim` builds **from the
  `third_party/PegasusSimulator` submodule** (not a fresh clone), so local edits there reach the
  image — this means `git submodule update --init third_party/PegasusSimulator` **is** required
  before `docker compose build sim`. `third_party/` also holds `zed-ros2-wrapper`, used directly
  by its `docker/` build scripts. See `third_party/README.md` for the local-branch workflow.
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

## 12. Workstation OS migration (22.04 → 24.04) — done 2026-09-21/22

Done by moving to a new PC (not an in-place upgrade), so no image/volume state carried over —
everything was rebuilt from source. Tracked here so nothing in the project silently depends on
22.04 or on the old machine's specifics.

What changed on the host, what actually happened, and how it was re-checked:

| Host layer | 22.04 / old PC | 24.04 / new PC | Re-check |
|---|---|---|---|
| NVIDIA driver | 580 | New PC shipped with **595.91.07** (R590 branch) — **confirmed incompatible**: segfaults Isaac Sim 5.1's RTX renderer in `librtx.scenedb.plugin.so` right after `app ready` (known upstream bug, isaac-sim/IsaacSim#648/#619/#651/#537). Downgraded to **580.178.04**, which fixed it. `scripts/check_env.sh` now hard-fails on any 59x driver. | `nvidia-smi`, `scripts/check_env.sh` |
| Container toolkit | nvidia runtime present | `nvidia-container-toolkit` had to be installed fresh (apt repo was pre-configured but package wasn't installed); `docker-compose-v2` also had to be installed separately (Ubuntu's `docker.io` package doesn't bundle it) | `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` — passed |
| `docker` group | — | new user `bisg` was not a member; `usermod -aG docker` + `newgrp` needed | `docker info` without sudo |
| Display server | X11 session | still an X11 session on the new PC (`DISPLAY=:0`); Wayland concern didn't materialize | Phase 1 `sim` profile — GUI not re-tested this round, headless confirmed |
| Host ROS 2 | Humble (debug only) | **no ROS installed at all** on the new host | `ros2 topic list` against a running `ros` container — not yet re-run |
| Docker | 29 | 29.1.3, compose v2 (once installed) | `docker compose version` |
| Disk / bulk storage | `/media/ubuntu/ssd` (6 TB) | that mount **does not exist** on the new PC; bulk storage is `/opt` (1.9 TB, ~1.4 TB free). `ARCHIVE_DIR` overridden in `docker/.env` | `df -h /opt` |

Rules (retroactively satisfied by the rebuild, kept here for the next migration):
- No project script may assume host ROS Humble or any 22.04-only apt package — confirmed true; new host has no ROS at all and nothing broke.
- Cache volumes are named Docker volumes, so they survive a host reinstall if preserved/moved — moot this time (new PC, fresh volumes).
- Verified after migrating: Phase 1 headless smoke test (arm → 1.6 m → land → disarm) **PASS**; MAVROS `connected: true` on `/drone_1`; clean `./bisg down` (~10 s, no stray containers).
