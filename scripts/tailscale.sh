#!/usr/bin/env bash
# Remote access from another network: the `tailscale` compose service, a Tailscale node on the host network (ADR-009).
# Own compose project (bisg-tailscale), so `./bisg down` stops the sim but never cuts remote access. Usually called through ./bisg tailscale.
# docs/remote-access.md
#
#   tailscale.sh up              start it; not logged in yet (and in a terminal): runs the login below
#   tailscale.sh login [--qr]    browser login started from this terminal: prints a URL to open on any device (--qr: also a QR code
#                          for a phone) and waits until done. No auth keys by design (ADR-009): a stored key is a standing secret.
#   tailscale.sh status          tailnet state, this host's address, and what a remote machine can open
#   tailscale.sh ip              this host's tailnet IPv4 (empty if not up)
#   tailscale.sh logs [-f] | down | logout (forget the login; the next login asks again)
set -euo pipefail
. "$(dirname "$0")/_common.sh"

vcompose(){ docker compose -p bisg-tailscale -f "$COMPOSE_FILE" --profile tailscale "$@"; }
ts(){ docker exec "$TAILSCALE_NAME" tailscale "$@"; }
backend(){ ts status --json 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("BackendState",""))' 2>/dev/null || true; }
# --reset: `up` applies exactly these flags; TAILSCALE_EXTRA_ARGS (config/bisg.conf) adds more, e.g. --ssh
read -ra UP_ARGS <<<"up --reset --hostname=${TAILSCALE_HOSTNAME} --accept-dns=false ${TAILSCALE_EXTRA_ARGS:-}"

start(){
  [[ -e /dev/net/tun ]] || die "/dev/net/tun missing on the host (sudo modprobe tun)"
  container_running "$TAILSCALE_NAME" || { vcompose up -d tailscale >/dev/null; ok "$TAILSCALE_NAME started (Tailscale ${TAILSCALE_TAG})"; }
  local st=""; for _ in $(seq 1 30); do st="$(backend)"; [[ -n "$st" && "$st" != NoState ]] && break; sleep 1; done
}

reach(){
  local ip="$1"
  info "from any device on your tailnet"
  echo "  browser view   http://${ip}:${SIM_WEB_PORT}/        (./bisg up web)"
  echo "  WebRTC client  ${ip}                    (./bisg up webrtc, with SIM_VIEW_ADDR=tailscale in docker/.env)"
  echo "  ssh            ssh $(id -un)@${ip}         (or the MagicDNS name: ${TAILSCALE_HOSTNAME})"
  echo "  QGroundControl GCS_URL=udp://@<remote machine's tailnet IP>:14550 in docker/.env, then ./bisg mavros up"
  [[ "${SIM_VIEW_ADDR:-}" == tailscale ]] || echo "  note: SIM_VIEW_ADDR=${SIM_VIEW_ADDR:-<empty>}: set SIM_VIEW_ADDR=tailscale in docker/.env so WebRTC advertises this address"
}
connected(){ local ip; ip="$(tailscale_ip)"; ok "on the tailnet: ${ip}  (${TAILSCALE_HOSTNAME})"; reach "$ip"; }

login(){
  local qr=()
  while [[ $# -gt 0 ]]; do case "$1" in --qr) qr=(--qr);; *) die "tailscale login: [--qr]";; esac; shift; done
  [[ -t 0 && -t 1 ]] || die "the login is interactive: run ./bisg tailscale login in a terminal"
  start
  info "log '${TAILSCALE_HOSTNAME}' into your tailnet: open the URL below in a browser on ANY device (a phone is fine). Waits until you finish; Ctrl+C to stop"
  docker exec -it "$TAILSCALE_NAME" tailscale "${UP_ARGS[@]}" "${qr[@]}"
  [[ "$(backend)" == Running ]] || die "not connected (state: $(backend)); ./bisg tailscale logs"
  connected
}

case "${1:-status}" in
  up)
    start
    if [[ "$(backend)" == Running ]]; then connected
    elif [[ -t 0 && -t 1 ]]; then login
    else warn "running, not logged in: run ./bisg tailscale login in a terminal"; fi;;
  login) shift; login "$@";;
  status)
    container_running "$TAILSCALE_NAME" || { warn "tailscale not running: ./bisg tailscale up"; exit 1; }
    st="$(backend)"; [[ "$st" == Running ]] && ok "connected" || warn "state: ${st:-unknown} (./bisg tailscale login)"
    ts status 2>/dev/null | sed 's/^/  /' || true
    [[ "$st" == Running ]] && reach "$(tailscale_ip)";;
  ip) tailscale_ip;;
  logs) shift; docker logs ${1:-} "$TAILSCALE_NAME";;
  down) vcompose down >/dev/null 2>&1 || true; ok "tailscale stopped (login kept; ./bisg tailscale up reconnects)";;
  logout) container_running "$TAILSCALE_NAME" && ts logout >/dev/null 2>&1 || true
          vcompose down -v >/dev/null 2>&1 || true; ok "tailscale stopped and login removed";;
  *) die "tailscale: up | login [--qr] | status | ip | logs [-f] | down | logout";;
esac
