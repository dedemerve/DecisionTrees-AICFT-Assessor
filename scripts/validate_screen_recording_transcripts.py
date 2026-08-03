#!/usr/bin/env python3
"""Validate CODAP screen-recording transcripts against audio quality heuristics."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcript_quality import (
    DEFAULT_AUDIO_ROOT,
    REPO_ROOT,
    analyze_audio,
    assess_transcript,
)

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Validate screen-recording transcripts.")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--report", type=Path, help="Write JSON report to this path")
    p.add_argument("--fail-on-issues", action="store_true", help="Exit 1 if any transcript is not ok")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    audio_root = args.audio_root.resolve()
    rows = []
    has_issues = False

    for student_dir in sorted(audio_root.iterdir(), key=lambda p: p.name.lower()):
        if not student_dir.is_dir():
            continue
        student_id = student_dir.name
        wav = student_dir / f"{student_id}.wav"
        transcript_path = student_dir / f"{student_id}_transcript.json"
        labeled_path = student_dir / f"{student_id}_transcript_labeled.json"
        if not transcript_path.is_file() and labeled_path.is_file():
            transcript_path = labeled_path
        extraction_error = student_dir / f"{student_id}_extraction_error.json"
        if extraction_error.is_file() and not wav.is_file():
            err = json.loads(extraction_error.read_text(encoding="utf-8"))
            rows.append(
                {
                    "student_id": student_id,
                    "status": "extraction_failed",
                    "issues": ["corrupt_source_video"],
                    "notes": [err.get("detail") or err.get("error", "")],
                }
            )
            has_issues = True
            continue
        if not wav.is_file() or not transcript_path.is_file():
            rows.append({"student_id": student_id, "status": "missing", "issues": ["missing_files"]})
            has_issues = True
            continue

        audio = analyze_audio(wav)
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        assessment = assess_transcript(student_id, transcript, audio)
        if assessment.status in {"needs_review", "missing"}:
            has_issues = True
        rows.append(
            {
                "student_id": assessment.student_id,
                "status": assessment.status,
                "segment_count": assessment.segment_count,
                "duration_minutes": round(assessment.duration_seconds / 60, 1),
                "segments_per_minute": assessment.segments_per_minute,
                "hallucination_fraction": assessment.hallucination_fraction,
                "speech_fraction": round(assessment.audio.speech_fraction, 4),
                "mean_volume_db": assessment.audio.mean_volume_db,
                "issues": assessment.issues,
                "notes": assessment.notes,
            }
        )

    report = {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "audio_root": str(audio_root.relative_to(REPO_ROOT)),
        "summary": {
            "total": len(rows),
            "ok": sum(1 for r in rows if r["status"] == "ok"),
            "no_speech": sum(1 for r in rows if r["status"] == "no_speech"),
            "needs_review": sum(1 for r in rows if r["status"] == "needs_review"),
            "missing": sum(1 for r in rows if r["status"] == "missing"),
            "extraction_failed": sum(1 for r in rows if r["status"] == "extraction_failed"),
        },
        "students": rows,
    }

    print(f"{'Student':<10} {'Status':<12} {'Segs':>5} {'Seg/Min':>7} {'Hall%':>6} {'Speech%':>8}")
    for row in rows:
        hall_pct = f"{row.get('hallucination_fraction', 0) * 100:.0f}" if row.get("hallucination_fraction") is not None else "-"
        speech_pct = f"{row.get('speech_fraction', 0) * 100:.1f}" if row.get("speech_fraction") is not None else "-"
        print(
            f"{row['student_id']:<10} {row['status']:<12} "
            f"{row.get('segment_count', '-'):>5} "
            f"{row.get('segments_per_minute', '-'):>7} "
            f"{hall_pct:>6} {speech_pct:>8}"
        )

    print(
        f"\nSummary: ok={report['summary']['ok']} "
        f"no_speech={report['summary']['no_speech']} "
        f"needs_review={report['summary']['needs_review']} "
        f"missing={report['summary']['missing']}"
    )

    report_path = args.report or audio_root / "transcript_validation_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Report → {report_path.relative_to(REPO_ROOT)}")

    if args.fail_on_issues and has_issues:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
