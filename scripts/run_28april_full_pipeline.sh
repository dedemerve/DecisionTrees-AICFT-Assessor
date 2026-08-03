#!/usr/bin/env bash
# Full MMLA pipeline for 28 April CODAP Arbor cohort:
#   1. Diarization   — hybrid_diarization.py (whisperx, ~5-15 min per student)
#   2. Re-extraction — dynamic_video_analytics.py (full_multimodal mode)
#   3. Frame analysis — codap_frame_analyzer.py (vision API)
#
# Prerequisites:
#   export ANTHROPIC_API_KEY=...    (or --provider openai + OPENAI_API_KEY)
#   .venv-hybrid must have whisperx, pyannote, noisereduce installed
#
# Usage:
#   bash scripts/run_28april_full_pipeline.sh            # all students
#   bash scripts/run_28april_full_pipeline.sh Irma Nadia  # specific students

set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$REPO/.venv-hybrid/bin/python"
AUDIO_ROOT="$REPO/data_sources_2026/codap_arbor_28april_audio"
VIDEO_ROOT="$REPO/data_sources_2026/28 April CODAP Arbor Screen Recordings"
LOG_CSV="$REPO/data_sources_2026/All Documents/28 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv"
SESSION_DATE="2026-04-28"
SESSION_LABEL="28_Nisan_2026_CODAP"

# Build student list
if [ $# -gt 0 ]; then
    STUDENTS=("$@")
else
    STUDENTS=(Bruno Irma Isabel Marco Melinda Nadia Serena Ulysses Zara)
fi

echo "=== Step 1: Diarization ==="
for SID in "${STUDENTS[@]}"; do
    DIAR="$AUDIO_ROOT/$SID/${SID}_hybrid_diarization.json"
    if [ -f "$DIAR" ]; then
        echo "[$SID] diarization exists — skipping"
        continue
    fi
    WAV="$AUDIO_ROOT/$SID/${SID}.wav"
    if [ ! -f "$WAV" ]; then
        echo "[$SID] no WAV file — skipping diarization"
        continue
    fi
    echo "[$SID] Running diarization..."
    "$VENV" "$REPO/scripts/hybrid_diarization.py" \
        --audio-root "$AUDIO_ROOT" \
        "$SID" \
        && echo "[$SID] diarization OK" \
        || echo "[$SID] diarization FAILED (continuing)"
done

echo ""
echo "=== Step 2: Frame re-extraction (full_multimodal) ==="
for SID in "${STUDENTS[@]}"; do
    DIAR="$AUDIO_ROOT/$SID/${SID}_hybrid_diarization.json"
    if [ ! -f "$DIAR" ]; then
        echo "[$SID] no diarization — skipping re-extraction"
        continue
    fi
    echo "[$SID] Re-extracting frames..."
    "$VENV" "$REPO/scripts/dynamic_video_analytics.py" \
        --audio-root "$AUDIO_ROOT" \
        --video-root "$VIDEO_ROOT" \
        "$SID" \
        && echo "[$SID] extraction OK" \
        || echo "[$SID] extraction FAILED (continuing)"
done

echo ""
echo "=== Step 3: Targeted emit frame extraction ==="
"$VENV" "$REPO/scripts/extract_emit_frames.py" \
    "${STUDENTS[@]}" \
    --audio-root "$AUDIO_ROOT" \
    --video-root "$VIDEO_ROOT" \
    --log-csv "$LOG_CSV" \
    --session-date "$SESSION_DATE" \
    -v \
    || echo "WARN: emit frame extraction had errors (continuing)"

echo ""
echo "=== Step 4: Frame vision analysis ==="
"$VENV" "$REPO/scripts/codap_frame_analyzer.py" \
    "${STUDENTS[@]}" \
    --audio-root "$AUDIO_ROOT" \
    --video-root "$VIDEO_ROOT" \
    --log-csv "$LOG_CSV" \
    --session-date "$SESSION_DATE" \
    --session-label "$SESSION_LABEL" \
    --provider anthropic \
    --skip-existing \
    -v

echo ""
echo "=== Pipeline complete ==="
