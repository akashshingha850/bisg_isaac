#!/usr/bin/env bash
# Build the ZED SDK + zed-ros2-wrapper image with Stereolabs' official build scripts
# (third_party/zed-ros2-wrapper/docker). We do not maintain our own ZED Dockerfile.
#
#   docker/zed/build.sh desktop      # x86_64 workstation: Jazzy, Ubuntu 24.04, SDK $ZED_SDK
#   docker/zed/build.sh jetson       # Orin NX, JetPack 7.x: run ON the Jetson; L4T read from /etc/nv_tegra_release
#                                    # (override: ZED_L4T=r39.2). Base tags: hub.docker.com/r/stereolabs/zed/tags
#
# Upstream result + docker/zed/rmw.Dockerfile (CycloneDDS RMW) -> bisg/zed:<variant>.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ZED_SDK="${ZED_SDK:-$(grep -E '^ZED_SDK=' "$ROOT/docker/.env" 2>/dev/null | cut -d= -f2 || true)}"
ZED_SDK="${ZED_SDK:-5.4.1}"
WRAPPER="$ROOT/third_party/zed-ros2-wrapper"
[[ -d "$WRAPPER/docker" ]] || { echo "missing $WRAPPER — run scripts/fetch_third_party.sh first"; exit 1; }

case "${1:-desktop}" in
  desktop)
    ( cd "$WRAPPER/docker" && ./build_desktop.sh --ros-distro jazzy --os ubuntu-24.04 --sdk "$ZED_SDK" --cuda 12.8 )
    src=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep -m1 -E "zed_ros2_jazzy.*ubuntu.*24" || true)
    tag=bisg/zed:desktop ;;
  jetson)
    # Base image must match the board's L4T exactly (this Orin NX: R39.2.1) or the SDK refuses to start.
    L4T="${ZED_L4T:-$(sed -nE 's/^# R([0-9]+) \(release\), REVISION: ([0-9]+)\..*/r\1.\2/p' /etc/nv_tegra_release 2>/dev/null)}"
    [[ -n "$L4T" ]] || { echo "cannot read L4T from /etc/nv_tegra_release; set ZED_L4T=r39.2"; exit 1; }
    ( cd "$WRAPPER/docker" && ./build_jetson.sh --ros-distro jazzy --os "l4t-$L4T" --sdk "$ZED_SDK" )
    src=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep -m1 -E "zed_ros2_jazzy.*l4t-$L4T" || true)
    tag=bisg/zed:jetson ;;
  *) echo "usage: $0 desktop|jetson"; exit 2 ;;
esac
[[ -n "$src" ]] || { echo "build finished but no zed_ros2 image found (docker images | grep zed_ros2)"; exit 1; }
# Add the CycloneDDS RMW on top (docker/zed/rmw.Dockerfile), then tag the result.
docker build -f "$ROOT/docker/zed/rmw.Dockerfile" --build-arg BASE="$src" -t "$tag" "$ROOT/docker/zed" && echo "built $tag from $src"
