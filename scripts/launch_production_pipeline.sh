#!/usr/bin/env bash
# launch_production_pipeline.sh
#
# Production launcher for 21 April CODAP + coverage re-audit.
# Decouples execution from the terminal via nohup.
# Streams structured telemetry to logs/pipeline_runs/production_run.log.
#
# Usage:
#   ANTHROPIC_API_KEY="sk-ant-..." bash scripts/launch_production_pipeline.sh
#   bash scripts/launch_production_pipeline.sh Amy Ulysses   # subset

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$REPO/.venv-hybrid/bin/python"
LOG_DIR="$REPO/logs/pipeline_runs"
RUN_LOG="$LOG_DIR/production_run_$(date +%Y%m%dT%H%M%S).log"
AUDIO_21="$REPO/data_sources_2026/codap_arbor_21april_audio"

# ── Guard: API key must be present ────────────────────────────────────────────
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "[ERROR] ANTHROPIC_API_KEY is not set."
    echo "        Run:  export ANTHROPIC_API_KEY='sk-ant-...'"
    echo "        Then: bash scripts/launch_production_pipeline.sh"
    exit 1
fi

# ── Guard: .venv-hybrid must have anthropic ────────────────────────────────────
if ! "$VENV" -c "import anthropic" 2>/dev/null; then
    echo "[ERROR] anthropic package missing in .venv-hybrid."
    echo "        Run: $REPO/.venv-hybrid/bin/pip install anthropic"
    exit 1
fi

mkdir -p "$LOG_DIR"

if [ $# -gt 0 ]; then
    STUDENTS=("$@")
else
    STUDENTS=(Amy Bruno Helena Iris Irma Isabel Marco Marcus Nadia Shana Sheila Ulysses Zara)
fi

echo "[LAUNCH] Production pipeline starting"
echo "[LAUNCH] Students : ${STUDENTS[*]}"
echo "[LAUNCH] Log file : $RUN_LOG"
echo "[LAUNCH] PID will be written to $LOG_DIR/production.pid"

# Export key so child processes inherit it
export ANTHROPIC_API_KEY

# ── Detached execution via nohup ──────────────────────────────────────────────
nohup bash -c "
set -euo pipefail
export ANTHROPIC_API_KEY='${ANTHROPIC_API_KEY}'
REPO='$REPO'
VENV='$VENV'
AUDIO_21='$AUDIO_21'
VIDEO_21='$REPO/data_sources_2026/21 April CODAP Arbor Screen Recordings'
LOG_CSV='$REPO/data_sources_2026/All Documents/21 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv'
SESSION_DATE='2026-04-21'
SESSION_LABEL='21_Nisan_2026_CODAP'

log() { echo \"\$(date '+%Y-%m-%dT%H:%M:%S') [\$1] \$2\"; }

# ────────────────────────────────────────────────────────
# STEP 1: Re-extraction for motion_only_fallback students
# ────────────────────────────────────────────────────────
log INFO 'Step 1: Re-extraction for motion_only students'
for SID in ${STUDENTS[*]}; do
    MANIFEST=\"\$AUDIO_21/\$SID/\${SID}_video_extraction_manifest.json\"
    DIAR=\"\$AUDIO_21/\$SID/\${SID}_hybrid_diarization.json\"
    [ -f \"\$MANIFEST\" ] || { log WARN \"\$SID: no manifest — skipping\"; continue; }
    [ -f \"\$DIAR\"     ] || { log WARN \"\$SID: no diarization — skipping re-extract\"; continue; }
    SPEECH=\$(\"\$VENV\" -c \"
import json
m = json.load(open('\$MANIFEST'))
print(m.get('summary',{}).get('speech_anchor_count', 0))
\")
    if [ \"\$SPEECH\" -gt 0 ]; then
        log INFO \"\$SID: speech_anchors=\$SPEECH — skipping re-extraction\"
        continue
    fi
    log INFO \"\$SID: motion_only_fallback — re-extracting with full_multimodal\"
    \"\$VENV\" \"\$REPO/scripts/dynamic_video_analytics.py\" \
        --audio-root \"\$AUDIO_21\" \
        --video-root \"\$VIDEO_21\" \
        \"\$SID\" \
        && log INFO \"\$SID: re-extraction OK\" \
        || log WARN \"\$SID: re-extraction FAILED (continuing)\"
done

# ────────────────────────────────────────────────────────
# STEP 2: Targeted emit_tree_data frame extraction
# ────────────────────────────────────────────────────────
log INFO 'Step 2: Extracting frames at emit_tree_data timestamps'
\"\$VENV\" \"\$REPO/scripts/extract_emit_frames.py\" \
    ${STUDENTS[*]} \
    --audio-root \"\$AUDIO_21\" \
    --video-root \"\$VIDEO_21\" \
    --log-csv \"\$LOG_CSV\" \
    --session-date \"\$SESSION_DATE\" \
    -v \
    && log INFO 'emit frame extraction OK' \
    || log WARN 'emit frame extraction had errors (continuing)'

# ────────────────────────────────────────────────────────
# STEP 3: Claude vision analysis per frame
# ────────────────────────────────────────────────────────
log INFO 'Step 3: Claude vision analysis (codap_frame_analyzer)'
\"\$VENV\" \"\$REPO/scripts/codap_frame_analyzer.py\" \
    ${STUDENTS[*]} \
    --audio-root \"\$AUDIO_21\" \
    --video-root \"\$VIDEO_21\" \
    --log-csv \"\$LOG_CSV\" \
    --session-date \"\$SESSION_DATE\" \
    --session-label \"\$SESSION_LABEL\" \
    --provider anthropic \
    --skip-existing \
    -v \
    && log INFO 'Vision analysis OK' \
    || log WARN 'Vision analysis had errors'

# ────────────────────────────────────────────────────────
# STEP 4: Coverage re-audit
# ────────────────────────────────────────────────────────
log INFO 'Step 4: mmla_coverage_validator re-audit'
\"\$VENV\" \"\$REPO/scripts/mmla_coverage_validator.py\" \
    --audio-root \"\$AUDIO_21\" \
    --environment codap \
    --output \"\$REPO/logs/pipeline_runs/qa_coverage_report_21april.json\" \
    && log INFO 'Coverage audit OK' \
    || log WARN 'Coverage audit returned non-zero (see report)'

log INFO 'Production pipeline COMPLETE'
" >> "$RUN_LOG" 2>&1 &

PID=$!
echo $PID > "$LOG_DIR/production.pid"

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  Pipeline launched in background  PID=$PID"
echo "║  Log: $RUN_LOG"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Monitor commands:"
echo ""
echo "  # Live telemetry (key events only):"
echo "  tail -f $RUN_LOG | grep -E --line-buffered 'Step|OK|WARN|FAIL|ERROR|emit|Vision|Anchor|Motion|Fallback|complete'"
echo ""
echo "  # Progress by student (all INFO lines):"
echo "  tail -f $RUN_LOG | grep -E --line-buffered '\[INFO\]|\[WARN\]|\[ERROR\]'"
echo ""
echo "  # Vision API calls only:"
echo "  tail -f $RUN_LOG | grep -E --line-buffered 'claude|Vision|vision|anthropic|scored|LO3|rubric'"
echo ""
echo "  # Check if still running:"
echo "  kill -0 $PID 2>/dev/null && echo 'RUNNING' || echo 'DONE'"
echo ""
