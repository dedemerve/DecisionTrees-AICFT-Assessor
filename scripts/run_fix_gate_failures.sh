#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs/pipeline_runs
exec caffeinate -i "$ROOT/.venv-hybrid/bin/python" -u scripts/fix_gate_failures.py -v \
  --plan logs/pipeline_runs/fix_gate_failures_plan_20260711_115109.json \
  >> logs/pipeline_runs/fix_gate_failures.log 2>&1
