#!/usr/bin/env python3
"""Sample IRR coding units from the 2025 calibration dataset.

Selects episodes (contiguous frame sequences) from irr_students split,
stratified to oversample rare behaviors (B2, B8, B11, B13).

Output:
    calibration/irr_sample_manifest.json
    calibration/irr_coding_sheet.csv

Usage:
    python scripts/sample_irr_units.py
    python scripts/sample_irr_units.py --n-episodes 100
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V2_CAL = REPO_ROOT / "calibration" / "2025_calibration_dataset_v2.json"
SPLITS = REPO_ROOT / "calibration" / "splits_2025.json"
OUT_MANIFEST = REPO_ROOT / "calibration" / "irr_sample_manifest.json"
OUT_SHEET = REPO_ROOT / "calibration" / "irr_coding_sheet.csv"

SEED = 42
EPISODE_LENGTH_S = 60.0  # seconds per episode
N_EPISODES_DEFAULT = 80
RARE_BEHAVIORS = {"B2", "B8", "B11"}  # oversample these
RARE_BOOST = 3  # multiplier for rare behavior frames in sampling


def group_into_episodes(frames: list[dict], episode_len: float) -> list[dict]:
    """Group consecutive frames into fixed-duration episodes."""
    if not frames:
        return []
    frames = sorted(frames, key=lambda f: f["timestamp_s"])
    episodes: list[dict] = []
    episode_frames: list[dict] = []
    ep_start = frames[0]["timestamp_s"]

    for f in frames:
        if f["timestamp_s"] - ep_start > episode_len and episode_frames:
            episodes.append({
                "episode_id": f"{episode_frames[0]['student_id']}_ep_{len(episodes)+1:03d}",
                "student_id": episode_frames[0]["student_id"],
                "start_s": ep_start,
                "end_s": episode_frames[-1]["timestamp_s"],
                "n_frames": len(episode_frames),
                "frame_ids": [f["frame_id"] for f in episode_frames],
                "behaviors_present": sorted(set(
                    b for f in episode_frames for b in f.get("rubric_behaviors", [])
                )),
                "silver_confidence_dominant": max(
                    set(f.get("silver_confidence", "none") for f in episode_frames),
                    key=lambda c: {"high": 3, "medium": 2, "low": 1, "none": 0}.get(c, 0)
                ),
            })
            episode_frames = []
            ep_start = f["timestamp_s"]
        episode_frames.append(f)

    if episode_frames:
        episodes.append({
            "episode_id": f"{episode_frames[0]['student_id']}_ep_{len(episodes)+1:03d}",
            "student_id": episode_frames[0]["student_id"],
            "start_s": ep_start,
            "end_s": episode_frames[-1]["timestamp_s"],
            "n_frames": len(episode_frames),
            "frame_ids": [f["frame_id"] for f in episode_frames],
            "behaviors_present": sorted(set(
                b for f in episode_frames for b in f.get("rubric_behaviors", [])
            )),
            "silver_confidence_dominant": "none",
        })
    return episodes


def main() -> int:
    ap = argparse.ArgumentParser(description="Sample IRR episodes")
    ap.add_argument("--n-episodes", type=int, default=N_EPISODES_DEFAULT)
    args = ap.parse_args()

    random.seed(SEED)

    if not V2_CAL.is_file():
        print("ERROR: Run build_2025_calibration_dataset_v2.py first.")
        return 1

    cal = json.loads(V2_CAL.read_text(encoding="utf-8"))
    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    irr_students = set(splits["irr_students"])

    irr_frames = [f for f in cal["frames"] if f["student_id"] in irr_students]
    print(f"IRR frames from irr_students: {len(irr_frames)}")

    # Group by student then into episodes
    by_student: dict[str, list[dict]] = defaultdict(list)
    for f in irr_frames:
        by_student[f["student_id"]].append(f)

    all_episodes: list[dict] = []
    for sid, frames in by_student.items():
        eps = group_into_episodes(frames, EPISODE_LENGTH_S)
        all_episodes.extend(eps)

    print(f"Total episodes: {len(all_episodes)}")

    # Stratified sampling: oversample rare behaviors
    rare_episodes = [e for e in all_episodes if any(b in e["behaviors_present"] for b in RARE_BEHAVIORS)]
    other_episodes = [e for e in all_episodes if e not in rare_episodes]

    random.shuffle(rare_episodes)
    random.shuffle(other_episodes)

    n_rare = min(len(rare_episodes), args.n_episodes // 3)
    n_other = min(len(other_episodes), args.n_episodes - n_rare)

    selected = rare_episodes[:n_rare] + other_episodes[:n_other]
    random.shuffle(selected)
    print(f"Selected: {len(selected)} episodes ({n_rare} rare-behavior, {n_other} other)")

    # Behavior coverage
    behavior_coverage: dict[str, int] = defaultdict(int)
    for e in selected:
        for b in e["behaviors_present"]:
            behavior_coverage[b] += 1

    manifest = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "2025_calibration_dataset_v2.json",
        "irr_students": sorted(irr_students),
        "n_episodes": len(selected),
        "episode_length_s": EPISODE_LENGTH_S,
        "rare_behaviors_oversampled": sorted(RARE_BEHAVIORS),
        "behavior_coverage": dict(sorted(behavior_coverage.items())),
        "episodes": selected,
    }

    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Manifest → {OUT_MANIFEST.relative_to(REPO_ROOT)}")

    # Write coding sheet CSV
    LEVELS = ["Deepen", "Acquire", "not_observed", "not_measurable"]
    behaviors_in_sheet = [
        "B0","B1","B2","B3","B4","B5","B6","B7","B8","B9","B10","B11","B12","B13"
    ]

    with OUT_SHEET.open("w", newline="", encoding="utf-8") as f:
        fieldnames = (
            ["episode_id", "student_id", "start_s", "end_s", "n_frames",
             "behaviors_present_indicator", "silver_confidence", "rater_id"]
            + [f"{b}_level" for b in behaviors_in_sheet]
            + [f"{b}_evidence" for b in behaviors_in_sheet]
            + ["general_notes"]
        )
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        # Two blank rows per episode (one per rater)
        for ep in selected:
            for rater in ["Rater_1", "Rater_2"]:
                row = {
                    "episode_id": ep["episode_id"],
                    "student_id": ep["student_id"],
                    "start_s": ep["start_s"],
                    "end_s": ep["end_s"],
                    "n_frames": ep["n_frames"],
                    "behaviors_present_indicator": "|".join(ep["behaviors_present"]),
                    "silver_confidence": ep["silver_confidence_dominant"],
                    "rater_id": rater,
                }
                for b in behaviors_in_sheet:
                    row[f"{b}_level"] = ""
                    row[f"{b}_evidence"] = ""
                row["general_notes"] = ""
                w.writerow(row)

    print(f"Coding sheet → {OUT_SHEET.relative_to(REPO_ROOT)}")
    print(f"\nBehavior coverage in sample:")
    for b, n in sorted(behavior_coverage.items()):
        print(f"  {b}: {n} episodes positive")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
