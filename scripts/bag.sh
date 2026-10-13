#!/usr/bin/env bash
# rosbag2 recording of the running stack, for debugging. Topic sets and the on/off switch: docker/ros/bag.yaml.
# Bags (MCAP) go to $BAG_DIR (config/bisg.conf, default $ARCHIVE_DIR/bags); the recorder runs in bisg-ros as this user.
#
#   bag.sh [status]                 enabled?, default profile, the running recording, $BAG_DIR
#   bag.sh enable | disable         record automatically once the sim is ready (./bisg up | all | wait)
#   bag.sh start [PROFILE] [NAME]   start recording now (default profile from bag.yaml); NAME is appended to the bag name
#   bag.sh stop                     close the running bag cleanly (SIGINT: the MCAP footer is written)
#   bag.sh profiles                 the topic sets in bag.yaml (* = default)
#   bag.sh list                     bags in $BAG_DIR, newest last
#   bag.sh info [BAG]               `ros2 bag info` (default: the newest bag)
#   bag.sh play BAG [ARGS..]        `ros2 bag play` in bisg-ros (stop the sim first: replayed /clock and topics collide with live ones)
#   bag.sh autostart                (internal) start if enabled and not running; used when the sim becomes ready
set -euo pipefail
. "$(dirname "$0")/_common.sh"

RB="$ROOT/scripts/ros_bag.py"
PIDF=/tmp/bisg-bag.pid
NAMEF=/tmp/bisg-bag.name

ros_up(){
  container_running "$ROS_NAME" || { compose --profile tools up -d ros >/dev/null && ok "ros started"; }
  docker exec "$ROS_NAME" test -d /bags || die "bisg-ros has no /bags mount (an old container): ./bisg ros down && ./bisg ros up"
}
running(){ container_running "$ROS_NAME" && docker exec "$ROS_NAME" bash -c "kill -0 \$(cat $PIDF 2>/dev/null) 2>/dev/null"; }
current(){ docker exec "$ROS_NAME" cat "$NAMEF" 2>/dev/null; }
newest(){ ls -1d "$BAG_DIR"/*/ 2>/dev/null | tail -1 | xargs -r basename; }
resolve(){   # a bag name in $BAG_DIR or a path under it -> the container path
  local b="${1:-$(newest)}"; [[ -n "$b" ]] || die "no bags in $BAG_DIR"
  b="${b%/}"; b="${b#"$BAG_DIR"/}"; [[ -e "$BAG_DIR/$b" ]] || die "no bag $BAG_DIR/$b"
  echo "/bags/$b"
}

start(){
  local profile="${1:-$("$RB" profile)}" tag="${2:-}" name line
  running && { ok "already recording: $(current) (./bisg bag stop first)"; return 0; }
  ros_up
  name="$(date +%Y%m%d-%H%M%S)_${profile}${tag:+_$tag}"
  line=$("$RB" cmd "$profile" "/bags/$name") || exit 1
  mkdir -p "$BAG_DIR"
  docker exec -d -u "$(id -u):$(id -g)" -e HOME=/tmp -e ROS_LOG_DIR=/tmp/bisg-bag-log "$ROS_NAME" bash -c \
    "source /opt/ros/jazzy/setup.bash; echo \$\$ >$PIDF; echo $name >$NAMEF; exec $line >/tmp/bisg-bag.log 2>&1"
  sleep 3
  running || { docker exec "$ROS_NAME" tail -5 /tmp/bisg-bag.log >&2 || true; die "the recorder exited (log above)"; }
  ok "recording '$profile' -> $BAG_DIR/$name   (stop: ./bisg bag stop; log: docker exec $ROS_NAME cat /tmp/bisg-bag.log)"
}

stop(){
  running || { info "no bag recording"; return 0; }
  local name; name=$(current)
  # SIGINT = ros2 bag's own Ctrl-C path: flushes the cache and writes the MCAP footer + metadata.yaml
  docker exec "$ROS_NAME" bash -c "p=\$(cat $PIDF); kill -INT \$p; for i in \$(seq 1 40); do kill -0 \$p 2>/dev/null || exit 0; sleep 0.5; done; kill -TERM \$p"
  docker exec "$ROS_NAME" rm -f "$PIDF" "$NAMEF"
  ok "bag closed: $BAG_DIR/$name ($(du -sh "$BAG_DIR/$name" 2>/dev/null | cut -f1))"
}

status(){
  "$RB" enabled && echo "  autostart  enabled  (./bisg bag disable)" || echo "  autostart  disabled (./bisg bag enable)"
  echo "  profile    $("$RB" profile)   (./bisg bag profiles)"
  echo "  bag dir    $BAG_DIR"
  if running; then local n; n=$(current); echo "  recording  $n  $(du -sh "$BAG_DIR/$n" 2>/dev/null | cut -f1)"
  else echo "  recording  no"; fi
}

case "${1:-status}" in
  status) status;;
  enable|disable) "$RB" set "$([[ $1 == enable ]] && echo on || echo off)"
      ok "bag autostart ${1}d in docker/ros/bag.yaml$([[ $1 == enable ]] && ! running && echo ' (starts with the next sim; now: ./bisg bag start)')";;
  start) shift; start "${1:-}" "${2:-}";;
  stop) stop;;
  restart) shift; stop; start "${1:-}" "${2:-}";;
  profiles) "$RB" profiles;;
  list) ls -1d "$BAG_DIR"/*/ 2>/dev/null | while read -r d; do printf '  %-48s %s\n' "$(basename "$d")" "$(du -sh "$d" | cut -f1)"; done
        [[ -n "$(newest)" ]] || info "no bags in $BAG_DIR";;
  info) shift; b=$(resolve "${1:-}"); ros_up; docker exec "$ROS_NAME" bash -c "source /opt/ros/jazzy/setup.bash; ros2 bag info $b";;
  play) shift; b=$(resolve "${1:?play BAG [ros2 bag play args]}"); shift
        container_running "$SIM_NAME" && warn "the sim is running: replayed topics and /clock will mix with the live ones"
        ros_up; docker exec -it -u "$(id -u):$(id -g)" -e HOME=/tmp "$ROS_NAME" bash -c "source /opt/ros/jazzy/setup.bash; ros2 bag play $b --clock $*";;
  autostart) "$RB" enabled && ! running && start || true;;
  *) die "bag: status|enable|disable|start [PROFILE] [NAME]|stop|restart|profiles|list|info [BAG]|play BAG";;
esac
