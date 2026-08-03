#!/bin/bash
# Sequential frame analysis pipeline — April 21 (remaining) + April 28
# Waits for Amy and Marco (already running) to finish before starting.

set -euo pipefail

REPO="/Users/mrved/Desktop/DecisionTrees-AICFT-Assessor"
ANALYZER="$REPO/scripts/codap_frame_analyzer.py"
LOG="$REPO/scripts/run_all_frame_analyses.log"

export ANTHROPIC_API_KEY="$API_KEY"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

run_student() {
  local student="$1"
  local date="$2"
  local audio_root="$3"
  log "=== START $student ($date) ==="
  python3 "$ANALYZER" "$student" \
    --session-date "$date" \
    --audio-root "$audio_root" \
    --all-manifest-frames \
    --overwrite -v \
    2>&1 | tee -a "$LOG"
  log "=== END $student ($date) ==="
}

# Wait for Amy and Marco (Sonnet-5) to finish
log "Waiting for Amy and Marco to complete..."
while true; do
  amy_done=false
  marco_done=false

  if python3 -c "
import json, sys
try:
    d = json.load(open('$REPO/data_sources_2026/codap_arbor_21april_audio/Amy/Amy_codap_frame_analyses.json'))
    sys.exit(0 if d.get('complete') and d.get('model','') == 'claude-sonnet-5' else 1)
except: sys.exit(1)
" 2>/dev/null; then amy_done=true; fi

  if python3 -c "
import json, sys
try:
    d = json.load(open('$REPO/data_sources_2026/codap_arbor_21april_audio/Marco/Marco_codap_frame_analyses.json'))
    sys.exit(0 if d.get('complete') and d.get('model','') == 'claude-sonnet-5' else 1)
except: sys.exit(1)
" 2>/dev/null; then marco_done=true; fi

  log "Amy done: $amy_done | Marco done: $marco_done"
  if $amy_done && $marco_done; then
    log "Amy and Marco complete. Starting batch."
    break
  fi
  sleep 60
done

AUDIO_21="$REPO/data_sources_2026/codap_arbor_21april_audio"
AUDIO_28="$REPO/data_sources_2026/codap_arbor_28april_audio"

# April 21 — remaining (Amy and Marco already done)
log "===== APRIL 21 BATCH ====="
for student in Bruno Helena Iris Irma Isabel Marcus Nadia Shana Zara Sheila Ulysses; do
  run_student "$student" "2026-04-21" "$AUDIO_21"
done

# April 28 — all students
log "===== APRIL 28 BATCH ====="
for student in Bruno Irma Isabel Marco Melinda Nadia Serena Zara Ulysses; do
  run_student "$student" "2026-04-28" "$AUDIO_28"
done

log "===== ALL DONE ====="
