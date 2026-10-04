# syntax=docker/dockerfile:1.6
# bisg/ros — ROS 2 Jazzy + MAVROS + CycloneDDS + our ros2_ws. Same image for the
# workstation (against PX4 SITL) and the Jetson Orin NX (against the Pixracer).
#
# Build amd64 (workstation):  docker compose -f docker/compose.yaml build ros
# Build arm64 (Jetson):        docker buildx build --platform linux/arm64 -f docker/ros/Dockerfile -t bisg/ros:arm64 .

FROM ros:jazzy-ros-base
ARG DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=jazzy \
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    CYCLONEDDS_URI=file:///workspace/docker/cyclonedds.xml \
    LANG=C.UTF-8 LC_ALL=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        ros-jazzy-mavros ros-jazzy-mavros-extras ros-jazzy-mavros-msgs \
        ros-jazzy-rmw-cyclonedds-cpp \
        ros-jazzy-tf2-tools ros-jazzy-rqt-graph ros-jazzy-foxglove-bridge \
        python3-pip python3-colcon-common-extensions python3-rosdep python3-vcstool \
        python3-numpy python3-scipy python3-yaml \
        udev usbutils iproute2 net-tools less nano \
    && rm -rf /var/lib/apt/lists/*

# MAVROS needs the GeographicLib datasets (geoid) for global position conversions.
RUN /opt/ros/jazzy/lib/mavros/install_geographiclib_datasets.sh

# Video out (docker/ros/video_stream.py): ROS Image -> RTP/H.264 for QGroundControl.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3-gi gir1.2-gstreamer-1.0 gstreamer1.0-tools \
        gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-ugly \
    && rm -rf /var/lib/apt/lists/*

# rosdep for our workspace (initialised once at image build; updated at first run if needed)
RUN rosdep init 2>/dev/null || true && rosdep update --rosdistro jazzy || true

# Every interactive/`docker exec` bash gets ROS 2 + the overlay sourced (entrypoint does it for CMD).
RUN printf '%s\n' 'source /opt/ros/jazzy/setup.bash' '[ -f /workspace/ros2_ws/install/setup.bash ] && source /workspace/ros2_ws/install/setup.bash' >> /etc/bash.bashrc

WORKDIR /workspace/ros2_ws
COPY docker/ros/entrypoint.sh /usr/local/bin/ros-entrypoint.sh
COPY docker/ros/mavros_sim_time.py /usr/local/lib/bisg/mavros_sim_time.py
COPY docker/ros/video_stream.py /usr/local/lib/bisg/video_stream.py
RUN chmod +x /usr/local/bin/ros-entrypoint.sh
ENTRYPOINT ["/usr/local/bin/ros-entrypoint.sh"]
CMD ["bash"]
