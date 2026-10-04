#!/usr/bin/env bash
# The real drone: MAVROS on the Pixracer + the ZED stack on the real camera (compose profile `drone`, docker/compose.yaml).
# Same file and images as the sim, picked by CPU architecture: on the Jetson (arm64) bisg/zed:l4t-r38, on the workstation
# bisg/zed:desktop (bench test with a USB ZED Mini). What the ZED does is docker/zed/zed.yaml, minus its `sim:` block.
#
#   drone.sh build                    build the images for THIS machine: bisg/ros:jazzy and bisg/zed:<variant> (once; ZED image ~15 GB)
#   drone.sh up [--drone N] [--fcu URL]   MAVROS (serial, DRONE_FCU_URL, default serial:///dev/px4:921600) + wrapper + the services the YAML enables
#   drone.sh down | status | logs [mavros|zed|bridge|video] [-f]
#   drone.sh check [args]             live SDK check without ground truth (tests/zed_sdk_check.py --no-gt)
set -euo pipefail
. "$(dirname "$0")/_common.sh"

sub="${1:-status}"; shift || true
passthru=()
while [[ $# -gt 0 ]]; do case "$1" in
  --drone) export DRONE_ID=$2; shift;;
  --fcu) export DRONE_FCU_URL=$2; shift;;
  *) passthru+=("$1");; esac; shift; done
export ZED_STACK_SIM=0                       # hardware: no `sim:` deltas, real clock
ZNAME="bisg-zed-${DRONE_ID}"; MNAME="bisg-mavros-${DRONE_ID}"
svc_name(){ case $1 in mavros) echo "$MNAME";; zed|wrapper) echo "$ZNAME";; bridge) echo "bisg-zed-bridge-${DRONE_ID}";; video) echo "bisg-zed-video-${DRONE_ID}";; *) die "unknown service $1 (mavros|zed|bridge|video)";; esac; }
zexec(){ docker exec "$ZNAME" bash -lc "source /sbin/ros_entrypoint.sh >/dev/null 2>&1; $*"; }

case "$sub" in
  build)
    info "images for ${BISG_ARCH}: bisg/ros:jazzy, bisg/zed:${ZED_VARIANT}"
    compose --profile drone build drone-mavros
    "$ROOT/docker/zed/build.sh";;

  up)
    zs plan >/dev/null || die "docker/zed/zed.yaml is invalid (fix it: ./bisg zed plan --hw)"
    for img in bisg/ros:jazzy "bisg/zed:${ZED_VARIANT}"; do docker image inspect "$img" >/dev/null 2>&1 || die "$img is not built on this machine: ./bisg drone build"; done
    [[ -e /dev/px4 ]] || die "/dev/px4 not found: add the udev rule for the Pixracer (docs/hardware.md); drone-mavros maps that device into its container"
    info "drone ${DRONE_ID} on ${BISG_ARCH}: MAVROS (${DRONE_FCU_URL:-serial:///dev/px4:921600}) + ZED wrapper (bisg/zed:${ZED_VARIANT})"
    compose --profile drone up -d --force-recreate drone-mavros drone-zed
    for s in $(zs services); do compose --profile drone up -d --force-recreate "$s"; ok "$s started"; done
    for s in zed-bridge zed-video; do [[ " $(zs services | tr '\n' ' ') " == *" $s "* ]] || compose --profile drone rm -sf "$s" >/dev/null 2>&1 || true; done
    ok "up. ./bisg drone status";;

  down) compose --profile drone rm -sf drone-mavros drone-zed zed-bridge zed-video >/dev/null 2>&1 || true; ok "drone ${DRONE_ID} stack stopped";;

  status)
    docker ps -a --filter "name=bisg-.*-${DRONE_ID}$" --format '  {{.Names}}\t{{.Status}}\t{{.Image}}'
    container_running "$MNAME" && docker exec "$MNAME" bash -lc "source /opt/ros/jazzy/setup.bash; timeout 8 ros2 topic echo --once /drone_${DRONE_ID}/mavros/state 2>/dev/null | grep -E '^(connected|armed|mode):'" | sed 's/^/  mavros /' || warn "MAVROS not running"
    container_running "$ZNAME" && zexec "for t in left/color/rect/image depth/depth_registered odom imu/data; do
        printf '  %-26s' \\$t; timeout 8 ros2 topic hz /drone_${DRONE_ID}/zed/zed_node/\\$t 2>&1 | grep -m1 'average rate' || echo '(none)'; done" || warn "ZED wrapper not running";;

  logs)
    which=zed; follow=""
    for a in "${passthru[@]:-}"; do case "$a" in mavros|zed|bridge|video) which=$a;; -f|--follow) follow=-f;; "") ;; *) die "logs: mavros|zed|bridge|video [-f]";; esac; done
    exec docker logs $follow --tail 100 "$(svc_name $which)";;

  check) container_running "$ZNAME" || die "$ZNAME is not running (./bisg drone up)"
         zexec "python3 /workspace/tests/zed_sdk_check.py --drone ${DRONE_ID} --no-gt ${passthru[*]:-}";;

  *) sed -n 2,13p "$0"; exit 2;;
esac
