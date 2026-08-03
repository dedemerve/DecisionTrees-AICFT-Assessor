#!/usr/bin/env bash
# Full CODAP Arbor 28 April pipeline: extract → transcribe → validate → hybrid → labeled.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-$ROOT/.venv-hybrid/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="${PYTHON_FALLBACK:-python3}"
fi

INPUT="${INPUT:-$ROOT/data_sources_2026/28 April CODAP Arbor Screen Recordings}"
AUDIO_ROOT="${AUDIO_ROOT:-$ROOT/data_sources_2026/codap_arbor_28april_audio}"
STUDENTS=("$@")

echo "== CODAP 28 April pipeline =="
echo "input: $INPUT"
echo "audio_root: $AUDIO_ROOT"

extract_args=(--input "$INPUT" --output "$AUDIO_ROOT")
transcribe_args=(--audio-root "$AUDIO_ROOT")
if [[ ${#STUDENTS[@]} -gt 0 ]]; then
  extract_args+=("${STUDENTS[@]}")
  transcribe_args+=("${STUDENTS[@]}")
fi

echo "-- [1/6] extract audio"
python3 scripts/extract_screen_recording_audio.py "${extract_args[@]}"

echo "-- [2/6] transcribe (mlx large-v3)"
"$PYTHON" scripts/transcribe_screen_recording_audio.py "${transcribe_args[@]}"

echo "-- [3/6] validate + fix silent/hallucinated"
"$PYTHON" scripts/validate_screen_recording_transcripts.py --audio-root "$AUDIO_ROOT" || true
"$PYTHON" scripts/fix_screen_recording_transcripts.py --audio-root "$AUDIO_ROOT" || true
"$PYTHON" scripts/validate_screen_recording_transcripts.py --audio-root "$AUDIO_ROOT" \
  --report "$AUDIO_ROOT/transcript_validation_report.json" || true

echo "-- [4/6] hybrid diarization"
"$PYTHON" scripts/hybrid_diarization.py --audio-root "$AUDIO_ROOT" --skip-existing \
  --whisper-model small --device cpu --compute-type int8 --batch-size 4 \
  "${STUDENTS[@]}"

echo "-- [5/6] normalize hybrid v2"
"$PYTHON" scripts/normalize_hybrid_diarization.py --audio-root "$AUDIO_ROOT" "${STUDENTS[@]}"

echo "-- [6/6] speaker labeling"
AUDIO_ROOT="$AUDIO_ROOT" "$PYTHON" scripts/apply_merged_speaker_labels.py --audio-root "$AUDIO_ROOT" "${STUDENTS[@]}"
"$PYTHON" scripts/speaker_labeling_qa.py --audio-root "$AUDIO_ROOT" "${STUDENTS[@]}"

echo "== done: $AUDIO_ROOT/*_transcript_labeled.json =="
