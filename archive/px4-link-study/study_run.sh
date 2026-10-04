#!/usr/bin/env bash
# Run a command in a throw-away ZED SDK container with the study data mounted (docs/study-vo-perception.md).
#   scripts/study_run.sh <command...>      (cwd inside the container: /workspace, tests/ and logs/ visible)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec docker run --rm --cpuset-cpus 0-21 --runtime nvidia -e NVIDIA_VISIBLE_DEVICES=all -e NVIDIA_DRIVER_CAPABILITIES=all \
  -v "$ROOT":/workspace -v bisg_zed-resources:/usr/local/zed/resources -v bisg_zed-settings:/usr/local/zed/settings \
  -w /workspace --entrypoint bash bisg/zed:desktop -lc "source /sbin/ros_entrypoint.sh >/dev/null 2>&1; $*"
