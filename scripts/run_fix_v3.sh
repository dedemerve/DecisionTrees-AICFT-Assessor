#!/usr/bin/env bash
# Re-extract all students that still fail gate (v3: Colab guard + 90s gap-fill).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p calibration/colab_task_templates logs/pipeline_runs

echo ">>> Seeding Colab templates..."
"$ROOT/.venv-hybrid/bin/python" scripts/seed_colab_task_templates.py || true

echo ">>> Re-extracting gate failures (v3)..."
exec caffeinate -i "$ROOT/.venv-hybrid/bin/python" -u scripts/fix_gate_failures.py -v \
  --plan logs/pipeline_runs/fix_gate_failures_plan_v3.json \
  >> logs/pipeline_runs/fix_gate_failures_v3.log 2>&1
