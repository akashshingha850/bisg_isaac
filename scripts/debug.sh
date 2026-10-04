#!/usr/bin/env bash
# Diagnostics for the sim stack. Usually called through ./bisg debug <cmd>.
#
#   debug.sh report                 collect host/container/PX4/ROS state into logs/debug_<ts>/ (+ .tar.gz)
#   debug.sh px4 <cmd...>           run a PX4 shell command in the running SITL (e.g. commander status, ekf2 status, param show EKF2_EV*)
#   debug.sh mavlink [PORT]         pymavlink heartbeat probe from the host (default 14550 GCS link)
#   debug.sh topics | hz TOPIC | echo TOPIC     ROS 2 graph via the ros container (starts it if needed)
#   debug.sh kitlog [-f]            Isaac Kit log of the current/last run (isaac-logs volume)
#   debug.sh perf                   real-time factor / step rate / VRAM + the active perf settings
#   debug.sh ports | gpu | versions | dds
#   debug.sh clean-cache            delete Isaac shader/compute cache volumes (next boot recompiles)
#   debug.sh clean-all              delete ALL bisg volumes incl. downloaded assets (asks)
set -euo pipefail
. "$(dirname "$0")/_common.sh"

usage(){ sed -n 2,12p "$0"; }
PX4BIN=/opt/PX4-Autopilot/build/px4_sitl_default/bin

need_sim(){ container_running "$SIM_NAME" || die "$SIM_NAME is not running (./bisg up)"; }
need_ros(){ container_running "$ROS_NAME" || compose --profile tools up -d ros >/dev/null; }

cmd_px4(){
  need_sim; [[ $# -gt 0 ]] || die "px4: give a command, e.g. commander status"
  local c=$1; shift
  # px4-<module> clients talk to the daemon socket of instance 0 (the SITL Pegasus autolaunched).
  docker exec -e PX4_INSTANCE=0 "$SIM_NAME" bash -c "cd /tmp && $PX4BIN/px4-$c $*" 2>&1 || warn "client failed — try: ./bisg shell then ls $PX4BIN | grep px4-"
}

cmd_mavlink(){
  local port="${1:-${MAVLINK_GCS_PORT:-14550}}"
  python3 - "$port" <<'PY'
import sys, time
from pymavlink import mavutil
port=int(sys.argv[1]); print(f"listening udpin:0.0.0.0:{port} (PX4 sends GCS traffic here; QGC must be closed for 14550)")
m=mavutil.mavlink_connection(f"udpin:0.0.0.0:{port}", source_system=251)
hb=m.wait_heartbeat(timeout=15)
if not hb: print("no heartbeat in 15 s"); sys.exit(1)
print(f"heartbeat: sysid={m.target_system} type={hb.type} autopilot={hb.autopilot} base_mode={hb.base_mode} custom_mode={hb.custom_mode} status={hb.system_status}")
t=time.time(); seen={}
while time.time()-t<5:
    msg=m.recv_match(blocking=True, timeout=1)
    if msg: seen[msg.get_type()]=seen.get(msg.get_type(),0)+1
print("msg types in 5 s:", ", ".join(f"{k}:{v}" for k,v in sorted(seen.items(), key=lambda x:-x[1])[:12]))
PY
}

cmd_topics(){ need_ros; ros_exec 'ros2 daemon stop >/dev/null 2>&1; timeout 30 ros2 topic list --no-daemon' ; }
cmd_hz(){ need_ros; ros_exec "timeout 20 ros2 topic hz --window 50 $1 2>&1 | grep -m1 -E 'average|no new'" ; }
cmd_echo(){ need_ros; ros_exec "timeout 30 ros2 topic echo --once $1" ; }

cmd_kitlog(){
  local f=""; [[ "${1:-}" == "-f" ]] && f=1
  # Text log: volume bisg_isaac-kit-logs = /isaac-sim/kit/logs -> Kit/Isaac-Sim Python/<ver>/kit_<ts>.log
  # (the .nvidia-omniverse/logs volume only holds structured telemetry json).
  # path contains a space ("Isaac-Sim Python"): let find hand the names to ls -t, never word-split them
  # Do not let `docker run -v` create the volume: compose must own it, or every later
  # `compose up` warns "volume ... was not created by Docker Compose".
  docker volume inspect bisg_isaac-kit-logs >/dev/null 2>&1 || die "volume bisg_isaac-kit-logs does not exist yet — start the sim once (./bisg up)"
  local latest; latest=$(docker run --rm -v bisg_isaac-kit-logs:/l:ro alpine sh -c 'find /l -name "kit_*.log" -exec ls -t {} + 2>/dev/null | head -1')
  [[ -n "$latest" ]] || die "no kit_*.log in volume bisg_isaac-kit-logs yet (first run after this volume was added?)"
  echo "kit log: $latest"
  if [[ -n $f ]]; then docker run --rm -it -v bisg_isaac-kit-logs:/l:ro alpine tail -f "$latest"; else docker run --rm -v bisg_isaac-kit-logs:/l:ro alpine sh -c "grep -E -i '\[error\]|\[fatal\]|pegasus|isaacsim.ros2' '$latest' | grep -v -E 'Sending (GPS|sensor) msgs' | tail -40; echo ---; tail -20 '$latest'"; fi
}

cmd_perf(){
  # The launcher prints "[launch] perf step N X steps/s rtf=Y" every app.heartbeat_steps steps.
  # rtf >= 1.0 means the sim keeps up with wall clock. See docs/performance.md.
  container_running "$SIM_NAME" || die "$SIM_NAME is not running (./bisg up)"
  local cfg; cfg=$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$SIM_NAME" | grep -m1 '^SIM_CONFIG=' | cut -d= -f2-)
  echo "config: ${cfg:-?}"
  local host="$ROOT${cfg#/workspace}"
  [[ -f "$host" ]] && { echo "perf block:"; sed -n '/^perf:/,/^[a-z]/p' "$host" | grep -E "^  [a-z_]+:" | grep -v ": *null" | sed 's/^/  /'; }
  echo "boot:"
  sim_ready && ok "reached 'sim ready'" || warn "not ready yet"
  echo "steady state (last 5 heartbeats):"
  docker logs "$SIM_NAME" 2>&1 | grep "perf step" | tail -5 | sed 's/.*\[launch\] INFO /  /' || warn "no perf lines yet (app.heartbeat_steps=0 disables them)"
  echo "gpu:"; nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader | sed 's/^/  /'
  echo "handbook: https://docs.isaacsim.omniverse.nvidia.com/6.0.0/reference_material/sim_performance_optimization_handbook.html"
}

cmd_ports(){
  echo "expected: tcp 4560+i (Pegasus<->PX4), udp 14580+i/14540+i (PX4<->MAVROS), udp 18570+i local + 14550 remote (GCS)"
  ss -ltnup 2>/dev/null | grep -E ":(456[0-9]|1454[0-9]|1458[0-9]|14550|1857[0-9]|1428[0-9]|1303[0-9]) " | awk '{print "  "$1, $5, $7}' | sort -u
  echo "listeners on 14540 other than PX4 block MAVROS/smoke (only one process can bind it)."
}
cmd_gpu(){ nvidia-smi; echo; echo "in sim container:"; container_running "$SIM_NAME" && docker exec "$SIM_NAME" nvidia-smi --query-gpu=name,memory.used --format=csv 2>/dev/null || echo "  (sim not running)"; }
cmd_versions(){
  echo "pins (config): ISAAC_TAG=$ISAAC_TAG PX4_TAG=$PX4_TAG PEGASUS_TAG=$PEGASUS_TAG ZED_SDK=$ZED_SDK"
  echo "images:"; docker images --format '{{.Repository}}:{{.Tag}}  {{.Size}}  {{.CreatedSince}}' | grep -E "^(bisg|nvcr.io/nvidia/isaac-sim|ros:jazzy)" | sed 's/^/  /' || true
  echo "sim image contents:"; docker run --rm --entrypoint bash "bisg/sim:${ISAAC_TAG}" -c 'echo "  isaac $(cat /isaac-sim/VERSION)"; cd /opt/PX4-Autopilot && echo "  px4 $(git describe --tags 2>/dev/null || cat build/px4_sitl_default/src/lib/version/build_git_version.h | grep -m1 -o "v[0-9.]*")"; echo "  pegasus $(/isaac-sim/python.sh -m pip show pegasus-simulator 2>/dev/null | grep ^Version | cut -d" " -f2)"; echo "  ros bridge: ROS_DISTRO=$ROS_DISTRO RMW=$RMW_IMPLEMENTATION"' 2>/dev/null
  echo "ros image:"; docker run --rm bisg/ros:jazzy bash -lc 'echo "  $(ros2 pkg xml mavros 2>/dev/null | grep -o "<version>[^<]*" | cut -d">" -f2 | sed "s/^/mavros /") jazzy rmw=$RMW_IMPLEMENTATION"' 2>/dev/null
  echo "host: driver $(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null), docker $(docker --version | awk '{print $3}' | tr -d ,), compose $(docker compose version --short), $(grep PRETTY /etc/os-release | cut -d'"' -f2)"
}
cmd_dds(){
  echo "ROS_DOMAIN_ID=$ROS_DOMAIN_ID  profile: $ROOT/docker/cyclonedds.xml"
  echo "host net.core.rmem_max=$(sysctl -n net.core.rmem_max) (>=10485760 recommended for point clouds)"
  for c in "$SIM_NAME" "$ROS_NAME" "bisg-mavros-${DRONE_ID}"; do container_running "$c" && echo "  $c: $(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$c" | grep -E '^(RMW_IMPLEMENTATION|ROS_DOMAIN_ID|CYCLONEDDS_URI)=' | tr '\n' ' ')"; done
  container_running "$ROS_NAME" && { ros_exec 'ros2 daemon stop >/dev/null 2>&1; ros2 daemon start >/dev/null 2>&1'; echo "  ros2 daemon restarted in $ROS_NAME"; } || true
}
cmd_clean_cache(){ compose "${ALL_PROFILES[@]}" down >/dev/null 2>&1 || true; docker volume rm bisg_isaac-cache-main bisg_isaac-cache-compute bisg_isaac-cache-kit 2>/dev/null && ok "shader/compute caches removed (next boot is slower)" || warn "nothing removed"; }
cmd_clean_all(){ read -r -p "Delete ALL bisg volumes (caches, downloaded assets, logs)? [y/N] " a; [[ $a == y ]] || exit 0; compose "${ALL_PROFILES[@]}" down -v --remove-orphans; ok "volumes removed"; }

cmd_report(){
  local ts; ts=$(date +%Y%m%d_%H%M%S); local d="$ROOT/logs/debug_${ts}"; mkdir -p "$d"
  info "collecting into $d"
  ( echo "date: $(date -Is)"; echo "repo: $ROOT"; cmd_versions ) > "$d/versions.txt" 2>&1 || true
  { nvidia-smi; echo; docker info 2>/dev/null | grep -E "Server Version|Runtimes|Default Runtime|Docker Root Dir|Operating System|Kernel"; echo; free -h; df -h "$ROOT" | tail -1; echo "DISPLAY=${DISPLAY:-} XDG_SESSION_TYPE=${XDG_SESSION_TYPE:-}"; xhost 2>/dev/null | head -3; } > "$d/host.txt" 2>&1
  docker ps -a --filter name=bisg- > "$d/containers.txt" 2>&1
  compose "${ALL_PROFILES[@]}" config > "$d/compose.resolved.yaml" 2>&1 || true
  sed 's/^\(.*TOKEN.*=\).*/\1<redacted>/' "$ENV_FILE" > "$d/env.txt" 2>/dev/null || true
  cp -r "$CONF_DIR" "$d/config" 2>/dev/null || true
  for c in "$SIM_NAME" "bisg-mavros-${DRONE_ID}" "$ROS_NAME"; do docker logs "$c" > "$d/$c.log" 2>&1 || true; done
  ( cmd_ports ) > "$d/ports.txt" 2>&1 || true
  ( cmd_dds ) > "$d/dds.txt" 2>&1 || true
  ( cmd_perf ) > "$d/perf.txt" 2>&1 || true
  ( cmd_kitlog ) > "$d/kitlog_summary.txt" 2>&1 || true
  docker volume inspect bisg_isaac-kit-logs >/dev/null 2>&1 && docker run --rm -v bisg_isaac-kit-logs:/l:ro alpine sh -c 'f=$(find /l -name "kit_*.log" -exec ls -t {} + 2>/dev/null | head -1); [ -n "$f" ] && cat "$f"' > "$d/kit_latest.log" 2>/dev/null || true
  if container_running "$SIM_NAME" && px4_ready; then
    ( for c in "commander status" "ekf2 status" "sensors status" "mavlink status" "uorb top -1" "param show MAV_* EKF2_EV* COM_RCL_EXCEPT"; do echo "### px4-$c"; cmd_px4 $c; echo; done ) > "$d/px4_status.txt" 2>&1 || true
  fi
  if container_running "$ROS_NAME"; then ( cmd_topics; echo; ros_exec "ros2 node list --no-daemon 2>/dev/null" ) > "$d/ros_graph.txt" 2>&1 || true; fi
  cp "$ROOT/docker/sim/configs/"*.yaml "$d/" 2>/dev/null || true
  tar -czf "$d.tar.gz" -C "$ROOT/logs" "debug_${ts}"
  ok "report: $d.tar.gz  ($(du -h "$d.tar.gz" | cut -f1))"
  echo "  quick look: $d/versions.txt, $d/${SIM_NAME}.log, $d/px4_status.txt, $d/kitlog_summary.txt"
}

case "${1:-}" in
  report) cmd_report;; px4) shift; cmd_px4 "$@";; mavlink) shift; cmd_mavlink "$@";; topics) cmd_topics;; hz) cmd_hz "$2";; echo) cmd_echo "$2";;
  kitlog) shift; cmd_kitlog "$@";; perf) cmd_perf;; ports) cmd_ports;; gpu) cmd_gpu;; versions) cmd_versions;; dds) cmd_dds;;
  clean-cache) cmd_clean_cache;; clean-all) cmd_clean_all;; -h|--help|help|"") usage;; *) die "unknown command: $1";;
esac
