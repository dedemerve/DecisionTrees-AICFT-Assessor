#!/usr/bin/env bash
# 21 April CODAP Arbor — transcript-fused local hybrid diarization cohort run.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-$ROOT/.venv-hybrid/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="${PYTHON_FALLBACK:-python3}"
fi

AUDIO_ROOT="${AUDIO_ROOT:-data_sources_2026/codap_arbor_21april_audio}"
LOG_FILE="${LOG_FILE:-logs/21april_diarization_run.log}"
mkdir -p "$(dirname "$LOG_FILE")"

export PYTHONUNBUFFERED=1

echo "== 21 April CODAP hybrid diarization =="
echo "python:     $PYTHON"
echo "audio_root: $AUDIO_ROOT"
echo "log:        $LOG_FILE"
echo "started:    $(date -u +%Y-%m-%dT%H:%M:%SZ)"

"$PYTHON" -u scripts/hybrid_diarization.py \
  --audio-root "$AUDIO_ROOT" \
  --fuse-existing-transcript \
  --local-diarization-only \
  --device cpu \
  --min-speakers 2 \
  --max-speakers 8 \
  --skip-existing \
  -v \
  "$@" 2>&1 | tee "$LOG_FILE"

echo "finished:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "== cohort status =="
bash scripts/cohort_hybrid_status.sh
