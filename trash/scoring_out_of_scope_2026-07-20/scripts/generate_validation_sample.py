#!/usr/bin/env python3
"""Stratified random sampling for expert frame review.

Selects a balanced test suite from a student's extraction manifest and produces
a verification sheet that binds each sampled frame to its surrounding transcript
dialogue — enabling an expert to confirm cross-modal alignment without watching
the full recording.

Stratification:
  - 5 frames: speech_anchor, speaker role == student
  - 5 frames: speech_anchor, speaker role == teacher
  - 5 frames: motion_threshold_exceeded (any pixel-change trigger)

Output: logs/validation_suite_<Student>_<Timestamp>.json
"""

from __future__ import annotations

import argparse
import json
import logging
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR  = REPO_ROOT / "logs"

LOGGER = logging.getLogger("validation_sample")

STRATA_SPEC: list[dict[str, Any]] = [
    {
        "label": "speech_anchor_student",
        "n": 5,
        "match": lambda e: (
            "speech_anchor" in (e.get("extraction_trigger_reason") or "")
            and (e.get("associated_speaker_role") or "").lower() == "student"
        ),
    },
    {
        "label": "speech_anchor_teacher",
        "n": 5,
        "match": lambda e: (
            "speech_anchor" in (e.get("extraction_trigger_reason") or "")
            and (e.get("associated_speaker_role") or "").lower() == "teacher"
        ),
    },
    {
        "label": "motion_threshold_exceeded",
        "n": 5,
        "match": lambda e: (
            (e.get("pixel_change_percentage") is not None)
            or "motion" in (e.get("extraction_trigger_reason") or "").lower()
        ),
    },
]

CONTEXT_WINDOW = 3   # dialogue lines before and after the sampled frame timestamp


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _frame_entries(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return manifest.get("frames") or manifest.get("segments") or []


def _resolve_frame_path(entry: dict[str, Any], student_dir: Path, student_id: str) -> Path:
    stored = entry.get("file_path") or ""
    if stored:
        candidate = REPO_ROOT / stored
        if candidate.is_file():
            return candidate
    frame_id = entry["frame_id"]
    return student_dir / f"{student_id}_frames" / f"{frame_id}.jpg"


def _load_transcript(student_dir: Path, student_id: str) -> list[dict[str, Any]]:
    """Return transcript segments sorted by start time.

    Tries hybrid diarization JSON first, then plain transcript JSON.
    Falls back to empty list if neither exists.
    """
    candidates = [
        student_dir / f"{student_id}_hybrid_diarization.json",
        student_dir / f"{student_id}_transcript.json",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = _load_json(path)
            # hybrid diarization wraps segments under "segments" key
            segs = data if isinstance(data, list) else data.get("segments", [])
            return sorted(segs, key=lambda s: float(s.get("start", 0)))
        except (json.JSONDecodeError, OSError, KeyError) as exc:
            LOGGER.warning("Could not load transcript from %s: %s", path.name, exc)
    return []


def _dialogue_context(
    transcript: list[dict[str, Any]],
    frame_ts: float,
) -> dict[str, list[dict[str, Any]]]:
    """Return preceding, concurrent, and succeeding segments around frame_ts."""
    preceding   = []
    concurrent  = []
    succeeding  = []

    for seg in transcript:
        start = float(seg.get("start", 0))
        end   = float(seg.get("end",   start))
        if end < frame_ts:
            preceding.append(seg)
        elif start > frame_ts:
            succeeding.append(seg)
        else:
            concurrent.append(seg)

    return {
        "preceding":  preceding[-CONTEXT_WINDOW:],
        "concurrent": concurrent,
        "succeeding": succeeding[:CONTEXT_WINDOW],
    }


def _stratum_sample(
    entries: list[dict[str, Any]],
    match_fn: Any,
    n: int,
    rng: random.Random,
) -> list[dict[str, Any]]:
    pool = [e for e in entries if match_fn(e)]
    if len(pool) < n:
        LOGGER.warning(
            "Stratum pool has only %d entries (requested %d) — returning all",
            len(pool), n,
        )
        return pool
    return rng.sample(pool, n)


def build_verification_entry(
    entry: dict[str, Any],
    student_dir: Path,
    student_id: str,
    transcript: list[dict[str, Any]],
    stratum_label: str,
) -> dict[str, Any]:
    frame_ts   = float(entry.get("source_timestamp_seconds", 0))
    frame_path = _resolve_frame_path(entry, student_dir, student_id)
    context    = _dialogue_context(transcript, frame_ts)

    return {
        "frame_id":                   entry["frame_id"],
        "stratum":                    stratum_label,
        "source_timestamp_seconds":   frame_ts,
        "absolute_image_path":        str(frame_path.resolve()),
        "file_exists_on_disk":        frame_path.is_file(),
        "extraction_trigger_reason":  entry.get("extraction_trigger_reason"),
        "associated_speaker_role":    entry.get("associated_speaker_role"),
        "associated_transcript_id":   entry.get("associated_transcript_id"),
        "pixel_change_percentage":    entry.get("pixel_change_percentage"),
        "high_value_interaction_zone": entry.get("high_value_interaction_zone", False),
        "dialogue_context": {
            "preceding":  [
                {
                    "start":   s.get("start"),
                    "end":     s.get("end"),
                    "speaker": s.get("speaker") or s.get("role"),
                    "text":    s.get("text") or s.get("transcript"),
                }
                for s in context["preceding"]
            ],
            "concurrent": [
                {
                    "start":   s.get("start"),
                    "end":     s.get("end"),
                    "speaker": s.get("speaker") or s.get("role"),
                    "text":    s.get("text") or s.get("transcript"),
                }
                for s in context["concurrent"]
            ],
            "succeeding": [
                {
                    "start":   s.get("start"),
                    "end":     s.get("end"),
                    "speaker": s.get("speaker") or s.get("role"),
                    "text":    s.get("text") or s.get("transcript"),
                }
                for s in context["succeeding"]
            ],
        },
    }


def generate_for_student(
    student_id: str,
    student_dir: Path,
    *,
    seed: int | None = None,
) -> Path:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest   = _load_json(manifest_path)
    entries    = _frame_entries(manifest)
    transcript = _load_transcript(student_dir, student_id)

    if not transcript:
        LOGGER.warning("[%s] No transcript found — dialogue_context blocks will be empty", student_id)

    rng = random.Random(seed)

    sampled_entries: list[tuple[str, dict[str, Any]]] = []
    for spec in STRATA_SPEC:
        drawn = _stratum_sample(entries, spec["match"], spec["n"], rng)
        for e in drawn:
            sampled_entries.append((spec["label"], e))

    verification_suite = []
    for label, entry in sampled_entries:
        item = build_verification_entry(entry, student_dir, student_id, transcript, label)
        verification_suite.append(item)
        LOGGER.info(
            "[%s] sampled %s  t=%.1fs  trigger=%s",
            student_id, label,
            item["source_timestamp_seconds"],
            item["extraction_trigger_reason"],
        )

    LOGS_DIR.mkdir(exist_ok=True)
    ts_str    = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    out_path  = LOGS_DIR / f"validation_suite_{student_id}_{ts_str}.json"

    output = {
        "generated_at":    datetime.now(timezone.utc).isoformat(),
        "student_id":      student_id,
        "seed":            seed,
        "total_sampled":   len(verification_suite),
        "strata_summary": {
            spec["label"]: sum(1 for lbl, _ in sampled_entries if lbl == spec["label"])
            for spec in STRATA_SPEC
        },
        "manifest_frame_count": len(entries),
        "transcript_segment_count": len(transcript),
        "frames": verification_suite,
    }

    out_path.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return out_path


def _print_markdown_summary(results: list[tuple[str, Path | None, str | None]]) -> None:
    header = "| Student | Status | Output File |"
    sep    = "|---------|--------|-------------|"
    print("\n" + header)
    print(sep)
    for student_id, out_path, error in results:
        if out_path is not None:
            status = "OK"
            fname  = out_path.name
        else:
            status = f"FAIL — {error}"
            fname  = "—"
        print(f"| {student_id:<12} | {status} | {fname} |")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate stratified validation sample for expert review"
    )
    parser.add_argument("students", nargs="+", help="Student IDs to sample")
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42, help="RNG seed for reproducibility")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    audio_root = args.audio_root.resolve()
    if not audio_root.is_dir():
        LOGGER.error("audio-root not found: %s", audio_root)
        return 1

    results: list[tuple[str, Path | None, str | None]] = []
    exit_code = 0

    for student_id in args.students:
        student_dir = audio_root / student_id
        if not student_dir.is_dir():
            LOGGER.error("[%s] Directory not found: %s", student_id, student_dir)
            results.append((student_id, None, "directory not found"))
            exit_code = 1
            continue

        try:
            out_path = generate_for_student(student_id, student_dir, seed=args.seed)
            LOGGER.info("[%s] Saved -> %s", student_id, out_path.relative_to(REPO_ROOT))
            results.append((student_id, out_path, None))
        except FileNotFoundError as exc:
            LOGGER.error("[%s] %s", student_id, exc)
            results.append((student_id, None, str(exc)))
            exit_code = 1
        except Exception as exc:
            LOGGER.exception("[%s] Unexpected error: %s", student_id, exc)
            results.append((student_id, None, str(exc)))
            exit_code = 1

    _print_markdown_summary(results)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
