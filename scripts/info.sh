#!/usr/bin/env bash
# Every way into this host on one screen: addresses, sim view (browser / WebRTC), Foxglove, QGroundControl (MAVLink + ZED video), ssh,
# each with its live state (from the listening ports and containers) and the link per address: this machine, LAN, tailnet.
# Read-only, starts nothing. Usually called through ./bisg info.   Details: ./bisg view, ./bisg tailscale status, docs/remote-access.md
set -euo pipefail
. "$(dirname "$0")/_common.sh"

listening(){ [[ -n "$(ss -H -l"${2:-t}"n "sport = :$1" 2>/dev/null)" ]]; }   # listening PORT [t|u]
state(){ if "$@"; then printf '%s' "${C_G}up  ${C_0}"; else printf '%s' "${C_Y}off ${C_0}"; fi; }
row(){ printf '  %-14s %s %s\n' "$1" "$2" "$3"; }          # row LABEL STATE TEXT
sub(){ printf '  %-14s      %s\n' "" "$1"; }                # continuation line
ts_json(){
  if host_tailscale; then tailscale status --json 2>/dev/null || true
  else container_running "$TAILSCALE_NAME" && docker exec "$TAILSCALE_NAME" tailscale status --json 2>/dev/null || true; fi
}

LAN="$(lan_ip)"; TS_IP="$(tailscale_ip)"
TS_DNS="$(ts_json | python3 -c 'import sys,json; print(json.load(sys.stdin).get("Self",{}).get("DNSName","").rstrip("."))' 2>/dev/null || true)"
# hosts a viewer can use: label=address
HOSTS=("local=localhost"); [[ -n "$LAN" ]] && HOSTS+=("LAN=$LAN"); [[ -n "$TS_IP" ]] && HOSTS+=("tailnet=$TS_IP")
each(){ local h; for h in "${HOSTS[@]}"; do sub "$(printf '%-8s %s' "${h%%=*}" "$("$@" "${h#*=}")")"; done; }

info "bisg info: $(hostname -s)  (${BISG_ARCH}, drone ${DRONE_ID})"
row "LAN" "    " "${LAN:-<none>}"
if [[ -n "$TS_IP" ]]; then
  row "Tailscale" "$(state true)" "${TS_IP}${TS_DNS:+  ${TS_DNS}}  ($(host_tailscale && echo "host's daemon" || echo "container ${TAILSCALE_NAME}"))"
else
  row "Tailscale" "$(state false)" "not connected: ./bisg tailscale up   (needed to reach this host from another network)"
fi
up="$(docker ps --filter name=bisg- --format '{{.Names}}' 2>/dev/null | sed 's/^bisg-//' | sort | tr '\n' ' ')"
row "containers" "    " "${up:-none running}"

info "sim view"
if container_running "$SIM_NAME"; then
  env_of(){ docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$SIM_NAME" | grep -m1 "^$1=" | cut -d= -f2- || true; }
  row "sim" "$(state true)" "$( [[ "$(env_of SIM_HEADLESS)" == 1 ]] && echo headless || echo "gui window" ), stream: $(env_of SIM_STREAM | sed 's/^$/off/')"
else
  row "sim" "$(state false)" "not running: ./bisg up   (SIM_VIEW=${SIM_VIEW})"
fi
row "browser view" "$(state listening "$SIM_WEB_PORT")" "still frames on TCP ${SIM_WEB_PORT} (./bisg up web; survives a VS Code/SSH port forward)"
web_url(){ echo "http://$1:${SIM_WEB_PORT}/"; }
each web_url
row "WebRTC" "$(state listening "$STREAM_SIGNAL_PORT")" "Isaac Sim WebRTC Streaming Client -> $(stream_addr)   (./bisg up webrtc; TCP ${STREAM_SIGNAL_PORT} + UDP ${STREAM_MEDIA_PORT}: LAN or tailnet, no tunnel)"
[[ -z "${SIM_VIEW_ADDR:-}" ]] && sub "remote clients: set SIM_VIEW_ADDR (LAN IP, or tailscale) in docker/.env: it is the address the server advertises"

info "Foxglove (bridge ws :${FOXGLOVE_BRIDGE_PORT} in ${ROS_NAME}, web UI :${FOXGLOVE_UI_PORT} = lichtblick; ./bisg ros start foxglove)"
row "bridge" "$(state listening "$FOXGLOVE_BRIDGE_PORT")" "ws://<address>:${FOXGLOVE_BRIDGE_PORT}   (also for the Foxglove desktop app)"
row "web UI" "$(state container_running bisg-lichtblick)" "VS Code: 'Simple Browser: Show'; over a VS Code tunnel / Remote-SSH forward port ${FOXGLOVE_UI_PORT} in the Ports panel (only that one; bridge proxied at /ws)"
each foxglove_url

info "QGroundControl"
row "MAVLink" "$(state container_running "bisg-mavros-${DRONE_ID}")" "PX4 -> UDP ${MAVLINK_GCS_PORT} on this host (QGC here connects by itself)"
sub "remote QGC: GCS_URL=udp://@<its LAN/tailnet IP>:${MAVLINK_GCS_PORT} in docker/.env, then ./bisg mavros up   (now: GCS_URL=${GCS_URL:-<empty>})"
video="$(python3 -c 'import sys,yaml; v=(yaml.safe_load(open(sys.argv[1])) or {}).get("services",{}).get("qgc_video",{}); print(v.get("enabled",False), v.get("host",""), v.get("port",""))' "$ROOT/docker/zed/zed.yaml" 2>/dev/null || echo "False ? ?")"
read -r v_on v_host v_port <<<"$video"
row "ZED video" "$(state container_running "bisg-zed-video-${DRONE_ID}")" "H.264 RTP -> udp://${v_host}:${v_port}  (QGC: Video source UDP h.264, port ${v_port}; enabled in zed.yaml: ${v_on,,})"
sub "remote QGC: services.qgc_video.host = its IP (docker/zed/zed.yaml) or ./bisg zed video --video-host <IP>"

info "shell"
if listening 22; then row "ssh" "$(state true)" "ssh $(id -un)@${TS_DNS:-${TS_IP:-${LAN:-<host>}}}"
else row "ssh" "$(state false)" "no ssh server on port 22 (sudo apt install openssh-server; or Tailscale SSH: TAILSCALE_EXTRA_ARGS=--ssh)"; fi
