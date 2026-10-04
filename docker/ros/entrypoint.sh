#!/usr/bin/env bash
# Entrypoint for bisg/ros. Sources ROS 2 and the overlay in /workspace/ros2_ws if built.
#   mavros            launch MAVROS for DRONE_ID using FCU_URL (defaults to SITL instance DRONE_ID-1)
#   vio_mock          launch the sim mock VIO source (bisg_vehicle) in namespace /drone_<DRONE_ID>
#   video_stream      ROS Image topic -> RTP/H.264 UDP for QGroundControl (VIDEO_* env, docs/video-qgc.md)
#   build             colcon build the workspace (ros2_ws/src bind-mounted)
#   bash | <cmd>      shell / arbitrary command with the environment sourced
set -eo pipefail
source /opt/ros/jazzy/setup.bash
[[ -f /workspace/ros2_ws/install/setup.bash ]] && source /workspace/ros2_ws/install/setup.bash

DRONE_ID="${DRONE_ID:-1}"
INSTANCE=$((DRONE_ID - 1))
# PX4 SITL instance i: local 14580+i -> remote 14540+i (px4-rc.mavlink). Serial on the Jetson.
FCU_URL="${FCU_URL:-udp://:$((14540 + INSTANCE))@127.0.0.1:$((14580 + INSTANCE))}"
NS="${NS:-drone_${DRONE_ID}}"
# true in the sim stack (docker/compose.yaml): PX4 SITL runs on sim time and the launcher publishes
# /clock. false on hardware (deploy/jetson), where PX4 and the Jetson both run on real time.
USE_SIM_TIME="${USE_SIM_TIME:-false}"
MAVROS_SHARE=/opt/ros/jazzy/share/mavros/launch

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
         --params-file "${MAVROS_SHARE}/px4_pluginlists.yaml" --params-file "${MAVROS_SHARE}/px4_config.yaml"
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
  video_stream)
    echo "[entrypoint] video_stream drone=${DRONE_ID} -> udp://${VIDEO_HOST:-127.0.0.1}:${VIDEO_PORT:-5600}"
    exec python3 /usr/local/lib/bisg/video_stream.py
    ;;
  build)
    cd /workspace/ros2_ws
    rosdep install --from-paths src --ignore-src -r -y || true
    exec colcon build --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
    ;;
  *)
    exec "$@"
    ;;
esac
