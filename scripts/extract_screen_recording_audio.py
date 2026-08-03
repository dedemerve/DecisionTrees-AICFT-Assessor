#!/usr/bin/env python3
"""Extract audio and video tracks from student screen recording .webm files."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = (
    REPO_ROOT
    / "data_sources_2026"
    / "21 April CODAP Arbor Screen Recordings"
)
DEFAULT_OUTPUT = REPO_ROOT / "data_sources_2026" / "codap_arbor_21april_audio"


def probe_duration_seconds(path: Path) -> float | None:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(path),
    ]
    try:
        out = subprocess.check_output(cmd, text=True).strip()
        return round(float(out), 2)
    except (subprocess.CalledProcessError, ValueError):
        return None


def _link_source_video(video: Path, student_dir: Path) -> Path:
    """Symlink original .webm into the student folder (no duplicate copy)."""
    link = student_dir / video.name
    if link.exists() or link.is_symlink():
        return link
    link.symlink_to(video.resolve())
    return link


def extract_one(video: Path, out_dir: Path) -> dict:
    student_id = video.stem
    student_dir = out_dir / student_id
    student_dir.mkdir(parents=True, exist_ok=True)

    wav_path = student_dir / f"{student_id}.wav"
    m4a_path = student_dir / f"{student_id}.m4a"
    video_path = student_dir / f"{student_id}.video.webm"
    source_link = _link_source_video(video, student_dir)

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(wav_path),
        ],
        check=True,
        capture_output=True,
    )

    # Encode m4a from wav so duration matches the full recording.
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(wav_path),
            "-acodec",
            "aac",
            "-b:a",
            "128k",
            str(m4a_path),
        ],
        check=True,
        capture_output=True,
    )

    # Video-only copy (no re-encode) for vision / replay without duplicating audio.
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-an",
            "-c:v",
            "copy",
            str(video_path),
        ],
        check=True,
        capture_output=True,
    )

    wav_dur = probe_duration_seconds(wav_path)
    return {
        "student_id": student_id,
        "source_video": video.name,
        "source_link": str(source_link.relative_to(REPO_ROOT)),
        "duration_seconds": wav_dur,
        "wav": str(wav_path.relative_to(REPO_ROOT)),
        "m4a": str(m4a_path.relative_to(REPO_ROOT)),
        "video": str(video_path.relative_to(REPO_ROOT)),
        "wav_bytes": wav_path.stat().st_size,
        "m4a_bytes": m4a_path.stat().st_size,
        "video_bytes": video_path.stat().st_size,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Extract audio from CODAP screen recordings.")
    p.add_argument("students", nargs="*", help="Optional student name(s); default = all in folder")
    p.add_argument(
        "--from",
        dest="from_student",
        metavar="NAME",
        help="Process this student and all later names alphabetically (e.g. Amy)",
    )
    p.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return p.parse_args(argv)


def select_videos(in_dir: Path, args: argparse.Namespace) -> list[Path]:
    all_videos = sorted(in_dir.glob("*.webm"), key=lambda p: p.stem.lower())
    if args.students:
        wanted = {s.lower() for s in args.students}
        videos = [v for v in all_videos if v.stem.lower() in wanted]
    elif args.from_student:
        start = args.from_student.lower()
        videos = [v for v in all_videos if v.stem.lower() >= start]
    else:
        videos = all_videos
    return videos


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    in_dir = args.input.resolve()
    out_dir = args.output.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    videos = select_videos(in_dir, args)
    if not videos:
        print(f"No matching .webm files in {in_dir}", file=sys.stderr)
        return 1

    manifest: dict = {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(in_dir.relative_to(REPO_ROOT)),
        "output_dir": str(out_dir.relative_to(REPO_ROOT)),
        "layout": "one subfolder per student: {Student}/{Student}.wav, .m4a, .video.webm, symlink .webm",
        "format": {
            "wav": "pcm_s16le, 16 kHz, mono (STT-ready)",
            "m4a": "aac 128 kbps from wav (full duration)",
            "video": "vp9 video-only webm (stream copy, no audio)",
        },
        "recordings": [],
        "errors": [],
    }

    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] {video.name} …", flush=True)
        try:
            entry = extract_one(video, out_dir)
        except subprocess.CalledProcessError as exc:
            err = {
                "student_id": video.stem,
                "source_video": video.name,
                "error": f"ffmpeg failed (exit {exc.returncode})",
                "stderr": (exc.stderr or b"").decode("utf-8", errors="replace")[-500:],
            }
            manifest["errors"].append(err)
            print(f"  ! FAILED: {err['error']}", flush=True)
            continue
        except OSError as exc:
            err = {"student_id": video.stem, "source_video": video.name, "error": str(exc)}
            manifest["errors"].append(err)
            print(f"  ! FAILED: {exc}", flush=True)
            continue
        manifest["recordings"].append(entry)
        mins = (entry["duration_seconds"] or 0) / 60
        print(
            f"  → {entry['wav']} ({entry['duration_seconds']}s / {mins:.1f} min)",
            flush=True,
        )

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {manifest_path.relative_to(REPO_ROOT)} "
        f"({len(manifest['recordings'])} ok, {len(manifest['errors'])} failed)"
    )
    return 0 if not manifest["errors"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
