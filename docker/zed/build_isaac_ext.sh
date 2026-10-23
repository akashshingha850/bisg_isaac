#!/usr/bin/env bash
# Build Stereolabs' `zed-isaac-sim` Isaac Sim extension (docker/zed/zed-isaac-sim, tag ZED_ISAAC_EXT_TAG).
# The extension streams a simulated ZED camera (stereo + IMU) into the real ZED SDK / zed_wrapper, so the
# sim and the Jetson run the same perception stack (docs/zed-sdk-sim.md).
#
#   docker/zed/build_isaac_ext.sh        # ~3 min: downloads Stereolabs' sl_zed libs + Kit SDK, compiles the plugin
#
# Built inside the bisg/sim image (has the toolchain, nothing is installed on the host; LD_LIBRARY_PATH is cleared because
# the image points it at Isaac's bundled ROS libs, whose libcrypto breaks wget/openssl); output stays in
# docker/zed/zed-isaac-sim/exts/sl.sensor.camera/bin and is picked up by the sim launcher via --ext-folder.
# Needs `./bisg setup` (bisg/sim image); clones the extension source itself if it is missing.
# Local fixes to the pinned extension are docker/zed/patches-isaac-ext/*.patch (the clone is git-ignored, so they are the only
# record): checked, applied for the build, reverted afterwards; the built bin/ keeps them (docs/zed-sdk-sim.md).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
. "$ROOT/scripts/_common.sh"
EXT="$ROOT/docker/zed/zed-isaac-sim"
IMG="bisg/sim:${ISAAC_TAG}"
if [[ ! -f "$EXT/build.sh" ]]; then   # source not cloned yet: fetch just this repo (pinned tag)
  info "cloning $ZED_ISAAC_EXT_REPO @ $ZED_ISAAC_EXT_TAG"
  git clone --depth 1 --branch "$ZED_ISAAC_EXT_TAG" "$ZED_ISAAC_EXT_REPO" "$EXT" || die "clone of $ZED_ISAAC_EXT_REPO failed"
fi
docker image inspect "$IMG" >/dev/null 2>&1 || die "image $IMG not built — run ./bisg setup"

# The v5.2.x extension declares Kit 110.1.2 (Isaac Sim 6.0.1); the 6.0.0 image is Kit 110.1.1. The code is the same,
# only the load gate differs, so widen it. (Remove once ISAAC_TAG moves to 6.0.1.)
TOML="$EXT/exts/sl.sensor.camera/config/extension.toml"
if grep -q '^kit = \["110.1.2"\]' "$TOML"; then
  sed -i 's/^kit = \["110.1.2"\]/kit = ["110.1.1", "110.1.2"]/' "$TOML"
  info "widened extension Kit range to 110.1.1 + 110.1.2 (image ISAAC_TAG=${ISAAC_TAG})"
fi

BIN="$EXT/exts/sl.sensor.camera/bin"
STAMP="$EXT/.bisg-built"
PATCHES=("$ROOT"/docker/zed/patches-isaac-ext/*.patch)
[[ -e "${PATCHES[0]}" ]] || PATCHES=()
stamp(){ { git -C "$EXT" rev-parse HEAD; git -C "$EXT" diff HEAD | sha256sum; echo "$IMG"
           if (( ${#PATCHES[@]} )); then cat "${PATCHES[@]}" | sha256sum; fi; } 2>/dev/null | tr '\n' ' '; }
if [[ "${1:-}" != "--force" && -f "$BIN/libsl.sensor.camera.plugin.so" && -f "$BIN/libsl_zed.so" && -f "$STAMP" && "$(cat "$STAMP")" == "$(stamp)" ]]; then
  ok "extension already built from this source ($EXT/exts); skipping (--force rebuilds)"; exit 0
fi

# Kit's packman dependencies (CUDA, Kit SDK, python: ~12 GB unpacked) go to a host cache so they are fetched once and
# do not fill the container layer. Override with PACKMAN_CACHE (e.g. a path on /opt when / is small).
CACHE="${PACKMAN_CACHE:-${XDG_CACHE_HOME:-$HOME/.cache}/packman}"
mkdir -p "$CACHE"

STAMP_NOW="$(stamp)"            # before patching: names the source + patches, not the patched tree
unpatch(){ for p in "${PATCHES[@]}"; do git -C "$EXT" apply -R "$p" 2>/dev/null || true; done; }
for p in "${PATCHES[@]}"; do
  git -C "$EXT" apply --check "$p" || die "patch $(basename "$p") does not apply to zed-isaac-sim at $(git -C "$EXT" rev-parse --short HEAD)"
done
trap unpatch EXIT
for p in "${PATCHES[@]}"; do git -C "$EXT" apply "$p" && info "applied $(basename "$p")"; done
info "building zed-isaac-sim ${ZED_ISAAC_EXT_TAG} in $IMG (as uid $(id -u); packman cache $CACHE)"
docker run --rm --user "$(id -u):$(id -g)" --entrypoint bash \
  -e HOME=/tmp -e LD_LIBRARY_PATH= -e PM_PACKAGES_ROOT=/packman \
  -v "$EXT:/src" -v "$CACHE:/packman" -w /src "$IMG" -c './build.sh'

for f in libsl.sensor.camera.plugin.so libsl_zed.so; do
  [[ -f "$BIN/$f" ]] || die "build finished but $BIN/$f is missing"
done
echo "$STAMP_NOW" > "$STAMP"
ok "extension built: $EXT/exts (sl.sensor.camera ${ZED_ISAAC_EXT_TAG})"
