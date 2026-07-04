"""
WS4 validation: compares extraction against rubric answer key.

B1 and B5 are deterministic (numeric range).
B2 is deterministic (token-set match).
B3 and B4 are keyword-heuristic (interpretive — flags strong signals only).
"""

from __future__ import annotations
from typing import Any

# ---------------------------------------------------------------------------
# Answer key constants
# ---------------------------------------------------------------------------

B1_RANGE = (13.0, 14.0)          # avocado fat(13) to french fries fat(14)
B2_TARGET = frozenset({"jelibon", "kraker", "yulaf", "avokado"})
B5_RANGE = (160.0, 223.0)        # avocado energy(160) to raspberry jam energy(223)

# Equivalence tokens for B2 food matching
B2_EQUIVALENCES: dict[str, frozenset[str]] = {
    "jelibon":  frozenset({"jelibon", "gummy bears", "gummy", "jelybon", "ayıcık"}),
    "kraker":   frozenset({"kraker", "crispbread", "gevrek", "ekmek"}),
    "yulaf":    frozenset({"yulaf", "oats", "müsli"}),
    "avokado":  frozenset({"avokado", "avocado", "avakado"}),
}

# Keywords for B3 (error-reduction reasoning)
B3_STRONG = frozenset({
    "daha az", "azaldı", "azalır", "hata azal", "yanlış azal",
    "4'ten 2", "4 ten 2", "4 hata", "2 hata", "2'ye", "2ye",
    "2'e düş", "2ye düş", "düştü", "düşer", "düşüyor",
    "fewer", "less error",
})
B3_WEAK = frozenset({
    "daha iyi", "daha doğru", "daha az hata",
    "daha iyi sınıf", "doğru sınıf",
})

# Keywords for B4 (Pia — equal fat reasoning)
B4_EQUAL_FAT = frozenset({
    "aynı", "eşit", "0.2", "0,2", "equal", "same",
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _norm(text: str | None) -> str:
    if not text:
        return ""
    return str(text).lower().strip()


def _contains_any(text: str, tokens: frozenset[str]) -> bool:
    normed = _norm(text)
    return any(t in normed for t in tokens)


def _resolve_food(raw: str) -> str | None:
    """Map a raw food token to its canonical key, or None if unrecognised."""
    normed = _norm(raw)
    for canonical, aliases in B2_EQUIVALENCES.items():
        if normed in aliases or any(a in normed for a in aliases):
            return canonical
    return None


# ---------------------------------------------------------------------------
# Per-item checks
# ---------------------------------------------------------------------------

def _check_b1(item: dict[str, Any]) -> dict[str, Any]:
    """Threshold line placement between avokado (13g) and patates kızartması (14g)."""
    value = item.get("threshold_value_parsed")
    desc = item.get("placement_description", "")

    if value is not None:
        try:
            v = float(value)
            if B1_RANGE[0] < v < B1_RANGE[1]:
                return {"is_correct": True, "error_flag": None}
            return {"is_correct": False, "error_flag": "threshold_value_out_of_range"}
        except (TypeError, ValueError):
            pass

    NEGATIVE_MARKERS = frozenset({
        "no ", "not ", "none", "yok", "çizmemiş", "işaretlenmemiş",
        "there is no", "no vertical", "no line", "no mark",
    })
    if desc:
        desc_norm = _norm(desc)
        mentions_avocado = any(w in desc_norm for w in ("avokado", "avocado"))
        mentions_fries   = any(w in desc_norm for w in ("patates kızartması", "patates", "french fries"))
        is_negative = any(neg in desc_norm for neg in NEGATIVE_MARKERS)
        # Both boundary foods must be present — one alone is insufficient
        if mentions_avocado and mentions_fries and not is_negative:
            return {"is_correct": True, "error_flag": None}
        if (mentions_avocado or mentions_fries) and not is_negative:
            return {"is_correct": False, "error_flag": "wrong_threshold_placement"}

    return {"is_correct": None, "error_flag": "threshold_not_placed"}


def _check_b2(item: dict[str, Any]) -> dict[str, Any]:
    """Four misclassified foods: jelibon, kraker, yulaf, avokado."""
    foods: list[str] = item.get("foods_parsed") or []

    found: set[str] = set()
    for raw in foods:
        canonical = _resolve_food(str(raw))
        if canonical:
            found.add(canonical)

    missing = sorted(B2_TARGET - found)
    n_correct = len(found & B2_TARGET)

    if n_correct == 4:
        return {"is_correct": True, "error_flag": None}
    if n_correct >= 2:
        return {"is_correct": None, "error_flag": f"missing_foods: {', '.join(missing)}"}
    return {"is_correct": False, "error_flag": f"missing_foods: {', '.join(missing)}"}


def _check_b3(item: dict[str, Any]) -> dict[str, Any]:
    """Error-reduction rationale: must cite that error count decreased."""
    text = item.get("response_raw") or ""
    if not text or _norm(text) in {"(bos)", "bos", ""}:
        return {"is_correct": False, "error_flag": "missing_error_reduction_rationale"}
    if _contains_any(text, B3_STRONG):
        return {"is_correct": True, "error_flag": None}
    if _contains_any(text, B3_WEAK):
        return {"is_correct": None, "error_flag": "weak_error_reduction_rationale"}
    return {"is_correct": False, "error_flag": "missing_error_reduction_rationale"}


def _check_b4(item: dict[str, Any]) -> dict[str, Any]:
    """Pia evaluation: must agree AND cite equal fat values (0.2g)."""
    agrees = item.get("agrees_with_pia")
    text = item.get("response_raw") or ""
    mentions_equal = _contains_any(text, B4_EQUAL_FAT)

    if agrees is True and mentions_equal:
        return {"is_correct": True, "error_flag": None}
    if agrees is True and not mentions_equal:
        return {"is_correct": False, "error_flag": "missing_equal_fat_explanation"}
    if agrees is False:
        return {"is_correct": False, "error_flag": "disagrees_with_pia"}
    return {"is_correct": None, "error_flag": "unclear_pia_response"}


def _check_b5(item: dict[str, Any]) -> dict[str, Any]:
    """Energy threshold: must be in range [160, 223] kcal."""
    value = item.get("threshold_value_parsed")
    if value is None:
        return {"is_correct": False, "error_flag": "missing_numeric_threshold_value"}
    try:
        v = float(value)
        if B5_RANGE[0] <= v <= B5_RANGE[1]:
            return {"is_correct": True, "error_flag": None}
        return {"is_correct": False, "error_flag": "energy_threshold_out_of_range"}
    except (TypeError, ValueError):
        return {"is_correct": False, "error_flag": "missing_numeric_threshold_value"}


# ---------------------------------------------------------------------------
# Summary generator
# ---------------------------------------------------------------------------

def generate_ws4_system_analytical_summary(
    extraction: dict[str, Any],
    validation: dict[str, Any],
) -> str:
    checks = validation.get("item_checks", {})
    parts: list[str] = []

    # B2 — Görev 1
    b2 = checks.get("WS4_B2", {})
    flag_b2 = b2.get("error_flag") or ""
    if b2.get("is_correct") is True:
        parts.append("Görev 1: 4 yanlış sınıflandırılan kart doğru tespit edilmiş.")
    elif "missing_foods" in flag_b2:
        missing_str = flag_b2.replace("missing_foods: ", "")
        parts.append(f"Görev 1: Eksik kart(lar): {missing_str}.")
    else:
        parts.append("Görev 1: Yanlış sınıflandırılan kartlar tespit edilememiş.")

    # B1 — Görev 2 threshold konumu
    b1 = checks.get("WS4_B1", {})
    if b1.get("is_correct") is True:
        parts.append("Görev 2 (Threshold value konumu): Avokado ile patates kızartması arasına doğru yerleştirilmiş.")
    elif b1.get("error_flag") == "threshold_value_out_of_range":
        parts.append("Görev 2 (Threshold value konumu): Değer aralık dışında.")
    else:
        parts.append("Görev 2 (Threshold value konumu): Eşik değeri veya çizgi konumu belirlenemedi.")

    # B3 — Görev 3
    b3 = checks.get("WS4_B3", {})
    if b3.get("is_correct") is True:
        parts.append("Görev 3: Hata sayısının azaldığını doğru biçimde gerekçelendirmiş.")
    elif b3.get("error_flag") == "weak_error_reduction_rationale":
        parts.append("Görev 3: İyileşme belirtilmiş ama hata-sayısı gerekçesi zayıf — yorumsal inceleme gerekli.")
    else:
        parts.append("Görev 3: Hata azalması gerekçesi kurulamamış.")

    # B4 — Görev 4
    b4 = checks.get("WS4_B4", {})
    if b4.get("is_correct") is True:
        parts.append("Görev 4 (Pia): Pia'ya katılmış ve yağ değerlerinin eşit (0.2g) olduğunu doğru açıklamış.")
    elif b4.get("error_flag") == "missing_equal_fat_explanation":
        parts.append("Görev 4 (Pia): Pia'ya katılmış ancak yağ değerlerinin eşitliğini açıklayamamış — kavramsal hata.")
    elif b4.get("error_flag") == "disagrees_with_pia":
        parts.append("Görev 4 (Pia): Pia'ya katılmamış — hatalı değerlendirme.")
    else:
        parts.append("Görev 4 (Pia): Yanıt belirsiz — yorumsal inceleme gerekli.")

    # B5 — Görev 5
    b5 = checks.get("WS4_B5", {})
    if b5.get("is_correct") is True:
        parts.append("Görev 5 (Enerji threshold value): Doğru aralıkta.")
    elif b5.get("error_flag") == "energy_threshold_out_of_range":
        val = (extraction.get("WS4_B5") or {}).get("threshold_value_parsed")
        parts.append(f"Görev 5 (Enerji threshold value): Aralık dışı değer ({val} kcal, beklenen 160–223).")
    else:
        parts.append("Görev 5 (Enerji threshold value): Sayısal değer belirlenememiş.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_ws4_validation_block(extraction: dict[str, Any]) -> dict[str, Any]:
    items = extraction or {}

    item_checks = {
        "WS4_B1": _check_b1(items.get("WS4_B1") or {}),
        "WS4_B2": _check_b2(items.get("WS4_B2") or {}),
        "WS4_B3": _check_b3(items.get("WS4_B3") or {}),
        "WS4_B4": _check_b4(items.get("WS4_B4") or {}),
        "WS4_B5": _check_b5(items.get("WS4_B5") or {}),
    }

    validation: dict[str, Any] = {"item_checks": item_checks}
    validation["system_analytical_summary"] = generate_ws4_system_analytical_summary(
        extraction, validation
    )
    return validation
