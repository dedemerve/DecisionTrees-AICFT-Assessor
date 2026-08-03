#!/usr/bin/env python3
"""Wall-clock alignment between video frame timestamps and CODAP Arbor log events.

Problem: CODAP's log timestamp_ms resets to 0 on every page reload. A single
recording session can contain dozens of resets, making timestamp_ms useless as
a global time axis. The only reliable clock is created_at (UTC wall clock).

Alignment strategy:
  video_wall_time(frame) = video_start_utc + frame_source_timestamp_seconds
  log_wall_time(event)   = created_at (UTC)
  match window           = |video_wall_time - log_wall_time| <= window_s

video_start_utc estimation (first available wins):
  1. ffprobe creation_time tag (rarely present in Chrome-recorded webm)
  2. First log event created_at on session_date (reliable proxy)

The offset between video start and first log event is typically < 60 s and is
stored in the pipeline output for researcher review.
"""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

LOGGER = logging.getLogger("codap_alignment")

PRIORITY_ACTIONS = ("emit_tree_data",)

# Decision actions: direct tree-building choices
SECONDARY_ACTIONS = (
    "drop_attribute",
    "change_split_values",
    "set_dependent_variable",
    "change_tree_type",
    "swap_focus_split",
    "refresh_tree",         # tree reset — struggle indicator (student gave up and restarted)
)

# Contextual actions: navigation and exploration signals
CONTEXTUAL_ACTIONS = (
    "set_focus_node",       # which node the student examined
    "data_context_change",  # dataset switch — compare_models behaviour
    # "dragend" excluded: fires for every drag including cancellations (~90/student),
    # creating noise. drop_attribute already captures successful drags.
)

# System/background actions excluded intentionally:
#   session_start, codap_component_change, codap_document_change,
#   dragstart, dragenter, dragleave  — not student decisions

ALL_ANCHOR_ACTIONS = PRIORITY_ACTIONS + SECONDARY_ACTIONS + CONTEXTUAL_ACTIONS


# ─────────────────────────────────────────────────────────────
# video_start_utc estimation
# ─────────────────────────────────────────────────────────────

def estimate_video_start_utc(
    video_path: Path | None,
    log_df: pd.DataFrame,
    student_id: str,
    session_date: str,
) -> tuple[datetime | None, str]:
    """Return (video_start_utc, method_used) for aligning video frames to log events.

    method_used is one of: 'ffprobe', 'first_log_event', 'unavailable'
    """
    if video_path is not None and video_path.is_file():
        ts = _ffprobe_creation_time(video_path)
        if ts is not None:
            LOGGER.debug("[%s] video_start from ffprobe: %s", student_id, ts)
            return ts, "ffprobe"

    ts = _first_log_event_utc(log_df, student_id, session_date)
    if ts is not None:
        LOGGER.debug(
            "[%s] video_start from first_log_event: %s (proxy)", student_id, ts
        )
        return ts, "first_log_event"

    LOGGER.warning("[%s] Cannot estimate video_start_utc", student_id)
    return None, "unavailable"


def _ffprobe_creation_time(video_path: Path) -> datetime | None:
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                str(video_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        data = json.loads(result.stdout)
        ct = data.get("format", {}).get("tags", {}).get("creation_time")
        if ct:
            return datetime.fromisoformat(ct.replace("Z", "+00:00"))
    except Exception:
        pass
    return None


def _first_log_event_utc(
    log_df: pd.DataFrame,
    student_id: str,
    session_date: str,
) -> datetime | None:
    from codap_log_window import student_log_rows
    rows = student_log_rows(log_df, student_id)
    if rows.empty:
        return None
    rows = rows.copy()
    rows["_dt"] = pd.to_datetime(rows["created_at"], utc=True)
    day_rows = rows[rows["_dt"].dt.date.astype(str) == session_date].sort_values("_dt")
    if day_rows.empty:
        return None
    return day_rows["_dt"].iloc[0].to_pydatetime()


# ─────────────────────────────────────────────────────────────
# aligned log window
# ─────────────────────────────────────────────────────────────

def log_window_entries_aligned(
    log_df: pd.DataFrame,
    student_id: str,
    frame_timestamp_s: float,
    video_start_utc: datetime,
    *,
    window_s: float = 10.0,
    session_date: str | None = None,
) -> list[dict[str, Any]]:
    """Return log entries within ±window_s of a frame's wall-clock time.

    Times in returned entries are expressed as video-relative ms so the model
    prompt reads the same as before.
    """
    from codap_log_window import student_log_rows
    from log_extractor import _parse_parameters

    rows = student_log_rows(log_df, student_id)
    if rows.empty:
        return []

    rows = rows.copy()
    rows["_dt"] = pd.to_datetime(rows["created_at"], utc=True)
    if session_date:
        rows = rows[rows["_dt"].dt.date.astype(str) == session_date]
    if rows.empty:
        return []

    frame_wall_ts = video_start_utc.timestamp() + frame_timestamp_s
    lo = frame_wall_ts - window_s
    hi = frame_wall_ts + window_s

    rows = rows.copy()
    rows["_wall_ts"] = rows["_dt"].apply(lambda x: x.timestamp())
    window = rows[(rows["_wall_ts"] >= lo) & (rows["_wall_ts"] <= hi)].sort_values("_dt")

    video_start_ts = video_start_utc.timestamp()
    out: list[dict[str, Any]] = []
    for _, row in window.iterrows():
        params = row.get("_params") or {}
        if not isinstance(params, dict):
            params = _parse_parameters(str(params))
        rel_ms = int(round((row["_wall_ts"] - video_start_ts) * 1000))
        out.append(
            {
                "timestamp_ms": rel_ms,
                "action": str(row.get("action", "")),
                "parameters": params,
                "line": (
                    f"[t={rel_ms}] {row.get('action', '')} | "
                    f"{json.dumps(params, ensure_ascii=False)}"
                ),
            }
        )
    return out


def log_window_text_aligned(
    log_df: pd.DataFrame,
    student_id: str,
    frame_timestamp_s: float,
    video_start_utc: datetime,
    *,
    window_s: float = 10.0,
    session_date: str | None = None,
) -> str:
    entries = log_window_entries_aligned(
        log_df,
        student_id,
        frame_timestamp_s,
        video_start_utc,
        window_s=window_s,
        session_date=session_date,
    )
    if not entries:
        return "(log yok — bu zaman penceresinde kayıt bulunamadı)"
    return "\n".join(e["line"] for e in entries)


# ─────────────────────────────────────────────────────────────
# meaningful event timestamps for frame selection
# ─────────────────────────────────────────────────────────────

def meaningful_event_timestamps_s(
    log_df: pd.DataFrame,
    student_id: str,
    video_start_utc: datetime,
    *,
    session_date: str | None = None,
    priority_actions: tuple[str, ...] = PRIORITY_ACTIONS,
    secondary_actions: tuple[str, ...] = SECONDARY_ACTIONS,
    contextual_actions: tuple[str, ...] = CONTEXTUAL_ACTIONS,
) -> list[dict[str, Any]]:
    """Return anchor events as video-relative seconds, sorted by time.

    Each entry: {"timestamp_s": float, "action": str, "priority": bool, "params": dict}
    priority=True  → emit_tree_data (tree submission)
    priority=False → decision actions + contextual navigation/struggle signals
    """
    from codap_log_window import student_log_rows
    from log_extractor import _parse_parameters

    rows = student_log_rows(log_df, student_id)
    if rows.empty:
        return []

    rows = rows.copy()
    rows["_dt"] = pd.to_datetime(rows["created_at"], utc=True)
    if session_date:
        rows = rows[rows["_dt"].dt.date.astype(str) == session_date]
    if rows.empty:
        return []

    all_actions = set(priority_actions) | set(secondary_actions) | set(contextual_actions)
    rows = rows[rows["action"].isin(all_actions)].sort_values("_dt")

    video_start_ts = video_start_utc.timestamp()
    out: list[dict[str, Any]] = []
    # Dedup strategy differs by action type:
    #
    # change_split_values (threshold slider): keep the LAST event in each 2s burst.
    #   Rationale: rapid slider drags fire many events; only the final settled value
    #   matters for rubric assessment. First-event dedup would keep the drag start
    #   and discard the final threshold choice.
    #
    # All other non-priority actions: keep the FIRST event in each 2s burst.
    #   Rationale: prevents event storms (e.g. set_focus_node) while preserving
    #   the moment the student initiated the action.
    #
    # Priority actions (emit_tree_data): never deduped.

    DEDUP_WINDOW_S = 2.0

    # For threshold actions, buffer events and flush on gap
    THRESHOLD_ACTIONS = {"change_split_values"}
    threshold_buffer: dict[str, dict] = {}  # action -> latest event dict
    threshold_last_t: dict[str, float] = {}

    first_seen: dict[str, float] = {}  # for first-event dedup

    raw_events = []
    for _, row in rows.iterrows():
        params = row.get("_params") or {}
        if not isinstance(params, dict):
            params = _parse_parameters(str(params))
        t_s = row["_dt"].timestamp() - video_start_ts
        if t_s < -60:
            continue
        action = str(row.get("action", ""))
        raw_events.append({"t_s": t_s, "action": action, "params": params,
                            "row": row})

    # Two-pass: first collect threshold bursts (keep last), then first-event for rest
    for ev in raw_events:
        t_s = ev["t_s"]
        action = ev["action"]
        is_priority = action in priority_actions

        if is_priority:
            out.append({"timestamp_s": max(0.0, t_s), "action": action,
                        "priority": True, "params": ev["params"]})

        elif action in THRESHOLD_ACTIONS:
            prev_t = threshold_last_t.get(action, -9999)
            if t_s - prev_t > DEDUP_WINDOW_S and action in threshold_buffer:
                # flush previous burst — emit the settled (last) value
                b = threshold_buffer[action]
                out.append({"timestamp_s": max(0.0, b["t_s"]), "action": action,
                            "priority": False, "params": b["params"]})
            # always overwrite buffer with latest event in burst
            threshold_buffer[action] = ev
            threshold_last_t[action] = t_s

        else:
            prev = first_seen.get(action, -9999)
            if t_s - prev >= DEDUP_WINDOW_S:
                first_seen[action] = t_s
                out.append({"timestamp_s": max(0.0, t_s), "action": action,
                            "priority": False, "params": ev["params"]})

    # Flush any remaining threshold buffers
    for action, b in threshold_buffer.items():
        if not any(e["action"] == action and abs(e["timestamp_s"] - max(0.0, b["t_s"])) < 0.01
                   for e in out):
            out.append({"timestamp_s": max(0.0, b["t_s"]), "action": action,
                        "priority": False, "params": b["params"]})

    out.sort(key=lambda e: e["timestamp_s"])
    return out
