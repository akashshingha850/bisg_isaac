#!/usr/bin/env bash
# Remote access from another network: the `vpn` compose service, a Tailscale node on the host network (ADR-009).
# Own compose project (bisg-vpn), so `./bisg down` stops the sim but never cuts remote access. Usually called through ./bisg vpn.
# docs/remote-access.md
#
#   vpn.sh up        start it; first time without TS_AUTHKEY: prints the login URL and waits for you to open it
#   vpn.sh status    tailnet state, this host's address, and what a remote machine can open
#   vpn.sh ip        this host's tailnet IPv4 (empty if not up)
#   vpn.sh logs [-f] | down | logout (down + forget the login, next `up` asks again)
set -euo pipefail
. "$(dirname "$0")/_common.sh"

vcompose(){ docker compose -p bisg-vpn -f "$COMPOSE_FILE" --profile vpn "$@"; }
ts(){ docker exec "$VPN_NAME" tailscale "$@"; }
backend(){ ts status --json 2>/dev/null | python3 -c 'import sys,json; print(json.load(sys.stdin).get("BackendState",""))' 2>/dev/null || true; }

reach(){
  local ip="$1"
  info "from any device on your tailnet"
  echo "  browser view   http://${ip}:${SIM_WEB_PORT}/        (./bisg up web)"
  echo "  WebRTC client  ${ip}                    (./bisg up webrtc, with SIM_VIEW_ADDR=vpn in docker/.env)"
  echo "  ssh            ssh $(id -un)@${ip}         (or the MagicDNS name: ${VPN_HOSTNAME})"
  echo "  QGroundControl GCS_URL=udp://@<remote machine's tailnet IP>:14550 in docker/.env, then ./bisg mavros up"
  [[ "${SIM_VIEW_ADDR:-}" == vpn ]] || echo "  note: SIM_VIEW_ADDR=${SIM_VIEW_ADDR:-<empty>} — set SIM_VIEW_ADDR=vpn in docker/.env so WebRTC advertises this address"
}

case "${1:-status}" in
  up)
    [[ -e /dev/net/tun ]] || die "/dev/net/tun missing on the host (sudo modprobe tun)"
    info "vpn: Tailscale ${TAILSCALE_TAG} as '${VPN_HOSTNAME}'"
    vcompose up -d vpn >/dev/null; ok "$VPN_NAME started"
    url=""; st=""
    for _ in $(seq 1 180); do
      st="$(backend)"
      [[ "$st" == Running ]] && break
      # the URL changes when tailscaled restarts after an unused one expires: always show the newest
      u=$(docker logs "$VPN_NAME" 2>&1 | grep -oE 'https://login\.tailscale\.com/[A-Za-z0-9/._-]+' | tail -1 || true)
      if [[ -n "$u" && "$u" != "$url" ]]; then
        [[ -z "$url" ]] && info "log this host into your tailnet — open in any browser (waiting up to 3 min; the login is kept in the vpn-state volume):"
        url="$u"; echo "  ${C_B}${url}${C_0}"
      fi
      sleep 1
    done
    [[ "$st" == Running ]] || die "not connected yet (state: ${st:-unknown}). The service keeps waiting: open the newest URL above (or ./bisg vpn up again), then ./bisg vpn status"
    ip="$(vpn_ip)"; ok "on the tailnet: ${ip}  (${VPN_HOSTNAME})"
    reach "$ip";;
  status)
    container_running "$VPN_NAME" || { warn "vpn not running: ./bisg vpn up"; exit 1; }
    st="$(backend)"; [[ "$st" == Running ]] && ok "connected" || warn "state: ${st:-unknown} (./bisg vpn up to log in)"
    ts status 2>/dev/null | sed 's/^/  /' || true
    ip="$(vpn_ip)"; [[ -n "$ip" ]] && reach "$ip";;
  ip) vpn_ip;;
  logs) shift; docker logs ${1:-} "$VPN_NAME";;
  down) vcompose down >/dev/null 2>&1 || true; ok "vpn stopped (login kept; ./bisg vpn up reconnects)";;
  logout) container_running "$VPN_NAME" && ts logout >/dev/null 2>&1 || true
          vcompose down -v >/dev/null 2>&1 || true; ok "vpn stopped and login removed";;
  *) die "vpn: up | status | ip | logs [-f] | down | logout";;
esac
