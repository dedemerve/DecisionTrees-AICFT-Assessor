"""
WS5 row validation against ProDaBi food-card reference data.

Scores threshold grid rows: operator correctness (≤/≥ vs strict </>), arithmetic
consistency, and confusion-matrix match to data/prodabi_food_cards.csv.
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

MCR_TOLERANCE = 0.021  # allow 0.20 vs 0.2 and minor OCR rounding


def parse_threshold_expression(text: str | None) -> dict[str, Any] | None:
    """Parse 'şeker ≤ 10', 'yag <= 8.0', 'enerji > 180' etc."""
    if text is None:
        return None
    raw = str(text).strip()
    if normalize_token(raw) in BLANK_SENTINELS:
        return None

    # Normalize unicode operators and spacing
    norm = raw.replace("=<", "<=").replace("=>", ">=")
    for src, dst in (("≤", "<="), ("≥", ">="), ("＜", "<"), ("＞", ">")):
        norm = norm.replace(src, dst)

    m = re.match(
        r"^(.+?)\s*(<=|>=|<|>)\s*([+-]?\d+(?:[.,]\d+)?)\s*$",
        norm.strip(),
        flags=re.IGNORECASE,
    )
    if not m:
        return None

    feature_raw, op, value_raw = m.group(1), m.group(2), m.group(3)
    feature = resolve_feature(feature_raw)
    if not feature:
        return None

    value = float(value_raw.replace(",", "."))
    return {
        "raw": raw,
        "feature": feature,
        "feature_name": feature_raw.strip(),
        "operator": op,
        "value": value,
        "operator_inclusive": op in INCLUSIVE_OPS,
        "operator_strict": op in STRICT_OPS,
    }


def _compare(feature_value: float, op: str, threshold: float) -> bool:
    if op in ("<=", "≤"):
        return feature_value <= threshold
    if op in (">=", "≥"):
        return feature_value >= threshold
    if op == "<":
        return feature_value < threshold
    if op == ">":
        return feature_value > threshold
    raise ValueError(f"Unknown operator: {op}")


def predict_recommended(card: dict[str, Any], parsed: dict[str, Any]) -> bool | None:
    """
    ProDaBi WS5: one written branch; opposite branch uses complementary operator.

    Pairs: ≤↔>, <↔≥, ≥↔<, >↔≤. Equality at threshold goes to the false branch
    (e.g. < t on evet → value == t is not recommended).
    """
    value = float(card[parsed["feature"]])
    threshold = float(parsed["value"])
    op = parsed["operator"]

    if op in ("<=", "≤"):
        return value <= threshold
    if op in (">=", "≥"):
        return value >= threshold
    if op == "<":
        return value < threshold
    if op == ">":
        return value > threshold
    return None


def expected_row_counts(
    parsed: dict[str, Any],
    *,
    cards: tuple[dict[str, Any], ...] | None = None,
) -> dict[str, Any]:
    """Compute expected correct/errors/MCR from food cards."""
    cards = cards or load_food_cards()
    n = len(cards)
    errors = 0
    correct = 0
    unclassified = 0

    for card in cards:
        predicted = predict_recommended(card, parsed)
        actual = bool(card["recommended"])
        if predicted is None:
            unclassified += 1
            errors += 1  # unclassified counts as misclassification / gap
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


def _parse_count(text: str | None) -> int | None:
    if text is None:
        return None
    s = str(text).strip()
    if normalize_token(s) in BLANK_SENTINELS:
        return None
    try:
        return int(float(s.replace(",", ".")))
    except ValueError:
        return None


def _parse_mcr(text: str | None) -> float | None:
    if text is None:
        return None
    s = str(text).strip().replace(",", ".")
    if normalize_token(s) in BLANK_SENTINELS:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def validate_ws5_row(
    threshold_text: str | None,
    correct_text: str | None,
    errors_text: str | None,
    mcr_text: str | None,
    *,
    dataset_size: int | None = None,
    partial_score: float = 0.5,
) -> dict[str, Any]:
    """
    Validate one WS5 grid row.

    Returns dict with ok, credit ('full'|'partial'|'zero'|'not_attempted'), score,
    and diagnostic fields for validation.json.
    """
    parsed = parse_threshold_expression(threshold_text)
    correct = _parse_count(correct_text)
    errors = _parse_count(errors_text)
    mcr = _parse_mcr(mcr_text)

    if parsed is None and correct is None and errors is None and mcr is None:
        return {
            "ok": False,
            "credit": "not_attempted",
            "score": 0.0,
            "reason": "blank_row",
        }

    if parsed is None:
        return {
            "ok": False,
            "credit": "zero",
            "score": 0.0,
            "reason": "unparseable_threshold",
            "threshold": threshold_text,
        }

    cards = load_food_cards()
    n = dataset_size or len(cards)
    expected = expected_row_counts(parsed, cards=cards)

    result: dict[str, Any] = {
        "threshold": threshold_text,
        "parsed": {
            "feature": parsed["feature"],
            "operator": parsed["operator"],
            "value": parsed["value"],
            "operator_inclusive": parsed["operator_inclusive"],
            "operator_strict": parsed["operator_strict"],
            "expected_complement": complementary_operator(parsed["operator"]),
        },
        "expected": expected,
        "student": {
            "correct": correct,
            "errors": errors,
            "mcr": mcr,
        },
    }

    if correct is None or errors is None or mcr is None:
        result.update(ok=False, credit="zero", score=0.0, reason="incomplete_row")
        return result

    sum_ok = (correct + errors) == n
    mcr_ok = abs(mcr - (errors / n)) <= MCR_TOLERANCE
    arithmetic_ok = sum_ok and mcr_ok

    counts_match = (
        correct == expected["correct"]
        and errors == expected["errors"]
        and abs(mcr - expected["mcr"]) <= MCR_TOLERANCE
    )

    result["sum"] = f"{correct}+{errors}={correct + errors}"
    result["arithmetic_ok"] = arithmetic_ok

    if counts_match and arithmetic_ok:
        result.update(ok=True, credit="full", score=1.0)
        return result

    if arithmetic_ok and not counts_match:
        result.update(
            ok=False,
            credit="partial",
            score=partial_score,
            reason="wrong_counts_with_valid_feature_and_arithmetic",
            review=True,
            review_reason="counts_inconsistent_with_food_cards",
        )
        return result

    result.update(ok=False, credit="zero", score=0.0, reason="arithmetic_inconsistent")
    return result


def validate_ws5_extraction(
    responses: dict[str, str],
    rubric: dict[str, Any],
) -> dict[str, Any]:
    """Build deterministic_checks for all filled WS5 rows."""
    checks: dict[str, Any] = {}
    partial_score = 0.5
    failures: list[str] = []

    for row_def in rubric.get("rows") or []:
        row_key = row_def["row"]
        if row_def.get("optional"):
            cells = row_def["cells"]
            if not str(responses.get(cells["threshold"], "")).strip():
                continue

        cells = row_def["cells"]
        item_cfg = rubric.get("items", {}).get(row_key, {})
        partial_score = float(item_cfg.get("partial_score", 0.5))

        outcome = validate_ws5_row(
            responses.get(cells["threshold"]),
            responses.get(cells["correct"]),
            responses.get(cells["errors"]),
            responses.get(cells["mcr"]),
            dataset_size=rubric.get("dataset_size"),
            partial_score=partial_score,
        )
        checks[row_key] = outcome
        if outcome.get("credit") == "zero" and outcome.get("reason") not in {
            "blank_row", None,
        }:
            failures.append(row_key)

    # Row-level failures do not block the whole worksheet; scoring uses per-row credit.
    b25 = validate_ws5_b25(responses, rubric, row_checks=checks)
    checks["WS5_B25"] = b25

    return {
        "deterministic_checks": checks,
        "parse_success": bool(checks),
        "blocked": False,
        "blocked_reason": None,
        "row_failures": failures,
    }


def _threshold_signature(parsed: dict[str, Any] | None) -> tuple[str, str, float] | None:
    if not parsed:
        return None
    return (parsed["feature"], parsed["operator"], float(parsed["value"]))


def _match_b25_to_row(
    b25_text: str | None,
    trials: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Match free-text B25 to a grid trial by parsed threshold or substring."""
    if not b25_text or normalize_token(str(b25_text)) in BLANK_SENTINELS:
        return None

    parsed_b25 = parse_threshold_expression(b25_text)
    sig_b25 = _threshold_signature(parsed_b25)

    for trial in trials:
        trial_parsed = trial.get("parsed")
        if sig_b25 and _threshold_signature(trial_parsed) == sig_b25:
            return trial

    norm_b25 = normalize_token(b25_text)
    for trial in trials:
        raw = str(trial.get("threshold") or "")
        if raw and normalize_token(raw) in norm_b25:
            return trial

    if parsed_b25:
        for trial in trials:
            trial_parsed = trial.get("parsed")
            if not trial_parsed:
                continue
            if (
                trial_parsed.get("feature") == parsed_b25.get("feature")
                and trial_parsed.get("value") == parsed_b25.get("value")
            ):
                return trial

    return None


def _collect_ws5_trials(
    responses: dict[str, str],
    rubric: dict[str, Any],
    row_checks: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Grid trials eligible for B25 comparison.

    Assumes each filled row has valid recommended/not-recommended totals and
    misclassification count (arithmetic_ok). Uses the student's entered error count.
    """
    row_checks = row_checks or {}
    trials: list[dict[str, Any]] = []

    for row_def in rubric.get("rows") or []:
        row_key = row_def["row"]
        cells = row_def["cells"]
        threshold = responses.get(cells["threshold"])
        if not str(threshold or "").strip():
            continue

        check = row_checks.get(row_key)
        if check is None:
            check = validate_ws5_row(
                threshold,
                responses.get(cells["correct"]),
                responses.get(cells["errors"]),
                responses.get(cells["mcr"]),
                dataset_size=rubric.get("dataset_size"),
            )

        student = check.get("student") or {}
        errors = student.get("errors")
        if errors is None or not check.get("arithmetic_ok"):
            continue

        trials.append({
            "row": row_key,
            "threshold": threshold,
            "parsed": check.get("parsed"),
            "errors": int(errors),
            "mcr": student.get("mcr"),
            "row_credit": check.get("credit"),
            "counts_match_cards": check.get("ok") or check.get("credit") == "full",
        })

    return trials


def validate_ws5_b25(
    responses: dict[str, str],
    rubric: dict[str, Any],
    *,
    row_checks: dict[str, Any] | None = None,
    partial_score: float = 0.5,
) -> dict[str, Any]:
    """
    B25: student should prefer the threshold with the lowest misclassification count
    among grid trials (assuming per-row counts and MCR are valid).

    When multiple trials tie for minimum errors, any tied choice is full credit;
    flag `tie_at_minimum` when alternatives exist but only one is named in B25.
    """
    b25_text = responses.get("WS5_B25")
    trials = _collect_ws5_trials(responses, rubric, row_checks=row_checks)

    result: dict[str, Any] = {
        "threshold": b25_text,
        "trials_considered": [
            {
                "row": t["row"],
                "threshold": t["threshold"],
                "errors": t["errors"],
                "mcr": t["mcr"],
            }
            for t in trials
        ],
    }

    if not trials:
        return {
            **result,
            "ok": False,
            "credit": "not_attempted" if not str(b25_text or "").strip() else "zero",
            "score": 0.0,
            "reason": "no_valid_grid_trials",
        }

    if not str(b25_text or "").strip() or normalize_token(str(b25_text)) in BLANK_SENTINELS:
        return {
            **result,
            "ok": False,
            "credit": "not_attempted",
            "score": 0.0,
            "reason": "blank_b25",
        }

    min_errors = min(t["errors"] for t in trials)
    tied = [t for t in trials if t["errors"] == min_errors]
    chosen = _match_b25_to_row(b25_text, trials)

    result["minimum_errors"] = min_errors
    result["tied_at_minimum"] = [
        {"row": t["row"], "threshold": t["threshold"], "errors": t["errors"]}
        for t in tied
    ]
    result["tie_at_minimum"] = len(tied) > 1

    if chosen is None:
        return {
            **result,
            "ok": False,
            "credit": "zero",
            "score": 0.0,
            "reason": "threshold_not_in_grid",
        }

    result["chosen"] = {
        "row": chosen["row"],
        "threshold": chosen["threshold"],
        "errors": chosen["errors"],
    }

    if len(tied) > 1:
        other_tied = [
            t for t in tied
            if t["row"] != chosen["row"]
        ]
        result["other_tied_thresholds"] = [
            {"row": t["row"], "threshold": t["threshold"]}
            for t in other_tied
        ]
        result["tie_note"] = (
            "Birden fazla eşik aynı en düşük yanlış sınıflandırma sayısına sahip; "
            "öğretmen adayı yalnızca birini yazmış olabilir — alternatifler: "
            + ", ".join(t["threshold"] for t in other_tied)
        )
        result["review"] = True
        result["review_reason"] = "tie_at_minimum_single_named"

    if chosen["errors"] == min_errors:
        return {
            **result,
            "ok": True,
            "credit": "full",
            "score": 1.0,
            "reason": "minimum_misclassification_choice",
        }

    return {
        **result,
        "ok": False,
        "credit": "partial",
        "score": partial_score,
        "reason": "not_minimum_misclassification",
        "review": True,
        "review_reason": "higher_error_count_than_minimum",
    }


def score_ws5_b25(
    responses: dict[str, str],
    rubric: dict[str, Any],
    *,
    row_checks: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score B25 from grid trials and minimum-error rule."""
    item_cfg = rubric.get("items", {}).get("WS5_B25", {})
    partial = float(item_cfg.get("partial_score", 0.5))
    max_score = float(item_cfg.get("max_score", 1))
    outcome = validate_ws5_b25(
        responses, rubric, row_checks=row_checks, partial_score=partial,
    )
    return {
        **outcome,
        "score": row_score_from_check(outcome, max_score),
    }


def validate_ws5_row_item(
    item_id: str,
    responses: dict[str, str],
    rubric: dict[str, Any],
) -> dict[str, Any]:
    """Validate one WS5_rowN item using rubric row cell mapping."""
    row_def = next(
        (r for r in (rubric.get("rows") or []) if r.get("row") == item_id),
        None,
    )
    if not row_def:
        return {"ok": False, "credit": "zero", "score": 0.0, "reason": "unknown_row"}

    cells = row_def["cells"]
    item_cfg = rubric.get("items", {}).get(item_id, {})
    return validate_ws5_row(
        responses.get(cells["threshold"]),
        responses.get(cells["correct"]),
        responses.get(cells["errors"]),
        responses.get(cells["mcr"]),
        dataset_size=rubric.get("dataset_size"),
        partial_score=float(item_cfg.get("partial_score", 0.5)),
    )


def row_score_from_check(check: dict[str, Any], max_score: float = 1.0) -> float:
    from rubric_deterministic import score_from_credit

    return score_from_credit(check, max_score)


def _compute_leaf_counts(parsed: dict[str, Any], cards: tuple[dict[str, Any], ...]) -> dict[str, int]:
    """Compute expected leaf counts for both branches from food card data."""
    left_rec = left_not_rec = right_rec = right_not_rec = 0
    for card in cards:
        goes_left = predict_recommended(card, parsed)
        is_rec = bool(card["recommended"])
        if goes_left is True or goes_left is None:
            if is_rec:
                left_rec += 1
            else:
                left_not_rec += 1
        else:
            if is_rec:
                right_rec += 1
            else:
                right_not_rec += 1
    return {
        "left_leaf_recommended": left_rec,
        "left_leaf_not_recommended": left_not_rec,
        "right_leaf_recommended": right_rec,
        "right_leaf_not_recommended": right_not_rec,
    }


def build_ws5_validation_block(extraction: dict[str, Any]) -> dict[str, Any]:
    """
    Build the validation block from the WS5 extraction format.

    Each trial has: parsed_feature, left_operator, left_threshold,
    left_leaf_recommended, left_leaf_not_recommended,
    right_operator, right_threshold,
    right_leaf_recommended, right_leaf_not_recommended,
    student_error_count, student_mcr.

    Validation output per trial:
      system_error_count, is_leaf_counts_correct,
      is_error_count_correct, is_operator_logic_correct, error_flag
    """
    cards = load_food_cards()

    raw_trials = extraction.get("trials") or []
    final_decision_raw = extraction.get("final_decision_raw")

    validated_trials: list[dict[str, Any]] = []
    eligible: list[dict[str, Any]] = []

    for trial in raw_trials:
        trial_id = trial.get("trial_id")
        feature = trial.get("parsed_feature")
        left_op = trial.get("left_operator")
        left_thresh = trial.get("left_threshold")
        right_op = trial.get("right_operator")
        right_thresh = trial.get("right_threshold")
        student_errors = trial.get("student_error_count")

        parsed = None
        if feature and left_op and left_thresh is not None:
            resolved = resolve_feature(feature)
            if resolved:
                parsed = {
                    "feature": resolved,
                    "operator": left_op,
                    "value": float(left_thresh),
                    "operator_inclusive": left_op in INCLUSIVE_OPS,
                    "operator_strict": left_op in STRICT_OPS,
                }

        if parsed is None:
            validated_trials.append({
                "trial_id": trial_id,
                "system_error_count": None,
                "is_leaf_counts_correct": False,
                "is_error_count_correct": False,
                "is_operator_logic_correct": False,
                "error_flag": "unparseable_threshold",
            })
            continue

        # is_operator_logic_correct: complementary pair AND matching thresholds
        op_flags: list[str] = []
        op_logic_correct = True
        if left_op and right_op:
            if not operators_are_complementary(left_op, right_op):
                expected_right = complementary_operator(left_op)
                op_flags.append(
                    f"non_complementary_operators"
                    f" (left={left_op}, right={right_op}, expected_right={expected_right})"
                )
                op_logic_correct = False
        else:
            op_flags.append("missing_operator")
            op_logic_correct = False

        if left_thresh is not None and right_thresh is not None:
            if abs(float(left_thresh) - float(right_thresh)) > 1e-9:
                op_flags.append(
                    f"threshold_mismatch (left={left_thresh}, right={right_thresh})"
                )
                op_logic_correct = False

        # Leaf count check
        system_leaves = _compute_leaf_counts(parsed, cards)
        student_leaves = {
            "left_leaf_recommended": trial.get("left_leaf_recommended"),
            "left_leaf_not_recommended": trial.get("left_leaf_not_recommended"),
            "right_leaf_recommended": trial.get("right_leaf_recommended"),
            "right_leaf_not_recommended": trial.get("right_leaf_not_recommended"),
        }
        is_leaf_counts_correct = all(
            student_leaves.get(k) == system_leaves[k] for k in system_leaves
        )
        if not is_leaf_counts_correct:
            op_flags.append("leaf_count_mismatch")

        expected = expected_row_counts(parsed, cards=cards)
        system_errors = expected["errors"]
        is_error_count_correct = student_errors is not None and student_errors == system_errors

        if not is_error_count_correct:
            op_flags.append("arithmetic_inconsistent")

        error_flag = "; ".join(op_flags) if op_flags else None

        validated_trials.append({
            "trial_id": trial_id,
            "system_error_count": system_errors,
            "is_leaf_counts_correct": is_leaf_counts_correct,
            "is_error_count_correct": is_error_count_correct,
            "is_operator_logic_correct": op_logic_correct,
            "error_flag": error_flag,
        })

        if is_error_count_correct and student_errors is not None:
            eligible.append({
                "trial_id": trial_id,
                "feature": feature,
                "left_threshold": left_thresh,
                "student_errors": student_errors,
            })

    # final_decision_logical: student chose a trial with minimum student-reported errors
    final_decision_logical = False
    if final_decision_raw and eligible:
        min_errors = min(t["student_errors"] for t in eligible)
        parsed_final = parse_threshold_expression(final_decision_raw)
        for t in eligible:
            if t["student_errors"] != min_errors:
                continue
            matched = False
            if parsed_final:
                resolved = resolve_feature(t["feature"] or "")
                matched = (
                    parsed_final.get("feature") == resolved
                    and abs(parsed_final.get("value", -1) - float(t["left_threshold"] or 0)) < 1e-9
                )
            if not matched and t["feature"]:
                norm_final = normalize_token(final_decision_raw)
                raw_val = t["left_threshold"] or 0
                thresh_candidates = [str(raw_val), str(raw_val).replace(".", ",")]
                if isinstance(raw_val, float) and raw_val == int(raw_val):
                    thresh_candidates.append(str(int(raw_val)))
                matched = normalize_token(t["feature"]) in norm_final and any(
                    normalize_token(tc) in norm_final for tc in thresh_candidates
                )
            if matched:
                final_decision_logical = True
                break

    return {
        "trials": validated_trials,
        "final_decision_logical": final_decision_logical,
    }


def generate_ws5_snapshot(extraction: dict[str, Any], validation: dict[str, Any]) -> str:
    """Generate a Turkish ws_snapshot comparing extraction and validation results."""
    ext_trials = extraction.get("trials") or []
    val_trials = {t["trial_id"]: t for t in (validation.get("trials") or [])}
    final_logical = validation.get("final_decision_logical", False)

    parts: list[str] = []
    n = len(ext_trials)
    features = [t.get("parsed_feature", "?") for t in ext_trials]
    parts.append(f"Öğrenci {n} deneme yapmış: {', '.join(features)} değişkenlerini test etmiş.")

    trial_summaries: list[str] = []
    for t in ext_trials:
        tid = t.get("trial_id")
        feature = t.get("parsed_feature", "?")
        left_op = t.get("left_operator", "?")
        left_thresh = t.get("left_threshold", "?")
        student_err = t.get("student_error_count")
        vt = val_trials.get(tid, {})
        system_err = vt.get("system_error_count")
        eflag = vt.get("error_flag") or ""

        if student_err is not None and system_err is not None:
            if student_err == system_err:
                count_str = "doğru sayım"
            else:
                count_str = f"öğrenci {student_err}, sistem {system_err} — sayma hatası"
        elif student_err is None:
            count_str = "hata sayısı boş"
        else:
            count_str = "sistem doğrulanamadı"

        extra = ""
        if "non_complementary" in eflag:
            extra = "; operatör çifti hatalı"
        elif "threshold_mismatch" in eflag:
            extra = "; eşik değerleri uyumsuz"
        elif "leaf_count_mismatch" in eflag:
            extra = "; dal sayıları hatalı"

        trial_summaries.append(
            f"Deneme {tid} ({feature} {left_op} {left_thresh}): {count_str}{extra}"
        )

    parts.append(" | ".join(trial_summaries) + ".")

    if final_logical:
        parts.append("Nihai kararında en düşük hata sayılı eşiği doğru seçmiş.")
    else:
        parts.append(
            "Nihai kararı kendi sayımındaki en düşük hata sayılı denemeyle örtüşmüyor."
        )

    return " ".join(parts)
