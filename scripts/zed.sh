#!/usr/bin/env bash
# The ZED Mini stack: real ZED SDK wrapper + the services around it, all configured by docker/zed/zed.yaml
# (docs/zed-stack.md). In the sim it reads the Isaac ZED Mini twin (docs/zed-sdk-sim.md). Usually called through ./bisg.
#
#   zed.sh plan [--hw]                what is on: SDK modules, topics, services (default: with the sim deltas)
#   zed.sh set KEY=VALUE [...]        edit docker/zed/zed.yaml in place, validated:  set object_detection.enabled=true
#   zed.sh up [-d] [--drone N] [--video-host H] [--video-port P]   -d = start in the background and return at once (no wait for frames)
#                                     start the wrapper, then every service the YAML enables (px4 bridge, QGC video;
#                                     --video-host also turns the video on). H = an IP or a tailnet device name (./bisg tailscale status)
#   zed.sh services                   restart only the side services after a `set` (the wrapper keeps running)
#   zed.sh video [--video-host H] [--video-port P]   only the QGC video sender (services.qgc_video), whatever services.qgc_video.enabled
#                                     says; reads left/color/rect/image, so it also works on the emulated rig (no zed_wrapper)
#   zed.sh enable MODULE [on|off]     switch object_detection|body_tracking|spatial_mapping|streaming|depth in the running wrapper
#   zed.sh down | status | logs [wrapper|bridge|video] [-f] | check [args]
#   zed.sh video-test                 host GStreamer player on the video port (close QGC's video first)
#   zed.sh test                       unit tests + the bridge against fake topics (no camera, no sim)
#   zed.sh bench [--quick] [--streaming] [--window S]   test + benchmark every SDK module on a FRESH sim (restarts it), table -> out/zed_bench.*
#   zed.sh build | image [--force]   build the Isaac Sim extension / the bisg/zed image (once; each skips when its sources are unchanged, --force rebuilds)
#
# Typical run:   ./bisg all headless && ./bisg zed up && ./bisg zed status
set -euo pipefail
. "$(dirname "$0")/_common.sh"

sub="${1:-status}"; shift || true
passthru=(); hw=0; detach=0; video_host=""; video_port=""
while [[ $# -gt 0 ]]; do case "$1" in
  --drone) export DRONE_ID=$2; shift;;
  --hw) hw=1;;
  -d|--detach) detach=1;;
  --video-host) video_host=$2; shift;;
  --video-port) video_port=$2; shift;;
  *) passthru+=("$1");; esac; shift; done
ZNAME="bisg-zed-${DRONE_ID}"
# Port math lives with the launcher (sim/launcher/zed_sdk_cfg.py): drone N = vehicle id N-1 -> 30000 + 2*(N-1).
export ZED_SIM_PORT=$((30000 + 2 * (DRONE_ID - 1)))
# --video-host: an IPv4, or a device name on the tailnet (resolved through the tailscale service) / in DNS
video_ip(){
  [[ "$1" =~ ^[0-9]+(\.[0-9]+){3}$ ]] && { echo "$1"; return; }
  local ip=""
  container_running "$TAILSCALE_NAME" && ip="$(docker exec "$TAILSCALE_NAME" tailscale ip -4 "$1" 2>/dev/null | head -1 || true)"
  [[ -n "$ip" ]] || ip="$(getent ahostsv4 "$1" | awk '{print $1; exit}')"
  [[ -n "$ip" ]] || die "--video-host $1: not an IP, not a device on the tailnet (./bisg tailscale status), not in DNS"
  echo "$ip"
}
[[ -n "$video_host" ]] && export VIDEO_HOST="$(video_ip "$video_host")"
[[ -n "$video_port" ]] && export VIDEO_PORT=$video_port

zexec(){ docker exec "$ZNAME" bash -lc "source /workspace/docker/zed/ros_env.sh >/dev/null 2>&1; $*"; }
# best_effort: the wrapper publishes sensor-data QoS; a default (reliable) subscriber would never match it
have_frames(){ zexec "timeout 15 ros2 topic echo --once --qos-reliability best_effort --field header.stamp /drone_${DRONE_ID}/zed/zed_node/left/color/rect/image" >/dev/null 2>&1; }
svc_name(){ case $1 in wrapper|zed) echo "$ZNAME";; bridge|zed-bridge) echo "bisg-zed-bridge-${DRONE_ID}";; video|zed-video) echo "bisg-zed-video-${DRONE_ID}";; *) die "unknown service $1 (wrapper|bridge|video)";; esac; }

# (Re)start the services the YAML enables, stop the ones it disables. The wrapper is not touched.
start_services(){
  local wanted=" $(zs services --sim | tr '\n' ' ')" s
  [[ -n "$video_host" ]] && wanted+=" zed-video "      # an explicit --video-host means: stream to it
  for s in zed-bridge zed-video; do
    if [[ "$wanted" == *" $s "* ]]; then
      [[ $s == zed-bridge ]] && ! container_running "bisg-mavros-${DRONE_ID}" && warn "MAVROS for drone ${DRONE_ID} is not running (./bisg mavros up): the bridge has nowhere to send"
      compose --profile zed up -d --force-recreate "$s" >/dev/null; ok "$s started"
    else compose --profile zed rm -sf "$s" >/dev/null 2>&1 || true; fi
  done
  [[ "$wanted" == *" zed-video "* ]] && video_hint
  return 0
}
video_hint(){ info "QGC on ${VIDEO_HOST:-the host in services.qgc_video}: Application Settings > Video > Source 'UDP h.264 Video Stream', port ${VIDEO_PORT:-$(zs plan --sim | sed -n 's/.*udp:\/\/[^:]*:\([0-9]*\).*/\1/p' | head -1)}"; }

case "$sub" in
  plan) zs plan $([[ $hw == 1 ]] || echo --sim);;
  set)  zs set "${passthru[@]}";;
  build|ext-build) exec "$ROOT/docker/zed/build_isaac_ext.sh" "${passthru[@]:-}";;
  image)     exec "$ROOT/docker/zed/build.sh" "${passthru[@]:-}";;           # variant by CPU architecture

  up)
    zs plan --sim >/dev/null || die "docker/zed/zed.yaml is invalid (fix it: ./bisg zed plan)"
    docker image inspect bisg/zed:${ZED_VARIANT} >/dev/null 2>&1 || die "bisg/zed:${ZED_VARIANT} is not built: ./bisg zed image"
    container_running "$SIM_NAME" || die "the sim is not running: ./bisg up headless"
    [[ -e "/dev/shm/sl_local_video_${ZED_SIM_PORT}" ]] \
      || warn "no ZED stream segment /dev/shm/sl_local_video_${ZED_SIM_PORT} yet: the sim opens it once the timeline plays (./bisg wait)"
    for attempt in 1 2; do
      info "zed_wrapper for drone ${DRONE_ID} (stream port ${ZED_SIM_PORT}, attempt ${attempt}/2)"
      compose --profile zed up -d --force-recreate zed >/dev/null
      if (( detach )); then ok "$ZNAME started in the background (frames in ~1 min, first start ~3 min: ./bisg zed status | logs)"; start_services; exit 0; fi
      for _ in $(seq 1 45); do   # first start also compiles the depth model: allow it
        container_running "$ZNAME" && have_frames && { ok "$ZNAME publishing /drone_${DRONE_ID}/zed/zed_node/*"; break 2; }
        sleep 4
      done
      warn "no frames after ~3 min; the SDK connects once, so the next try restarts the wrapper"
      [[ $attempt == 2 ]] && { docker logs --tail 30 "$ZNAME" 2>&1 | sed 's/\x1b\[[0-9;]*m//g' | cut -c1-200 >&2
                              die "zed_wrapper never received frames — see docs/zed-sdk-sim.md 'Troubleshooting'"; }
    done
    start_services; exit 0;;

  video)    # only the video sender; any source of left/color/rect/image will do (zed_wrapper, or the sim's emulated rig)
    container_running "$SIM_NAME" || container_running "$ZNAME" || die "nothing publishes the ZED image: start the sim (./bisg up) or ./bisg zed up"
    docker image inspect bisg/zed:${ZED_VARIANT} >/dev/null 2>&1 || die "bisg/zed:${ZED_VARIANT} is not built: ./bisg zed image"
    rmem=$(sysctl -n net.core.rmem_max 2>/dev/null || echo 0)
    (( rmem >= 10485760 )) || warn "net.core.rmem_max=${rmem}: CycloneDDS cannot reassemble a camera image, the video will stay black (camera_info flows, images don't). Fix: echo 'net.core.rmem_max=16777216' | sudo tee /etc/sysctl.d/60-bisg-dds.conf && sudo sysctl --system, then ./bisg zed video again (no sudo: ZED_RMW=rmw_fastrtps_cpp ./bisg zed video)"
    compose --profile zed up -d --force-recreate zed-video >/dev/null; ok "zed-video started"; video_hint
    info "check it: ./bisg zed logs video  ('streaming: N frames' every 5 s)";;

  services) container_running "$ZNAME" || die "$ZNAME is not running (./bisg zed up)"; start_services;;   # restart only the side services (after `zed set`), wrapper untouched

  bench)
    # One wrapper, every module in turn (tests/zed_bench.py). The SDK connects once per sim run (B18), so this restarts the sim.
    window=20; extra=()
    for a in "${passthru[@]:-}"; do case "$a" in --quick) extra+=(--skip-ai --window 8);; --streaming) extra+=(--streaming);; --window) ;; "") ;; [0-9]*) window=$a;; *) die "bench: [--quick] [--streaming] [--window S]";; esac; done
    info "fresh SDK sim for the benchmark (./bisg down; ./bisg all headless)"
    "$ROOT/bisg" zed down >/dev/null 2>&1 || true; "$ROOT/bisg" down >/dev/null 2>&1 || true
    ZED_AUTOSTART=0 ROS_TOOLS_AUTOSTART=0 "$ROOT/bisg" all headless >/dev/null 2>&1 || die "sim did not come up (./bisg logs)"
    zs derive -o "$ROOT/docker/zed/.bench.yaml" \
      video.publish_rgb=true video.publish_raw=true video.publish_gray=true video.publish_stereo=true \
      sensors.publish_imu_raw=true sensors.publish_cam_imu_transf=true \
      depth.publish_depth_confidence=true depth.publish_disparity=true depth.publish_depth_info=true \
      region_of_interest.enabled=true region_of_interest.publish_roi_mask=true \
      positional_tracking.publish_pose_cov=true positional_tracking.publish_cam_path=true positional_tracking.publish_3d_landmarks=true \
      plane_detection.enabled=true >/dev/null
    export ZED_STACK_CONFIG=docker/zed/.bench.yaml
    "$0" up --drone "$DRONE_ID" >/dev/null 2>&1 || die "zed up failed on the bench config"
    mkdir -p "$ROOT/out"
    zexec "cd /workspace && mkdir -p /tmp/o && python3 tests/zed_bench.py --drone ${DRONE_ID} --window ${window} ${extra[*]:-} --json /tmp/o/zed_bench.json" 2>&1 | grep -v '^\[WARN\]' | tee "$ROOT/out/zed_bench.txt"
    docker cp "$ZNAME:/tmp/o/zed_bench.json" "$ROOT/out/zed_bench.json" 2>/dev/null && ok "out/zed_bench.json"
    docker stats --no-stream --format '  {{.Name}}: cpu {{.CPUPerc}}  mem {{.MemUsage}}' "$ZNAME" "bisg-zed-bridge-${DRONE_ID}" 2>/dev/null
    unset ZED_STACK_CONFIG; "$ROOT/bisg" zed down >/dev/null 2>&1 || true; info "sim left running; ./bisg down to stop";;

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
      docker exec "$bn" bash -lc "source /workspace/docker/zed/ros_env.sh >/dev/null 2>&1; timeout 6 ros2 topic echo --once --field data /drone_${DRONE_ID}/zed_stack/status" 2>/dev/null \
        | sed "s/^'//; s/'\$//; s/^data: //" | grep -m1 '^{' \
        | python3 -c 'import json,sys
for l in sys.stdin:
    d=json.loads(l); print("  bridge state:", d["state"])
    for k,v in d["components"].items(): print("   %-18s %-9s %s" % (k, v["state"], {a:b for a,b in v.items() if a!="state"}))' \
        || warn "no zed_stack/status yet (is the health module on?)"
    else info "px4 bridge not running (services.px4_bridge in docker/zed/zed.yaml)"; fi
    container_running "$(svc_name video)" && ok "$(svc_name video) running"
    true;;

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

  *) sed -n 2,20p "$0"; exit 2;;
esac
