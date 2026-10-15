#!/usr/bin/env bash
# ZED VIO calibration + benchmark + ablation on this machine (docs/vio.md). Usually called through ./bisg.
#
#   vio.sh bench [--configs a,b] [--reps N] [--view V] [--resume DIR] [--archive] [--leave-up]
#                 fresh sim per flight, every config of tests/vio_bench.yaml x reps; results + verdict in
#                 $ARCHIVE_DIR/vio_bench/<date>-<host>/ (summary.md, figures/). Restarts the sim. ~6.5 min per flight
#   vio.sh check  quick "is the VIO right on this PC": bench --configs calibrated --reps 1
#   vio.sh report DIR            rebuild summary + verdict from a campaign dir (stdlib python only)
#   vio.sh eval ULG|NPZ [OUT]    tests/vio_eval.py on one PX4 log / archived extract
#   vio.sh list                  campaigns under $ARCHIVE_DIR/vio_bench with their verdicts
set -euo pipefail
. "$(dirname "$0")/_common.sh"

BENCH_ROOT="${ARCHIVE_DIR/#\~/$HOME}/vio_bench"
sub="${1:-help}"; shift || true
case "$sub" in
  bench) exec python3 "$ROOT/tests/vio_campaign.py" --root "$BENCH_ROOT" "$@";;
  check) exec python3 "$ROOT/tests/vio_campaign.py" --root "$BENCH_ROOT" --configs calibrated --reps 1 "$@";;
  report) [[ $# -ge 1 ]] || die "report: give a campaign dir (./bisg vio list)"; exec python3 "$ROOT/tests/vio_report.py" "$1";;
  eval)
    [[ $# -ge 1 ]] || die "eval: give a .ulg or a topics.npz"
    src="$1"; out="${2:-$(dirname "$src")}"; kind=--ulog; [[ "$src" == *.npz ]] && kind=--npz
    exec python3 "$ROOT/tests/vio_eval.py" "$kind" "$src" --out "$out" --series;;
  list)
    for d in "$BENCH_ROOT"/*/; do [[ -d "$d" ]] || continue
      v=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['verdict'])" "$d/summary.json" 2>/dev/null || echo "(no report)")
      echo "$v  $d"; done;;
  -h|--help|help) sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//';;
  *) die "unknown: vio $sub (bench|check|report|eval|list)";;
esac
