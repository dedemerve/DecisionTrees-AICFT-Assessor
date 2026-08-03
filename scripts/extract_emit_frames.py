#!/usr/bin/env python3
"""Extract targeted frames at emit_tree_data timestamps using ffmpeg.

For every emit_tree_data event where no manifest frame is within CLOSE_THRESHOLD
seconds, extract a frame from the video at (emit_time + FRAME_OFFSET_S) and add
it to the student's frames directory and manifest.

These frames represent the exact moments a student submitted a decision tree —
the highest-value frames for LO3 rubric assessment.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for p in (str(SCRIPTS_DIR), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from codap_alignment import estimate_video_start_utc, meaningful_event_timestamps_s
from codap_log_window import load_log_dataframe
from multimodal_cognitive_assessor import DEFAULT_AUDIO_ROOT

LOGGER = logging.getLogger("extract_emit_frames")

CLOSE_THRESHOLD_S = 15.0   # this close to a manifest frame = already covered
FRAME_OFFSET_S    = 3.0    # extract this many seconds AFTER the emit event
JPEG_QUALITY      = 88

VIDEO_ROOTS = {
    "2026-04-21": REPO_ROOT / "data_sources_2026" / "21 April CODAP Arbor Screen Recordings",
    "2026-04-28": REPO_ROOT / "data_sources_2026" / "28 April CODAP Arbor Screen Recordings",
}
LOG_CSVS = {
    "2026-04-21": REPO_ROOT / "data_sources_2026" / "All Documents" / "21 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv",
    "2026-04-28": REPO_ROOT / "data_sources_2026" / "All Documents" / "28 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv",
}


def find_video(student_id: str, video_root: Path) -> Path | None:
    for ext in (".webm", ".mp4", ".mkv", ".mov", ".m4v", ".avi", ".wmv", ".mpeg", ".mpg"):
        p = video_root / f"{student_id}{ext}"
        if p.is_file():
            return p
    return None


def extract_frame_ffmpeg(
    video_path: Path,
    timestamp_s: float,
    out_path: Path,
    *,
    quality: int = JPEG_QUALITY,
) -> bool:
    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{timestamp_s:.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", str(max(1, min(31, int(31 - quality * 31 / 100)))),
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0 and out_path.is_file() and out_path.stat().st_size > 1000


def process_student(
    student_id: str,
    student_dir: Path,
    video_root: Path,
    log_df,
    session_date: str,
    *,
    dry_run: bool = False,
) -> dict:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not manifest_path.is_file():
        return {"student_id": student_id, "error": "no manifest"}

    manifest = json.loads(manifest_path.read_text())
    all_frames = manifest.get("frames", [])
    all_ts = sorted(float(f["source_timestamp_seconds"]) for f in all_frames)
    video_end = max(all_ts) if all_ts else 0

    video_path = find_video(student_id, video_root)
    video_start, _ = estimate_video_start_utc(None, log_df, student_id, session_date)
    if not video_start:
        return {"student_id": student_id, "error": "no video_start"}

    events = meaningful_event_timestamps_s(
        log_df, student_id, video_start, session_date=session_date
    )
    # Target all events that have no manifest frame within CLOSE_THRESHOLD_S,
    # not just emit_tree_data. Priority (emit) events get a +3s offset to show
    # the result; contextual events get 0s offset to capture the action itself.
    emits = events  # renamed variable kept for minimal diff

    frames_dir = student_dir / f"{student_id}_frames"
    frames_dir.mkdir(exist_ok=True)

    extracted = []
    skipped_covered = 0
    skipped_no_video = []

    for event in emits:
        et = event["timestamp_s"]
        nearest = min((abs(t - et) for t in all_ts), default=9999)

        if nearest <= CLOSE_THRESHOLD_S:
            skipped_covered += 1
            continue

        # emit_tree_data: show result 3s after; all other actions: capture at the moment
        offset = FRAME_OFFSET_S if event["action"] == "emit_tree_data" else 0.0
        target_s = et + offset

        if target_s > video_end + 30:
            skipped_no_video.append(
                {"emit_t": round(et, 1), "target_t": round(target_s, 1),
                 "video_end": round(video_end, 1),
                 "accuracy": event["params"].get("accuracy")}
            )
            continue

        if not video_path:
            LOGGER.warning("[%s] No video file found", student_id)
            break

        # build a deterministic frame_id that won't collide with manifest frames
        action_slug = event["action"].replace("_", "")[:12]
        frame_id = f"{action_slug}_{int(round(et))}"
        out_path = frames_dir / f"{frame_id}.jpg"

        if not dry_run:
            ok = extract_frame_ffmpeg(video_path, target_s, out_path)
            if not ok:
                LOGGER.warning("[%s] ffmpeg failed for t=%.1fs", student_id, target_s)
                continue

        entry = {
            "frame_id": frame_id,
            "source_timestamp_seconds": round(target_s, 3),
            "extraction_trigger_reason": f"{event['action']}_targeted",
            "metrics": {
                "pixel_change_percentage": None,
                "emit_accuracy": event["params"].get("accuracy"),
                "emit_timestamp_s": round(et, 3),
                "associated_speaker_role": None,
                "associated_transcript_id": None,
                "high_value_interaction_zone": True,
            },
            "file_path": str(out_path.relative_to(REPO_ROOT)),
        }

        if not dry_run:
            # inject into manifest
            existing_ids = {f["frame_id"] for f in manifest["frames"]}
            if frame_id not in existing_ids:
                manifest["frames"].append(entry)

        extracted.append({
            "frame_id": frame_id,
            "emit_t": round(et, 1),
            "target_t": round(target_s, 1),
            "accuracy": event["params"].get("accuracy"),
            "dry_run": dry_run,
        })
        LOGGER.info(
            "[%s] %s emit_t=%.1fs target=%.1fs acc=%s",
            student_id,
            "DRY-RUN" if dry_run else "EXTRACTED",
            et, target_s,
            event["params"].get("accuracy"),
        )

    if not dry_run and extracted:
        # re-sort manifest frames by timestamp
        manifest["frames"].sort(key=lambda f: float(f["source_timestamp_seconds"]))
        manifest["_emit_frames_added"] = len(extracted)
        manifest["_emit_frames_added_at"] = datetime.now(timezone.utc).isoformat()
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return {
        "student_id": student_id,
        "total_emits": len(emits),
        "already_covered": skipped_covered,
        "extracted": len(extracted),
        "no_video_coverage": skipped_no_video,
        "details": extracted,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Extract targeted frames at emit_tree_data timestamps"
    )
    parser.add_argument("students", nargs="*", help="Student IDs (default: all with manifests)")
    parser.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    parser.add_argument("--session-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--video-root", type=Path)
    parser.add_argument("--log-csv", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    video_root = args.video_root or VIDEO_ROOTS.get(args.session_date)
    if not video_root or not video_root.is_dir():
        LOGGER.error("Video root not found for %s", args.session_date)
        return 1

    log_csv = args.log_csv or LOG_CSVS.get(args.session_date)
    if not log_csv or not log_csv.is_file():
        LOGGER.error("Log CSV not found for %s", args.session_date)
        return 1

    log_df = load_log_dataframe(log_csv)
    LOGGER.info("Loaded log: %s (%d rows)", log_csv.name, len(log_df))

    audio_root = args.audio_root.resolve()
    targets = args.students or [
        d.name for d in sorted(audio_root.iterdir())
        if d.is_dir() and (d / f"{d.name}_video_extraction_manifest.json").is_file()
    ]

    total_extracted = 0
    total_no_video = 0
    for student_id in targets:
        student_dir = audio_root / student_id
        if not student_dir.is_dir():
            LOGGER.warning("Directory not found: %s", student_dir)
            continue
        result = process_student(
            student_id, student_dir, video_root, log_df, args.session_date,
            dry_run=args.dry_run,
        )
        if "error" in result:
            LOGGER.warning("[%s] %s", student_id, result["error"])
            continue
        total_extracted += result["extracted"]
        total_no_video  += len(result["no_video_coverage"])
        LOGGER.info(
            "[%s] emits=%d covered=%d extracted=%d no_video=%d",
            student_id,
            result["total_emits"],
            result["already_covered"],
            result["extracted"],
            len(result["no_video_coverage"]),
        )
        for nv in result["no_video_coverage"]:
            LOGGER.warning(
                "[%s] emit at %.0fs is after video end (%.0fs) — acc=%s — CANNOT CAPTURE",
                student_id, nv["emit_t"], nv["video_end"], nv["accuracy"],
            )

    action = "Would extract" if args.dry_run else "Extracted"
    LOGGER.info("%s %d frames total; %d emit events have no video coverage",
                action, total_extracted, total_no_video)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
