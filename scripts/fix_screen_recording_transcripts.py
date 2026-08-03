#!/usr/bin/env python3
"""Fix or flag broken CODAP screen-recording transcripts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcript_quality import (
    DEFAULT_AUDIO_ROOT,
    REPO_ROOT,
    analyze_audio,
    assess_transcript,
    clean_segments,
    filter_segments,
    make_clean_payload,
    make_no_speech_payload,
    write_transcript_bundle,
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fix silent/hallucinated screen-recording transcripts.")
    p.add_argument("students", nargs="*", help="Optional student subset")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    wanted = {s.lower() for s in args.students} if args.students else None

    for student_dir in sorted(args.audio_root.iterdir(), key=lambda p: p.name.lower()):
        if not student_dir.is_dir():
            continue
        student_id = student_dir.name
        if wanted and student_id.lower() not in wanted:
            continue

        wav = student_dir / f"{student_id}.wav"
        transcript_path = student_dir / f"{student_id}_transcript.json"
        if not wav.is_file() or not transcript_path.is_file():
            print(f"[skip] {student_id}: missing wav or transcript")
            continue

        audio = analyze_audio(wav)
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        assessment = assess_transcript(student_id, transcript, audio)

        if assessment.status == "no_speech":
            payload = make_no_speech_payload(
                student_id,
                transcript.get("source_audio", str(wav.relative_to(REPO_ROOT))),
                audio,
                model=transcript.get("model", "unknown"),
                language=transcript.get("language", "tr"),
                previous_segment_count=assessment.segment_count,
            )
            action = "flag_no_speech"
        else:
            cleaned, clean_stats = clean_segments(transcript.get("segments", []))
            removed = clean_stats["removed_total"]
            if removed == 0 and assessment.status == "ok":
                print(f"[ok] {student_id}: no changes needed")
                continue
            payload = make_clean_payload(transcript, cleaned, removed, audio, clean_stats)
            action = (
                f"cleaned_removed_{removed}"
                f"(silence={clean_stats['removed_silence_hallucination']},"
                f"burst={clean_stats['removed_burst_runs']},"
                f"chain={clean_stats['removed_chain_repetitions']},"
                f"invalid={clean_stats['removed_invalid_timestamp']},"
                f"ghost={clean_stats['removed_ghost_blocks']},"
                f"vacuum={clean_stats['removed_vacuum_fillers']})"
            )

        if args.dry_run:
            print(f"[dry-run] {student_id}: {action} -> status={payload.get('status')}")
            continue

        write_transcript_bundle(student_dir, payload)
        print(f"[fixed] {student_id}: {action} (segments={payload['segment_count']})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
