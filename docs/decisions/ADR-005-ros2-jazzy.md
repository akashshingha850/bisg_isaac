# ADR-005 — ROS 2 Jazzy (Ubuntu 24.04) in all containers

Status: accepted (2026-09-12)

## Context
The companion computer is a **Jetson Orin NX on JetPack 7.2**, which is L4T r38 on **Ubuntu 24.04**
with CUDA 13. Stereolabs ships ZED SDK images for that L4T on 24.04 bases, and the ZED ROS 2
wrapper in that environment builds against **Jazzy**. At the time of this decision the workstation
host ran Ubuntu 22.04 with ROS 2 Humble; per ADR-002 nothing runs natively on the host, so this
distro choice was host-OS-independent by design. (The host itself has since moved to Ubuntu 24.04 —
`docs/plan.md` §12 — which only reinforces the decision below.)

## Decision
- All `bisg/*` containers use **ROS 2 Jazzy** (`ros:jazzy-ros-base`, Ubuntu 24.04), on amd64 and arm64.
- Isaac Sim's bundled ROS 2 bridge is run with its **Jazzy** library set (5.1: `exts/isaacsim.ros2.bridge/jazzy`; 6.0: `exts/isaacsim.ros2.core/jazzy`).
- MAVROS from `ros-jazzy-mavros` + `ros-jazzy-mavros-extras`.
- The host has no ROS install at all (see CLAUDE.md); every ROS 2 process, including ad-hoc
  debugging, runs inside a `bisg/ros` container.

## Reasons
- One distro across sim, workstation containers and the Jetson; a Humble container on a JetPack 7
  host would need the ZED SDK's CUDA 13 / L4T r38 libraries inside a 22.04 image — unsupported.
- Jazzy is LTS (to 2029), longer than Humble (2027).

## Consequences
- Verified 2026-09-12: Isaac Sim 5.1.0 ships an internal Jazzy bridge (`exts/isaacsim.ros2.bridge/jazzy/{lib,rclpy}`); Pegasus's own install docs select it with `ROS_DISTRO=jazzy` + `LD_LIBRARY_PATH`. Pegasus ROS 2 backend on Jazzy still to be exercised in Phase 3.
- Verified 2026-09-12: `ros-jazzy-mavros` / `-extras` 2.15.1 exist for amd64 and arm64.
- Verified 2026-10-02 (Isaac Sim 6.0.0 migration): the bundled bridge moved to `exts/isaacsim.ros2.core/jazzy/{lib,rclpy}` (still Cyclone-capable); OmniGraph node names are still `isaacsim.ros2.bridge.*`; Pegasus ROS 2 backend + MAVROS + `/clock` work across containers on Jazzy.
- CycloneDDS packages: `ros-jazzy-rmw-cyclonedds-cpp` (ADR-004 unchanged).
- If Isaac's Jazzy bridge proves unusable, fallback is Humble in the `sim` container only with a
  DDS bridge to Jazzy — a documented exception, not a distro change.
