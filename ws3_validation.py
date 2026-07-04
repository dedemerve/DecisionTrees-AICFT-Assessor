"""
WS3 validation: compares extracted blanks against rubric answer key.

B1, B3, B5: label checks (tavsiye edilemez / edilebilir).
B2, B4, B6: reason checks (must cite food value, 8g threshold, correct direction).
B7: left threshold expression (operator must be < or ≤; value in 71-223 kcal range).
B8: right threshold expression (complementary operator; value must match B7).

Extraction format: flat dict with keys WS3_B1 … WS3_B8 as strings.
"""

from __future__ import annotations
import re
from typing import Any

# ---------------------------------------------------------------------------
# Answer key constants
# ---------------------------------------------------------------------------

FAT_THRESHOLD = 8.0   # grams of fat

# Label equivalences
NOT_RECOMMENDED = frozenset({
    "tavsiye edilemez", "tavsiye edilmez", "önerilmez",
    "not recommended", "not suitable",
})
RECOMMENDED = frozenset({
    "tavsiye edilebilir", "tavsiye edilir", "önerilir",
    "recommended", "suitable",
})

# Correct labels per food
CORRECT_LABEL = {
    "B1": "not_recommended",   # mısır gevreği, 16g fat > 8g
    "B3": "recommended",       # elma, 0.2g fat < 8g
    "B5": "not_recommended",   # patates kızartması, 14g fat > 8g
}

# Fat values per food (for reason validation)
FOOD_FAT = {
    "B1": 23.0,    # mısır gevreği (patlamış mısır)
    "B3": 0.2,     # elma
    "B5": 14.0,    # patates kızartması
}

# Tokens indicating "greater than" direction
GREATER_TOKENS = frozenset({"büyük", "fazla", "yüksek", "aşıyor", "geçiyor", ">", "daha fazla"})
LESS_TOKENS    = frozenset({"küçük", "az", "düşük", "altında", "<", "daha az"})

# Energy threshold range (B7/B8)
ENERGY_RANGE = (71.0, 223.0)   # kcal

# Complementary operator pairs: left → valid right operators
COMPLEMENTARY: dict[str, frozenset[str]] = {
    "<":  frozenset({">", "≥", ">="}),
    "≤":  frozenset({">", "≥", ">="}),
    "<=": frozenset({">", "≥", ">="}),
    ">":  frozenset({"<", "≤", "<="}),
    "≥":  frozenset({"<", "≤", "<="}),
    ">=": frozenset({"<", "≤", "<="}),
}
LEFT_OPERATORS  = frozenset({"<", "≤", "<="})
RIGHT_OPERATORS = frozenset({">", "≥", ">="})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(text: str | None) -> str:
    return str(text or "").lower().strip()


def _classify_label(v: str) -> str | None:
    """Return 'not_recommended', 'recommended', or None."""
    if any(t in v for t in NOT_RECOMMENDED):
        return "not_recommended"
    if any(t in v for t in RECOMMENDED):
        return "recommended"
    return None


def _extract_number(text: str) -> float | None:
    """Pull the first decimal number from text (handles comma decimals)."""
    cleaned = text.replace(",", ".")
    m = re.search(r"\d+(?:\.\d+)?", cleaned)
    return float(m.group()) if m else None


def _extract_operator(text: str) -> str | None:
    """Extract first recognised comparison operator token."""
    for op in ("<=", ">=", "≤", "≥", "<", ">"):
        if op in text:
            return op
    return None


# ---------------------------------------------------------------------------
# Per-item checks
# ---------------------------------------------------------------------------

def _check_label(item_key: str, value: str | None) -> dict[str, Any]:
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "score": 0.0, "note": "Boş."}
    label = _classify_label(v)
    expected = CORRECT_LABEL[item_key]
    if label == expected:
        return {"is_correct": True, "score": 1.0, "note": None}
    if label is not None:
        return {
            "is_correct": False,
            "score": 0.0,
            "note": f"Yanlış etiket — beklenen: {expected}, yazılan: {label}.",
        }
    return {
        "is_correct": False,
        "score": 0.0,
        "note": f"Tanınan etiket bulunamadı — yazılan: {value!r}.",
    }


def _check_reason(item_key: str, value: str | None) -> dict[str, Any]:
    """
    A correct reason must contain:
      1. The food's fat value (approximately).
      2. The threshold value (8).
      3. A comparison direction consistent with the expected label.
    """
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "score": 0.0, "note": "Boş."}

    food_fat = FOOD_FAT[item_key]
    expected_label = CORRECT_LABEL[item_key]

    has_threshold = "8" in v

    # Check food fat value presence: exact value or close synonym
    food_fat_str = str(food_fat).rstrip("0").rstrip(".")  # "16", "0.2", "14"
    alt = food_fat_str.replace(".", ",")
    has_food_val = (food_fat_str in v) or (alt in v)

    # Direction check: the comparison must imply food_fat vs threshold direction
    if expected_label == "not_recommended":
        # food_fat > threshold; student should imply greater-than
        correct_direction = any(t in v for t in GREATER_TOKENS)
        # Also accept reversed expression: "8 < 16" is equivalent
        if not correct_direction:
            # Check reversed: threshold < food_value
            ops = [_extract_operator(v)]
            for op in ops:
                if op in {"<", "≤", "<="} and has_food_val and has_threshold:
                    correct_direction = True
    else:
        # food_fat < threshold; student should imply less-than
        correct_direction = any(t in v for t in LESS_TOKENS)
        if not correct_direction:
            ops = [_extract_operator(v)]
            for op in ops:
                if op in {">", "≥", ">="} and has_food_val and has_threshold:
                    correct_direction = True

    if has_threshold and has_food_val and correct_direction:
        return {"is_correct": True, "score": 1.0, "note": None}
    if has_threshold or has_food_val:
        missing = []
        if not has_threshold:
            missing.append("8g eşik değeri")
        if not has_food_val:
            missing.append(f"gıdanın yağ değeri ({food_fat}g)")
        if not correct_direction:
            missing.append("doğru karşılaştırma yönü")
        return {
            "is_correct": None,
            "score": 0.5,
            "note": f"Kısmi gerekçe — eksik: {', '.join(missing)}.",
        }
    return {
        "is_correct": False,
        "score": 0.0,
        "note": "Gerekçede eşik değeri ve gıda yağ değeri tespit edilemedi.",
    }


def _check_b7(value: str | None) -> dict[str, Any]:
    """Left threshold: operator must be < or ≤; value in [71, 223]."""
    v = _norm(value)
    if not v or v in {"(bos)", "bos"}:
        return {"is_correct": False, "operator": None, "value": None, "note": "Boş."}
    op = _extract_operator(v)
    num = _extract_number(v)
    if op not in LEFT_OPERATORS:
        return {
            "is_correct": False,
            "operator": op,
            "value": num,
            "note": f"Sol eşik operatörü < veya ≤ olmalı; bulunan: {op!r}.",
        }
    if num is None:
        return {
            "is_correct": False,
            "operator": op,
            "value": None,
            "note": "Sayısal değer okunamadı.",
        }
    in_range = ENERGY_RANGE[0] <= num <= ENERGY_RANGE[1]
    return {
        "is_correct": in_range,
        "operator": op,
        "value": num,
        "note": None if in_range else f"{num} değeri [{ENERGY_RANGE[0]}, {ENERGY_RANGE[1]}] aralığında değil.",
    }


def _check_b8(value: str | None, b7_check: dict[str, Any]) -> dict[str, Any]:
    """Right threshold: operator complementary to B7; value must match B7 value."""
    v = _norm(value)
    if not v or v in {"(bos)", "bos"}:
        return {"is_correct": False, "operator": None, "value": None, "note": "Boş."}
    op = _extract_operator(v)
    num = _extract_number(v)
    b7_op = b7_check.get("operator")
    b7_val = b7_check.get("value")

    errors: list[str] = []
    if op not in RIGHT_OPERATORS:
        errors.append(f"Sağ eşik operatörü > veya ≥ olmalı; bulunan: {op!r}.")
    elif b7_op and op not in COMPLEMENTARY.get(b7_op, frozenset()):
        errors.append(f"Operatör B7 ({b7_op!r}) ile tamamlayıcı değil; bulunan: {op!r}.")

    if num is None:
        errors.append("Sayısal değer okunamadı.")
    elif b7_val is not None and abs(num - b7_val) > 0.01:
        errors.append(f"Değer B7 ile uyuşmuyor (B7={b7_val}, B8={num}).")
    elif num is not None and not (ENERGY_RANGE[0] <= num <= ENERGY_RANGE[1]):
        errors.append(f"{num} değeri [{ENERGY_RANGE[0]}, {ENERGY_RANGE[1]}] aralığında değil.")

    return {
        "is_correct": len(errors) == 0,
        "operator": op,
        "value": num,
        "note": " ".join(errors) if errors else None,
    }


# ---------------------------------------------------------------------------
# Summary generator
# ---------------------------------------------------------------------------

_FOOD_NAMES = {
    "B1": "Mısır gevreği",
    "B3": "Elma",
    "B5": "Patates kızartması",
}

_FOOD_FAT_STR = {
    "B1": "23g",
    "B3": "0.2g",
    "B5": "14g",
}


def generate_ws3_system_analytical_summary(
    raw: dict[str, Any],
    validation: dict[str, Any],
) -> str:
    checks = validation.get("item_checks", {})
    parts: list[str] = []

    for label_key, reason_key, food_key in (
        ("WS3_B1", "WS3_B2", "B1"),
        ("WS3_B3", "WS3_B4", "B3"),
        ("WS3_B5", "WS3_B6", "B5"),
    ):
        food_name = _FOOD_NAMES[food_key]
        fat_str = _FOOD_FAT_STR[food_key]
        expected = CORRECT_LABEL[food_key]
        expected_str = "tavsiye edilemez" if expected == "not_recommended" else "tavsiye edilebilir"

        l_check = checks.get(label_key, {})
        r_check = checks.get(reason_key, {})

        label_ok = l_check.get("is_correct") is True
        reason_ok = r_check.get("is_correct") is True
        reason_partial = r_check.get("score") == 0.5

        if label_ok and reason_ok:
            parts.append(
                f"{food_name} ({fat_str}): Etiket ve gerekçe doğru ({expected_str})."
            )
        elif label_ok and reason_partial:
            parts.append(
                f"{food_name} ({fat_str}): Etiket doğru ama gerekçe eksik — {r_check.get('note', '')}"
            )
        elif label_ok and not reason_ok:
            parts.append(
                f"{food_name} ({fat_str}): Etiket doğru ama gerekçe hatalı/boş."
            )
        elif not label_ok and reason_ok:
            parts.append(
                f"{food_name} ({fat_str}): Gerekçe doğru ama etiket hatalı ({raw.get(label_key, '?')!r}, beklenen: {expected_str})."
            )
        else:
            parts.append(
                f"{food_name} ({fat_str}): Etiket hatalı ({raw.get(label_key, '?')!r}) ve gerekçe eksik."
            )

    # B7/B8 threshold pair
    b7 = checks.get("WS3_B7", {})
    b8 = checks.get("WS3_B8", {})
    b7_ok = b7.get("is_correct") is True
    b8_ok = b8.get("is_correct") is True

    if b7_ok and b8_ok:
        parts.append(
            f"Enerji eşiği (B7/B8): Tutarlı ve doğru aralıkta "
            f"({b7.get('operator')} {b7.get('value')} / {b8.get('operator')} {b8.get('value')})."
        )
    else:
        issues: list[str] = []
        if not b7_ok:
            issues.append(f"B7 hatalı: {b7.get('note', raw.get('WS3_B7', '?'))!r}")
        if not b8_ok:
            issues.append(f"B8 hatalı: {b8.get('note', raw.get('WS3_B8', '?'))!r}")
        parts.append("Enerji eşiği (B7/B8): " + "; ".join(issues) + ".")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_ws3_validation_block(raw: dict[str, Any]) -> dict[str, Any]:
    b7_check = _check_b7(raw.get("WS3_B7"))

    item_checks = {
        "WS3_B1": _check_label("B1", raw.get("WS3_B1")),
        "WS3_B2": _check_reason("B1", raw.get("WS3_B2")),
        "WS3_B3": _check_label("B3", raw.get("WS3_B3")),
        "WS3_B4": _check_reason("B3", raw.get("WS3_B4")),
        "WS3_B5": _check_label("B5", raw.get("WS3_B5")),
        "WS3_B6": _check_reason("B5", raw.get("WS3_B6")),
        "WS3_B7": b7_check,
        "WS3_B8": _check_b8(raw.get("WS3_B8"), b7_check),
    }

    validation: dict[str, Any] = {"item_checks": item_checks}
    validation["system_analytical_summary"] = generate_ws3_system_analytical_summary(raw, validation)
    return validation
