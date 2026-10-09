#!/usr/bin/env bash
# Launch / operate the sim stack. Usually called through ./bisg.
#
#   launch.sh up [gui|headless|web|webrtc|both] [-c SCENARIO] [--attach] [--no-wait] [--no-bridge]
#                                      start the sim (view defaults to SIM_VIEW in config/bisg.conf)
#   launch.sh view [--addr IP]         how to watch the running sim (browser URL / WebRTC client)
#   launch.sh wait [TIMEOUT_S]         block until "[launch] sim ready" + PX4 "Ready for takeoff"
#   launch.sh config [--edit|--path]   show the resolved settings and where each came from
#   launch.sh status                   containers, ready markers, ports, GPU
#   launch.sh logs [sim|mavros|ros] [-f]
#   launch.sh shell [sim|ros]          interactive shell (sim: running container or a fresh one)
#   launch.sh smoke [--alt 2] [--timeout 300]   arm / takeoff / land test against SITL instance 0
#   launch.sh mavros up|down|logs|state|restart [--drone N]
#   launch.sh build [sim|ros|px4-bridge|zed|all] [--no-cache] [--force]   build the images (default: all) and the ZED Isaac extension
#   launch.sh ros up|down|shell|tools|enable N|disable N|start N|stop N|restart N   dev container + the GUI tools in docker/ros/tools.yaml (rviz, rqt, ...)
#   launch.sh zed plan|set|up|services|enable|status|logs|check|test|bench|down|build|image   the ZED Mini stack (scripts/zed.sh, docs/zed-stack.md)
#   launch.sh px4-bridge plan|up|down|status|logs|params|build [mavros|mavsdk|xrce|none]   the PX4 bridge(s), chosen by PX4_BRIDGE (scripts/px4-bridge.sh, docs/px4-bridge.md)
#   launch.sh drone up|down|status|logs|check|build   the real drone: MAVROS on the Pixracer + the ZED stack (scripts/drone.sh; Jetson or bench)
#   launch.sh all [gui|headless]       sim + mavros + ros, then wait
#   launch.sh stop | down | restart    stop keeps volumes; down removes containers (both keep caches)
set -euo pipefail
. "$(dirname "$0")/_common.sh"

usage(){ sed -n 2,21p "$0"; }

cmd_up(){
  local cfg="" attach=0 wait=1 win="" str="" bridge=1
  # A window word and a stream word are both accepted, in either order; each one replaces only
  # its half of SIM_VIEW, so `./bisg up headless` keeps the configured stream.
  while [[ $# -gt 0 ]]; do case "$1" in
    gui|headless|auto) win=$1;; web|webrtc|both) str=$1;; *+*) win=""; str=""; export SIM_VIEW=$1;;
    -c|--config) cfg=$2; shift;; --attach) attach=1;; --no-wait) wait=0;; --no-bridge) bridge=0;;
    --stream) str=webrtc;; --web) str=web;; --both) str=both;; --no-stream) str=off;;
    *) die "up: unknown arg $1";; esac; shift; done
  [[ "$BISG_ARCH" == x86_64 ]] || die "the sim (Isaac Sim) is x86_64 only; this is ${BISG_ARCH}. On the Jetson use ./bisg drone"
  view_parse                                       # validates SIM_VIEW -> VIEW_MODE / VIEW_STREAM
  [[ -n "$win" ]] && VIEW_MODE="$win"
  [[ -n "$str" ]] && VIEW_STREAM="$str"
  [[ "$VIEW_MODE" == auto ]] && { have_x11 && VIEW_MODE=gui || VIEW_MODE=headless; }
  local mode="$VIEW_MODE"
  # compose and the launcher still take the two derived values; SIM_VIEW never enters a container
  export SIM_VIEW="$(view_label)" SIM_STREAM="$VIEW_STREAM"
  # Service and profile names coincide: `sim` (GUI) / `sim-headless`. Name the service explicitly —
  # `compose --profile sim-headless up sim` would happily start the GUI service instead.
  local profile=sim; [[ $mode == headless ]] && profile=sim-headless
  if container_running "$SIM_NAME"; then warn "$SIM_NAME already running (./bisg status). Use restart."; return 0; fi
  gpu_preflight || exit 1
  # SIM_VIEW_ADDR=tailscale -> this host's tailnet IP (what WebRTC advertises); only matters when something is served
  if [[ "$VIEW_STREAM" != off ]]; then resolve_view_addr; elif [[ "${SIM_VIEW_ADDR:-}" == tailscale ]]; then export SIM_VIEW_ADDR=""; fi
  # scenario: -c flag > SIM_CONFIG exported in the shell > SIM_SCENARIO (config file) > compose default
  if [[ -n "$cfg" ]]; then export SIM_CONFIG="$(scenario_path "$cfg")"
  elif [[ "${BISG_SRC[SIM_CONFIG]:-}" != environment && -n "${SIM_SCENARIO:-}" ]]; then
    export SIM_CONFIG="$(scenario_path "$SIM_SCENARIO")"
  fi
  [[ $mode == gui ]] && { have_x11 || die "gui needs a reachable X server (DISPLAY=${DISPLAY:-unset}); use headless or set SIM_VIEW"; xhost +local: >/dev/null 2>&1 || true; }
  info "starting sim (view=$SIM_VIEW) config=${SIM_CONFIG:-default}"
  compose --profile "$profile" up -d --remove-orphans "$profile"
  ok "container $SIM_NAME started"
  # the PX4 bridge(s) PX4_BRIDGE names (MAVROS by default) come up with the sim; it reconnects until PX4 is ready
  [[ $bridge == 1 ]] && "$(dirname "$0")/px4-bridge.sh" up
  if [[ $attach == 1 ]]; then exec docker logs -f "$SIM_NAME"; fi
  [[ $wait == 1 ]] && cmd_wait "$SIM_WAIT_TIMEOUT"
  view_on && cmd_view
  echo "  follow logs: ./bisg logs -f     stop: ./bisg down"
}

# ZED_AUTOSTART=1: once the sim streams the ZED twin, start the wrapper (+ the services zed.yaml enables) in the background.
# The wrapper connects once per sim run (B18) and must start after the stream is live, so this runs from cmd_wait, not from cmd_up.
zed_autostart(){
  [[ "${ZED_AUTOSTART:-1}" == 1 ]] || return 0
  local log; log=$(docker logs "$SIM_NAME" 2>&1)
  [[ "$log" == *"ZED SDK twin attached"* ]] || return 0                                  # the scenario has no ZED
  container_running "bisg-zed-${DRONE_ID}" && return 0
  # "sim ready" comes before the streamer opens its UDP port: a wrapper that gets there first takes the port and the sim's
  # streamer then fails ("failed to create RTP Session"), leaving no ZED topics. Wait until the sim itself holds the port.
  local port=$(( 30000 + 2 * (DRONE_ID - 1) )) w=0
  until ss -uan 2>/dev/null | grep -q ":${port}\b"; do
    docker logs "$SIM_NAME" 2>&1 | grep -q "Streamer initialization failed" && { warn "the sim's ZED streamer failed: restart the sim (./bisg restart)"; return 0; }
    (( w >= 90 )) && { warn "ZED stream port ${port} not open after ${w}s; start the wrapper later: ./bisg zed up"; return 0; }
    sleep 2; w=$(( w + 2 ))
  done
  info "starting the ZED wrapper (ZED_AUTOSTART=1; first start optimises the depth model, ~6 min)"
  "$(dirname "$0")/zed.sh" up -d >/dev/null 2>&1 && ok "bisg-zed-${DRONE_ID} started in the background (./bisg zed status)" \
    || warn "ZED wrapper did not start: ./bisg zed up"
}

cmd_wait(){
  local timeout="${1:-${SIM_WAIT_TIMEOUT:-600}}" t0=$(date +%s) shown_ready=0
  container_running "$SIM_NAME" || die "$SIM_NAME is not running (./bisg up)"
  info "waiting for sim ready + PX4 ready (timeout ${timeout}s; warm boot ~1 min, first boot ~3 min)"
  while true; do
    local el=$(( $(date +%s) - t0 ))
    if sim_failed; then fail "launcher error after ${el}s:"; docker logs "$SIM_NAME" 2>&1 | grep -E -A3 "Traceback|Failed to create any GPU" | tail -12; return 1; fi
    if ! container_running "$SIM_NAME"; then fail "container exited (code $(docker inspect -f '{{.State.ExitCode}}' "$SIM_NAME")) — ./bisg logs"; return 1; fi
    if [[ $shown_ready == 0 ]] && sim_ready; then ok "[launch] sim ready after ${el}s"; shown_ready=1; zed_autostart; ros_tools_autostart; fi
    if px4_ready; then ok "PX4 'Ready for takeoff' after ${el}s"; return 0; fi
    (( el > timeout )) && { fail "timeout after ${el}s (last lines below)"; docker logs --tail 5 "$SIM_NAME" 2>&1 | cut -c1-140; return 1; }
    sleep 3
  done
}

cmd_status(){
  info "containers"; docker ps -a --filter name=bisg- --format '  {{.Names}}\t{{.Status}}\t{{.Image}}' || true
  if container_running "$SIM_NAME"; then
    sim_ready && ok "sim ready" || warn "sim booting (no 'sim ready' yet)"
    px4_ready && ok "PX4 ready for takeoff" || warn "PX4 not ready"
    local m; m=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$SIM_NAME" | grep -E "^SIM_(CONFIG|HEADLESS|STREAM)=" | tr '\n' ' '); echo "  $m"
    local sv; sv=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$SIM_NAME" | grep -m1 '^SIM_STREAM=' | cut -d= -f2-)
    if [[ "$sv" =~ ^(web|browser|both)$ ]]; then
      _sim_log_has "web view ready" && ok "browser view: http://$(stream_addr):${SIM_WEB_PORT}/ (./bisg view)" || warn "browser view requested, not serving yet"
    fi
    if [[ "$sv" =~ ^(webrtc|on|true|1|yes|both)$ ]]; then
      _sim_log_has "livestream webrtc ready" && ok "livestream up — WebRTC client -> $(stream_addr) (./bisg view)" || warn "livestream requested, not ready yet"
    fi
  fi
  info "ports (4560 sim link, 14540/14580 offboard, 14550 GCS, 18570 PX4 GCS local)"
  ss -ltnup 2>/dev/null | grep -E ":(456[0-9]|1454[0-9]|1458[0-9]|14550|1857[0-9]) " | awk '{print "  "$1, $5, $7}' | sort -u | head -12 || true
  # container processes are visible from the host PID namespace; only a px4 OUTSIDE docker is a leak
  local stray=0 inside=0; for p in $(pgrep -x px4 2>/dev/null); do grep -q -E "docker|containerd" /proc/$p/cgroup 2>/dev/null && inside=$((inside+1)) || stray=$((stray+1)); done
  echo "  px4 SITL processes: $inside in containers$( (( stray > 0 )) && echo ", ${C_Y}$stray stray on host (pkill -x px4)${C_0}")"
  info "gpu"; nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null | sed 's/^/  /' || true
}

cmd_logs(){
  local svc=sim follow=""
  for a in "$@"; do case "$a" in sim|mavros|ros) svc=$a;; -f|--follow) follow=-f;; *) die "logs: unknown arg $a";; esac; done
  local name; case $svc in sim) name=$SIM_NAME;; mavros) name="bisg-mavros-${DRONE_ID}";; ros) name=$ROS_NAME;; esac
  exec docker logs $follow --tail 200 "$name"
}

cmd_shell(){
  case "${1:-sim}" in
    sim) if container_running "$SIM_NAME"; then exec docker exec -it "$SIM_NAME" bash; else info "no running sim; opening a fresh sim container shell"; exec compose run --rm sim shell; fi;;
    ros) container_running "$ROS_NAME" || compose --profile tools up -d ros >/dev/null; exec docker exec -it "$ROS_NAME" bash;;
    *) die "shell: sim|ros";; esac
}

cmd_smoke(){
  container_running "$SIM_NAME" || die "sim not running"
  px4_ready || { warn "PX4 not ready yet — waiting"; cmd_wait "$SIM_WAIT_TIMEOUT"; }
  info "smoke test: arm → takeoff → land (SITL instance 0)"
  if python3 -c "import pymavlink" 2>/dev/null; then python3 "$ROOT/tests/smoke_takeoff.py" "$@"
  else docker exec "$SIM_NAME" /isaac-sim/python.sh /workspace/tests/smoke_takeoff.py "$@"; fi
}

cmd_mavros(){
  local sub="${1:-state}"; shift || true
  while [[ $# -gt 0 ]]; do case "$1" in --drone) export DRONE_ID=$2; shift;; *) die "mavros: unknown arg $1";; esac; shift; done
  local name="bisg-mavros-${DRONE_ID}"
  case $sub in
    up) info "MAVROS for drone ${DRONE_ID} (ns /drone_${DRONE_ID}, fcu ${FCU_URL:-udp instance $((DRONE_ID-1))})"; "$(dirname "$0")/px4-bridge.sh" up mavros; compose --profile tools up -d ros >/dev/null;;
    down) "$(dirname "$0")/px4-bridge.sh" down mavros;;
    restart) docker restart "$name";;
    logs) exec docker logs -f --tail 100 "$name";;
    state) container_running "$ROS_NAME" || compose --profile tools up -d ros >/dev/null
           ros_exec "ros2 daemon stop >/dev/null 2>&1; timeout 30 ros2 topic echo --no-daemon /drone_${DRONE_ID}/mavros/state --once 2>/dev/null | grep -E '^(connected|armed|guided|mode|system_status)'" || fail "no state from /drone_${DRONE_ID}/mavros/state (is the sim + PX4 up? ./bisg status)";;
    *) die "mavros: up|down|restart|logs|state [--drone N]";; esac
}

cmd_build(){
  local nc=() force=() targets=()
  for a in "$@"; do case "$a" in --no-cache) nc=(--no-cache);; --force) force=(--force);; sim|ros|px4-bridge|zed|all) targets+=("$a");; *) die "build: [sim|ros|px4-bridge|zed|all] [--no-cache] [--force]";; esac; done
  if [[ ${#targets[@]} -eq 0 || " ${targets[*]} " == *" all "* ]]; then
    targets=(ros px4-bridge); [[ "$BISG_ARCH" == x86_64 ]] && targets=(sim ros px4-bridge zed)
  fi
  local z="$(dirname "$0")/zed.sh"
  for t in "${targets[@]}"; do case $t in
    sim) info "building bisg/sim:${ISAAC_TAG}"; compose build "${nc[@]}" sim;;
    ros) info "building bisg/ros:jazzy"; compose --profile ros build "${nc[@]}" ros;;
    px4-bridge) info "building bisg/px4-bridge:jazzy (the agent compile takes ~10 min the first time)"; compose --profile px4-bridge build "${nc[@]}" px4-bridge;;
    zed) "$z" image "${force[@]}" && "$z" build "${force[@]}";;     # bisg/zed image + the Stereolabs Isaac extension; each skips if its sources are unchanged
  esac; done
  ok "build done: ${targets[*]}"
}

# ROS 2 tools from docker/ros/tools.yaml, detached in bisg-ros on the host display. Extra args replace the yaml ones.
ros_tool_start(){
  local name=$1; shift || true; [[ -n "$name" ]] || die "ros start NAME  (./bisg ros tools lists them)"
  local tp="$ROOT/scripts/ros_tools.py" exe line
  exe=$("$tp" exe "$name") || exit 1; line=$("$tp" cmd "$name" "$@")
  container_running "$ROS_NAME" || compose --profile tools up -d ros >/dev/null
  if [[ $exe == rviz2 || $exe == rqt* ]] && ! docker exec "$ROS_NAME" bash -c "source /opt/ros/jazzy/setup.bash; command -v $exe" >/dev/null 2>&1; then
    info "$exe is not in the bisg/ros image yet: rebuilding it (one time, a few minutes)"
    compose --profile tools build ros && compose --profile tools up -d --force-recreate ros >/dev/null || die "ros image build failed"
  fi
  if docker exec "$ROS_NAME" bash -c "kill -0 \$(cat /tmp/bisg-tool-$name.pid 2>/dev/null) 2>/dev/null"; then ok "$name is already running"; return 0; fi
  command -v xhost >/dev/null && xhost +local: >/dev/null 2>&1 || true   # let the container draw on the host display
  docker exec -d -e DISPLAY="${DISPLAY:-:0}" "$ROS_NAME" bash -c "source /opt/ros/jazzy/setup.bash; echo \$\$ >/tmp/bisg-tool-$name.pid; exec $line >/tmp/$name.log 2>&1"
  ok "$name started in the background (log: docker exec $ROS_NAME cat /tmp/$name.log; stop: ./bisg ros stop $name)"
}
ros_tool_stop(){
  [[ -n "${1:-}" ]] || die "ros stop NAME"
  # kill, then wait for the process to be gone (a restart right after must not see the old pid)
  docker exec "$ROS_NAME" bash -c "p=\$(cat /tmp/bisg-tool-$1.pid 2>/dev/null); kill -0 \$p 2>/dev/null || exit 1; kill \$p; for i in 1 2 3 4 5 6 7 8 9 10; do kill -0 \$p 2>/dev/null || exit 0; sleep 0.5; done; kill -9 \$p" \
    && ok "$1 stopped" || info "$1 is not running"
}
# ROS_TOOLS_AUTOSTART=1: the tools enabled in docker/ros/tools.yaml start when the sim is ready (display tools need a desktop).
ros_tools_autostart(){
  [[ "${ROS_TOOLS_AUTOSTART:-1}" == 1 ]] || return 0
  local n; for n in $("$ROOT/scripts/ros_tools.py" enabled); do ros_tool_start "$n" || warn "ros tool $n did not start"; done
}

cmd_ros(){
  case "${1:-shell}" in
    up) compose --profile tools up -d ros; ok "$ROS_NAME up";;
    down) compose --profile tools stop ros; compose --profile tools rm -f ros >/dev/null;;
    shell) cmd_shell ros;;
    tools|list) "$ROOT/scripts/ros_tools.py" list;;
    enable|disable) [[ -n "${2:-}" ]] || die "ros $1 NAME  (./bisg ros tools lists them)"
        "$ROOT/scripts/ros_tools.py" set "$2" "$([[ $1 == enable ]] && echo on || echo off)" && ok "$2 ${1}d in docker/ros/tools.yaml";;
    start) shift; ros_tool_start "${1:-}" "${@:2}";;
    stop) shift; ros_tool_stop "${1:-}";;
    restart) shift; ros_tool_stop "${1:-}" || true; ros_tool_start "${1:-}" "${@:2}";;
    rviz|rqt) local n=$1; shift
        case "${1:-}" in start) ros_tool_start "$n" "${@:2}";; stop) ros_tool_stop "$n";; restart) ros_tool_stop "$n" || true; ros_tool_start "$n" "${@:2}";; *) ros_tool_start "$n" "$@";; esac;;   # shortcuts
    build) compose --profile tools run --rm ros build;;
    *) die "ros: up|down|shell|tools|enable|disable|start|stop|restart|build";; esac
}

# How to watch a run. Two very different transports (docs/remote-access.md):
#   web    one TCP port serving still frames  -> survives a VS Code / SSH port forward
#   webrtc TCP 49100 + UDP 47998, interactive -> needs real UDP (LAN or Tailscale), not a tunnel
cmd_view(){
  while [[ $# -gt 0 ]]; do case "$1" in --addr) export SIM_VIEW_ADDR=$2; shift;; *) die "view: --addr IP";; esac; shift; done
  local addr; addr="$(stream_addr)" running=0 mode=""
  if container_running "$SIM_NAME"; then
    running=1
    mode=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$SIM_NAME" | grep -m1 '^SIM_STREAM=' | cut -d= -f2-)
    [[ -n "$mode" && "$mode" != "off" ]] || warn "the running sim was started without a view: ./bisg restart --web (or --stream)"
  else
    warn "no sim running: ./bisg up web   (browser)   |   ./bisg up webrtc   (WebRTC client)"
    mode="$(sim_stream)"
  fi
  # Nothing enabled yet: still explain both routes — that is what this command is for.
  [[ "$mode" =~ ^(off|)$ ]] && mode=both

  if [[ "$mode" =~ ^(web|browser|both)$ ]]; then
    info "browser view (TCP ${SIM_WEB_PORT}, still frames every ${SIM_WEB_INTERVAL}s)"
    if [[ $running == 1 ]]; then
      _sim_log_has "web view ready" && ok "serving" || warn "not up yet — the page appears once the world has loaded"
    fi
    echo "  local:      http://127.0.0.1:${SIM_WEB_PORT}/"
    echo "  LAN:        http://${addr}:${SIM_WEB_PORT}/"
    echo "  VS Code:    Ports panel -> Forward a Port -> ${SIM_WEB_PORT}, then Ctrl+Shift+P 'Simple Browser: Show' -> http://localhost:${SIM_WEB_PORT}/"
    echo "  SSH:        ssh -L ${SIM_WEB_PORT}:127.0.0.1:${SIM_WEB_PORT} <this-host>"
  fi

  if [[ "$mode" =~ ^(webrtc|on|true|1|yes|both)$ ]]; then
    info "WebRTC livestream (interactive)"
    if [[ $running == 1 ]]; then
      _sim_log_has "livestream webrtc ready" && ok "serving" || warn "not up yet"
    fi
    echo "  1. install the Isaac Sim WebRTC Streaming Client (NVIDIA download; the viewing machine needs no GPU)"
    echo "  2. connect it to:  ${C_B}${addr}${C_0}     (same machine: 127.0.0.1)"
    echo "  3. needs TCP ${STREAM_SIGNAL_PORT} + UDP ${STREAM_MEDIA_PORT} — UDP will not pass a VS Code/SSH tunnel; use a Tailscale or the browser view"
    [[ -z "${SIM_VIEW_ADDR:-}" ]] && echo "  remote clients also need SIM_VIEW_ADDR=${addr} in docker/.env (it is what the server advertises); another network: SIM_VIEW_ADDR=tailscale + ./bisg tailscale up"
  fi

  ss -ltnup 2>/dev/null | grep -E ":(${STREAM_SIGNAL_PORT}|${STREAM_MEDIA_PORT}|${SIM_WEB_PORT}) " | awk '{print "  listening: "$1, $5}' | sort -u || true
  echo "  docs: docs/remote-access.md"
}

# Print every setting with its origin (environment / docker/.env / config/<file>.conf / built-in).
cmd_config(){
  local files; mapfile -t files < <(conf_files)
  case "${1:-}" in
    --path) printf '%s\n' "${files[@]}"; return 0;;
    --edit) exec "${EDITOR:-${VISUAL:-nano}}" "${files[@]}";;
    "") ;;
    *) die "config: --edit | --path";;
  esac
  info "settings"
  local f; for f in "${files[@]}"; do printf '  %-22s %s\n' "${f#$ROOT/}" "$(sed -n '1s/^# *//p' "$f")"; done
  echo "  machine override : ${ENV_FILE#$ROOT/}$( [[ -f "$ENV_FILE" ]] || echo '   (missing)')"
  local k v
  show(){ info "$1"; shift; for k in "$@"; do v="${!k:-}"; printf '  %-18s %-46s %s\n' "$k" "${v:-<empty>}" "${BISG_SRC[$k]:-unset}"; done; }
  show "view"       SIM_VIEW SIM_VIEW_ADDR SIM_WEB_PORT SIM_WEB_INTERVAL DISPLAY
  show "remote"     TAILSCALE_HOSTNAME TAILSCALE_EXTRA_ARGS
  show "sim"        SIM_SCENARIO SIM_WAIT_TIMEOUT
  show "ros 2"      ROS_DOMAIN_ID
  show "endpoints"  DRONE_ID FCU_URL GCS_URL MAVLINK_GCS_PORT
  show "px4 bridge" PX4_BRIDGE MAVROS_PLUGINS MAVSDK_PORT XRCE_PORT XRCE_BAUD
  show "pins"       ISAAC_TAG PX4_TAG PEGASUS_TAG ZED_SDK ZED_ISAAC_EXT_TAG TAILSCALE_TAG ISAAC_IMAGE ROS_BASE_IMAGE
  show "links"      PEGASUS_REPO ZED_WRAPPER_REPO ZED_ISAAC_EXT_REPO PX4_REPO ARCHIVE_DIR
  info "resolved for the next ./bisg up"
  view_parse
  echo "  view      $(view_label)$( [[ "${SIM_VIEW}" == auto ]] && { have_x11 && echo "   (auto: X server on $DISPLAY)" || echo "   (auto: no X server)"; } )"
  echo "  scenario  $( [[ -n "${SIM_SCENARIO:-}" ]] && scenario_path "$SIM_SCENARIO" || echo "${SIM_CONFIG:-/workspace/docker/sim/configs/single_iris.yaml}" )"
  echo "  fcu_url   ${FCU_URL:-udp://:$((14540 + DRONE_ID - 1))@127.0.0.1:$((14580 + DRONE_ID - 1))  (derived from DRONE_ID)}"
  local _v=""
  [[ "$VIEW_STREAM" =~ ^(web|both)$ ]]    && _v="http://$(stream_addr):${SIM_WEB_PORT}/"
  [[ "$VIEW_STREAM" =~ ^(webrtc|both)$ ]] && _v="${_v:+$_v + }webrtc client -> $(stream_addr):${STREAM_SIGNAL_PORT}"
  echo "  watch at  ${_v:-nothing served (./bisg up web | webrtc)}  (./bisg view)"
  echo "  edit: ./bisg config --edit   (machine-only values: ${ENV_FILE#$ROOT/})"
}

cmd_all(){
  cmd_up "${1:-headless}" --no-wait                    # starts the bridge(s) PX4_BRIDGE names (MAVROS by default) too
  compose --profile ros up -d ros >/dev/null; ok "ros started"   # odometry comes from the ZED SDK (./bisg zed up)
  cmd_wait "$SIM_WAIT_TIMEOUT"
  if [[ ",$PX4_BRIDGE," == *,mavros,* ]]; then cmd_mavros state; else "$(dirname "$0")/px4-bridge.sh" status; fi
}
cmd_stop(){ info "stopping"; compose "${ALL_PROFILES[@]}" stop; docker stop $(docker ps -q --filter 'name=^bisg-(mavros|mavsdk|xrce)-[0-9]+$') >/dev/null 2>&1 || true; }
cmd_down(){ info "removing containers (caches kept)"; compose "${ALL_PROFILES[@]}" down --remove-orphans; "$(dirname "$0")/px4-bridge.sh" down --all >/dev/null; }
cmd_restart(){ local m=""; container_running "$SIM_NAME" && { docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$SIM_NAME" | grep -q "SIM_HEADLESS=1" && m=headless || m=gui; }; cmd_down; cmd_up ${m:-} "$@"; }

case "${1:-}" in
  up) shift; cmd_up "$@";; wait) shift; cmd_wait "$@";; status) cmd_status;; logs) shift; cmd_logs "$@";;
  build) shift; cmd_build "$@";; shell) shift; cmd_shell "$@";; smoke) shift; cmd_smoke "$@";; mavros) shift; cmd_mavros "$@";; ros) shift; cmd_ros "$@";; rviz|rqt) cmd_ros "$@";;
  config) shift; cmd_config "$@";;
  zed) shift; exec "$(dirname "$0")/zed.sh" "$@";;
  drone) shift; exec "$(dirname "$0")/drone.sh" "$@";;
  px4-bridge) shift; exec "$(dirname "$0")/px4-bridge.sh" "$@";;
  view|stream) shift; cmd_view "$@";;
  all) shift; cmd_all "$@";; stop) cmd_stop;; down) cmd_down;; restart) shift; cmd_restart "$@";;
  -h|--help|help|"") usage;; *) die "unknown command: $1";;
esac
