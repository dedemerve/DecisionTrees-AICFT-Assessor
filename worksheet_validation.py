"""
worksheet_validation.py — Technical validation for Group B worksheets (WS5, WS6, WS7).

Validation answers: "Is this data fit to score?" — not rubric scoring.
Does NOT duplicate answered/blank/missing (derivable from extraction.responses).
"""

from __future__ import annotations

from typing import Any

from student_bundle import extraction_responses
from ws_extraction_normalize import normalize_scoring_responses, normalization_diff


def _responses_for_validation(worksheet: str, extraction: dict[str, Any]) -> tuple[dict[str, str], list[dict]]:
    raw = extraction_responses(extraction)
    if worksheet not in {"WS5", "WS6"}:
        return raw, []
    normalized = normalize_scoring_responses(worksheet, raw)
    return normalized, normalization_diff(worksheet, raw)


def _validation_failure(base: dict[str, Any], exc: Exception) -> dict[str, Any]:
    base["parse_success"] = False
    base["blocked"] = True
    base["blocked_reason"] = str(exc)
    base["validation_error"] = str(exc)
    return base


def build_technical_validation(
    worksheet: str,
    extraction: dict[str, Any],
    *,
    student_id: str | None = None,
) -> dict[str, Any]:
    """Build pipeline-health validation payload for deterministic worksheets."""
    responses, ocr_fixes = _responses_for_validation(worksheet, extraction)

    base: dict[str, Any] = {
        "parse_success": True,
        "ocr_quality": None,
        "formula_parsed": True,
        "tree_detected": None,
        "missing_regions": [],
        "deterministic_checks": {},
        "blocked": False,
        "blocked_reason": None,
    }
    if ocr_fixes:
        base["ocr_normalization"] = ocr_fixes

    if worksheet == "WS5":
        from pipeline_schema import load_rubric
        from ws5_validation import validate_ws5_extraction

        try:
            rubric = load_rubric("WS5")
            ws5 = validate_ws5_extraction(responses, rubric)
            base["deterministic_checks"] = ws5["deterministic_checks"]
            base["parse_success"] = ws5["parse_success"]
            base["blocked"] = ws5["blocked"]
            base["blocked_reason"] = ws5["blocked_reason"]
        except Exception as exc:
            return _validation_failure(base, exc)

    elif worksheet == "WS6":
        from pipeline_schema import load_rubric
        from ws6_validation import validate_ws6_extraction

        try:
            rubric = load_rubric("WS6")
            ws6 = validate_ws6_extraction(responses, rubric)
            base["deterministic_checks"] = ws6["deterministic_checks"]
            base["parse_success"] = ws6["parse_success"]
            base["tree_detected"] = ws6["tree_detected"]
            base["blocked"] = ws6["blocked"]
            base["blocked_reason"] = ws6["blocked_reason"]
            if ws6.get("mcr"):
                base["mcr"] = ws6["mcr"]
        except Exception as exc:
            return _validation_failure(base, exc)

    elif worksheet == "WS7":
        from pipeline_schema import load_rubric
        from student_bundle import load_extraction_responses
        from ws7_validation import validate_ws7_extraction

        try:
            rubric = load_rubric("WS7")
            sid = student_id or extraction.get("student_id")
            ws6_responses = load_extraction_responses(sid, "WS6") if sid else {}

            ws7 = validate_ws7_extraction(responses, rubric, ws6_responses=ws6_responses or None)
            base["deterministic_checks"] = ws7["deterministic_checks"]
            base["parse_success"] = ws7["parse_success"]
            base["blocked"] = ws7["blocked"]
            base["blocked_reason"] = ws7["blocked_reason"]
            if ws7.get("ws6_path_specs"):
                base["ws6_path_specs"] = ws7["ws6_path_specs"]
            base["sample_tree_reference"] = ws7.get("sample_tree_reference")
        except Exception as exc:
            return _validation_failure(base, exc)

    return base


def ws10_extraction_quality(extraction_result_status: str, row_count: int) -> dict[str, Any]:
    """WS10 is Group A — quality metadata lives on extraction, not validation.json."""
    blocked = extraction_result_status == "error" or row_count < 7
    return {
        "htr_status": extraction_result_status,
        "table_rows_captured": row_count,
        "parse_success": not blocked and extraction_result_status == "success",
        "blocked": blocked,
        "blocked_reason": None if not blocked else "Numeric table incomplete or HTR review required.",
    }
