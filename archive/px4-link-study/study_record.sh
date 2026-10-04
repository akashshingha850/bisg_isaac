#!/usr/bin/env bash
# Record one study dataset: sim (real ZED SDK) in a given world, scripted flight, SVO + truth.   docs/study-vo-perception.md
#   scripts/study_record.sh <name> "<World preset>" [flight-scale]      e.g.  scripts/study_record.sh d2 "Full Warehouse"
# Output: logs/study/<name>/{flight.svo2,truth.csv,clock.csv,odom_live.csv,frames.csv,marks.log,calib.json}
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"; cd "$ROOT"
NAME="$1"; WORLD="$2"; SCALE="${3:-1.0}"
OUT="logs/study/$NAME"; rm -rf "$OUT"; mkdir -p "$OUT"
CFG="sim/configs/study_zed.yaml"; TMP="sim/configs/_study_$NAME.yaml"
sed "s/preset: \"Warehouse\"/preset: \"$WORLD\"/" "$CFG" > "$TMP"
trap 'rm -f "$TMP"; ./bisg zed down >/dev/null 2>&1 || true' EXIT
docker rm -f bisg-zed-1 >/dev/null 2>&1 || true
ZED_SOURCE=sdk ./bisg restart headless -c "$TMP" >/dev/null 2>&1
ZED_SOURCE=sdk ./bisg wait >/dev/null 2>&1
./bisg zed up >/dev/null 2>&1
docker exec bisg-zed-1 bash -c "rm -rf /tmp/study/$NAME; mkdir -p /tmp/study/$NAME"
docker exec -d bisg-zed-1 bash -lc "source /sbin/ros_entrypoint.sh >/dev/null 2>&1; python3 /workspace/tests/study/record_run.py --out /tmp/study/$NAME --svo /tmp/study/$NAME/flight.svo2 > /tmp/study/$NAME/rec.log 2>&1"
sleep 8
docker exec -i bisg-sim /isaac-sim/python.sh - --profile full --scale "$SCALE" < tests/study/fly_profile.py | tee "$OUT/marks.log"
sleep 2
docker logs bisg-zed-1 > "$OUT/zed.log" 2>&1 || true
docker exec bisg-zed-1 touch "/tmp/study/$NAME/STOP"; sleep 10
docker cp "bisg-zed-1:/tmp/study/$NAME/." "$OUT/"
echo "recorded $OUT"
