#!/usr/bin/env bash
# Install ROS 2 Jazzy on THIS host (Ubuntu 24.04), for debugging only: ros2 topic/echo/bag, rviz2, rqt, PlotJuggler-style
# tools on the desktop without `docker exec`. Nothing in bisg depends on it (every runtime piece stays in its container).
# After it: `source scripts/host_ros_env.sh` puts a shell on the containers' ROS domain + CycloneDDS profile.
#
#   sudo scripts/install_host_ros.sh            ros-jazzy-desktop + the bits bisg topics need
#   sudo scripts/install_host_ros.sh --base     ros-jazzy-ros-base instead (no rviz2/rqt)
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run with sudo: sudo $0 $*" >&2; exit 1; }
. /etc/os-release
[[ "${VERSION_CODENAME:-}" == noble ]] || { echo "ROS 2 Jazzy needs Ubuntu 24.04 (noble); this is ${PRETTY_NAME:-unknown}" >&2; exit 1; }
META=ros-jazzy-desktop; [[ "${1:-}" == --base ]] && META=ros-jazzy-ros-base

# ROS apt source, the way the Jazzy install guide does it (ros2-apt-source package: key + sources entry, kept up to date)
apt-get update
apt-get install -y software-properties-common curl
add-apt-repository -y universe
if ! dpkg -s ros2-apt-source >/dev/null 2>&1; then
  ver=$(curl -fsSL https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest | grep -F '"tag_name"' | awk -F'"' '{print $4}')
  [[ -n "$ver" ]] || { echo "could not read the ros-apt-source release (GitHub API)" >&2; exit 1; }
  curl -fsSL -o /tmp/ros2-apt-source.deb \
    "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${ver}/ros2-apt-source_${ver}.${VERSION_CODENAME}_all.deb"
  dpkg -i /tmp/ros2-apt-source.deb
fi
apt-get update

# The DDS the containers use (ADR-004), MCAP bags (./bisg bag), message types bisg publishes, TF tools.
apt-get install -y "$META" ros-dev-tools \
  ros-jazzy-rmw-cyclonedds-cpp \
  ros-jazzy-rosbag2-storage-mcap \
  ros-jazzy-mavros-msgs \
  ros-jazzy-tf2-tools ros-jazzy-tf2-ros-py \
  ros-jazzy-image-transport-plugins

# Images over DDS need a big socket receive buffer (docker/cyclonedds.xml asks for 16 MB; bisg docs/setup.md)
cur=$(sysctl -n net.core.rmem_max)
if (( cur < 16777216 )); then
  echo "net.core.rmem_max=16777216" > /etc/sysctl.d/60-bisg-dds.conf && sysctl -p /etc/sysctl.d/60-bisg-dds.conf
fi

echo
echo "ROS 2 Jazzy installed ($META). In a shell: source $(cd "$(dirname "$0")" && pwd)/host_ros_env.sh"
