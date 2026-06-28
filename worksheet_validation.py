"""
worksheet_validation.py — Technical validation for Group B worksheets (WS5, WS6, WS7).

Validation answers: "Is this data fit to score?" — not rubric scoring.
Does NOT duplicate answered/blank/missing (derivable from extraction.responses).
"""

from __future__ import annotations

from typing import Any


def build_technical_validation(
    worksheet: str,
    extraction: dict[str, Any],
    legacy_validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build pipeline-health validation payload for deterministic worksheets."""
    legacy = legacy_validation or {}
    responses = extraction.get("responses") or {}
    if not responses and extraction.get("gate_1_extraction"):
        responses = extraction["gate_1_extraction"].get("items", {})

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

    if worksheet == "WS5":
        numeric = legacy.get("numeric_checks", {})
        base["deterministic_checks"] = numeric
        base["parse_success"] = bool(numeric)
        failures = [k for k, v in numeric.items() if isinstance(v, dict) and not v.get("ok", True)]
        if failures:
            base["blocked"] = True
            base["blocked_reason"] = f"Numeric row checks failed: {failures[:3]}"

    elif worksheet == "WS6":
        tree = extraction.get("tree_structure") or extraction.get("full_tree")
        layout = extraction.get("layout_roi")
        base["tree_detected"] = bool(tree or layout)
        if isinstance(tree, dict) and tree.get("error"):
            base["tree_detected"] = False
            base["parse_success"] = False
        if not base["tree_detected"]:
            base["blocked"] = True
            base["blocked_reason"] = "Decision tree canvas not detected or vision pipeline failed."

    elif worksheet == "WS7":
        path_checks = legacy.get("path_checks") or legacy.get("numeric_checks") or {}
        base["deterministic_checks"] = path_checks
        base["parse_success"] = legacy.get("path_matching_ok", True) is not False
        if legacy.get("blocked"):
            base["blocked"] = True
            base["blocked_reason"] = legacy.get("blocked_reason", "Path matching validation failed.")

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
