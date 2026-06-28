#!/usr/bin/env python3
"""
validate_pipeline_outputs.py — CI validation for rubrics and student bundle contracts.

Run: python validate_pipeline_outputs.py
Exit 0 on success, 1 on failure.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from confidence_calibration import REVIEW_THRESHOLD, apply_review_flag
from pipeline_schema import (
    load_mapping,
    scoring_item_ids,
    validate_all_rubrics,
    WORKSHEET_ITEM_IDS,
)
from student_bundle import (
    STUDENT_BUNDLE_SCHEMA_VERSION,
    bundle_path,
    extraction_responses,
)

REPO_ROOT = Path(__file__).parent
SCHEMA_VERSION = "1.0"
EVIDENCE_STRENGTHS = frozenset({"none", "weak", "moderate", "strong"})


def _err(errors: list[str], msg: str) -> None:
    errors.append(msg)


def validate_scoring_data(data: dict, prefix: str, errors: list[str]) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        _err(errors, f"{prefix}: schema_version must be {SCHEMA_VERSION!r}")

    for field in ("worksheet", "student_id"):
        if field not in data:
            _err(errors, f"{prefix}: missing {field}")

    ws = data.get("worksheet")
    if data.get("blocked"):
        return

    items = data.get("items")
    if not isinstance(items, list):
        _err(errors, f"{prefix}: items must be an array")
        return

    expected = set(scoring_item_ids(ws))
    found = {r["item"] for r in items if isinstance(r, dict) and "item" in r}
    if expected != found:
        _err(errors, f"{prefix}: scoring items mismatch expected={len(expected)} found={len(found)} diff={sorted(expected ^ found)[:5]}")

    mapping = load_mapping(ws)
    for rec in items:
        item_id = rec.get("item")
        if item_id not in mapping["items"]:
            _err(errors, f"{prefix} {item_id}: not in mapping")
        conf = rec.get("confidence")
        review = rec.get("review")
        score = rec.get("score")
        if conf is not None and not (0.0 <= float(conf) <= 1.0):
            _err(errors, f"{prefix} {item_id}: confidence out of range")
        if review is not None and apply_review_flag(float(conf or 0), score) != review:
            _err(errors, f"{prefix} {item_id}: review={review} inconsistent with confidence={conf} (threshold={REVIEW_THRESHOLD})")
        for lo in rec.get("learning_outcomes", []):
            if lo.get("evidence_strength") not in EVIDENCE_STRENGTHS:
                _err(errors, f"{prefix} {item_id}: invalid evidence_strength")


def validate_summary_data(data: dict, prefix: str, errors: list[str]) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        _err(errors, f"{prefix}: schema_version must be {SCHEMA_VERSION!r}")

    for field in ("worksheet", "student_id", "max_score", "learning_outcomes"):
        if field not in data:
            _err(errors, f"{prefix}: missing {field}")

    if data.get("total_score") is not None and data.get("total_score") > data.get("max_score", 0):
        _err(errors, f"{prefix}: total_score exceeds max_score")


def validate_ocr_data(data: dict, ws: str, prefix: str, errors: list[str]) -> None:
    responses = extraction_responses({"worksheets": {ws: {"extraction": data}}}, ws)
    if data.get("schema_version") and data.get("schema_version") != SCHEMA_VERSION:
        if "gate_1_extraction" not in data:
            _err(errors, f"{prefix}: schema_version must be {SCHEMA_VERSION!r}")

    if not isinstance(responses, dict):
        _err(errors, f"{prefix}: responses must be an object")
        return

    ocr_keys = WORKSHEET_ITEM_IDS.get(ws, [])
    if ocr_keys:
        missing_from_ocr = set(ocr_keys) - set(responses)
        if missing_from_ocr:
            _err(errors, f"{prefix}: OCR missing keys {sorted(missing_from_ocr)[:5]}")


def validate_validation_data(data: dict, prefix: str, errors: list[str]) -> None:
    if data.get("schema_version") != SCHEMA_VERSION:
        _err(errors, f"{prefix}: schema_version must be {SCHEMA_VERSION!r}")

    for field in ("worksheet", "student_id", "answered", "blank", "missing"):
        if field not in data:
            _err(errors, f"{prefix}: missing {field}")


def validate_portfolio_data(data: dict, prefix: str, errors: list[str]) -> None:
    for field in ("worksheets_scored", "learning_outcomes", "ai_cft_proposal"):
        if field not in data:
            _err(errors, f"{prefix}: missing portfolio.{field}")

    proposal = data.get("ai_cft_proposal", {})
    if proposal.get("is_final") is not False:
        _err(errors, f"{prefix}: ai_cft_proposal.is_final must be false")


def validate_student_bundle(student_id: str, errors: list[str]) -> None:
    path = bundle_path(student_id)
    prefix = path.relative_to(REPO_ROOT)

    if not path.exists():
        _err(errors, f"Missing student bundle: {prefix}")
        return

    bundle = json.loads(path.read_text(encoding="utf-8"))
    if bundle.get("schema_version") != STUDENT_BUNDLE_SCHEMA_VERSION:
        _err(errors, f"{prefix}: schema_version must be {STUDENT_BUNDLE_SCHEMA_VERSION!r}")
    if bundle.get("student_id") != student_id:
        _err(errors, f"{prefix}: student_id mismatch")

    worksheets = bundle.get("worksheets", {})
    if not isinstance(worksheets, dict) or not worksheets:
        _err(errors, f"{prefix}: worksheets must be a non-empty object")
        return

    for ws, sections in sorted(worksheets.items()):
        ws_prefix = f"{prefix} worksheets.{ws}"
        if not isinstance(sections, dict):
            _err(errors, f"{ws_prefix}: must be an object")
            continue

        extraction = sections.get("extraction")
        if extraction:
            validate_ocr_data(extraction, ws, f"{ws_prefix}.extraction", errors)

        validation = sections.get("validation")
        if validation:
            validate_validation_data(validation, f"{ws_prefix}.validation", errors)

        scoring = sections.get("scoring")
        if scoring:
            validate_scoring_data(scoring, f"{ws_prefix}.scoring", errors)

        summary = sections.get("summary")
        if summary:
            validate_summary_data(summary, f"{ws_prefix}.summary", errors)

    portfolio = bundle.get("portfolio", {})
    if portfolio:
        validate_portfolio_data(portfolio, f"{prefix}.portfolio", errors)
    else:
        _err(errors, f"{prefix}: missing portfolio section")


def main() -> int:
    errors: list[str] = []
    errors.extend(validate_all_rubrics())

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

    validate_student_bundle("Sample_Student", errors)

    if errors:
        print(f"Pipeline validation failed ({len(errors)} issues):\n", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print("Pipeline validation passed (rubrics + Sample_Student bundle).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
