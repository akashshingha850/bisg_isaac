#!/usr/bin/env bash
# Shared helpers for bisg scripts. Source, do not execute.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="${COMPOSE_FILE:-$ROOT/docker/compose.yaml}"
ENV_FILE="$ROOT/docker/.env"
SIM_NAME=bisg-sim
ROS_NAME=bisg-ros
ALL_PROFILES=(--profile sim --profile sim-headless --profile ros --profile tools --profile zed --profile drone --profile px4-bridge)

# --- output -------------------------------------------------------------------
if [[ -t 1 ]]; then C_G=$'\e[32m'; C_Y=$'\e[33m'; C_R=$'\e[31m'; C_B=$'\e[1m'; C_0=$'\e[0m'; else C_G=; C_Y=; C_R=; C_B=; C_0=; fi
info(){ echo "${C_B}==>${C_0} $*"; }
ok(){ echo "  ${C_G}[ok]${C_0}   $*"; }
# warn/fail go to stderr: they must not land in a "$(...)" capture (e.g. scenario_path).
warn(){ echo "  ${C_Y}[warn]${C_0} $*" >&2; }
fail(){ echo "  ${C_R}[FAIL]${C_0} $*" >&2; }
die(){ fail "$*"; exit 1; }

# --- configuration ------------------------------------------------------------
# Layered, first writer wins: shell environment > docker/.env (per machine) >
# config/bisg.conf (project defaults) > the built-ins below.
# `./bisg config` shows the result and the origin of every key.
CONF_DIR="${BISG_CONF_DIR:-$ROOT/config}"
conf_files(){ local f; for f in "$CONF_DIR"/*.conf; do [[ -e "$f" ]] && echo "$f"; done; }

declare -A BISG_SRC=()          # key -> where the value came from
declare -A _BISG_ENV0=()        # keys that were already in the environment
while IFS='=' read -r _k _; do [[ -n "$_k" ]] && _BISG_ENV0[$_k]=1; done < <(env)

# Read KEY=VALUE lines; never overwrite a key that already has a value.
load_conf(){
  local file="$1" label="$2" line key val
  [[ -f "$file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%%#*}"                                     # values must not contain '#'
    [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=(.*)$ ]] || continue
    key="${BASH_REMATCH[1]}"; val="${BASH_REMATCH[2]}"
    val="${val#"${val%%[![:space:]]*}"}"; val="${val%"${val##*[![:space:]]}"}"
    [[ ${#val} -ge 2 && ${val:0:1} == '"' && ${val: -1} == '"' ]] && val="${val:1:${#val}-2}"
    [[ ${#val} -ge 2 && ${val:0:1} == "'" && ${val: -1} == "'" ]] && val="${val:1:${#val}-2}"
    if [[ -n "${!key:-}" ]]; then
      [[ -n "${BISG_SRC[$key]:-}" ]] || BISG_SRC[$key]="$([[ -n "${_BISG_ENV0[$key]:-}" ]] && echo environment || echo "$label")"
      continue
    fi
    export "$key=$val"; BISG_SRC[$key]="$label"
  done < "$file"
}
conf_default(){ local k="$1"; [[ -n "${!k:-}" ]] && return 0; export "$k=$2"; BISG_SRC[$k]="built-in"; }

load_conf "$ENV_FILE" "docker/.env"
while read -r _f; do load_conf "$_f" "config/$(basename "$_f")"; done < <(conf_files)
# Fallbacks so the scripts still work with no config file at all; keep in sync with config/bisg.conf.
conf_default SIM_VIEW gui+webrtc;        conf_default SIM_SCENARIO single_iris;  conf_default SIM_WAIT_TIMEOUT 600
conf_default ZED_AUTOSTART 1;     conf_default ROS_TOOLS_AUTOSTART 1;     conf_default SIM_WEB_PORT 8899;    conf_default SIM_WEB_INTERVAL 1.0
conf_default ROS_DOMAIN_ID 0;      conf_default DRONE_ID 1;                conf_default MAVLINK_GCS_PORT 14550
conf_default ISAAC_TAG 6.0.0;      conf_default PX4_TAG v1.17.0;           conf_default PEGASUS_TAG pr144-fcb99c0
conf_default ZED_SDK 5.4.1;        conf_default ISAAC_IMAGE nvcr.io/nvidia/isaac-sim
conf_default ZED_ISAAC_EXT_TAG v5.2.1;  conf_default TAILSCALE_TAG v1.102.5
conf_default TAILSCALE_HOSTNAME "bisg-$(hostname -s 2>/dev/null || echo sim)"; conf_default TAILSCALE_EXTRA_ARGS ""
conf_default PX4_BRIDGE mavros
conf_default MAVROS_PLUGINS lean;  conf_default MAVSDK_PORT 50051;          conf_default XRCE_PORT 8888;  conf_default XRCE_BAUD 921600
conf_default ROS_BASE_IMAGE ros:jazzy-ros-base
# One compose file serves the x86_64 workstation and the arm64 Jetson; the only per-arch thing is the ZED image tag.
case "$(uname -m)" in
  aarch64|arm64) conf_default BISG_ARCH arm64;  conf_default ZED_VARIANT l4t-r38;;   # Jetson, JetPack 7 (docker/zed/build.sh jetson)
  *)             conf_default BISG_ARCH x86_64; conf_default ZED_VARIANT desktop;;    # workstation (docker/zed/build.sh desktop)
esac
conf_default ARCHIVE_DIR /media/ubuntu/ssd/docker-archive
conf_default PEGASUS_REPO https://github.com/PegasusSimulator/PegasusSimulator.git
conf_default ZED_WRAPPER_REPO https://github.com/stereolabs/zed-ros2-wrapper.git
conf_default ZED_ISAAC_EXT_REPO https://github.com/stereolabs/zed-isaac-sim.git
conf_default PX4_REPO https://github.com/PX4/PX4-Autopilot.git
# The PX4 bridge on the real drone: the Pixracer's serial port instead of the sim's UDP, wall-clock time (docker/bridge/*.yaml read these).
bridge_env_drone(){
  local ser="${DRONE_FCU_URL:-serial:///dev/px4:921600}"
  export BRIDGE_DEVICE=/dev/px4 BRIDGE_SIM_TIME=false FCU_URL="$ser" MAVSDK_URL="$ser" XRCE_TRANSPORT=serial
}
export FCU_URL="${FCU_URL:-}" GCS_URL="${GCS_URL:-}"      # empty = derived / disabled
export SIM_VIEW_ADDR="${SIM_VIEW_ADDR:-}"                 # empty = local viewers only

# SIM_MODE and SIM_STREAM were merged into SIM_VIEW. A leftover in a file would now be read,
# exported, and quietly ignored, so say so instead of booting the wrong way.
for _k in SIM_MODE SIM_STREAM SIM_STREAM_ADDR; do
  case "${BISG_SRC[$_k]:-}" in
    config/*|docker/.env) die "${_k} was replaced by SIM_VIEW / SIM_VIEW_ADDR — remove it from ${BISG_SRC[$_k]} (docs/configuration.md)";;
  esac
  [[ -n "${_BISG_ENV0[$_k]:-}" ]] && warn "${_k} is set in the environment but no longer read; SIM_VIEW decides the view"
done

STREAM_SIGNAL_PORT=49100      # TCP, hardcoded in the Isaac Sim WebRTC Streaming Client
STREAM_MEDIA_PORT=47998       # UDP, likewise
TAILSCALE_NAME=bisg-tailscale
# This host's tailnet IPv4 from the `tailscale` service (./bisg tailscale up); empty when it is not up or not logged in.
tailscale_ip(){ container_running "$TAILSCALE_NAME" && docker exec "$TAILSCALE_NAME" tailscale ip -4 2>/dev/null | head -1 || true; }
# SIM_VIEW_ADDR=tailscale means "this host's tailnet IP". Resolve it to an address before anything uses it.
resolve_view_addr(){
  [[ "${SIM_VIEW_ADDR:-}" == vpn ]] && die "SIM_VIEW_ADDR=vpn was renamed: set SIM_VIEW_ADDR=tailscale in docker/.env"
  [[ "${SIM_VIEW_ADDR:-}" == tailscale ]] || return 0
  local ip; ip="$(tailscale_ip)"
  [[ -n "$ip" ]] || die "SIM_VIEW_ADDR=tailscale but the tailscale service has no address: ./bisg tailscale up (then ./bisg tailscale status)"
  export SIM_VIEW_ADDR="$ip"
}
# Where a viewer should connect: SIM_VIEW_ADDR, else this host's LAN IP, else loopback.
stream_addr(){
  [[ "${SIM_VIEW_ADDR:-}" == tailscale ]] && { local v; v="$(tailscale_ip)"; echo "${v:-<tailscale not up>}"; return; }
  if [[ -n "${SIM_VIEW_ADDR:-}" ]]; then echo "$SIM_VIEW_ADDR"; return; fi
  local ip; ip=$(ip -4 route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' | head -1)
  echo "${ip:-127.0.0.1}"
}
# SIM_VIEW is the one knob for the window and the remote view. It resolves into the two things
# the container actually takes: which compose profile (SIM_HEADLESS) and what the launcher serves
# (SIM_STREAM). `auto` depends on $DISPLAY, so resolve lazily in a function, never at source time.
# Sets VIEW_MODE (gui|headless) and VIEW_STREAM (off|web|webrtc|both) rather than echoing them,
# so a bad value reaches `die` instead of dying inside a "$(...)" subshell.
view_parse(){
  local raw="${1:-${SIM_VIEW:-auto}}" tok win="" web=0 rtc=0 toks=()
  IFS='+' read -r -a toks <<<"${raw,,}"
  for tok in "${toks[@]}"; do
    tok="${tok// /}"
    case "$tok" in
      ""|auto)              [[ -z "$win" ]] && win=auto;;
      gui|window)           win=gui;;
      headless|off|none)    win=headless;;
      web|browser)          web=1;;
      webrtc|stream|livestream) rtc=1;;
      both)                 web=1; rtc=1;;
      remote) die "SIM_VIEW=remote is ambiguous: 'web' survives a VS Code/SSH tunnel, 'webrtc' is interactive but needs UDP on a LAN or Tailscale (docs/remote-access.md)";;
      *) die "SIM_VIEW: unknown value '$tok' (gui|headless|web|webrtc|both|auto, combined with '+'; got '$raw')";;
    esac
  done
  # a stream named on its own implies headless — serving a picture is the whole point of it
  if [[ -z "$win" ]]; then (( web || rtc )) && win=headless || win=auto; fi
  if [[ "$win" == auto ]]; then have_x11 && win=gui || win=headless; fi
  local str=off
  if   (( web && rtc )); then str=both
  elif (( web ));        then str=web
  elif (( rtc ));        then str=webrtc; fi
  VIEW_MODE="$win"; VIEW_STREAM="$str"
}
VIEW_MODE=""; VIEW_STREAM=off
# The SIM_VIEW spelling for a resolved pair, e.g. gui, headless, headless+web.
view_label(){ local m="${1:-$VIEW_MODE}" s="${2:-$VIEW_STREAM}"; [[ "$s" == off ]] && echo "$m" || echo "$m+$s"; }
sim_stream(){ view_parse "${1:-}"; echo "$VIEW_STREAM"; }
streaming_on(){ [[ "$(sim_stream)" =~ ^(webrtc|both)$ ]]; }
web_view_on(){ [[ "$(sim_stream)" =~ ^(web|both)$ ]]; }
view_on(){ [[ "$(sim_stream)" != off ]]; }

# True when $DISPLAY names an X server with a local socket (the one compose bind-mounts).
have_x11(){
  [[ -n "${DISPLAY:-}" ]] || return 1
  local n="${DISPLAY#*:}"; n="${n%%.*}"
  [[ -e "/tmp/.X11-unix/X${n}" ]]
}
# gui|headless from an explicit SIM_VIEW value, else the configured one.
sim_mode(){ view_parse "${1:-}"; echo "$VIEW_MODE"; }
# Scenario name (docker/sim/configs/<name>.yaml) or a path -> the /workspace path the container sees.
scenario_path(){
  local s="$1"
  [[ "$s" == */* || "$s" == *.yaml || "$s" == *.yml ]] || s="$ROOT/docker/sim/configs/$s.yaml"
  [[ -f "$s" || -f "$ROOT/${s#/workspace/}" ]] || warn "scenario file not found on the host: $s"
  to_ws "$s"
}

compose(){ docker compose -f "$COMPOSE_FILE" "$@"; }

# Every GPU container fails at `docker start` when the loaded nvidia module and the installed
# userspace disagree (apt upgraded the driver under a running kernel module). Catch it here: the
# raw failure is an unreadable OCI/CDI error. Set BISG_SKIP_GPU_CHECK=1 to bypass.
gpu_preflight(){
  [[ "${BISG_SKIP_GPU_CHECK:-0}" == "1" ]] && return 0
  nvidia-smi -L >/dev/null 2>&1 && return 0
  local err; err=$(nvidia-smi -L 2>&1 | head -2)
  fail "GPU unusable, containers cannot start: ${err}"
  if [[ "$err" == *"version mismatch"* ]]; then
    local loaded ondisk
    loaded=$(cat /sys/module/nvidia/version 2>/dev/null || echo "?")
    ondisk=$(modinfo -F version nvidia 2>/dev/null || echo "?")
    echo "  loaded kernel module: ${loaded}    installed on disk: ${ondisk}"
    echo "  fix A (reboot, also picks up any pending kernel):   sudo reboot"
    echo "  fix B (no reboot; ends the local desktop session, keeps SSH/VS Code tunnels):"
    echo "      sudo systemctl stop gdm3"
    echo "      sudo rmmod nvidia_uvm nvidia_drm nvidia_modeset nvidia && sudo modprobe nvidia"
    echo "      nvidia-smi && sudo systemctl start gdm3   # last part optional"
  fi
  echo "  details: ./bisg check    docs/debugging.md"
  return 1
}
container_running(){ [[ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" == "true" ]]; }
# NOTE: scripts use `set -o pipefail`; `docker logs | grep -q` then fails spuriously when grep exits early
# (docker logs gets EPIPE). Test grep's own status via PIPESTATUS instead.
_sim_log_has(){ docker logs "$SIM_NAME" 2>&1 | grep -q -E "$1"; [[ ${PIPESTATUS[1]} -eq 0 ]]; }
sim_ready(){ _sim_log_has "\[launch\] sim ready"; }
px4_ready(){ _sim_log_has "Ready for takeoff"; }
sim_failed(){ _sim_log_has "Traceback|\[launch\] .*(unknown|FATAL)|Failed to create any GPU devices"; }
# Run a command in the ros container with ROS 2 (and the ros2_ws overlay) sourced.
ros_exec(){ docker exec "$ROS_NAME" bash -c "source /opt/ros/jazzy/setup.bash; [ -f /workspace/docker/ros/ros2_ws/install/setup.bash ] && source /workspace/docker/ros/ros2_ws/install/setup.bash; $*"; }
# host path (inside repo) -> /workspace path
to_ws(){ local p="$1"; [[ "$p" = /workspace/* ]] && { echo "$p"; return; }; p="$(realpath -m "$p")"; echo "/workspace${p#"$ROOT"}"; }

# zed_stack (docker/zed/zed.yaml compiler/validator) is plain python + PyYAML: host python when it has yaml, else the ros image.
zs(){
  if python3 -c 'import yaml' 2>/dev/null; then PYTHONPATH="$ROOT/docker/zed" python3 -m zed_stack "$@"
  else docker run --rm -v "$ROOT":/workspace:ro -e PYTHONPATH=/workspace/docker/zed --entrypoint python3 bisg/ros:jazzy -m zed_stack "$@"; fi
}
