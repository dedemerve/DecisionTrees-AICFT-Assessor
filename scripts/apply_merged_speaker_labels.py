#!/usr/bin/env python3
"""Apply hybrid diarization speaker labels → separate labeled transcript files."""

from __future__ import annotations

import argparse
import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speaker_merge import (
    build_role_mapping,
    count_needs_review,
    get_hybrid_timeline,
    load_merge_rules,
    merge_transcript_segments,
    summarize_roles,
)
from transcript_quality import DEFAULT_AUDIO_ROOT, REPO_ROOT
from transcript_speaker_utils import (
    ham_transcript_path,
    labeled_transcript_path,
    strip_transcript_to_ham,
    write_json,
)

MERGE_METHOD = "merged_transcript_hybrid_diarization_v2"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge transcript text with hybrid diarization roles.")
    p.add_argument("students", nargs="*", help="Student IDs (default: active cohort)")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--rules", type=Path, default=None, help="speaker_merge_rules.json path")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--restore-ham",
        action="store_true",
        help="Rewrite *_transcript.json as mlx-only (strip speaker fields)",
    )
    return p.parse_args(argv)


def process_student(
    student_dir: Path,
    *,
    dry_run: bool,
    rules_path: Path | None,
    restore_ham: bool,
    audio_root: Path,
) -> dict | None:
    student_id = student_dir.name
    student_dir = student_dir.resolve()
    audio_root = audio_root.resolve()
    transcript_path = ham_transcript_path(student_dir, student_id)
    labeled_path = labeled_transcript_path(student_dir, student_id)
    hybrid_path = student_dir / f"{student_id}_hybrid_diarization.json"

    if transcript_path.is_file():
        raw = json.loads(transcript_path.read_text(encoding="utf-8"))
    elif labeled_path.is_file():
        raw = json.loads(labeled_path.read_text(encoding="utf-8"))
    else:
        return None
    ham = strip_transcript_to_ham(raw)

    if ham.get("status") == "no_speech" or not ham.get("segments"):
        return {"student_id": student_id, "skipped": "no_speech"}

    if not hybrid_path.is_file():
        return {"student_id": student_id, "skipped": "no_hybrid_diarization"}

    hybrid = json.loads(hybrid_path.read_text(encoding="utf-8"))
    if hybrid.get("status") != "ok":
        return {"student_id": student_id, "skipped": f"hybrid_{hybrid.get('status')}"}

    rules = load_merge_rules(rules_path)
    mapping = build_role_mapping(hybrid, focal_pt_student_id=student_id)
    before = summarize_roles(ham["segments"])
    merged = merge_transcript_segments(ham["segments"], get_hybrid_timeline(hybrid), mapping, rules)
    after = summarize_roles(merged)
    review_count = count_needs_review(merged)

    if dry_run:
        return {
            "student_id": student_id,
            "before": before,
            "after": after,
            "needs_review": review_count,
            "teacher_speaker": mapping.teacher_speaker,
            "focal_speaker": mapping.focal_speaker,
        }

    labeled = copy.deepcopy(ham)
    labeled["segments"] = merged
    labeled["speaker_labeling"] = {
        "method": MERGE_METHOD,
        "rules_version": rules.version,
        "labeled_at": datetime.now(timezone.utc).isoformat(),
        "source_transcript": str(transcript_path.relative_to(REPO_ROOT.resolve())),
        "source_diarization": str(hybrid_path.relative_to(REPO_ROOT.resolve())),
        "output_labeled": str(labeled_path.relative_to(REPO_ROOT.resolve())),
        "focal_pt_student_id": student_id,
        "focal_pt_note": (
            "PT öğrencisi kimliği kayıt metadata'sından gelir (klasör adı = ekran kaydı sahibi). "
            "Ses timbresi ile isim eşleştirilmez; focal speaker kümesi bu öğrenciye atanır."
        ),
        "teacher_speaker": mapping.teacher_speaker,
        "focal_student_speaker": mapping.focal_speaker,
        "role_counts": after,
        "needs_review_count": review_count,
    }
    write_json(labeled_path, labeled)

    if restore_ham or raw != ham:
        write_json(transcript_path, ham)

    return {
        "student_id": student_id,
        "before": before,
        "after": after,
        "needs_review": review_count,
        "ham_path": str(transcript_path.relative_to(REPO_ROOT.resolve())),
        "labeled_path": str(labeled_path.relative_to(REPO_ROOT.resolve())),
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    audio_root = args.audio_root.resolve()
    if args.students:
        dirs = [audio_root / s for s in args.students]
    else:
        dirs = sorted([d for d in audio_root.iterdir() if d.is_dir()], key=lambda p: p.name.lower())

    for student_dir in dirs:
        result = process_student(
            student_dir,
            dry_run=args.dry_run,
            rules_path=args.rules,
            restore_ham=args.restore_ham or True,
            audio_root=audio_root,
        )
        if not result:
            continue
        if "skipped" in result:
            print(f"[skip] {result['student_id']}: {result['skipped']}")
        else:
            b = result["before"]
            a = result["after"]
            print(
                f"[{'dry' if args.dry_run else 'ok'}] {result['student_id']}: "
                f"unknown {b.get('unknown', 0)} -> {a.get('unknown', 0)} | "
                f"teacher {a.get('teacher', 0)} student {a.get('student', 0)} "
                f"classmate {a.get('classmate', 0)} | review {result.get('needs_review', 0)}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
