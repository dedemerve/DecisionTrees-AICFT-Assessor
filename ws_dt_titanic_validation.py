"""Validation + ocr_output export for WS15."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pipeline_schema import load_rubric

REPO_ROOT = Path(__file__).resolve().parent
OCR_OUTPUT_DIR = REPO_ROOT / "ocr_output"

TITANIC_ITEM_IDS = [f"DTI_{i:02d}" for i in range(1, 48)]

SECTION_RANGES: dict[str, range] = {
    "titanic_vs1_egitim": range(1, 10),
    "titanic_vs1_test": range(10, 19),
    "titanic_vs1_interpretation": range(19, 23),
    "titanic_vs2_egitim": range(23, 32),
    "titanic_vs2_test": range(32, 41),
    "titanic_vs2_interpretation": range(41, 45),
    "genel_sorular": range(45, 48),
}

METRIC_KEYS = (
    ("vs1_egitim", "egitim_veri_seti1", (5, 6, 7, 8, 9)),
    ("vs1_test", "test_veri_seti1", (14, 15, 16, 17, 18)),
    ("vs2_egitim", "egitim_veri_seti2", (27, 28, 29, 30, 31)),
    ("vs2_test", "test_veri_seti2", (36, 37, 38, 39, 40)),
)
METRIC_NAMES = ("accuracy", "sensitivity", "specificity", "precision", "MCR")

BLANK = frozenset({"(bos)", "(okunamiyor)", "(missing)", "(not_extracted)", ""})


def _item_id(n: int) -> str:
    return f"DTI_{n:02d}"


def sectioned_extraction(items: dict[str, str]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for section, nums in SECTION_RANGES.items():
        out[section] = {_item_id(n): items.get(_item_id(n), "(not_extracted)") for n in nums}
    return out


def _parse_int(text: str) -> int | None:
    if not text or text in BLANK:
        return None
    m = re.search(r"-?\d+", str(text).replace(".", "").replace(",", ""))
    return int(m.group()) if m else None


def _parse_ratio_value(text: str) -> float | None:
    if not text or text in BLANK:
        return None
    s = str(text).strip().lower().replace(",", ".")
    s = re.sub(r"\s*=\s*.*$", "", s)
    if re.fullmatch(r"1[,.]0*|1", s):
        return 1.0
    if re.fullmatch(r"0[,.]0*|0", s):
        return 0.0
    m = re.search(r"=\s*\(?\s*([01](?:\.\d+)?)\s*\)?\s*$", s)
    if m:
        return float(m.group(1))
    if "/" in s:
        parts = re.split(r"/", s)
        if len(parts) == 2:
            num = _parse_float_expr(parts[0])
            den = _parse_float_expr(parts[1])
            if num is not None and den and den != 0:
                return round(num / den, 3)
    val = _parse_float_expr(s)
    if val is not None and 0 <= val <= 1.5:
        return round(val, 3)
    pct = re.search(r"(\d{1,3})\s*%", s)
    if pct:
        return round(int(pct.group(1)) / 100, 3)
    return None


def _parse_float_expr(expr: str) -> float | None:
    expr = expr.strip().replace(",", ".")
    expr = re.sub(r"[^\d.+\-*/() ]", "", expr)
    if not expr:
        return None
    if re.fullmatch(r"\d+(?:\.\d+)?", expr):
        return float(expr)
    nums = re.findall(r"\d+(?:\.\d+)?", expr)
    if not nums:
        return None
    if "+" in expr and "/" not in expr:
        return float(sum(float(n) for n in nums))
    if len(nums) == 1:
        return float(nums[0])
    return None


def _normalize_canonical_block(raw: dict[str, Any]) -> dict[str, Any]:
    """Flatten WS15 nested canonical into flat keys used by validators."""
    if "root_total" in raw:
        return dict(raw)
    out: dict[str, Any] = {
        "root_total": raw.get("root"),
        "root_survived": raw.get("root_survived"),
        "N": raw.get("N") or raw.get("root"),
        "TP": raw.get("TP"),
        "TN": raw.get("TN"),
        "FP": raw.get("FP"),
        "FN": raw.get("FN"),
    }
    female = raw.get("female") or {}
    male = raw.get("male") or {}
    if isinstance(female, dict):
        out["female_n"] = female.get("total")
        out["female_survived"] = female.get("survived")
        out["female_died"] = female.get("died")
    if isinstance(male, dict):
        out["male_n"] = male.get("total")
        out["male_survived"] = male.get("survived")
        out["male_died"] = male.get("died")
    metrics = raw.get("metrics") or {}
    for key in METRIC_NAMES:
        if key in raw:
            out[key] = raw[key]
        elif key in metrics:
            out[key] = metrics[key]
    return out


def _load_canonical() -> dict[str, Any]:
    raw = load_rubric("WS15")["titanic_canonical"]
    return {k: _normalize_canonical_block(v) for k, v in raw.items() if k != "note"}


def _metric_checks(items: dict[str, str], canonical: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    tol = 0.02
    for prefix, canon_key, dti_nums in METRIC_KEYS:
        canon = canonical[canon_key]
        for name, dti_n in zip(METRIC_NAMES, dti_nums):
            key = f"{prefix}_{name}"
            formula = items.get(_item_id(dti_n), "")
            student_val = _parse_ratio_value(formula)
            canon_val = float(canon[name])
            delta = None if student_val is None else round(abs(student_val - canon_val), 3)
            out[key] = {
                "student_formula": formula,
                "student_value": student_val,
                "canonical": canon_val,
                "delta": delta,
                "is_correct": student_val is not None and delta is not None and delta <= tol,
            }
    return out


def _detect_vs2_swap(items: dict[str, str], canonical: dict[str, Any]) -> dict[str, Any] | None:
    c = canonical["test_veri_seti2"]
    raw_65 = items.get("DTI_32", "")
    raw_66 = items.get("DTI_33", "")
    raw_67 = items.get("DTI_34", "")
    if raw_65 in BLANK and raw_66 in BLANK:
        return None

    nums_66 = [int(x) for x in re.findall(r"\d+", raw_66)]
    nums_67 = [int(x) for x in re.findall(r"\d+", raw_67)]
    swap = False
    if len(nums_66) >= 2 and nums_66[0] == c["female_died"] and nums_66[1] == c["female_survived"]:
        swap = True
    if len(nums_67) >= 2 and nums_67[0] == c["male_died"] and nums_67[1] == c["male_survived"]:
        swap = True
    if "124" in raw_65 or (len(nums_66) >= 2 and nums_66[1] == c["female_died"]):
        swap = True
    if not swap:
        return None

    corrected = {
        "DTI_32": f"{c['root_total']}/{c['root_total'] - c['root_survived']}",
        "DTI_33": f"{c['female_n']}/{c['female_survived']}",
        "DTI_34": f"{c['male_n']}/{c['male_survived']}",
    }
    return {
        "vs2_test_hayatta_kaldi_yanlisi": {
            "flag": "SURVIVED_DIED_SWAP",
            "status": "OPERATOR_CORRECTED",
            "original_student_readings": {"DTI_32": raw_65, "DTI_33": raw_66, "DTI_34": raw_67},
            "corrected_to": corrected,
            "description": "Hayatta/oldu sutun karisikligi; operator duzeltmesi uygulandi",
        }
    }


def _trap_questions(items: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for dti, premise in (
        ("DTI_43", "VS1 ifadesi VS2'ye uygulanir: egitim duyarliligi yuksekti. VS2 gercegi: ~%28."),
        ("DTI_44", "VS1 ifadesi VS2'ye uygulanir: egitim MCR dusuktu. VS2 gercegi: ~%60."),
    ):
        ans = items.get(dti, "")
        blank = ans in BLANK
        recognized = not blank and any(
            w in ans.lower()
            for w in ("ters", "yanlis", "dogru degil", "underfitting", "zaten", "dusuk", "yuksek degil")
        )
        out[dti] = {
            "flag": "TUZAK_SORU",
            "question_premise": premise,
            "student_answer": ans,
            "student_recognized_contradiction": recognized,
            "note": "Bos." if blank else ("Celiski fark edildi." if recognized else "Celiski belirtilmemis."),
        }
    return out


def apply_operator_corrections(items: dict[str, str]) -> tuple[dict[str, str], dict[str, Any]]:
    corrected = dict(items)
    reading_errors: dict[str, Any] = {}
    canon = _load_canonical()
    swap = _detect_vs2_swap(items, canon)
    if swap:
        reading_errors.update(swap)
        for k, v in swap["vs2_test_hayatta_kaldi_yanlisi"]["corrected_to"].items():
            corrected[k] = v
    root = items.get("DTI_10", "")
    if root and "96=56+40" in root.replace(" ", ""):
        reading_errors["vs1_test_root_node"] = {
            "flag": "ROOT_COUNT_ERROR",
            "student_value": root,
            "canonical": "231",
        }
    return corrected, reading_errors


def build_item_checks(
    items: dict[str, str],
    metrics: dict[str, Any],
    traps: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    metric_by_dti = {}
    for prefix, _, dti_nums in METRIC_KEYS:
        for name, dti_n in zip(METRIC_NAMES, dti_nums):
            metric_by_dti[_item_id(dti_n)] = f"{prefix}_{name}"

    checks: dict[str, dict[str, Any]] = {}
    for iid in TITANIC_ITEM_IDS:
        raw = items.get(iid, "")
        blank = raw in BLANK
        error_flag = None
        is_correct = not blank

        if blank:
            is_correct = False
            error_flag = "BLANK"
        elif iid in metric_by_dti:
            m = metrics.get(metric_by_dti[iid], {})
            if m.get("student_value") is not None:
                is_correct = bool(m.get("is_correct"))
                if not is_correct:
                    error_flag = "NUMERIC_TOLERANCE"
            else:
                is_correct = False
                error_flag = "UNPARSEABLE"
        elif iid in traps:
            trap = traps[iid]
            if blank:
                is_correct = False
                error_flag = "BLANK"
            elif trap.get("student_recognized_contradiction"):
                is_correct = True
            else:
                is_correct = False
                error_flag = "TRAP_NOT_RECOGNIZED"

        checks[iid] = {"is_correct": is_correct, "error_flag": error_flag}
    return checks


def build_validation(items: dict[str, str], *, ws_snapshot: str = "") -> dict[str, Any]:
    canon = _load_canonical()
    corrected, reading_errors = apply_operator_corrections(items)
    metrics = _metric_checks(corrected, canon)
    traps = _trap_questions(items)
    item_checks = build_item_checks(corrected, metrics, traps)
    correct_count = sum(1 for m in metrics.values() if m.get("is_correct"))
    summary = ws_snapshot or (
        f"Titanic metrik dogrulugu: {correct_count}/{len(metrics)}. "
        f"Tuzak DTI_43: {traps.get('DTI_43', {}).get('student_recognized_contradiction')}."
    )
    return {
        "titanic_numeric_checks": metrics,
        "titanic_reading_errors": reading_errors,
        "trap_question_check": traps,
        "item_checks": item_checks,
        "system_analytical_summary": summary,
    }


def build_ocr_output_document(
    student_id: str,
    items: dict[str, str],
    *,
    ws_snapshot: str = "",
    page_notes: str = "(bos)",
) -> dict[str, Any]:
    corrected, _ = apply_operator_corrections(items)
    validation = build_validation(items, ws_snapshot=ws_snapshot)
    return {
        "student_id": student_id,
        "worksheet": "WS15",
        "ws_snapshot": ws_snapshot or validation["system_analytical_summary"],
        "page_notes": page_notes,
        "extraction": sectioned_extraction(corrected),
        "validation": validation,
    }


def export_ocr_output(
    student_id: str,
    items: dict[str, str],
    *,
    ws_snapshot: str = "",
    page_notes: str = "(bos)",
) -> Path:
    doc = build_ocr_output_document(
        student_id, items, ws_snapshot=ws_snapshot, page_notes=page_notes,
    )
    out_dir = OCR_OUTPUT_DIR / student_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{student_id}_Worksheet_Titanic.json"
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
