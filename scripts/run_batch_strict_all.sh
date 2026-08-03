#!/usr/bin/env bash
# Strict MMLA extraction for 21 April, 28 April, and 5 May cohorts.
# Amy (21 April) is skipped automatically when quality gate passes.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p logs/pipeline_runs
LOG=logs/pipeline_runs/batch_strict_cohorts_$(date +%Y%m%d_%H%M%S).log
echo "Logging to $LOG"
exec caffeinate -i .venv-hybrid/bin/python -u scripts/batch_extract_strict_cohorts.py -v \
  "$@" 2>&1 | tee -a "$LOG"
