#!/usr/bin/env python3
"""Select a stratified validation sample from the 2025 calibration dataset.

Strategy:
  - For each behavior (B0-B17, excluding B13/B14 which have no 2025 labels):
      * Up to N_POS positive frames  (behavior present, direct_reliable preferred)
      * Up to N_NEG negative frames  (behavior absent, direct_reliable preferred)
  - Student diversity enforced: max MAX_PER_STUDENT frames per student total
  - Only frames whose image file actually exists on disk

Target: ~200-250 frames covering all scoreable behaviors with balanced pos/neg.

Output:
    calibration/validation_sample.json
"""

from __future__ import annotations

import json
import random
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / "calibration" / "2025_calibration_dataset.json"
GOLD_ROOT = REPO_ROOT / "training_datasets" / "2025"
OUT = REPO_ROOT / "calibration" / "validation_sample.json"

SEED = 42
N_POS = 10      # positive frames per behavior
N_NEG = 8       # negative frames per behavior (sampled from non-positive pool)
MAX_PER_STUDENT = 20

# Exclude: no labels in 2025 or requires transcript
SKIP_BEHAVIORS = {"B13", "B14"}

ALL_BEHAVIORS = [b for b in [
    "B0","B1","B2","B3","B4","B5","B6","B7",
    "B8","B9","B10","B11","B12",
    "B15","B16","B17",
] if b not in SKIP_BEHAVIORS]


def load_silver_conf(students: list[str]) -> dict[str, str]:
    conf_map: dict[str, str] = {}
    for sid in students:
        p = GOLD_ROOT / sid / f"{sid}_gold_behavior_alignment.json"
        if not p.is_file():
            continue
        gold = json.loads(p.read_text(encoding="utf-8"))
        for row in gold.get("alignments", []):
            fid = row.get("silver_video", {}).get("matched_frame_id")
            conf = row.get("silver_video", {}).get("confidence", "none")
            if fid:
                conf_map[fid] = conf
    return conf_map


def priority(frame: dict, conf_map: dict[str, str]) -> int:
    """Lower number = higher priority for selection."""
    conf = conf_map.get(frame["frame_id"], "none")
    if conf in ("high", "medium"):
        return 0
    if frame.get("label_source") == "nearest_gold_silver_anchor":
        if frame.get("expert_screenshot"):
            return 1
        return 2
    return 3


def select_diverse(
    candidates: list[dict],
    n: int,
    student_budget: dict[str, int],
) -> list[dict]:
    """Pick up to n frames, respecting per-student budget."""
    picked: list[dict] = []
    for c in candidates:
        if len(picked) >= n:
            break
        sid = c["student_id"]
        if student_budget.get(sid, 0) >= MAX_PER_STUDENT:
            continue
        picked.append(c)
        student_budget[sid] = student_budget.get(sid, 0) + 1
    return picked


def main() -> int:
    random.seed(SEED)

    dataset = json.loads(DATASET.read_text(encoding="utf-8"))
    frames = dataset["frames"]
    students = list(dataset["students"].keys())
    conf_map = load_silver_conf(students)

    # Filter to frames with existing images
    frames = [f for f in frames if Path(f["frame_image_path"]).is_file()]
    print(f"Frames with existing images: {len(frames)}")

    # Sort by priority (direct_reliable first)
    frames.sort(key=lambda f: (priority(f, conf_map), f["student_id"], f["timestamp_s"]))

    # Index by behavior
    pos_by_beh: dict[str, list[dict]] = defaultdict(list)
    for f in frames:
        for b in f["rubric_behaviors"]:
            pos_by_beh[b].append(f)

    selected_ids: set[str] = set()
    student_budget: dict[str, int] = {}
    records: list[dict] = []

    for bid in ALL_BEHAVIORS:
        positives = [f for f in pos_by_beh.get(bid, []) if f["frame_id"] not in selected_ids]
        picked_pos = select_diverse(positives, N_POS, student_budget)
        for f in picked_pos:
            selected_ids.add(f["frame_id"])
            records.append({**f, "_validation_role": "positive", "_target_behavior": bid})

    # Negative frames: frames that do NOT have the target behavior
    all_frame_index = {f["frame_id"]: f for f in frames}
    for bid in ALL_BEHAVIORS:
        pos_ids = {f["frame_id"] for f in pos_by_beh.get(bid, [])}
        neg_pool = [
            f for f in frames
            if f["frame_id"] not in pos_ids
            and f["frame_id"] not in selected_ids
        ]
        random.shuffle(neg_pool)
        neg_pool.sort(key=lambda f: priority(f, conf_map))
        picked_neg = select_diverse(neg_pool, N_NEG, student_budget)
        for f in picked_neg:
            selected_ids.add(f["frame_id"])
            records.append({**f, "_validation_role": "negative", "_target_behavior": bid})

    # Deduplicate (a frame may appear as positive for one behavior, negative for another)
    # Keep per frame_id the best record (positive role preferred)
    deduped: dict[str, dict] = {}
    for r in records:
        fid = r["frame_id"]
        if fid not in deduped or r["_validation_role"] == "positive":
            deduped[fid] = r

    final = sorted(deduped.values(), key=lambda r: (r["student_id"], r["timestamp_s"]))

    # Annotate with gold label for each behavior
    for r in final:
        r["gold_labels"] = {
            bid: (1 if bid in r["rubric_behaviors"] else 0)
            for bid in ALL_BEHAVIORS
        }
        r["silver_confidence"] = conf_map.get(r["frame_id"], "none")
        r.pop("_validation_role", None)
        r.pop("_target_behavior", None)

    payload = {
        "dataset_source": "2025_calibration_dataset",
        "selection_strategy": f"stratified pos≤{N_POS} neg≤{N_NEG} per behavior, max {MAX_PER_STUDENT} per student",
        "target_behaviors": ALL_BEHAVIORS,
        "total_frames": len(final),
        "student_counts": {sid: sum(1 for r in final if r["student_id"] == sid) for sid in students},
        "behavior_positive_counts": {
            bid: sum(1 for r in final if r["gold_labels"].get(bid, 0) == 1)
            for bid in ALL_BEHAVIORS
        },
        "frames": final,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"\nValidation sample: {len(final)} frames")
    print(f"Students: {sum(1 for v in payload['student_counts'].values() if v > 0)}")
    print()
    print(f"{'Behavior':<8}  {'Positive':>8}  {'Negative':>8}")
    print(f"  {'-'*28}")
    for bid in ALL_BEHAVIORS:
        pos = payload["behavior_positive_counts"][bid]
        neg = len(final) - pos
        print(f"  {bid:<8}  {pos:>8}  {neg:>8}")

    print(f"\nWrote → {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
