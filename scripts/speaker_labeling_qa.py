#!/usr/bin/env python3
"""QA report for speaker-labeled transcripts."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speaker_merge import get_hybrid_timeline
from transcript_quality import DEFAULT_AUDIO_ROOT, REPO_ROOT, format_timestamp
from transcript_speaker_utils import labeled_transcript_path, load_json

LOGS_DIR = REPO_ROOT / "logs"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Speaker labeling QA report.")
    p.add_argument("students", nargs="*", help="Student IDs (default: active cohort)")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--logs-dir", type=Path, default=LOGS_DIR)
    return p.parse_args(argv)


def confidence_histogram(segments: list[dict]) -> dict[str, int]:
    buckets = {"0.0-0.3": 0, "0.3-0.5": 0, "0.5-0.7": 0, "0.7-0.9": 0, "0.9-1.0": 0}
    for seg in segments:
        c = float(seg.get("speaker_confidence", 0.0))
        if c < 0.3:
            buckets["0.0-0.3"] += 1
        elif c < 0.5:
            buckets["0.3-0.5"] += 1
        elif c < 0.7:
            buckets["0.5-0.7"] += 1
        elif c < 0.9:
            buckets["0.7-0.9"] += 1
        else:
            buckets["0.9-1.0"] += 1
    return buckets


def find_diarization_gaps(
    transcript_segments: list[dict],
    hybrid_segments: list[dict],
    *,
    gap_threshold: float = 25.0,
) -> list[dict]:
    """Intervals where many transcript segments lack diarization overlap."""
    if not transcript_segments or not hybrid_segments:
        return []

    hybrid_sorted = sorted(hybrid_segments, key=lambda s: float(s["start"]))
    gaps: list[dict] = []
    run_start: float | None = None
    run_count = 0

    def has_overlap(start: float, end: float) -> bool:
        for h in hybrid_sorted:
            if float(h["end"]) < start:
                continue
            if float(h["start"]) > end:
                break
            if min(end, float(h["end"])) - max(start, float(h["start"])) > 0:
                return True
        return False

    for seg in transcript_segments:
        start, end = float(seg["start"]), float(seg["end"])
        method = str(seg.get("speaker_method", ""))
        unmapped = method in {"unmapped", "diarization_gap_interpolate", "diarization_tail_interpolate"}
        if unmapped or not has_overlap(start, end):
            if run_start is None:
                run_start = start
            run_count += 1
        elif run_start is not None and run_count > 0:
            run_end = float(seg["start"])
            if run_end - run_start >= gap_threshold:
                gaps.append(
                    {
                        "start": round(run_start, 2),
                        "end": round(run_end, 2),
                        "start_hms": format_timestamp(run_start),
                        "end_hms": format_timestamp(run_end),
                        "duration_seconds": round(run_end - run_start, 2),
                        "unmapped_segments": run_count,
                    }
                )
            run_start = None
            run_count = 0

    if run_start is not None and transcript_segments:
        run_end = float(transcript_segments[-1]["end"])
        if run_end - run_start >= gap_threshold:
            gaps.append(
                {
                    "start": round(run_start, 2),
                    "end": round(run_end, 2),
                    "start_hms": format_timestamp(run_start),
                    "end_hms": format_timestamp(run_end),
                    "duration_seconds": round(run_end - run_start, 2),
                    "unmapped_segments": run_count,
                }
            )
    return gaps


def find_role_flips(segments: list[dict], *, max_gap: float = 2.0) -> list[dict]:
    flips: list[dict] = []
    for i in range(1, len(segments) - 1):
        prev_s = segments[i - 1]
        cur = segments[i]
        next_s = segments[i + 1]
        pr = prev_s.get("speaker_role")
        cr = cur.get("speaker_role")
        nr = next_s.get("speaker_role")
        if pr != nr or cr == pr:
            continue
        gap_prev = float(cur["start"]) - float(prev_s["end"])
        gap_next = float(next_s["start"]) - float(cur["end"])
        if gap_prev <= max_gap and gap_next <= max_gap:
            flips.append(
                {
                    "segment_id": cur.get("id"),
                    "start": cur.get("start"),
                    "end": cur.get("end"),
                    "text": str(cur.get("text", ""))[:120],
                    "pattern": f"{pr}->{cr}->{nr}",
                    "speaker_method": cur.get("speaker_method"),
                }
            )
    return flips


def analyze_student(student_dir: Path) -> dict | None:
    student_id = student_dir.name
    labeled_path = labeled_transcript_path(student_dir, student_id)
    hybrid_path = student_dir / f"{student_id}_hybrid_diarization.json"

    if not labeled_path.is_file():
        return {"student_id": student_id, "status": "missing_labeled_transcript"}

    labeled = load_json(labeled_path)
    segments = labeled.get("segments") or []
    total = len(segments)
    role_counts = Counter(str(s.get("speaker_role", "unknown")) for s in segments)
    method_counts = Counter(str(s.get("speaker_method", "none")) for s in segments)
    review_segments = [s for s in segments if s.get("needs_review")]
    unknown_rate = role_counts.get("unknown", 0) / total if total else 0.0

    hybrid_segments: list[dict] = []
    if hybrid_path.is_file():
        hybrid = load_json(hybrid_path)
        hybrid_segments = get_hybrid_timeline(hybrid)

    report = {
        "student_id": student_id,
        "status": "ok",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "segment_count": total,
        "role_counts": dict(role_counts),
        "unknown_rate": round(unknown_rate, 4),
        "speaker_method_counts": dict(method_counts.most_common(20)),
        "confidence_histogram": confidence_histogram(segments),
        "needs_review_count": len(review_segments),
        "needs_review_rate": round(len(review_segments) / total, 4) if total else 0.0,
        "diarization_coverage_gaps": find_diarization_gaps(segments, hybrid_segments),
        "suspicious_role_flips": find_role_flips(segments)[:50],
        "labeling_meta": labeled.get("speaker_labeling", {}),
        "sample_review_segments": [
            {
                "id": s.get("id"),
                "start_hms": s.get("start_hms"),
                "text": str(s.get("text", ""))[:100],
                "speaker_role": s.get("speaker_role"),
                "speaker_confidence": s.get("speaker_confidence"),
                "review_reason": s.get("review_reason"),
            }
            for s in review_segments[:25]
        ],
    }
    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.logs_dir.mkdir(parents=True, exist_ok=True)

    if args.students:
        dirs = [args.audio_root / s for s in args.students]
    else:
        dirs = sorted([d for d in args.audio_root.iterdir() if d.is_dir()], key=lambda p: p.name.lower())

    cohort_rows: list[dict] = []
    for student_dir in dirs:
        report = analyze_student(student_dir)
        if not report:
            continue
        out_path = args.logs_dir / f"speaker_labeling_qa_{report['student_id']}.json"
        out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        cohort_rows.append(report)
        if report.get("status") == "ok":
            print(
                f"[qa] {report['student_id']}: unknown_rate={report['unknown_rate']:.2%} "
                f"review={report['needs_review_count']} gaps={len(report['diarization_coverage_gaps'])} "
                f"flips={len(report['suspicious_role_flips'])}"
            )
        else:
            print(f"[qa] {report['student_id']}: {report['status']}")

    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "students": cohort_rows,
        "cohort_summary": {
            "count": len(cohort_rows),
            "avg_unknown_rate": round(
                sum(r.get("unknown_rate", 0.0) for r in cohort_rows if r.get("status") == "ok")
                / max(1, sum(1 for r in cohort_rows if r.get("status") == "ok")),
                4,
            ),
            "total_needs_review": sum(r.get("needs_review_count", 0) for r in cohort_rows),
        },
    }
    summary_path = args.logs_dir / "speaker_labeling_qa_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[qa] summary -> {summary_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
