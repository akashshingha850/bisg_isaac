#!/usr/bin/env bash
# Entrypoint for bisg/ros. Sources ROS 2 and the overlay in /workspace/docker/ros/ros2_ws if built.
#   mavros            launch MAVROS for DRONE_ID using FCU_URL (defaults to SITL instance DRONE_ID-1)
#   vio_mock          launch the sim mock VIO source (bisg_vehicle) in namespace /drone_<DRONE_ID>
#   build             colcon build the workspace (docker/ros/ros2_ws/src bind-mounted)
#   bash | <cmd>      shell / arbitrary command with the environment sourced
set -eo pipefail
source /opt/ros/jazzy/setup.bash
[[ -f /workspace/docker/ros/ros2_ws/install/setup.bash ]] && source /workspace/docker/ros/ros2_ws/install/setup.bash

DRONE_ID="${DRONE_ID:-1}"
INSTANCE=$((DRONE_ID - 1))
# PX4 SITL instance i: local 14580+i -> remote 14540+i (px4-rc.mavlink). Serial on the Jetson.
FCU_URL="${FCU_URL:-udp://:$((14540 + INSTANCE))@127.0.0.1:$((14580 + INSTANCE))}"
NS="${NS:-drone_${DRONE_ID}}"
# true in the sim stack (docker/compose.yaml): PX4 SITL runs on sim time and the launcher publishes
# /clock. false on hardware (compose profile `drone`), where PX4 and the Jetson both run on real time.
USE_SIM_TIME="${USE_SIM_TIME:-false}"
MAVROS_SHARE=/opt/ros/jazzy/share/mavros/launch
# Lean plugin list (docker/ros/mavros_lean.yaml): only what the drone uses, idle CPU 28 % -> 9 % (archive/px4-link-study/study-px4-link.md).
# Falls back to MAVROS' stock list when the repo is not mounted.
PLUGIN_LIST=/workspace/docker/ros/mavros_lean.yaml
[[ -f "$PLUGIN_LIST" ]] || PLUGIN_LIST="${MAVROS_SHARE}/px4_pluginlists.yaml"

case "${1:-bash}" in
  mavros)
    echo "[entrypoint] MAVROS ns=/${NS} tgt_system=${DRONE_ID} fcu_url=${FCU_URL} use_sim_time=${USE_SIM_TIME} ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}"
    # Same node + param files as `ros2 launch mavros px4.launch` (its node.launch), run directly so
    # use_sim_time can be set: px4.launch has no argument for it. -p reaches mavros_node and the
    # router only; MAVROS 2.15.1 builds each plugin node with use_global_arguments(false), so they
    # ignore -p and every --params-file. mavros_sim_time.py sets it on them at runtime.
    extra=()
    [[ -n "${GCS_URL:-}" ]] && extra+=(-p "gcs_url:=${GCS_URL}")   # an empty -p value is not a string
    cmd=(ros2 run mavros mavros_node --ros-args -r __ns:="/${NS}"
         --params-file "${PLUGIN_LIST}" --params-file "${MAVROS_SHARE}/px4_config.yaml"
         -p fcu_url:="${FCU_URL}" -p tgt_system:="${DRONE_ID}" -p tgt_component:=1 -p fcu_protocol:=v2.0
         -p use_sim_time:="${USE_SIM_TIME}" "${extra[@]}")
    [[ "${USE_SIM_TIME}" == true ]] || exec "${cmd[@]}"
    "${cmd[@]}" & pid=$!
    trap 'kill -TERM "$pid" 2>/dev/null' TERM INT        # keep `compose stop` clean (MAVROS is not PID 1)
    python3 /usr/local/lib/bisg/mavros_sim_time.py "/${NS}" || echo "[entrypoint] WARNING: MAVROS plugins still on wall time"
    wait "$pid" || wait "$pid" 2>/dev/null || true   # 1st wait returns early on SIGTERM; let MAVROS finish
    ;;
  vio_mock)
    echo "[entrypoint] vio_mock ns=/${NS} ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}"
    exec ros2 run bisg_vehicle vio_mock --ros-args -r "__ns:=/${NS}" -p use_sim_time:="${USE_SIM_TIME}"
    ;;
  build)
    cd /workspace/docker/ros/ros2_ws
    rosdep install --from-paths src --ignore-src -r -y || true
    exec colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
    ;;
  *)
    exec "$@"
    ;;
esac
