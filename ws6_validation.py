"""
WS6 two-level decision tree validation against ProDaBi food cards (N=11).

Same classroom card set as WS5 (data/prodabi_food_cards.csv). Validates thresholds,
branch operators, leaf labels, and tree structure. MCR=0 with a two-level tree is valid
(students may split twice even when one level would suffice).
"""

from __future__ import annotations

import re
from typing import Any

from food_cards_data import (
    INCLUSIVE_OPS,
    STRICT_OPS,
    complementary_operator,
    load_food_cards,
    normalize_token,
    operators_are_complementary,
    parse_operator_in_text,
    resolve_feature,
)
from rubric_deterministic import BLANK_SENTINELS
from ws5_validation import parse_threshold_expression

YES_TOKENS = frozenset({
    "evet", "yes", "true", "dogru", "doğru", "pozitif", "≤", "<=",
})
NO_TOKENS = frozenset({
    "hayir", "hayır", "no", "false", "yanlis", "yanlış", "negatif", ">", ">=",
})
RECOMMENDED_LEAF = frozenset({
    "tavsiye edilir", "tavsiye edilebilir", "onerilir", "önerilir",
    "onerilebilir", "önerilebilir", "uygun", "recommended", "recommendable",
})
NOT_RECOMMENDED_LEAF = frozenset({
    "tavsiye edilmez", "tavsiye edilemez", "onerilmez", "önerilmez",
    "uygun degil", "uygun değil", "not recommended", "not recommendable",
})


def _is_blank(text: str | None) -> bool:
    return not str(text or "").strip() or normalize_token(str(text)) in BLANK_SENTINELS


def parse_threshold_field(
    threshold_text: str | None,
    feature_text: str | None,
) -> dict[str, Any] | None:
    """Parse B2/B7 style '≤ 10' using feature from B1/B6, or full 'şeker ≤ 10'."""
    if _is_blank(threshold_text):
        return None

    full = parse_threshold_expression(threshold_text)
    if full:
        return full

    if _is_blank(feature_text):
        return None

    raw = str(threshold_text).strip()
    norm = raw.replace("=<", "<=").replace("=>", ">=")
    for src, dst in (("≤", "<="), ("≥", ">="), ("＜", "<"), ("＞", ">")):
        norm = norm.replace(src, dst)

    m = re.match(
        r"^(<=|>=|<|>)\s*([+-]?\d+(?:[.,]\d+)?)\s*$",
        norm.strip(),
    )
    if not m:
        return None

    feature = resolve_feature(str(feature_text))
    if not feature:
        return None

    op, value_raw = m.group(1), m.group(2)
    return {
        "raw": raw,
        "feature": feature,
        "feature_name": str(feature_text).strip(),
        "operator": op,
        "value": float(value_raw.replace(",", ".")),
        "operator_inclusive": op in INCLUSIVE_OPS,
        "operator_strict": op in STRICT_OPS,
    }


def _has_branch_token(text: str | None, tokens: frozenset[str]) -> bool:
    if _is_blank(text):
        return False
    norm = normalize_token(str(text))
    return any(tok in norm for tok in tokens)


def parse_leaf_label(text: str | None) -> bool | None:
    """True = recommended leaf, False = not recommended, None = unparseable."""
    if _is_blank(text):
        return None
    norm = normalize_token(str(text))
    if any(k in norm for k in RECOMMENDED_LEAF):
        return True
    if any(k in norm for k in NOT_RECOMMENDED_LEAF):
        return False
    return None


def _operator_pair_consistent(true_op: str, false_label: str | None) -> bool:
    """True branch op must pair with false branch: <↔≥, >↔≤, ≤↔>, ≥↔<."""
    false_op = parse_operator_in_text(false_label)
    if false_op is None:
        return True
    return operators_are_complementary(true_op, false_op)


def build_ws6_tree(responses: dict[str, str]) -> dict[str, Any]:
    """Parse OCR fields into a two-level tree model."""
    root_feature = responses.get("WS6_B1")
    root_threshold = parse_threshold_field(responses.get("WS6_B2"), root_feature)
    inner_feature = responses.get("WS6_B6")
    inner_threshold = parse_threshold_field(responses.get("WS6_B7"), inner_feature)

    has_inner = (
        not _is_blank(inner_feature)
        and resolve_feature(str(inner_feature)) is not None
        and inner_threshold is not None
    )

    leaves = {
        "B5": responses.get("WS6_B5"),
        "B10": responses.get("WS6_B10"),
        "B11": responses.get("WS6_B11"),
        "B12": responses.get("WS6_B12"),
        "B13": responses.get("WS6_B13"),
    }

    return {
        "root_feature": root_feature,
        "root_threshold": root_threshold,
        "root_yes_label": responses.get("WS6_B3"),
        "root_no_label": responses.get("WS6_B4"),
        "inner_feature": inner_feature,
        "inner_threshold": inner_threshold,
        "inner_yes_label": responses.get("WS6_B8"),
        "inner_no_label": responses.get("WS6_B9"),
        "has_inner": has_inner,
        "leaves": leaves,
    }


def _eval_split(feature_value: float, op: str, threshold: float) -> bool:
    """True = evet branch; value equal to t goes to complementary false branch."""
    if op in ("<=", "≤"):
        return feature_value <= threshold
    if op in (">=", "≥"):
        return feature_value >= threshold
    if op == "<":
        return feature_value < threshold
    if op == ">":
        return feature_value > threshold
    return False


def classify_card_with_tree(
    card: dict[str, Any],
    tree: dict[str, Any],
) -> bool | None:
    """
  Walk the student's two-level tree for one food card.
  True branch = evet / ≤ side at each split.
    """
    root_t = tree.get("root_threshold")
    if not root_t:
        return None

    value = float(card[root_t["feature"]])
    root_true = _eval_split(value, root_t["operator"], float(root_t["value"]))

    if root_true:
        if tree.get("has_inner"):
            inner_t = tree.get("inner_threshold")
            if not inner_t:
                return None
            v2 = float(card[inner_t["feature"]])
            inner_true = _eval_split(v2, inner_t["operator"], float(inner_t["value"]))
            leaf_key = "B10" if inner_true else "B11"
            return parse_leaf_label(tree["leaves"].get(leaf_key))
        return parse_leaf_label(tree["leaves"].get("B5"))
    return parse_leaf_label(tree["leaves"].get("B13"))


def compute_tree_mcr(
    tree: dict[str, Any],
    *,
    cards: tuple[dict[str, Any], ...] | None = None,
) -> dict[str, Any]:
    """Confusion stats for the tree over 11 food cards."""
    cards = cards or load_food_cards()
    n = len(cards)
    errors = 0
    correct = 0
    unclassified = 0

    for card in cards:
        predicted = classify_card_with_tree(card, tree)
        actual = bool(card["recommended"])
        if predicted is None:
            unclassified += 1
            errors += 1
            continue
        if predicted == actual:
            correct += 1
        else:
            errors += 1

    mcr = errors / n if n else 0.0
    return {
        "dataset_size": n,
        "correct": correct,
        "errors": errors,
        "mcr": round(mcr, 4),
        "unclassified": unclassified,
    }


def validate_feature_field(text: str | None, *, must_differ_from: str | None = None) -> dict[str, Any]:
    if _is_blank(text):
        return {"ok": False, "credit": "not_attempted", "score": 0.0, "reason": "blank"}
    feature = resolve_feature(str(text))
    if not feature:
        return {"ok": False, "credit": "zero", "score": 0.0, "reason": "invalid_feature"}
    if must_differ_from and not _is_blank(must_differ_from):
        if normalize_token(str(text)) == normalize_token(str(must_differ_from)):
            return {"ok": False, "credit": "zero", "score": 0.0, "reason": "same_as_root_feature"}
    return {"ok": True, "credit": "full", "score": 1.0, "feature": feature}


def validate_threshold_field(
    threshold_text: str | None,
    feature_text: str | None,
    *,
    false_label: str | None = None,
    partial_score: float = 0.5,
) -> dict[str, Any]:
    if _is_blank(threshold_text):
        return {"ok": False, "credit": "not_attempted", "score": 0.0, "reason": "blank"}

    parsed = parse_threshold_field(threshold_text, feature_text)
    if parsed is None:
        # value without operator?
        nums = re.findall(r"\d+(?:[.,]\d+)?", str(threshold_text))
        if nums and not _is_blank(feature_text) and resolve_feature(str(feature_text)):
            return {
                "ok": False,
                "credit": "partial",
                "score": partial_score,
                "reason": "operator_missing",
            }
        return {"ok": False, "credit": "zero", "score": 0.0, "reason": "unparseable_threshold"}

    result: dict[str, Any] = {
        "parsed": {
            "operator": parsed["operator"],
            "value": parsed["value"],
            "operator_inclusive": parsed["operator_inclusive"],
            "operator_strict": parsed["operator_strict"],
            "expected_complement": complementary_operator(parsed["operator"]),
        },
        "ok": True,
        "credit": "full",
        "score": 1.0,
    }
    false_op = parse_operator_in_text(false_label)
    if false_op and not operators_are_complementary(parsed["operator"], false_op):
        result.update(
            ok=False,
            credit="partial",
            score=partial_score,
            operator_issue="complementary_operator_mismatch",
            reason="false_branch_operator_must_complement_true",
            false_operator=false_op,
            expected_complement=complementary_operator(parsed["operator"]),
        )
    return result


def validate_branch_labels(
    yes_text: str | None,
    no_text: str | None,
    *,
    threshold_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    yes_ok = _has_branch_token(yes_text, YES_TOKENS)
    no_ok = _has_branch_token(no_text, NO_TOKENS)
    if not yes_ok and not no_ok:
        return {"ok": False, "credit": "not_attempted", "score": 0.0, "reason": "blank"}

    result: dict[str, Any]
    if yes_ok and no_ok:
        result = {"ok": True, "credit": "full", "score": 1.0}
    else:
        result = {"ok": False, "credit": "partial", "score": 0.5, "reason": "one_branch_label_missing"}

    true_op = (
        (threshold_check or {}).get("parsed", {}).get("operator")
        or parse_operator_in_text(yes_text)
    )
    false_op = parse_operator_in_text(no_text)
    if true_op and false_op and not operators_are_complementary(true_op, false_op):
        result.update(
            ok=False,
            credit="partial",
            score=0.5,
            operator_issue="complementary_operator_mismatch",
            reason="false_branch_operator_must_complement_true",
            true_operator=true_op,
            false_operator=false_op,
            expected_complement=complementary_operator(true_op),
        )

    return result


def _operators_cover_all_cards(
    tree: dict[str, Any],
    mcr_stats: dict[str, Any],
) -> bool:
    """Full operator credit when complementary pairs on both splits and all cards classified."""
    if mcr_stats.get("unclassified", 0) > 0:
        return False
    root_t = tree.get("root_threshold")
    if not root_t:
        return False
    if not _operator_pair_consistent(root_t["operator"], tree.get("root_no_label")):
        return False
    if tree.get("has_inner"):
        inner_t = tree.get("inner_threshold")
        if not inner_t:
            return False
        if not _operator_pair_consistent(inner_t["operator"], tree.get("inner_no_label")):
            return False
    return True


def validate_leaves(
    responses: dict[str, str],
    tree: dict[str, Any],
    mcr_stats: dict[str, Any],
) -> dict[str, Any]:
    """Leaf labels present and consistent with tree paths over food cards."""
    required_keys: list[str] = ["B13"]
    if tree.get("has_inner"):
        required_keys.extend(["B10", "B11"])
    else:
        required_keys.append("B5")

    labeled = 0
    required = 0
    path_errors = 0

    for key in required_keys:
        required += 1
        leaf_val = tree["leaves"].get(key)
        if parse_leaf_label(leaf_val) is not None:
            labeled += 1

    if required == 0:
        return {"ok": False, "credit": "zero", "score": 0.0, "reason": "no_leaf_slots"}

    if labeled == required:
        credit = "full"
        score = 1.0
        ok = True
    elif labeled >= max(1, required - 1):
        credit = "partial"
        score = 0.5
        ok = False
        path_errors = mcr_stats.get("errors", 0)
    else:
        credit = "zero"
        score = 0.0
        ok = False

    return {
        "ok": ok and credit == "full",
        "credit": credit,
        "score": score,
        "labeled_leaves": labeled,
        "required_leaves": required,
        "mcr": mcr_stats.get("mcr"),
        "errors": mcr_stats.get("errors"),
        "path_errors": path_errors,
        "note": "MCR=0 with two-level tree is valid; extra depth is not penalized.",
    }


def validate_tree_structure(
    responses: dict[str, str],
    tree: dict[str, Any],
    mcr_stats: dict[str, Any],
) -> dict[str, Any]:
    """
    Holistic two-level tree validity.

    Full credit: ≥2 features, inner split present (çift seviyeli), leaves labeled,
    complementary operators. MCR=0 does not reduce credit.
    """
    components: dict[str, bool] = {}
    root_t = tree.get("root_threshold")
    inner_t = tree.get("inner_threshold")

    components["depth"] = bool(tree.get("has_inner") and root_t)
    components["features"] = (
        bool(root_t)
        and tree.get("has_inner")
        and not _is_blank(tree.get("inner_feature"))
        and resolve_feature(str(tree.get("inner_feature") or ""))
        and normalize_token(str(tree.get("root_feature") or ""))
        != normalize_token(str(tree.get("inner_feature") or ""))
    )
    leaves_check = validate_leaves(responses, tree, mcr_stats)
    components["leaves_labeled"] = leaves_check.get("labeled_leaves", 0) >= leaves_check.get("required_leaves", 1)

    op_ok = _operators_cover_all_cards(tree, mcr_stats)
    components["operators"] = op_ok
    if not op_ok:
        components["operator_complement_gap"] = True

    met = sum(1 for k, v in components.items() if not k.endswith("_gap") and v)
    need = 4
    partial_on = 2

    if met >= need:
        credit = "full"
        score = 1.0
        ok = True
    elif met >= partial_on:
        credit = "partial"
        score = 0.5
        ok = False
    else:
        credit = "zero"
        score = 0.0
        ok = False

    return {
        "ok": ok,
        "credit": credit,
        "score": score,
        "components": components,
        "components_met": met,
        "mcr": mcr_stats.get("mcr"),
        "errors": mcr_stats.get("errors"),
        "two_level_ok": components["depth"],
        "mcr_zero_valid": mcr_stats.get("mcr", 1) == 0.0,
        "note": (
            "Complementary operator pairs required: <↔≥, >↔≤, ≤↔>, ≥↔<. "
            "MCR=0 with two levels is acceptable."
        ),
    }


def validate_ws6_extraction(
    responses: dict[str, str],
    rubric: dict[str, Any],
) -> dict[str, Any]:
    """Build deterministic_checks for all WS6 rubric items."""
    tree = build_ws6_tree(responses)
    mcr_stats = compute_tree_mcr(tree)
    partial_thr = float(rubric.get("items", {}).get("WS6_root_threshold", {}).get("partial_score", 0.5))

    root_thr = validate_threshold_field(
        responses.get("WS6_B2"),
        responses.get("WS6_B1"),
        false_label=responses.get("WS6_B4"),
        partial_score=partial_thr,
    )
    inner_thr = validate_threshold_field(
        responses.get("WS6_B7"),
        responses.get("WS6_B6"),
        false_label=responses.get("WS6_B9"),
        partial_score=partial_thr,
    )

    checks: dict[str, Any] = {
        "WS6_root_feature": validate_feature_field(responses.get("WS6_B1")),
        "WS6_root_threshold": root_thr,
        "WS6_root_labels": validate_branch_labels(
            responses.get("WS6_B3"),
            responses.get("WS6_B4"),
            threshold_check=root_thr,
        ),
        "WS6_inner_feature": validate_feature_field(
            responses.get("WS6_B6"), must_differ_from=responses.get("WS6_B1"),
        ),
        "WS6_inner_threshold": inner_thr,
        "WS6_inner_labels": validate_branch_labels(
            responses.get("WS6_B8"),
            responses.get("WS6_B9"),
            threshold_check=inner_thr,
        ),
        "WS6_leaves": validate_leaves(responses, tree, mcr_stats),
        "WS6_tree_structure": validate_tree_structure(responses, tree, mcr_stats),
        "mcr": mcr_stats,
        "tree_model": {
            "has_inner": tree.get("has_inner"),
            "root": tree.get("root_threshold"),
            "inner": tree.get("inner_threshold"),
        },
    }

    ocr_present = not _is_blank(responses.get("WS6_B1")) and not _is_blank(responses.get("WS6_B2"))
    return {
        "deterministic_checks": checks,
        "parse_success": ocr_present,
        "tree_detected": ocr_present,
        "blocked": False,
        "blocked_reason": None,
        "mcr": mcr_stats,
    }


def item_score_from_check(check: dict[str, Any], max_score: float = 1.0) -> float:
    from rubric_deterministic import score_from_credit

    return score_from_credit(check, max_score)


row_score_from_check = item_score_from_check
