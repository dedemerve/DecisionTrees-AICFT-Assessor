#!/usr/bin/env python3
"""
Score WS14 (Xeno) and WS15 (Titanic) for all students via LLM rubric scoring.

Extraction artifacts exist for all 15 students but no scoring.json was produced
after the WS_DT_XENO/WS_DT_TITANIC -> WS14/WS15 rename. This script recovers
those scores without touching any existing extraction artifacts.

Usage:
    python scripts/score_ws13_ws14.py                    # all students, both worksheets
    python scripts/score_ws13_ws14.py Bruno Helena       # specific students
    python scripts/score_ws13_ws14.py --worksheet WS14   # one worksheet only
    python scripts/score_ws13_ws14.py --dry-run          # report coverage, no API calls
    python scripts/score_ws13_ws14.py --force            # re-score even if scoring.json exists

Requires ANTHROPIC_API_KEY in the environment.
Output: students/<student>/WS14/scoring.json and/or students/<student>/WS15/scoring.json
Audit:  logs/score_ws13_ws14_<run_id>.jsonl
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline_schema import load_rubric, scoring_item_ids
from rubric_deterministic import score_from_credit
from student_bundle import (
    STUDENTS_DIR,
    artifact_payload,
    extraction_responses,
    load_artifact,
    save_scoring_bundle,
)

LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

MODEL = "claude-sonnet-5-5"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0

NO_ANSWER = frozenset({"(not_extracted)", "(bos)", "(okunamiyor)", "(missing)", "", None})

ALL_STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel",
    "Marco", "Marcus", "Melinda", "Nadia", "Serena",
    "Shana", "Sheila", "Ulysses", "Zara",
]
TARGET_WORKSHEETS = ("WS14", "WS15")

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("score_ws13_ws14")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def coverage_summary(responses: dict[str, str]) -> dict[str, Any]:
    answered = sum(1 for v in responses.values() if v not in NO_ANSWER)
    blank = sum(1 for v in responses.values() if v in {"(bos)", "(okunamiyor)"})
    missing = sum(1 for v in responses.values() if v in {"(not_extracted)", "(missing)", None, ""})
    total = len(responses)
    return {
        "answered": answered,
        "blank_or_illegible": blank,
        "missing": missing,
        "total": total,
        "completion_rate": round(answered / total, 3) if total else 0.0,
    }


def assess_with_retry(
    client: Any,
    student_id: str,
    worksheet: str,
    responses: dict[str, str],
    model: str,
    audit_log: list[dict],
) -> Any:
    import anthropic
    from worksheet_assessor import assess_worksheet

    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return assess_worksheet(client, student_id, worksheet, responses, model=model)
        except (
            anthropic.RateLimitError,
            anthropic.APITimeoutError,
            anthropic.APIConnectionError,
        ) as exc:
            last_exc = exc
            if attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                log.warning("%s %s attempt %d/%d — retrying in %.0fs: %s",
                            student_id, worksheet, attempt, MAX_RETRIES, delay, exc)
                audit_log.append({
                    "ts": _now(), "student": student_id, "worksheet": worksheet,
                    "event": "retry", "attempt": attempt, "error": str(exc),
                })
                time.sleep(delay)
        except anthropic.APIStatusError as exc:
            last_exc = exc
            if exc.status_code in (429, 500, 502, 503, 529) and attempt < MAX_RETRIES:
                delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
                log.warning("%s %s HTTP %d — retrying in %.0fs",
                            student_id, worksheet, exc.status_code, delay)
                audit_log.append({
                    "ts": _now(), "student": student_id, "worksheet": worksheet,
                    "event": "retry", "attempt": attempt, "http_status": exc.status_code,
                })
                time.sleep(delay)
            else:
                raise
    raise last_exc


def score_student_worksheet(
    client: Any,
    student_id: str,
    worksheet: str,
    model: str,
    force: bool,
    audit_log: list[dict],
) -> dict[str, Any]:
    result = {
        "ts": _now(), "student": student_id, "worksheet": worksheet,
        "outcome": None, "total_score": None, "max_score": None,
        "n_items": None, "n_review": 0, "error": None,
    }

    # Guard: never overwrite extraction
    ext_path = STUDENTS_DIR / student_id / worksheet / "extraction.json"
    if not ext_path.exists():
        result.update({"outcome": "skip_no_extraction"})
        log.warning("%s %s — no extraction.json, skipping", student_id, worksheet)
        return result

    # Skip if already scored (unless --force)
    scoring_path = STUDENTS_DIR / student_id / worksheet / "scoring.json"
    if scoring_path.exists() and not force:
        result.update({"outcome": "skip_already_scored"})
        log.info("%s %s — scoring.json exists, skipping (use --force to re-score)", student_id, worksheet)
        return result

    extraction = load_artifact(student_id, worksheet, "extraction", STUDENTS_DIR)
    responses = extraction_responses(artifact_payload(extraction))
    cov = coverage_summary(responses)
    result["coverage"] = cov

    if cov["answered"] == 0:
        result.update({"outcome": "skip_no_responses", "error": "all items not_extracted"})
        log.warning("%s %s — 0 answered items, skipping scoring", student_id, worksheet)
        return result

    rubric = load_rubric(worksheet)
    rubric_items = rubric.get("items", {})
    scored_ids = scoring_item_ids(worksheet)

    log.info("%s %s — calling LLM (%d answered / %d items)",
             student_id, worksheet, cov["answered"], cov["total"])

    assessment = assess_with_retry(client, student_id, worksheet, responses, model, audit_log)

    items_out = []
    total = 0.0
    max_total = 0.0
    n_review = 0

    for item in assessment.item_scores:
        cfg = rubric_items.get(item.item_id, {})
        max_score = float(cfg.get("max_score", 1))
        max_total += max_score
        score = score_from_credit({"credit": item.credit}, max_score)
        total += score
        needs_review = item.credit in {"partial", "zero"} or item.flag is not None
        if needs_review:
            n_review += 1
        items_out.append({
            "item": item.item_id,
            "score": score,
            "max_score": max_score,
            "confidence": 1.0 if item.credit == "full" and not item.flag else 0.6,
            "review": needs_review,
            "credit": item.credit,
            "rationale": item.llm_rationale,
            "evidence": item.evidence_quote,
            "flag": item.flag,
        })

    # Verify item count
    expected = len(scored_ids)
    actual = len(items_out)
    if actual != expected:
        log.warning("%s %s — expected %d items, got %d from assessment",
                    student_id, worksheet, expected, actual)

    scoring = {
        "stage": "scoring",
        "student_id": student_id,
        "worksheet": worksheet,
        "total_score": round(total, 2),
        "max_score": round(max_total, 2),
        "items": items_out,
        "note": f"LLM-scored via worksheet_assessor.assess_worksheet (model={model}); {n_review} item(s) flagged for review.",
        "scored_at": _now(),
        "scoring_model": model,
        "coverage": cov,
    }

    save_scoring_bundle(student_id, worksheet, scoring, base_dir=STUDENTS_DIR)

    result.update({
        "outcome": "scored",
        "total_score": round(total, 2),
        "max_score": round(max_total, 2),
        "n_items": len(items_out),
        "n_review": n_review,
    })
    log.info("%s %s — scored %.1f / %.1f (%d items, %d for review)",
             student_id, worksheet, total, max_total, len(items_out), n_review)
    return result


def dry_run_report(students: list[str], worksheets: tuple[str, ...]) -> None:
    print("\nDRY RUN — coverage report (no API calls)")
    print(f"{'Student':<12} {'WS':<5} {'Extraction':<12} {'Scoring':<10} {'Answered':<10} {'Completion'}")
    print("-" * 65)
    for ws in worksheets:
        for s in students:
            ext_path = STUDENTS_DIR / s / ws / "extraction.json"
            score_path = STUDENTS_DIR / s / ws / "scoring.json"
            if not ext_path.exists():
                print(f"{s:<12} {ws:<5} {'MISSING':<12} {'—':<10} {'—':<10}")
                continue
            extraction = load_artifact(s, ws, "extraction", STUDENTS_DIR)
            responses = extraction_responses(artifact_payload(extraction))
            cov = coverage_summary(responses)
            has_scoring = "EXISTS" if score_path.exists() else "missing"
            print(f"{s:<12} {ws:<5} {'pass':<12} {has_scoring:<10} {cov['answered']}/{cov['total']:<8} {cov['completion_rate']:.0%}")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Score WS14 (Xeno) and WS15 (Titanic)")
    parser.add_argument("students", nargs="*", help="Student IDs (default: all)")
    parser.add_argument("--worksheet", choices=["WS14", "WS15"],
                        help="Score one worksheet only")
    parser.add_argument("--force", action="store_true",
                        help="Re-score even if scoring.json already exists")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show coverage report only; no API calls")
    parser.add_argument("--model", default=MODEL, help=f"Claude model ID (default: {MODEL})")
    args = parser.parse_args()

    students = args.students if args.students else ALL_STUDENTS
    worksheets = (args.worksheet,) if args.worksheet else TARGET_WORKSHEETS

    if args.dry_run:
        dry_run_report(students, worksheets)
        return 0

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        log.error(
            "ANTHROPIC_API_KEY is not set.\n"
            "  export ANTHROPIC_API_KEY='sk-...'\n"
            "  python scripts/score_ws13_ws14.py"
        )
        return 1

    import anthropic
    client = anthropic.Anthropic(api_key=api_key)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    audit_path = LOG_DIR / f"score_ws13_ws14_{run_id}.jsonl"
    audit_log: list[dict] = []

    results = []
    for ws in worksheets:
        for s in students:
            row = score_student_worksheet(client, s, ws, args.model, args.force, audit_log)
            results.append(row)
            audit_log.append(row)
            with audit_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Summary
    scored = [r for r in results if r["outcome"] == "scored"]
    skipped = [r for r in results if r["outcome"] and r["outcome"].startswith("skip")]
    errors = [r for r in results if r["outcome"] == "error"]

    print(f"\n=== Run {run_id} ===")
    print(f"Scored:  {len(scored)}")
    print(f"Skipped: {len(skipped)}")
    print(f"Errors:  {len(errors)}")
    if scored:
        print("\nScored results:")
        for r in scored:
            print(f"  {r['student']:<12} {r['worksheet']:<5} {r['total_score']}/{r['max_score']}  ({r['n_review']} for review)")
    if errors:
        print("\nErrors:")
        for r in errors:
            print(f"  {r['student']:<12} {r['worksheet']:<5} {r['error']}")
    print(f"\nAudit log: {audit_path}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
