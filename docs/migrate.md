# BISG Isaac — Isaac Sim 5.1 → 6.0 Migration

This document describes the migration of the BISG Isaac simulation stack from **NVIDIA Isaac Sim 5.1** to **Isaac Sim 6.0**, while preserving the existing ROS 2 interfaces, PX4/MAVROS integration, Pegasus vehicle model, ZED sensor abstraction, and multi-drone architecture.

The migration is based on the official Isaac Sim 6.0 migration documentation and the Pegasus Simulator Isaac Sim 6.0 migration work.

---

## 1. Target Stack

### Current stack

```text
Ubuntu 24.04
├── ROS 2 Jazzy
├── Docker
└── NVIDIA Isaac Sim 5.1
    ├── Pegasus 5.1
    └── PX4 SITL
```

### Migration target

```text
Ubuntu 24.04
├── ROS 2 Jazzy
├── Isaac ROS 4.6
└── NVIDIA Isaac Sim 6.0
    ├── Pegasus Isaac-6 migration
    └── PX4 SITL 1.16.x
```

### Version matrix

| Component | Current      | Migration target             |
| --------- | ------------ | ---------------------------- |
| OS        | Ubuntu 24.04 | Ubuntu 24.04                 |
| ROS 2     | Jazzy        | Jazzy                        |
| Isaac Sim | 5.1.0        | **6.0.0**                    |
| Isaac ROS | —            | **4.6.x**                    |
| Pegasus   | 5.1.0        | **Isaac-6 migration branch** |
| PX4       | 1.17.0       | **1.16.0 initially**         |
| Python    | 3.11         | **3.12**                     |
| ZED SDK   | 5.4.1        | 5.4.1 initially              |
| DDS       | CycloneDDS   | CycloneDDS initially         |

> **Important:** Isaac ROS 5.x is a separate migration target because Isaac ROS 5 moved to ROS 2 Lyrical. This document therefore targets **Isaac ROS 4.6 + ROS 2 Jazzy**.

---

# 2. Why Isaac Sim 6.0?

The purpose of this migration is not simply to upgrade the simulator version.

Isaac Sim 6.0 provides the newer NVIDIA simulation stack required for the project's longer-term AI/robotics development while retaining the current ROS 2 architecture.

Important improvements relevant to BISG include:

* newer RTX sensor architecture
* improved sensor timing
* improved ROS 2 integration
* newer Python runtime
* newer Isaac Sim core APIs
* improved synthetic-data infrastructure
* newer NVIDIA Omniverse/Kit stack
* continued support for photorealistic rendering
* better compatibility with current NVIDIA robotics tooling

Isaac Sim 6.0 is also the version against which the Pegasus Isaac-6 migration has been explicitly tested.

---

# 3. Why Not Upgrade Directly to Isaac Sim 6.1?

Isaac Sim 6.1 is newer, but the primary constraint for this project is **Pegasus compatibility**.

The Pegasus Isaac-6 migration PR targets Isaac Sim 6.0 and was tested with:

* Isaac Sim 6.0.0
* ROS 2 Jazzy
* PX4 1.16.0
* QGroundControl
* Pegasus PX4 backend

Therefore, Isaac Sim 6.0 is used as the intermediate stable target.

The recommended migration path is:

```text
Isaac Sim 5.1
      │
      ▼
Isaac Sim 6.0
      │
      │  stabilize Pegasus + PX4 + ROS 2
      ▼
Isaac Sim 6.1
      │
      ▼
future Isaac versions
```

Do not attempt to solve the Pegasus 5.1 → 6.x API migration and the 6.0 → 6.1 migration simultaneously.

---

# 4. Important ROS / Isaac ROS Compatibility

## Recommended configuration

```text
Ubuntu 24.04
      │
ROS 2 Jazzy
      │
Isaac ROS 4.6
      │
Isaac Sim 6.0
```

This is the configuration used for this migration.

## Isaac ROS 5

Isaac ROS 5 should **not** be installed into the existing Jazzy environment.

Isaac ROS 5 targets ROS 2 Lyrical.

Therefore:

```text
Ubuntu 24.04
ROS 2 Jazzy
Isaac ROS 4.6
Isaac Sim 6.0
```

is the recommended stack for this repository.

A future Isaac ROS 5 migration should be treated as a separate project.

---

# 5. Migration Strategy

The migration must be performed in isolated stages.

Do not simultaneously change:

* Isaac Sim
* Pegasus
* PX4
* ROS 2
* ZED
* AI dependencies

The recommended order is:

```text
1. Freeze Isaac 5.1 baseline
2. Upgrade Isaac Sim runtime
3. Upgrade Pegasus
4. Validate standalone Pegasus
5. Validate PX4
6. Validate ROS 2
7. Validate sensors
8. Validate ZED interface
9. Validate Isaac ROS
10. Validate multi-drone
11. Benchmark
12. Consider Isaac Sim 6.1
```

---

# 6. Create Migration Branch

Before making changes:

```bash
cd ~/bisg_isaac

git status

git checkout -b migrate/isaac-6.0

git tag isaac-5.1-baseline

git push origin isaac-5.1-baseline
```

The `isaac-5.1-baseline` tag must remain reproducible.

Do not modify the baseline branch.

---

# 7. Freeze Current Performance Baseline

Before migration, record the following from Isaac Sim 5.1:

### Simulator

* simulator startup time
* FPS
* physics frequency
* GPU memory
* CPU utilization
* GPU utilization

### PX4

* SITL startup time
* connection time
* ARM time
* takeoff
* position hold
* landing

### ROS 2

Record:

```bash
ros2 topic list
```

and:

```bash
ros2 topic hz <topic>
```

for important topics.

### Sensors

Record:

* RGB FPS
* depth FPS
* IMU rate
* LiDAR rate
* timestamp behavior
* TF frequency

These values become the migration baseline.

---

# 8. Update Version Configuration

Current configuration:

```text
ISAAC_TAG=5.1.0
PX4_TAG=v1.17.0
PEGASUS_TAG=v5.1.0
```

Initial migration configuration:

```text
ISAAC_TAG=6.0.0
PX4_TAG=v1.16.0
```

The Pegasus Isaac-6 migration was validated against PX4 1.16.0.

Do not upgrade PX4 and Isaac Sim simultaneously.

After the Isaac 6 migration is stable, PX4 1.17.x can be tested separately.

---

# 9. Isaac Sim Python Runtime

Isaac Sim 5.1 uses:

```text
Python 3.11
```

Isaac Sim 6.0 uses:

```text
Python 3.12
```

All Python dependencies must therefore be rebuilt.

Do **not** copy:

```text
site-packages/
venv/
```

from Isaac Sim 5.1 to Isaac Sim 6.0.

Reinstall dependencies using the Isaac Sim 6.0 Python runtime.

This includes:

* Python packages
* compiled wheels
* native extensions
* ROS 2 Python packages
* custom message packages
* ML packages

NVIDIA explicitly recommends rebuilding these components rather than copying the 5.x environment.

---

# 10. Docker Migration

The simulator Docker image currently uses:

```dockerfile
FROM nvcr.io/nvidia/isaac-sim:${ISAAC_TAG}
```

Change:

```text
ISAAC_TAG=5.1.0
```

to:

```text
ISAAC_TAG=6.0.0
```

The Docker image must be rebuilt from scratch.

```bash
docker compose build --no-cache sim
```

Then:

```bash
docker compose up sim
```

Do not reuse the Isaac 5.1 Python environment.

---

# 11. Remove Isaac 5.1 ROS Library Paths

Search the repository:

```bash
grep -R "isaacsim.ros2.bridge" .
grep -R "omni.isaac" .
grep -R "dynamic_control" .
grep -R "Python 3.11" .
```

Any hard-coded Isaac 5.1 paths must be reviewed.

Isaac Sim 6.0 changed the ROS 2 extension structure and uses the newer ROS 2 package layout.

---

# 12. Pegasus Migration

Pegasus is the largest part of the migration.

The Pegasus Isaac-6 migration identifies the following major breaking changes:

```text
Isaac Sim 5.1
    ↓
Isaac Sim 6.0

World
    ↓
SimulationManager + RenderingManager

Robot
    ↓
plain Python class + USD prim management

dynamic_control
    ↓
RigidPrim / Articulation

omni.isaac.*
    ↓
isaacsim.*

old ROS camera utilities
    ↓
isaacsim.ros2.core utilities
```

The migration PR contains the implementation for these changes and has been tested with Isaac Sim 6.0, ROS 2 Jazzy and PX4 1.16.0.

Reference:

https://github.com/PegasusSimulator/PegasusSimulator/pull/144

---

# 13. Pegasus Branch

Use the Pegasus Isaac-6 migration branch as the starting point.

Do not manually port Pegasus 5.1 from scratch.

The migration PR targets:

```text
PegasusSimulator:dev_6.0.1
```

and contains the required Isaac Sim 6.0 changes.

The PR was tested with:

```text
Isaac Sim 6.0.0
ROS 2 Jazzy
PX4 1.16.0
```

and successfully demonstrated:

```text
PX4 SITL
QGroundControl
takeoff
ROS 2 topics
Python control
people/NavMesh
```

---

# 14. Isaac `World` API Migration

Isaac Sim 5.1:

```python
from omni.isaac.core import World
```

Isaac Sim 6.0 removes this API.

Pegasus uses:

```python
from isaacsim.core.simulation_manager import SimulationManager
from isaacsim.core.rendering_manager import RenderingManager
```

World-level operations must be migrated accordingly.

Examples:

```python
world.add_physics_callback(...)
```

becomes the Isaac 6 callback system:

```python
SimulationManager.register_callback(...)
```

Render callbacks use:

```python
RenderingManager.register_callback(...)
```

The Pegasus migration PR implements this throughout the simulator.

---

# 15. Simulation Callbacks

Isaac 5.1:

```python
world.add_physics_callback(...)
world.add_render_callback(...)
```

Isaac 6.0:

```python
SimulationManager.register_callback(
    SimulationEvent.PHYSICS_POST_STEP,
    callback
)
```

and:

```python
RenderingManager.register_callback(
    RenderingEvent.NEW_FRAME,
    callback
)
```

Callback signatures must also be updated.

Isaac 6 physics callbacks receive:

```python
(dt, context=None)
```

rather than relying on the old World callback behavior.

---

# 16. `Robot` API Migration

Isaac Sim 5.1 Pegasus vehicles inherit from the Isaac `Robot` class.

Isaac Sim 6.0 removes this dependency.

The migrated Pegasus vehicle is a normal Python class and explicitly manages:

```text
USD prim
RigidPrim
Articulation
callbacks
vehicle state
```

The vehicle must therefore define and maintain its own:

```python
prim_path
```

and initial pose.

Do not attempt a simple:

```text
Robot → Articulation
```

replacement.

The lifecycle has changed.

---

# 17. Dynamic Control Migration

Isaac 5.1:

```python
omni.isaac.dynamic_control
```

is removed in Isaac 6.0.

Use:

```python
isaacsim.core.experimental.prims.RigidPrim
```

for rigid-body operations.

For multirotor articulation:

```python
isaacsim.core.experimental.prims.Articulation
```

is used.

Example force application:

```python
rigid_prim.apply_forces_and_torques_at_pos(
    forces=forces,
    torques=torques,
    positions=positions,
    local_frame=True
)
```

Vehicle state should be obtained using:

```python
RigidPrim.get_world_poses()
RigidPrim.get_velocities()
```

---

# 18. Warp Array / ROS 2 Conversion

Isaac Sim 6.0 physics APIs can return Warp arrays.

Example:

```text
RigidPrim.get_world_poses()
        ↓
Warp float32 array
```

ROS 2 Python bindings expect normal Python-compatible floating-point values.

Therefore:

```python
array.numpy().astype(np.float64)
```

must be performed before passing values into ROS messages where required.

This avoids ROS 2 Python/C-binding failures caused by Warp float32 values.

The Pegasus migration explicitly encountered and fixed this issue.

---

# 19. Multirotor Migration

Pegasus multirotor control must migrate from:

```text
dynamic_control articulation/joints
```

to:

```text
Articulation
```

Rotor DOF indices should be obtained using:

```python
Articulation.get_dof_indices()
```

and propeller visual animation should use:

```python
Articulation.set_dof_velocities()
```

Rotor transforms should be obtained through:

```python
UsdGeom.XformCache
```

rather than the removed dynamic-control relative-body-pose APIs.

---

# 20. Rotor Geometry Validation

After migration, explicitly validate rotor positions.

The rotor allocation geometry is critical to:

* thrust
* roll
* pitch
* yaw
* PX4 flight stability

Verify:

```text
rotor 0
rotor 1
rotor 2
rotor 3
```

relative to:

```text
base_link
```

and confirm that:

```text
thrust
roll
pitch
yaw
```

directions remain unchanged.

Do not assume API migration preserves the exact transform semantics.

---

# 21. Isaac Sim 6 ROS 2 Extension Changes

Isaac Sim 6.0 reorganized ROS 2 extensions.

Old references such as:

```text
isaacsim.ros2.bridge
```

must be reviewed.

The Isaac 6 ecosystem uses:

```text
isaacsim.ros2.core
isaacsim.ros2.nodes
isaacsim.ros2.ui
isaacsim.ros2.examples
```

as appropriate.

The exact extension dependency list should follow the Isaac Sim 6.0 ROS documentation and the migrated Pegasus `extension.toml`.

---

# 22. Camera Info Migration

The old camera information utility:

```python
read_camera_info
```

moved in Isaac Sim 6.0.

Old:

```text
isaacsim.ros2.bridge
```

New:

```python
from isaacsim.ros2.core.impl.camera_info_utils import read_camera_info
```

Update all imports.

---

# 23. ROS 2 Workspace Migration

Isaac Sim 6.0 changes the NVIDIA ROS workspace package layout.

The old package:

```text
isaacsim
```

becomes:

```text
isaacsim_bringup
```

Several packages also move from:

```text
ament_cmake
```

to:

```text
ament_python
```

Review:

* `package.xml`
* `setup.py`
* `setup.cfg`
* launch files
* CI
* README commands
* `get_package_share_directory()`
* package dependencies

NVIDIA's official migration table documents these changes.

---

# 24. ROS 2 Launch Environment

For Jazzy, prefer the external/system ROS installation unless the project specifically requires Isaac Sim's internal libraries.

Example:

```bash
source /opt/ros/jazzy/setup.bash
```

Before launching Isaac Sim, verify:

```bash
echo $ROS_DISTRO
echo $RMW_IMPLEMENTATION
echo $LD_LIBRARY_PATH
```

Expected:

```text
ROS_DISTRO=jazzy
```

ROS 2 library selection must be configured before Isaac Sim starts.

Do not dynamically enable the ROS bridge after Isaac Sim has already started with an incompatible ROS environment.

---

# 25. DDS

The current project uses CycloneDDS.

Keep this initially:

```bash
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
```

Do not change DDS during the Isaac migration.

Only investigate DDS changes after the basic stack works.

---

# 26. ROS 2 Interface Contract

The migration must preserve the existing BISG ROS interface.

The following must remain unchanged:

```text
/drone_1/...
/drone_2/...
/drone_3/...
```

and:

```text
map
└── odom
    └── base_link
```

The simulator implementation may change.

The ROS interface must not.

---

# 27. MAVROS

MAVROS remains outside the Isaac Sim API migration.

Its responsibility remains:

```text
PX4
 ↕
MAVLink
 ↕
MAVROS
 ↕
ROS 2
```

Validate:

```bash
ros2 topic list | grep mavros
```

At minimum:

```text
/drone_1/mavros/state
/drone_1/mavros/local_position/pose
/drone_1/mavros/imu/data
/drone_1/mavros/battery
```

---

# 28. PX4 Migration

Do not begin with PX4 1.17.

Use the Pegasus-tested version first:

```text
PX4 1.16.0
```

Validation order:

```text
Isaac Sim
  ↓
Pegasus
  ↓
PX4 SITL
  ↓
MAVLink
  ↓
QGroundControl
  ↓
ARM
  ↓
TAKEOFF
  ↓
POSITION HOLD
  ↓
LAND
```

Only after this passes should PX4 1.17 be tested.

---

# 29. PX4 Airframe

The existing configuration contains:

```yaml
airframe: gazebo-classic_iris
```

Do not change this during the first migration.

The objective is to reproduce the existing behavior before changing flight-controller configuration.

After successful migration, evaluate whether the PX4 airframe should be updated for the selected PX4 version.

---

# 30. Lockstep

The existing configuration uses:

```yaml
enable_lockstep: false
```

Keep:

```yaml
enable_lockstep: false
```

during the initial migration.

After the simulator is stable, benchmark:

```text
lockstep=false
lockstep=true
```

Lockstep should be enabled only after:

* PX4 communication works
* sensor timing works
* ROS 2 works
* multi-drone spawning works

---

# 31. ZED Sensor Layer

Do not migrate the ZED abstraction at the same time as Pegasus.

Keep the existing interface:

```yaml
zed:
  enabled: true
  mount_xyz_rpy: [0.18, 0.0, -0.02, 0, 0, 0]
  baseline: 0.063
  resolution: [1280, 720]
  fps: 30.0
  imu_rate: 200.0
  depth_range: [0.1, 15.0]
```

The migration objective is:

```text
Isaac 5.1 ZED interface
        ↓
Isaac 6.0 ZED interface
```

without changing:

```text
ROS topics
TF
camera parameters
sensor rates
```

---

# 32. Sensor Validation

After migration, verify:

### RGB

```bash
ros2 topic hz /drone_1/zed/rgb/image_rect_color
```

### Depth

```bash
ros2 topic hz /drone_1/zed/depth/depth_registered
```

### IMU

```bash
ros2 topic hz /drone_1/zed/imu/data
```

### TF

```bash
ros2 run tf2_tools view_frames
```

Check:

```text
base_link
camera_link
camera_left
camera_right
```

---

# 33. RTX LiDAR

Isaac Sim 6.0 includes updated RTX sensor infrastructure.

Existing LiDAR configurations must be checked against the Isaac Sim 6.0 sensor migration documentation.

Pay particular attention to:

* sensor tick rate
* timestamps
* frame skipping
* RTX LiDAR assets
* PointCloud2 metadata
* ROS 2 sensor graphs

Do not reproduce old helper-node frame skipping if Isaac Sim 6.0 sensor `tickRate` provides the required behavior.

---

# 34. ROS 2 Sensor Graphs

Review all saved Action Graphs.

Check:

```text
Camera
CameraInfo
RTX LiDAR
PointCloud2
IMU
TF
Clock
```

Isaac Sim 6.0 changed several ROS 2 OmniGraph and sensor graph workflows.

Saved graphs from Isaac Sim 5.1 should not be assumed to be forward compatible.

NVIDIA provides dedicated migration documentation for ROS 2 OmniGraph and sensor graphs.

---

# 35. People / Human Simulation

If the project uses Pegasus people simulation, Isaac Sim 6.0 requires additional migration.

The old:

```text
Biped_Setup.usd
AnimationGraphAPI
PrimPaths
CharacterUtil
```

workflow changed.

Isaac Sim 6.0 uses:

```text
HumanMotionLibrary.usd
BehaviorAgent API
```

The behavior-agent setup must be deferred asynchronously in standalone mode to avoid OmniGraph initialization problems.

If people simulation is not required for the initial BISG milestone, defer this feature until after the vehicle/PX4 migration.

---

# 36. USD Asset Validation

All existing USD assets must be checked.

Validate:

```text
USD opens
textures load
materials load
physics loads
collision geometry works
camera mounts correctly
LiDAR mounts correctly
```

Do not convert every USD asset automatically.

First determine which assets actually fail in Isaac Sim 6.0.

---

# 37. Custom Drone Asset

For the Iris/custom UAV:

```text
/World/Drone_1
```

verify:

```text
body
rotors
camera
depth sensor
LiDAR
IMU
```

Then verify:

```text
base_link
camera_link
lidar_link
```

and the corresponding ROS TF tree.

---

# 38. Isaac ROS Integration

Isaac ROS should be integrated only after:

```text
Isaac Sim 6
+
Pegasus
+
PX4
+
ROS 2
+
sensors
```

are working.

Recommended architecture:

```text
                  Isaac Sim 6
                       │
             ┌─────────┼─────────┐
             │         │         │
            RGB      Depth     RTX LiDAR
             │         │         │
             └─────────┼─────────┘
                       │
                     ROS 2
                       │
                  Isaac ROS
             ┌─────────┼─────────┐
             │         │         │
          cuVSLAM    nvblox     DNN
             │         │         │
             └─────────┼─────────┘
                       │
                 Drone autonomy
                       │
                     PX4
```

The simulator should only provide sensor and vehicle interfaces.

AI algorithms should remain simulator-independent.

---

# 39. Multi-Drone Migration

Only after one vehicle works:

```text
drone_1
```

enable:

```text
drone_2
drone_3
...
```

Verify that every vehicle has unique:

```text
MAV_SYS_ID
PX4 instance
UDP port
ROS namespace
TF namespace
sensor topic namespace
```

Expected:

```text
/drone_1/...
/drone_2/...
/drone_3/...
```

---

# 40. Multi-Drone Acceptance Test

Start:

```text
2 drones
```

Then:

```text
4 drones
```

Then increase until GPU/CPU saturation.

Record:

| Drones | FPS | Physics Hz | GPU VRAM | CPU | Sensor FPS |
| -----: | --: | ---------: | -------: | --: | ---------: |
|      1 |     |            |          |     |            |
|      2 |     |            |          |     |            |
|      4 |     |            |          |     |            |
|      8 |     |            |          |     |            |

This establishes the simulation capacity of the workstation (measured on the RTX 4500 Ada, not a 5090 — see `migration-report.md` §6).

---

# 41. Migration Acceptance Criteria

> Ticked 2026-10-02 from the evidence in [`migration-report.md`](migration-report.md). Unticked items say why.

The migration is complete when all of the following pass.

## Isaac Sim

* [x] Isaac Sim 6.0 starts — **DONE**
* [x] RTX renderer works — **DONE**
* [x] custom USD environments load — **DONE (Isaac warehouse + Iris; our own site USDs do not exist yet, Phase 4)**
* [x] no Isaac 5.1 compatibility errors — **DONE (remaining deprecated-API use listed in migration-errors.md M12)**

## Pegasus

* [x] Pegasus extension loads — **DONE**
* [x] Iris vehicle spawns — **DONE**
* [x] physics works — **DONE**
* [x] rotor actuation works — **DONE (flight-verified; no explicit per-rotor geometry dump)**
* [ ] vehicle reset works — **NOT TESTED**

## PX4

* [x] PX4 SITL starts — **DONE**
* [x] PX4 connects to Pegasus — **DONE**
* [ ] QGroundControl connects — **PARTIAL (MAVLink heartbeat on udp 14550 verified; QGC not installed on this host)**
* [x] vehicle arms — **DONE**
* [x] takeoff works — **DONE**
* [x] position hold works — **DONE** (`tests/hold_position.py`: 0.03 m drift over 20 sim s)
* [x] landing works — **DONE**

## ROS 2

* [x] ROS 2 Jazzy works — **DONE**
* [x] `/clock` works — **DONE**
* [x] TF works — **DONE (static ZED tree, 6 frames)**
* [x] MAVROS works — **DONE**
* [x] vehicle state publishes — **DONE**
* [x] pose publishes — **DONE**
* [x] IMU publishes — **DONE**
* [x] battery publishes — **DONE**

## Sensors

* [x] RGB works — **DONE (320x180 here; HD720 blocked by host rmem_max, bugs.md B2)**
* [x] depth works — **DONE**
* [x] IMU works — **DONE**
* [x] LiDAR works — **N/A (no lidar in this project)**
* [x] camera info works — **DONE**
* [x] PointCloud2 works — **DONE (ZED point cloud; no lidar)**
* [x] timestamps are correct — **DONE (one sim clock, 31 Hz images)**
* [x] TF is correct — **DONE**

## Isaac ROS

* [ ] Isaac ROS launches — **NOT DONE (out of scope: Isaac ROS is not in plan.md/roadmap.md)**
* [ ] camera data reaches Isaac ROS — **NOT DONE**
* [ ] GPU acceleration works — **NOT DONE**
* [ ] TensorRT works — **NOT DONE**
* [ ] perception pipeline works — **NOT DONE**

## Multi-drone

* [x] 2 drones work — **DONE (also 4; 8 boots)**
* [x] unique MAV_SYS_ID values — **DONE**
* [x] unique namespaces — **DONE**
* [x] unique sensor topics — **DONE** (`two_iris_vio_lowres`: separate `/drone_1|2/zed/…` streams)
* [x] independent control — **DONE (each instance armed/flew separately)**
* [x] no cross-drone TF collisions — **DONE** (12 static transforms, per-drone `drone_N/` prefixes)

---

# 42. Common Migration Errors

## `ModuleNotFoundError: omni.isaac.*`

Cause:

Old Isaac 5.1 API.

Solution:

Replace with the corresponding Isaac 6.0 `isaacsim.*` API.

---

## `World` import failure

Example:

```text
ModuleNotFoundError:
omni.isaac.core.world
```

Solution:

Use:

```text
SimulationManager
RenderingManager
```

and migrate callbacks.

---

## `dynamic_control` failure

Example:

```text
omni.isaac.dynamic_control
```

Solution:

Use:

```text
RigidPrim
Articulation
```

---

## ROS 2 bridge loads but topics do not appear

Check before starting Isaac Sim:

```bash
echo $ROS_DISTRO
echo $RMW_IMPLEMENTATION
echo $LD_LIBRARY_PATH
```

Then:

```bash
source /opt/ros/jazzy/setup.bash
```

Restart Isaac Sim after changing ROS library settings.

---

## ROS 2 segmentation fault

Check for Warp float32 values being passed directly into ROS 2 Python messages.

Convert:

```python
.astype(np.float64)
```

where required.

---

## People simulation crashes

Isaac Sim 6.0 changed the animation system.

Use:

```text
HumanMotionLibrary
BehaviorAgent
```

and defer behavior-agent initialization until the simulator is ready.

---

## USD quaternion type error

Isaac Sim 6.0/NVIDIA assets may use:

```text
GfQuatf
```

instead of:

```text
GfQuatd
```

for `xformOp:orient`.

Use the precision matching the USD attribute.

---

# 43. Migration Search Commands

Run these commands after the initial migration:

```bash
grep -R "omni.isaac" .
```

```bash
grep -R "dynamic_control" .
```

```bash
grep -R "SimulationContext" .
```

```bash
grep -R "World(" .
```

```bash
grep -R "isaacsim.ros2.bridge" .
```

```bash
grep -R "isaacsim.core.api" .
```

```bash
grep -R "Robot" extensions/
```

Any remaining matches must be reviewed individually.

---

# 44. Git Migration Strategy

Use separate commits.

Recommended history:

```text
migrate: create Isaac 6 branch
migrate: update Isaac Sim container to 6.0
migrate: update Pegasus to Isaac 6
migrate: migrate vehicle APIs
migrate: migrate multirotor APIs
migrate: migrate ROS 2 integration
migrate: migrate sensor interfaces
migrate: migrate PX4 integration
migrate: restore ZED pipeline
migrate: restore Isaac ROS pipeline
migrate: validate multi-drone
```

Avoid one giant migration commit.

---

# 45. Rollback

If Isaac 6 migration fails:

```bash
git checkout isaac-5.1-baseline
```

The original Isaac 5.1 environment must remain usable.

The migration must never make the baseline unreproducible.

---

# 46. Recommended Migration Order

The complete workflow is:

```text
                 START
                   │
                   ▼
          Freeze Isaac 5.1
                   │
                   ▼
        Create migration branch
                   │
                   ▼
         Isaac Sim 6.0 Docker
                   │
                   ▼
         ROS 2 Jazzy validation
                   │
                   ▼
       Pegasus Isaac-6 migration
                   │
                   ▼
            Iris vehicle
                   │
                   ▼
            PX4 1.16 SITL
                   │
                   ▼
           QGroundControl
                   │
                   ▼
              MAVROS
                   │
                   ▼
              RGB/Depth
                   │
                   ▼
             IMU / LiDAR
                   │
                   ▼
               ZED layer
                   │
                   ▼
             Isaac ROS 4.6
                   │
                   ▼
             AI pipeline
                   │
                   ▼
            Multi-drone
                   │
                   ▼
             Benchmark
                   │
                   ▼
          Consider Isaac 6.1
```

---

# 47. Final Target Architecture

The completed system should look like:

```text
┌─────────────────────────────────────────────────────────┐
│                    Ubuntu 24.04                         │
│                                                         │
│  ┌──────────────────────┐     ┌──────────────────────┐ │
│  │    Isaac Sim 6.0    │     │     ROS 2 Jazzy      │ │
│  │                      │     │                      │ │
│  │  RTX Renderer        │     │  MAVROS              │ │
│  │  RTX Camera          │     │  Mission             │ │
│  │  RTX LiDAR            │     │  Fleet               │ │
│  │  Depth               │     │  AI                  │ │
│  │  USD                  │     │                      │ │
│  └──────────┬───────────┘     └──────────┬───────────┘ │
│             │                            │             │
│             │       ROS 2 Jazzy          │             │
│             └────────────┬───────────────┘             │
│                          │                             │
│                   ┌──────▼──────┐                      │
│                   │   Pegasus  │                      │
│                   └──────┬─────┘                      │
│                          │                             │
│                   MAVLink / UDP                        │
│                          │                             │
│                   ┌──────▼──────┐                      │
│                   │ PX4 SITL    │                      │
│                   └─────────────┘                      │
│                                                         │
│                   Isaac ROS 4.6                        │
│              ┌──────────┼──────────┐                   │
│              │          │          │                   │
│            cuVSLAM     nvblox      DNN                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

# 48. Future: Isaac Sim 6.1

Do not make Isaac Sim 6.1 part of the initial migration.

After the 6.0 stack is stable:

```text
Isaac Sim 6.0
+
Pegasus Isaac-6
+
PX4
+
ROS 2 Jazzy
+
Isaac ROS 4.6
```

should be tagged as a known-good release.

Then create:

```text
migrate/isaac-6.1
```

and test the 6.1 upgrade separately.

The 6.1 migration should be treated as a compatibility upgrade, not a complete project migration.

---

# 49. References

### NVIDIA Isaac Sim 6.0 Migration

https://docs.isaacsim.omniverse.nvidia.com/latest/migration_guides/isaac_sim_6_0/

### Isaac Sim 6.0 Migration Strategy

https://docs.isaacsim.omniverse.nvidia.com/latest/migration_guides/isaac_sim_6_0/migration_strategy.html

### ROS 2 Workspace Migration

https://docs.isaacsim.omniverse.nvidia.com/latest/migration_guides/isaac_sim_6_0/ros2_workspace_package_migration.html

### Pegasus Isaac Sim 6.0 Migration

https://github.com/PegasusSimulator/PegasusSimulator/pull/144

### BISG Isaac Repository

https://github.com/akashshingha850/bisg_isaac

---

# 50. Migration Success Definition

The migration is considered successful when:

```text
Ubuntu 24.04
     │
ROS 2 Jazzy
     │
Isaac ROS 4.6
     │
Isaac Sim 6.0
     │
Pegasus
     │
PX4
     │
MAVROS
     │
RGB + Depth + IMU + LiDAR
     │
AI / Isaac ROS
     │
Multi-drone
```

runs without modifying the existing BISG ROS interface.

The migration should change the **simulation implementation**, not the **research/robotics interface**.

The long-term goal is:

```text
                         BISG ROS API
                              │
              ┌───────────────┴───────────────┐
              │                               │
          Simulation                       Hardware
              │                               │
        Isaac Sim 6.x                       Jetson
              │                               │
          Pegasus                         PX4/FC
              │                               │
             PX4                            Sensors
```

This preserves the digital-twin architecture and allows the simulation backend to evolve independently of the autonomy, perception, and swarm research code.
