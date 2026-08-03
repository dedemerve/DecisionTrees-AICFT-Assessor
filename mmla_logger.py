"""
mmla_logger.py

Structured JSONL logger for the MMLA rubric scoring pipeline.
Every pipeline event is written as a single JSON line to:
  logs/mmla_scoring_{session_key}_{timestamp}.jsonl

Each line has:
  ts        — ISO-8601 UTC timestamp
  level     — DEBUG / INFO / WARNING / ERROR
  stage     — pipeline stage (see STAGES below)
  student   — student identifier (or "ALL" for session-level)
  frame_id  — frame identifier if applicable, else null
  msg       — human-readable message
  data      — optional structured payload

Usage:
  from mmla_logger import get_logger
  log = get_logger("21apr_codap")
  log.frame_scored("Amy", "Amy_21apr_t2743s", triggered=["B1a","B3","B5"], lo={"LO3.1":"Triggered"})
  log.behavior_skipped("Amy", "Amy_21apr_t2743s", behavior="B2", reason="no transcript justification")
  log.session_done("Amy", frames=370, duration_seconds=4974)
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

STAGES = {
    "INIT":          "Pipeline initialized",
    "RUBRIC_LOAD":   "Rubric loaded",
    "FRAME_START":   "Frame analysis started",
    "BEHAVIOR":      "Behavior evaluation",
    "LO_AGGREGATE":  "LO aggregation",
    "FRAME_DONE":    "Frame analysis complete",
    "API_CALL":      "API call",
    "API_ERROR":     "API error",
    "SESSION_DONE":  "Student session complete",
    "COHORT_DONE":   "Cohort complete",
    "WARNING":       "Warning",
    "ERROR":         "Error",
}


class MMLALogger:
    def __init__(self, session_key: str):
        self.session_key = session_key
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.log_path = LOGS_DIR / f"mmla_scoring_{session_key}_{ts}.jsonl"
        self._file = open(self.log_path, "w", encoding="utf-8")
        self._py_logger = logging.getLogger(f"mmla.{session_key}")

        self._write("INFO", "INIT", "ALL", None,
                    f"MMLA scoring pipeline started — session={session_key}",
                    {"log_path": str(self.log_path)})

    def _write(self, level: str, stage: str, student: str,
               frame_id: str | None, msg: str, data: dict | None = None):
        record = {
            "ts":       datetime.now(timezone.utc).isoformat(),
            "level":    level,
            "stage":    stage,
            "student":  student,
            "frame_id": frame_id,
            "msg":      msg,
        }
        if data:
            record["data"] = data
        line = json.dumps(record, ensure_ascii=False)
        self._file.write(line + "\n")
        self._file.flush()
        getattr(self._py_logger, level.lower(), self._py_logger.info)(
            f"[{stage}] {student} | {msg}"
        )

    # ── Rubric ──────────────────────────────────────────────────

    def rubric_loaded(self, rubric_id: str, behavior_count: int):
        self._write("INFO", "RUBRIC_LOAD", "ALL", None,
                    f"Rubric loaded: {rubric_id} ({behavior_count} behaviors)",
                    {"rubric_id": rubric_id, "behavior_count": behavior_count})

    # ── Frame-level events ──────────────────────────────────────

    def frame_start(self, student: str, frame_id: str, timestamp_s: float,
                    trigger: str, session_type: str):
        self._write("DEBUG", "FRAME_START", student, frame_id,
                    f"t={timestamp_s:.0f}s trigger={trigger}",
                    {"timestamp_seconds": timestamp_s,
                     "trigger": trigger,
                     "session_type": session_type})

    def behavior_triggered(self, student: str, frame_id: str,
                           behavior: str, lo: str, evidence: str):
        self._write("INFO", "BEHAVIOR", student, frame_id,
                    f"{behavior} ({lo}) TRIGGERED",
                    {"behavior": behavior, "lo": lo, "evidence": evidence})

    def behavior_not_triggered(self, student: str, frame_id: str,
                                behavior: str, lo: str, reason: str):
        self._write("DEBUG", "BEHAVIOR", student, frame_id,
                    f"{behavior} ({lo}) not triggered",
                    {"behavior": behavior, "lo": lo, "reason": reason})

    def lo_result(self, student: str, frame_id: str, lo: str,
                  status: str, triggering: list[str]):
        level = "INFO" if status == "Triggered" else "DEBUG"
        self._write(level, "LO_AGGREGATE", student, frame_id,
                    f"{lo} → {status}",
                    {"lo": lo, "status": status, "triggering_behaviors": triggering})

    def frame_done(self, student: str, frame_id: str,
                   triggered_behaviors: list[str], lo_summary: dict):
        self._write("INFO", "FRAME_DONE", student, frame_id,
                    f"Behaviors: {triggered_behaviors or 'none'} | "
                    f"LO: {[k for k,v in lo_summary.items() if v=='Triggered'] or 'none'}",
                    {"triggered_behaviors": triggered_behaviors,
                     "lo_summary": lo_summary})

    # ── API events ───────────────────────────────────────────────

    def api_call(self, student: str, frame_id: str,
                 model: str, input_tokens: int):
        self._write("DEBUG", "API_CALL", student, frame_id,
                    f"API call: {model} input_tokens={input_tokens}",
                    {"model": model, "input_tokens": input_tokens})

    def api_response(self, student: str, frame_id: str,
                     output_tokens: int, latency_ms: int):
        self._write("DEBUG", "API_CALL", student, frame_id,
                    f"API response: output_tokens={output_tokens} latency={latency_ms}ms",
                    {"output_tokens": output_tokens, "latency_ms": latency_ms})

    def api_error(self, student: str, frame_id: str,
                  error: str, retry: int):
        self._write("WARNING", "API_ERROR", student, frame_id,
                    f"API error (attempt {retry}): {error}",
                    {"error": error, "retry": retry})

    def api_fatal(self, student: str, frame_id: str, error: str):
        self._write("ERROR", "API_ERROR", student, frame_id,
                    f"API fatal error — frame skipped: {error}",
                    {"error": error, "skipped": True})

    # ── Session / cohort events ──────────────────────────────────

    def session_done(self, student: str, frames_total: int,
                     frames_skipped: int, duration_seconds: float,
                     lo_final: dict, behaviors_never_seen: list[str],
                     output_path: str):
        self._write("INFO", "SESSION_DONE", student, None,
                    f"Done: {frames_total} frames | "
                    f"LO3.1={lo_final.get('LO3.1')} "
                    f"LO3.2={lo_final.get('LO3.2')} "
                    f"LO3.3={lo_final.get('LO3.3')}",
                    {"frames_total": frames_total,
                     "frames_skipped": frames_skipped,
                     "duration_seconds": duration_seconds,
                     "lo_final": lo_final,
                     "behaviors_never_seen": behaviors_never_seen,
                     "output_path": output_path})

    def cohort_done(self, students: list[str], total_frames: int,
                    total_api_calls: int, elapsed_seconds: float,
                    estimated_cost_usd: float):
        self._write("INFO", "COHORT_DONE", "ALL", None,
                    f"Cohort done: {len(students)} students | "
                    f"{total_frames} frames | ${estimated_cost_usd:.2f}",
                    {"students": students,
                     "total_frames": total_frames,
                     "total_api_calls": total_api_calls,
                     "elapsed_seconds": elapsed_seconds,
                     "estimated_cost_usd": estimated_cost_usd})

    # ── Warnings / errors ────────────────────────────────────────

    def warn(self, student: str, frame_id: str | None, msg: str, data: dict | None = None):
        self._write("WARNING", "WARNING", student, frame_id, msg, data)

    def error(self, student: str, frame_id: str | None, msg: str, data: dict | None = None):
        self._write("ERROR", "ERROR", student, frame_id, msg, data)

    # ── Lifecycle ────────────────────────────────────────────────

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def get_logger(session_key: str) -> MMLALogger:
    return MMLALogger(session_key)
