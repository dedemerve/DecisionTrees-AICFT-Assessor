#!/usr/bin/env bash
# Autonomous MMLA pipeline supervisor — crash recovery for 21 April CODAP video analytics.
#
# Detached launch (safe to close Terminal.app):
#   cd /Users/mrved/Desktop/DecisionTrees-AICFT-Assessor
#   mkdir -p logs
#   nohup bash scripts/resilient_mmla_supervisor.sh >> logs/supervisor_nohup.log 2>&1 &
#   echo $! > logs/supervisor.pid
#
set -euo pipefail

ROOT="/Users/mrved/Desktop/DecisionTrees-AICFT-Assessor"
cd "$ROOT"

LOG_DIR="$ROOT/logs"
PIPELINE_LOG="$LOG_DIR/21april_video_analytics.log"
PIPELINE_PID_FILE="$LOG_DIR/21april_video_analytics.pid"
SUPERVISOR_LOG="$LOG_DIR/supervisor_telemetry.log"
SUPERVISOR_PID_FILE="$LOG_DIR/supervisor.pid"

MULTIMODAL_STUDENTS=(Amy Bruno Helena Marcus Shana)
MOTION_ONLY_STUDENTS=(Iris Irma Isabel Marco Nadia Sheila Ulysses Zara)
ALL_STUDENTS=("${MULTIMODAL_STUDENTS[@]}" "${MOTION_ONLY_STUDENTS[@]}")

RECOVERY_SLEEP_SECONDS=5
POLL_INTERVAL_SECONDS=15

timestamp() {
  date "+%Y-%m-%d %H:%M:%S"
}

log() {
  local line="[$(timestamp)] $*"
  echo "$line"
  echo "$line" >> "$SUPERVISOR_LOG"
}

activate_virtualenv() {
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    log "ENV: virtualenv already active ($VIRTUAL_ENV)"
    return 0
  fi
  if [[ -f "$ROOT/.venv-hybrid/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$ROOT/.venv-hybrid/bin/activate"
    log "ENV: activated .venv-hybrid"
    return 0
  fi
  if [[ -f "$ROOT/venv/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$ROOT/venv/bin/activate"
    log "ENV: activated venv"
    return 0
  fi
  log "ENV: WARNING — no virtualenv found; relying on system/python fallback in runner"
  return 0
}

audit_log_state() {
  local last_student="unknown"
  local last_anchor="none"
  local last_motion="none"
  local last_line=""

  if [[ -f "$PIPELINE_LOG" ]]; then
    last_line="$(tail -n 1 "$PIPELINE_LOG" 2>/dev/null || true)"
    last_student="$(grep -E 'INFO [A-Za-z]+: (Multimodal|Fallback|skipping)' "$PIPELINE_LOG" 2>/dev/null | tail -n 1 | sed -E 's/.*INFO ([A-Za-z]+):.*/\1/' || echo "unknown")"
    last_anchor="$(grep -E 'Anchor: frame_[0-9]+' "$PIPELINE_LOG" 2>/dev/null | tail -n 1 | sed -E 's/.*(frame_[0-9]+).*/\1/' || echo "none")"
    last_motion="$(grep -E '^(Motion|Fallback): frame_' "$PIPELINE_LOG" 2>/dev/null | tail -n 1 | sed -E 's/.*(frame_[0-9]+).*/\1/' || echo "none")"
  fi

  log "AUDIT: last_student=$last_student last_anchor=$last_anchor last_motion=$last_motion"
  if [[ -n "$last_line" ]]; then
    log "AUDIT: pipeline_log_tail=${last_line}"
  fi
}

manifest_complete() {
  local student_id="$1"
  local manifest="$ROOT/data_sources_2026/codap_arbor_21april_audio/${student_id}/${student_id}_video_extraction_manifest.json"
  local py="$ROOT/.venv-hybrid/bin/python"
  if [[ ! -x "$py" ]]; then
    py="python3"
  fi
  if [[ ! -f "$manifest" ]]; then
    return 1
  fi
  "$py" - "$manifest" <<'PY'
import json
import sys

path = sys.argv[1]
try:
    payload = json.loads(open(path, encoding="utf-8").read())
except json.JSONDecodeError:
    sys.exit(1)
frames = payload.get("frames") or []
if not frames:
    sys.exit(1)
sample = frames[0]
for key in ("frame_id", "source_timestamp_seconds", "extraction_trigger_reason", "file_path"):
    if key not in sample or sample[key] in (None, ""):
        sys.exit(1)
sys.exit(0)
PY
}

count_completed_students() {
  local done=0
  local student_id
  for student_id in "${ALL_STUDENTS[@]}"; do
    if manifest_complete "$student_id"; then
      done=$((done + 1))
    fi
  done
  echo "$done"
}

cohort_complete() {
  local student_id
  for student_id in "${ALL_STUDENTS[@]}"; do
    if ! manifest_complete "$student_id"; then
      return 1
    fi
  done
  return 0
}

should_terminate() {
  if cohort_complete; then
    log "TERMINATE: all ${#ALL_STUDENTS[@]} student manifests validated (including Zara)"
    return 0
  fi
  return 1
}

record_system_telemetry() {
  log "TELEMETRY: recording vm_stat and uptime before recovery restart"
  {
    echo "----- $(timestamp) -----"
    uptime
    vm_stat
    echo ""
  } >> "$SUPERVISOR_LOG"
}

pipeline_process_running() {
  local pid=""
  if [[ -f "$PIPELINE_PID_FILE" ]]; then
    pid="$(cat "$PIPELINE_PID_FILE" 2>/dev/null || true)"
    if [[ -n "$pid" ]] && ps -p "$pid" >/dev/null 2>&1; then
      return 0
    fi
  fi
  if pgrep -f "scripts/dynamic_video_analytics.py" >/dev/null 2>&1; then
    return 0
  fi
  if pgrep -f "scripts/run_21april_video_analytics.sh" >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

wait_for_pipeline_exit() {
  local waited=0
  log "WATCHDOG: waiting for pipeline subprocess to finish"
  while pipeline_process_running; do
    sleep "$POLL_INTERVAL_SECONDS"
    waited=$((waited + POLL_INTERVAL_SECONDS))
    if (( waited % 300 == 0 )); then
      audit_log_state
      log "WATCHDOG: still running (${waited}s elapsed)"
    fi
  done
  log "WATCHDOG: pipeline subprocess exited after ~${waited}s"
}

launch_pipeline_detached() {
  log "LAUNCH: bash scripts/run_21april_video_analytics.sh --detach"
  bash "$ROOT/scripts/run_21april_video_analytics.sh" --detach >> "$SUPERVISOR_LOG" 2>&1
  if [[ -f "$PIPELINE_PID_FILE" ]]; then
    log "LAUNCH: pipeline pid=$(cat "$PIPELINE_PID_FILE")"
  else
    log "LAUNCH: WARNING — pid file not written"
  fi
}

on_supervisor_signal() {
  local sig="$1"
  log "SIGNAL: supervisor received $sig — will exit after logging"
  exit 0
}

trap 'on_supervisor_signal SIGTERM' TERM
trap 'on_supervisor_signal SIGINT' INT
trap '' HUP

mkdir -p "$LOG_DIR"
echo $$ > "$SUPERVISOR_PID_FILE"

log "SUPERVISOR: starting resilient MMLA agent (pid=$$)"
log "SUPERVISOR: root=$ROOT"
log "SUPERVISOR: cohort multimodal=${MULTIMODAL_STUDENTS[*]}"
log "SUPERVISOR: cohort motion_only=${MOTION_ONLY_STUDENTS[*]}"

activate_virtualenv

completed="$(count_completed_students)"
log "SUPERVISOR: initial completed manifests=$completed/${#ALL_STUDENTS[@]}"

attempt=0
while true; do
  if should_terminate; then
    log "SUPERVISOR: success — cohort processing complete"
    break
  fi

  attempt=$((attempt + 1))
  log "LOOP: attempt=$attempt starting pipeline spike"
  audit_log_state

  launch_pipeline_detached
  wait_for_pipeline_exit

  if should_terminate; then
    log "SUPERVISOR: success after attempt=$attempt"
    break
  fi

  log "RECOVERY: pipeline stopped before cohort completion — exit watchdog triggered"
  record_system_telemetry
  log "RECOVERY: sleeping ${RECOVERY_SLEEP_SECONDS}s to clear OS thread locks"
  sleep "$RECOVERY_SLEEP_SECONDS"
done

log "SUPERVISOR: final manifest validation"
audit_log_state

completed="$(count_completed_students)"
log "SUPERVISOR: final completed manifests=$completed/${#ALL_STUDENTS[@]}"
log "SUPERVISOR: telemetry=$SUPERVISOR_LOG pipeline=$PIPELINE_LOG"
log "SUPERVISOR: shutdown complete"
