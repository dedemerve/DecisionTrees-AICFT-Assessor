#!/usr/bin/env python3
"""Evaluate speaker labels against gold annotation clips."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcript_quality import DEFAULT_AUDIO_ROOT, REPO_ROOT
from transcript_speaker_utils import labeled_transcript_path, load_json

DEFAULT_GOLD = REPO_ROOT / "calibration" / "gold_speaker_labels.json"
DEFAULT_TEMPLATE = REPO_ROOT / "calibration" / "gold_speaker_labels_template.json"
LOGS_DIR = REPO_ROOT / "logs"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate labeled transcripts vs gold set.")
    p.add_argument("--gold", type=Path, default=DEFAULT_GOLD)
    p.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--bootstrap-template", action="store_true")
    return p.parse_args(argv)


def segments_in_clip(segments: list[dict], start: float, end: float) -> list[dict]:
    return [s for s in segments if float(s["end"]) > start and float(s["start"]) < end]


def bootstrap_gold_from_labeled(
    template: dict,
    audio_root: Path,
) -> dict:
    """Pre-fill gold clip segments from auto labels for human correction."""
    out = json.loads(json.dumps(template))
    for student_id, student_block in out.get("students", {}).items():
        labeled_path = labeled_transcript_path(audio_root / student_id, student_id)
        if not labeled_path.is_file():
            continue
        labeled = load_json(labeled_path)
        segments = labeled.get("segments") or []
        for clip in student_block.get("clips", []):
            clip_segs = segments_in_clip(segments, float(clip["start"]), float(clip["end"]))
            clip["segments"] = [
                {
                    "id": s.get("id"),
                    "start": s.get("start"),
                    "end": s.get("end"),
                    "text": s.get("text"),
                    "gold_role": s.get("speaker_role"),
                    "auto_role": s.get("speaker_role"),
                    "auto_method": s.get("speaker_method"),
                    "auto_confidence": s.get("speaker_confidence"),
                }
                for s in clip_segs
            ]
    return out


def compute_metrics(gold: dict, audio_root: Path) -> dict:
    per_role_tp: dict[str, int] = defaultdict(int)
    per_role_fp: dict[str, int] = defaultdict(int)
    per_role_fn: dict[str, int] = defaultdict(int)
    compared = 0
    clips_with_labels = 0

    for student_id, student_block in gold.get("students", {}).items():
        labeled_path = labeled_transcript_path(audio_root / student_id, student_id)
        if not labeled_path.is_file():
            continue
        labeled = load_json(labeled_path)
        auto_by_id = {s.get("id"): s for s in labeled.get("segments") or []}

        for clip in student_block.get("clips", []):
            gold_segments = clip.get("segments") or []
            human_labeled = [
                g
                for g in gold_segments
                if g.get("gold_role") and g.get("gold_role") != g.get("auto_role")
            ]
            if not human_labeled:
                continue
            clips_with_labels += 1
            for g in human_labeled:
                seg_id = g.get("id")
                gold_role = str(g.get("gold_role"))
                auto = auto_by_id.get(seg_id)
                if not auto:
                    continue
                auto_role = str(auto.get("speaker_role", "unknown"))
                compared += 1
                if auto_role == gold_role:
                    per_role_tp[gold_role] += 1
                else:
                    per_role_fp[auto_role] += 1
                    per_role_fn[gold_role] += 1

    roles = sorted(set(per_role_tp) | set(per_role_fp) | set(per_role_fn))
    per_role: dict[str, dict] = {}
    for role in roles:
        tp = per_role_tp[role]
        fp = per_role_fp[role]
        fn = per_role_fn[role]
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
        per_role[role] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

    return {
        "compared_segments": compared,
        "clips_with_human_labels": clips_with_labels,
        "per_role": per_role,
        "ready": clips_with_labels > 0 and compared > 0,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    if args.bootstrap_template:
        template = json.loads(args.template.read_text(encoding="utf-8"))
        bootstrapped = bootstrap_gold_from_labeled(template, args.audio_root)
        args.gold.parent.mkdir(parents=True, exist_ok=True)
        args.gold.write_text(json.dumps(bootstrapped, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[gold] bootstrapped -> {args.gold.relative_to(REPO_ROOT)}")
        print("[gold] İnsan annotator gold_role alanlarını düzeltmeli.")

    gold_path = args.gold if args.gold.is_file() else args.template
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    metrics = compute_metrics(gold, args.audio_root)
    out_path = LOGS_DIR / "speaker_labeling_baseline_metrics.json"
    payload = {
        "gold_source": str(gold_path.relative_to(REPO_ROOT)),
        "metrics": metrics,
    }
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if metrics["ready"]:
        print(f"[metrics] compared={metrics['compared_segments']} clips={metrics['clips_with_human_labels']}")
        for role, m in metrics["per_role"].items():
            print(f"  {role}: P={m['precision']:.2f} R={m['recall']:.2f} F1={m['f1']:.2f}")
    else:
        print(
            "[metrics] Henüz insan gold_role yok. "
            "Önce: python scripts/evaluate_speaker_gold.py --bootstrap-template"
        )
    print(f"[metrics] -> {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
