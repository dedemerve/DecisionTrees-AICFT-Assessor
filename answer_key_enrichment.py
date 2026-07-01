"""
Enrich worksheet answer_key.json with field-level reference answers.

Merges rubric-derived item keys with frozen reference files and computed grids.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
DATA_DIR = REPO_ROOT / "data"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ws10_fields() -> dict[str, Any]:
    ref = _load_json(DATA_DIR / "ws10_energy_reference.json")
    out: dict[str, Any] = {}
    for fid, meta in ref.get("blank_map", {}).items():
        out[fid] = {
            "printed_blank": meta.get("blank_number"),
            "answer": meta.get("response"),
            "example_response": str(meta.get("response")),
            "scoring_mode": "fixed_exact",
            "source": "data/ws10_energy_reference.json",
        }
    return out


def _ws7_fields() -> dict[str, Any]:
    ref = _load_json(DATA_DIR / "ws7_sample_tree.json")
    out: dict[str, Any] = {}
    for fid, letter in ref.get("p1_answers", {}).items():
        out[fid] = {
            "answer": letter,
            "example_response": letter,
            "scoring_mode": "fixed_exact",
            "source": "data/ws7_sample_tree.json",
        }
    examples = {
        "WS7_B1": "Eğer şeker ≤ 10 ve yağ ≤ 5 ise → Tavsiye edilir.",
        "WS7_B2": "Eğer şeker ≤ 10 ve yağ > 5 ise → Tavsiye edilmez.",
        "WS7_B3": "Eğer şeker > 10 ise → Tavsiye edilmez.",
    }
    for fid, text in examples.items():
        out[fid] = {
            "example_response": text,
            "scoring_mode": "cross_worksheet",
            "depends_on": ["WS6"],
            "source": "ws7_validation (student WS6 tree)",
        }
    return out


def _ws5_fields() -> dict[str, Any]:
    """Sample_Student fixtures — counts are computed from prodabi cards for each threshold."""
    rows = [
        ("şeker ≤ 5", "8", "3", "0.27"),
        ("yağ ≤ 8", "8", "3", "0.27"),
        ("şeker ≤ 10", "8", "3", "0.27"),
        ("şeker ≤ 12", "9", "2", "0.18"),
        ("şeker ≤ 15", "9", "2", "0.18"),
    ]
    out: dict[str, Any] = {}
    for i, (thr, cor, err, mcr) in enumerate(rows, start=1):
        base = (i - 1) * 4
        mapping = {
            f"WS5_B{base + 1}": {"example_response": thr, "role": "threshold"},
            f"WS5_B{base + 2}": {"example_response": cor, "role": "correct"},
            f"WS5_B{base + 3}": {"example_response": err, "role": "errors"},
            f"WS5_B{base + 4}": {"example_response": mcr, "role": "mcr"},
        }
        for fid, meta in mapping.items():
            out[fid] = {
                **meta,
                "scoring_row": f"WS5_row{i}",
                "scoring_mode": "computed",
                "no_fixed_answer": True,
                "source": "data/prodabi_food_cards.csv (dynamic per threshold)",
            }
    out["WS5_B25"] = {
        "example_response": (
            "Şeker ≤ 12'yi tercih ederim; 2 yanlış sınıflandırma ile tablomdaki en düşük hata sayısı."
        ),
        "scoring_mode": "computed",
        "no_fixed_answer": True,
        "source": "ws5_validation (minimum errors among student's grid trials)",
    }
    return out


def _ws6_fields() -> dict[str, Any]:
    """Sample_Student fixtures — tree validated dynamically over prodabi cards."""
    canonical = {
        "WS6_B1": "şeker",
        "WS6_B2": "≤ 10",
        "WS6_B3": "evet (≤ 10)",
        "WS6_B4": "hayır (> 10)",
        "WS6_B5": "Tavsiye edilir",
        "WS6_B6": "yağ",
        "WS6_B7": "≤ 5",
        "WS6_B8": "evet (≤ 5)",
        "WS6_B9": "hayır (> 5)",
        "WS6_B10": "Tavsiye edilir",
        "WS6_B11": "Tavsiye edilmez",
        "WS6_B13": "Tavsiye edilmez",
    }
    return {
        fid: {
            "example_response": val,
            "scoring_mode": "computed",
            "no_fixed_answer": True,
            "source": "ws6_validation (student tree over data/prodabi_food_cards.csv)",
        }
        for fid, val in canonical.items()
    }


def _ws11_fields(rubric: dict[str, Any]) -> dict[str, Any]:
    feedback = _load_json(DATA_DIR / "ws11_feedback_reference.json")
    out: dict[str, Any] = {}
    for fid, meta in feedback.get("fields", {}).items():
        out[fid] = {
            "printed_question": meta.get("printed_question"),
            "question_tr": meta.get("prompt_tr"),
            "scoring_mode": meta.get("scoring_mode"),
            "no_correct_answer": True,
            "allowed_responses": meta.get("options"),
            "source": "data/ws11_feedback_reference.json",
        }
    for item_id, item in rubric.get("items", {}).items():
        if item_id.startswith("WS11_Q10_"):
            out[item_id] = {
                "answer": item.get("correct_answer"),
                "example_response": item.get("example_answer"),
                "scoring_mode": "fixed_exact",
                "deterministic": True,
            }
        elif item_id.startswith("WS11_Q11_"):
            out[item_id] = {
                "answer": item.get("correct_answer"),
                "example_response": str(item.get("correct_answer")),
                "scoring_mode": "fixed_exact",
                "deterministic": True,
            }
        elif item_id.startswith("WS11_Q12_"):
            checked = bool(item.get("correct"))
            out[item_id] = {
                "answer": checked,
                "example_response": "İşaretli" if checked else "İşaretlenmemiş",
                "scoring_mode": "fixed_exact",
                "deterministic": True,
            }
        elif item_id in {"WS11_B8a", "WS11_B8b", "WS11_B9"}:
            out[item_id] = {
                "example_response": item.get("example_answer"),
                "scoring_mode": "interpretive",
                "open_response": True,
            }
    return out


def _ws1_fields(rubric: dict[str, Any]) -> dict[str, Any]:
    examples = {
        "WS1_B1": "etiket",
        "WS1_B2": "nesne",
        "WS1_B3": "özellik",
        "WS1_B4": "değer",
        "WS1_B5": "nesne",
        "WS1_B6": "nesne",
        "WS1_B7": "özellik",
        "WS1_B8": "7",
        "WS1_B9": "Enerji, Yağ, Doymuş Yağ, Karbonhidrat, Şeker, Protein, Tuz",
        "WS1_B10": "Fındıklı Gofret",
        "WS1_B11": "etiket olarak",
    }
    out: dict[str, Any] = {}
    for fid, ex in examples.items():
        item = rubric.get("items", {}).get(fid, {})
        entry: dict[str, Any] = {
            "example_response": ex,
            "source": "rubrics/WS1_rubric.json",
        }
        if item.get("check") == "any_of_tokens":
            entry["scoring_mode"] = "equivalence"
            entry["accept_sets"] = item.get("accept_sets")
        elif item.get("check") == "unordered_token_set":
            entry["scoring_mode"] = "fixed_exact"
        else:
            entry["scoring_mode"] = "interpretive"
        out[fid] = entry
    return out


def _ws3_fields(rubric: dict[str, Any]) -> dict[str, Any]:
    examples = {
        "WS3_B1": "Tavsiye edilemez",
        "WS3_B2": "Yağ değeri 8g eşiğinin üstünde olduğu için tavsiye edilemez.",
        "WS3_B3": "Tavsiye edilebilir",
        "WS3_B4": "Yağ değeri 8g eşiğinin altında olduğu için tavsiye edilebilir.",
        "WS3_B5": "Tavsiye edilemez",
        "WS3_B6": "Yağ değeri 8g eşiğinin üstünde olduğu için tavsiye edilemez.",
        "WS3_B7": "şeker ≤ 10",
        "WS3_B8": "şeker > 10",
    }
    return {
        fid: {
            "example_response": ex,
            "scoring_mode": "interpretive" if fid in {"WS3_B2", "WS3_B4", "WS3_B6"} else "fixed_exact",
            "source": "rubrics/WS3_rubric.json",
        }
        for fid, ex in examples.items()
    }


def _ws4_fields() -> dict[str, Any]:
    return {
        "WS4_B1": {
            "example_response": "Avokado ile patates kızartması arasına çizgi (yeni eşik)",
            "scoring_mode": "interpretive",
        },
        "WS4_B2": {
            "example_response": "jelibon, kraker, yulaf, avokado",
            "scoring_mode": "fixed_exact",
            "answer_tokens": ["jelibon", "kraker", "yulaf", "avokado"],
        },
        "WS4_B3": {
            "example_response": "Yeni eşikle daha az yanlış sınıflandırma oldu.",
            "scoring_mode": "interpretive",
        },
        "WS4_B4": {
            "example_response": "Pia haklı; elma ile ahududu reçelinin yağ değerleri aynı.",
            "scoring_mode": "interpretive",
        },
        "WS4_B5": {
            "example_response": "408",
            "answer_range": [160, 2223],
            "scoring_mode": "fixed_exact",
        },
    }


FIELD_BUILDERS = {
    "WS1": lambda r: _ws1_fields(r),
    "WS3": lambda r: _ws3_fields(r),
    "WS4": lambda _: _ws4_fields(),
    "WS5": lambda _: _ws5_fields(),
    "WS6": lambda _: _ws6_fields(),
    "WS7": lambda _: _ws7_fields(),
    "WS10": lambda _: _ws10_fields(),
    "WS11": lambda r: _ws11_fields(r),
}


def enrich_answer_key(worksheet: str, rubric: dict[str, Any], base: dict[str, Any]) -> dict[str, Any]:
    """Add field-level answer reference section to an answer_key payload."""
    out = dict(base)
    builder = FIELD_BUILDERS.get(worksheet)
    if builder:
        out["fields"] = builder(rubric)
        out["field_note"] = (
            "Per-field reference for OCR/extraction alignment and Sample_Student fixtures. "
            "Interpretive fields carry example_response only."
        )
    return out
