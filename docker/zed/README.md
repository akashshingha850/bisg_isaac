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

ZED Mini is a USB camera, so no GMSL capture card and no `zed_x` kernel drivers are needed.
