#!/usr/bin/env bash
# Pull the Isaac Sim base image and (optionally) archive it to the SSD (risk R7).
#   scripts/pull_images.sh            # pull only
#   scripts/pull_images.sh --save     # pull + docker save to $ARCHIVE_DIR
set -euo pipefail
. "$(dirname "$0")/_common.sh"      # ISAAC_TAG / ISAAC_IMAGE / ARCHIVE_DIR from config/bisg.conf
img="${ISAAC_IMAGE}:${ISAAC_TAG}"
echo "pulling $img (about 20 GB, first time only)"
docker pull "$img"
docker pull "$ROS_BASE_IMAGE"
if [[ "${1:-}" == "--save" ]]; then
  mkdir -p "$ARCHIVE_DIR"
  out="$ARCHIVE_DIR/isaac-sim-${ISAAC_TAG}.tar"
  echo "saving $img -> $out"
  docker save "$img" -o "$out"
  echo "restore later with: docker load -i $out"
fi
