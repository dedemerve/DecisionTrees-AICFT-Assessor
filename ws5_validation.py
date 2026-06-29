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
