# ADR-002 — Docker-first, including Isaac Sim

Status: accepted (2026-09-12)

## Context
Isaac Sim, PX4 SITL, ROS 2 + MAVROS and the ZED SDK all have strict version couplings
(driver, CUDA, L4T, Python). A previous native setup on this workstation drifted and became
unreproducible. The same stack must later run on Jetsons.

## Decision
Every runtime component ships as a Docker image; `docker/compose.yaml` profiles compose them:
`sim`, `sim-headless`, `ros`, `jetson`. Isaac Sim runs from `nvcr.io/nvidia/isaac-sim:5.1.0`
with Pegasus and PX4 SITL layered on top (`bisg/sim`). ROS 2 code lives in `bisg/ros`,
built for amd64 and arm64. ZED SDK in `bisg/zed`.

## Reasons
- Reproducible pins; a fresh machine reaches a flying drone with `docker compose up`.
- The **same** `bisg/ros` image runs on the workstation (against SITL) and on the Jetson
  (against the Pixracer) — the strongest possible parity guarantee.
- Isolation of Isaac's bundled Python/ROS libs from host ROS.

## Consequences
- Isaac image is ~20 GB; first pull and shader caches are slow → named cache volumes, `docker save` backup.
- GUI needs X11 passthrough (or livestream); headless is the default for tests.
- `network_mode: host` everywhere for DDS/MAVLink simplicity; isolation via `ROS_DOMAIN_ID`.
- Host installs remain allowed for one-off debugging but never as a dependency of a documented workflow.
