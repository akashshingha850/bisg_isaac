#!/usr/bin/env bash
# Standalone PX4 SITL with the built-in SIH physics (no Isaac Sim) for the link benchmark: px4.sh up|down|cmd <px4-client args>
# Runs as PX4 INSTANCE 1 so it never touches the ports of the Isaac stack (instance 0: 14540/14580/14550/18570/8888):
#   MAVLink onboard 14581 -> 14541, GCS 18571 -> 14551, DDS 8889 (no topic namespace), MAV_SYS_ID 2, ROS_DOMAIN_ID 77.
set -euo pipefail
N=bisg-px4-sih
case "${1:-up}" in
  up)   docker rm -f $N >/dev/null 2>&1 || true
        docker run -d --name $N --network host --ipc host -e ROS_DOMAIN_ID=77 -e PX4_UXRCE_DDS_PORT=8889 -e PX4_UXRCE_DDS_NS= --entrypoint bash bisg/sim:6.0.0 -c \
          'mkdir -p /tmp/rootfs && cd /tmp/rootfs && export PX4_SIM_MODEL=sihsim_quadx && exec /opt/PX4-Autopilot/build/px4_sitl_default/bin/px4 /opt/PX4-Autopilot/ROMFS/px4fmu_common/ -s /opt/PX4-Autopilot/ROMFS/px4fmu_common/init.d-posix/rcS -i 1 -d' >/dev/null
        for _ in $(seq 1 60); do docker logs $N 2>&1 | grep -q "Ready for takeoff" && exit 0; sleep 1; done
        echo "PX4 did not become ready" >&2; exit 1;;
  down) docker rm -f $N >/dev/null 2>&1 || true;;
  cmd)  shift; c=$1; shift     # px4-<module> --instance 1 <args>: the client talks to the daemon socket of instance 1
        docker exec $N bash -c "cd /tmp && /opt/PX4-Autopilot/build/px4_sitl_default/bin/px4-$c --instance 1 $*" 2>&1;;
esac
