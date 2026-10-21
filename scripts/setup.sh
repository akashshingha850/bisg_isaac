#!/usr/bin/env bash
# One-shot workstation setup for bisg_isaac. Idempotent: re-run any time.
#
#   scripts/setup.sh                 # check host, write .env, xhost, pull, build sim + ros
#   scripts/setup.sh --arm64         # also cross-build bisg/ros:arm64 for the Jetson (qemu, ~15 min)
#   scripts/setup.sh --third-party   # also clone Pegasus + zed-ros2-wrapper into docker/sim/ and docker/zed/
#   scripts/setup.sh --rebuild       # force rebuild images (--no-cache)
#   scripts/setup.sh --no-build      # stop after pulls (e.g. to run builds later)
#   scripts/setup.sh --save-images   # docker save the Isaac base image to the SSD (risk R7)
set -euo pipefail
. "$(dirname "$0")/_common.sh"

ARM64=0; THIRD=0; REBUILD=0; NOBUILD=0; SAVE=0
for a in "$@"; do case "$a" in
  --arm64) ARM64=1;; --third-party) THIRD=1;; --rebuild) REBUILD=1;; --no-build) NOBUILD=1;; --save-images) SAVE=1;;
  -h|--help) sed -n 2,10p "$0"; exit 0;; *) die "unknown option $a";; esac; done

info "1/7 host preflight"
"$ROOT/scripts/check_env.sh" || die "host check failed — fix the [FAIL] lines above"

info "2/7 config (project defaults: config/bisg.conf; machine overrides: docker/.env)"
if [[ ! -f "$ENV_FILE" ]]; then
  cp "$ENV_FILE.example" "$ENV_FILE"
  [[ -n "${DISPLAY:-}" ]] && sed -i "s|^DISPLAY=.*|DISPLAY=${DISPLAY}|" "$ENV_FILE"
  ok "created $ENV_FILE (DISPLAY=${DISPLAY:-unset})"
else ok "exists: $ENV_FILE"; fi
ok "defaults: $CONF_DIR/*.conf (./bisg config to review, --edit <name> to change)"

info "3/7 X11 access for the sim container (user isaac-sim, uid 1234)"
if [[ -n "${DISPLAY:-}" ]] && command -v xhost >/dev/null; then xhost +local: >/dev/null && ok "xhost +local:"; else warn "no DISPLAY/xhost — GUI profile unavailable in this shell"; fi

info "4/7 base images"
docker pull -q "nvcr.io/nvidia/isaac-sim:${ISAAC_TAG}" >/dev/null && ok "nvcr.io/nvidia/isaac-sim:${ISAAC_TAG}"
docker pull -q ros:jazzy-ros-base >/dev/null && ok "ros:jazzy-ros-base"
if [[ $SAVE == 1 ]]; then "$ROOT/scripts/pull_images.sh" --save; fi

if [[ $THIRD == 1 ]]; then info "5/7 upstream sources"; "$ROOT/scripts/fetch_sources.sh"; else info "5/7 upstream sources (skipped; --third-party)"; fi

if [[ $NOBUILD == 1 ]]; then info "6/7 build skipped (--no-build)"; exit 0; fi
info "6/7 build images (sim: PX4 ${PX4_TAG} SITL + Pegasus ${PEGASUS_TAG} on Isaac ${ISAAC_TAG}; ros: Jazzy + MAVROS)"
BARGS=(); [[ $REBUILD == 1 ]] && BARGS+=(--no-cache)
if [[ $REBUILD == 0 ]] && docker image inspect "bisg/sim:${ISAAC_TAG}" >/dev/null 2>&1; then ok "bisg/sim:${ISAAC_TAG} exists (use --rebuild to force)"; else compose build "${BARGS[@]}" sim; fi
if [[ $REBUILD == 0 ]] && docker image inspect bisg/ros:jazzy >/dev/null 2>&1; then ok "bisg/ros:jazzy exists"; else compose build "${BARGS[@]}" ros; fi
if [[ $ARM64 == 1 ]]; then
  ls /proc/sys/fs/binfmt_misc 2>/dev/null | grep -q aarch64 || die "no arm64 binfmt: run  docker run --privileged --rm tonistiigi/binfmt --install arm64"
  docker buildx build --platform linux/arm64 -f "$ROOT/docker/ros/Dockerfile" -t bisg/ros:arm64 --load "$ROOT" && ok "bisg/ros:arm64"
fi

info "7/7 sanity"
docker run --rm --entrypoint bash "bisg/sim:${ISAAC_TAG}" -c 'test -x /opt/PX4-Autopilot/build/px4_sitl_default/bin/px4 && /isaac-sim/python.sh -m pip show pegasus-simulator >/dev/null' && ok "sim image: PX4 SITL binary + Pegasus present"
docker run --rm bisg/ros:jazzy bash -lc 'ros2 pkg prefix mavros >/dev/null && test -f /usr/share/GeographicLib/geoids/egm96-5.pgm' && ok "ros image: MAVROS + geoid datasets"
echo
echo "${C_B}Setup complete.${C_0} Next:"
echo "  ./bisg config             # settings: gui/headless, scenario, endpoints, pins"
echo "  ./bisg up headless        # or: ./bisg up gui | web | webrtc   (default: SIM_VIEW in config/bisg.conf)"
echo "  ./bisg up headless --web  # + a browser view you can reach over a VS Code/SSH tunnel"
echo "  ./bisg wait && ./bisg smoke"
echo "  ./bisg mavros up && ./bisg mavros state"
echo "  docs/runbook-sim.md, docs/debugging.md"
