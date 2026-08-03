#!/usr/bin/env python3
"""Audit no_speech cohort students — ffprobe + RMS check."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcript_quality import DEFAULT_AUDIO_ROOT, REPO_ROOT, analyze_audio, ffprobe_duration

LOGS_DIR = REPO_ROOT / "logs"
NO_SPEECH_STUDENTS = ("Iris", "Irma", "Isabel", "Marco", "Nadia", "Sheila", "Ulysses", "Zara")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit silent / no_speech audio files.")
    p.add_argument("students", nargs="*", help="Student IDs (default: 8 no_speech cohort)")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    return p.parse_args(argv)


def ffprobe_streams(audio_path: Path) -> list[dict]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=index,codec_type,channels,sample_rate,duration",
        "-of",
        "json",
        str(audio_path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        payload = json.loads(proc.stdout)
        return payload.get("streams") or []
    except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
        return []


def rms_speech_fraction(audio_path: Path) -> dict:
    try:
        import librosa

        y, sr = librosa.load(str(audio_path), sr=16000, mono=True)
        if len(y) == 0:
            return {"rms_max": 0.0, "speech_fraction": 0.0, "duration": 0.0}
        frame = 2048
        hop = 512
        rms = librosa.feature.rms(y=y, frame_length=frame, hop_length=hop)[0]
        threshold = 0.004
        speech_fraction = float(np.mean(rms > threshold))
        return {
            "rms_max": round(float(np.max(rms)), 5),
            "speech_fraction": round(speech_fraction, 4),
            "duration": round(len(y) / sr, 2),
        }
    except Exception as exc:
        return {"error": str(exc)}


def audit_student(student_dir: Path) -> dict:
    student_id = student_dir.name
    audio_path = student_dir / f"{student_id}.wav"
    transcript_path = student_dir / f"{student_id}_transcript.json"
    hybrid_path = student_dir / f"{student_id}_hybrid_diarization.json"

    row: dict = {
        "student_id": student_id,
        "audio_exists": audio_path.is_file(),
        "transcript_exists": transcript_path.is_file(),
        "hybrid_exists": hybrid_path.is_file(),
    }

    if audio_path.is_file():
        row["ffprobe_streams"] = ffprobe_streams(audio_path)
        row["duration_seconds"] = ffprobe_duration(audio_path)
        audio_analysis = analyze_audio(audio_path)
        row["audio_analysis"] = {
            "duration_seconds": audio_analysis.duration_seconds,
            "speech_fraction": audio_analysis.speech_fraction,
            "silence_fraction": audio_analysis.silence_fraction,
            "mean_volume_db": audio_analysis.mean_volume_db,
        }
        row["rms"] = rms_speech_fraction(audio_path)
        speech_frac = max(
            float(audio_analysis.speech_fraction),
            float(row["rms"].get("speech_fraction", 0.0)),
        )
        if speech_frac >= 0.02:
            row["recommendation"] = "retry_transcription_and_diarization"
        elif speech_frac >= 0.005:
            row["recommendation"] = "check_audio_gain_or_wrong_track"
        else:
            row["recommendation"] = "likely_true_silence_or_empty_track"

    if transcript_path.is_file():
        transcript = json.loads(transcript_path.read_text(encoding="utf-8"))
        row["transcript_status"] = transcript.get("status", "ok")
        row["transcript_segments"] = len(transcript.get("segments") or [])

    if hybrid_path.is_file():
        hybrid = json.loads(hybrid_path.read_text(encoding="utf-8"))
        row["hybrid_status"] = hybrid.get("status")

    return row


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    students = args.students or list(NO_SPEECH_STUDENTS)

    rows = []
    for student_id in students:
        row = audit_student(args.audio_root / student_id)
        rows.append(row)
        rec = row.get("recommendation", "n/a")
        sf = row.get("rms", {}).get("speech_fraction", "?")
        print(f"[audit] {student_id}: speech_fraction={sf} -> {rec}")

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "students": rows,
    }
    out_path = LOGS_DIR / "no_speech_audio_audit.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[audit] -> {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
