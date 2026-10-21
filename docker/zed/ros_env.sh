# Source this instead of /sbin/ros_entrypoint.sh in the ZED image (bisg/zed): Stereolabs' script hard-codes
# `export ROS_DOMAIN_ID=0`, which silently moves the wrapper/bridge/video off the domain the rest of the stack uses
# (ROS_DOMAIN_ID=auto, docs/configuration.md). This sources it, then puts the container's own domain back.
_bisg_domain="${ROS_DOMAIN_ID:-0}"
source /sbin/ros_entrypoint.sh
export ROS_DOMAIN_ID="$_bisg_domain"
unset _bisg_domain
