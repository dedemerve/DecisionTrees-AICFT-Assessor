"""
Deterministic rubric checks shared by scoring, validation, and assessor overrides.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

CREDIT_LEVELS = ("full", "partial", "zero", "not_attempted")

BLANK_SENTINELS = frozenset({
    "(bos)", "(okunamiyor)", "(missing)", "(not_extracted)",
    "(transcription_error)", "",
})


def normalize_token(text: str) -> str:
    """Lowercase ASCII-ish form for Turkish nutrient / label matching."""
    s = unicodedata.normalize("NFKD", text.strip().lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    # common OCR / keyboard variants
    for src, dst in (
        ("ı", "i"), ("ğ", "g"), ("ü", "u"), ("ş", "s"), ("ö", "o"), ("ç", "c"),
    ):
        s = s.replace(src, dst)
    s = re.sub(r"\s+", " ", s)
    return s


def _group_aliases(group: dict[str, Any] | list[str]) -> list[str]:
    if isinstance(group, dict):
        aliases = list(group.get("aliases") or [])
        gid = group.get("id")
        if gid:
            aliases.append(str(gid))
        return aliases
    return list(group)


def count_matched_token_groups(response: str | None, item: dict[str, Any]) -> tuple[int, int]:
    """
    Return (matched_count, total_groups) for an unordered token-set item.
    Order of tokens in the student response does not matter.
    """
    groups = item.get("token_groups") or []
    if not groups:
        return 0, 0
    if response is None or normalize_token(str(response)) in BLANK_SENTINELS:
        return 0, len(groups)

    norm = normalize_token(str(response))
    matched = 0
    for group in groups:
        aliases = _group_aliases(group)
        if any(normalize_token(alias) in norm for alias in aliases if alias):
            matched += 1
    return matched, len(groups)


def score_unordered_token_set(
    response: str | None,
    item: dict[str, Any],
) -> dict[str, Any]:
    """
    Score a list-style answer where token order is irrelevant.

    Rubric fields:
      - token_groups: [{id, aliases: [...]}, ...] or [[alias, ...], ...]
      - need_tokens: minimum matches for full credit (default: len(token_groups))
      - partial_on_tokens: minimum matches for partial credit (default: need_tokens - 1)
    """
    matched, total = count_matched_token_groups(response, item)
    need = int(item.get("need_tokens") or total or 1)
    partial_on = int(item.get("partial_on_tokens") or max(need - 1, 1))

    if response is None or normalize_token(str(response)) in BLANK_SENTINELS:
        credit = "not_attempted"
    elif matched >= need:
        credit = "full"
    elif matched >= partial_on:
        credit = "partial"
    else:
        credit = "zero"

    return {
        "credit": credit,
        "matched_tokens": matched,
        "total_tokens": total,
        "need_tokens": need,
        "partial_on_tokens": partial_on,
        "order_insensitive": True,
        "ok": credit == "full",
    }


def resolve_accepted_aliases(
    item: dict[str, Any],
    rubric: dict[str, Any] | None = None,
) -> list[str]:
    """Expand accept_sets + explicit accepted_aliases into one alias list."""
    aliases: list[str] = []
    if item.get("accepted_aliases"):
        aliases.extend(str(a) for a in item["accepted_aliases"] if a)
    rubric = rubric or {}
    sets = rubric.get("equivalence_sets") or {}
    for key in item.get("accept_sets") or []:
        group = sets.get(key)
        if isinstance(group, dict):
            aliases.extend(str(a) for a in group.get("aliases") or [] if a)
        elif isinstance(group, list):
            aliases.extend(str(a) for a in group if a)
    aliases.extend(str(a) for a in item.get("extra_aliases") or [] if a)
    seen: set[str] = set()
    out: list[str] = []
    for alias in aliases:
        norm = normalize_token(alias)
        if norm and norm not in seen:
            seen.add(norm)
            out.append(alias)
    return out


def extract_numbers(response: str | None) -> list[float]:
    """Pull numeric literals from free-text or numeric worksheet responses."""
    if response is None:
        return []
    text = str(response).strip()
    if normalize_token(text) in BLANK_SENTINELS:
        return []
    # Turkish decimal comma → dot for parsing; keep digit groups intact.
    normalized = text.replace(",", ".")
    found: list[float] = []
    for match in re.findall(r"-?\d+(?:\.\d+)?", normalized):
        try:
            found.append(float(match))
        except ValueError:
            continue
    return found


def score_numeric_range(
    response: str | None,
    item: dict[str, Any],
) -> dict[str, Any]:
    """
    Score when any extracted number falls within [min_value, max_value] inclusive.

    Rubric fields: min_value, max_value (aliases: range_min, range_max).
    """
    min_val = item.get("min_value", item.get("range_min"))
    max_val = item.get("max_value", item.get("range_max"))
    if min_val is None or max_val is None:
        raise ValueError("numeric_range requires min_value and max_value")

    lo = float(min_val)
    hi = float(max_val)
    numbers = extract_numbers(response)

    if response is None or normalize_token(str(response)) in BLANK_SENTINELS:
        credit = "not_attempted"
        matched = None
    elif any(lo <= n <= hi for n in numbers):
        credit = "full"
        matched = next(n for n in numbers if lo <= n <= hi)
    else:
        credit = "zero"
        matched = None

    return {
        "credit": credit,
        "matched_value": matched,
        "min_value": lo,
        "max_value": hi,
        "extracted_numbers": numbers,
        "ok": credit == "full",
    }


def score_any_of_tokens(
    response: str | None,
    item: dict[str, Any],
    rubric: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Score a short fill-in where any one accepted alias earns full credit.

    WS1 uses equivalence_sets so nesne|özellik and değişken|etiket are interchangeable
    per blank configuration (accept_sets on each item).
    """
    aliases = resolve_accepted_aliases(item, rubric)
    if response is None or normalize_token(str(response)) in BLANK_SENTINELS:
        return {
            "credit": "not_attempted",
            "matched_alias": None,
            "accepted_aliases": aliases,
            "ok": False,
        }

    norm = normalize_token(str(response))
    matched: str | None = None
    for alias in aliases:
        if normalize_token(alias) in norm:
            matched = alias
            break

    credit = "full" if matched else "zero"
    return {
        "credit": credit,
        "matched_alias": matched,
        "accepted_aliases": aliases,
        "ok": credit == "full",
    }
