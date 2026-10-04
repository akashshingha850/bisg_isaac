#!/usr/bin/env bash
# The ZED Mini stack: real ZED SDK wrapper + the services around it, all configured by docker/zed/zed.yaml
# (docs/zed-stack.md). In the sim it reads the Isaac ZED Mini twin (ZED_SOURCE=sdk, docs/zed-sdk-sim.md). Usually called through ./bisg.
#
#   zed.sh plan [--hw]                what is on: SDK modules, topics, services (default: with the sim deltas)
#   zed.sh set KEY=VALUE [...]        edit docker/zed/zed.yaml in place, validated:  set object_detection.enabled=true
#   zed.sh up [--drone N] [--video-host IP] [--video-port P]
#                                     start the wrapper, then every service the YAML enables (px4 bridge, QGC video)
#   zed.sh services                   restart only the side services after a `set` (the wrapper keeps running)
#   zed.sh enable MODULE [on|off]     switch object_detection|body_tracking|spatial_mapping|streaming|depth in the running wrapper
#   zed.sh down | status | logs [wrapper|bridge|video] [-f] | check [args]
#   zed.sh video-test                 host GStreamer player on the video port (close QGC's video first)
#   zed.sh test                       unit tests + the bridge against fake topics (no camera, no sim)
#   zed.sh ext-build | image          build the Isaac Sim extension / the bisg/zed image (once)
#
# Typical run:   ZED_SOURCE=sdk ./bisg all headless && ./bisg zed up && ./bisg zed status
set -euo pipefail
. "$(dirname "$0")/_common.sh"

sub="${1:-status}"; shift || true
passthru=(); hw=0; video_host=""; video_port=""
while [[ $# -gt 0 ]]; do case "$1" in
  --drone) export DRONE_ID=$2; shift;;
  --hw) hw=1;;
  --video-host) video_host=$2; shift;;
  --video-port) video_port=$2; shift;;
  *) passthru+=("$1");; esac; shift; done
ZNAME="bisg-zed-${DRONE_ID}"
# Port math lives with the launcher (sim/launcher/zed_sdk_cfg.py): drone N = vehicle id N-1 -> 30000 + 2*(N-1).
export ZED_SIM_PORT=$((30000 + 2 * (DRONE_ID - 1)))
[[ -n "$video_host" ]] && export VIDEO_HOST=$video_host
[[ -n "$video_port" ]] && export VIDEO_PORT=$video_port

zexec(){ docker exec "$ZNAME" bash -lc "source /sbin/ros_entrypoint.sh >/dev/null 2>&1; $*"; }
# best_effort: the wrapper publishes sensor-data QoS; a default (reliable) subscriber would never match it
have_frames(){ zexec "timeout 15 ros2 topic echo --once --qos-reliability best_effort --field header.stamp /drone_${DRONE_ID}/zed/zed_node/left/color/rect/image" >/dev/null 2>&1; }
svc_name(){ case $1 in wrapper|zed) echo "$ZNAME";; bridge|zed-bridge) echo "bisg-zed-bridge-${DRONE_ID}";; video|zed-video) echo "bisg-zed-video-${DRONE_ID}";; *) die "unknown service $1 (wrapper|bridge|video)";; esac; }

# (Re)start the services the YAML enables, stop the ones it disables. The wrapper is not touched.
start_services(){
  local wanted=" $(zs services --sim | tr '\n' ' ')" s
  for s in zed-bridge zed-video; do
    if [[ "$wanted" == *" $s "* ]]; then
      [[ $s == zed-bridge ]] && ! container_running "bisg-mavros-${DRONE_ID}" && warn "MAVROS for drone ${DRONE_ID} is not running (./bisg mavros up): the bridge has nowhere to send"
      compose --profile zed up -d --force-recreate "$s" >/dev/null; ok "$s started"
    else compose --profile zed rm -sf "$s" >/dev/null 2>&1 || true; fi
  done
  [[ "$wanted" == *" zed-video "* ]] && info "QGC: Application Settings > Video > Source 'UDP h.264 Video Stream', port ${VIDEO_PORT:-$(zs plan --sim | sed -n 's/.*udp:\/\/[^:]*:\([0-9]*\).*/\1/p' | head -1)}"
  return 0
}

case "$sub" in
  plan) zs plan $([[ $hw == 1 ]] || echo --sim);;
  set)  zs set "${passthru[@]}";;
  ext-build) exec "$ROOT/docker/zed/build_isaac_ext.sh";;
  image)     exec "$ROOT/docker/zed/build.sh";;           # variant by CPU architecture

  up)
    zs plan --sim >/dev/null || die "docker/zed/zed.yaml is invalid (fix it: ./bisg zed plan)"
    docker image inspect bisg/zed:${ZED_VARIANT} >/dev/null 2>&1 || die "bisg/zed:${ZED_VARIANT} is not built: ./bisg zed image"
    container_running "$SIM_NAME" || die "the sim is not running: ZED_SOURCE=sdk ./bisg up headless"
    docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$SIM_NAME" | grep -q '^ZED_SOURCE=sdk$' \
      || warn "the running sim was started with ZED_SOURCE != sdk: it publishes the emulated rig, there is no stream to read"
    [[ -e "/dev/shm/sl_local_video_${ZED_SIM_PORT}" ]] \
      || warn "no ZED stream segment /dev/shm/sl_local_video_${ZED_SIM_PORT} yet: the sim opens it once the timeline plays (./bisg wait)"
    for attempt in 1 2; do
      info "zed_wrapper for drone ${DRONE_ID} (stream port ${ZED_SIM_PORT}, attempt ${attempt}/2)"
      compose --profile zed up -d --force-recreate zed >/dev/null
      for _ in $(seq 1 45); do   # first start also compiles the depth model: allow it
        container_running "$ZNAME" && have_frames && { ok "$ZNAME publishing /drone_${DRONE_ID}/zed/zed_node/*"; break 2; }
        sleep 4
      done
      warn "no frames after ~3 min; the SDK connects once, so the next try restarts the wrapper"
      [[ $attempt == 2 ]] && { docker logs --tail 30 "$ZNAME" 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | cut -c1-200 >&2
                              die "zed_wrapper never received frames — see docs/zed-sdk-sim.md 'Troubleshooting'"; }
    done
    start_services; exit 0;;

  services) container_running "$ZNAME" || die "$ZNAME is not running (./bisg zed up)"; start_services;;   # restart only the side services (after `zed set`), wrapper untouched

  enable)   # switch an SDK module on/off in the RUNNING wrapper (no restart); docker/zed/zed.yaml is not changed
    mod="${passthru[0]:-}"; state="${passthru[1]:-on}"
    case "$mod" in object_detection) srv=enable_obj_det;; body_tracking) srv=enable_body_trk;; spatial_mapping) srv=enable_mapping;;
      streaming) srv=enable_streaming;; depth) srv=enable_depth;; *) die "enable: object_detection|body_tracking|spatial_mapping|streaming|depth [on|off]";; esac
    case "$state" in on|true) v=true;; off|false) v=false;; *) die "enable: state is on|off";; esac
    container_running "$ZNAME" || die "$ZNAME is not running (./bisg zed up)"
    zexec "ros2 service call /drone_${DRONE_ID}/zed/zed_node/$srv std_srvs/srv/SetBool '{data: $v}'" | grep -E "success|message" | sed 's/^/  /';;

  down) compose --profile zed rm -sf zed zed-bridge zed-video >/dev/null 2>&1 || true; ok "ZED stack of drone ${DRONE_ID} stopped";;

  status)
    container_running "$ZNAME" || { warn "$ZNAME is not running (./bisg zed up)"; exit 1; }
    ok "$ZNAME running"
    zexec "for t in left/color/rect/image depth/depth_registered odom imu/data; do
             printf '  %-26s' \$t; timeout 8 ros2 topic hz /drone_${DRONE_ID}/zed/zed_node/\$t 2>&1 | grep -m1 'average rate' || echo '(none)'; done
           timeout 6 ros2 topic echo --once /drone_${DRONE_ID}/zed/zed_node/status/health 2>&1 | grep -E 'low_' | sed 's/^/  /'"
    bn="$(svc_name bridge)"
    if container_running "$bn"; then
      ok "$bn running"
      docker exec "$bn" bash -lc "source /sbin/ros_entrypoint.sh >/dev/null 2>&1; timeout 6 ros2 topic echo --once --field data /drone_${DRONE_ID}/zed_stack/status" 2>/dev/null \
        | sed "s/^'//; s/'\$//; s/^data: //" | grep -m1 '^{' \
        | python3 -c 'import json,sys
for l in sys.stdin:
    d=json.loads(l); print("  bridge state:", d["state"])
    for k,v in d["components"].items(): print("   %-18s %-9s %s" % (k, v["state"], {a:b for a,b in v.items() if a!="state"}))' \
        || warn "no zed_stack/status yet (is the health module on?)"
    else info "px4 bridge not running (services.px4_bridge in docker/zed/zed.yaml)"; fi
    container_running "$(svc_name video)" && ok "$(svc_name video) running";;

  logs)
    which=wrapper; follow=""
    for a in "${passthru[@]:-}"; do case "$a" in wrapper|bridge|video) which=$a;; -f|--follow) follow=-f;; "") ;; *) die "logs: wrapper|bridge|video [-f]";; esac; done
    exec docker logs $follow --tail 100 "$(svc_name $which)";;

  check)
    container_running "$ZNAME" || die "$ZNAME is not running (./bisg zed up)"
    zexec "python3 /workspace/tests/zed_sdk_check.py --drone ${DRONE_ID} ${passthru[*]:-}";;

  video-test)
    command -v gst-launch-1.0 >/dev/null || die "video-test: needs gst-launch-1.0 on the host"
    port="${VIDEO_PORT:-5600}"
    info "playing udp ${port} (Ctrl-C to stop; close QGC's video first - one receiver per port)"
    exec gst-launch-1.0 udpsrc port="$port" caps="application/x-rtp,media=video,encoding-name=H264,payload=96" \
      ! rtph264depay ! avdec_h264 ! videoconvert ! autovideosink sync=false;;

  test)
    info "unit tests (host)"; PYTHONPATH="$ROOT/docker/zed" python3 -m unittest discover -s "$ROOT/tests/unit" 2>&1 | tail -4
    info "bridge against fake ZED + MAVROS topics (bisg/zed:${ZED_VARIANT}, ROS_DOMAIN_ID=77)"
    docker run --rm --network host --ipc host -e ROS_DOMAIN_ID=77 -v "$ROOT":/workspace:ro --entrypoint bash bisg/zed:${ZED_VARIANT} \
      -lc 'source /opt/ros/jazzy/setup.bash; cd /workspace && python3 tests/zed_bridge_fake.py' 2>&1 | grep -E "PASS|FAIL|^[a-z]" ;;

  *) sed -n 2,21p "$0"; exit 2;;
esac
