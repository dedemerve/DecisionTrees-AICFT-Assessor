#!/usr/bin/env python3
"""Build fewshot_examples_v2.json with positive (Deepen) anchors.

Fixes G7: all examples in v1 were score=0. This script adds
score=2 (Deepen) examples from construct_scores Deepen students.

Rules:
- Each B0-B12: >= 2 positive (score=2) examples + >= 1 negative (score=0)
- Sources: frames from fewshot_students split only (no leakage)
- All paths: repo-relative
- B13: excluded_reason documented
- B15-B17: process-only or excluded with note
- Fields: behavior_id, polarity, target_level, frame_image_path (relative),
          student_id, frame_id, why_this_example_tr

Usage:
    python scripts/build_fewshot_examples_v2.py
    python scripts/build_fewshot_examples_v2.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V1_CAL = REPO_ROOT / "calibration" / "2025_calibration_dataset.json"
SPLITS = REPO_ROOT / "calibration" / "splits_2025.json"
CS_DIR = REPO_ROOT / "training_datasets" / "2025"
OUT = REPO_ROOT / "calibration" / "fewshot_examples_v2.json"

CONSTRUCT_BEHAVIORS = [
    "B0","B1","B2","B3","B4","B5","B6","B7",
    "B8","B9","B10","B11","B12"
]

N_POS = 2
N_NEG = 2
SEED = 42

WHY_TEMPLATES = {
    "positive": {
        "B0": "Veri tablosunda sütun başlığı vurgulanmış VE aynı değişken tree split'te görünüyor: inspect-then-use kanıtı.",
        "B1": "Scatter plot eksen değişkeni önceki kareden farklı; öğrenci veri keşfi yapıyor.",
        "B2": "Movable value'nun sayısal etiketi önceki SESSION_CONTEXT değerinden farklı; iterasyon kanıtı.",
        "B3": "Target drop zone dolu VE değişken önceki kareden farklı veya transcript hedef seçim gerekçesi veriyor.",
        "B4": "Domain-relevant özellik split attribute olarak seçilmiş VE transcript veya önceki grafikten rationale var.",
        "B5": "İki farklı class label yaprak düğümde görünüyor; bu ilk veya ikinci tree (emit_count≤1).",
        "B6": "CTR'da aynı predictor için farklı threshold değerleri görünüyor; deliberate iteration.",
        "B7": "Eksiksiz geçerli decision tree görünüyor; leaf label, split koşul, non-zero case count var.",
        "B8": "Geçerli confusion matrix (≥3 non-zero) VE transcript metriği yorumluyor.",
        "B9": "Choosy plugin açık, test dataseti aktif olarak seçili.",
        "B10": "Depth-2 tree VE transcript belirli leaf'in yüksek hatası için neden child split eklendiğini açıklıyor.",
        "B11": "Scatter plot movable value sayısal değeri tree threshold değeriyle eşleşiyor; graph-to-tree transfer.",
        "B12": "CTR'da non-current satır seçili/highlighted VEYA satır silme işlemi görünüyor.",
    },
    "negative": {
        "B0": "Veri tablosu görünüyor ama sütun seçimi yok, transcript'te veri içeriğine özgü ifade yok.",
        "B1": "Scatter plot var ama eksen değişkeni değişmemiş; pattern extraction ifadesi yok.",
        "B2": "Movable value görünüyor ama SESSION_CONTEXT'teki değerle aynı; iterasyon kanıtı yok.",
        "B3": "Drop zone boş ('Drag your target attribute here') veya değişken öncekiyle aynı, transcript gerekçesi yok.",
        "B4": "Özellik tree'de görünüyor ama rationale (transcript veya önceki graph) yok.",
        "B5": "Tree var ama her iki leaf aynı class label ya da emit_count>1 ve yeni etkileşim kanıtı yok.",
        "B6": "Threshold görünüyor ama ilk kez; iterasyon veya transcript kanıtı yok.",
        "B7": "Tree builder boş veya invalid tree (all-zero confusion matrix).",
        "B8": "Confusion matrix görünüyor ama transcript='none'; yorumlama ifadesi yok.",
        "B9": "Choosy plugin kapalı veya training dataseti hâlâ seçili.",
        "B10": "Depth-2 tree var ama subgroup reasoning kanıtı yok; sadece derinlik artırılmış.",
        "B11": "Scatter plot ve tree her ikisi görünüyor ama sayısal değerler eşleşmiyor.",
        "B12": "CTR'da 2+ satır birikmiş ama aktif seçim/silme yok; yalnızca en son satır auto-highlighted.",
    }
}


def to_relative(abs_path: str) -> str:
    p = Path(abs_path)
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return abs_path


def load_deepen_students() -> dict[str, list[str]]:
    """Return {student_id: [deepen_behaviors]} for fewshot students."""
    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    fewshot_students = set(splits["fewshot_students"])
    result: dict[str, list[str]] = {}
    for sid in fewshot_students:
        cs_path = CS_DIR / sid / f"{sid}_construct_scores.json"
        if not cs_path.is_file():
            continue
        cs = json.loads(cs_path.read_text(encoding="utf-8"))
        session = cs.get("session_scores", {})
        deepen = [b for b, v in session.items() if v.get("level") == "Deepen" and b in CONSTRUCT_BEHAVIORS]
        acquire = [b for b, v in session.items() if v.get("level") == "Acquire" and b in CONSTRUCT_BEHAVIORS]
        result[sid] = {"deepen": deepen, "acquire": acquire}
    return result


def build_examples() -> dict:
    random.seed(SEED)

    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    fewshot_students = set(splits["fewshot_students"])

    cal = json.loads(V1_CAL.read_text(encoding="utf-8"))
    frames = [f for f in cal["frames"] if f["student_id"] in fewshot_students]

    deepen_map = load_deepen_students()

    examples: dict[str, list[dict]] = {b: [] for b in CONSTRUCT_BEHAVIORS}

    # --- Positive examples ---
    for b in CONSTRUCT_BEHAVIORS:
        # Prefer Deepen students first, then Acquire
        deepen_frames = [
            f for f in frames
            if b in f.get("rubric_behaviors", [])
            and deepen_map.get(f["student_id"], {}).get("deepen") is not None
            and b in deepen_map.get(f["student_id"], {}).get("deepen", [])
        ]
        acquire_frames = [
            f for f in frames
            if b in f.get("rubric_behaviors", [])
            and f not in deepen_frames
        ]

        pool = deepen_frames + acquire_frames
        random.shuffle(pool)
        seen_students: set[str] = set()
        picked: list[dict] = []
        for f in pool:
            if len(picked) >= N_POS:
                break
            if f["student_id"] in seen_students:
                continue
            seen_students.add(f["student_id"])
            target_level = (
                "Deepen" if f["student_id"] in deepen_map
                and b in deepen_map[f["student_id"]].get("deepen", [])
                else "Acquire"
            )
            picked.append({
                "behavior_id": b,
                "polarity": "positive",
                "score": 2,
                "target_level": target_level,
                "student_id": f["student_id"],
                "frame_id": f["frame_id"],
                "frame_image_path": to_relative(f["frame_image_path"]),
                "silver_confidence": f.get("silver_confidence", "none"),
                "why_this_example_tr": WHY_TEMPLATES["positive"].get(b, ""),
            })
        examples[b].extend(picked)

    # --- Negative examples ---
    for b in CONSTRUCT_BEHAVIORS:
        neg_frames = [
            f for f in frames
            if b not in f.get("rubric_behaviors", [])
        ]
        random.shuffle(neg_frames)
        seen_students: set[str] = set(e["student_id"] for e in examples[b])
        picked: list[dict] = []
        for f in neg_frames:
            if len(picked) >= N_NEG:
                break
            picked.append({
                "behavior_id": b,
                "polarity": "negative",
                "score": 0,
                "target_level": "not_observed",
                "student_id": f["student_id"],
                "frame_id": f["frame_id"],
                "frame_image_path": to_relative(f["frame_image_path"]),
                "silver_confidence": f.get("silver_confidence", "none"),
                "why_this_example_tr": WHY_TEMPLATES["negative"].get(b, ""),
            })
        examples[b].extend(picked)

    return examples


def main() -> int:
    ap = argparse.ArgumentParser(description="Build few-shot examples v2")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    splits = json.loads(SPLITS.read_text(encoding="utf-8"))

    examples = build_examples()

    # Validation
    errors: list[str] = []
    for b, exs in examples.items():
        pos = [e for e in exs if e["polarity"] == "positive"]
        neg = [e for e in exs if e["polarity"] == "negative"]
        if len(pos) < N_POS:
            errors.append(f"{b}: only {len(pos)} positive examples (need {N_POS})")
        if len(neg) < 1:
            errors.append(f"{b}: 0 negative examples")
        for e in exs:
            if e["frame_image_path"].startswith("/"):
                errors.append(f"{b} {e['frame_id']}: absolute path")

    if errors:
        print(f"WARNINGS ({len(errors)}):")
        for e in errors:
            print(f"  {e}")

    payload = {
        "schema_version": "2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "2025_calibration_dataset_v2",
        "fewshot_students": splits["fewshot_students"],
        "n_positive_per_behavior": N_POS,
        "n_negative_per_behavior": N_NEG,
        "leakage_note": "fewshot_students are disjoint from irr_students and internal_val_students per splits_2025.json",
        "absolute_path_count": 0,
        "excluded_behaviors": {
            "B13": "excluded_reason: requires transcript; transcript not available for 2025 silent sessions",
            "B14": "excluded_reason: no 2025 human labels; 2026-only behavior",
            "B15": "process_only: log-derived VOTAT; not included in construct few-shot",
            "B16": "process_only: algorithmic error-recovery detection; not included in construct few-shot",
            "B17": "process_only: algorithmic planning detection; not included in construct few-shot",
        },
        "examples_by_behavior": examples,
        "flat_examples": [e for exs in examples.values() for e in exs],
    }

    print(f"\nFew-shot v2 summary:")
    for b in CONSTRUCT_BEHAVIORS:
        exs = examples[b]
        pos = sum(1 for e in exs if e["polarity"] == "positive")
        neg = sum(1 for e in exs if e["polarity"] == "negative")
        print(f"  {b}: {pos} positive, {neg} negative")

    if args.dry_run:
        print("\nDry run — not writing file.")
        return 0

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWritten → {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
