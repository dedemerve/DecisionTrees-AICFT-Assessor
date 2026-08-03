#!/usr/bin/env python3
"""Prune an extracted frame set to frames that pass the current CodapTaskGuard."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dynamic_video_analytics import (
    DEFAULT_CODAP_TASK_TEMPLATE_DIR,
    DEFAULT_COLAB_TASK_TEMPLATE_DIR,
    DEFAULT_NON_TASK_TEMPLATE_DIR,
    NonTaskScreenFilter,
    build_task_screen_guard,
    frame_kept_by_pipeline_guard,
    task_activity_from_params,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prune student frames to CODAP-guard-compliant subset.")
    p.add_argument("student_id")
    p.add_argument(
        "--audio-root",
        type=Path,
        default=REPO_ROOT / "data_sources_2026" / "codap_arbor_21april_audio",
    )
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def prune(student_dir: Path, student_id: str, *, dry_run: bool) -> dict:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    frames_dir = student_dir / f"{student_id}_frames"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    params = manifest.get("parameters") or {}
    task_activity = task_activity_from_params(params)
    task_guard = build_task_screen_guard(
        task_activity,
        codap_template_dir=DEFAULT_CODAP_TASK_TEMPLATE_DIR,
        colab_template_dir=DEFAULT_COLAB_TASK_TEMPLATE_DIR,
    )
    filt = NonTaskScreenFilter(
        DEFAULT_NON_TASK_TEMPLATE_DIR,
        task_guard=task_guard,
        require_codap_content=True,
        phash_threshold=10,
    )

    kept_entries: list[dict] = []
    removed: list[str] = []

    for entry in sorted(manifest.get("frames", []), key=lambda e: e["source_timestamp_seconds"]):
        src = REPO_ROOT / entry["file_path"]
        if not src.is_file():
            src = frames_dir / f"{entry['frame_id']}.jpg"
        bgr = cv2.imread(str(src))
        if bgr is None:
            removed.append(entry["frame_id"])
            continue
        trigger = entry.get("extraction_trigger_reason", "motion_threshold_exceeded")
        if not frame_kept_by_pipeline_guard(
            bgr,
            filt=filt,
            task_guard=task_guard,
            trigger_reason=trigger,
            task_activity=task_activity,
        ):
            removed.append(entry["frame_id"])
            continue
        kept_entries.append(entry)

    if dry_run:
        return {
            "student_id": student_id,
            "source": len(manifest.get("frames", [])),
            "kept": len(kept_entries),
            "removed": len(removed),
            "removed_ids": removed[:20],
            "dry_run": True,
        }

    staging = student_dir / f"{student_id}_frames_prune_staging"
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    new_frames: list[dict] = []
    for idx, entry in enumerate(kept_entries, start=1):
        src = REPO_ROOT / entry["file_path"]
        if not src.is_file():
            src = frames_dir / f"{entry['frame_id']}.jpg"
        new_id = f"frame_{idx:04d}"
        dst = staging / f"{new_id}.jpg"
        shutil.copy2(src, dst)
        new_entry = dict(entry)
        new_entry["frame_id"] = new_id
        new_entry["file_path"] = str(dst.relative_to(REPO_ROOT))
        new_frames.append(new_entry)

    shutil.rmtree(frames_dir)
    staging.rename(frames_dir)

    for entry in new_frames:
        entry["file_path"] = str((frames_dir / f"{entry['frame_id']}.jpg").relative_to(REPO_ROOT))

    summary = dict(manifest.get("summary", {}))
    summary["total_frames_extracted"] = len(new_frames)
    summary["pruned_frames_removed"] = len(removed)

    manifest["frames"] = new_frames
    manifest["summary"] = summary
    manifest["pruned_at"] = "prune_to_guard.py"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "student_id": student_id,
        "source": len(manifest.get("frames", [])) + len(removed),
        "kept": len(new_frames),
        "removed": len(removed),
        "removed_ids": removed[:20],
        "dry_run": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    student_dir = args.audio_root.resolve() / args.student_id
    result = prune(student_dir, args.student_id, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
