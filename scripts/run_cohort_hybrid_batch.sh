#!/usr/bin/env bash
# Run full cohort hybrid diarization (safe for long nohup sessions).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
mkdir -p logs
export PYTHONUNBUFFERED=1
exec .venv-hybrid/bin/python -u scripts/hybrid_diarization.py \
  --skip-existing \
  --whisper-model small \
  --device cpu \
  --compute-type int8 \
  --batch-size 4 \
  "$@"
