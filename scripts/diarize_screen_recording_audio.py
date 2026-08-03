#!/usr/bin/env python3
"""Speaker diarization for screen recording audio (pyannote).

Requires:
  pip install pyannote.audio
  export HF_TOKEN=...   # HuggingFace token with pyannote model access

Accept model terms at:
  https://huggingface.co/pyannote/speaker-diarization-3.1
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speaker_role import (
    identify_focal_student_cluster,
    identify_teacher_cluster,
    merge_diarization_labels,
)
from transcript_quality import DEFAULT_AUDIO_ROOT


def run_pyannote_diarization(audio_path: Path, hf_token: str) -> list[dict]:
    from pyannote.audio import Pipeline

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )
    diarization = pipeline(str(audio_path))
    turns: list[dict] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        turns.append(
            {
                "start": round(float(turn.start), 3),
                "end": round(float(turn.end), 3),
                "speaker": speaker,
            }
        )
    return turns


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Diarize screen recording audio and label transcript roles.")
    p.add_argument("students", nargs="*", help="Student folders")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--hf-token", default=os.environ.get("HF_TOKEN"))
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if not args.hf_token:
        print("HF_TOKEN required for pyannote diarization.", file=sys.stderr)
        return 1

    dirs = sorted([d for d in args.audio_root.iterdir() if d.is_dir()], key=lambda p: p.name.lower())
    if args.students:
        wanted = {s.lower() for s in args.students}
        dirs = [d for d in dirs if d.name.lower() in wanted]

    for student_dir in dirs:
        student_id = student_dir.name
        wav = student_dir / f"{student_id}.wav"
        m4a = student_dir / f"{student_id}.m4a"
        audio_path = wav if wav.exists() else m4a
        transcript_path = student_dir / f"{student_id}_transcript.json"
        if not audio_path.exists() or not transcript_path.exists():
            continue

        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        if transcript.get("status") == "no_speech" or not transcript.get("segments"):
            print(f"[skip] {student_id}: no_speech")
            continue

        print(f"[diarize] {student_id} ...")
        turns = run_pyannote_diarization(audio_path, args.hf_token)
        diar_path = student_dir / f"{student_id}_diarization.json"
        diar_path.write_text(json.dumps({"turns": turns}, indent=2) + "\n", encoding="utf-8")

        teacher = identify_teacher_cluster(turns, transcript["segments"])
        focal = identify_focal_student_cluster(turns, transcript["segments"], teacher_speaker=teacher)
        labeled = merge_diarization_labels(
            transcript["segments"],
            turns,
            teacher_speaker=teacher,
            focal_student_speaker=focal or "__none__",
        )
        role_counts: dict[str, int] = {}
        for seg in labeled:
            role_counts[seg["speaker_role"]] = role_counts.get(seg["speaker_role"], 0) + 1

        transcript["segments"] = labeled
        transcript["speaker_labeling"] = {
            "method": "pyannote_diarization_3.1",
            "labeled_at": datetime.now(timezone.utc).isoformat(),
            "teacher_speaker": teacher,
            "focal_student_speaker": focal,
            "role_counts": role_counts,
            "diarization_path": str(diar_path.relative_to(Path.cwd())),
        }
        transcript_path.write_text(json.dumps(transcript, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"[done] {student_id}: teacher={teacher} focal={focal} {role_counts}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
