"""
Post-OCR normalization for WS5 / WS6 before deterministic validation.

Architecture:
  Kağıt → vision/LLM (extraction) → this module (mechanical fixes) → ws5/ws6_validation (rules)

Does not reinterpret student answers or apply rubric logic — only fixes common OCR artifacts
so the existing deterministic validators can parse fields reliably.
"""

from __future__ import annotations

import re
from typing import Any

_WS5_THRESHOLD_RE = re.compile(r"^WS5_B(\d+)$")
_WS6_OPERATOR_FIELDS = frozenset({
    "WS6_B2", "WS6_B3", "WS6_B4", "WS6_B7", "WS6_B8", "WS6_B9",
})


def _ws5_field_num(field_id: str) -> int | None:
    m = _WS5_THRESHOLD_RE.match(field_id)
    if not m:
        return None
    return int(m.group(1))


def is_ws5_threshold_field(field_id: str) -> bool:
    """WS5 threshold cells: B1, B5, B9, … and B25."""
    n = _ws5_field_num(field_id)
    if n is None:
        return False
    if n == 25:
        return True
    return (n - 1) % 4 == 0


def fix_operator_artifacts(text: str) -> str:
    """Repair mechanical OCR typos in inequality symbols; preserve student wording."""
    s = text.strip()
    s = s.replace("=<", "<=").replace("=>", ">=")
    s = s.replace("＜", "<").replace("＞", ">")
    return s


def normalize_ws5_responses(responses: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in responses.items():
        if not isinstance(value, str):
            out[key] = value
            continue
        if is_ws5_threshold_field(key):
            out[key] = fix_operator_artifacts(value)
        elif key.startswith("WS5_B"):
            out[key] = value.strip()
        else:
            out[key] = value
    return out


def normalize_ws6_responses(responses: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in responses.items():
        if not isinstance(value, str):
            out[key] = value
            continue
        if key in _WS6_OPERATOR_FIELDS:
            out[key] = fix_operator_artifacts(value)
        elif key.startswith("WS6_B"):
            out[key] = value.strip()
        else:
            out[key] = value
    return out


def normalize_scoring_responses(
    worksheet: str,
    responses: dict[str, str],
) -> dict[str, str]:
    """Return a copy of OCR responses with WS5/WS6 mechanical cleanup applied."""
    if worksheet == "WS5":
        return normalize_ws5_responses(responses)
    if worksheet == "WS6":
        return normalize_ws6_responses(responses)
    return dict(responses)


def normalization_diff(
    worksheet: str,
    raw: dict[str, str],
) -> list[dict[str, Any]]:
    """Fields changed by normalization (for validation metadata / review)."""
    cleaned = normalize_scoring_responses(worksheet, raw)
    changes: list[dict[str, Any]] = []
    for key in sorted(set(raw) | set(cleaned)):
        before = raw.get(key, "")
        after = cleaned.get(key, "")
        if before != after:
            changes.append({"field": key, "raw": before, "normalized": after})
    return changes
