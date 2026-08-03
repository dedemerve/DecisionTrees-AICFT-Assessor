#!/usr/bin/env python3
"""Analyze the 2025 calibration dataset from multiple angles.

Angles covered:
  1. Per-rubric frame supply — how many labeled examples exist for each behavior
  2. Student completeness — which students demonstrate which behaviors
  3. Label confidence quality — how many calibration frames have high/medium silver match
  4. Temporal density — how spread are frames across each session
  5. Few-shot candidate selection — best frames per rubric for prompt injection
  6. Gap analysis — behaviors with insufficient coverage for reliable scoring

Usage:
    python scripts/analyze_2025_training_angles.py
    python scripts/analyze_2025_training_angles.py --few-shot-count 3
    python scripts/analyze_2025_training_angles.py --export-fewshot calibration/fewshot_examples.json
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_FILE = REPO_ROOT / "calibration" / "2025_calibration_dataset.json"
GOLD_ROOT = REPO_ROOT / "training_datasets" / "2025"

ALL_RUBRIC = ["B0","B1","B2","B3","B4","B5","B6","B7","B8","B9","B10","B11","B12","B13",
              "B14","B15","B16","B17"]

# Minimum frames to consider a behavior well-represented for few-shot selection
WELL_REPRESENTED_THRESHOLD = 100
SPARSE_THRESHOLD = 50


def load_dataset() -> dict:
    return json.loads(DATASET_FILE.read_text())


def load_silver_confidence(student_id: str) -> dict[str, str]:
    """Map frame_id -> silver confidence level from gold alignment."""
    p = GOLD_ROOT / student_id / f"{student_id}_gold_behavior_alignment.json"
    if not p.is_file():
        return {}
    data = json.loads(p.read_text())
    conf_map: dict[str, str] = {}
    for row in data.get("alignments", []):
        frame_id = row.get("silver_video", {}).get("matched_frame_id")
        conf = row.get("silver_video", {}).get("confidence", "none")
        if frame_id:
            conf_map[frame_id] = conf
    return conf_map


def angle_1_rubric_supply(frames: list[dict]) -> dict[str, int]:
    counts: Counter = Counter()
    for f in frames:
        for rb in f["rubric_behaviors"]:
            counts[rb] += 1
    return dict(counts)


def angle_2_student_completeness(frames: list[dict]) -> dict[str, set[str]]:
    student_rubrics: dict[str, set[str]] = defaultdict(set)
    for f in frames:
        for rb in f["rubric_behaviors"]:
            student_rubrics[f["student_id"]].add(rb)
    return dict(student_rubrics)


def angle_3_label_confidence(
    frames: list[dict],
    silver_maps: dict[str, dict[str, str]],
) -> dict[str, dict]:
    """Per-rubric label quality breakdown.

    Three categories:
      direct_high/medium  — frame was the silver match for a gold step (high/medium dHash or Vision)
      inherited           — frame inherited its label from the nearest temporally-adjacent step
      direct_low/weak     — direct silver match but below the reliable confidence band
    """
    rubric_conf: dict[str, Counter] = defaultdict(Counter)
    for f in frames:
        sid = f["student_id"]
        fid = f["frame_id"]
        label_src = f.get("label_source", "")
        conf = silver_maps.get(sid, {}).get(fid, "unknown")

        if conf in ("high", "medium"):
            bucket = "direct_reliable"
        elif conf in ("low", "weak"):
            bucket = "direct_weak"
        elif label_src == "nearest_gold_silver_anchor":
            bucket = "inherited"
        else:
            bucket = "unlabeled"

        for rb in f["rubric_behaviors"]:
            rubric_conf[rb][bucket] += 1
    return {rb: dict(c) for rb, c in rubric_conf.items()}


def angle_4_temporal_density(frames: list[dict]) -> dict[str, dict]:
    """Per-student: frames per minute of session, and behavior timeline spans."""
    student_ts: dict[str, list[float]] = defaultdict(list)
    for f in frames:
        student_ts[f["student_id"]].append(f["timestamp_s"])

    result: dict[str, dict] = {}
    for sid, timestamps in student_ts.items():
        if not timestamps:
            continue
        ts = sorted(timestamps)
        duration_min = (ts[-1] - ts[0]) / 60.0
        result[sid] = {
            "frame_count": len(ts),
            "session_span_min": round(duration_min, 1),
            "frames_per_min": round(len(ts) / duration_min, 2) if duration_min > 0 else 0,
            "first_ts_s": round(ts[0], 1),
            "last_ts_s": round(ts[-1], 1),
        }
    return result


def angle_5_few_shot_candidates(
    frames: list[dict],
    silver_maps: dict[str, dict[str, str]],
    count: int,
) -> dict[str, list[dict]]:
    """Select best labeled frames per rubric for few-shot prompt injection.

    Priority order:
      1. direct_reliable (high/medium dHash or Vision match) — most trustworthy
      2. inherited with expert_screenshot available — visual reference present
      3. inherited without expert_screenshot
      4. direct_weak — match exists but below threshold
    Student diversity is enforced: pick from different students where possible.
    """
    CONF_RANK = {"high": 0, "medium": 1, "low": 2, "weak": 3, "none": 4, "unknown": 5}

    rubric_candidates: dict[str, list[dict]] = defaultdict(list)
    for f in frames:
        sid = f["student_id"]
        fid = f["frame_id"]
        conf = silver_maps.get(sid, {}).get(fid, "unknown")
        conf_rank = CONF_RANK.get(conf, 5)
        has_expert_shot = bool(f.get("expert_screenshot"))
        label_src = f.get("label_source", "")
        # Sort key: direct_reliable < inherited+screenshot < inherited < weak
        if conf in ("high", "medium"):
            priority = 0
        elif label_src == "nearest_gold_silver_anchor" and has_expert_shot:
            priority = 1
        elif label_src == "nearest_gold_silver_anchor":
            priority = 2
        else:
            priority = 3

        for rb in f["rubric_behaviors"]:
            rubric_candidates[rb].append({
                "student_id": sid,
                "frame_id": fid,
                "frame_image_path": f["frame_image_path"],
                "expert_screenshot": f.get("expert_screenshot"),
                "codebook_codes": f["codebook_codes"],
                "rubric_behaviors": f["rubric_behaviors"],
                "timestamp_s": f["timestamp_s"],
                "silver_confidence": conf,
                "label_source": label_src,
                "_priority": priority,
                "_conf_rank": conf_rank,
            })

    selected: dict[str, list[dict]] = {}
    for rb in ALL_RUBRIC:
        candidates = sorted(
            rubric_candidates.get(rb, []),
            key=lambda x: (x["_priority"], x["_conf_rank"], x["timestamp_s"]),
        )
        # Prefer diversity: pick from different students
        seen_students: set[str] = set()
        picked: list[dict] = []
        for c in candidates:
            if c["student_id"] not in seen_students:
                picked.append(c)
                seen_students.add(c["student_id"])
            if len(picked) >= count:
                break
        # Remove internal sort keys before output
        for p in picked:
            p.pop("_conf_rank", None)
            p.pop("_priority", None)
        selected[rb] = picked

    return selected


def angle_6_gap_analysis(supply: dict[str, int]) -> list[dict]:
    gaps = []
    for rb in ALL_RUBRIC:
        cnt = supply.get(rb, 0)
        if rb == "B13":
            status = "unmeasurable"
            reason = "Requires audio transcript — none in 2025 data"
        elif cnt == 0:
            status = "no_data"
            reason = "No labeled frames"
        elif cnt < SPARSE_THRESHOLD:
            status = "sparse"
            reason = f"Only {cnt} frames — few-shot will be unreliable"
        elif cnt < WELL_REPRESENTED_THRESHOLD:
            status = "moderate"
            reason = f"{cnt} frames — acceptable but not abundant"
        else:
            status = "well_represented"
            reason = f"{cnt} frames"
        gaps.append({"behavior": rb, "frames": cnt, "status": status, "reason": reason})
    return gaps


def print_report(
    frames: list[dict],
    silver_maps: dict[str, dict[str, str]],
    few_shot: dict[str, list[dict]],
    few_shot_count: int,
) -> None:
    supply = angle_1_rubric_supply(frames)
    completeness = angle_2_student_completeness(frames)
    conf_breakdown = angle_3_label_confidence(frames, silver_maps)
    density = angle_4_temporal_density(frames)
    gaps = angle_6_gap_analysis(supply)

    total = len(frames)
    n_students = len(density)

    print(f"\n{'='*70}")
    print(f"  2025 Training System — Multi-Angle Analysis")
    print(f"  {n_students} students    {total} labeled frames")
    print(f"{'='*70}\n")

    # Angle 1: Supply
    print("── Angle 1: Per-rubric frame supply ───────────────────────────────")
    print(f"  {'Behavior':<8} {'Frames':>7}  {'Status':<18}  Reason")
    print(f"  {'-'*62}")
    for g in gaps:
        rb = g["behavior"]
        cnt = g["frames"]
        status = g["status"]
        reason = g["reason"]
        print(f"  {rb:<8} {cnt:>7}  {status:<18}  {reason}")
    print()

    # Angle 2: Student completeness matrix
    print("── Angle 2: Student behavior completeness ─────────────────────────")
    behaviors_short = ALL_RUBRIC
    header = f"  {'Student':<12}  " + "  ".join(f"{rb:<3}" for rb in behaviors_short)
    print(header)
    print(f"  {'-'*75}")
    for sid in sorted(completeness.keys()):
        rb_set = completeness[sid]
        cells = "  ".join("Y  " if rb in rb_set else ".  " for rb in behaviors_short)
        print(f"  {sid:<12}  {cells}")
    print()

    # Angle 3: Label quality breakdown
    print("── Angle 3: Label quality per rubric ──────────────────────────────")
    print("  (direct_reliable = frame directly silver-matched with high/medium confidence)")
    print("  (inherited       = frame labelled via nearest temporally-adjacent gold step)")
    print("  (direct_weak     = silver match exists but below reliable threshold)")
    print()
    print(f"  {'Behavior':<8} {'Direct-OK':>10} {'Inherited':>10} {'Direct-Wk':>10}  Direct-OK%")
    print(f"  {'-'*55}")
    for rb in ALL_RUBRIC:
        conf = conf_breakdown.get(rb, {})
        d_ok  = conf.get("direct_reliable", 0)
        inh   = conf.get("inherited", 0)
        d_wk  = conf.get("direct_weak", 0)
        total_rb = d_ok + inh + d_wk
        pct = round(100.0 * d_ok / total_rb, 1) if total_rb else 0.0
        note = "  [unmeasurable]" if rb == "B13" else ""
        print(f"  {rb:<8} {d_ok:>10} {inh:>10} {d_wk:>10}  {pct:>8.1f}%{note}")
    print()
    print("  Note: 'inherited' labels are valid — temporal proximity is the design intent.")
    print("  Direct-OK frames make the strongest few-shot examples.")
    print()

    # Angle 4: Temporal density
    print("── Angle 4: Session temporal density ──────────────────────────────")
    print(f"  {'Student':<12} {'Frames':>7} {'Span(min)':>10} {'fps/min':>8}")
    print(f"  {'-'*42}")
    for sid, d in sorted(density.items()):
        print(f"  {sid:<12} {d['frame_count']:>7} {d['session_span_min']:>10.1f} {d['frames_per_min']:>8.2f}")
    print()

    # Angle 5: Few-shot candidates
    print(f"── Angle 5: Few-shot candidates ({few_shot_count} per behavior) ──────────────────")
    print(f"  {'Behavior':<8}  {'Student':<12}  {'Conf':<8}  {'LabelSrc'}")
    print(f"  {'-'*58}")
    for rb in ALL_RUBRIC:
        picks = few_shot.get(rb, [])
        if not picks:
            print(f"  {rb:<8}  (no candidates)")
            continue
        for p in picks:
            src = "direct" if p["silver_confidence"] in ("high","medium") else p.get("label_source","?")[:12]
            print(f"  {rb:<8}  {p['student_id']:<12}  {p['silver_confidence']:<8}  {src}")
    print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Multi-angle analysis of 2025 training data")
    ap.add_argument("--few-shot-count", type=int, default=3,
                    help="Number of few-shot candidates to select per rubric (default 3)")
    ap.add_argument("--export-fewshot", type=Path,
                    help="Write few-shot candidates to this JSON file")
    args = ap.parse_args(argv)

    if not DATASET_FILE.is_file():
        print("ERROR: calibration/2025_calibration_dataset.json not found.")
        print("Run: python scripts/build_2025_calibration_dataset.py first.")
        return 1

    dataset = load_dataset()
    frames = dataset["frames"]

    # Load silver confidence maps for all students
    students = list({f["student_id"] for f in frames})
    silver_maps = {sid: load_silver_confidence(sid) for sid in students}

    few_shot = angle_5_few_shot_candidates(frames, silver_maps, args.few_shot_count)

    print_report(frames, silver_maps, few_shot, args.few_shot_count)

    if args.export_fewshot:
        out = {
            "source": "2025_calibration_dataset",
            "few_shot_count_per_rubric": args.few_shot_count,
            "candidates": few_shot,
        }
        args.export_fewshot.write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Few-shot candidates written to {args.export_fewshot}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
