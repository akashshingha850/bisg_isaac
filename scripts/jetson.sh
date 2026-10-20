#!/usr/bin/env bash
# Operate the on-board stack (deploy/jetson/compose.yaml: mavros on the Pixracer serial link, zed,
# foxglove bridge, tailscale).
# ./bisg routes here automatically on aarch64 (the Jetson; the x86_64 workstation runs the sim), so Isaac Sim is
# never pulled on the drone.
#
#   jetson.sh up [mavros|zed|foxglove|tailscale]   start all on-board services (or some)
#   jetson.sh stop | down | restart [svc]
#   jetson.sh status                   containers + FCU device
#   jetson.sh logs [svc] [-f]
#   jetson.sh shell [svc]
set -euo pipefail
. "$(dirname "$0")/_common.sh"

JCOMPOSE="$ROOT/deploy/jetson/compose.yaml"
jcompose(){ docker compose -f "$JCOMPOSE" --profile jetson "$@"; }

# FCU_URL set -> used as is. Empty -> /dev/px4 (udev), a USB PX4 (by-id), any ttyACM/ttyUSB,
# then each Tegra UART that actually carries MAVLink at FCU_BAUD. Exports FCU_URL + FCU_DEV for compose.
fcu_detect(){
  local d
  if [[ -n "${FCU_URL:-}" ]]; then
    [[ $FCU_URL =~ ^serial://(/[^:]+) ]] && FCU_DEV="${BASH_REMATCH[1]}" || FCU_DEV=/dev/null
    export FCU_URL FCU_DEV; ok "FCU $FCU_URL (${BISG_SRC[FCU_URL]:-set})"; return 0
  fi
  if container_running bisg-mavros; then                  # it owns the port; probing would steal bytes
    FCU_URL="$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' bisg-mavros | grep -m1 '^FCU_URL=' | cut -d= -f2-)"
    [[ $FCU_URL =~ ^serial://(/[^:]+) ]] && FCU_DEV="${BASH_REMATCH[1]}" || FCU_DEV=/dev/null
    export FCU_URL FCU_DEV; ok "FCU $FCU_URL (running mavros)"; return 0
  fi
  local cands=(/dev/px4 /dev/serial/by-id/*{PX4,Pixracer,3D_Robotics,ArduPilot}* /dev/ttyACM* /dev/ttyUSB*)
  for d in "${cands[@]}"; do [[ -e $d ]] && { FCU_DEV="$d"; break; }; done
  if [[ -z "${FCU_DEV:-}" ]]; then
    for d in /dev/ttyTHS*; do
      [[ -e $d ]] || continue
      fuser -s "$d" 2>/dev/null && continue                # in use (another mavros / console)
      python3 "$ROOT/scripts/fcu_probe.py" "$d" "$FCU_BAUD" && { FCU_DEV="$d"; break; }
    done
  fi
  [[ -n "${FCU_DEV:-}" ]] || { warn "no FCU found (no /dev/px4, USB PX4, or UART with MAVLink at $FCU_BAUD baud); set FCU_URL to force one"; return 1; }
  FCU_DEV="$(readlink -f "$FCU_DEV")"
  export FCU_DEV FCU_URL="serial://$FCU_DEV:$FCU_BAUD"
  ok "FCU auto-detected: $FCU_URL"
}

cmd_up(){
  info "starting on-board stack (${*:-all})"
  if [[ $# -eq 0 || " $* " == *" mavros "* ]] && ! fcu_detect; then
    [[ $# -eq 0 ]] && { set -- $(jcompose config --services | grep -vx mavros); warn "starting without mavros: $*"; } || die "mavros needs an FCU"
  fi
  jcompose up -d --remove-orphans "$@"
  cmd_status
}

cmd_status(){
  info "containers"; jcompose ps --format '  {{.Name}}\t{{.Status}}\t{{.Image}}' || true
  container_running bisg-mavros && echo "  mavros FCU: $(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' bisg-mavros | grep -m1 '^FCU_URL=' | cut -d= -f2-)"
  return 0
}

cmd_logs(){
  local f=() s=()
  for a in "$@"; do [[ $a == -f ]] && f=(-f) || s+=("$a"); done
  jcompose logs --tail 200 "${f[@]}" "${s[@]}"
}

cmd_shell(){ docker exec -it "bisg-${1:-mavros}" bash; }

usage(){ sed -n 2,10p "$0"; }

case "${1:-}" in
  up) shift; cmd_up "$@";; status) cmd_status;; logs) shift; cmd_logs "$@";; shell) shift; cmd_shell "$@";;
  stop) shift; info "stopping"; jcompose stop "$@";;
  down) info "removing containers"; jcompose down --remove-orphans;;
  restart) shift; jcompose restart "$@";;
  *) usage;;
esac
