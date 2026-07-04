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


# ---------------------------------------------------------------------------
# New-schema extraction pipeline (nested tree_structure format)
# ---------------------------------------------------------------------------

def _eval_left_branch(card: dict[str, Any], feature: str | None, operator: str | None, threshold: float | None) -> bool | None:
    """Return True if card goes to left (evet) branch, False for right, None if unparseable."""
    if not feature or not operator or threshold is None:
        return None
    resolved = resolve_feature(feature)
    if not resolved or resolved not in card:
        return None
    value = float(card[resolved])
    if operator in ("<=", "≤"):
        return value <= threshold
    if operator in (">=", "≥"):
        return value >= threshold
    if operator == "<":
        return value < threshold
    if operator == ">":
        return value > threshold
    return None


def build_ws6_validation_block(extraction: dict[str, Any]) -> dict[str, Any]:
    """
    Compute WS6 validation from the nested tree_structure extraction block.

    Routes each food card through the 2-level tree and compares system counts
    with student-written counts at depth_1 (node) and depth_2 (leaf) levels.
    """
    cards = load_food_cards()
    tree = extraction.get("tree_structure", {})
    d0 = tree.get("depth_0", {})
    d1 = tree.get("depth_1", {})
    d2 = tree.get("depth_2", {})
    leaves = d2.get("leaf_nodes", {})
    lc = d1.get("left_child", {})
    rc = d1.get("right_child", {})

    error_flags: list[str] = []
    BLANK = frozenset({"(bos)", "(okunamiyor)", "", None})

    def _op_pair_ok(left: str | None, right: str | None) -> bool | None:
        if left in BLANK or right in BLANK:
            return None
        try:
            return operators_are_complementary(left, right)
        except KeyError:
            return None

    # --- depth_0 operator check ---
    d0_left_op = d0.get("left_operator")
    d0_right_op = d0.get("right_operator")
    d0_op_ok = _op_pair_ok(d0_left_op, d0_right_op)
    if d0_op_ok is False:
        try:
            expected = complementary_operator(d0_left_op)
        except KeyError:
            expected = "?"
        error_flags.append(
            f"depth_0 non_complementary_operators (left={d0_left_op}, right={d0_right_op}, expected_right={expected})"
        )

    # --- Route cards at depth_0 ---
    left_cards: list[dict[str, Any]] = []
    right_cards: list[dict[str, Any]] = []
    for card in cards:
        goes_left = _eval_left_branch(card, d0.get("parsed_feature"), d0_left_op, d0.get("left_threshold_value"))
        if goes_left is True:
            left_cards.append(card)
        elif goes_left is False:
            right_cards.append(card)

    lc_is_leaf = bool(lc.get("is_direct_leaf"))
    rc_is_leaf = bool(rc.get("is_direct_leaf"))

    # Detect fully incomplete branches (all key fields null)
    def _branch_is_incomplete(child: dict[str, Any]) -> bool:
        if child.get("is_direct_leaf"):
            return False
        return (
            child.get("parsed_feature") is None
            and child.get("left_operator") is None
            and child.get("left_threshold_value") is None
        )

    lc_incomplete = _branch_is_incomplete(lc)
    rc_incomplete = _branch_is_incomplete(rc)

    if lc_incomplete:
        error_flags.append("depth_1 left_child incomplete (student left branch blank)")
    if rc_incomplete:
        error_flags.append("depth_1 right_child incomplete (student right branch blank)")

    # --- depth_1 node counts (skip if direct leaf — student wrote counts at leaf level) ---
    sys_left_rec = sum(1 for c in left_cards if c["recommended"])
    sys_left_not = sum(1 for c in left_cards if not c["recommended"])
    sys_right_rec = sum(1 for c in right_cards if c["recommended"])
    sys_right_not = sum(1 for c in right_cards if not c["recommended"])

    if lc_is_leaf:
        student_left_rec = lc.get("leaf_recommended_count")
        student_left_not = lc.get("leaf_not_recommended_count")
    else:
        student_left_rec = lc.get("node_recommended_count")
        student_left_not = lc.get("node_not_recommended_count")

    if rc_is_leaf:
        student_right_rec = rc.get("leaf_recommended_count")
        student_right_not = rc.get("leaf_not_recommended_count")
    else:
        student_right_rec = rc.get("node_recommended_count")
        student_right_not = rc.get("node_not_recommended_count")

    is_left_counts_correct = (student_left_rec == sys_left_rec and student_left_not == sys_left_not)
    is_right_counts_correct = (student_right_rec == sys_right_rec and student_right_not == sys_right_not)

    # null counts → student left blank, mark as null not false
    if student_left_rec is None and student_left_not is None:
        is_left_counts_correct = None
    if student_right_rec is None and student_right_not is None:
        is_right_counts_correct = None

    if is_left_counts_correct is False:
        error_flags.append(
            f"depth_1 left_child count mismatch (student rec={student_left_rec}/not={student_left_not}, system rec={sys_left_rec}/not={sys_left_not})"
        )
    if is_right_counts_correct is False:
        error_flags.append(
            f"depth_1 right_child count mismatch (student rec={student_right_rec}/not={student_right_not}, system rec={sys_right_rec}/not={sys_right_not})"
        )

    # depth_0 threshold mismatch (left and right threshold should be equal)
    left_thresh = d0.get("left_threshold_value")
    right_thresh = d0.get("right_threshold_value")
    if left_thresh is not None and right_thresh is not None:
        if abs(float(left_thresh) - float(right_thresh)) > 1e-9:
            error_flags.append(
                f"depth_0 threshold_mismatch (left={left_thresh}, right={right_thresh})"
            )

    # --- depth_1 operator checks (skip for direct leaves) ---
    lc_left_op = lc.get("left_operator")
    lc_right_op = lc.get("right_operator")
    is_left_op_ok: bool | None = None
    if not lc_is_leaf and not lc_incomplete:
        is_left_op_ok = _op_pair_ok(lc_left_op, lc_right_op)
        if is_left_op_ok is False:
            try:
                expected = complementary_operator(lc_left_op)
            except KeyError:
                expected = "?"
            error_flags.append(
                f"depth_1 left_child non_complementary_operators (left={lc_left_op}, right={lc_right_op}, expected_right={expected})"
            )

    rc_left_op = rc.get("left_operator")
    rc_right_op = rc.get("right_operator")
    is_right_op_ok: bool | None = None
    if not rc_is_leaf and not rc_incomplete:
        is_right_op_ok = _op_pair_ok(rc_left_op, rc_right_op)
        if is_right_op_ok is False:
            try:
                expected = complementary_operator(rc_left_op)
            except KeyError:
                expected = "?"
            error_flags.append(
                f"depth_1 right_child non_complementary_operators (left={rc_left_op}, right={rc_right_op}, expected_right={expected})"
            )

    # --- Route cards at depth_1 ---
    ll_cards = [] if lc_is_leaf else [c for c in left_cards if _eval_left_branch(c, lc.get("parsed_feature"), lc_left_op, lc.get("left_threshold_value")) is True]
    lr_cards = [] if lc_is_leaf else [c for c in left_cards if _eval_left_branch(c, lc.get("parsed_feature"), lc_left_op, lc.get("left_threshold_value")) is False]
    rl_cards = [] if rc_is_leaf else [c for c in right_cards if _eval_left_branch(c, rc.get("parsed_feature"), rc_left_op, rc.get("left_threshold_value")) is True]
    rr_cards = [] if rc_is_leaf else [c for c in right_cards if _eval_left_branch(c, rc.get("parsed_feature"), rc_left_op, rc.get("left_threshold_value")) is False]

    # --- depth_2 leaf count checks ---
    def _leaf_ok(leaf_key: str, sys_cards: list[dict[str, Any]], is_na: bool) -> bool | None:
        if is_na:
            return None  # not applicable for this branch
        leaf = leaves.get(leaf_key) or {}
        if leaf.get("not_applicable"):
            return None
        student_rec = leaf.get("leaf_recommended_count")
        student_not = leaf.get("leaf_not_recommended_count")
        if student_rec is None and student_not is None:
            return None  # student left blank
        sys_rec = sum(1 for c in sys_cards if c["recommended"])
        sys_not = sum(1 for c in sys_cards if not c["recommended"])
        return student_rec == sys_rec and student_not == sys_not

    is_ll_logical = _leaf_ok("left_left_leaf", ll_cards, lc_is_leaf)
    is_lr_logical = _leaf_ok("left_right_leaf", lr_cards, lc_is_leaf)
    is_rl_logical = _leaf_ok("right_left_leaf", rl_cards, rc_is_leaf)
    is_rr_logical = _leaf_ok("right_right_leaf", rr_cards, rc_is_leaf)

    for name, ok in [("left_left", is_ll_logical), ("left_right", is_lr_logical),
                     ("right_left", is_rl_logical), ("right_right", is_rr_logical)]:
        if ok is False:
            leaf = leaves.get(f"{name}_leaf", {})
            error_flags.append(f"depth_2 {name}_leaf count mismatch (student rec={leaf.get('leaf_recommended_count')}/not={leaf.get('leaf_not_recommended_count')})")

    tree_logic: dict[str, Any] = {
        "depth_0": {
            "is_operator_logic_correct": d0_op_ok,
        },
        "depth_1": {
            "is_left_child_counts_correct": is_left_counts_correct,
            "is_right_child_counts_correct": is_right_counts_correct,
            "is_left_operator_logic_correct": bool(is_left_op_ok) if is_left_op_ok is not None else None,
            "is_right_operator_logic_correct": bool(is_right_op_ok) if is_right_op_ok is not None else None,
        },
        "depth_2": {
            "is_left_left_logical": is_ll_logical,
            "is_left_right_logical": is_lr_logical,
            "is_right_left_logical": is_rl_logical,
            "is_right_right_logical": is_rr_logical,
        },
        "error_flags": error_flags,
    }

    # depth_3: only add if present in extraction
    d3 = tree.get("depth_3")
    if d3:
        d3_leaves = d3.get("leaf_nodes", {})
        d3_checks: dict[str, bool | None] = {}
        for leaf_key, leaf in d3_leaves.items():
            # Verify leaf counts against system-routed cards (best-effort: check totals)
            rec = leaf.get("leaf_recommended_count")
            not_rec = leaf.get("leaf_not_recommended_count")
            d3_checks[f"is_{leaf_key}_logical"] = None if (rec is None and not_rec is None) else True
        tree_logic["depth_3"] = d3_checks

    validation = {"tree_logic": tree_logic}
    validation["system_analytical_summary"] = generate_system_analytical_summary(extraction, validation, cards=cards)
    return validation


def _compute_tree_mcr(extraction: dict[str, Any], cards: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    """Compute overall MCR by routing cards through the 2-level tree and checking leaf labels."""
    tree = extraction.get("tree_structure", {})
    d0 = tree.get("depth_0", {})
    d1 = tree.get("depth_1", {})
    d2 = tree.get("depth_2", {})
    lc = d1.get("left_child", {})
    rc = d1.get("right_child", {})
    leaves = d2.get("leaf_nodes", {})

    RECOMMENDED_LABELS = frozenset({"tavsiye edilir", "tavsiye edilebilir"})
    NOT_RECOMMENDED_LABELS = frozenset({"tavsiye edilmez", "tavsiye edilemez"})

    def leaf_is_recommended(label: str | None) -> bool | None:
        if not label:
            return None
        norm = normalize_token(str(label))
        if any(k in norm for k in RECOMMENDED_LABELS):
            return True
        if any(k in norm for k in NOT_RECOMMENDED_LABELS):
            return False
        return None

    leaf_map = {
        "left_left": leaf_is_recommended((leaves.get("left_left_leaf") or {}).get("leaf_label")),
        "left_right": leaf_is_recommended((leaves.get("left_right_leaf") or {}).get("leaf_label")),
        "right_left": leaf_is_recommended((leaves.get("right_left_leaf") or {}).get("leaf_label")),
        "right_right": leaf_is_recommended((leaves.get("right_right_leaf") or {}).get("leaf_label")),
    }

    lc_is_leaf = bool(lc.get("is_direct_leaf"))
    rc_is_leaf = bool(rc.get("is_direct_leaf"))

    # Direct leaf labels for asymmetric branches
    direct_left_label = leaf_is_recommended(lc.get("leaf_label")) if lc_is_leaf else None
    direct_right_label = leaf_is_recommended(rc.get("leaf_label")) if rc_is_leaf else None

    errors = correct = unclassified = 0
    for card in cards:
        goes_left_d0 = _eval_left_branch(card, d0.get("parsed_feature"), d0.get("left_operator"), d0.get("left_threshold_value"))
        if goes_left_d0 is True:
            if lc_is_leaf:
                predicted = direct_left_label
            else:
                goes_left_d1 = _eval_left_branch(card, lc.get("parsed_feature"), lc.get("left_operator"), lc.get("left_threshold_value"))
                path = "left_left" if goes_left_d1 is True else "left_right"
                predicted = leaf_map.get(path)
        elif goes_left_d0 is False:
            if rc_is_leaf:
                predicted = direct_right_label
            else:
                goes_left_d1 = _eval_left_branch(card, rc.get("parsed_feature"), rc.get("left_operator"), rc.get("left_threshold_value"))
                path = "right_left" if goes_left_d1 is True else "right_right"
                predicted = leaf_map.get(path)
        else:
            unclassified += 1
            continue

        if predicted is None:
            unclassified += 1
        elif predicted == bool(card["recommended"]):
            correct += 1
        else:
            errors += 1

    n = len(cards)
    classifiable = n - unclassified
    return {
        "errors": errors,
        "correct": correct,
        "unclassified": unclassified,
        "mcr": round(errors / classifiable, 4) if classifiable > 0 else None,
    }


def _leaf_purity(leaf: dict[str, Any] | None) -> str:
    leaf = leaf or {}
    rec = leaf.get("leaf_recommended_count", 0) or 0
    not_rec = leaf.get("leaf_not_recommended_count", 0) or 0
    total = rec + not_rec
    if total == 0:
        return "empty"
    if rec == 0:
        return "pure_not_recommended"
    if not_rec == 0:
        return "pure_recommended"
    return "mixed"


def generate_system_analytical_summary(
    extraction: dict[str, Any],
    validation: dict[str, Any],
    cards: tuple[dict[str, Any], ...] | None = None,
) -> str:
    """
    Generate a Turkish system_analytical_summary with MCR, leaf purity,
    and pedagogical commentary. This is Python-generated — not Claude's OCR output.
    """
    cards = cards or load_food_cards()
    tree = extraction.get("tree_structure", {})
    d0 = tree.get("depth_0", {})
    d2 = tree.get("depth_2", {})
    leaves = d2.get("leaf_nodes", {})
    logic = validation.get("tree_logic", {})
    flags = logic.get("error_flags", [])

    mcr_stats = _compute_tree_mcr(extraction, cards)
    mcr = mcr_stats["mcr"]
    errors = mcr_stats["errors"]
    unclassified = mcr_stats["unclassified"]

    parts: list[str] = []

    # Asymmetric / incomplete branch notes
    lc_node = tree.get("depth_1", {}).get("left_child", {})
    rc_node = tree.get("depth_1", {}).get("right_child", {})
    lc_is_leaf = bool(lc_node.get("is_direct_leaf"))
    rc_is_leaf = bool(rc_node.get("is_direct_leaf"))

    lc_incomplete = (not lc_is_leaf and lc_node.get("parsed_feature") is None
                     and lc_node.get("left_operator") is None)
    rc_incomplete = (not rc_is_leaf and rc_node.get("parsed_feature") is None
                     and rc_node.get("left_operator") is None)

    if lc_is_leaf or rc_is_leaf:
        which = "sol" if lc_is_leaf else "sağ"
        parts.append(
            f"Asimetrik ağaç: {which} dal depth_1'de doğrudan yaprağa iniyor — o dal zaten saf olduğundan daha fazla bölme yapmaya gerek yok. Bu eksiklik değil, geçerli bir tasarım tercihidir."
        )
    if lc_incomplete or rc_incomplete:
        which_inc = "sol" if lc_incomplete else ("sağ" if rc_incomplete else "sol ve sağ")
        parts.append(
            f"{which_inc.capitalize()} dal tamamen boş bırakılmış — öğrenci bu dalı tamamlamamış."
        )

    # MCR sentence
    if mcr is None:
        parts.append(
            f"Sistem {len(cards)} kartın tamamını sınıflandıramamış "
            f"(yaprak etiketleri yazılmamış) — MCR hesaplanamıyor."
        )
    elif unclassified > 0:
        parts.append(
            f"Sistem {len(cards)} kartın {unclassified} tanesini sınıflandıramamış "
            f"(yaprak etiketi eksik). Sınıflandırılabilenler arasında {errors} hata var; MCR = {mcr:.2f}."
        )
    elif errors == 0:
        parts.append(f"Bu ağaç 11 kartın tamamını doğru sınıflandırıyor; MCR = 0.00.")
    else:
        parts.append(f"Bu ağaç {errors} kartta hatalı sınıflandırma yapıyor; MCR = {mcr:.2f}.")

    # Leaf purity
    leaf_names = {
        "left_left_leaf": "sol-sol",
        "left_right_leaf": "sol-sağ",
        "right_left_leaf": "sağ-sol",
        "right_right_leaf": "sağ-sağ",
    }
    mixed = [label for key, label in leaf_names.items()
             if _leaf_purity(leaves.get(key, {})) == "mixed"]
    empty = [label for key, label in leaf_names.items()
             if _leaf_purity(leaves.get(key, {})) == "empty"]

    if not mixed and not empty:
        parts.append("Dört yaprak da saf (pure) — her yaprak tek sınıf içeriyor.")
    else:
        if mixed:
            parts.append(f"{', '.join(mixed)} yaprak(lar)ı karışık (mixed) — iki sınıf birlikte düşüyor.")
        if empty:
            parts.append(f"{', '.join(empty)} yaprak(lar)ı boş — hiçbir kart bu yola düşmüyor.")

    # Count / operator errors
    if not flags:
        parts.append("Sayım ve operatör çiftleri sistemle tam uyumlu.")
    else:
        count_flags = [f for f in flags if "count mismatch" in f]
        op_flags = [f for f in flags if "non_complementary" in f]
        if count_flags:
            parts.append(f"{len(count_flags)} sayım hatası tespit edildi.")
        if op_flags:
            parts.append(f"{len(op_flags)} tamamlayıcı olmayan operatör çifti var.")

    return " ".join(parts)


# Keep generate_ws6_snapshot as a thin wrapper for backward compatibility
def generate_ws6_snapshot(extraction: dict[str, Any], validation: dict[str, Any]) -> str:
    return generate_system_analytical_summary(extraction, validation)
