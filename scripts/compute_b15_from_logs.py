#!/usr/bin/env python3
"""Compute B15 (VOTAT systematic exploration) directly from 2026 CODAP event logs.

B15 does not require API scoring — it is fully derivable from the log event
sequence. This script writes per-student B15 results into a JSON sidecar file
that mmla_scorer can merge into final_scored.json.

Output per session:
    data_sources_2026/<session_dir>/<student>/<student>_<session>_b15_log.json

Usage:
    python scripts/compute_b15_from_logs.py
    python scripts/compute_b15_from_logs.py --session 21apr
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data_sources_2026"

# Each export file is cumulative: the 21 April file also holds 7 April rows,
# and the 28 April file holds 7, 21, 25 and 28 April rows. Rows are therefore
# filtered by the calendar date in created_at.
LOG_FILES = {
    "21apr": DATA_ROOT / "All Documents" / "21 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv",
    "28apr": DATA_ROOT / "All Documents" / "28 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv",
}

SESSION_DATES = {
    "21apr": "2026-04-21",
    "28apr": "2026-04-28",
}

SESSION_DIRS = {
    "21apr": "codap_arbor_21april_audio",
    "28apr": "codap_arbor_28april_audio",
}


def _id_resolver():
    """Use the site build's resolver so log IDs typed as real names map to the
    same pseudonyms everywhere. Unresolved IDs (for example instructors) are dropped."""
    sys.path.insert(0, str(REPO_ROOT / "mmla_explorer"))
    import build_site_data as site  # noqa: E402

    pmap = site.load_pseudonym_map()
    return lambda raw: site.resolve_log_id(raw, pmap)


def load_log(session_key: str) -> list[dict]:
    """Rows for one class session only, with student_id resolved to a pseudonym."""
    path = LOG_FILES.get(session_key)
    if path is None or not path.is_file():
        return []
    day = SESSION_DATES[session_key]
    resolve = _id_resolver()
    rows = []
    with path.open(encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if (row.get("created_at") or "")[:10] != day:
                continue
            sid = resolve(row.get("student_id"))
            if sid is None:
                continue
            rows.append(dict(row, student_id=sid))
    return rows


def _order_key(ev: dict):
    """Order events by wall-clock time. timestamp_ms is not monotonic within a
    session, so it is only a fallback when created_at is missing."""
    created = ev.get("created_at")
    if created:
        return (created, int(ev.get("id") or 0))
    return ("", int(ev.get("timestamp_ms") or 0))


def parse_params(raw: str) -> dict:
    try:
        return json.loads(raw) if raw and raw.strip() not in ("", "{}") else {}
    except (json.JSONDecodeError, TypeError):
        return {}


def compute_votat(events: list[dict]) -> dict:
    """Compute VOTAT metrics from a student's event sequence.

    Between each pair of consecutive emit_tree_data events, check whether
    exactly one dimension changed (predictor OR threshold, not both, not neither).

    Returns:
        votat_rate         — fraction of inter-emit intervals that are VOTAT
        votat_intervals    — list of (emit_a_ms, emit_b_ms, dimension_changed)
        total_emits        — total number of emit_tree_data events
        b15_observed       — True if at least 2 consecutive VOTAT intervals
        b15_level          — "Deepen" if 3+ consecutive VOTAT, "Acquire" if 2+
    """
    emit_events: list[dict] = []
    all_events = sorted(events, key=_order_key)

    for pos, ev in enumerate(all_events):
        action = ev.get("action", "")
        ts = int(ev.get("timestamp_ms") or 0)
        params = parse_params(ev.get("parameters", "{}"))
        if action == "emit_tree_data":
            emit_events.append({"ts": ts, "pos": pos, "params": params})

    if len(emit_events) < 2:
        return {
            "votat_rate": 0.0, "votat_intervals": [], "total_emits": len(emit_events),
            "b15_observed": False, "b15_level": None,
        }

    intervals = []
    for a, b in zip(emit_events[:-1], emit_events[1:]):
        ts_a, ts_b = a["ts"], b["ts"]
        # Collect events between the two emits (by position in time order)
        between = all_events[a["pos"] + 1:b["pos"]]
        pred_changes = sum(1 for ev in between if ev.get("action") == "drop_attribute")
        thresh_changes = sum(1 for ev in between if ev.get("action") == "change_split_values")

        only_pred = pred_changes > 0 and thresh_changes == 0
        only_thresh = thresh_changes > 0 and pred_changes == 0
        is_votat = only_pred or only_thresh
        dim = "predictor" if only_pred else ("threshold" if only_thresh else "none_or_both")

        intervals.append({
            "emit_a_ms": ts_a,
            "emit_b_ms": ts_b,
            "predictor_changes": pred_changes,
            "threshold_changes": thresh_changes,
            "is_votat": is_votat,
            "dimension_changed": dim,
        })

    n_votat = sum(1 for iv in intervals if iv["is_votat"])
    votat_rate = round(n_votat / len(intervals), 3) if intervals else 0.0

    # Count max consecutive VOTAT run
    max_run = cur_run = 0
    for iv in intervals:
        if iv["is_votat"]:
            cur_run += 1
            max_run = max(max_run, cur_run)
        else:
            cur_run = 0

    b15_observed = max_run >= 2
    b15_level = "Deepen" if max_run >= 3 else ("Acquire" if max_run >= 2 else None)

    return {
        "votat_rate": votat_rate,
        "votat_intervals": intervals,
        "total_emits": len(emit_events),
        "max_consecutive_votat": max_run,
        "b15_observed": b15_observed,
        "b15_level": b15_level,
    }


def run(session_key: str) -> None:
    rows = load_log(session_key)
    if not rows:
        print(f"[{session_key}] No log file found.")
        return

    by_student: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_student[row["student_id"]].append(row)

    session_dir = DATA_ROOT / SESSION_DIRS[session_key]
    print(f"\n[{session_key}] {len(by_student)} students in log")

    for student, events in sorted(by_student.items()):
        result = compute_votat(events)
        result["student_id"] = student
        result["session_key"] = session_key
        result["session_date"] = SESSION_DATES[session_key]
        result["computed_at"] = datetime.now(timezone.utc).isoformat()
        result["source"] = "2026_codap_event_log"
        result["filter"] = "created_at date == session_date; ordered by created_at"

        out_dir = session_dir / student
        if not out_dir.is_dir():
            print(f"  [{student}] output dir not found: {out_dir} — skipped")
            continue

        out_path = out_dir / f"{student}_{session_key}_b15_log.json"
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        obs = "OBSERVED" if result["b15_observed"] else "not_observed"
        print(
            f"  [{student}] emits={result['total_emits']}  "
            f"votat_rate={result['votat_rate']:.0%}  "
            f"max_run={result['max_consecutive_votat']}  "
            f"B15={obs} ({result['b15_level'] or '-'})"
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute B15 VOTAT from 2026 CODAP logs")
    ap.add_argument("--session", choices=["21apr", "28apr", "all"], default="all")
    args = ap.parse_args()

    sessions = ["21apr", "28apr"] if args.session == "all" else [args.session]
    for ses in sessions:
        run(ses)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
