"""
WS10 deterministic validation — fixed ProDaBi energy table (8 foods, 7 threshold rows).

Each blank has exactly one correct value (see data/ws10_energy_reference.json):
  B1–B7: misclassification count for printed threshold row 1–7
  B8: optimum threshold (408)
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from rubric_deterministic import BLANK_SENTINELS, normalize_token

REPO_ROOT = Path(__file__).resolve().parent
REFERENCE_PATH = REPO_ROOT / "data" / "ws10_energy_reference.json"

TABLE_BLANKS = tuple(f"WS10_B{i}" for i in range(1, 8))
OPTIMAL_BLANK = "WS10_B8"


@lru_cache(maxsize=1)
def load_ws10_reference() -> dict[str, Any]:
    return json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))


def printed_thresholds() -> list[int]:
    return list(load_ws10_reference()["printed_thresholds"])


def expected_answers() -> dict[str, int]:
    ref = load_ws10_reference()
    out: dict[str, int] = {}
    for field_id, meta in ref["blank_map"].items():
        out[field_id] = int(meta.get("response", meta.get("answer")))
    return out


def _parse_int(text: str | None) -> int | None:
    if text is None or normalize_token(str(text)) in BLANK_SENTINELS:
        return None
    raw = str(text).strip().split("|")[0].strip()
    try:
        return int(float(raw.replace(",", ".")))
    except ValueError:
        return None


def validate_ws10_blank(field_id: str, response: str | None) -> dict[str, Any]:
    """Single blank: exact integer match to reference answer."""
    answers = expected_answers()
    expected = answers.get(field_id)
    if expected is None:
        return {"ok": False, "credit": "zero", "score": 0.0, "reason": "unknown_field"}

    if response is None or normalize_token(str(response)) in BLANK_SENTINELS:
        return {
            "ok": False,
            "credit": "not_attempted",
            "score": 0.0,
            "reason": "blank",
            "expected": expected,
        }

    got = _parse_int(response)
    if got is None:
        return {
            "ok": False,
            "credit": "zero",
            "score": 0.0,
            "reason": "unparseable_number",
            "expected": expected,
            "response": response,
            "review": True,
        }

    ref = load_ws10_reference()
    meta = ref["blank_map"].get(field_id, {})
    result: dict[str, Any] = {
        "expected": expected,
        "student": got,
    }
    if meta.get("threshold") is not None:
        result["threshold_row"] = meta.get("row")
        result["printed_threshold"] = meta.get("threshold")

    if got == expected:
        result.update(ok=True, credit="full", score=1.0)
        return result

    result.update(
        ok=False,
        credit="zero",
        score=0.0,
        reason="wrong_value",
    )
    return result


def validate_ws10_extraction(responses: dict[str, str]) -> dict[str, Any]:
    """Build deterministic_checks for all WS10 blanks."""
    checks: dict[str, Any] = {}
    for field_id in list(TABLE_BLANKS) + [OPTIMAL_BLANK]:
        checks[field_id] = validate_ws10_blank(field_id, responses.get(field_id))

    all_full = all(c.get("credit") == "full" for c in checks.values())
    any_attempted = any(c.get("credit") != "not_attempted" for c in checks.values())

    return {
        "deterministic_checks": checks,
        "parse_success": any_attempted,
        "all_correct": all_full,
        "reference": str(REFERENCE_PATH.relative_to(REPO_ROOT)),
    }


def item_score_from_check(check: dict[str, Any], max_score: float) -> float:
    from rubric_deterministic import score_from_credit

    return score_from_credit(check, max_score)


def verify_reference_answers() -> list[str]:
    """Sanity checks on stored answer key (optimum must match minimum table count)."""
    ref = load_ws10_reference()
    issues: list[str] = []
    thresholds = ref["printed_thresholds"]
    expected_mc = ref["expected_misclassifications"]
    opt_th = int(ref["optimal_threshold"])
    if opt_th not in thresholds:
        issues.append(f"optimal {opt_th} not in printed thresholds")
    min_mc = min(expected_mc)
    min_rows = [thresholds[i] for i, mc in enumerate(expected_mc) if mc == min_mc]
    if opt_th not in min_rows:
        issues.append(f"optimal {opt_th} not among minimum-misclassification rows {min_rows}")
    b8 = ref["blank_map"]["WS10_B8"].get("response", ref["blank_map"]["WS10_B8"].get("answer"))
    if int(b8) != opt_th:
        issues.append(f"B8 answer {b8} != optimal_threshold {opt_th}")
    return issues
