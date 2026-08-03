#!/usr/bin/env python3
"""Audit 2025 frame extraction and observer label reliability.

Three questions:
  1. Are frames necessary?  (what does the pipeline lose without them)
  2. How reliable is observer labeling?  (confidence histogram + per-student breakdown)
  3. Where are the specific failure modes?  (students / steps below threshold)

Prints a structured report and exits 0 if the cohort meets minimum quality
thresholds, non-zero otherwise.

Usage:
    python scripts/audit_2025_frame_reliability.py
    python scripts/audit_2025_frame_reliability.py --threshold 0.70 --verbose
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "training_datasets" / "2025"

# A silver match is "reliable" if confidence is high or medium.
RELIABLE = {"high", "medium"}

# Minimum fraction of gold steps that must have a reliable silver match.
DEFAULT_COHORT_THRESHOLD = 0.65   # 65% across all steps
DEFAULT_STUDENT_THRESHOLD = 0.50  # per-student floor


# ── helpers ──────────────────────────────────────────────────────────────────

def load_gold(student_id: str) -> dict | None:
    p = OUT_ROOT / student_id / f"{student_id}_gold_behavior_alignment.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def load_manifest(student_id: str) -> dict | None:
    p = OUT_ROOT / student_id / f"{student_id}_video_extraction_manifest.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def load_observation_steps(student_id: str) -> dict | None:
    p = OUT_ROOT / student_id / f"{student_id}_observation_steps.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text())


def student_ids() -> list[str]:
    return sorted(
        d.name for d in OUT_ROOT.iterdir()
        if d.is_dir() and (d / f"{d.name}_observation_steps.json").is_file()
    )


# ── Q1: frame necessity ───────────────────────────────────────────────────────

def assess_frame_necessity(student_id: str) -> dict:
    obs = load_observation_steps(student_id)
    manifest = load_manifest(student_id)

    has_codap_log = False   # no 2025 CODAP event CSVs exist
    has_transcript = manifest.get("modalities", {}).get("has_usable_transcript_modality", False) if manifest else False
    has_video = manifest.get("modalities", {}).get("has_video", False) if manifest else False
    has_docx_screenshots = (obs.get("steps_with_docx_shot", 0) > 0) if obs else False
    frames_extracted = manifest.get("summary", {}).get("total_frames_extracted", 0) if manifest else 0

    # Without frames, the only visual evidence is the static docx screenshots.
    # With frames, we also get temporal coverage between documented steps.
    missing_from_no_frames = []
    if has_video and not has_transcript:
        missing_from_no_frames.append("temporal_visual_coverage")
    if has_video and not has_codap_log:
        missing_from_no_frames.append("behavioral_timeline_anchor")
    if not has_docx_screenshots:
        missing_from_no_frames.append("fallback_visual_gt")

    return {
        "student_id": student_id,
        "has_video": has_video,
        "has_transcript": has_transcript,
        "has_codap_log": has_codap_log,
        "has_docx_screenshots": has_docx_screenshots,
        "frames_extracted": frames_extracted,
        "frames_necessary": has_video and (not has_transcript or not has_codap_log),
        "modalities_lost_without_frames": missing_from_no_frames,
    }


# ── Q2 & Q3: label reliability ────────────────────────────────────────────────

def assess_label_reliability(student_id: str) -> dict:
    gold = load_gold(student_id)
    if gold is None:
        return {"student_id": student_id, "status": "no_gold_file"}

    hist = Counter(gold.get("silver_confidence_histogram", {}))
    total = sum(hist.values())
    reliable_count = sum(hist.get(k, 0) for k in RELIABLE)
    pct = round(100.0 * reliable_count / total, 1) if total else 0.0

    # Collect steps that failed to match reliably
    weak_steps = []
    for row in gold.get("alignments", []):
        silver = row.get("silver_video", {})
        conf = silver.get("confidence", "none")
        if conf not in RELIABLE:
            weak_steps.append({
                "step": row["metadata"]["observation_step_index"],
                "confidence": conf,
                "hamming": silver.get("hamming"),
                "method": silver.get("method"),
                "behavior_codes": row.get("gold", {}).get("behavior_code_list", []),
            })

    # Behavior code extraction check: count steps where regex produced no codes
    no_code_steps = sum(
        1 for row in gold.get("alignments", [])
        if not row.get("gold", {}).get("behavior_code_list")
    )

    return {
        "student_id": student_id,
        "status": "ok",
        "steps": total,
        "reliable_matches": reliable_count,
        "reliable_pct": pct,
        "confidence_histogram": dict(hist),
        "vision_enabled": gold.get("vision_enabled", False),
        "no_code_steps": no_code_steps,
        "weak_steps": weak_steps,
    }


# ── behavior code extraction check ───────────────────────────────────────────

def check_behavior_code_coverage(student_id: str) -> dict:
    obs = load_observation_steps(student_id)
    gold = load_gold(student_id)
    if not obs or not gold:
        return {"student_id": student_id, "status": "missing_data"}

    step_count = obs.get("step_count", 0)
    coded = sum(
        1 for row in gold.get("alignments", [])
        if row.get("gold", {}).get("behavior_code_list")
    )
    return {
        "student_id": student_id,
        "total_steps": step_count,
        "steps_with_codes": coded,
        "code_coverage_pct": round(100.0 * coded / step_count, 1) if step_count else 0,
    }


# ── report ────────────────────────────────────────────────────────────────────

def run_audit(
    *,
    cohort_threshold: float,
    student_threshold: float,
    verbose: bool,
) -> int:
    students = student_ids()
    print(f"\n{'='*64}")
    print(f"  2025 Frame & Observer-Label Reliability Audit")
    print(f"  Cohort: {len(students)} students")
    print(f"{'='*64}\n")

    # Q1 — Necessity
    print("── Q1: Are frames necessary? ──────────────────────────────")
    necessity_rows = [assess_frame_necessity(s) for s in students]
    frames_necessary = sum(1 for r in necessity_rows if r["frames_necessary"])
    no_video = sum(1 for r in necessity_rows if not r["has_video"])
    has_transcript = sum(1 for r in necessity_rows if r["has_transcript"])
    print(f"  Students with video:      {len(students) - no_video}/{len(students)}")
    print(f"  Students with transcript: {has_transcript}/{len(students)}")
    print(f"  No CODAP event log:       ALL (2025 cohort has no log CSVs)")
    print(f"  Frames necessary:         {frames_necessary}/{len(students)}")
    print()
    print("  WITHOUT frames → only static docx screenshots available.")
    print("  That means NO temporal coverage between documented steps,")
    print("  NO behavioral timeline anchor, and NO visual evidence for")
    print("  frames where the observer did not take a screenshot.")
    print()
    losing_sets: Counter = Counter()
    for r in necessity_rows:
        for m in r.get("modalities_lost_without_frames", []):
            losing_sets[m] += 1
    for modality, count in losing_sets.most_common():
        print(f"  Modality lost without frames [{modality}]: {count} students")
    print()

    # Q2 — Label reliability
    print("── Q2: Observer labeling reliability ──────────────────────")
    reliability_rows = [assess_label_reliability(s) for s in students]
    ok_rows = [r for r in reliability_rows if r.get("status") == "ok"]

    total_steps = sum(r["steps"] for r in ok_rows)
    total_reliable = sum(r["reliable_matches"] for r in ok_rows)
    cohort_pct = round(100.0 * total_reliable / total_steps, 1) if total_steps else 0.0

    global_hist: Counter = Counter()
    for r in ok_rows:
        for k, v in r["confidence_histogram"].items():
            global_hist[k] += v

    print(f"  Cohort silver-match confidence histogram:")
    for conf in ("high", "medium", "low", "weak", "none", "unavailable"):
        cnt = global_hist.get(conf, 0)
        bar = "#" * (cnt // 2)
        print(f"    {conf:12s}: {cnt:4d}  {bar}")
    print(f"\n  Reliable (high+medium): {total_reliable}/{total_steps} steps  "
          f"= {cohort_pct}%  [threshold={cohort_threshold*100:.0f}%]")
    print()

    # Per-student breakdown
    print("  Per-student breakdown:")
    failing_students = []
    header = f"  {'Student':<12} {'Steps':>6} {'High+Med':>10} {'Pct':>7}  {'Vision':>6}  Status"
    print(header)
    print(f"  {'-'*65}")
    for r in sorted(ok_rows, key=lambda x: x["reliable_pct"]):
        sid = r["student_id"]
        steps = r["steps"]
        rel = r["reliable_matches"]
        pct = r["reliable_pct"]
        vis = "Y" if r["vision_enabled"] else "N"
        threshold_met = pct / 100 >= student_threshold
        tag = "OK" if threshold_met else "BELOW THRESHOLD"
        if not threshold_met:
            failing_students.append(sid)
        print(f"  {sid:<12} {steps:>6} {rel:>10} {pct:>6.1f}%  {vis:>6}  {tag}")
    print()

    # Q3 — Failure modes
    if failing_students or verbose:
        print("── Q3: Failure-mode detail ─────────────────────────────────")
        problem_students = failing_students if not verbose else [r["student_id"] for r in ok_rows]
        for sid in problem_students:
            r = next((x for x in ok_rows if x["student_id"] == sid), None)
            if not r:
                continue
            print(f"\n  [{sid}]  {r['reliable_pct']}% reliable  "
                  f"vision_enabled={r['vision_enabled']}")
            hist = r["confidence_histogram"]
            weak = hist.get("weak", 0)
            low = hist.get("low", 0)
            unavail = hist.get("unavailable", 0)
            none_ = hist.get("none", 0)
            print(f"    weak={weak}  low={low}  unavailable={unavail}  none={none_}")
            if r.get("no_code_steps"):
                print(f"    Steps with no behavior codes: {r['no_code_steps']}")
            if verbose and r.get("weak_steps"):
                print(f"    Weak/failing steps (first 5):")
                for ws in r["weak_steps"][:5]:
                    print(f"      step={ws['step']:3d}  conf={ws['confidence']:<8s}  "
                          f"hamming={str(ws['hamming']):<5}  codes={ws['behavior_codes']}")

    # Behavior code coverage
    print("\n── Behavior code extraction coverage ───────────────────────")
    code_rows = [check_behavior_code_coverage(s) for s in students]
    for r in code_rows:
        if r.get("status") == "missing_data":
            continue
        pct = r["code_coverage_pct"]
        tag = "" if pct >= 80 else "  ← low"
        print(f"  {r['student_id']:<12} {r['steps_with_codes']:>4}/{r['total_steps']:<4}  "
              f"{pct:5.1f}%{tag}")
    print()

    # Vision upgrade candidates — exclude students whose video is frozen
    # (all silver confidences = "unavailable" means no frames exist to compare)
    print("── Vision upgrade candidates ───────────────────────────────")
    upgrade_needed = [
        r for r in ok_rows
        if not r["vision_enabled"]
        and r["reliable_pct"] / 100 < cohort_threshold  # any student below cohort bar
        and r["confidence_histogram"].get("unavailable", 0) != r["steps"]
        and (r["confidence_histogram"].get("weak", 0) + r["confidence_histogram"].get("low", 0)) > 0
    ]
    frozen_excluded = [
        r["student_id"] for r in ok_rows
        if r["confidence_histogram"].get("unavailable", 0) == r["steps"]
    ]
    if frozen_excluded:
        print(f"  Excluded (frozen video, Vision cannot help): {', '.join(frozen_excluded)}")
    if upgrade_needed:
        names = [r["student_id"] for r in upgrade_needed]
        print(f"  {len(upgrade_needed)} students need --vision re-run:")
        for r in upgrade_needed:
            print(f"    {r['student_id']:<12} {r['reliable_pct']}%")
        print(f"\n  Run:\n    python scripts/finalize_2025_gold_alignment.py --vision {' '.join(names)}")
    else:
        print("  All students already have vision or meet threshold.")
    print()

    # Final verdict
    print("── Verdict ─────────────────────────────────────────────────")
    passes = cohort_pct / 100 >= cohort_threshold
    print(f"  Cohort reliable match rate: {cohort_pct}%  {'PASS' if passes else 'FAIL'}")
    print(f"  Students below per-student threshold: {len(failing_students)}")
    if failing_students:
        print(f"  Failing: {', '.join(failing_students)}")
    print()

    return 0 if (passes and not failing_students) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Audit 2025 frame & label reliability")
    ap.add_argument("--threshold", type=float, default=DEFAULT_COHORT_THRESHOLD,
                    help="Cohort-level minimum reliable-match fraction (default 0.65)")
    ap.add_argument("--student-threshold", type=float, default=DEFAULT_STUDENT_THRESHOLD,
                    help="Per-student minimum (default 0.50)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    return run_audit(
        cohort_threshold=args.threshold,
        student_threshold=args.student_threshold,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    raise SystemExit(main())
