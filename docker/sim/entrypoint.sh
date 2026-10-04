#!/usr/bin/env bash
# Entrypoint for bisg/sim. Modes:
#   launch            run sim/launcher/launch.py with $SIM_CONFIG (default)
#   shell | bash      interactive shell with the Isaac env
#   python <args>     run Isaac's python with args
#   check             Isaac compatibility check (no window, quits after 10 s)
#   <anything else>   exec as-is
set -euo pipefail

export SIM_CONFIG="${SIM_CONFIG:-/workspace/docker/sim/configs/single_iris.yaml}"
if [[ "${SIM_HEADLESS:-0}" == "1" ]]; then
  export SIM_HEADLESS=1
fi

# Isaac ROS 2 bridge: Jazzy internal libs (see Dockerfile ENV). Make sure the
# bridge check tool sees the right distro if someone sources host ROS by accident.
export ROS_DISTRO=jazzy

# /isaac-sim/python.sh is a bash wrapper that runs python as a CHILD (no exec). As PID 1 that
# bash ignores SIGTERM, so `docker stop` never reaches the launcher and ends in SIGKILL.
# Replicate the wrapper's environment here and exec the interpreter directly.
isaac_python_exec() {
  export CARB_APP_PATH=/isaac-sim/kit ISAAC_PATH=/isaac-sim EXP_PATH=/isaac-sim/apps
  export PYTHONPATH="${PYTHONPATH:-}" LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}"   # setup script assumes they exist (set -u)
  # shellcheck disable=SC1091
  source /isaac-sim/setup_python_env.sh
  [[ -f /isaac-sim/vulkan_check.sh ]] && /isaac-sim/vulkan_check.sh
  export RESOURCE_NAME="IsaacSim" LD_PRELOAD=/isaac-sim/kit/libcarb.so
  exec /isaac-sim/kit/python/bin/python3 "$@"
}

case "${1:-launch}" in
  launch)
    echo "[entrypoint] SIM_CONFIG=${SIM_CONFIG} SIM_HEADLESS=${SIM_HEADLESS:-0} SIM_STREAM=${SIM_STREAM:-off} ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}"
    isaac_python_exec /workspace/sim/launcher/launch.py --config "${SIM_CONFIG}"
    ;;
  shell|bash)
    exec bash
    ;;
  python)
    shift
    isaac_python_exec "$@"
    ;;
  check)
    exec /isaac-sim/isaac-sim.compatibility_check.sh --/app/quitAfter=10 --no-window
    ;;
  *)
    exec "$@"
    ;;
esac
