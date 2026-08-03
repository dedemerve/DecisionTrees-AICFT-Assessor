#!/usr/bin/env bash
# Full May Colab Python pipeline: extract (audio+video) → transcribe → validate → hybrid → labeled.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
HYBRID_PYTHON="${HYBRID_PYTHON:-$ROOT/.venv-hybrid/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="${PYTHON_FALLBACK:-python3}"
fi
if [[ ! -x "$HYBRID_PYTHON" ]]; then
  HYBRID_PYTHON="$PYTHON"
fi

INPUT="${INPUT:-$ROOT/data_sources_2026/05 May Colab Python Screen Recordings}"
AUDIO_ROOT="${AUDIO_ROOT:-$ROOT/data_sources_2026/colab_may_audio}"
STUDENTS=("$@")

echo "== Colab May Python pipeline =="
echo "input: $INPUT"
echo "audio_root: $AUDIO_ROOT"

extract_args=(--input "$INPUT" --output "$AUDIO_ROOT")
transcribe_args=(--audio-root "$AUDIO_ROOT")
COLAB_PROMPT="$("$PYTHON" -c "import sys; sys.path.insert(0,'$ROOT/scripts'); from transcribe_screen_recording_audio import COLAB_INITIAL_PROMPT; print(COLAB_INITIAL_PROMPT)")"
transcribe_args+=(--initial-prompt "$COLAB_PROMPT")
if [[ ${#STUDENTS[@]} -gt 0 ]]; then
  extract_args+=("${STUDENTS[@]}")
  transcribe_args+=("${STUDENTS[@]}")
fi

echo "-- [1/6] extract audio + video"
python3 scripts/extract_screen_recording_audio.py "${extract_args[@]}"

echo "-- [2/6] transcribe (mlx large-v3)"
"$PYTHON" scripts/transcribe_screen_recording_audio.py "${transcribe_args[@]}"

echo "-- [3/6] validate + fix silent/hallucinated"
"$HYBRID_PYTHON" scripts/validate_screen_recording_transcripts.py --audio-root "$AUDIO_ROOT" || true
"$HYBRID_PYTHON" scripts/fix_screen_recording_transcripts.py --audio-root "$AUDIO_ROOT" || true
"$HYBRID_PYTHON" scripts/validate_screen_recording_transcripts.py --audio-root "$AUDIO_ROOT" \
  --report "$AUDIO_ROOT/transcript_validation_report.json" || true

echo "-- [4/6] hybrid diarization"
"$HYBRID_PYTHON" scripts/hybrid_diarization.py --audio-root "$AUDIO_ROOT" --skip-existing \
  --whisper-model small --device cpu --compute-type int8 --batch-size 4 \
  "${STUDENTS[@]}"

echo "-- [5/6] normalize hybrid v2"
"$HYBRID_PYTHON" scripts/normalize_hybrid_diarization.py --audio-root "$AUDIO_ROOT" "${STUDENTS[@]}"

echo "-- [6/6] speaker labeling"
"$HYBRID_PYTHON" scripts/apply_merged_speaker_labels.py --audio-root "$AUDIO_ROOT" "${STUDENTS[@]}"
"$HYBRID_PYTHON" scripts/speaker_labeling_qa.py --audio-root "$AUDIO_ROOT" "${STUDENTS[@]}"

echo "-- [7/7] finalize audit + metadata"
"$HYBRID_PYTHON" scripts/finalize_colab_may_cohort.py --skip-validate
"$HYBRID_PYTHON" scripts/validate_screen_recording_transcripts.py --audio-root "$AUDIO_ROOT" \
  --report "$AUDIO_ROOT/transcript_validation_report.json" || true

echo "== done: $AUDIO_ROOT/*_transcript_labeled.json =="
