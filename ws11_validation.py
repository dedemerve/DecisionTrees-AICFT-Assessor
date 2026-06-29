"""
WS11 deterministic validation for Q10–Q12 (and optional path checks).
"""

from __future__ import annotations

import re
from typing import Any

from pipeline_schema import load_rubric
from rubric_deterministic import BLANK_SENTINELS, normalize_token

CHECKED_MARKERS = frozenset({
    "isaretli", "isaretlendi", "isaretlenmeli", "evet", "dogru", "yes", "x", "✓", "✔",
    "checked", "secildi", "secili", "var",
})
UNCHECKED_MARKERS = frozenset({
    "isaretlenmemis", "isaretlenmemeli", "hayir", "no", "bos", "yok", "unchecked",
})


def _norm_response(response: str | None) -> str:
    if response is None:
        return ""
    return normalize_token(str(response))


def validate_true_false(field_id: str, response: str | None, rubric: dict[str, Any]) -> dict[str, Any]:
    item = rubric["items"][field_id]
    expected = str(item.get("correct_answer", "")).strip()
    got = str(response or "").strip()
    if _norm_response(got) in BLANK_SENTINELS:
        return {"field_id": field_id, "credit": "not_attempted", "ok": False, "expected": expected}
    ok = normalize_token(got) == normalize_token(expected)
    return {
        "field_id": field_id,
        "credit": "full" if ok else "zero",
        "ok": ok,
        "expected": expected,
        "got": got,
    }


def validate_ordering_step(field_id: str, response: str | None, rubric: dict[str, Any]) -> dict[str, Any]:
    item = rubric["items"][field_id]
    expected = int(item["correct_answer"])
    nums = re.findall(r"\d+", str(response or ""))
    if not nums:
        return {"field_id": field_id, "credit": "not_attempted", "ok": False, "expected": expected}
    got = int(nums[0])
    ok = got == expected
    return {
        "field_id": field_id,
        "credit": "full" if ok else "zero",
        "ok": ok,
        "expected": expected,
        "got": got,
    }


def _is_marked(response: str | None) -> bool | None:
    norm = _norm_response(response)
    if norm in BLANK_SENTINELS:
        return None
    if any(m in norm for m in CHECKED_MARKERS):
        return True
    if any(m in norm for m in UNCHECKED_MARKERS):
        return False
    # bare "Doğru"/"Yanlış" from T/F tables — treat non-empty as marked for Q12 rows
    if norm in {"dogru", "yanlis"}:
        return norm == "dogru"
    return True  # any other non-empty text → marked


def validate_multiselect(field_id: str, response: str | None, rubric: dict[str, Any]) -> dict[str, Any]:
    item = rubric["items"][field_id]
    should_check = bool(item.get("correct"))
    marked = _is_marked(response)
    if marked is None:
        return {"field_id": field_id, "credit": "not_attempted", "ok": False, "expected_checked": should_check}
    ok = marked == should_check
    return {
        "field_id": field_id,
        "credit": "full" if ok else "zero",
        "ok": ok,
        "expected_checked": should_check,
        "marked": marked,
    }


def validate_ws11_deterministic(responses: dict[str, str], rubric: dict[str, Any] | None = None) -> dict[str, Any]:
    rubric = rubric or load_rubric("WS11")
    checks: dict[str, Any] = {}
    for item_id, item in rubric.get("items", {}).items():
        ev = item.get("evaluation")
        if ev == "true_false":
            checks[item_id] = validate_true_false(item_id, responses.get(item_id), rubric)
        elif ev == "ordering_step":
            checks[item_id] = validate_ordering_step(item_id, responses.get(item_id), rubric)
        elif ev == "multiselect_subitem":
            checks[item_id] = validate_multiselect(item_id, responses.get(item_id), rubric)

    scored = [c for c in checks.values() if c.get("credit") != "not_attempted"]
    correct = sum(1 for c in scored if c.get("ok"))
    return {
        "deterministic_checks": checks,
        "all_correct": bool(scored) and correct == len(scored),
        "items_checked": len(checks),
        "items_correct": correct,
    }


def item_score_from_check(check: dict[str, Any], max_score: float) -> float:
    from rubric_deterministic import score_from_credit

    return score_from_credit(check, max_score)
