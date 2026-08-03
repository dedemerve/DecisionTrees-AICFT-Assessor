#!/usr/bin/env bash
# Launch post-batch orchestrator (waits for active extraction, then fix rounds).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs/pipeline_runs
exec caffeinate -i "$ROOT/.venv-hybrid/bin/python" -u scripts/orchestrator_complete_extraction.py \
  >> logs/pipeline_runs/orchestrator_complete.log 2>&1
