#!/usr/bin/env bash
# Entrypoint for bisg/ros. Sources ROS 2 and the overlay in /workspace/docker/ros/ros2_ws if built.
#   mavros            -> docker/px4-bridge/entrypoint.sh with PX4_BRIDGE=mavros (settings are env)
#   build             colcon build the workspace (docker/ros/ros2_ws/src bind-mounted)
#   bash | <cmd>      shell / arbitrary command with the environment sourced
set -eo pipefail
source /opt/ros/jazzy/setup.bash
[[ -f /workspace/docker/ros/ros2_ws/install/setup.bash ]] && source /workspace/docker/ros/ros2_ws/install/setup.bash

DRONE_ID="${DRONE_ID:-1}"
NS="${NS:-drone_${DRONE_ID}}"

case "${1:-bash}" in
  mavros)   # compose runs the px4-bridge service's entrypoint directly; kept so `docker run bisg/ros mavros` still works
    PX4_BRIDGE=mavros exec /workspace/docker/px4-bridge/entrypoint.sh
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
