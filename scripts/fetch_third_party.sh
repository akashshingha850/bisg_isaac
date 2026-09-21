#!/usr/bin/env bash
# Clone the pinned upstream repos into third_party/ for reading, patching and the ZED build scripts.
# The sim image clones PX4 and Pegasus itself at build time, so these are NOT required to build/run the sim.
# After `git init`, convert to submodules:  git submodule add -b <tag> <url> third_party/<name>
set -euo pipefail
. "$(dirname "$0")/_common.sh"      # tags and repo URLs come from config/bisg.conf / docker/.env
cd "$ROOT/third_party"
clone(){ local url=$1 tag=$2 dir=$3; shift 3
  if [[ -d "$dir/.git" ]]; then echo "exists: $dir"; else git clone --depth 1 --branch "$tag" "$@" "$url" "$dir"; fi; }
clone "$PEGASUS_REPO" "$PEGASUS_TAG" PegasusSimulator
clone "$ZED_WRAPPER_REPO" "v${ZED_SDK}" zed-ros2-wrapper
if [[ "${WITH_PX4:-0}" == "1" ]]; then   # ~1 GB even shallow; only for reading/patching firmware
  clone "$PX4_REPO" "$PX4_TAG" PX4-Autopilot --recursive --shallow-submodules
fi
echo "done: $(ls -d */ 2>/dev/null | tr '\n' ' ')"
