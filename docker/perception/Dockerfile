# syntax=docker/dockerfile:1.6
# bisg/perception — the two interchangeable perception backends in one image (docs/perception.md):
#   isaac_ros  NVIDIA Isaac ROS 4.6 (Jazzy, Ubuntu 24.04): cuVSLAM visual-inertial odometry + VPI stereo depth, NITROS
#   ros2       traditional CPU ROS 2: rtabmap stereo odometry + stereo_image_proc
# Both read the sim's ZED topics (zed/zed_node/...) and publish the same interface (perception/odom, perception/disparity),
# so the backend is a one-line switch (PERCEPTION_BACKEND in config/bisg.conf).
#
# Isaac ROS release line: release-4 = ROS 2 Jazzy (amd64 noble + arm64 noble-jetpack); release-5 = Lyrical only (checked
# 2026-10-03 against isaac.download.nvidia.com), so 4.6 is the line that matches our Jazzy containers and the Jetson.
# Needs the NVIDIA runtime at run time (compose `runtime: nvidia`); the host driver must support CUDA 13.x (580+ does).
#
# Build:  docker compose -f docker/compose.yaml --profile perception-isaac-ros build perception-isaac-ros

FROM ros:jazzy-ros-base
ARG DEBIAN_FRONTEND=noninteractive
ARG ISAAC_ROS_RELEASE=release-4
# NVIDIA VPI 4 (libnvvpi4, vpi4-dev) is a hard dependency of the Isaac ROS packages and is not in the two repos above.
ARG VPI_REPO=r38.4
ENV ROS_DISTRO=jazzy \
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    CYCLONEDDS_URI=file:///workspace/docker/cyclonedds.xml \
    LANG=C.UTF-8 LC_ALL=C.UTF-8 \
    NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=all

# NVIDIA CUDA repo (Isaac ROS packages depend on cuda-toolkit-13-2), the Isaac ROS apt repo and the VPI repo.
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg ca-certificates \
    && curl -fsSLo /tmp/cuda-keyring.deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb \
    && dpkg -i /tmp/cuda-keyring.deb && rm /tmp/cuda-keyring.deb \
    && curl -fsSL https://isaac.download.nvidia.com/isaac-ros/repos.key | gpg --dearmor -o /usr/share/keyrings/nvidia-isaac-ros.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/nvidia-isaac-ros.gpg] https://isaac.download.nvidia.com/isaac-ros/${ISAAC_ROS_RELEASE} noble main" \
        > /etc/apt/sources.list.d/nvidia-isaac-ros.list \
    && curl -fsSL https://repo.download.nvidia.com/jetson/jetson-ota-public.asc | gpg --dearmor -o /usr/share/keyrings/nvidia-jetson.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/nvidia-jetson.gpg] https://repo.download.nvidia.com/jetson/x86_64/noble ${VPI_REPO} main" \
        > /etc/apt/sources.list.d/nvidia-vpi.list \
    && rm -rf /var/lib/apt/lists/*

# Isaac ROS (GPU) ...
RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-isaac-ros-visual-slam \
        ros-jazzy-isaac-ros-stereo-image-proc \
        ros-jazzy-isaac-ros-image-proc \
        ros-jazzy-isaac-ros-nitros \
    && rm -rf /var/lib/apt/lists/*

# ... and the traditional CPU baseline + what our own nodes need.
RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-stereo-image-proc ros-jazzy-image-proc ros-jazzy-rtabmap-odom \
        ros-jazzy-rmw-cyclonedds-cpp ros-jazzy-tf2-ros ros-jazzy-tf2-tools \
        python3-numpy python3-scipy python3-yaml python3-pip \
        iproute2 procps less nano \
    && rm -rf /var/lib/apt/lists/*

RUN printf '%s\n' 'source /opt/ros/jazzy/setup.bash' '[ -f /workspace/ros2_ws/install/setup.bash ] && source /workspace/ros2_ws/install/setup.bash' >> /etc/bash.bashrc

WORKDIR /workspace/ros2_ws
COPY docker/perception/entrypoint.sh /usr/local/bin/perception-entrypoint.sh
RUN chmod +x /usr/local/bin/perception-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/perception-entrypoint.sh"]
CMD ["bash"]
