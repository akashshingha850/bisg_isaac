#!/usr/bin/env bash
# Entrypoint for bisg/ros. Sources ROS 2 and the overlay in /workspace/ros2_ws if built.
#   mavros            launch MAVROS for DRONE_ID using FCU_URL (defaults to SITL instance DRONE_ID-1)
#   vio_mock          launch the sim mock VIO source (bisg_vehicle) in namespace /drone_<DRONE_ID>
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

case "${1:-bash}" in
  mavros)
    echo "[entrypoint] MAVROS ns=/${NS} tgt_system=${DRONE_ID} fcu_url=${FCU_URL} ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}"
    extra=()
    [[ -n "${GCS_URL:-}" ]] && extra+=("gcs_url:=${GCS_URL}")   # empty gcs_url:= is a malformed launch arg
    exec ros2 launch mavros px4.launch \
        fcu_url:="${FCU_URL}" tgt_system:="${DRONE_ID}" tgt_component:=1 namespace:="${NS}" "${extra[@]}"
    ;;
  vio_mock)
    echo "[entrypoint] vio_mock ns=/${NS} ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}"
    exec ros2 run bisg_vehicle vio_mock --ros-args -r "__ns:=/${NS}"
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
