#!/usr/bin/env bash
# Entrypoint of the `px4-bridge` service (docker/compose.yaml): ONE container, the bridge it runs is PX4_BRIDGE. Settings are env only.
#   PX4_BRIDGE=mavros   MAVLink -> ROS 2 topics /drone_N/mavros/*   (FCU_URL, GCS_URL, MAVROS_PLUGINS, USE_SIM_TIME)
#   PX4_BRIDGE=mavsdk   mavsdk_server, gRPC front for MAVLink        (MAVSDK_URL, MAVSDK_PORT)
#   PX4_BRIDGE=xrce     Micro XRCE-DDS Agent: uORB -> ROS 2 /fmu/*   (XRCE_TRANSPORT, XRCE_PORT, XRCE_DEV, XRCE_BAUD)
#   PX4_BRIDGE=none     do nothing (exit 0; compose does not restart it)
# Common: DRONE_ID (drone N = PX4 SITL instance N-1), ROS_DOMAIN_ID. Docs: docs/px4-bridge.md
set -eo pipefail
source /opt/ros/jazzy/setup.bash
[[ -f /workspace/docker/ros/ros2_ws/install/setup.bash ]] && source /workspace/docker/ros/ros2_ws/install/setup.bash
[[ -f /opt/px4_ws/install/setup.bash ]] && source /opt/px4_ws/install/setup.bash       # px4_msgs (xrce clients)

DRONE_ID="${DRONE_ID:-1}"
INSTANCE=$((DRONE_ID - 1))

mavros() {
  # FCU_URL empty = the sim's PX4 (udp://:14540+i@127.0.0.1:14580+i); serial:///dev/px4:921600 on the drone
  local fcu="${FCU_URL:-udp://:$((14540 + INSTANCE))@127.0.0.1:$((14580 + INSTANCE))}"
  local ns="${NS:-drone_${DRONE_ID}}" sim="${USE_SIM_TIME:-false}" share=/opt/ros/jazzy/share/mavros/launch
  # lean (docker/ros/mavros_lean.yaml, 17 plugins, idle 9 % CPU) falls back to MAVROS' stock list when the repo is not mounted
  local plugins=/workspace/docker/ros/mavros_lean.yaml
  if [[ "${MAVROS_PLUGINS:-lean}" == full || ! -f "$plugins" ]]; then plugins="${share}/px4_pluginlists.yaml"; fi
  echo "[px4-bridge] mavros ns=/${ns} tgt_system=${DRONE_ID} fcu_url=${fcu} plugins=$(basename "$plugins") use_sim_time=${sim} ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}"
  # Same node + param files as `ros2 launch mavros px4.launch`, run directly so use_sim_time can be set (px4.launch has no argument for it).
  # -p reaches mavros_node and the router only; MAVROS 2.15.1 builds each plugin node with use_global_arguments(false), so they ignore
  # -p and every --params-file: mavros_sim_time.py sets use_sim_time on them at runtime.
  local extra=()
  [[ -n "${GCS_URL:-}" ]] && extra+=(-p "gcs_url:=${GCS_URL}")      # an empty -p value is not a string
  local cmd=(ros2 run mavros mavros_node --ros-args -r __ns:="/${ns}"
             --params-file "$plugins" --params-file "${share}/px4_config.yaml"
             -p fcu_url:="$fcu" -p tgt_system:="${DRONE_ID}" -p tgt_component:=1 -p fcu_protocol:=v2.0
             -p use_sim_time:="$sim" "${extra[@]}")
  [[ "$sim" == true ]] || exec "${cmd[@]}"
  "${cmd[@]}" & local pid=$!
  trap 'kill -TERM "$pid" 2>/dev/null' TERM INT                       # keep `compose stop` clean (MAVROS is not PID 1)
  python3 /workspace/docker/ros/mavros_sim_time.py "/${ns}" || echo "[px4-bridge] WARNING: MAVROS plugins still on wall time"
  wait "$pid" || wait "$pid" 2>/dev/null || true                      # 1st wait returns early on SIGTERM; let MAVROS finish
}

mavsdk() {
  # MAVSDK_URL empty = the sim's PX4 (udpin://0.0.0.0:14540+i: PX4 SITL instance i sends its onboard MAVLink there); serial on the drone
  local url="${MAVSDK_URL:-udpin://0.0.0.0:$((14540 + INSTANCE))}"
  local server; server="$(command -v mavsdk_server || python3 -c 'import mavsdk_grpc, os; print(os.path.join(os.path.dirname(mavsdk_grpc.__file__), "bin", "mavsdk_server"))')"
  echo "[px4-bridge] mavsdk_server: gRPC :${MAVSDK_PORT:-50051} <- ${url}"
  exec "$server" -p "${MAVSDK_PORT:-50051}" "$url"
}

xrce() {
  echo "[px4-bridge] xrce agent: transport=${XRCE_TRANSPORT:-udp} ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0} (PX4's UXRCE_DDS_DOM_ID must equal it)"
  if [[ "${XRCE_TRANSPORT:-udp}" == serial ]]; then
    echo "[px4-bridge] serial ${XRCE_DEV:-/dev/px4} @ ${XRCE_BAUD:-921600}: PX4 needs UXRCE_DDS_CFG = that port and MAVLink off on it (./bisg px4-bridge params xrce)"
    exec MicroXRCEAgent serial --dev "${XRCE_DEV:-/dev/px4}" -b "${XRCE_BAUD:-921600}"
  fi
  echo "[px4-bridge] udp4 port ${XRCE_PORT:-8888} (PX4 SITL's client dials 8888; instance N > 0 adds the topic namespace /px4_N)"
  exec MicroXRCEAgent udp4 -p "${XRCE_PORT:-8888}"
}

case "${PX4_BRIDGE:-mavros}" in
  mavros) mavros;;
  mavsdk) mavsdk;;
  xrce)   xrce;;
  none)   echo "[px4-bridge] PX4_BRIDGE=none: nothing to run"; exit 0;;
  *)      echo "[px4-bridge] PX4_BRIDGE=${PX4_BRIDGE} is not mavros | mavsdk | xrce | none" >&2; exit 2;;
esac
