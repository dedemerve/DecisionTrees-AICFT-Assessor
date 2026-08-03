#!/usr/bin/env python3
"""Log Synchronizer — maps CODAP log events to learning episodes.

Reads the episode file produced by LESA and the CODAP Arbor log CSV.
For each episode, finds log events that fall within [start_ms, end_ms]
(using video_start_utc to align log timestamps to video time).
Writes the enriched episodes back to the same file in place.

Usage:
    python scripts/log_synchronizer.py Marco \
        --session-date 2026-04-21 \
        --log-csv "data_sources_2026/All Documents/21 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv"
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("log_synchronizer")

SESSION_AUDIO_ROOTS: dict[str, str] = {
    "2026-04-21": "codap_arbor_21april_audio",
    "2026-04-28": "codap_arbor_28april_audio",
}

# Column names in the CODAP log CSV
COL_STUDENT   = "student_id"
COL_CREATED   = "created_at"
COL_EVENT     = "action"
COL_VALUE     = "parameters"


# ─────────────────────────────────────────────────────────────
# Log loading + student filtering
# ─────────────────────────────────────────────────────────────

def load_log(csv_path: Path, student_id: str) -> list[dict[str, Any]]:
    import csv
    rows: list[dict[str, Any]] = []
    with csv_path.open(encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if row.get(COL_STUDENT, "").strip().lower() == student_id.lower():
                rows.append(row)
    LOGGER.info("Log rows for %s: %d", student_id, len(rows))
    return rows


def parse_utc(ts_str: str) -> datetime | None:
    for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(ts_str.strip(), fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def estimate_video_start(log_rows: list[dict[str, Any]]) -> datetime | None:
    timestamps = []
    for row in log_rows:
        dt = parse_utc(row.get(COL_CREATED, ""))
        if dt:
            timestamps.append(dt)
    if not timestamps:
        return None
    return min(timestamps)


# ─────────────────────────────────────────────────────────────
# Core: match log events to episodes
# ─────────────────────────────────────────────────────────────

def synchronize(
    episodes: list[dict[str, Any]],
    log_rows: list[dict[str, Any]],
    video_start_utc: datetime | None,
) -> list[dict[str, Any]]:
    log_events: list[dict[str, Any]] = []
    for row in log_rows:
        # Prefer timestamp_ms from log (offset from session start) when available
        raw_ts = row.get("timestamp_ms", "").strip()
        if raw_ts:
            try:
                offset_ms = int(float(raw_ts))
            except ValueError:
                continue
        elif video_start_utc is not None:
            dt = parse_utc(row.get(COL_CREATED, ""))
            if dt is None:
                continue
            offset_ms = int((dt - video_start_utc).total_seconds() * 1000)
        else:
            continue

        log_events.append({
            "offset_ms": offset_ms,
            "event_type": row.get(COL_EVENT, "").strip(),
            "value": row.get(COL_VALUE, "").strip() or None,
        })

    log_events.sort(key=lambda e: e["offset_ms"])

    for ep in episodes:
        start_ms = ep["start_ms"]
        end_ms = ep["end_ms"]
        ep["log_events"] = [
            e for e in log_events
            if start_ms <= e["offset_ms"] <= end_ms
        ]

    return episodes


# ─────────────────────────────────────────────────────────────
# I/O
# ─────────────────────────────────────────────────────────────

def load_episode_file(student_id: str, session_date: str) -> tuple[dict[str, Any], Path]:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    path = REPO_ROOT / "data_sources_2026" / subdir / student_id / f"{student_id}_learning_episodes.json"
    if not path.is_file():
        raise FileNotFoundError(f"Episode file not found: {path}. Run lesa.py first.")
    return json.loads(path.read_text(encoding="utf-8")), path


def write_episode_file(payload: dict[str, Any], path: Path) -> None:
    payload["log_synchronized_at"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Log Synchronizer — attach CODAP log events to episodes")
    parser.add_argument("student", help="Student ID (e.g. Marco)")
    parser.add_argument("--session-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--log-csv", type=Path, required=True, help="CODAP Arbor log CSV path")
    args = parser.parse_args()

    payload, ep_path = load_episode_file(args.student, args.session_date)
    episodes = payload["episodes"]

    log_rows = load_log(args.log_csv.resolve(), args.student)
    if not log_rows:
        LOGGER.warning("No log rows found for student %s — log_events will be empty", args.student)

    video_start_utc = estimate_video_start(log_rows)
    if video_start_utc is None:
        LOGGER.info("video_start_utc unavailable — using log timestamp_ms column directly")

    episodes = synchronize(episodes, log_rows, video_start_utc)

    total_events = sum(len(ep["log_events"]) for ep in episodes)
    LOGGER.info("Attached %d log events across %d episodes", total_events, len(episodes))
    for ep in episodes:
        LOGGER.info("  %s: %d log events", ep["episode_id"], len(ep["log_events"]))

    payload["episodes"] = episodes
    write_episode_file(payload, ep_path)
    LOGGER.info("Updated: %s", ep_path)


if __name__ == "__main__":
    main()
