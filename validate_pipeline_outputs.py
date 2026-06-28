#!/usr/bin/env python3
"""
validate_pipeline_outputs.py — CI validation for rubrics and modular student artifacts.

Run: python validate_pipeline_outputs.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from confidence_calibration import apply_review_flag
from schema_validate import validate_all_mappings_v2, validate_portfolio_v1
from pipeline_schema import (
    WORKSHEETS_REQUIRING_VALIDATION,
    load_mapping,
    scoring_item_ids,
    validate_all_rubrics,
    WORKSHEET_ITEM_IDS,
)
from student_bundle import (
    artifact_payload,
    build_summary_from_scoring,
    extraction_responses,
    list_worksheets,
    load_artifact,
    portfolio_path,
    student_dir,
)

REPO_ROOT = Path(__file__).parent
EVIDENCE_STRENGTHS = frozenset({"none", "weak", "moderate", "strong"})
EVIDENCE_TYPES = frozenset({
    "direct", "supporting", "application", "early_indicator", "reflective", "prior_belief",
})
ENVELOPE_FIELDS = frozenset({"stage", "student_id", "worksheet"})


def _err(errors: list[str], msg: str) -> None:
    errors.append(msg)


def _validate_envelope(data: dict, stage: str, prefix: str, errors: list[str]) -> None:
    if data.get("schema_version") is not None:
        _err(errors, f"{prefix}: schema_version must not appear in pipeline output")
    if data.get("updated_at") is not None:
        _err(errors, f"{prefix}: updated_at must not appear in pipeline output")
    if data.get("stage") != stage:
        _err(errors, f"{prefix}: stage must be {stage!r}")
    for field in ("student_id", "worksheet"):
        if field not in data:
            _err(errors, f"{prefix}: missing envelope field {field!r}")


def validate_scoring_data(data: dict, prefix: str, errors: list[str]) -> None:
    _validate_envelope(data, "scoring", prefix, errors)
    payload = artifact_payload(data)
    ws = data.get("worksheet")
    if payload.get("blocked"):
        return
    items = payload.get("items")
    if not isinstance(items, list):
        _err(errors, f"{prefix}: items must be an array")
        return
    expected = set(scoring_item_ids(ws))
    found = {r["item"] for r in items if isinstance(r, dict) and "item" in r}
    if expected != found:
        _err(errors, f"{prefix}: scoring items mismatch expected={len(expected)} found={len(found)}")
    mapping = load_mapping(ws)
    for rec in items:
        item_id = rec.get("item")
        if item_id not in mapping["items"]:
            _err(errors, f"{prefix} {item_id}: not in mapping")
        if "learning_objects" in rec:
            _err(errors, f"{prefix} {item_id}: learning_objects belong in evidence.json")
        conf = rec.get("confidence")
        review = rec.get("review")
        score = rec.get("score")
        if conf is not None and not (0.0 <= float(conf) <= 1.0):
            _err(errors, f"{prefix} {item_id}: confidence out of range")
        if review is not None and apply_review_flag(float(conf or 0), score) != review:
            _err(errors, f"{prefix} {item_id}: review inconsistent with confidence={conf}")


def validate_evidence_data(data: dict, prefix: str, errors: list[str]) -> None:
    _validate_envelope(data, "evidence", prefix, errors)
    payload = artifact_payload(data)
    items = payload.get("items")
    if not isinstance(items, list):
        _err(errors, f"{prefix}: items must be an array")
        return
    for rec in items:
        item_id = rec.get("item")
        comps = rec.get("competencies") or rec.get("learning_objects")
        if not isinstance(comps, list):
            _err(errors, f"{prefix} {item_id}: competencies must be an array")
            continue
        for comp in comps:
            lo = comp.get("lo") or comp.get("LO")
            strength = comp.get("strength") or comp.get("evidence_strength")
            if strength not in EVIDENCE_STRENGTHS:
                _err(errors, f"{prefix} {item_id}: invalid strength for {lo}")
            et = comp.get("evidence_type")
            if et and et not in EVIDENCE_TYPES:
                _err(errors, f"{prefix} {item_id}: invalid evidence_type for {lo}")
            conf = comp.get("confidence")
            if conf is not None and not (0.0 <= float(conf) <= 1.0):
                _err(errors, f"{prefix} {item_id}: competency confidence out of range")


def validate_extraction_data(data: dict, ws: str, prefix: str, errors: list[str]) -> None:
    _validate_envelope(data, "extraction", prefix, errors)
    responses = extraction_responses(data)
    ocr_keys = WORKSHEET_ITEM_IDS.get(ws, [])
    if ocr_keys:
        missing = set(ocr_keys) - set(responses)
        if missing:
            _err(errors, f"{prefix}: OCR missing keys {sorted(missing)[:5]}")


def validate_validation_data(data: dict, prefix: str, errors: list[str]) -> None:
    _validate_envelope(data, "validation", prefix, errors)
    payload = artifact_payload(data)
    for field in ("parse_success", "blocked"):
        if field not in payload:
            _err(errors, f"{prefix}: missing technical field {field!r}")
    for legacy in ("answered", "blank", "missing"):
        if legacy in payload:
            _err(errors, f"{prefix}: legacy coverage field {legacy!r} must not be stored")


def validate_portfolio_data(data: dict, prefix: str, errors: list[str]) -> None:
    errors.extend(validate_portfolio_v1(data, prefix))


def validate_student_outputs(student_id: str, errors: list[str]) -> None:
    root = student_dir(student_id)
    if not root.is_dir():
        _err(errors, f"Missing student directory: {root.relative_to(REPO_ROOT)}")
        return

    worksheets = list_worksheets(student_id)
    if not worksheets:
        _err(errors, f"{root.relative_to(REPO_ROOT)}: no worksheet artifacts found")
        return

    for ws in worksheets:
        ws_dir = root / ws
        prefix = ws_dir.relative_to(REPO_ROOT)

        extraction = load_artifact(student_id, ws, "extraction")
        if extraction:
            validate_extraction_data(extraction, ws, f"{prefix}/extraction.json", errors)
        else:
            _err(errors, f"{prefix}/extraction.json: missing")

        if ws in WORKSHEETS_REQUIRING_VALIDATION:
            validation = load_artifact(student_id, ws, "validation")
            if validation:
                validate_validation_data(validation, f"{prefix}/validation.json", errors)
            else:
                _err(errors, f"{prefix}/validation.json: required for {ws}")

        scoring = load_artifact(student_id, ws, "scoring")
        if scoring:
            validate_scoring_data(scoring, f"{prefix}/scoring.json", errors)
            payload = artifact_payload(scoring)
            view = build_summary_from_scoring(payload, worksheet=ws)
            total = view.get("total_score")
            max_score = view.get("max_score")
            if total is not None and max_score is not None and total > max_score:
                _err(errors, f"{prefix}/scoring.json: total_score exceeds max_score")

        evidence = load_artifact(student_id, ws, "evidence")
        if evidence:
            validate_evidence_data(evidence, f"{prefix}/evidence.json", errors)

        if (ws_dir / "summary.json").exists():
            _err(errors, f"{prefix}/summary.json: deprecated — derive scorecard from scoring.json")


    pf = portfolio_path(student_id)
    if not pf.exists():
        _err(errors, f"Missing {pf.relative_to(REPO_ROOT)}")
    else:
        portfolio = json.loads(pf.read_text(encoding="utf-8"))
        validate_portfolio_data(portfolio, str(pf.relative_to(REPO_ROOT)), errors)


def main() -> int:
    errors: list[str] = []
    errors.extend(validate_all_rubrics())

    errors.extend(validate_all_mappings_v2(REPO_ROOT / "mappings"))

    for path in sorted((REPO_ROOT / "rubrics").glob("*_rubric.json")):
        rubric = json.loads(path.read_text(encoding="utf-8"))
        ws = rubric["worksheet"]
        map_path = REPO_ROOT / "mappings" / f"{ws}_AICFT_mapping.json"
        if not map_path.exists():
            _err(errors, f"Missing mapping for {ws}")
            continue
        mapping = json.loads(map_path.read_text(encoding="utf-8"))
        if set(rubric["items"]) != set(mapping["items"]):
            _err(errors, f"{path.name}: rubric/mapping item key mismatch")

    validate_student_outputs("Sample_Student", errors)

    if errors:
        print(f"Pipeline validation failed ({len(errors)} issues):\n", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("Pipeline validation passed (rubrics + Sample_Student worksheets).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
