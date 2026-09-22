# syntax=docker/dockerfile:1.6
# bisg/sim — Isaac Sim 5.1.0 + PX4 SITL + Pegasus Simulator, one image.
#
# Build (from repo root):  docker compose -f docker/compose.yaml build sim
# Pins are build args so ADR-003 changes are one-line edits in docker/.env.
#
# Facts about the base image (verified 2026-09-12): Ubuntu 24.04, runs as user
# `isaac-sim` (uid 1234, HOME=/isaac-sim), no sudo, Isaac python 3.11 at /isaac-sim/python.sh.

ARG ISAAC_TAG=5.1.0
FROM nvcr.io/nvidia/isaac-sim:${ISAAC_TAG}

ARG PX4_TAG=v1.17.0
ARG PEGASUS_TAG=v5.1.0
ARG DEBIAN_FRONTEND=noninteractive
ARG ISAAC_USER=isaac-sim

ENV ISAACSIM_PATH=/isaac-sim \
    ISAACSIM_PYTHON=/isaac-sim/python.sh \
    PX4_DIR=/opt/PX4-Autopilot \
    PEGASUS_DIR=/opt/PegasusSimulator \
    ACCEPT_EULA=Y \
    PRIVACY_CONSENT=Y \
    OMNI_KIT_ACCEPT_EULA=YES \
    TERM=xterm

# --- root: OS deps for the PX4 SITL toolchain -----------------------------------
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
        sudo git git-lfs ca-certificates curl wget build-essential cmake ninja-build \
        python3 python3-pip python3-dev python3-venv \
        rsync unzip zip file lsb-release pkg-config gdb \
        libxml2-utils astyle ccache \
        net-tools iproute2 procps psmisc \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p ${PX4_DIR} ${PEGASUS_DIR} \
    && chown ${ISAAC_USER}:${ISAAC_USER} ${PX4_DIR} ${PEGASUS_DIR}

# --- isaac-sim: clone PX4 at the pinned tag (shallow + shallow submodules) --------
USER ${ISAAC_USER}
RUN git clone --depth 1 --branch ${PX4_TAG} --recursive --shallow-submodules \
        https://github.com/PX4/PX4-Autopilot.git ${PX4_DIR}

# --- root: PX4's own dependency script (apt + system-wide pip, no NuttX/Gazebo) ---
USER root
RUN cd ${PX4_DIR} && bash Tools/setup/ubuntu.sh --no-nuttx --no-sim-tools \
    && rm -rf /var/lib/apt/lists/*

# --- isaac-sim: build the SITL binary only (no simulator target) ------------------
# Pegasus launches build/px4_sitl_default/bin/px4 itself with PX4_SIM_MODEL=gazebo-classic_iris.
USER ${ISAAC_USER}
RUN cd ${PX4_DIR} && make px4_sitl_default -j"$(nproc)" \
    && find build/px4_sitl_default -name "*.o" -delete

# --- isaac-sim: Pegasus at the pinned tag, installed into Isaac's Python ----------
RUN git clone --depth 1 --branch ${PEGASUS_TAG} \
        https://github.com/PegasusSimulator/PegasusSimulator.git ${PEGASUS_DIR} \
    && sed -i "s|^px4_dir:.*|px4_dir: ${PX4_DIR}|" \
        ${PEGASUS_DIR}/extensions/pegasus.simulator/config/configs.yaml
# setup.py needs ISAACSIM_PATH to patch apps/isaacsim.exp.base.kit (replicator agent ext).
RUN ${ISAACSIM_PYTHON} -m pip install --no-cache-dir --editable \
        ${PEGASUS_DIR}/extensions/pegasus.simulator \
    && ${ISAACSIM_PYTHON} -m pip install --no-cache-dir pyyaml pymavlink scipy

# Cache / log mount points must exist and be owned by isaac-sim, otherwise the named
# volumes in compose are created root-owned and Isaac cannot write to them.
# /isaac-sim/kit/logs holds the human-readable Kit log (Kit/Isaac-Sim Python/5.1/kit_*.log).
RUN mkdir -p /isaac-sim/.cache /isaac-sim/.nv/ComputeCache /isaac-sim/.nvidia-omniverse/logs \
        /isaac-sim/.nvidia-omniverse/config /isaac-sim/.local/share/ov/data \
        /isaac-sim/.local/share/ov/pkg /isaac-sim/Documents /isaac-sim/kit/logs

# --- Internal ROS 2 Jazzy bridge (base is 24.04; no host ROS needed) -------------
# Isaac 5.1 ships exts/isaacsim.ros2.bridge/{humble,jazzy}; select Jazzy and CycloneDDS
# (librmw_cyclonedds_cpp.so is bundled) per ADR-004/005.
ENV ROS_DISTRO=jazzy \
    RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
    LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:/isaac-sim/exts/isaacsim.ros2.bridge/jazzy/lib \
    CYCLONEDDS_URI=file:///workspace/docker/cyclonedds.xml

# Our code is bind-mounted at /workspace (see compose); nothing project-specific is baked in.
USER root
COPY docker/sim/entrypoint.sh /usr/local/bin/sim-entrypoint.sh
RUN chmod 755 /usr/local/bin/sim-entrypoint.sh && mkdir -p /workspace && chown ${ISAAC_USER} /workspace
USER ${ISAAC_USER}
WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/sim-entrypoint.sh"]
CMD ["launch"]
