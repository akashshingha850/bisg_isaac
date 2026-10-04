# ros2_ws/src

ROS 2 Jazzy packages shared by sim and hardware (Phase 2+): `bisg_msgs`, `bisg_vehicle`, `bisg_fleet`, `bisg_bringup`.
Build inside the `ros` container: `docker compose -f docker/compose.yaml run --rm ros build`.
Nodes here must not import `isaacsim`, `pegasus` or `omni` (parity rule, plan.md §8).
