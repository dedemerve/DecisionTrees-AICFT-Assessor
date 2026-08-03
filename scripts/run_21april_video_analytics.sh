#!/usr/bin/env bash
# 21 April CODAP Arbor — full-cohort dynamic video analytics (multimodal + motion-only).
#
# Detached background (macOS — survives SIGHUP):
#   bash scripts/run_21april_video_analytics.sh --detach
#
# Foreground:
#   bash scripts/run_21april_video_analytics.sh
#
# Live trigger monitor:
#   tail -f logs/21april_video_analytics.log | grep -E --line-buffered "Anchor|Motion|Fallback"
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

LOG_DIR="${LOG_DIR:-logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/21april_video_analytics.log}"
PID_FILE="${PID_FILE:-$LOG_DIR/21april_video_analytics.pid}"

if [[ "${1:-}" == "--detach" ]]; then
  shift
  mkdir -p "$LOG_DIR"
  if [[ -f "$PID_FILE" ]]; then
    OLD_PID="$(cat "$PID_FILE")"
    if ps -p "$OLD_PID" >/dev/null 2>&1; then
      echo "Already running: pid=$OLD_PID log=$LOG_FILE"
      exit 0
    fi
  fi
  # trap '' HUP in child; caffeinate prevents sleep during long motion scans
  nohup caffeinate -i bash "$ROOT/scripts/run_21april_video_analytics.sh" "$@" \
    >> "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  echo "Detached pid=$(cat "$PID_FILE") log=$LOG_FILE"
  echo "Monitor: tail -f $LOG_FILE | grep -E --line-buffered 'Anchor|Motion|Fallback'"
  exit 0
fi

PYTHON="${PYTHON:-$ROOT/.venv-hybrid/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="${PYTHON_FALLBACK:-python3}"
fi

AUDIO_ROOT="${AUDIO_ROOT:-data_sources_2026/codap_arbor_21april_audio}"
VIDEO_ROOT="${VIDEO_ROOT:-data_sources_2026/21 April CODAP Arbor Screen Recordings}"
LOG_DIR="${LOG_DIR:-logs}"
LOG_FILE="${LOG_FILE:-$LOG_DIR/21april_video_analytics.log}"
PID_FILE="${PID_FILE:-$LOG_DIR/21april_video_analytics.pid}"
STATUS_FILE="${STATUS_FILE:-$LOG_DIR/21april_video_analytics_status.json}"

# Verified upstream diarization cohort split
MULTIMODAL_STUDENTS=(Amy Bruno Helena Marcus Shana)
MOTION_ONLY_STUDENTS=(Iris Irma Isabel Marco Nadia Sheila Ulysses Zara)
ALL_STUDENTS=("${MULTIMODAL_STUDENTS[@]}" "${MOTION_ONLY_STUDENTS[@]}")

mkdir -p "$LOG_DIR"

on_signal() {
  local sig="$1"
  printf '%s [wrapper] caught %s — python child continues if already started\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$sig" >> "$LOG_FILE"
}
trap 'on_signal SIGTERM' SIGTERM
trap 'on_signal SIGINT' SIGINT
trap 'on_signal SIGHUP' SIGHUP

audit_manifests() {
  "$PYTHON" - <<'PY'
import json
import sys
from pathlib import Path

root = Path("data_sources_2026/codap_arbor_21april_audio")
multimodal = {"Amy", "Bruno", "Helena", "Marcus", "Shana"}
motion_only = {"Iris", "Irma", "Isabel", "Marco", "Nadia", "Sheila", "Ulysses", "Zara"}
required_frame_keys = {
    "frame_id",
    "source_timestamp_seconds",
    "extraction_trigger_reason",
    "file_path",
}
errors = []
report = {"students": {}, "ok": 0, "failed": 0}

for student_dir in sorted(root.iterdir()):
    if not student_dir.is_dir():
        continue
    sid = student_dir.name
    manifest_path = student_dir / f"{sid}_video_extraction_manifest.json"
    entry = {"manifest": str(manifest_path), "status": "missing"}
    if not manifest_path.is_file():
        errors.append(f"{sid}: manifest missing")
        report["students"][sid] = entry
        report["failed"] += 1
        continue
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{sid}: corrupt JSON ({exc})")
        entry["status"] = "corrupt"
        report["students"][sid] = entry
        report["failed"] += 1
        continue

    mode = payload.get("extraction_mode", "?")
    frames = payload.get("frames") or []
    entry.update(
        {
            "status": "ok",
            "extraction_mode": mode,
            "frame_count": len(frames),
            "speech_anchors": (payload.get("summary") or {}).get("speech_anchor_count", 0),
            "motion_keyframes": (payload.get("summary") or {}).get("motion_keyframe_count", 0),
        }
    )
    if sid in multimodal and mode != "full_multimodal":
        errors.append(f"{sid}: expected full_multimodal, got {mode}")
        entry["status"] = "mode_mismatch"
    if sid in motion_only and mode != "motion_only_fallback":
        errors.append(f"{sid}: expected motion_only_fallback, got {mode}")
        entry["status"] = "mode_mismatch"

    if frames:
        sample = frames[0]
        missing = required_frame_keys - set(sample.keys())
        if missing:
            errors.append(f"{sid}: frame missing keys {sorted(missing)}")
            entry["status"] = "schema_error"
        for key in ("source_timestamp_seconds", "extraction_trigger_reason", "file_path"):
            if key not in sample:
                continue
            if sample[key] in (None, ""):
                errors.append(f"{sid}: empty {key} in first frame")
                entry["status"] = "schema_error"

    if entry["status"] == "ok":
        report["ok"] += 1
    else:
        report["failed"] += 1
    report["students"][sid] = entry

out = Path("logs/21april_video_analytics_status.json")
out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"ok": report["ok"], "failed": report["failed"], "errors": errors}, indent=2))
sys.exit(0 if not errors else 1)
PY
}

echo "== 21 April CODAP video analytics =="
echo "python:      $PYTHON"
echo "audio_root:  $AUDIO_ROOT"
echo "video_root:  $VIDEO_ROOT"
echo "log:         $LOG_FILE"
echo "pid:         $$"
echo "started:     $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "multimodal:  ${MULTIMODAL_STUDENTS[*]}"
echo "motion_only: ${MOTION_ONLY_STUDENTS[*]}"

export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-4}"
export VECLIB_MAXIMUM_THREADS="${VECLIB_MAXIMUM_THREADS:-4}"
export OPENCV_LOG_LEVEL="${OPENCV_LOG_LEVEL:-ERROR}"
export OPENCV_FFMPEG_CAPTURE_OPTIONS="${OPENCV_FFMPEG_CAPTURE_OPTIONS:-loglevel;error}"

"$PYTHON" -u scripts/dynamic_video_analytics.py \
  --audio-root "$AUDIO_ROOT" \
  --video-root "$VIDEO_ROOT" \
  --compute-type int8 \
  --max-width 1920 \
  --motion-threshold 0.005 \
  --cooldown-ms 500 \
  --jpeg-quality 88 \
  --skip-existing \
  -v \
  "${ALL_STUDENTS[@]}"

EXIT_CODE=$?
echo "python_exit: $EXIT_CODE"
echo "finished:    $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "== manifest audit =="
if audit_manifests; then
  echo "audit: PASS — see $STATUS_FILE"
else
  echo "audit: FAIL — see $STATUS_FILE"
fi
exit "$EXIT_CODE"
