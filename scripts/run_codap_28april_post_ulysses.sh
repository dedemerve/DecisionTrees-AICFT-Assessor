#!/usr/bin/env bash
# Run after Ulysses mlx transcribe finishes: hybrid → normalize → labeled.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
AUDIO="$ROOT/data_sources_2026/codap_arbor_28april_audio"
PY="${PY:-$ROOT/.venv/bin/python}"
HYB="${HYB:-$ROOT/.venv-hybrid/bin/python}"
LOG="$ROOT/logs/codap_28april_ulysses_post.log"

exec > >(tee -a "$LOG") 2>&1
echo "== post-Ulysses labeling $(date -u +%Y-%m-%dT%H:%M:%SZ) =="

"$PY" scripts/validate_screen_recording_transcripts.py --audio-root "$AUDIO"
"$HYB" scripts/hybrid_diarization.py --audio-root "$AUDIO" Ulysses \
  --whisper-model small --device cpu --compute-type int8 --batch-size 4
"$PY" scripts/normalize_hybrid_diarization.py --audio-root "$AUDIO" Ulysses
"$PY" scripts/apply_merged_speaker_labels.py --audio-root "$AUDIO" Ulysses
"$PY" scripts/speaker_labeling_qa.py --audio-root "$AUDIO" Ulysses

echo "== done: $AUDIO/Ulysses/Ulysses_transcript_labeled.json =="
