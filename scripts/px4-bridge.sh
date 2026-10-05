#!/usr/bin/env bash
# The PX4 bridge: ONE compose service (px4-bridge, docker/compose.yaml), one container per drone and bridge: bisg-<mavros|mavsdk|xrce>-N.
# PX4_BRIDGE (config/bisg.conf) names what to run, one value or several ("mavros,xrce"). Usually called through ./bisg px4-bridge.   docs/px4-bridge.md
#
#   px4-bridge.sh plan [NAME..]    what would run and what it connects to; starts nothing
#   px4-bridge.sh up [NAME..]      start them; names (mavros | mavsdk | xrce | none) override PX4_BRIDGE for this run
#   px4-bridge.sh down [NAME..]    stop this drone's bridges (no name = all of them)       down --all: every drone's
#   px4-bridge.sh status [--all]   logs [NAME] [-f]   params [NAME]   build
#   flags: --drone N   --hw (serial port /dev/px4 instead of the sim's UDP; default on arm64)
set -euo pipefail
. "$(dirname "$0")/_common.sh"

sub="${1:-status}"; shift || true
hw=0; follow=""; all=0; names=(); [[ "$BISG_ARCH" == arm64 ]] && hw=1
while [[ $# -gt 0 ]]; do case "$1" in
  --drone) export DRONE_ID=$2; shift;; --hw) hw=1;; --all) all=1;; -f|--follow) follow=-f;;
  mavros|mavsdk|xrce|none) names+=("$1");;
  *) die "px4-bridge: unknown arg $1 (NAME: mavros mavsdk xrce none; flags: --drone N --hw --all -f)";; esac; shift; done
nexp=${#names[@]}; ((nexp)) || IFS=, read -ra names <<<"$PX4_BRIDGE"
for b in "${names[@]}"; do case "$b" in mavros|mavsdk|xrce|none) ;; *) die "PX4_BRIDGE: '$b' is not mavros | mavsdk | xrce | none (config/bisg.conf)";; esac; done
((hw)) && bridge_env_drone
ALL=(mavros mavsdk xrce)
cname(){ echo "bisg-$1-${DRONE_ID}"; }                  # one container per bridge and drone, so drones and methods run side by side
pcompose(){ docker compose -p "bisg-px4-$1-${DRONE_ID}" -f "$COMPOSE_FILE" --profile px4-bridge "${@:2}"; }   # own project each: `up` for one never touches another
port=$((14540 + DRONE_ID - 1)); ser="${DRONE_FCU_URL:-serial:///dev/px4:921600}"
rivals(){ if ((hw)); then printf '%s\n' "${ALL[@]}" | grep -vx "$1" || true; else case $1 in mavros) echo mavsdk;; mavsdk) echo mavros;; esac; fi; }   # share $1's endpoint

endpoint(){
  case "$1:$hw" in
    mavros:0) echo "MAVLink ${FCU_URL:-udp://:${port}@127.0.0.1:$((14580 + DRONE_ID - 1))} -> ROS 2 /drone_${DRONE_ID}/mavros/*, plugins ${MAVROS_PLUGINS}";;
    mavros:1) echo "MAVLink ${ser} -> ROS 2 /drone_${DRONE_ID}/mavros/*, plugins ${MAVROS_PLUGINS}";;
    mavsdk:0) echo "MAVLink udpin://0.0.0.0:${port} -> gRPC localhost:${MAVSDK_PORT}";;
    mavsdk:1) echo "MAVLink ${ser} -> gRPC localhost:${MAVSDK_PORT}";;
    xrce:0)   echo "XRCE udp4 :${XRCE_PORT} (PX4's client dials it) -> ROS 2 /fmu/in|out/*, domain ${ROS_DOMAIN_ID}";;
    xrce:1)   echo "XRCE serial /dev/px4 @ ${XRCE_BAUD} -> ROS 2 /fmu/in|out/*, domain ${ROS_DOMAIN_ID}";;
    none:*)   echo "nothing";;
  esac
}
stop(){ local b; for b in "$@"; do docker rm -f "$(cname "$b")" >/dev/null 2>&1 || true; done; }

case "$sub" in
  plan) info "PX4 bridge, drone ${DRONE_ID} ($([[ $hw == 1 ]] && echo drone || echo sim))"
        for b in "${names[@]}"; do printf '  %-6s %s\n' "$b" "$(endpoint "$b")"; done;;

  up)
    run=(); for b in "${names[@]}"; do [[ $b == none ]] || run+=("$b"); done
    ((${#run[@]})) || { stop "${ALL[@]}"; ok "none: no bridge running for drone ${DRONE_ID}"; exit 0; }
    for b in "${run[@]}"; do for r in $(rivals "$b"); do [[ " ${run[*]} " == *" $r "* ]] && die "$b and $r cannot run together here: they share one endpoint (docs/px4-bridge.md)"; done; done
    docker image inspect bisg/px4-bridge:jazzy >/dev/null 2>&1 || die "bisg/px4-bridge:jazzy is not built: ./bisg px4-bridge build"
    if ((hw)); then [[ -e /dev/px4 ]] || die "/dev/px4 not found: add the Pixracer udev rule (docs/hardware.md)"; fi
    for b in "${run[@]}"; do
      stop $(rivals "$b" | grep -vxF "$(printf '%s\n' "${run[@]}")" || true)
      info "$b: $(endpoint "$b")"
      PX4_BRIDGE=$b pcompose "$b" up -d --force-recreate px4-bridge >/dev/null; ok "$(cname "$b") started"
    done
    [[ " ${run[*]} " == *" mavros "* ]] || warn "no MAVROS: vio_mock, the ZED PX4 bridge (zed-bridge) and tests/vio_flight.py talk to /drone_${DRONE_ID}/mavros";;

  down)
    if ((all)); then ids=$(docker ps -aq --filter 'name=^bisg-(mavros|mavsdk|xrce)-[0-9]+$'); [[ -z "$ids" ]] || docker rm -f $ids >/dev/null; ok "stopped every PX4 bridge"; exit 0; fi
    if ((nexp)) && [[ "${names[*]}" != none ]]; then stop "${names[@]}"; ok "stopped ${names[*]} of drone ${DRONE_ID}"; exit 0; fi
    stop "${ALL[@]}"; ok "stopped the PX4 bridges of drone ${DRONE_ID}";;

  status)
    flt="^bisg-(mavros|mavsdk|xrce)-${DRONE_ID}\$"; ((all)) && flt='^bisg-(mavros|mavsdk|xrce)-[0-9]+$'
    mapfile -t cs < <(docker ps --filter "name=$flt" --format '{{.Names}}' | sort)
    ((${#cs[@]})) || { info "PX4 bridge: none running (PX4_BRIDGE=${PX4_BRIDGE}, drone ${DRONE_ID})"; exit 0; }
    for n in "${cs[@]}"; do
      b="${n#bisg-}"; b="${b%-*}"; d="${n##*-}"; up="$(docker ps --filter "name=^${n}\$" --format '{{.Status}}')"
      case $b in
        mavros) st="$(docker exec "$n" bash -lc "source /opt/ros/jazzy/setup.bash; timeout 8 ros2 topic echo --once /drone_${d}/mavros/state 2>/dev/null | grep -E '^(connected|armed|mode):' | tr '\n' ' '" || true)";;
        mavsdk) st="PX4 discovered x$(docker logs --tail 400 "$n" 2>&1 | grep -ciE 'system discovered' || true); gRPC :${MAVSDK_PORT} $(ss -ltn 2>/dev/null | grep -q ":${MAVSDK_PORT} " && echo listening || echo NOT listening)";;
        xrce)   st="ros2 topics under /fmu: $(docker exec "$n" bash -lc "source /opt/ros/jazzy/setup.bash; source /opt/px4_ws/install/setup.bash; timeout 8 ros2 topic list 2>/dev/null | grep -c '^/fmu'" 2>/dev/null || echo '?')";;
      esac
      printf '  drone %s  %-6s running (%s)  %s\n' "$d" "$b" "$up" "${st:-}"
    done;;

  logs) b="${names[0]}"; [[ $b == none ]] && die "logs: mavros | mavsdk | xrce"; exec docker logs $follow --tail 200 "$(cname "$b")";;

  params)
    b="${names[0]}"
    echo "PX4 parameters for '${b}' on a Pixracer (fmu-v4), companion on TELEM2 (docs/hardware.md); set them in QGC, then reboot the FC."
    echo "Names and values follow PX4 v1.17; the serial enums are board-specific, confirm them in QGC's parameter list."
    case $b in
      mavros|mavsdk) printf '  %-17s %s\n' MAV_1_CONFIG "TELEM 2 (102)" MAV_1_MODE "Onboard (2)" MAV_1_RATE "0 (the port's maximum)" SER_TEL2_BAUD 921600 UXRCE_DDS_CFG "Disabled (0): the DDS client must not share this port";;
      xrce) printf '  %-17s %s\n' UXRCE_DDS_CFG "TELEM 2 (102)" SER_TEL2_BAUD "921600 (= XRCE_BAUD)" MAV_1_CONFIG "Disabled (0): QGC then needs USB or a radio" UXRCE_DDS_DOM_ID "${ROS_DOMAIN_ID} (= ROS_DOMAIN_ID)" UXRCE_DDS_NS_IDX "${DRONE_ID} (= DRONE_ID: topics become /uav_${DRONE_ID}/fmu/*; PX4 offers only uav_<index>, not /drone_<id>)"
            echo "  note: no parameter access over this bridge; landing target, follow target, STATUSTEXT and the camera protocol are MAVLink only";;
      none) echo "  (none: no bridge)";;
    esac;;

  build) info "building bisg/ros:jazzy and bisg/px4-bridge:jazzy for ${BISG_ARCH} (the agent compile takes ~10 min)"
         compose --profile ros build ros && compose --profile px4-bridge build px4-bridge;;

  *) sed -n 2,10p "$0"; exit 2;;
esac
