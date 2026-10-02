#!/usr/bin/env bash
# Entrypoint for bisg/perception. Sources ROS 2 and the overlay in /workspace/ros2_ws (built with `./bisg ros build`).
#   perception   run the selected backend for DRONE_ID: PERCEPTION_BACKEND = isaac_ros | ros2   (docs/perception.md)
#   bench        score the running backend against the sim's ground truth (bisg_perception bench)
#   bash | <cmd> shell / arbitrary command with the environment sourced
# Environment (all set by ./bisg from config/bisg.conf):
#   PERCEPTION_BACKEND  isaac_ros | ros2          PERCEPTION_FEED_MAVROS  true|false (false = observer, used by the benchmark)
#   PERCEPTION_DEPTH    true|false                PERCEPTION_ODOM         true|false
#   PERCEPTION_IMU      true|false (cuVSLAM VIO)  DRONE_ID, USE_SIM_TIME
set -eo pipefail
source /opt/ros/jazzy/setup.bash
if [[ -f /workspace/ros2_ws/install/setup.bash ]]; then source /workspace/ros2_ws/install/setup.bash
else echo "[perception] ros2_ws is not built: run ./bisg ros build" >&2; fi

DRONE_ID="${DRONE_ID:-1}"
case "${1:-bash}" in
  perception)
    echo "[perception] backend=${PERCEPTION_BACKEND:-isaac_ros} drone=${DRONE_ID} feed_mavros=${PERCEPTION_FEED_MAVROS:-true}" \
         "odom=${PERCEPTION_ODOM:-true} depth=${PERCEPTION_DEPTH:-true} imu=${PERCEPTION_IMU:-false} sim_time=${USE_SIM_TIME:-true}"
    exec ros2 launch bisg_perception perception.launch.py \
        backend:="${PERCEPTION_BACKEND:-isaac_ros}" drone_id:="${DRONE_ID}" feed_mavros:="${PERCEPTION_FEED_MAVROS:-true}" \
        odom:="${PERCEPTION_ODOM:-true}" depth:="${PERCEPTION_DEPTH:-true}" imu:="${PERCEPTION_IMU:-false}" \
        use_sim_time:="${USE_SIM_TIME:-true}" confidence:="${PERCEPTION_ISAAC_CONFIDENCE:-60000}" max_disparity:="${PERCEPTION_ISAAC_MAXDISP:-64.0}"
    ;;
  bench)
    shift
    exec ros2 run bisg_perception bench --ros-args -r "__ns:=/drone_${DRONE_ID}" -p use_sim_time:=false \
        -p backend:="${PERCEPTION_BACKEND:-unknown}" "$@"
    ;;
  *)
    exec "$@"
    ;;
esac
