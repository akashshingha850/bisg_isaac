#!/usr/bin/env bash
# Clone the pinned upstream repos into the docker image folders (docker/sim, docker/zed) for reading, local edits and the ZED build scripts.
# The sim image clones PX4 fresh at build time (NOT required for that); Pegasus is built FROM the
# docker/sim/PegasusSimulator submodule (git submodule update --init required before building sim).
# After `git init`, convert to submodules:  git submodule add -b <tag> <url> docker/<image>/<name>
set -euo pipefail
. "$(dirname "$0")/_common.sh"      # tags and repo URLs come from config/bisg.conf / docker/.env
SIM="$ROOT/docker/sim"; ZED="$ROOT/docker/zed"
clone(){ local url=$1 tag=$2 dir=$3; shift 3
  if [[ -e "$dir/.git" ]]; then echo "exists: ${dir#$ROOT/}"; else git clone --depth 1 --branch "$tag" "$@" "$url" "$dir"; fi; }
if [[ "$PEGASUS_TAG" =~ ^pr([0-9]+)-([0-9a-f]+)$ ]]; then
  # Isaac Sim 6.0 support lives in Pegasus PR #144 (not yet a release tag): fetch the PR head, check out the pinned SHA.
  if [[ -e "$SIM/PegasusSimulator/.git" ]]; then echo "exists: docker/sim/PegasusSimulator"; else
    git clone --no-checkout "$PEGASUS_REPO" "$SIM/PegasusSimulator"
    git -C "$SIM/PegasusSimulator" fetch origin "refs/pull/${BASH_REMATCH[1]}/head:pr${BASH_REMATCH[1]}"
    git -C "$SIM/PegasusSimulator" checkout -B local "${BASH_REMATCH[2]}"
  fi
else
  clone "$PEGASUS_REPO" "$PEGASUS_TAG" "$SIM/PegasusSimulator"
fi
clone "$ZED_WRAPPER_REPO" "v${ZED_SDK}" "$ZED/zed-ros2-wrapper"
clone "$ZED_ISAAC_EXT_REPO" "$ZED_ISAAC_EXT_TAG" "$ZED/zed-isaac-sim"   # built by docker/zed/build_isaac_ext.sh (./bisg zed build)
if [[ "${WITH_PX4:-0}" == "1" ]]; then   # ~1 GB even shallow; only for reading/patching firmware
  clone "$PX4_REPO" "$PX4_TAG" "$SIM/PX4-Autopilot" --recursive --shallow-submodules
fi
echo "done: docker/sim: $(ls -d "$SIM"/*/ 2>/dev/null | xargs -n1 basename | tr '\n' ' ') | docker/zed: $(ls -d "$ZED"/*/ 2>/dev/null | xargs -n1 basename | tr '\n' ' ')"
