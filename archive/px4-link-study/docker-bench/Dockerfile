# syntax=docker/dockerfile:1.6
# bisg/px4link-bench — the three ways a Jetson companion talks to PX4, side by side (docs/study-px4-link.md):
#   MAVROS      (already in bisg/ros)        MAVLink  -> ROS 2 topics/services
#   MAVSDK      mavsdk python + mavsdk_server  MAVLink  -> gRPC API
#   uXRCE-DDS   Micro-XRCE-DDS-Agent v2.4.3 + px4_msgs release/1.17   PX4 uORB <-> ROS 2 (CDR over XRCE)
# Versions follow the pinned firmware: PX4 v1.17.0 ships Micro-XRCE-DDS-Client 2.4.x, whose Jazzy-compatible agent is v2.4.3.
FROM bisg/ros:jazzy
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git ca-certificates libssl-dev python3-venv python3-psutil python3-numpy tcpdump \
    && rm -rf /var/lib/apt/lists/*

# Micro XRCE-DDS Agent (builds its own Fast-DDS/Fast-CDR as an ExternalProject)
RUN git clone --depth 1 -b v2.4.3 https://github.com/eProsima/Micro-XRCE-DDS-Agent.git /tmp/agent \
 && cmake -S /tmp/agent -B /tmp/agent/build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build /tmp/agent/build -j"$(nproc)" && cmake --install /tmp/agent/build && ldconfig && rm -rf /tmp/agent

# px4_msgs: ROS 2 message definitions that must match the firmware (release/1.17 = v1.17.0)
RUN mkdir -p /opt/px4_ws/src && git clone --depth 1 -b release/1.17 https://github.com/PX4/px4_msgs.git /opt/px4_ws/src/px4_msgs \
 && . /opt/ros/jazzy/setup.sh && cd /opt/px4_ws && colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release \
 && rm -rf /opt/px4_ws/build /opt/px4_ws/log

# MAVSDK-Python 4.x = native binding (no gRPC, no server process); mavsdk-grpc = the older gRPC API (import mavsdk_grpc) that bundles mavsdk_server
RUN pip3 install --break-system-packages --no-cache-dir mavsdk mavsdk-grpc

ENV PX4_MSGS_SETUP=/opt/px4_ws/install/setup.bash
WORKDIR /workspace
