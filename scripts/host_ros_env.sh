# Source me (bash/zsh):  source scripts/host_ros_env.sh      (BISG_ROS_QUIET=1: no banner, e.g. from ~/.bashrc)
# Puts this shell on the bisg containers' ROS graph: host ROS 2 Jazzy (scripts/install_host_ros.sh), the same ROS_DOMAIN_ID
# (config/bisg.conf / docker/.env, else derived from the hostname) and the same CycloneDDS profile. Debugging only.
_bisg_root="$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")/.." && pwd)"
if [[ ! -f /opt/ros/jazzy/setup.bash ]]; then
  echo "no host ROS 2 Jazzy: sudo $_bisg_root/scripts/install_host_ros.sh" >&2
else
  if [[ -n "${ZSH_VERSION:-}" ]]; then source /opt/ros/jazzy/setup.zsh; else source /opt/ros/jazzy/setup.bash; fi
  export ROS_DOMAIN_ID="$(bash -c ". '$_bisg_root/scripts/_common.sh' >/dev/null 2>&1; echo \$ROS_DOMAIN_ID")"
  export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
  export CYCLONEDDS_URI="file://$_bisg_root/docker/cyclonedds.xml"
  [[ "${BISG_ROS_QUIET:-0}" == 1 ]] || echo "host ROS 2 jazzy: ROS_DOMAIN_ID=$ROS_DOMAIN_ID, cyclonedds ($CYCLONEDDS_URI). Sim topics need use_sim_time (e.g. rviz2 --ros-args -p use_sim_time:=true)"
fi
unset _bisg_root
