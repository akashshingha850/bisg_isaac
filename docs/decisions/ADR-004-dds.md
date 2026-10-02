# ADR-004 — CycloneDDS everywhere, zenoh bridge across WiFi

Status: accepted (2026-09-12), to be validated in Phase 2 (containers) and Phase 7 (WiFi)

## Context
ROS 2 traffic crosses container boundaries on the workstation (Isaac bridge → ros container)
and WiFi links between Jetsons and the ground station in the swarm. FastDDS shared-memory
transport is fragile across containers; DDS multicast discovery on WiFi is unreliable and
scales badly with N drones.

## Decision
- `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` in every container and on the host; a committed
  `cyclonedds.xml` (UDP only, interface pinned).
- Isaac Sim's bundled ROS 2 bridge is configured for Cyclone as well — verified 2026-09-12: Isaac 5.1.0 shipped `exts/isaacsim.ros2.bridge/jazzy/lib/librmw_cyclonedds_cpp.so` (Isaac 6.0.0: `exts/isaacsim.ros2.core/jazzy/lib/`, verified 2026-10-02); the sim image sets `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp` and `CYCLONEDDS_URI` to `docker/cyclonedds.xml`.
- Between drones and ground station: `zenoh-bridge-ros2dds` on each Jetson and on the GCS;
  drone-local traffic (images, VIO) never leaves the Jetson. Only `vehicle/state`, `vehicle/cmd`,
  `/fleet/*` and low-rate telemetry are allowed across the bridge (allow-list in the bridge config).
- `ROS_DOMAIN_ID`: one per fleet run; drones share it (namespaces separate them).

## Consequences
- Needs `network_mode: host` (already decided in ADR-002).
- Bandwidth budget per drone must be written down in Phase 7 before adding any new cross-bridge topic.
- If `ROS_DOMAIN_ID` isolation per drone is ever needed, the zenoh bridge can map domains.
