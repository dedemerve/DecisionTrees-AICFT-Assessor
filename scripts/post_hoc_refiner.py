#!/usr/bin/env python3
"""Post-hoc refinement of an existing video extraction manifest by CODAP content score."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import cv2

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dynamic_video_analytics import CodapContentAnalyzer, CodapTaskGuard, DEFAULT_CODAP_TASK_TEMPLATE_DIR


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a pilot frame subset with content_score >= min-score for Vision Audit.",
    )
    parser.add_argument("student_id", help="Student pseudonym (e.g. Amy)")
    parser.add_argument(
        "--audio-root",
        type=Path,
        default=REPO_ROOT / "data_sources_2026" / "codap_arbor_21april_audio",
    )
    parser.add_argument("--min-content-score", type=int, default=4)
    parser.add_argument(
        "--output-suffix",
        default="_frames_pilot",
        help="Output directory suffix appended to student_id (default: _frames_pilot)",
    )
    parser.add_argument(
        "--codap-task-templates",
        type=Path,
        default=DEFAULT_CODAP_TASK_TEMPLATE_DIR,
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def frame_passes_guard(
    frame_bgr: Any,
    *,
    min_content_score: int,
    codap_guard: CodapTaskGuard,
) -> tuple[bool, dict[str, Any]]:
    signals = CodapContentAnalyzer.analyze(frame_bgr)
    guard_match = codap_guard.classify(frame_bgr)
    passed = guard_match.is_task and signals.content_score >= min_content_score
    return passed, {
        "content_score": signals.content_score,
        "matched_signals": list(signals.matched_signals),
        "guard_reason": guard_match.reason,
        "guard_distance": guard_match.distance,
    }


def refine_student(
    student_dir: Path,
    student_id: str,
    *,
    min_content_score: int,
    output_suffix: str,
    codap_task_templates: Path,
    dry_run: bool,
) -> dict[str, Any]:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frames = manifest.get("frames", [])
    source_dir = student_dir / f"{student_id}_frames"
    pilot_dir = student_dir / f"{student_id}{output_suffix}"
    pilot_manifest_path = student_dir / f"{student_id}_video_extraction_manifest{output_suffix}.json"

    guard = CodapTaskGuard(codap_task_templates, phash_threshold=12)
    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for entry in frames:
        rel = entry["file_path"]
        src = REPO_ROOT / rel if not Path(rel).is_absolute() else Path(rel)
        if not src.is_file():
            src = source_dir / f"{entry['frame_id']}.jpg"
        frame = cv2.imread(str(src))
        if frame is None:
            rejected.append({**entry, "refine_reason": "unreadable_frame"})
            continue

        passed, audit = frame_passes_guard(
            frame,
            min_content_score=min_content_score,
            codap_guard=guard,
        )
        enriched = {**entry, "content_audit": audit}
        if passed:
            kept.append(enriched)
        else:
            rejected.append({**enriched, "refine_reason": "below_content_threshold_or_guard"})

    if not dry_run:
        if pilot_dir.exists():
            shutil.rmtree(pilot_dir)
        pilot_dir.mkdir(parents=True, exist_ok=True)

        pilot_frames: list[dict[str, Any]] = []
        for idx, entry in enumerate(kept, start=1):
            src = REPO_ROOT / entry["file_path"]
            if not src.is_file():
                src = source_dir / f"{entry['frame_id']}.jpg"
            pilot_name = f"frame_{idx:04d}.jpg"
            dst = pilot_dir / pilot_name
            shutil.copy2(src, dst)
            pilot_entry = dict(entry)
            pilot_entry["pilot_frame_id"] = f"frame_{idx:04d}"
            pilot_entry["file_path"] = str(dst.relative_to(REPO_ROOT))
            pilot_frames.append(pilot_entry)

        pilot_manifest = {
            **manifest,
            "schema_version": "video_extraction_manifest_pilot_v1",
            "refinement": {
                "source_manifest": str(manifest_path.relative_to(REPO_ROOT)),
                "min_content_score": min_content_score,
                "source_frame_count": len(frames),
                "pilot_frame_count": len(pilot_frames),
                "rejected_frame_count": len(rejected),
            },
            "summary": {
                **manifest.get("summary", {}),
                "total_frames_extracted": len(pilot_frames),
            },
            "frames": pilot_frames,
        }
        pilot_manifest_path.write_text(
            json.dumps(pilot_manifest, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return {
        "student_id": student_id,
        "source_frames": len(frames),
        "pilot_frames": len(kept),
        "rejected_frames": len(rejected),
        "pilot_dir": str(pilot_dir.relative_to(REPO_ROOT)),
        "pilot_manifest": str(pilot_manifest_path.relative_to(REPO_ROOT)),
        "dry_run": dry_run,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    student_dir = args.audio_root.resolve() / args.student_id
    if not student_dir.is_dir():
        print(f"Student directory not found: {student_dir}", file=sys.stderr)
        return 1

    result = refine_student(
        student_dir,
        args.student_id,
        min_content_score=args.min_content_score,
        output_suffix=args.output_suffix,
        codap_task_templates=args.codap_task_templates.resolve(),
        dry_run=args.dry_run,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
