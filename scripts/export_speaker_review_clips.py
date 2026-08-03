#!/usr/bin/env python3
"""Export ffmpeg commands / clip list for low-confidence speaker segments."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcript_quality import DEFAULT_AUDIO_ROOT, REPO_ROOT, format_timestamp
from transcript_speaker_utils import labeled_transcript_path, load_json

LOGS_DIR = REPO_ROOT / "logs"
ACTIVE_STUDENTS = ("Amy", "Bruno", "Helena", "Marcus", "Shana")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Export review clip manifest for speaker QA.")
    p.add_argument("students", nargs="*", help="Student IDs")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--max-clips", type=int, default=40)
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    students = args.students or list(ACTIVE_STUDENTS)
    repo_root = REPO_ROOT.resolve()
    audio_root = args.audio_root.resolve()

    all_clips: list[dict] = []
    for student_id in students:
        student_dir = audio_root / student_id
        labeled_path = labeled_transcript_path(student_dir, student_id)
        audio_path = student_dir / f"{student_id}.wav"
        if not labeled_path.is_file():
            continue
        labeled = load_json(labeled_path)
        review = [s for s in labeled.get("segments") or [] if s.get("needs_review")]
        review.sort(key=lambda s: float(s.get("speaker_confidence", 0.0)))
        for seg in review[: args.max_clips]:
            start = max(0.0, float(seg["start"]) - 1.5)
            end = float(seg["end"]) + 1.5
            clip_id = f"{student_id}_{seg.get('id')}"
            out_wav = LOGS_DIR / "review_clips" / f"{clip_id}.wav"
            all_clips.append(
                {
                    "clip_id": clip_id,
                    "student_id": student_id,
                    "segment_id": seg.get("id"),
                    "start": seg.get("start"),
                    "end": seg.get("end"),
                    "start_hms": seg.get("start_hms") or format_timestamp(float(seg["start"])),
                    "text": seg.get("text"),
                    "speaker_role": seg.get("speaker_role"),
                    "speaker_confidence": seg.get("speaker_confidence"),
                    "review_reason": seg.get("review_reason"),
                    "audio_source": str(audio_path.resolve().relative_to(repo_root)),
                    "output_wav": str(out_wav.resolve().relative_to(repo_root)),
                    "ffmpeg": (
                        f"ffmpeg -y -ss {start:.2f} -to {end:.2f} "
                        f"-i {audio_path} -ac 1 -ar 16000 {out_wav}"
                    ),
                }
            )

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "clip_count": len(all_clips),
        "clips": all_clips,
    }
    out_path = LOGS_DIR / "speaker_review_clips_manifest.json"
    out_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[review] {len(all_clips)} clips -> {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
