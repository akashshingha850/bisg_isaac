# ZED SDK image

Built from Stereolabs' own Docker scripts (vendored as `third_party/zed-ros2-wrapper`, tag matching
`ZED_SDK` in `docker/.env`) via `docker/zed/build.sh`. Verified upstream matrix (wrapper `docker/README.md`):
Jazzy on Ubuntu 24.04 desktop and on L4T r38.x (JetPack 7) — exactly our two targets.

| Target | Command | Base pulled by the script | Tag |
|---|---|---|---|
| Workstation (x86_64, for bench tests with a ZED Mini on USB) | `docker/zed/build.sh desktop` | `stereolabs/zed:5.4.x-devel-cuda12.8-ubuntu24.04` | `bisg/zed:desktop` |
| Jetson Orin NX, JetPack 7.2 | `docker/zed/build.sh jetson` (run on the Jetson) | `stereolabs/zed:5.4.x-devel-l4t-r38.4` | `bisg/zed:l4t-r38` |

Runtime (Phase 5, `deploy/jetson/compose.yaml`): `--privileged` or `/dev/bus/usb` + `/dev/video*` passthrough,
`network_mode: host`, `RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, wrapper launch
`ros2 launch zed_wrapper zed_camera.launch.py camera_model:=zedm` with our params overlay
(`deploy/jetson/zed_params.yaml`, Phase 3/5) that sets frame ids and rates per `docs/interface-contract.md`.

**CycloneDDS overlay.** Stereolabs' image is Fast DDS only, while every bisg container (and `deploy/jetson/compose.yaml`) sets
`RMW_IMPLEMENTATION=rmw_cyclonedds_cpp`, which aborts every ROS tool in a Fast-DDS-only image. `build.sh` therefore tags the upstream
result `bisg/zed:<variant>-base` and builds `Dockerfile.overlay` (one `apt install ros-jazzy-rmw-cyclonedds-cpp`) on top as `bisg/zed:<variant>`.

**Same image in the sim.** `docker/compose.yaml` service `zed` (`./bisg zed up`, profile `zed`) runs this image against the sim's streamed
ZED Mini twin; see `docs/zed-sdk-sim.md`. `build_isaac_ext.sh` builds Stereolabs' Isaac Sim extension for it (`./bisg zed ext-build`).

ZED Mini is a USB camera, so no GMSL capture card and no `zed_x` kernel drivers are needed.
