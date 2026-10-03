# Roadmap

Phases are sequential; each has an **exit test** that must pass before the next starts.
Effort is a rough guess for part-time work. Dates are deliberately absent — this is built gradually.

Ordering principle (user decision, 2026-09-12): **single-drone digital twin first** — sim, then the
assets and models (vehicle + site), then one real drone. The **swarm is a later migration** of that
proven single-drone twin to N vehicles.

| Phase | Name | Delivers | Effort |
|---|---|---|---|
| 0 | Foundations | this doc set, repo skeleton, pins, open questions answered | 1 week |
| 1 | Dockerized single-drone sim | `compose --profile sim`: Isaac + Pegasus + PX4 SITL, one drone flies via QGC | 2–3 weeks |
| 2 | ROS 2 + MAVROS control | `bisg/ros` image (Jazzy), MAVROS to SITL, offboard mission node, sim time | 2 weeks |
| 3 | Sensors + ZED Mini contract + VIO | Isaac stereo/depth/IMU under ZED names, mock VIO → EKF2, GPS-denied flight | 3 weeks |
| 4 | Digital-twin assets and models | vehicle USD matching the real quad, site world with collision, geo-reference, scenarios | 3–4 weeks |
| 5 | Hardware single drone | Jetson Orin NX containers (same images), Pixracer flashed + params, ZED Mini VIO, tethered flight | 4 weeks |
| 6 | Swarm in sim (migration) | N drones, N MAVROS, fleet manager, formation/waypoint tasks, VRAM budget | 3 weeks |
| 7 | Hardware swarm | multi-Jetson networking, fleet on ground station, same tasks as Phase 6 at the site | 4 weeks |
| 8 | Task library + CI | mission scenario library, headless regression in Docker, docs for adding a task | ongoing |

---

## Phase 0 — Foundations
**Goal:** agree on architecture, pins and layout before writing runtime code.

Deliverables
- `docs/` set (plan, roadmap, todo, skills, interface-contract, hardware, ADRs).
- Repo skeleton directories, `.gitignore`, `git init`, first commit.
- Open questions answered: Jetson Orin NX / JetPack 7.2, ZED Mini, swarm later, PX4 newest Pegasus-compatible (done 2026-09-12); remaining: drone count for Phase 7, current Pixracer firmware, deployment site.
- Claude Code project skills stubbed in `.claude/skills/`.

Exit test
- A reader with no context can explain from the docs what runs where, and which topic a mission node uses to move a drone.

## Phase 1 — Dockerized single-drone sim
**Goal:** one command brings up Isaac Sim + Pegasus + PX4 SITL with one drone that can be flown from QGroundControl.

Deliverables
- `docker/sim/Dockerfile` (Isaac 6.0 base since the 2026-10 migration — was 5.1; Pegasus installed, PX4 SITL built at the pinned tag), cache volumes, X11 + headless variants.
- `docker/compose.yaml` profiles `sim` and `sim-headless`.
- `sim/launcher/launch.py` + `sim/configs/single_iris.yaml`: world preset, vehicle, PX4 backend (autolaunch), instance/port derivation.
- `third_party/` submodules pinned (Pegasus tag, PX4 tag) — ADR-003 filled in after the compatibility run.
- `scripts/check_env.sh`: driver, nvidia runtime, X11, disk, VRAM.

Exit test
- `docker compose --profile sim up` → drone visible in a warehouse world; QGC connects on 14550; takeoff + land from QGC.
- `docker compose --profile sim-headless up` + a script arms, takes off to 2 m, lands, exits 0 in under 8 minutes cold.

## Phase 2 — ROS 2 + MAVROS control
**Goal:** move the drone from a ROS 2 node through MAVROS, with the same node that will later run on the Jetson.

Deliverables
- `docker/ros/Dockerfile` (ROS 2 **Jazzy** on Ubuntu 24.04, MAVROS + extras, geographiclib, CycloneDDS, colcon build of `ros2_ws`), amd64 + arm64 buildx.
- `ros2_ws/src/bisg_msgs` (`VehicleState`, `VehicleCmd`, `Task`), `bisg_vehicle` (`offboard_controller` node + Python API), `bisg_bringup/launch/sim_drone.launch.py`.
- MAVROS per-drone launch wrapper with namespace + `fcu_url` derivation; `use_sim_time` wiring; Isaac `/clock` (Isaac bridge set to Jazzy libs).
- Smoke test that the `ros` container sees Isaac bridge topics (ADR-004 validated).

Exit test
- `ros2 run bisg_vehicle mission_square --ns /drone_1` flies a 5 m square at 2 m altitude and lands; `mavros/state` shows OFFBOARD→AUTO.LAND; test exits 0.

## Phase 3 — Sensors, ZED Mini contract, VIO
**Goal:** the sim drone exposes the same sensor topics as the real ZED Mini drone, and PX4 flies GPS-denied on VIO.

Deliverables
- Isaac camera rig on the drone: stereo pair with the ZED Mini baseline (63 mm), HD720 intrinsics, depth, IMU; published under ZED wrapper names + TF tree per `interface-contract.md`.
- `bisg_vehicle/vio_mock`: Pegasus ground truth + noise + latency → `mavros/odometry/out`.
- PX4 params file for EV fusion (`EKF2_EV_CTRL`, `EKF2_HGT_REF`, `EKF2_EV_DELAY`, GPS disabled) loaded into SITL.
- Contract checker: `tests/check_contract.py` compares live topic list/types/rates against `interface-contract.md`.
- Optional (done 2026-10-03, `docs/zed-sdk-sim.md`): the real ZED SDK + wrapper against Isaac's streamed ZED Mini twin (`ZED_SOURCE=sdk`, `./bisg zed up|check`), so downstream code is identical in sim and on the Jetson. Needs Isaac Sim 6.0.

Exit test
- With GPS disabled in SITL, the square mission from Phase 2 completes on mock VIO; `mavros/local_position/pose` vs ground truth error < 0.3 m.
- `check_contract.py` passes against the sim drone.

## Phase 4 — Digital-twin assets and models
**Goal:** the sim vehicle and the sim world are faithful models of the real quad and the real site.

Deliverables
- **Vehicle model** `sim/assets/vehicles/bisg_quad/`: USD of the real frame (mass, inertia, arm length, motor/prop placement, ZED Mini mount pose, Pixracer IMU position), Pegasus thrust curve fitted to the real motor/prop/battery, registered as a Pegasus vehicle preset. Documented measurement procedure in `docs/hardware.md`.
- **Site world** `sim/worlds/<site>/`: capture route chosen (3DGS/NuRec via nerfstudio/Postshot, or photogrammetry mesh), render asset + invisible collision proxies (floor, walls, obstacles) + spawn points + geofence.
- Geo-reference: PX4 `LAT/LON/ALT` home = real site origin so GPS and local frames match hardware.
- Asset pipeline docs: how to re-capture, re-export, and validate scale (a known 1 m reference in the scene).
- Scenario YAMLs for one drone: `hover_check`, `square`, `survey_strip`, `inspect_structure`.

Exit test
- Phase 3 exit test runs with the `bisg_quad` model in the site world with the same task YAML; measured hover thrust / climb rate in sim within 15 % of the real quad's bench numbers (or of the spec sheet until Phase 5 provides bench data).

## Phase 5 — Hardware single drone
**Goal:** one real drone (Jetson Orin NX, JetPack 7.2, Pixracer, ZED Mini) runs the Phase 2/3 stack.

Deliverables
- `deploy/jetson/compose.yaml` profile `jetson`: `mavros`, `zed`, `vehicle` services (arm64 images from Phase 2/3; ZED image on the L4T r38 base).
- Pixracer: PX4 pinned tag flashed, `deploy/px4_params/drone_1.params` (TELEM2 921600 onboard mode, EV fusion, safety).
- `bisg_bringup/launch/real_drone.launch.py`: ZED wrapper + `vio_relay` (zed odom → `mavros/odometry/out`).
- Bench procedure (`hardware.md`): props off, MAVROS heartbeat, EKF2 EV fusion healthy (`ekf2 status`), offboard on bench.
- udev rules, boot-time service, log collection. Bench numbers fed back into the Phase 4 vehicle model.

Exit test
- Tethered/indoor hover + 3 m square on VIO, props on, with the *same* `mission_square` from Phase 2. Flight log reviewed (EKF innovations, EV delay). Sim vs real trajectory overlay within tolerance.

## Phase 6 — Swarm in sim (migration)
**Goal:** the single-drone twin becomes N identical drones under `/drone_1..N`, driven by a fleet manager.

Deliverables
- Launcher supports a `vehicles:` list (id, spawn pose, sensor set); PX4 instance/port math automated.
- `scripts/gen_compose.py --drones N` emits per-drone `mavros_i` / `vehicle_i` services.
- `bisg_fleet`: fleet manager (task queue, allocation, geofence, collective arm/land/RTL), formation and waypoint-split tasks.
- VRAM/FPS budget table for 1–4 drones with/without cameras, headless and GUI, in the site world.

Exit test
- 3 drones take off, fly a line formation, split into a 3-way area survey, return and land, headless, exits 0.
- Budget table committed; sim runs ≥ 15 FPS (render) at the chosen swarm config.

## Phase 7 — Hardware swarm
**Goal:** the Phase 6 tasks fly on N real drones.

Deliverables
- Network: per-drone `zenoh-bridge-ros2dds` (or CycloneDDS peer list), ground-station router, `ROS_DOMAIN_ID` plan, bandwidth budget (no raw images over WiFi).
- Fleet manager on the ground station, single QGC for safety override, kill-switch procedure.
- Deployment script: pull images, push params, health check, per-drone config from one `fleet.yaml`.

Exit test
- 2–3 drones execute `formation_demo` then `survey` at the site; logs show all vehicles followed the fleet plan within tolerance.

## Phase 8 — Task library + CI
**Goal:** adding a swarm task is a documented, tested workflow.

Deliverables
- `tests/scenarios/*.yaml` run headless in CI (self-hosted runner on this workstation with the GPU).
- Task-author guide: contract → task node → sim scenario → hardware checklist.
- Nightly headless regression with JUnit output and a VRAM/FPS trend.

Exit test
- A new task (e.g. perimeter patrol) goes from idea to passing sim test using only the guide, no undocumented steps.
