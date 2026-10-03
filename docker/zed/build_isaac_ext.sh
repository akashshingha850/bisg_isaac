#!/usr/bin/env bash
# Build Stereolabs' `zed-isaac-sim` Isaac Sim extension (third_party/zed-isaac-sim, tag ZED_ISAAC_EXT_TAG).
# The extension streams a simulated ZED camera (stereo + IMU) into the real ZED SDK / zed_wrapper, so the
# sim and the Jetson run the same perception stack (docs/zed-sdk-sim.md).
#
#   docker/zed/build_isaac_ext.sh        # ~3 min: downloads Stereolabs' sl_zed libs + Kit SDK, compiles the plugin
#
# Built inside the bisg/sim image (has the toolchain, nothing is installed on the host; LD_LIBRARY_PATH is cleared because
# the image points it at Isaac's bundled ROS libs, whose libcrypto breaks wget/openssl); output stays in
# third_party/zed-isaac-sim/exts/sl.sensor.camera/bin and is picked up by the sim launcher via --ext-folder.
# Needs `./bisg setup` (bisg/sim image) and `scripts/fetch_third_party.sh` first.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
. "$ROOT/scripts/_common.sh"
EXT="$ROOT/third_party/zed-isaac-sim"
IMG="bisg/sim:${ISAAC_TAG}"
[[ -f "$EXT/build.sh" ]] || die "missing $EXT — run scripts/fetch_third_party.sh first"
docker image inspect "$IMG" >/dev/null 2>&1 || die "image $IMG not built — run ./bisg setup"

# The v5.2.x extension declares Kit 110.1.2 (Isaac Sim 6.0.1); the 6.0.0 image is Kit 110.1.1. The code is the same,
# only the load gate differs, so widen it. (Remove once ISAAC_TAG moves to 6.0.1.)
TOML="$EXT/exts/sl.sensor.camera/config/extension.toml"
if grep -q '^kit = \["110.1.2"\]' "$TOML"; then
  sed -i 's/^kit = \["110.1.2"\]/kit = ["110.1.1", "110.1.2"]/' "$TOML"
  info "widened extension Kit range to 110.1.1 + 110.1.2 (image ISAAC_TAG=${ISAAC_TAG})"
fi

# Kit's packman dependencies (CUDA, Kit SDK, python: ~12 GB unpacked) go to a host cache so they are fetched once and
# do not fill the container layer. Override with PACKMAN_CACHE (e.g. a path on /opt when / is small).
CACHE="${PACKMAN_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/packman}"
mkdir -p "$CACHE"

info "building zed-isaac-sim ${ZED_ISAAC_EXT_TAG} in $IMG (as uid $(id -u); packman cache $CACHE)"
docker run --rm --user "$(id -u):$(id -g)" --entrypoint bash \
  -e HOME=/tmp -e LD_LIBRARY_PATH= -e PM_PACKAGES_ROOT=/packman \
  -v "$EXT:/src" -v "$CACHE:/packman" -w /src "$IMG" -c './build.sh'

BIN="$EXT/exts/sl.sensor.camera/bin"
for f in libsl.sensor.camera.plugin.so libsl_zed.so; do
  [[ -f "$BIN/$f" ]] || die "build finished but $BIN/$f is missing"
done
ok "extension built: $EXT/exts (sl.sensor.camera ${ZED_ISAAC_EXT_TAG})"
