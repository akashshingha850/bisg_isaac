# syntax=docker/dockerfile:1.6
# bisg/px4-bridge — the one image of the `px4-bridge` service: MAVROS (inherited from bisg/ros) + the MAVSDK server + the uXRCE-DDS agent;
# PX4_BRIDGE picks which one the entrypoint runs. Docs: docs/px4-bridge.md.
#   uXRCE-DDS   Micro-XRCE-DDS-Agent v2.4.3 (the Jazzy-compatible release for PX4 v1.17's client) + px4_msgs release/1.17
#               (message definitions must match the firmware; PX4 1.17 versions its topics: /fmu/out/vehicle_status_v1 ...)
#   MAVSDK      mavsdk_server (gRPC, from the mavsdk-grpc wheel) as a service, plus both Python bindings for clients:
#               `mavsdk` 4.x = native binding (no server), `mavsdk_grpc` = the older gRPC API
# One image on x86_64 and arm64 (the Jetson builds it natively; agent ~10 min, everything else is wheels/colcon).
#
# Build:  docker compose -f docker/compose.yaml --profile px4-bridge build px4-bridge        (needs bisg/ros:jazzy first)
FROM bisg/ros:jazzy
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git ca-certificates libssl-dev python3-venv python3-psutil python3-numpy tcpdump \
    && rm -rf /var/lib/apt/lists/*

# Micro XRCE-DDS Agent (builds its own Fast-DDS/Fast-CDR as an ExternalProject)
RUN git clone --depth 1 -b v2.4.3 https://github.com/eProsima/Micro-XRCE-DDS-Agent.git /tmp/agent \
 && cmake -S /tmp/agent -B /tmp/agent/build -DCMAKE_BUILD_TYPE=Release \
 && cmake --build /tmp/agent/build -j"$(nproc)" && cmake --install /tmp/agent/build && ldconfig && rm -rf /tmp/agent

# px4_msgs for the firmware in use (PX4_TAG v1.17.0 -> release/1.17)
RUN mkdir -p /opt/px4_ws/src && git clone --depth 1 -b release/1.17 https://github.com/PX4/px4_msgs.git /opt/px4_ws/src/px4_msgs \
 && . /opt/ros/jazzy/setup.sh && cd /opt/px4_ws && colcon build --cmake-args -DCMAKE_BUILD_TYPE=Release \
 && rm -rf /opt/px4_ws/build /opt/px4_ws/log

# MAVSDK: native binding + gRPC package (which carries mavsdk_server)
RUN pip3 install --break-system-packages --no-cache-dir mavsdk mavsdk-grpc \
 && ln -sf "$(python3 -c 'import mavsdk_grpc, os; print(os.path.join(os.path.dirname(mavsdk_grpc.__file__), "bin", "mavsdk_server"))')" /usr/local/bin/mavsdk_server

WORKDIR /workspace
# The entrypoint (docker/px4-bridge/entrypoint.sh) is bind-mounted from the repo by compose, so changing it needs no rebuild.
CMD ["bash"]
