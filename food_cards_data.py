"""
ProDaBi unplugged food-card reference dataset (11 classroom cards).

Used by WS3–WS6 threshold and tree validation. CSV: data/prodabi_food_cards.csv
"""

from __future__ import annotations

import csv
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_CSV = REPO_ROOT / "data" / "prodabi_food_cards.csv"

FEATURE_ALIASES: dict[str, str] = {
    "enerji": "energy_kcal",
    "energy": "energy_kcal",
    "kcal": "energy_kcal",
    "yag": "fat_g",
    "yağ": "fat_g",
    "fat": "fat_g",
    "doymus yag": "saturated_fat_g",
    "doymuş yağ": "saturated_fat_g",
    "saturated fat": "saturated_fat_g",
    "karbonhidrat": "carbohydrates_g",
    "carbohydrates": "carbohydrates_g",
    "carbs": "carbohydrates_g",
    "seker": "sugar_g",
    "şeker": "sugar_g",
    "sugar": "sugar_g",
    "protein": "protein_g",
    "tuz": "salt_g",
    "salt": "salt_g",
}

INCLUSIVE_OPS = frozenset({"<=", "≤", ">=", "≥"})
STRICT_OPS = frozenset({"<", ">"})
VALID_OPS = INCLUSIVE_OPS | STRICT_OPS

# DT branch pairing: true-side op on evet / written threshold → required false-side op
# < ↔ ≥, > ↔ ≤, ≤ ↔ >, ≥ ↔ <
COMPLEMENTARY_OPERATOR: dict[str, str] = {
    "<=": ">",
    "≤": ">",
    "<": ">=",
    ">": "<=",
    ">=": "<",
    "≥": "<",
}


def normalize_operator(op: str) -> str:
    """Map unicode inequality symbols to ASCII tokens."""
    mapping = {"≤": "<=", "≥": ">=", "＜": "<", "＞": ">"}
    return mapping.get(op.strip(), op.strip())


def complementary_operator(op: str) -> str:
    """Return the operator required on the opposite DT branch."""
    return COMPLEMENTARY_OPERATOR[normalize_operator(op)]


def operators_are_complementary(true_op: str, false_op: str) -> bool:
    """True when false_op is the required complement of true_op (e.g. < and >=)."""
    return normalize_operator(false_op) == complementary_operator(true_op)


def parse_operator_in_text(text: str | None) -> str | None:
    """Extract the first comparison operator from a threshold or branch label."""
    if text is None or not str(text).strip():
        return None
    raw = str(text).replace("=<", "<=").replace("=>", ">=")
    for src, dst in (("≤", "<="), ("≥", ">="), ("＜", "<"), ("＞", ">")):
        raw = raw.replace(src, dst)
    for op in (">=", "<=", ">", "<"):
        if op in raw:
            return op
    return None


def normalize_token(text: str) -> str:
    s = unicodedata.normalize("NFKD", text.strip().lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    for src, dst in (("ı", "i"), ("ğ", "g"), ("ü", "u"), ("ş", "s"), ("ö", "o"), ("ç", "c")):
        s = s.replace(src, dst)
    return s.strip()


def resolve_feature(name: str) -> str | None:
    key = normalize_token(name)
    if key in FEATURE_ALIASES:
        return FEATURE_ALIASES[key]
    for alias, field in FEATURE_ALIASES.items():
        if normalize_token(alias) == key:
            return field
    return None


@lru_cache(maxsize=1)
def load_food_cards(csv_path: str | None = None) -> tuple[dict[str, Any], ...]:
    path = Path(csv_path) if csv_path else DEFAULT_CSV
    cards: list[dict[str, Any]] = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            cards.append({
                "card_id": row["card_id"],
                "name_tr": row["name_tr"],
                "name_en": row["name_en"],
                "label": row["label"],
                "recommended": row["label"] == "recommended",
                "energy_kcal": float(row["energy_kcal"]),
                "fat_g": float(row["fat_g"]),
                "saturated_fat_g": float(row["saturated_fat_g"]),
                "carbohydrates_g": float(row["carbohydrates_g"]),
                "sugar_g": float(row["sugar_g"]),
                "protein_g": float(row["protein_g"]),
                "salt_g": float(row["salt_g"]),
            })
    return tuple(cards)


def dataset_size(csv_path: str | None = None) -> int:
    return len(load_food_cards(csv_path))
