#!/usr/bin/env python3
"""Extract frames from .webm videos that have missing or empty _frames/ directories.

Scans all student subdirectories under a given audio root, finds those whose
_frames/ folder is absent or empty, and extracts frames at 1 fps using OpenCV
(with ffmpeg fallback). Writes/updates a video_extraction_manifest.json per student.

Supported sessions:
    codap_21apr  ->  data_sources_2026/codap_arbor_21april_audio/
    codap_28apr  ->  data_sources_2026/codap_arbor_28april_audio/
    colab_05may  ->  data_sources_2026/colab_python_audio/

Usage:
    python scripts/extract_missing_frames.py
    python scripts/extract_missing_frames.py --session codap_21apr
    python scripts/extract_missing_frames.py --session codap_21apr --student Sheila Ulysses
    python scripts/extract_missing_frames.py --fps 0.5 --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]

SESSION_DIRS: dict[str, Path] = {
    "codap_21apr": REPO / "data_sources_2026" / "codap_arbor_21april_audio",
    "codap_28apr": REPO / "data_sources_2026" / "codap_arbor_28april_audio",
    "colab_05may": REPO / "data_sources_2026" / "colab_python_audio",
}

MANIFEST_SCHEMA = "video_extraction_manifest_v1"

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("extract_missing_frames")


def _find_webm(student_dir: Path) -> Path | None:
    candidates = list(student_dir.glob("*.webm"))
    if not candidates:
        return None
    return candidates[0]


def _frames_dir(student_dir: Path, student_id: str) -> Path:
    return student_dir / f"{student_id}_frames"


def _needs_extraction(frames_dir: Path) -> bool:
    if not frames_dir.exists():
        return True
    jpgs = list(frames_dir.glob("*.jpg")) + list(frames_dir.glob("*.jpeg"))
    return len(jpgs) == 0


def _extract_with_opencv(
    video_path: Path,
    out_dir: Path,
    fps: float,
    dry_run: bool,
) -> list[dict[str, Any]]:
    try:
        import cv2  # type: ignore
    except ImportError:
        return []

    if dry_run:
        log.info("  [dry-run] would extract via OpenCV: %s", video_path.name)
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(str(video_path))
    native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    interval_frames = max(1, int(round(native_fps / fps)))

    frames_meta: list[dict[str, Any]] = []
    frame_idx = 0
    saved = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % interval_frames == 0:
            ts_ms = int((frame_idx / native_fps) * 1000)
            filename = f"frame_{saved + 1:04d}.jpg"
            out_path = out_dir / filename
            cv2.imwrite(str(out_path), frame)
            frames_meta.append({"filename": filename, "source_timestamp_ms": ts_ms})
            saved += 1
        frame_idx += 1

    cap.release()
    log.info("  OpenCV: extracted %d frames -> %s", saved, out_dir)
    return frames_meta


def _extract_with_ffmpeg(
    video_path: Path,
    out_dir: Path,
    fps: float,
    dry_run: bool,
) -> list[dict[str, Any]]:
    if dry_run:
        log.info("  [dry-run] would extract via ffmpeg: %s", video_path.name)
        return []

    out_dir.mkdir(parents=True, exist_ok=True)
    pattern = str(out_dir / "frame_%04d.jpg")
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-q:v", "2",
        pattern,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error("  ffmpeg failed:\n%s", result.stderr[-500:])
        return []

    frames_meta: list[dict[str, Any]] = []
    for i, jpg in enumerate(sorted(out_dir.glob("frame_*.jpg"))):
        ts_ms = int((i / fps) * 1000)
        frames_meta.append({"filename": jpg.name, "source_timestamp_ms": ts_ms})

    log.info("  ffmpeg: extracted %d frames -> %s", len(frames_meta), out_dir)
    return frames_meta


def _write_manifest(
    student_dir: Path,
    student_id: str,
    session: str,
    video_path: Path,
    frames_dir: Path,
    frames_meta: list[dict[str, Any]],
) -> None:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"

    existing: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text())
        except Exception:
            existing = {}

    manifest = {
        **existing,
        "schema_version": MANIFEST_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "student_id": student_id,
        "session": session,
        "path_resolution": {
            **(existing.get("path_resolution") or {}),
            "source_video": str(video_path.relative_to(REPO)),
            "output_frames_dir": str(frames_dir.relative_to(REPO)),
        },
        "frames_extracted": len(frames_meta),
        "frames": frames_meta,
    }

    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    log.info("  manifest written: %s", manifest_path.relative_to(REPO))


def process_student(
    student_dir: Path,
    student_id: str,
    session: str,
    fps: float,
    dry_run: bool,
    force: bool,
) -> dict[str, Any]:
    webm = _find_webm(student_dir)
    if webm is None:
        log.warning("%s: no .webm file found in %s", student_id, student_dir)
        return {"student_id": student_id, "status": "no_webm"}

    frames_dir = _frames_dir(student_dir, student_id)

    if not force and not _needs_extraction(frames_dir):
        count = len(list(frames_dir.glob("*.jpg")))
        log.info("%s: frames already present (%d jpgs), skipping", student_id, count)
        return {"student_id": student_id, "status": "already_extracted", "frame_count": count}

    log.info("%s: extracting from %s", student_id, webm.name)

    frames_meta = _extract_with_opencv(webm, frames_dir, fps, dry_run)
    if not frames_meta and not dry_run:
        frames_meta = _extract_with_ffmpeg(webm, frames_dir, fps, dry_run)

    if not dry_run:
        _write_manifest(student_dir, student_id, session, webm, frames_dir, frames_meta)

    return {
        "student_id": student_id,
        "status": "extracted" if not dry_run else "dry_run",
        "frame_count": len(frames_meta),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract missing frames from .webm videos")
    parser.add_argument(
        "--session",
        choices=list(SESSION_DIRS.keys()),
        help="Session to process (default: all sessions)",
    )
    parser.add_argument(
        "--student",
        nargs="+",
        metavar="NAME",
        help="Student name(s) to process (default: all with missing frames)",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=1.0,
        help="Extraction rate in frames per second (default: 1.0)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-extract even if _frames/ already has files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be extracted without writing files",
    )
    args = parser.parse_args()

    sessions = {args.session: SESSION_DIRS[args.session]} if args.session else SESSION_DIRS

    results: list[dict[str, Any]] = []

    for session_key, audio_root in sessions.items():
        if not audio_root.exists():
            log.warning("Session directory not found, skipping: %s", audio_root)
            continue

        student_dirs = sorted(
            d for d in audio_root.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

        for student_dir in student_dirs:
            student_id = student_dir.name
            if args.student and student_id not in args.student:
                continue

            result = process_student(
                student_dir, student_id, session_key,
                fps=args.fps, dry_run=args.dry_run, force=args.force,
            )
            results.append(result)

    extracted = [r for r in results if r.get("status") == "extracted"]
    skipped = [r for r in results if r.get("status") == "already_extracted"]
    no_webm = [r for r in results if r.get("status") == "no_webm"]

    print(f"\nDone. extracted={len(extracted)}  skipped={len(skipped)}  no_webm={len(no_webm)}")
    if no_webm:
        print("No .webm found for:", [r["student_id"] for r in no_webm])


if __name__ == "__main__":
    main()
