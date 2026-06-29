"""
WS7 validation — Part 1 path letters (fixed sample tree) + Part 2 rules vs WS6 tree.

Each scored blank has a single correct answer:
  P1 boxes: exact path letter (B, A, C) per printed rule row.
  B1–B3: if-then rule matching one leaf path of the student's WS6 tree (features, operators, values, label).
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from food_cards_data import complementary_operator, normalize_operator, resolve_feature
from rubric_deterministic import BLANK_SENTINELS, normalize_token
from ws6_validation import build_ws6_tree, parse_leaf_label

REPO_ROOT = Path(__file__).resolve().parent
SAMPLE_TREE_PATH = REPO_ROOT / "data" / "ws7_sample_tree.json"
VALUE_TOLERANCE = 0.05

P1_ANSWERS: dict[str, str] = {
    "WS7_P1_box1": "B",
    "WS7_P1_box2": "A",
    "WS7_P1_box3": "C",
}

RULE_BLANKS = ("WS7_B1", "WS7_B2", "WS7_B3")

# Longer phrases first when detecting natural-language operators.
_OP_PHRASES: list[tuple[str, tuple[str, ...]]] = [
    (">=", ("buyuk veya esit", "den buyuk veya esit", "dan buyuk veya esit", "fazla veya esit")),
    ("<=", ("kucuk veya esit", "den kucuk veya esit", "dan kucuk veya esit", "az veya esit")),
    (">", ("den buyuk", "dan buyuk", "den fazla", "dan fazla", "ustunde", "buyuk", "fazla")),
    ("<", ("den az", "dan az", "azsa", "kucuk")),
]

FEATURE_HINTS = (
    "enerji", "energy", "protein", "seker", "şeker", "sugar", "yag", "yağ", "fat",
    "karbonhidrat", "tuz", "salt",
)


def _is_blank(text: str | None) -> bool:
    return not str(text or "").strip() or normalize_token(str(text)) in BLANK_SENTINELS


@lru_cache(maxsize=1)
def load_sample_tree() -> dict[str, Any]:
    return json.loads(SAMPLE_TREE_PATH.read_text(encoding="utf-8"))


def normalize_path_letter(text: str | None) -> str | None:
    """Extract single path letter A/B/C from student response."""
    if _is_blank(text):
        return None
    raw = str(text).strip().upper()
    if raw in {"A", "B", "C"}:
        return raw
    m = re.search(r"\b([ABC])\b", raw)
    return m.group(1) if m else None


def validate_path_matching(
    field_id: str,
    response: str | None,
    *,
    partial_score: float = 0.0,
) -> dict[str, Any]:
    """Part 1: one correct letter per box — no partial credit."""
    expected = P1_ANSWERS.get(field_id)
    if expected is None:
        return {"ok": False, "credit": "zero", "score": 0.0, "reason": "unknown_field"}

    if _is_blank(response):
        return {
            "ok": False,
            "credit": "not_attempted",
            "score": 0.0,
            "reason": "blank",
            "expected": expected,
        }

    got = normalize_path_letter(response)
    if got is None:
        return {
            "ok": False,
            "credit": "zero",
            "score": 0.0,
            "reason": "unparseable_path_letter",
            "expected": expected,
            "response": response,
            "review": True,
        }

    if got == expected:
        return {
            "ok": True,
            "credit": "full",
            "score": 1.0,
            "expected": expected,
            "matched": got,
        }

    return {
        "ok": False,
        "credit": "zero",
        "score": partial_score,
        "reason": "wrong_path_letter",
        "expected": expected,
        "matched": got,
    }


def _parse_value(raw: str) -> float | None:
    try:
        return float(raw.replace(",", "."))
    except ValueError:
        return None


def _detect_operator_in_clause(norm_clause: str) -> str | None:
    for sym in (">=", "<=", "≥", "≤"):
        if sym in norm_clause:
            return normalize_operator(sym)
    for sym in (">", "<"):
        if sym in norm_clause:
            return normalize_operator(sym)
    for op, phrases in _OP_PHRASES:
        if any(p in norm_clause for p in phrases):
            return op
    return None


def _extract_feature_from_clause(norm_clause: str) -> str | None:
    for hint in FEATURE_HINTS:
        if normalize_token(hint) in norm_clause:
            return hint
    m = re.search(
        r"\b(enerji|protein|seker|sugar|yag|fat|karbonhidrat|tuz|energy)\b",
        norm_clause,
    )
    return m.group(1) if m else None


def parse_rule_condition(clause: str) -> dict[str, Any] | None:
    """Parse one conjunct: 'şeker ≤ 10', 'yağ > 5', or Turkish phrasing."""
    if not clause.strip():
        return None

    raw = clause.strip()
    norm = normalize_token(raw)
    norm = norm.replace("=<", "<=").replace("=>", ">=")
    for src, dst in (("≤", "<="), ("≥", ">=")):
        norm = norm.replace(src, dst)

    sym = re.search(
        r"(enerji|protein|seker|sugar|yag|fat|karbonhidrat|tuz|energy|seker|yağ|şeker)"
        r"\s*(<=|>=|≤|≥|<|>)\s*([+-]?\d+(?:[.,]\d+)?)",
        norm,
    )
    if sym:
        feat, op, val = sym.group(1), normalize_operator(sym.group(2)), sym.group(3)
        value = _parse_value(val)
        if value is None:
            return None
        return {
            "feature": feat,
            "feature_key": resolve_feature(feat),
            "operator": op,
            "value": value,
            "raw": raw,
        }

    op = _detect_operator_in_clause(norm)
    if op is None:
        return None

    feat = _extract_feature_from_clause(norm)
    nums = re.findall(r"(\d+(?:[.,]\d+)?)", norm)
    if not feat or not nums:
        return None
    value = _parse_value(nums[0])
    if value is None:
        return None

    return {
        "feature": feat,
        "feature_key": resolve_feature(feat),
        "operator": op,
        "value": value,
        "raw": raw,
    }


def parse_decision_rule(text: str | None) -> dict[str, Any] | None:
    """
    Parse student if-then rule into conditions + recommended label.
    Accepts 'Eğer … ise → …' and arrow/semicolon separators.
    """
    if _is_blank(text):
        return None

    raw = str(text).strip()
    body = raw
    conclusion = ""

    split_patterns = [
        r"\s*(?:→|->|=>|ise\s*→|ise\s*:)\s*",
        r"\s+ise\s+",
        r"\s+then\s+",
    ]
    for pat in split_patterns:
        parts = re.split(pat, raw, maxsplit=1, flags=re.IGNORECASE)
        if len(parts) == 2:
            body, conclusion = parts[0].strip(), parts[1].strip()
            break

    body_norm = normalize_token(body)
    if body_norm.startswith("eger "):
        body = body[4:].strip() if len(body) > 4 else body
    if body_norm.startswith("if "):
        body = body[3:].strip()

    cond_part = body
    if cond_part.lower().endswith(" ise"):
        cond_part = cond_part[:-4].strip()

    clauses = re.split(r"\s+ve\s+|\s+and\s+", cond_part, flags=re.IGNORECASE)
    conditions: list[dict[str, Any]] = []
    for clause in clauses:
        parsed = parse_rule_condition(clause)
        if parsed:
            conditions.append(parsed)

    if not conditions:
        return None

    label = parse_leaf_label(conclusion or raw)
    return {
        "raw": raw,
        "conditions": conditions,
        "recommended": label,
        "conclusion_text": conclusion or None,
    }


def _features_match(expected_feat: str, parsed_feat: str) -> bool:
    if normalize_token(expected_feat) == normalize_token(parsed_feat):
        return True
    ek = resolve_feature(expected_feat)
    pk = resolve_feature(parsed_feat)
    return ek is not None and pk is not None and ek == pk


def _condition_key(cond: dict[str, Any]) -> tuple[str, float]:
    fk = cond.get("feature_key") or resolve_feature(str(cond.get("feature", ""))) or ""
    return (str(fk), float(cond["value"]))


def _spec_condition_to_dict(
    feature_name: str,
    operator: str,
    value: float,
) -> dict[str, Any]:
    return {
        "feature": feature_name,
        "feature_key": resolve_feature(feature_name),
        "operator": normalize_operator(operator),
        "value": float(value),
    }


def enumerate_ws6_path_specs(tree: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Build expected rule specs for B1–B3 in traversal order:
      1) root evet + inner evet (if inner exists)
      2) root evet + inner hayır
      3) root hayır
    Two-path trees yield two specs; B3 is not_applicable.
    """
    root_t = tree.get("root_threshold")
    if not root_t:
        return []

    root_name = str(tree.get("root_feature") or root_t.get("feature_name") or "")
    specs: list[dict[str, Any]] = []

    if tree.get("has_inner"):
        inner_t = tree.get("inner_threshold")
        inner_name = str(tree.get("inner_feature") or (inner_t or {}).get("feature_name") or "")
        if inner_t:
            specs.append({
                "path_index": 1,
                "conditions": [
                    _spec_condition_to_dict(root_name, root_t["operator"], root_t["value"]),
                    _spec_condition_to_dict(inner_name, inner_t["operator"], inner_t["value"]),
                ],
                "recommended": parse_leaf_label(tree["leaves"].get("B10")),
                "leaf_field": "WS6_B10",
            })
            comp_inner = complementary_operator(inner_t["operator"])
            specs.append({
                "path_index": 2,
                "conditions": [
                    _spec_condition_to_dict(root_name, root_t["operator"], root_t["value"]),
                    _spec_condition_to_dict(inner_name, comp_inner, inner_t["value"]),
                ],
                "recommended": parse_leaf_label(tree["leaves"].get("B11")),
                "leaf_field": "WS6_B11",
            })
    else:
        specs.append({
            "path_index": 1,
            "conditions": [
                _spec_condition_to_dict(root_name, root_t["operator"], root_t["value"]),
            ],
            "recommended": parse_leaf_label(tree["leaves"].get("B5")),
            "leaf_field": "WS6_B5",
        })

    comp_root = complementary_operator(root_t["operator"])
    specs.append({
        "path_index": len(specs) + 1,
        "conditions": [
            _spec_condition_to_dict(root_name, comp_root, root_t["value"]),
        ],
        "recommended": parse_leaf_label(tree["leaves"].get("B13")),
        "leaf_field": "WS6_B13",
    })
    return specs


def _conditions_align(
    parsed_conds: list[dict[str, Any]],
    expected_conds: list[dict[str, Any]],
) -> tuple[bool, bool, list[str]]:
    """
    Return (features_and_values_ok, all_operators_ok, issues).
    Condition order does not matter.
    """
    issues: list[str] = []
    if len(parsed_conds) != len(expected_conds):
        issues.append("condition_count_mismatch")
        return False, False, issues

    exp_by_key = {_condition_key(c): c for c in expected_conds}
    used: set[tuple[str, float]] = set()
    features_ok = True
    operators_ok = True

    for pc in parsed_conds:
        key = _condition_key(pc)
        ec = exp_by_key.get(key)
        if ec is None:
            if not any(_features_match(str(ec2.get("feature", "")), str(pc.get("feature", "")))
                       for ec2 in expected_conds):
                features_ok = False
                issues.append(f"unknown_feature:{pc.get('feature')}")
            else:
                features_ok = False
                issues.append(f"wrong_threshold_value:{pc.get('value')}")
            continue
        used.add(key)
        if not _features_match(str(ec.get("feature", "")), str(pc.get("feature", ""))):
            features_ok = False
            issues.append("feature_mismatch")
        if abs(float(pc["value"]) - float(ec["value"])) > VALUE_TOLERANCE:
            features_ok = False
            issues.append("value_mismatch")
        if normalize_operator(str(pc["operator"])) != normalize_operator(str(ec["operator"])):
            operators_ok = False
            issues.append(
                f"operator_mismatch:{pc.get('feature')}:{pc.get('operator')}!={ec.get('operator')}"
            )

    if len(used) != len(expected_conds):
        features_ok = False
        issues.append("missing_condition")

    return features_ok, operators_ok, issues


def validate_rule_against_spec(
    rule_text: str | None,
    spec: dict[str, Any],
    *,
    partial_score: float = 0.5,
) -> dict[str, Any]:
    """Score one B-field rule against the WS6 path specification."""
    if spec.get("not_applicable"):
        if _is_blank(rule_text):
            return {"ok": True, "credit": "not_applicable", "score": 0.0, "reason": "path_not_in_tree"}
        return {"ok": False, "credit": "zero", "score": 0.0, "reason": "unexpected_rule_for_na_path"}

    if _is_blank(rule_text):
        return {"ok": False, "credit": "not_attempted", "score": 0.0, "reason": "blank"}

    parsed = parse_decision_rule(rule_text)
    if parsed is None:
        return {
            "ok": False,
            "credit": "zero",
            "score": 0.0,
            "reason": "unparseable_rule",
            "review": True,
        }

    expected_conds = spec.get("conditions") or []
    exp_label = spec.get("recommended")
    features_ok, operators_ok, issues = _conditions_align(parsed["conditions"], expected_conds)

    label_ok = exp_label is not None and parsed["recommended"] == exp_label
    if exp_label is None:
        label_ok = parsed["recommended"] is not None

    result: dict[str, Any] = {
        "parsed": {
            "conditions": [
                {
                    "feature": c.get("feature"),
                    "operator": c.get("operator"),
                    "value": c.get("value"),
                }
                for c in parsed["conditions"]
            ],
            "recommended": parsed["recommended"],
        },
        "expected": {
            "conditions": expected_conds,
            "recommended": exp_label,
            "leaf_field": spec.get("leaf_field"),
        },
        "issues": issues,
    }

    if features_ok and operators_ok and label_ok:
        result.update(ok=True, credit="full", score=1.0)
        return result

    if features_ok and label_ok and not operators_ok:
        result.update(
            ok=False,
            credit="partial",
            score=partial_score,
            reason="wrong_operator_direction",
            operator_issue="wrong_operator_direction",
        )
        return result

    if not label_ok:
        result.update(ok=False, credit="zero", score=0.0, reason="wrong_conclusion_label")
    elif not features_ok:
        result.update(ok=False, credit="zero", score=0.0, reason="feature_or_value_mismatch")
    else:
        result.update(ok=False, credit="zero", score=0.0, reason="rule_mismatch")
    return result


def validate_ws7_extraction(
    ws7_responses: dict[str, str],
    rubric: dict[str, Any],
    *,
    ws6_responses: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Full WS7 deterministic checks for validation.json."""
    checks: dict[str, Any] = {}
    failures: list[str] = []

    for field_id, expected in P1_ANSWERS.items():
        item_cfg = rubric.get("items", {}).get(field_id, {})
        outcome = validate_path_matching(
            field_id,
            ws7_responses.get(field_id),
            partial_score=float(item_cfg.get("partial_score", 0.0)),
        )
        checks[field_id] = outcome
        if outcome.get("credit") not in {"full", "not_applicable"}:
            failures.append(field_id)

    path_specs: list[dict[str, Any]] = []
    ws6_blocked = False
    if ws6_responses:
        tree = build_ws6_tree(ws6_responses)
        path_specs = enumerate_ws6_path_specs(tree)
        if not tree.get("root_threshold"):
            ws6_blocked = True
    else:
        ws6_blocked = True

    for idx, blank_id in enumerate(RULE_BLANKS):
        item_cfg = rubric.get("items", {}).get(blank_id, {})
        partial = float(item_cfg.get("partial_score", 0.5))

        if ws6_blocked:
            checks[blank_id] = {
                "ok": False,
                "credit": "not_attempted" if _is_blank(ws7_responses.get(blank_id)) else "zero",
                "score": 0.0,
                "reason": "ws6_missing_or_unparseable",
                "review": True,
                "blocked_dependency": "WS6",
            }
            if not _is_blank(ws7_responses.get(blank_id)):
                failures.append(blank_id)
            continue

        if idx >= len(path_specs):
            spec = {"not_applicable": True}
        else:
            spec = path_specs[idx]

        outcome = validate_rule_against_spec(
            ws7_responses.get(blank_id),
            spec,
            partial_score=partial,
        )
        checks[blank_id] = outcome
        if outcome.get("credit") not in {"full", "not_applicable", "not_attempted"}:
            failures.append(blank_id)

    p1_ok = all(
        checks.get(k, {}).get("credit") == "full"
        for k in P1_ANSWERS
    )
    b_ok = all(
        checks.get(k, {}).get("credit") in {"full", "not_applicable"}
        for k in RULE_BLANKS
    )

    return {
        "deterministic_checks": checks,
        "parse_success": p1_ok or b_ok,
        "blocked": ws6_blocked and any(not _is_blank(ws7_responses.get(b)) for b in RULE_BLANKS),
        "blocked_reason": "WS6 extraction required for B1–B3 rule checks." if ws6_blocked else None,
        "ws6_path_specs": [
            {
                "path_index": s.get("path_index"),
                "leaf_field": s.get("leaf_field"),
                "conditions": s.get("conditions"),
                "recommended": s.get("recommended"),
            }
            for s in path_specs
        ],
        "sample_tree_reference": str(SAMPLE_TREE_PATH.relative_to(REPO_ROOT)),
    }


def item_score_from_check(check: dict[str, Any], max_score: float) -> float:
    from rubric_deterministic import score_from_credit

    return score_from_credit(check, max_score)
