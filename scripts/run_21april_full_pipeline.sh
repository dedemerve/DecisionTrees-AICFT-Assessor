#!/usr/bin/env bash
# MMLA pipeline for 21 April CODAP Arbor cohort.
#
# Amy, Bruno, Marcus, Shana already have full_multimodal manifests (speech anchors).
# Iris, Irma, Isabel, Marco, Nadia, Sheila, Ulysses, Zara need diarization first.
# Helena has a manifest but no log entry — visual-only analysis.
#
# Usage:
#   bash scripts/run_21april_full_pipeline.sh            # all students
#   bash scripts/run_21april_full_pipeline.sh Amy Shana  # specific students

set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$REPO/.venv-hybrid/bin/python"
AUDIO_ROOT="$REPO/data_sources_2026/codap_arbor_21april_audio"
VIDEO_ROOT="$REPO/data_sources_2026/21 April CODAP Arbor Screen Recordings"
LOG_CSV="$REPO/data_sources_2026/All Documents/21 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv"
SESSION_DATE="2026-04-21"
SESSION_LABEL="21_Nisan_2026_CODAP"

if [ $# -gt 0 ]; then
    STUDENTS=("$@")
else
    STUDENTS=(Amy Bruno Helena Iris Irma Isabel Marco Marcus Nadia Shana Sheila Ulysses Zara)
fi

echo "=== Step 1: Diarization (skipped if already done) ==="
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
echo "=== Step 2: Frame re-extraction (only for motion_only_fallback students with new diarization) ==="
for SID in "${STUDENTS[@]}"; do
    MANIFEST="$AUDIO_ROOT/$SID/${SID}_video_extraction_manifest.json"
    DIAR="$AUDIO_ROOT/$SID/${SID}_hybrid_diarization.json"
    [ -f "$MANIFEST" ] || continue
    [ -f "$DIAR" ] || continue
    SPEECH=$(python3 -c "import json; d=json.load(open('$MANIFEST')); print(d.get('summary',{}).get('speech_anchor_count',0))")
    if [ "$SPEECH" -gt "0" ]; then
        echo "[$SID] already has speech anchors ($SPEECH) — skipping re-extraction"
        continue
    fi
    echo "[$SID] Re-extracting frames (full_multimodal)..."
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
