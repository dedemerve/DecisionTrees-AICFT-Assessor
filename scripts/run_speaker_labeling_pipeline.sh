#!/usr/bin/env bash
# Full free speaker-labeling pipeline for codap_arbor_21april cohort.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-$ROOT/.venv-hybrid/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="${PYTHON_FALLBACK:-python3}"
fi

AUDIO_ROOT="${AUDIO_ROOT:-data_sources_2026/codap_arbor_21april_audio}"
FORCE="${FORCE:-0}"
STUDENTS=("$@")

echo "== speaker labeling pipeline =="
echo "python: $PYTHON"
echo "audio_root: $AUDIO_ROOT"

echo "-- [1/5] validate transcripts"
"$PYTHON" scripts/validate_screen_recording_transcripts.py --audio-root "$AUDIO_ROOT" || true

echo "-- [2/5] audit no_speech audio"
"$PYTHON" scripts/audit_no_speech_audio.py --audio-root "$AUDIO_ROOT"

if [[ ${#STUDENTS[@]} -eq 0 ]]; then
  echo "-- [3/5] merge hybrid diarization -> *_transcript_labeled.json"
  "$PYTHON" scripts/apply_merged_speaker_labels.py --audio-root "$AUDIO_ROOT"
  echo "-- [4/5] QA reports"
  "$PYTHON" scripts/speaker_labeling_qa.py --audio-root "$AUDIO_ROOT"
  echo "-- [5/5] gold bootstrap + metrics + review manifest"
  "$PYTHON" scripts/evaluate_speaker_gold.py --bootstrap-template --audio-root "$AUDIO_ROOT"
  "$PYTHON" scripts/evaluate_speaker_gold.py --audio-root "$AUDIO_ROOT"
  "$PYTHON" scripts/export_speaker_review_clips.py --audio-root "$AUDIO_ROOT"
else
  echo "-- [3/5] merge hybrid diarization -> *_transcript_labeled.json"
  "$PYTHON" scripts/apply_merged_speaker_labels.py --audio-root "$AUDIO_ROOT" "${STUDENTS[@]}"
  echo "-- [4/5] QA reports"
  "$PYTHON" scripts/speaker_labeling_qa.py --audio-root "$AUDIO_ROOT" "${STUDENTS[@]}"
  echo "-- [5/5] gold bootstrap + metrics + review manifest"
  "$PYTHON" scripts/evaluate_speaker_gold.py --bootstrap-template --audio-root "$AUDIO_ROOT"
  "$PYTHON" scripts/evaluate_speaker_gold.py --audio-root "$AUDIO_ROOT"
  "$PYTHON" scripts/export_speaker_review_clips.py --audio-root "$AUDIO_ROOT" "${STUDENTS[@]}"
fi

echo "== done =="
echo "logs/speaker_labeling_qa_summary.json"
echo "logs/speaker_labeling_baseline_metrics.json"
echo "logs/no_speech_audio_audit.json"
