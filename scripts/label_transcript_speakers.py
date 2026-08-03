#!/usr/bin/env python3
"""Label transcript segments with teacher / student / classmate roles."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speaker_role import label_segments_text
from transcript_quality import DEFAULT_AUDIO_ROOT

def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Label transcript segments with speaker roles.")
    p.add_argument("students", nargs="*", help="Student folders to process")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--method", choices=("text", "auto"), default="text")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    dirs = sorted(
        [d for d in args.audio_root.iterdir() if d.is_dir()],
        key=lambda p: p.name.lower(),
    )
    if args.students:
        wanted = {s.lower() for s in args.students}
        dirs = [d for d in dirs if d.name.lower() in wanted]

    for student_dir in dirs:
        student_id = student_dir.name
        transcript_path = student_dir / f"{student_id}_transcript.json"
        if not transcript_path.exists():
            continue
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        if transcript.get("status") == "no_speech" or not transcript.get("segments"):
            print(f"[skip] {student_id}: no_speech")
            continue

        labeled = label_segments_text(transcript["segments"])
        role_counts = {}
        for seg in labeled:
            role_counts[seg["speaker_role"]] = role_counts.get(seg["speaker_role"], 0) + 1

        transcript["segments"] = labeled
        transcript["speaker_labeling"] = {
            "method": "text_lexicon_v1",
            "labeled_at": datetime.now(timezone.utc).isoformat(),
            "role_counts": role_counts,
            "notes": (
                "Text-only labels are approximate. For reliable teacher/student separation, "
                "run pyannote diarization and merge with merge_diarization_labels()."
            ),
        }
        transcript_path.write_text(json.dumps(transcript, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[labeled] {student_id}: {role_counts}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
