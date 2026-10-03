#!/usr/bin/env bash
# The real ZED SDK in the sim (docs/zed-sdk-sim.md). Usually called through ./bisg.
#
#   zed.sh ext-build                  build the Stereolabs Isaac Sim extension once (~1-4 min, docker/zed/build_isaac_ext.sh)
#   zed.sh image                      build bisg/zed:desktop (ZED SDK + zed_wrapper + CycloneDDS; ~15 GB, once)
#   zed.sh up [--drone N]             start zed_wrapper for drone N against the sim's streamed ZED Mini (sim must be up
#                                     with ZED_SOURCE=sdk); waits for frames and retries the connect once
#   zed.sh down [--drone N]
#   zed.sh status [--drone N]         wrapper state, topic rates, tracking + image health
#   zed.sh logs [--drone N] [-f]
#   zed.sh check [--drone N] [args]   contract + SDK checks (tests/zed_sdk_check.py), exit 0 = PASS
#
# Typical run:   ZED_SOURCE=sdk ./bisg up headless && ./bisg zed up && ./bisg zed check
set -euo pipefail
. "$(dirname "$0")/_common.sh"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sub="${1:-status}"; shift || true
passthru=()
while [[ $# -gt 0 ]]; do case "$1" in
  --drone) export DRONE_ID=$2; shift;;
  *) passthru+=("$1");; esac; shift; done
ZNAME="bisg-zed-${DRONE_ID}"
# Port math lives with the launcher (sim/launcher/zed_sdk_cfg.py): drone N = vehicle id N-1 -> 30000 + 2*(N-1).
export ZED_SIM_PORT=$((30000 + 2 * (DRONE_ID - 1)))

zexec(){ docker exec "$ZNAME" bash -lc "source /sbin/ros_entrypoint.sh >/dev/null 2>&1; $*"; }
# best_effort: the wrapper publishes sensor-data QoS; a default (reliable) subscriber would never match it
have_frames(){ zexec "timeout 15 ros2 topic echo --once --qos-reliability best_effort --field header.stamp /drone_${DRONE_ID}/zed/zed_node/left/color/rect/image" >/dev/null 2>&1; }

case "$sub" in
  ext-build) exec "$ROOT/docker/zed/build_isaac_ext.sh";;
  image)     exec "$ROOT/docker/zed/build.sh" desktop;;

  up)
    docker image inspect bisg/zed:desktop >/dev/null 2>&1 || die "bisg/zed:desktop is not built: ./bisg zed image"
    container_running "$SIM_NAME" || die "the sim is not running: ZED_SOURCE=sdk ./bisg up headless"
    docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$SIM_NAME" | grep -q '^ZED_SOURCE=sdk$' \
      || warn "the running sim was started with ZED_SOURCE != sdk: it publishes the emulated rig, there is no stream to read"
    [[ -e "/dev/shm/sl_local_video_${ZED_SIM_PORT}" ]] \
      || warn "no ZED stream segment /dev/shm/sl_local_video_${ZED_SIM_PORT} yet: the sim opens it once the timeline plays (./bisg wait)"
    for attempt in 1 2; do
      info "zed_wrapper for drone ${DRONE_ID} (stream port ${ZED_SIM_PORT}, attempt ${attempt}/2)"
      compose --profile zed up -d --force-recreate zed >/dev/null
      for _ in $(seq 1 45); do   # first start also compiles the depth model: allow it
        container_running "$ZNAME" && have_frames && { ok "$ZNAME publishing /drone_${DRONE_ID}/zed/zed_node/*"; exit 0; }
        sleep 4
      done
      warn "no frames after ~3 min; the SDK connects once, so the next try restarts the wrapper"
    done
    docker logs --tail 30 "$ZNAME" 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | cut -c1-200 >&2
    die "zed_wrapper never received frames — see docs/zed-sdk-sim.md 'Troubleshooting'";;

  down) compose --profile zed stop zed >/dev/null 2>&1 || true; compose --profile zed rm -f zed >/dev/null 2>&1 || true; ok "$ZNAME stopped";;

  status)
    container_running "$ZNAME" || { warn "$ZNAME is not running (./bisg zed up)"; exit 1; }
    ok "$ZNAME running"
    zexec "for t in left/color/rect/image depth/depth_registered odom imu/data; do
             printf '  %-26s' \$t; timeout 8 ros2 topic hz /drone_${DRONE_ID}/zed/zed_node/\$t 2>&1 | grep -m1 'average rate' || echo '(none)'; done
           timeout 6 ros2 topic echo --once /drone_${DRONE_ID}/zed/zed_node/status/health 2>&1 | grep -E 'low_' | sed 's/^/  /'";;

  logs) exec docker logs "${passthru[@]:-}" --tail 100 "$ZNAME";;

  check)
    container_running "$ZNAME" || die "$ZNAME is not running (./bisg zed up)"
    zexec "python3 /workspace/tests/zed_sdk_check.py --drone ${DRONE_ID} ${passthru[*]:-}";;

  *) sed -n 2,15p "$0"; exit 2;;
esac
