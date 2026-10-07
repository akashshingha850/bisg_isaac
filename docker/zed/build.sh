#!/usr/bin/env bash
# Build the ZED SDK + zed-ros2-wrapper image with Stereolabs' official build scripts
# (docker/zed/zed-ros2-wrapper/docker). We do not maintain our own ZED Dockerfile.
#
#   docker/zed/build.sh              # no argument = the variant for this machine (desktop on x86_64, jetson on aarch64)
#   docker/zed/build.sh desktop      # x86_64 workstation: Jazzy, Ubuntu 24.04, SDK $ZED_SDK
#   docker/zed/build.sh --force      # rebuild the upstream image even if the wrapper sources / SDK version are unchanged
#   docker/zed/build.sh jetson       # Orin NX, JetPack 7.x (L4T r38.4): run ON the Jetson (or arm64 buildx host)
#
# Result: the upstream image is tagged bisg/zed:<variant>-base, then docker/zed/Dockerfile.overlay adds CycloneDDS
# on top -> bisg/zed:<variant> (what docker/compose.yaml uses: ZED_VARIANT = desktop | l4t-r38, chosen by ./bisg from the CPU architecture).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ZED_SDK="${ZED_SDK:-$(grep -E '^ZED_SDK=' "$ROOT/docker/.env" 2>/dev/null | cut -d= -f2 || true)}"
ZED_SDK="${ZED_SDK:-5.4.1}"
WRAPPER="$ROOT/docker/zed/zed-ros2-wrapper"
[[ -d "$WRAPPER/docker" ]] || { echo "missing $WRAPPER — run scripts/fetch_sources.sh first"; exit 1; }

FORCE=0; [[ "${1:-}" == "--force" ]] && { FORCE=1; shift; }
# The upstream script re-copies the wrapper into its build context every run, so Docker's cache never hits and the wrapper is
# recompiled (minutes). Skip that when the wrapper checkout + SDK version are exactly what the existing base image was built from.
src_stamp(){ { git -C "$WRAPPER" rev-parse HEAD; git -C "$WRAPPER" diff HEAD | sha256sum; echo "$ZED_SDK"; sha256sum "$ROOT/docker/zed/build.sh" | cut -d' ' -f1; } 2>/dev/null | tr '\n' ' '; }
default=desktop; [[ "$(uname -m)" == aarch64 ]] && default=jetson     # pick by CPU architecture
variant="${1:-$default}"
STAMP="$ROOT/docker/zed/.build-stamp-$variant"
if (( ! FORCE )) && [[ "$variant" != "" ]] && docker image inspect "bisg/zed:${variant/jetson/l4t-r38}-base" >/dev/null 2>&1 \
   && [[ -f "$STAMP" && "$(cat "$STAMP")" == "$(src_stamp)" ]]; then
  echo "bisg/zed:${variant/jetson/l4t-r38}-base is up to date (wrapper sources + SDK $ZED_SDK unchanged); skipping the upstream build (--force rebuilds)"
  final=bisg/zed:${variant/jetson/l4t-r38}; docker build -f "$ROOT/docker/zed/Dockerfile.overlay" --build-arg BASE="${final}-base" -t "$final" "$ROOT/docker/zed" && echo "built $final"
  exit 0
fi
case "$variant" in
  desktop)
    ( cd "$WRAPPER/docker" && ./build_desktop.sh --ros-distro jazzy --os ubuntu-24.04 --sdk "$ZED_SDK" --cuda 12.8 )
    src=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep -m1 -E "zed_ros2_(desktop_)?jazzy.*u(buntu)?-?24" || true)
    tag=bisg/zed:desktop-base; final=bisg/zed:desktop ;;
  jetson)
    # JetPack 7.x = L4T r38.4 (Ubuntu 24.04, CUDA 13). Adjust --os if `cat /etc/nv_tegra_release` differs.
    ( cd "$WRAPPER/docker" && ./build_jetson.sh --ros-distro jazzy --os l4t-r38.4 --sdk "$ZED_SDK" )
    src=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep -m1 -E "zed_ros2_(l4t_|jetson_)?jazzy.*(l4t|jetson)|zed_ros2_(l4t|jetson).*jazzy" || true)
    tag=bisg/zed:l4t-r38-base; final=bisg/zed:l4t-r38 ;;
  *) echo "usage: $0 desktop|jetson"; exit 2 ;;
esac
[[ -n "$src" ]] || { echo "build finished; tag the zed_ros2 image manually to $tag (docker images | grep zed_ros2), then re-run the overlay step"; exit 1; }
docker tag "$src" "$tag" && echo "tagged $src -> $tag"
# Overlay: + CycloneDDS (the upstream image is Fast DDS only), see docker/zed/Dockerfile.overlay
docker build -f "$ROOT/docker/zed/Dockerfile.overlay" --build-arg BASE="$tag" -t "$final" "$ROOT/docker/zed" && echo "built $final"
src_stamp > "$STAMP"
