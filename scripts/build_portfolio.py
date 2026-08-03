#!/usr/bin/env python3
"""Build per-student portfolio summaries from scored 2026 sessions.

For each student who has final_scored.json files across sessions, this script:
  1. Merges CODAP Arbor sessions (21apr and/or 28apr) with B15 log results
  2. Merges Colab Python session (05may) if present
  3. Produces a portfolio_summary.json per student in outputs/portfolios/
  4. Writes a cohort-level summary CSV

Behavior levels across sessions are aggregated as:
  - Deepen in ANY session  → portfolio level = Deepen
  - Acquire in ANY session → portfolio level = Acquire (if no Deepen)
  - All not_observed       → not_observed
  - All not_measurable     → not_measurable

Usage:
    python scripts/build_portfolio.py
    python scripts/build_portfolio.py --student Amy
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = REPO_ROOT / "data_sources_2026"
OUT_DIR = REPO_ROOT / "outputs" / "portfolios"

SESSION_DIRS = {
    "21apr": "codap_arbor_21april_audio",
    "28apr": "codap_arbor_28april_audio",
    "05may": "colab_python_audio",
}

ALL_BEHAVIORS = [
    "B0", "B1", "B2", "B3", "B4", "B5", "B6", "B7",
    "B8", "B9", "B10", "B11", "B12", "B13",
    "B14", "B15", "B16", "B17",
]

LEVEL_RANK = {"Deepen": 3, "Acquire": 2, "not_observed": 1, "not_measurable": 0, None: -1}


def load_final_scored(student: str, session_key: str) -> dict | None:
    path = DATA_ROOT / SESSION_DIRS[session_key] / student / f"{student}_{session_key}_final_scored.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_b15_log(student: str, session_key: str) -> dict | None:
    if session_key not in ("21apr", "28apr"):
        return None
    path = DATA_ROOT / SESSION_DIRS[session_key] / student / f"{student}_{session_key}_b15_log.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def best_level(levels: list[str | None]) -> str | None:
    """Return the highest-ranked level across sessions."""
    best = None
    for lv in levels:
        if LEVEL_RANK.get(lv, -1) > LEVEL_RANK.get(best, -1):
            best = lv
    return best


def merge_behavior(bid: str, session_records: list[dict]) -> dict:
    """Merge one behavior across all available session records."""
    decisions: list[str | None] = []
    levels: list[str | None] = []
    confidences: list[str | None] = []
    evidence_sources: list[str] = []

    for rec in session_records:
        bdata = rec.get("behaviors", {}).get(bid, {})
        if not bdata:
            continue
        decision = bdata.get("decision")
        level = bdata.get("level")
        conf = bdata.get("confidence")
        decisions.append(decision)
        levels.append(level)
        confidences.append(conf)
        n_frames = len(bdata.get("frame_evidence", []))
        if n_frames:
            evidence_sources.append(f"{rec['_session_key']}: {n_frames} frames")

    if not decisions:
        return {"decision": "not_scored", "level": None, "confidence": None, "sessions_with_evidence": []}

    # Aggregate decision
    if "not_measurable" in decisions and all(d in ("not_measurable", None) for d in decisions):
        agg_decision = "not_measurable"
        agg_level = None
    elif any(d == "observed" for d in decisions):
        agg_decision = "observed"
        agg_level = best_level(levels)
    else:
        agg_decision = "not_observed"
        agg_level = None

    # Aggregate confidence: highest that appeared
    conf_rank = {"High": 3, "Medium": 2, "Low": 1, None: 0}
    agg_conf = max(confidences, key=lambda c: conf_rank.get(c, 0), default=None)

    return {
        "decision": agg_decision,
        "level": agg_level,
        "confidence": agg_conf,
        "sessions_with_evidence": evidence_sources,
    }


def build_student_portfolio(student: str) -> dict | None:
    session_records: list[dict] = []

    for ses_key in ("21apr", "28apr", "05may"):
        scored = load_final_scored(student, ses_key)
        if scored is None:
            continue
        scored["_session_key"] = ses_key

        # Merge B15 from log if available
        b15_log = load_b15_log(student, ses_key)
        if b15_log and b15_log.get("b15_observed"):
            level = b15_log["b15_level"]
            existing = scored.get("behaviors", {}).get("B15", {})
            if existing.get("decision") not in ("observed",) or LEVEL_RANK.get(level, 0) > LEVEL_RANK.get(existing.get("level"), 0):
                scored.setdefault("behaviors", {})["B15"] = {
                    "decision": "observed",
                    "level": level,
                    "confidence": "High",
                    "reason": f"VOTAT rate={b15_log['votat_rate']:.0%}, max_run={b15_log['max_consecutive_votat']}",
                    "frame_evidence": [],
                    "source": "log_derived",
                }
        session_records.append(scored)

    if not session_records:
        return None

    behaviors: dict[str, dict] = {}
    for bid in ALL_BEHAVIORS:
        behaviors[bid] = merge_behavior(bid, session_records)

    sessions_scored = [r["_session_key"] for r in session_records]
    has_codap = any(s in sessions_scored for s in ("21apr", "28apr"))
    has_colab = "05may" in sessions_scored

    return {
        "student_id": student,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rubric_version": "codap_arbor_v4.1",
        "sessions_scored": sessions_scored,
        "has_codap_sessions": has_codap,
        "has_colab_session": has_colab,
        "behaviors": behaviors,
        "summary": {
            "deepen_count": sum(1 for b in behaviors.values() if b.get("level") == "Deepen"),
            "acquire_count": sum(1 for b in behaviors.values() if b.get("level") == "Acquire"),
            "not_observed_count": sum(1 for b in behaviors.values() if b.get("decision") == "not_observed"),
            "not_measurable_count": sum(1 for b in behaviors.values() if b.get("decision") == "not_measurable"),
        },
    }


def all_students() -> list[str]:
    students: set[str] = set()
    for ses_dir in SESSION_DIRS.values():
        d = DATA_ROOT / ses_dir
        if d.is_dir():
            for sub in d.iterdir():
                if sub.is_dir():
                    students.add(sub.name)
    return sorted(students)


def write_cohort_csv(portfolios: list[dict]) -> Path:
    csv_path = OUT_DIR / "cohort_portfolio_summary.csv"
    fieldnames = ["student_id", "sessions_scored"] + [
        f"{bid}_decision" for bid in ALL_BEHAVIORS
    ] + [f"{bid}_level" for bid in ALL_BEHAVIORS] + [
        "deepen_count", "acquire_count", "not_observed_count"
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for p in portfolios:
            row: dict = {
                "student_id": p["student_id"],
                "sessions_scored": "|".join(p["sessions_scored"]),
            }
            for bid in ALL_BEHAVIORS:
                b = p["behaviors"].get(bid, {})
                row[f"{bid}_decision"] = b.get("decision", "not_scored")
                row[f"{bid}_level"] = b.get("level") or ""
            row.update(p["summary"])
            w.writerow(row)
    return csv_path


def main() -> int:
    ap = argparse.ArgumentParser(description="Build 2026 student portfolios")
    ap.add_argument("--student", help="Score only this student")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    students = [args.student] if args.student else all_students()
    portfolios: list[dict] = []

    print(f"\nBuilding portfolios for {len(students)} students...\n")
    for sid in students:
        p = build_student_portfolio(sid)
        if p is None:
            print(f"  [{sid}] no scored sessions found — skipped")
            continue
        out = OUT_DIR / f"{sid}_portfolio.json"
        out.write_text(json.dumps(p, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        portfolios.append(p)
        d = p["summary"]["deepen_count"]
        a = p["summary"]["acquire_count"]
        print(
            f"  [{sid}] sessions={','.join(p['sessions_scored'])}  "
            f"Deepen={d}  Acquire={a}  → {out.name}"
        )

    if portfolios:
        csv_path = write_cohort_csv(portfolios)
        print(f"\nCohort CSV: {csv_path.relative_to(REPO_ROOT)}")
        print(f"Portfolio JSONs: {OUT_DIR.relative_to(REPO_ROOT)}/")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
