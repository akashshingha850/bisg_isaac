#!/usr/bin/env bash
# Perception backend control (docs/perception.md).
#   perception.sh build                         build the bisg/perception image (Isaac ROS 4.6 + CPU baselines, ~14 GB)
#   perception.sh up [mock|isaac_ros|ros2] [--observer]   start a backend for DRONE_ID (default: PERCEPTION_BACKEND from config)
#   perception.sh down                          stop whichever backend runs (perception service and/or vio_mock)
#   perception.sh status                        which backend is up and what it publishes
#   perception.sh bench [isaac_ros|ros2|all] [-c scenario]   boot the sim, fly the same VIO flight, score each backend
#   perception.sh report                        merge logs/perception/*.json into one Markdown table
# `./bisg all` honours PERCEPTION_BACKEND too. --observer = the backend does NOT feed MAVROS (evaluate without influencing).
set -euo pipefail
. "$(dirname "$0")/_common.sh"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PERC="bisg-perception-${DRONE_ID}"
OUT="$ROOT/logs/perception"
BENCH_SCENARIO_DEFAULT=single_iris_vio_lowres

container_running(){ [[ "$(docker inspect -f '{{.State.Running}}' "$1" 2>/dev/null)" == true ]]; }
ros_exec(){ docker exec "$ROS_NAME" bash -lc "source /opt/ros/jazzy/setup.bash; [ -f /workspace/ros2_ws/install/setup.bash ] && source /workspace/ros2_ws/install/setup.bash; $*"; }
perc_exec(){ docker exec "$PERC" bash -lc "source /opt/ros/jazzy/setup.bash; source /workspace/ros2_ws/install/setup.bash; $*"; }
backend_ok(){ [[ "$1" =~ ^(mock|isaac_ros|ros2)$ ]] || die "PERCEPTION_BACKEND must be mock | isaac_ros | ros2 (got '$1')"; }

cmd_build(){ info "building bisg/perception (ISAAC_ROS_RELEASE=${ISAAC_ROS_RELEASE})"; compose --profile perception build perception; ok "bisg/perception:jazzy"; }

cmd_up(){
  local b="${PERCEPTION_BACKEND}" feed=true
  while [[ $# -gt 0 ]]; do case "$1" in --observer) feed=false;; mock|isaac_ros|ros2) b=$1;; *) die "up: [mock|isaac_ros|ros2] [--observer]";; esac; shift; done
  backend_ok "$b"
  docker image inspect bisg/perception:jazzy >/dev/null 2>&1 || [[ "$b" == mock ]] || die "bisg/perception:jazzy is not built: ./bisg perception build"
  if [[ "$b" == mock ]]; then
    compose --profile perception stop perception >/dev/null 2>&1 || true
    compose --profile ros up -d vehicle >/dev/null; ok "backend mock: vio_mock up (ground truth + noise)"
  else
    [[ "$feed" == true ]] && compose --profile ros stop vehicle >/dev/null 2>&1   # one vision source into MAVROS, never two
    [[ "$feed" == true ]] && compose --profile ros rm -f vehicle >/dev/null 2>&1
    PERCEPTION_BACKEND_RUN="$b" PERCEPTION_FEED_MAVROS="$feed" compose --profile perception up -d --force-recreate perception >/dev/null
    ok "backend $b up for /drone_${DRONE_ID} (feed_mavros=$feed, depth=${PERCEPTION_DEPTH}, imu=${PERCEPTION_IMU})  logs: docker logs -f $PERC"
  fi
}
cmd_down(){ compose --profile perception stop perception >/dev/null 2>&1 || true; compose --profile perception rm -f perception >/dev/null 2>&1 || true
            compose --profile ros stop vehicle >/dev/null 2>&1 || true; ok "perception backends stopped"; }
cmd_status(){
  info "perception (config: PERCEPTION_BACKEND=${PERCEPTION_BACKEND}, depth=${PERCEPTION_DEPTH}, imu=${PERCEPTION_IMU})"
  container_running "bisg-vehicle-${DRONE_ID}" && ok "mock: bisg-vehicle-${DRONE_ID} (vio_mock) running"
  if container_running "$PERC"; then
    ok "$PERC running: $(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "$PERC" | grep -E '^PERCEPTION_(BACKEND|FEED_MAVROS)=' | tr '\n' ' ')"
    container_running "$ROS_NAME" && ros_exec "for t in perception/odom perception/disparity zed/zed_node/odom; do echo -n \"  /drone_${DRONE_ID}/\$t  \"; timeout 6 ros2 topic hz /drone_${DRONE_ID}/\$t 2>&1 | grep -m1 'average rate' || echo '(none)'; done"
  else warn "$PERC is not running"; fi
}

SAMPLER_PID=""
bench_one(){
  local b=$1 scen=$2 tag="$3" ts; ts=$(date +%Y%m%d_%H%M%S)
  mkdir -p "$OUT"
  info "bench [$b] boot sim + MAVROS + vio_mock (the mock flies; $b only observes) scenario=$scen"
  "$ROOT/bisg" down >/dev/null 2>&1 || true
  SIM_SCENARIO="$scen" PERCEPTION_BACKEND=mock "$ROOT/bisg" all headless >/dev/null 2>&1 || die "sim did not come up (./bisg all headless)"
  sleep 5
  PERCEPTION_BACKEND_RUN="$b" PERCEPTION_FEED_MAVROS=false compose --profile perception up -d --force-recreate perception >/dev/null
  info "bench [$b] warm-up 25 s"; sleep 25
  docker logs "$PERC" 2>&1 | grep -iE "error|exception|failed" | head -5 || true
  local stop="/tmp/bisg_sample_stop_$$" marker="/tmp/bisg_bench_marker_$$"; rm -f "$stop"; touch "$marker"
  python3 "$HERE/perception_sample.py" "$OUT/${b}_${tag}_${ts}.resources.json" --stop-file "$stop" \
      --containers "$PERC,$SIM_NAME" --perception "$PERC" --period 2 &
  SAMPLER_PID=$!
  docker exec -d "$PERC" bash -lc "source /opt/ros/jazzy/setup.bash; source /workspace/ros2_ws/install/setup.bash; \
      /usr/local/bin/perception-entrypoint.sh bench -p tag:=${tag} -p max_wall_s:=420.0 > /workspace/logs/perception/${b}_${tag}_${ts}.bench.log 2>&1"
  sleep 3
  info "bench [$b] flying vio_flight (mock-fed)"
  ros_exec "python3 /workspace/tests/vio_flight.py --drone ${DRONE_ID}" > "$OUT/${b}_${tag}_${ts}.flight.log" 2>&1 && ok "flight PASS" || warn "flight did not pass: $OUT/${b}_${tag}_${ts}.flight.log"
  for _ in $(seq 1 30); do [[ -n "$(find "$OUT" -maxdepth 1 -name "${b}_${tag}_*.json" ! -name '*resources*' -newer "$marker" 2>/dev/null)" ]] && break; sleep 2; done
  touch "$stop"; wait "$SAMPLER_PID" 2>/dev/null || true; rm -f "$stop"
  docker logs "$PERC" > "$OUT/${b}_${tag}_${ts}.backend.log" 2>&1 || true
  compose --profile perception stop perception >/dev/null 2>&1; compose --profile perception rm -f perception >/dev/null 2>&1
  "$ROOT/bisg" down >/dev/null 2>&1 || true
  ok "bench [$b] done -> $OUT/${b}_${tag}_${ts}.*"
}
cmd_bench(){
  local which=all scen="$BENCH_SCENARIO_DEFAULT" tag=""
  while [[ $# -gt 0 ]]; do case "$1" in -c) scen=$2; shift;; --tag) tag=$2; shift;; isaac_ros|ros2|all) which=$1;; *) die "bench: [isaac_ros|ros2|all] [-c scenario] [--tag name]";; esac; shift; done
  docker image inspect bisg/perception:jazzy >/dev/null 2>&1 || die "bisg/perception:jazzy is not built: ./bisg perception build"
  [[ -f "$ROOT/ros2_ws/install/setup.bash" ]] || die "ros2_ws is not built: ./bisg ros build"
  [[ -n "$tag" ]] || tag="$scen"
  local rmem; rmem=$(sysctl -n net.core.rmem_max 2>/dev/null || echo 0)
  (( rmem >= 8000000 )) || warn "net.core.rmem_max=${rmem}: HD720 images will not reach the backends (bugs.md B2). Use a low-res scenario or: sudo sysctl -w net.core.rmem_max=16777216"
  for b in $([[ $which == all ]] && echo "ros2 isaac_ros" || echo "$which"); do bench_one "$b" "$scen" "$tag"; done
  cmd_report
}
cmd_report(){ python3 "$HERE/perception_report.py" "$OUT"; }

backend_ok "$PERCEPTION_BACKEND"
case "${1:-status}" in
  build) cmd_build;; up) shift; cmd_up "$@";; down) cmd_down;; status) cmd_status;; bench) shift; cmd_bench "$@";; report) cmd_report;;
  -h|--help|help) sed -n 2,11p "$0";; *) die "perception: build|up|down|status|bench|report";;
esac
