"""
WS1 validation: compares extracted blanks against rubric answer key.

Output format per item: {is_correct, error_flag}
- is_correct: True | False | None (None = partial credit or interpretive review needed)
- error_flag: None if correct, otherwise a descriptive code string

Item structure:
  B1-B4  Diagram labeling  — match arrow to correct data-science term
  B5-B7  Paragraph fill-in — use correct term in running text
  B8     Count             — how many features appear on a food label (answer: 7)
  B9     Feature list      — name the 7 features
  B10    Object example    — give the concrete food object shown (Fındıklı Gofret)
  B11    Label role        — identify what the label is in the paragraph (Etiket)
"""

from __future__ import annotations
from typing import Any

# ---------------------------------------------------------------------------
# Term sets
# ---------------------------------------------------------------------------

LABEL_TERMS    = frozenset({"etiket", "label"})
OBJECT_TERMS   = frozenset({"nesne", "object", "obje"})
FEATURE_TERMS  = frozenset({"özellik", "karakteristik", "değişken", "feature", "variable"})
VALUE_TERMS    = frozenset({
    "değer", "value",
    "özellik değeri", "karakteristik değeri", "değişken değeri",
    "özelliğin değeri", "karakteristiğin değeri", "değişkenin değeri",
})

# Known concrete examples that indicate soyut-terim-yerine-somut-örnek hataları
LABEL_EXAMPLES   = frozenset({"tavsiye edilemez", "tavsiye edilebilir", "tavsiye edilir"})
OBJECT_EXAMPLES  = frozenset({"fındıklı gofret", "gofret", "findikli gofret"})
VALUE_EXAMPLES   = frozenset({"542", "542 kcal", "kcal", "7,6", "18,6"})

FEATURE_LIST_CANONICAL = frozenset({
    "enerji", "yağ", "doymuş yağ", "karbonhidrat", "şeker", "protein", "tuz",
})
# English aliases for each feature (in case of EN responses)
FEATURE_ALIASES = frozenset({
    "energy", "fat", "saturated fat", "carbohydrate", "sugar", "salt",
})


def _norm(text: str | None) -> str:
    return str(text or "").lower().strip()


def _contains_any(v: str, terms: frozenset[str]) -> bool:
    return any(t in v for t in terms)


# ---------------------------------------------------------------------------
# B1 — Diagram: Etiket
# ---------------------------------------------------------------------------

def _check_b1(value: str | None) -> dict[str, Any]:
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "error_flag": "blank"}
    if _contains_any(v, LABEL_TERMS):
        return {"is_correct": True, "error_flag": None}
    if _contains_any(v, LABEL_EXAMPLES):
        return {"is_correct": None, "error_flag": "concrete_example_instead_of_term"}
    return {"is_correct": False, "error_flag": f"wrong_term: {value!r}"}


# ---------------------------------------------------------------------------
# B2 — Diagram: Nesne
# ---------------------------------------------------------------------------

def _check_b2(value: str | None) -> dict[str, Any]:
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "error_flag": "blank"}
    if _contains_any(v, OBJECT_TERMS):
        return {"is_correct": True, "error_flag": None}
    if _contains_any(v, OBJECT_EXAMPLES):
        return {"is_correct": None, "error_flag": "concrete_example_instead_of_term"}
    return {"is_correct": False, "error_flag": f"wrong_term: {value!r}"}


# ---------------------------------------------------------------------------
# B3 — Diagram: Özellik / Karakteristik / Değişken
# ---------------------------------------------------------------------------

def _check_b3(value: str | None) -> dict[str, Any]:
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "error_flag": "blank"}
    if _contains_any(v, FEATURE_TERMS):
        return {"is_correct": True, "error_flag": None}
    return {"is_correct": False, "error_flag": f"wrong_term: {value!r}"}


# ---------------------------------------------------------------------------
# B4 — Diagram: Değer  (özelliğin/karakteristiğin/değişkenin değeri)
# Common error: student writes a FEATURE term instead of VALUE term.
# ---------------------------------------------------------------------------

def _check_b4(value: str | None) -> dict[str, Any]:
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "error_flag": "blank"}
    if _contains_any(v, VALUE_TERMS):
        return {"is_correct": True, "error_flag": None}
    if _contains_any(v, VALUE_EXAMPLES):
        return {"is_correct": None, "error_flag": "concrete_example_instead_of_term"}
    # Most common mistake: student wrote a feature-level term (özellik/değişken/karakteristik)
    # without the "değeri" qualifier — B3 answer repeated in B4 slot
    if _contains_any(v, FEATURE_TERMS):
        return {"is_correct": False, "error_flag": "feature_term_instead_of_value_term"}
    return {"is_correct": False, "error_flag": f"wrong_term: {value!r}"}


# ---------------------------------------------------------------------------
# B5, B6 — Paragraph: Nesne
# ---------------------------------------------------------------------------

def _check_object_term(value: str | None) -> dict[str, Any]:
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "error_flag": "blank"}
    if _contains_any(v, OBJECT_TERMS):
        return {"is_correct": True, "error_flag": None}
    return {"is_correct": False, "error_flag": f"wrong_term: {value!r}"}


# ---------------------------------------------------------------------------
# B7 — Paragraph: Özellik / Karakteristik / Değişken
# ---------------------------------------------------------------------------

def _check_feature_term(value: str | None) -> dict[str, Any]:
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "error_flag": "blank"}
    if _contains_any(v, FEATURE_TERMS):
        return {"is_correct": True, "error_flag": None}
    return {"is_correct": False, "error_flag": f"wrong_term: {value!r}"}


# ---------------------------------------------------------------------------
# B8 — Count: how many features on a food label (answer: 7)
# Common error: student writes a TERM (özellik/değişken/karakteristik) instead of a number.
# ---------------------------------------------------------------------------

def _check_b8(value: str | None) -> dict[str, Any]:
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "error_flag": "blank"}
    if "7" in v or "yedi" in v:
        return {"is_correct": True, "error_flag": None}
    # Most common mistake: student writes a data-science term instead of a count
    if _contains_any(v, FEATURE_TERMS | LABEL_TERMS | VALUE_TERMS | OBJECT_TERMS):
        return {"is_correct": False, "error_flag": "wrote_term_instead_of_count"}
    return {"is_correct": False, "error_flag": f"incorrect_count: {value!r}"}


# ---------------------------------------------------------------------------
# B9 — Feature list: name the 7 nutritional features
# ---------------------------------------------------------------------------

def _check_b9(value: str | None) -> dict[str, Any]:
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "error_flag": "blank", "found_count": 0}

    found = sum(1 for f in FEATURE_LIST_CANONICAL | FEATURE_ALIASES if f in v)

    # Iris-style: student wrote example sentences with numeric values, not a plain list.
    # Detect by absence of commas/dashes combined with presence of numeric values.
    is_example_format = (
        found < 5
        and any(ch.isdigit() for ch in v)
        and ("," not in v and "-" not in v and "\n" not in v)
    )
    if is_example_format:
        return {
            "is_correct": None,
            "error_flag": "examples_instead_of_feature_names",
            "found_count": found,
        }

    if found >= 5:
        return {"is_correct": True, "error_flag": None, "found_count": found}
    if found >= 2:
        missing = sorted(FEATURE_LIST_CANONICAL - {f for f in FEATURE_LIST_CANONICAL if f in v})
        return {
            "is_correct": None,
            "error_flag": f"incomplete_feature_list: {found}/7",
            "found_count": found,
        }
    return {"is_correct": False, "error_flag": "missing_feature_list", "found_count": found}


# ---------------------------------------------------------------------------
# B10 — Object example: Fındıklı Gofret
# Common error: student writes "nesne" (the abstract term) instead of the concrete food name.
# ---------------------------------------------------------------------------

def _check_b10(value: str | None) -> dict[str, Any]:
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "error_flag": "blank"}
    if _contains_any(v, OBJECT_EXAMPLES):
        return {"is_correct": True, "error_flag": None}
    # Student wrote the abstract term instead of the food name
    if _contains_any(v, OBJECT_TERMS) and not _contains_any(v, OBJECT_EXAMPLES):
        return {"is_correct": False, "error_flag": "abstract_term_instead_of_example"}
    return {"is_correct": False, "error_flag": f"wrong_example: {value!r}"}


# ---------------------------------------------------------------------------
# B11 — Label role: Etiket
# ---------------------------------------------------------------------------

def _check_b11(value: str | None) -> dict[str, Any]:
    v = _norm(value)
    if not v or v in {"(bos)", "bos", "(okunamiyor)"}:
        return {"is_correct": False, "error_flag": "blank"}
    if _contains_any(v, LABEL_TERMS):
        return {"is_correct": True, "error_flag": None}
    return {"is_correct": False, "error_flag": f"wrong_term: {value!r}"}


# ---------------------------------------------------------------------------
# Summary generator
# ---------------------------------------------------------------------------

def generate_ws1_system_analytical_summary(
    raw: dict[str, Any],
    validation: dict[str, Any],
) -> str:
    checks = validation.get("item_checks", {})
    parts: list[str] = []

    def ok(key: str) -> bool:
        return checks.get(key, {}).get("is_correct") is True

    def flag(key: str) -> str:
        return checks.get(key, {}).get("error_flag") or ""

    # --- Diyagram bölümü (B1-B4) ---
    diagram_correct = [k for k in ("WS1_B1", "WS1_B2", "WS1_B3", "WS1_B4") if ok(k)]
    diagram_errors  = [k for k in ("WS1_B1", "WS1_B2", "WS1_B3", "WS1_B4")
                       if checks.get(k, {}).get("is_correct") is False]

    if len(diagram_correct) == 4:
        parts.append("Diyagram (B1-B4): Etiket, Nesne, Özellik ve Değer dört kavram da doğru eşleştirilmiş.")
    else:
        # B4 feature_term error is the dominant pattern — name it explicitly
        if flag("WS1_B4") == "feature_term_instead_of_value_term":
            parts.append(
                f"Diyagram (B1-B4): B4'te 'Değer' yerine özellik terimi yazılmış "
                f"({raw.get('WS1_B4')!r}) — özellik ile değer kavramları karıştırılmış."
            )
        elif flag("WS1_B4") == "concrete_example_instead_of_term":
            parts.append(
                f"Diyagram (B1-B4): B4'te somut bir değer yazılmış ({raw.get('WS1_B4')!r}) "
                f"— soyut terim ('Değer') bekleniyor."
            )
        # B3 wrong term (e.g. "Etiket" instead of Özellik)
        if flag("WS1_B3") and "wrong_term" in flag("WS1_B3"):
            parts.append(
                f"B3'te 'Özellik/Karakteristik/Değişken' yerine hatalı terim yazılmış "
                f"({raw.get('WS1_B3')!r})."
            )
        # Other B1/B2 errors
        for k in ("WS1_B1", "WS1_B2"):
            f = flag(k)
            if f == "concrete_example_instead_of_term":
                parts.append(f"{k}: Soyut terim yerine somut örnek yazılmış ({raw.get(k)!r}).")
            elif f and "wrong_term" in f:
                parts.append(f"{k}: Hatalı terim ({raw.get(k)!r}).")

        if not parts:
            errs = ", ".join(f"{k}={raw.get(k)!r}" for k in diagram_errors)
            parts.append(f"Diyagram (B1-B4): Hata(lar): {errs}.")

    # --- Paragraf bölümü (B5-B7) ---
    para_errors = [k for k in ("WS1_B5", "WS1_B6", "WS1_B7")
                   if checks.get(k, {}).get("is_correct") is False]
    if not para_errors:
        parts.append("Paragraf (B5-B7): Nesne ve Özellik terimleri metin içinde doğru kullanılmış.")
    else:
        errs = ", ".join(f"{k}={raw.get(k)!r}" for k in para_errors)
        parts.append(f"Paragraf (B5-B7): Terim hatası — {errs}.")

    # --- Sayısal bilgi (B8) ---
    b8 = checks.get("WS1_B8", {})
    if b8.get("is_correct") is True:
        parts.append("B8 (Özellik sayısı): Doğru — 7.")
    elif flag("WS1_B8") == "wrote_term_instead_of_count":
        parts.append(
            f"B8 (Özellik sayısı): Sayı yerine terim yazılmış ({raw.get('WS1_B8')!r}) "
            f"— 'kaç tane' sorusunu kavramsal terimle yanıtlamış."
        )
    elif flag("WS1_B8") == "blank":
        parts.append("B8 (Özellik sayısı): Boş bırakılmış.")
    else:
        parts.append(f"B8 (Özellik sayısı): Hatalı — {raw.get('WS1_B8')!r}, beklenen 7.")

    # --- Özellik listesi (B9) ---
    b9 = checks.get("WS1_B9", {})
    found = b9.get("found_count", 0)
    if b9.get("is_correct") is True:
        parts.append(f"B9 (Özellik listesi): Yeterli — {found}/7 tespit edildi.")
    elif flag("WS1_B9") == "examples_instead_of_feature_names":
        parts.append(
            "B9 (Özellik listesi): Özellik adları yerine özellik-değer örnek cümleleri yazılmış "
            "— liste formatı kullanılmamış."
        )
    elif "incomplete_feature_list" in flag("WS1_B9"):
        parts.append(f"B9 (Özellik listesi): Eksik — {found}/7 tespit edildi.")
    elif flag("WS1_B9") == "blank":
        parts.append("B9 (Özellik listesi): Boş bırakılmış.")
    else:
        parts.append("B9 (Özellik listesi): Tespit edilemedi.")

    # --- Somutlama (B10-B11) ---
    b10_ok = ok("WS1_B10")
    b11_ok = ok("WS1_B11")

    if b10_ok and b11_ok:
        parts.append("B10-B11: Somut gıda örneği (Fındıklı Gofret) ve etiket rolü doğru.")
    else:
        if flag("WS1_B10") == "abstract_term_instead_of_example":
            parts.append(
                "B10 (Örnek nesne): 'Nesne' terimi yazılmış, somut gıda adı (Fındıklı Gofret) yazılmamış."
            )
        elif not b10_ok:
            parts.append(f"B10 (Örnek nesne): Hatalı — {raw.get('WS1_B10')!r}.")
        if not b11_ok:
            parts.append(f"B11 (Etiket rolü): Hatalı — {raw.get('WS1_B11')!r}, beklenen 'Etiket'.")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_ws1_validation_block(raw: dict[str, Any]) -> dict[str, Any]:
    item_checks = {
        "WS1_B1":  _check_b1(raw.get("WS1_B1")),
        "WS1_B2":  _check_b2(raw.get("WS1_B2")),
        "WS1_B3":  _check_b3(raw.get("WS1_B3")),
        "WS1_B4":  _check_b4(raw.get("WS1_B4")),
        "WS1_B5":  _check_object_term(raw.get("WS1_B5")),
        "WS1_B6":  _check_object_term(raw.get("WS1_B6")),
        "WS1_B7":  _check_feature_term(raw.get("WS1_B7")),
        "WS1_B8":  _check_b8(raw.get("WS1_B8")),
        "WS1_B9":  _check_b9(raw.get("WS1_B9")),
        "WS1_B10": _check_b10(raw.get("WS1_B10")),
        "WS1_B11": _check_b11(raw.get("WS1_B11")),
    }

    validation: dict[str, Any] = {"item_checks": item_checks}
    validation["system_analytical_summary"] = generate_ws1_system_analytical_summary(
        raw, validation
    )
    return validation
