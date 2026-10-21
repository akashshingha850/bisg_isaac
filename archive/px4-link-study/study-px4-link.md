# Study: how the Jetson talks to PX4 — MAVROS vs MAVSDK vs uXRCE-DDS

Date: 2026-10-04 · PX4 **v1.17.0** · ROS 2 **Jazzy** (Ubuntu 24.04) · target: Jetson Orin NX (JetPack 7.2) + Pixracer (fmu-v4)
Source of the three options: Seeed's [Control PX4 with reComputer Jetson](https://wiki.seeedstudio.com/control_px4_with_recomputer_jetson/)
(uXRCE-DDS, MAVSDK, MAVROS; their stack was Orin Nano + Pixhawk 4 Mini + PX4 v1.15 + ROS 2 Humble).
Reproduce everything with `tools/px4link_bench/` (see §9). Raw data: `logs/px4link_bench/`.

## TL;DR

- **uXRCE-DDS is not suitable as the *only* link for this project**, even though it is the lightest and has the highest telemetry rates: it cannot carry
  landing target, follow target, STATUSTEXT, parameters or the MAVLink camera protocol (§5), it welds `px4_msgs` to the exact firmware (PX4 1.17 renamed
  topics to `…_v1`), its command round trip is the *slowest* measured (16.5 ms) and the Pixracer (fmu-v4, constrained RAM) has never been run with it.
- **MAVROS is the heaviest, but only because of its default plugin list.** The default `px4.launch` plugin set idles at **28 % of a core / 255 MB**
  (and 53 % at 200 Hz setpoints); the same MAVROS with the 17 plugins this project needs (`tools/px4link_bench/mavros_lean.yaml`) idles at **9 % / 144 MB** —
  a 3× cut for one YAML file. Under CPU contention default MAVROS collapses (command round trip 4 → **65 ms, max 407 ms**), lean MAVROS degrades to 11 ms.
- **MAVSDK 4.x native (`pip install mavsdk`) is the lightest and quickest MAVLink option**: no bridge process, 71 MB, ~2–3 % of a core, 4.2 ms command
  round trip, unchanged under load (3.6 ms). The **gRPC flavour** (what Seeed's page installs) costs a `mavsdk_server` process and **3× the latency** (12 ms).
- **Accuracy is identical** for all of them: the same external-vision pose arrives at PX4 with 0 m / 0.0006° / 0 error — MAVROS' ENU/FLU → NED/FRD conversion is
  correct (the thing ADR-001 relied on), MAVSDK and DDS are correct *when the caller converts* (a hidden MAVSDK trap: frame `MOCAP_NED` gives PX4 a NaN position, `LOCAL_FRD` works).
- **Recommendation (§7):** stay on **MAVLink**; keep **MAVROS, but lean**, as the single link owner today (already integrated, converts frames, covers almost every message
  the ZED→PX4 bridge needs); treat **MAVSDK 4.x native** as the designated replacement/companion *if* the Orin NX shows lean MAVROS is too heavy — decision gate and
  Jetson measurement list in §7. This study ran on a workstation, not on the Orin NX: absolute CPU numbers do not transfer, the ordering and the 3×/15× ratios should.


## 1. What was compared

| | What it is | PX4 side | Companion side |
|---|---|---|---|
| **MAVROS** 2.15 | MAVLink ⇄ ROS 2 topics/services, ~50 plugins, does ENU/FLU ⇄ NED/FRD | MAVLink "onboard" instance (`MAV_1_CONFIG`) | `mavros_node` (router + one node per plugin) |
| **MAVSDK** | C++ library, plugin API (`action`, `telemetry`, `offboard`, `mocap`, `mavlink_direct`, `camera_server`, …) | same MAVLink instance | **4.x native binding** (`pip install mavsdk`: no server, no gRPC — new since v4) **or** the older **gRPC** package (`mavsdk-grpc` = what Seeed's page installs: Python → gRPC → `mavsdk_server` → MAVLink) |
| **uXRCE-DDS** | PX4 uORB topics exposed as ROS 2 topics (`/fmu/in|out/*`, `px4_msgs`) | `uxrce_dds_client` (in the firmware) | `MicroXRCEAgent` (v2.4.3 for Jazzy) + `px4_msgs` built for the exact firmware |

Two extra variants were tested because "test each setting" matters: **MAVROS lean** (`plugin_allowlist` with only the 17 plugins this
project uses — `tools/px4link_bench/mavros_lean.yaml`) and **both MAVSDK flavours**. Zenoh (experimental in PX4 1.17) was not tested.

## 2. Method

- **Standalone PX4 v1.17.0 SITL with the built-in SIH physics** (container `bisg-px4-sih`, no Isaac Sim): real-time, unloaded, restarted
  before every run. The same PX4 serves MAVLink (UDP 14540/14580) and DDS (UDP 8888) — on the drone it is one *or* the other per UART.
- **Companion container** `bisg/px4link-bench:jazzy` (from `bisg/ros:jazzy`: + Micro-XRCE-DDS-Agent v2.4.3, `px4_msgs` release/1.17, MAVSDK 4.0.3 + `mavsdk-grpc`).
- Identical work per method (`tools/px4link_bench/bench.py`), each phase on a fresh PX4, bridge started by the client so its CPU/RSS is measured apart:

| Phase | Work | Metrics |
|---|---|---|
| idle | connect, then nothing for 20 s (6 s warm-up skipped) | connect time, CPU spent connecting, steady CPU + RSS of bridge and client |
| telemetry | subscribe attitude, position/velocity, armed state, 20 s, **default stream settings** | arrival rate, inter-arrival jitter (p95/max), CPU, PX4 tx bytes/s |
| rtt | 200 × "set HOLD mode" and wait for the ACK | p50/p95/p99/max round trip |
| odom | external-vision pose at 30 Hz for 20 s, **sent as a ROS/ZED user has it (ENU/FLU)** | what PX4 received (rate, position/attitude/velocity error vs the pose that was meant), PX4 rx bytes/s |
| offboard | arm + OFFBOARD + position setpoints at 50/100/200 Hz | rate PX4 registers vs sent |
| *_load | telemetry and rtt again with client+bridge pinned to 2 cores that two busy loops also occupy | does latency/jitter survive CPU contention (the Jetson also runs the ZED wrapper) |

- **Caveats, stated up front:** (1) measured on a 24-core x86 workstation, not on the Orin NX — CPU percentages are *relative*; expect an
  Orin NX core to be roughly 2–4× slower, so read "50 % of a core here" as "most of a core there". (2) UDP loopback, not a 921600-baud UART
  (bandwidth is reported in bytes/s so it can be compared with the ~92 kB/s a 921600 UART carries). (3) PX4 SIH is real-time; SIH time is
  lockstep-based so PX4-side timestamps cannot be compared with companion wall time — latency is therefore measured as request→ACK round trip.
  (4) One-way telemetry latency was not measured. (5) Another session's Isaac Sim + ZED stack ran on the same host during the final runs (this study used PX4 instance 1 — MAVLink 14541/14581, DDS 8889, ROS domain 77 — and pinned its contention test to cores 22–23, so the two did not share ports; some CPU/cache noise from the other stack cannot be excluded, which is why every CPU number is a mean of 2 repeats and only large ratios are drawn on).

## 3. Results (final data set: `logs/px4link_bench/final/results.json`, 65 runs; repeats ×2 for idle/telemetry/rtt/odom)

All numbers are means over repeats on the workstation. "Bridge" = `mavros_node` / `MicroXRCEAgent` / `mavsdk_server`; MAVSDK native has no bridge process (the library runs
inside the client). CPU is percent of one core.

#### Connect, idle footprint (bridge running, nothing flowing; 6 s warm-up excluded)

| method | connect | CPU spent connecting | bridge CPU (idle) | bridge RSS | client CPU | client RSS |
|---|---|---|---|---|---|---|
| MAVROS (default plugins) | 1.0 s | 1.0 s | 28.4 % | 255 MB | 0.4 % | 100 MB |
| MAVROS (lean plugin list) | 0.9 s | 0.3 s | 9.1 % | 144 MB | 0.4 % | 97 MB |
| MAVSDK 4.x (native) | 0.9 s | n/a | 0.0 % | 0 MB | 1.6 % | 71 MB |
| MAVSDK (gRPC) | 1.0 s | 0.0 s | 1.6 % | 18 MB | 0.3 % | 82 MB |
| uXRCE-DDS | 7.8 s | 0.0 s | 0.9 % | 27 MB | 0.5 % | 100 MB |

#### Telemetry in (PX4 -> companion), default stream settings, 20 s

| method | attitude rate | attitude gap p95 | attitude gap max | position rate | position gap p95 | bridge CPU | client CPU | PX4 tx B/s on that link |
|---|---|---|---|---|---|---|---|---|
| MAVROS (default plugins) | 49 Hz | 21.0 ms | 22.2 ms | 30 Hz | 37.0 ms | 27.9 % | 3.2 % | 24566 |
| MAVROS (lean plugin list) | 49 Hz | 21.0 ms | 23.1 ms | 30 Hz | 37.0 ms | 9.8 % | 3.5 % | 24543 |
| MAVSDK 4.x (native) | 49 Hz | 21.0 ms | 22.3 ms | 29 Hz | 37.1 ms | 0.0 % | 3.0 % | 24863 |
| MAVSDK (gRPC) | 49 Hz | 21.0 ms | 22.3 ms | 30 Hz | 37.0 ms | 2.0 % | 2.0 % | 24285 |
| uXRCE-DDS | 98 Hz | 12.5 ms | 13.3 ms | 49 Hz | 20.9 ms | 1.1 % | 3.0 % | 39160 |

#### Command -> ACK round trip (200 x set HOLD mode; PX4 SIH on the same host)

| method | p50 | p95 | p99 | max | bridge CPU |
|---|---|---|---|---|---|
| MAVROS (default plugins) | 4.3 ms | 5.1 ms | 5.6 ms | 6.0 ms | 46.6 % |
| MAVROS (lean plugin list) | 4.3 ms | 5.0 ms | 5.3 ms | 45.0 ms | 15.2 % |
| MAVSDK 4.x (native) | 4.2 ms | 4.7 ms | 5.1 ms | 5.4 ms | 0.0 % |
| MAVSDK (gRPC) | 12.2 ms | 19.2 ms | 20.9 ms | 21.3 ms | 2.4 % |
| uXRCE-DDS | 16.5 ms | 17.3 ms | 17.5 ms | 17.8 ms | 1.0 % |

#### External-vision odometry, 30 Hz for 20 s: what PX4 received (pose sent: ENU/FLU like a ROS/ZED user has it)

| method | PX4 topic | rate seen by PX4 | position err | attitude err | velocity err | ang-vel err | bridge CPU | client CPU | PX4 rx B/s |
|---|---|---|---|---|---|---|---|---|---|
| MAVROS (default plugins) | vehicle_visual_odometry | 30.5 Hz | 0.00000 m | 0.0006° | 0.00000 | 0.00000 | 31.6 % | 1.4 % | 7682 |
| MAVROS (lean plugin list) | vehicle_visual_odometry | 30.0 Hz | 0.00000 m | 0.0006° | 0.00000 | 0.00000 | 10.9 % | 1.4 % | 7561 |
| MAVSDK 4.x (native) | vehicle_visual_odometry | 30.0 Hz | 0.00000 m | 0.0006° | 0.00000 | 0.00000 | 0.0 % | 2.5 % | 7124 |
| MAVSDK (gRPC) | vehicle_visual_odometry | 29.0 Hz | 0.00000 m | 0.0006° | 0.00000 | 0.00000 | 2.5 % | 2.3 % | 7124 |
| uXRCE-DDS | vehicle_visual_odometry | 31.0 Hz | 0.00000 m | 0.0006° | 0.00000 | 0.00000 | 1.1 % | 0.9 % | 3560 |

#### Offboard position setpoints: rate PX4 actually registers vs rate sent (armed + OFFBOARD, 16 s)

| method | target 50 Hz: PX4 / sent | target 100 Hz | target 200 Hz |
|---|---|---|---|
| MAVROS (default plugins) | 51 / 50 Hz (Offboard), bridge 37 % + client 2 % | 102 / 100 Hz (Offboard), bridge 39 % + client 2 % | 203 / 200 Hz (Offboard), bridge 53 % + client 4 % |
| MAVROS (lean plugin list) | 51 / 50 Hz (Offboard), bridge 11 % + client 2 % | 102 / 100 Hz (Offboard), bridge 14 % + client 2 % | 204 / 200 Hz (Offboard), bridge 18 % + client 3 % |
| MAVSDK 4.x (native) | 51 / 50 Hz (Offboard), bridge 0 % + client 3 % | 102 / 100 Hz (Offboard), bridge 0 % + client 4 % | 203 / 200 Hz (Offboard), bridge 0 % + client 6 % |
| MAVSDK (gRPC) | 51 / 50 Hz (Offboard), bridge 3 % + client 3 % | 102 / 100 Hz (Offboard), bridge 4 % + client 5 % | 203 / 200 Hz (Offboard), bridge 5 % + client 7 % |
| uXRCE-DDS | 51 / 50 Hz (Offboard), bridge 1 % + client 1 % | 102 / 100 Hz (Offboard), bridge 2 % + client 1 % | 205 / 200 Hz (Offboard), bridge 2 % + client 2 % |

#### Under CPU contention: client + bridge pinned to 2 cores that two busy loops also occupy (all other numbers are unloaded)

| method | command RTT p50 | p95 | max | attitude gap p95 | attitude gap max | attitude rate |
|---|---|---|---|---|---|---|
| MAVROS (default plugins) | 64.6 ms | 77.3 ms | 407 ms | 24.7 ms | 108 ms | 48 Hz |
| MAVROS (lean plugin list) | 11.1 ms | 29.6 ms | 41 ms | 25.2 ms | 30 ms | 49 Hz |
| MAVSDK 4.x (native) | 3.6 ms | 4.5 ms | 7 ms | 21.7 ms | 25 ms | 49 Hz |
| MAVSDK (gRPC) | 12.3 ms | 17.1 ms | 21 ms | 21.2 ms | 28 ms | 49 Hz |
| uXRCE-DDS | 16.3 ms | 17.2 ms | 21 ms | 12.7 ms | 18 ms | 98 Hz |

Reading notes: (a) MAVROS's default telemetry rates are PX4's onboard-profile defaults (attitude ≈ 50 Hz, position ≈ 30 Hz); PX4 streams over DDS at up to 100/50 Hz by default
— MAVLink stream rates are configurable (`MAV_1_RATE`, `SET_MESSAGE_INTERVAL`), this table is "out of the box". (b) The DDS round trip is quantised by the client's
~5 ms service cycle on both legs. (c) The rate PX4 "registers" for offboard is the `offboard_control_mode` publication rate (the `trajectory_setpoint` topic is also
re-published by PX4's own offboard flight task, which first made MAVROS look like it tripled the rate — it does not). (d) `PX4 tx B/s` is what PX4 sends on that
link with default streams; a 921600-baud UART carries ≈ 92 kB/s: MAVLink's 24.5 kB/s and DDS's 39 kB/s both fit, DDS with less headroom once topics are added.


## 4. Findings along the way (each cost time; each is in the data or the harness)

1. **MAVSDK-Python 4.x is a different library from the one in Seeed's tutorial.** `pip install mavsdk` now gives a *native binding* (no gRPC, no `mavsdk_server` process, `from mavsdk.asyncio import Mavsdk`);
   Seeed's code (`System()`, `drone.connect(system_address=…)`) needs `pip install mavsdk-grpc` / `import mavsdk_grpc`. Both were benchmarked.
2. **PX4 1.17 versioned its ROS topics**: `/fmu/out/vehicle_status_v1`, `/fmu/out/vehicle_local_position_v1`, `…/arming_check_request_v1`. A client written for the un-suffixed names from older docs connects and sees nothing, silently.
   `px4_msgs` branch `release/1.17` must match the firmware.
3. **MAVSDK `Odometry(frame_id=MOCAP_NED)` delivers a NaN position and `pose_frame 0` to PX4** (attitude and velocity are fine); `LOCAL_FRD` delivers the correct pose (`pose_frame 2`, the same as MAVROS). All fields of
   `mocap.Odometry` (`reset_counter`, `estimator_type`, `quality_percent`) must be set or the call raises.
4. **MAVROS defaults are not for a small computer**: ~50 plugins as separate nodes. The `plugin_allowlist` cuts idle CPU 3× and RSS 1.8×. Its obstacle plugin also defaults to `mav_frame: GLOBAL` (body-frame scans need `BODY_FRD`),
   and `manual_control/send` passes stick values unscaled (−1000…1000).
5. **PX4's DDS client ships in the Pixracer build**: `boards/px4/fmu-v4/default.px4board` has `CONFIG_MODULES_UXRCE_DDS_CLIENT=y` in v1.17.0, and ADR-003 already measured the default build at 95.3 % flash. That answers ADR-001's "uncertain"
   for flash; the board is `CONSTRAINED_MEMORY` (client: 8 kB task stack + ≥ 4 kB stream buffers) and has not been run.
6. `px4-<module>` shell clients address a second SITL instance with `--instance N`, not `PX4_INSTANCE`; `mavlink status` prints to the daemon's stdout, not to the caller.

## 5. Feature coverage for what this project needs (static analysis of the pinned firmware and the three stacks)

PX4 v1.17.0 `uxrce_dds_client/dds_topics.yaml`, PX4 `mavlink_receiver.cpp`, MAVROS 2.15 plugin list, MAVSDK 4.0.3 plugin list.

| Need (docs/zed-px4-bridge.md) | MAVROS | MAVSDK 4.x | uXRCE-DDS |
|---|---|---|---|
| External vision (ODOMETRY) | `odometry/out` (`vision_pose/*`): **converts ENU/FLU → NED/FRD for you** | `mocap.set_odometry` (you convert) | `/fmu/in/vehicle_visual_odometry` (you convert) |
| Obstacle distance (collision prevention, QGC radar) | `obstacle/send` (LaserScan; plugin param `mav_frame` defaults to GLOBAL — must be set to BODY_FRD) | no dedicated plugin → `mavlink_direct` | `/fmu/in/obstacle_distance` |
| Distance sensor | plugin exists but **denylisted** by default (`px4_pluginlists.yaml`) | `mavlink_direct` | `/fmu/in/distance_sensor` |
| Landing target | `landing_target/pose` | `mavlink_direct` | **not exposed** |
| Follow target (follow-me) | no plugin → raw `mavlink_sink` | `mavlink_direct` | **not exposed** |
| Optical flow | `px4flow/raw/send` | `mavlink_direct` | `/fmu/in/sensor_optical_flow` |
| Companion health (STATUSTEXT, NAMED_VALUE_FLOAT, ONBOARD_COMPUTER_STATUS) | `statustext/send`, `debug_value/*`, `onboard_computer/status` | `mavlink_direct` | only `onboard_computer_status` |
| MAVLink camera component (QGC auto-discovers the video) | raw only | **`camera_server` plugin** | **not possible** (MAVLink only) |
| Parameters (EKF2, CP_*, MAV_*) | `param/*` services | `param` plugin | **no parameter access** (needs MAVLink/QGC anyway) |
| Offboard / setpoints | `setpoint_position|velocity|raw|accel|attitude|trajectory` | `offboard` | `trajectory_setpoint`, `goto_setpoint`, attitude/rates/thrust/torque/**actuator** setpoints (superset) |
| Commands (arm, mode, takeoff) | `cmd/*`, `set_mode` | `action` | `vehicle_command` (any MAV_CMD) |
| PX4 → companion state | all standard MAVLink streams as ROS messages | `telemetry` (curated) | ~25 topics in the yaml (e.g. `estimator_status_flags`, `failsafe_flags`); **more topics = edit `dds_topics.yaml` and rebuild the firmware** |
| Raw escape hatch | `mavlink_sink` / `mavlink_source` | `mavlink_direct` | — |
| Time sync | `time` plugin | built in | built into the client (`timesync_status`) |
| Multi-vehicle | one MAVROS per `tgt_system` + namespace | one connection per system | client `-n <ns>` namespace, one agent per link |

## 6. Operational factors

| | MAVROS | MAVSDK 4.x native | MAVSDK gRPC | uXRCE-DDS |
|---|---|---|---|---|
| Install on Jetson (Ubuntu 24.04 / Jazzy) | `apt install ros-jazzy-mavros*` (amd64 + arm64) | `pip install mavsdk` (manylinux wheels incl. aarch64) | `pip install mavsdk-grpc` | **build the agent from source** (no apt package for Jazzy), build `px4_msgs` for *the exact firmware* |
| Firmware coupling | none beyond the MAVLink dialect | none | none | **message definitions must match the firmware**; v1.17 versions topics (`/fmu/out/vehicle_status_v1`, `…/vehicle_local_position_v1` — an un-suffixed client from older docs silently sees nothing) and needs the [message translation node](https://docs.px4.io/main/en/ros2/px4_ros2_msg_translation_node.html) when ROS and firmware versions differ |
| ROS 2 integration | native (standard `sensor_msgs`, `nav_msgs`, `geometry_msgs`) | none (asyncio/sync API; wrap in a node yourself) | none | native but PX4 types |
| PX4 board | any | any | any | needs the client in the firmware: v1.17 `fmu-v4/default.px4board` has `CONFIG_MODULES_UXRCE_DDS_CLIENT=y` and `px4_fmu-v4_default` links at 95.3 % flash (ADR-003) — but fmu-v4 is `CONSTRAINED_MEMORY` (256 KB RAM): **not run on a real Pixracer yet** |
| Serial link | `serial:///dev/ttyTHS1:921600` | `serial:///dev/ttyTHS1:921600` | same | agent `serial --dev … -b 921600`; PX4 `UXRCE_DDS_CFG`, **disables MAVLink on that port** (Seeed: `MAV_1_CONFIG` off) |
| Security | MAVLink (signing optional) | same | same | "unauthenticated and reaches uORB directly" (PX4 docs): keep the network isolated |
| Upstream stance | actively maintained, CI on Humble/Jazzy/Kilted/Lyrical/Rolling | PX4's own SDK | continues as a separate package | PX4: "recommended for most [ROS 2] users, more established and more thoroughly tested" |



## 7. Recommendation for this project

Scoring against the three asks (lightweight, fast, accurate) plus what the project needs (ZED → PX4 bridge with MAVLink-only messages, ROS 2 Jazzy, Pixracer, Jetson):

| | Lightweight | Fast (command RTT / rates) | Accurate | Robust under CPU load | Covers the bridge's messages | Integration cost here | Pixracer risk |
|---|---|---|---|---|---|---|---|
| MAVROS default | ✗ 28 % / 255 MB | ✓ 4.3 ms | ✓ (converts frames) | ✗ 65 ms, max 407 ms | ✓ plugins + raw | 0 (in use) | none |
| **MAVROS lean** | ○ 9 % / 144 MB | ✓ 4.3 ms | ✓ (converts frames) | ○ 11 ms | ✓ plugins + raw | 0 + one YAML | none |
| **MAVSDK 4.x native** | ✓ ~2–3 %, 71 MB, no bridge | ✓ 4.2 ms | ✓ (caller converts; trap in §4 item 3) | ✓ 3.6 ms | ✓ `mavlink_direct`, `camera_server`, `mocap` | rewrite ROS-facing parts | none |
| MAVSDK gRPC | ✓ 18 MB server | ✗ 12 ms | ✓ | ✓ 12 ms | ✓ | as above + server process | none |
| uXRCE-DDS | ✓ best (27 MB, ~1 %) | ○ rates 2× best, **RTT 16.5 ms** | ✓ (caller converts, NED/FRD native) | ✓ 16 ms | ✗ no landing/follow target, STATUSTEXT, params, camera protocol | agent build, `px4_msgs` pin, second MAVLink link still needed | **unverified** (RAM), disables MAVLink on its UART |

**Decision (proposed, for the user to confirm):**
1. **Stay on MAVLink for everything.** DDS cannot be the only link (feature gaps) and would force two stacks; revisit only for a Pixhawk 6X-class board where an extra DDS link is cheap.
2. **Adopt MAVROS with the lean plugin list now** (`tools/px4link_bench/mavros_lean.yaml`, add `distance_sensor`/`px4flow` when those bridge modules arrive — they are denylisted by default). Zero migration, frame conversion proven correct, ADR-001 stands (add an addendum).
3. **Decision gate for MAVSDK 4.x native, measured on the Orin NX** (not the workstation): switch the ZED→PX4 bridge to MAVSDK-native if, with the ZED wrapper running, lean MAVROS idles above ~15 % of a core, or its command RTT p95 exceeds ~30 ms, or the bridge needs the MAVLink camera component (`camera_server` saves a hand-written protocol). Two MAVLink clients can share one UART only through a router (MAVROS router UDP endpoint or `mavlink-router`); do not open the serial port twice.
4. **Do not use MAVSDK-gRPC.** Its only advantage is the old API; it costs a process and 3× the latency of the native binding.

**To run on the Jetson (bench day):** `docker run` the bench image (arm64 build of `docker/bench/Dockerfile`), point `fcu_url` / `system_address` at `/dev/ttyTHS1:921600` (and `SER_TEL2_BAUD`, `MAV_1_CONFIG=TELEM2`, `MAV_1_MODE=Onboard` on the Pixracer), run `bench.py --phase idle|telemetry|rtt` for MAVROS lean and MAVSDK-native **with the ZED wrapper running** (the contention test), and record: idle CPU/RSS, RTT p50/p95/max, attitude gap p95/max, serial bytes/s. Also check uxrce_dds_client RAM on the Pixracer (`uxrce_dds_client status` + `top`) if DDS stays on the table.

## 8. What this study did not measure
One-way telemetry latency (PX4 SIH uses lockstep time, so PX4 and companion clocks cannot be compared); serial-link behaviour (UDP loopback, no baud-rate limit, no byte errors); GPU/ZED load on the CPU; offboard streaming under CPU contention; MAVLink stream rates above the onboard defaults; the Zenoh transport (experimental in PX4 1.17); the Orin NX itself.


## 9. Reproduce

```bash
docker build -f docker/bench/Dockerfile -t bisg/px4link-bench:jazzy .              # agent v2.4.3 + px4_msgs + mavsdk (~15 min)
docker run -d --name bisg-px4link --network host --ipc host -v "$PWD":/workspace \
       -e RMW_IMPLEMENTATION=rmw_fastrtps_cpp --entrypoint bash bisg/px4link-bench:jazzy -c 'sleep infinity'
python3 tools/px4link_bench/run.py --repeats 2                                        # all methods x all phases, ~70 min
python3 tools/px4link_bench/report.py logs/px4link_bench/<run>                        # the tables above
```
Files: `docker/bench/Dockerfile`, `tools/px4link_bench/{bench.py,run.py,report.py,px4.sh,mavros_lean.yaml}`.
**On the Jetson**: the same harness runs unchanged against a real Pixracer if `fcu_url`/`system_address` are changed to the serial device
(see `bench.py`, `Mavros.start`, `MavsdkNative.connect`, `Dds.start`); only the bandwidth sampling uses SIH-container commands.
