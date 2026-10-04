#!/usr/bin/env bash
# Analysis of a study run (numpy/scipy/matplotlib come from the Isaac image). docs/study-vo-perception.md
#   scripts/study_analyze.sh logs/study/d1
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN="${1%/}"
exec docker run --rm --user 0 -e HOME=/tmp -v "$ROOT":/workspace -w /workspace --entrypoint bash bisg/sim:6.0.0 \
  -c "/isaac-sim/python.sh tests/study/analyze.py $* ; chown -R $(id -u):$(id -g) $RUN/analysis"
