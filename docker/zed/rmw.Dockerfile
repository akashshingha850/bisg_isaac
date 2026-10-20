# Thin layer on the Stereolabs-built ZED image (docker/zed/build.sh): their image only ships the
# default Fast DDS RMW, but every bisg container talks CycloneDDS (docker/cyclonedds.xml).
ARG BASE
FROM ${BASE}
RUN apt-get update && apt-get install -y --no-install-recommends ros-jazzy-rmw-cyclonedds-cpp \
    && rm -rf /var/lib/apt/lists/*
