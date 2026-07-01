#!/usr/bin/env python3
"""orchestrator.py — run validation -> scoring -> evidence -> portfolio for one or more students.

Usage:
  python orchestrator.py Sample_Student
  python orchestrator.py --all
  python orchestrator.py Ozzy Ally Bella --workers 3
  python orchestrator.py --all --llm-score          # also scores WS1/WS3/WS4 via Claude

Scope
-----
Deterministic path (always runs): Group B validation + scoring (WS5, WS6, WS7),
WS10 validation + scoring, WS11 deterministic items (Q10-Q12), evidence_units.json
build + schema validation, confidence calibration, portfolio.json build.

Optional LLM path (--llm-score, requires ANTHROPIC_API_KEY): interpretive scoring
for WS1, WS3, WS4 via worksheet_assessor.assess_worksheet. WS_DT is intentionally
excluded — it needs log_extractor-derived features (assess_worksheet_dt) that this
orchestrator does not assemble; score it separately until that wiring exists.

Students are processed concurrently (ThreadPoolExecutor, --workers, default 3) so
that --llm-score run time is bounded by Claude round-trips rather than the student
count, without exceeding a small number of concurrent API calls.

Diagnostics
-----------
Every worksheet outcome (success, missing extraction, known validation failure
reason, review flag, exception) is written to one run-scoped JSONL file under
logs/ — the first place these are aggregated across students instead of sitting
individually inside each student's validation.json / scoring.json.

Review manifest
----------------
After the run, every item flagged for review (deterministic reason codes,
review=True scoring items, or LLM credit/flag) is collected into
pending_manual_review/<run_id>_manifest.json. Entries point at the canonical
students/<id>/<ws>/scoring.json path rather than copying files out — a copy would
drift from the source of truth the moment anyone re-runs scoring.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from confidence_calibration import calibrate_student_scoring
from evidence_unit_runtime import build_and_save_evidence_units
from pipeline_integration import (
    score_ws5_deterministic,
    score_ws6_deterministic,
    score_ws7_deterministic,
    score_ws10_deterministic,
    score_ws11_deterministic,
)
from pipeline_schema import load_rubric
from portfolio_builder import build_and_save_portfolio
from rubric_deterministic import score_from_credit
from schema_validate import validate_evidence_units
from student_bundle import (
    STUDENTS_DIR,
    _VALID_STUDENT_ID,
    artifact_payload,
    extraction_responses,
    list_student_ids,
    load_artifact,
    save_artifact,
    save_scoring_bundle,
    write_student_manifest,
)
from ws10_validation import validate_ws10_extraction
from ws_extraction_normalize import normalize_scoring_responses
from worksheet_validation import build_technical_validation

GROUP_B_WORKSHEETS = ("WS5", "WS6", "WS7")
GROUP_A_LLM_WORKSHEETS = ("WS1", "WS3", "WS4")  # WS_DT needs assess_worksheet_dt + log features
KNOWN_DIAGNOSTIC_REASONS = {"unparseable_threshold", "arithmetic_inconsistent", "rubric_item_missing"}

LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
REVIEW_DIR = REPO_ROOT / "pending_manual_review"
REVIEW_DIR.mkdir(exist_ok=True)

log = logging.getLogger("orchestrator")
log.setLevel(logging.INFO)
_console = logging.StreamHandler()
_console.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
log.addHandler(_console)


class DiagnosticLog:
    """Central run-scoped diagnostic sink: console + JSONL file. Thread-safe."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.path = LOG_DIR / f"orchestrator_run_{run_id}.jsonl"
        self._fh = self.path.open("a", encoding="utf-8")
        self._lock = threading.Lock()
        self.records: list[dict[str, Any]] = []

    def record(self, *, student_id: str, worksheet: str, stage: str, level: str,
               status: str, reason: str = "", detail: str = "") -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "student_id": student_id,
            "worksheet": worksheet,
            "stage": stage,
            "status": status,  # "success" | "failed" | "skipped"
            "level": level,
            "reason": reason,
            "detail": detail,
        }
        with self._lock:
            self.records.append(entry)
            self._fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            self._fh.flush()
        getattr(log, level.lower(), log.info)(f"[{student_id}/{worksheet}/{stage}] {status} {reason} {detail}".strip())

    def close(self) -> None:
        self._fh.close()


def _review_items_from_scoring(student_id: str, worksheet: str, diag: DiagnosticLog) -> list[dict[str, Any]]:
    try:
        scoring = load_artifact(student_id, worksheet, "scoring", STUDENTS_DIR)
    except Exception as exc:  # noqa: BLE001 — best-effort review scan; corrupt file shouldn't sink the run
        diag.record(student_id=student_id, worksheet=worksheet, stage="review_scan",
                     level="error", status="failed", reason="corrupt_artifact", detail=str(exc))
        return []
    if not scoring:
        return []
    out = []
    for rec in artifact_payload(scoring).get("items", []):
        if rec.get("review"):
            out.append({
                "student_id": student_id,
                "worksheet": worksheet,
                "item": rec.get("item"),
                "score": rec.get("score"),
                "confidence": rec.get("confidence"),
                "path": f"students/{student_id}/{worksheet}/scoring.json",
            })
    return out


def _score_group_b(student_id: str, worksheet: str, diag: DiagnosticLog) -> bool:
    extraction = load_artifact(student_id, worksheet, "extraction", STUDENTS_DIR)
    if not extraction:
        diag.record(student_id=student_id, worksheet=worksheet, stage="scoring",
                     level="warning", status="skipped", reason="missing_extraction")
        return False

    ext = artifact_payload(extraction)
    responses = normalize_scoring_responses(worksheet, extraction_responses(ext))
    validation = build_technical_validation(worksheet, extraction, student_id=student_id)
    save_artifact(student_id, worksheet, "validation",
                  {"stage": "validation", "student_id": student_id, "worksheet": worksheet, **validation},
                  STUDENTS_DIR)

    for item_id, check in (validation.get("deterministic_checks") or {}).items():
        reason = check.get("reason")
        if reason in KNOWN_DIAGNOSTIC_REASONS:
            diag.record(student_id=student_id, worksheet=worksheet, stage="validation",
                         level="warning", status="failed", reason=reason, detail=item_id)

    scorer = {"WS5": score_ws5_deterministic, "WS6": score_ws6_deterministic, "WS7": score_ws7_deterministic}[worksheet]
    scoring = scorer(responses, student_id, validation=validation)
    save_scoring_bundle(student_id, worksheet, scoring, base_dir=STUDENTS_DIR)
    diag.record(student_id=student_id, worksheet=worksheet, stage="scoring", level="info", status="success",
                detail=f"{scoring.get('total_score')}/{scoring.get('max_score')}")
    return True


def _score_ws10(student_id: str, diag: DiagnosticLog) -> bool:
    extraction = load_artifact(student_id, "WS10", "extraction", STUDENTS_DIR)
    if not extraction:
        diag.record(student_id=student_id, worksheet="WS10", stage="scoring",
                     level="warning", status="skipped", reason="missing_extraction")
        return False
    responses = extraction_responses(artifact_payload(extraction))
    validation = validate_ws10_extraction(responses)
    save_artifact(student_id, "WS10", "validation",
                  {"stage": "validation", "student_id": student_id, "worksheet": "WS10", **validation},
                  STUDENTS_DIR)
    scoring = score_ws10_deterministic(responses, student_id)
    save_scoring_bundle(student_id, "WS10", scoring, base_dir=STUDENTS_DIR)
    diag.record(student_id=student_id, worksheet="WS10", stage="scoring", level="info", status="success",
                detail=f"{scoring.get('total_score')}/{scoring.get('max_score')}")
    return True


def _score_ws11(student_id: str, diag: DiagnosticLog) -> bool:
    extraction = load_artifact(student_id, "WS11", "extraction", STUDENTS_DIR)
    if not extraction:
        diag.record(student_id=student_id, worksheet="WS11", stage="scoring",
                     level="warning", status="skipped", reason="missing_extraction")
        return False
    responses = extraction_responses(artifact_payload(extraction))
    existing = load_artifact(student_id, "WS11", "scoring", STUDENTS_DIR)
    interpretive = None
    if existing:
        # Interpretive (LLM-scored) items are whatever the WS11 rubric defines minus the
        # deterministic Q10-Q12 block scored here. Deriving this from the rubric — rather than
        # a hardcoded id list — avoids silently dropping/misnaming items when rubric ids change
        # (this previously referenced "WS11_B8a"/"WS11_B9", which do not exist in the current
        # rubric and crashed calibration downstream with a KeyError).
        deterministic_prefixes = ("WS11_Q10", "WS11_Q11", "WS11_Q12")
        rubric_items = set(load_rubric("WS11")["items"].keys())
        interpretive_ids = {
            iid for iid in rubric_items
            if not iid.startswith(deterministic_prefixes)
        }
        interpretive = {
            r["item"]: r
            for r in artifact_payload(existing).get("items", [])
            if r["item"] in interpretive_ids
        }
    scoring = score_ws11_deterministic(responses, student_id, interpretive_items=interpretive)
    save_scoring_bundle(student_id, "WS11", scoring, base_dir=STUDENTS_DIR)
    for rec in scoring.get("items", []):
        if rec.get("reason") in KNOWN_DIAGNOSTIC_REASONS:
            diag.record(student_id=student_id, worksheet="WS11", stage="scoring",
                         level="warning", status="failed", reason=rec["reason"], detail=rec.get("item", ""))
    diag.record(student_id=student_id, worksheet="WS11", stage="scoring", level="info", status="success",
                detail=f"{scoring.get('total_score')}/{scoring.get('max_score')}")
    return True


LLM_MAX_RETRIES = 3
LLM_RETRY_BASE_DELAY = 2.0  # seconds; doubles each retry


def _assess_worksheet_with_retry(assess_worksheet_fn, client, student_id, worksheet, responses, model, diag):
    """Retry transient Claude API errors (rate limit, timeout, overload) with backoff.

    A 15-student --llm-score batch makes dozens of sequential API calls per student;
    without this, one 429/503 aborts that student's whole worksheet instead of recovering.
    """
    import anthropic

    last_exc: Exception | None = None
    for attempt in range(1, LLM_MAX_RETRIES + 1):
        try:
            return assess_worksheet_fn(client, student_id, worksheet, responses, model=model)
        except (anthropic.RateLimitError, anthropic.APITimeoutError, anthropic.APIConnectionError) as exc:
            last_exc = exc
            if attempt < LLM_MAX_RETRIES:
                delay = LLM_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                diag.record(student_id=student_id, worksheet=worksheet, stage="llm_scoring",
                             level="warning", status="failed", reason="transient_api_error",
                             detail=f"attempt {attempt}/{LLM_MAX_RETRIES}, retrying in {delay:.0f}s: {exc}")
                time.sleep(delay)
        except anthropic.APIStatusError as exc:
            last_exc = exc
            if exc.status_code in (429, 500, 502, 503, 529) and attempt < LLM_MAX_RETRIES:
                delay = LLM_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                diag.record(student_id=student_id, worksheet=worksheet, stage="llm_scoring",
                             level="warning", status="failed", reason="transient_api_error",
                             detail=f"attempt {attempt}/{LLM_MAX_RETRIES}, retrying in {delay:.0f}s: {exc}")
                time.sleep(delay)
            else:
                raise
    raise last_exc  # noqa: RSE102 — exhausted retries, surface the last transient error


def _score_group_a_llm(student_id: str, worksheet: str, client: Any, model: str, diag: DiagnosticLog) -> bool:
    from worksheet_assessor import assess_worksheet  # imports anthropic; only needed on this path

    extraction = load_artifact(student_id, worksheet, "extraction", STUDENTS_DIR)
    if not extraction:
        diag.record(student_id=student_id, worksheet=worksheet, stage="llm_scoring",
                     level="warning", status="skipped", reason="missing_extraction")
        return False

    responses = extraction_responses(artifact_payload(extraction))
    rubric = load_rubric(worksheet)
    assessment = _assess_worksheet_with_retry(assess_worksheet, client, student_id, worksheet, responses, model, diag)

    items_out = []
    total = 0.0
    max_total = 0.0
    flagged = 0
    for item in assessment.item_scores:
        cfg = rubric["items"].get(item.item_id, {})
        max_score = float(cfg.get("max_score", 1))
        max_total += max_score
        score = score_from_credit({"credit": item.credit}, max_score)
        total += score
        review = item.credit in {"partial", "zero"} or item.flag is not None
        if review:
            flagged += 1
            diag.record(student_id=student_id, worksheet=worksheet, stage="llm_scoring",
                         level="warning", status="failed" if item.credit == "zero" else "success",
                         reason=item.flag or f"llm_credit_{item.credit}", detail=item.item_id)
        items_out.append({
            "item": item.item_id,
            "score": score,
            "confidence": 1.0 if item.credit == "full" and not item.flag else 0.6,
            "review": review,
        })

    scoring = {
        "blocked": False,
        "items": items_out,
        "total_score": total,
        "max_score": max_total,
        "note": f"LLM-scored via worksheet_assessor.assess_worksheet (model={model}); {flagged} item(s) flagged for review.",
    }
    save_scoring_bundle(student_id, worksheet, scoring, base_dir=STUDENTS_DIR)
    diag.record(student_id=student_id, worksheet=worksheet, stage="llm_scoring", level="info", status="success",
                detail=f"{total}/{max_total}, {flagged} flagged")
    return True


def _flag_group_a_gaps(student_id: str, diag: DiagnosticLog, skip: set[str]) -> None:
    for worksheet in (*GROUP_A_LLM_WORKSHEETS, "WS_DT"):
        if worksheet in skip:
            continue
        try:
            extraction = load_artifact(student_id, worksheet, "extraction", STUDENTS_DIR)
            if not extraction:
                continue
            scoring = load_artifact(student_id, worksheet, "scoring", STUDENTS_DIR)
            if not scoring:
                diag.record(student_id=student_id, worksheet=worksheet, stage="scoring",
                             level="warning", status="skipped", reason="pending_llm_scoring",
                             detail="run --llm-score (WS1/WS3/WS4) or assess_worksheet_dt manually (WS_DT)")
        except Exception as exc:  # noqa: BLE001 — a corrupt artifact here must not sink the whole student
            diag.record(student_id=student_id, worksheet=worksheet, stage="scoring",
                         level="error", status="failed", reason="corrupt_artifact", detail=str(exc))


def _run_student_body(student_id: str, diag: DiagnosticLog, *, llm_client: Any, llm_model: str) -> dict[str, Any]:
    log.info("=== %s ===", student_id)
    result: dict[str, Any] = {"student_id": student_id, "worksheets_scored": [], "errors": []}

    for worksheet in GROUP_B_WORKSHEETS:
        try:
            if _score_group_b(student_id, worksheet, diag):
                result["worksheets_scored"].append(worksheet)
        except Exception as exc:  # noqa: BLE001 — record and continue with other worksheets/students
            diag.record(student_id=student_id, worksheet=worksheet, stage="scoring",
                         level="error", status="failed", reason="exception", detail=str(exc))
            result["errors"].append(f"{worksheet}: {exc}")

    for label, fn in (("WS10", _score_ws10), ("WS11", _score_ws11)):
        try:
            if fn(student_id, diag):
                result["worksheets_scored"].append(label)
        except Exception as exc:  # noqa: BLE001
            diag.record(student_id=student_id, worksheet=label, stage="scoring",
                         level="error", status="failed", reason="exception", detail=str(exc))
            result["errors"].append(f"{label}: {exc}")

    llm_scored: set[str] = set()
    if llm_client is not None:
        for worksheet in GROUP_A_LLM_WORKSHEETS:
            try:
                if _score_group_a_llm(student_id, worksheet, llm_client, llm_model, diag):
                    result["worksheets_scored"].append(worksheet)
                    llm_scored.add(worksheet)
            except Exception as exc:  # noqa: BLE001
                diag.record(student_id=student_id, worksheet=worksheet, stage="llm_scoring",
                             level="error", status="failed", reason="exception", detail=str(exc))
                result["errors"].append(f"{worksheet}: {exc}")

    _flag_group_a_gaps(student_id, diag, skip=llm_scored)

    try:
        eu_path = build_and_save_evidence_units(student_id)
        write_student_manifest(student_id)
        eu_doc = json.loads(eu_path.read_text(encoding="utf-8"))
        eu_errors = validate_evidence_units(eu_doc, str(eu_path.relative_to(REPO_ROOT)))
        if eu_errors:
            diag.record(student_id=student_id, worksheet="-", stage="evidence_units",
                         level="error", status="failed", reason="schema_invalid",
                         detail="; ".join(eu_errors))
            result["errors"].append(f"evidence_units: {len(eu_errors)} schema error(s)")
        else:
            diag.record(student_id=student_id, worksheet="-", stage="evidence_units", level="info", status="success")
    except Exception as exc:  # noqa: BLE001
        diag.record(student_id=student_id, worksheet="-", stage="evidence_units",
                     level="error", status="failed", reason="exception", detail=str(exc))
        result["errors"].append(f"evidence_units: {exc}")

    try:
        calibrate_student_scoring(student_id)
        diag.record(student_id=student_id, worksheet="-", stage="calibration", level="info", status="success")
    except Exception as exc:  # noqa: BLE001
        diag.record(student_id=student_id, worksheet="-", stage="calibration",
                     level="error", status="failed", reason="exception", detail=str(exc))
        result["errors"].append(f"calibration: {exc}")

    try:
        portfolio = build_and_save_portfolio(student_id)
        result["data_gaps"] = portfolio.get("data_gaps", [])
        diag.record(student_id=student_id, worksheet="-", stage="portfolio", level="info", status="success")
    except Exception as exc:  # noqa: BLE001
        diag.record(student_id=student_id, worksheet="-", stage="portfolio",
                     level="error", status="failed", reason="exception", detail=str(exc))
        result["errors"].append(f"portfolio: {exc}")

    result["review_items"] = [
        item
        for worksheet in (*GROUP_B_WORKSHEETS, "WS10", "WS11", *GROUP_A_LLM_WORKSHEETS)
        for item in _review_items_from_scoring(student_id, worksheet, diag)
    ]
    return result


def run_student(student_id: str, diag: DiagnosticLog, *, llm_client: Any, llm_model: str) -> dict[str, Any]:
    """Thin crash-containment wrapper around _run_student_body.

    Every known failure mode inside the body is already caught per-stage and recorded, but this
    outer guard exists so that an unanticipated bug (e.g. a new corrupt-artifact shape a stress
    test hasn't hit yet) degrades to "this one student failed" instead of losing the whole batch's
    diagnostic log and review manifest — a single bad file used to be able to take down a 15-student
    run because the exception propagated out through ThreadPoolExecutor.future.result().
    """
    try:
        return _run_student_body(student_id, diag, llm_client=llm_client, llm_model=llm_model)
    except Exception as exc:  # noqa: BLE001 — last line of defense, see docstring
        diag.record(student_id=student_id, worksheet="-", stage="run_student",
                     level="error", status="failed", reason="unhandled_exception", detail=str(exc))
        return {"student_id": student_id, "worksheets_scored": [], "errors": [f"unhandled: {exc}"], "review_items": []}


def write_review_manifest(run_id: str, results: list[dict[str, Any]], diag: DiagnosticLog) -> Path:
    manifest = {
        "run_id": run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "review_items": [item for r in results for item in r.get("review_items", [])],
        "diagnostic_flags": [
            rec for rec in diag.records
            if rec["level"] in {"warning", "error"}
        ],
    }
    path = REVIEW_DIR / f"{run_id}_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run validation -> scoring -> evidence -> portfolio for one or more students")
    parser.add_argument("student_ids", nargs="*", help="Student directory keys; omit with --all")
    parser.add_argument("--all", action="store_true", help="Run for every student under students/")
    parser.add_argument("--workers", type=int, default=3, help="Concurrent students to process (default 3)")
    parser.add_argument("--llm-score", action="store_true",
                         help="Also LLM-score WS1/WS3/WS4 via worksheet_assessor (needs ANTHROPIC_API_KEY)")
    parser.add_argument("--llm-model", default="claude-sonnet-4-6")
    parser.add_argument("--json-summary", action="store_true", help="Print final summary as JSON")
    args = parser.parse_args()

    targets = list_student_ids() if args.all else args.student_ids
    if not targets:
        print("No students specified. Pass student ids or --all.", file=sys.stderr)
        return 1

    # Reject path-traversal / malformed ids (e.g. "../../etc") before touching the filesystem,
    # rather than letting student_dir()'s ValueError surface mid-run as a per-student failure.
    bad_ids = [sid for sid in targets if not _VALID_STUDENT_ID.match(sid)]
    if bad_ids:
        print(f"Invalid student id(s), refusing to run: {bad_ids!r}", file=sys.stderr)
        return 1

    workers = max(1, min(args.workers, 8))
    if args.workers != workers:
        print(f"--workers {args.workers} out of range, clamped to {workers}.", file=sys.stderr)
    if args.llm_score and workers > 5:
        print(f"Warning: --llm-score with --workers {workers} may hit Claude rate limits; "
              "consider --workers 3-5.", file=sys.stderr)

    llm_client = None
    if args.llm_score:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            print("--llm-score requires ANTHROPIC_API_KEY in the environment.", file=sys.stderr)
            return 1
        import anthropic
        llm_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    diag = DiagnosticLog(run_id)

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(run_student, sid, diag, llm_client=llm_client, llm_model=args.llm_model): sid
            for sid in targets
        }
        for future in as_completed(futures):
            sid = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:  # noqa: BLE001 — run_student already catches its own errors;
                # this only fires for a bug in run_student itself, and must not lose the rest of the batch.
                diag.record(student_id=sid, worksheet="-", stage="run_student",
                             level="error", status="failed", reason="unhandled_exception", detail=str(exc))
                results.append({"student_id": sid, "worksheets_scored": [], "errors": [f"unhandled: {exc}"], "review_items": []})
    diag.close()

    manifest_path = write_review_manifest(run_id, results, diag)
    failed = [r for r in results if r["errors"]]
    review_count = sum(len(r.get("review_items", [])) for r in results)
    log.info("Run complete: %d student(s), %d with errors, %d item(s) flagged for review.",
              len(results), len(failed), review_count)
    log.info("Diagnostic log: %s", diag.path)
    log.info("Review manifest: %s", manifest_path)

    if args.json_summary:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
