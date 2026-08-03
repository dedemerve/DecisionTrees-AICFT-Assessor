#!/usr/bin/env python3
"""Produce gold_behavior_alignment.v1.jsonl for 2026 cohort sessions.

Primary alignment method: ordinal-proportional heuristic (same as Edgar fix).
For each observation step i (0-indexed), assigns the frame at:
    frame_idx = round(i / (n_steps - 1) * (n_frames - 1))
and derives timestamp_ms from the video extraction manifest.

Optional Claude Vision verification: with --vision-verify, sends the top-K
frames nearest each ideal frame to the Claude API for confirmation. Requires
ANTHROPIC_API_KEY in the environment.

Output per student/session (v2 layout):
    training_datasets/2026/{student}/{session}/annotations/
        {student}_gold_behavior_alignment.v1.jsonl
    training_datasets/2026/{student}/{session}/intermediate/
        {student}_silver_cost_matrix_meta.json

Usage:
    python scripts/finalize_2026_gold_alignment.py --student Amy --session codap_21apr
    python scripts/finalize_2026_gold_alignment.py --all
    python scripts/finalize_2026_gold_alignment.py --all --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_2026 = REPO_ROOT / "data_sources_2026"
OUT_ROOT = REPO_ROOT / "training_datasets" / "2026"

SESSIONS: list[str] = ["codap_21apr", "codap_28apr", "colab_05may"]

SESSION_FRAME_DIRS: dict[str, str] = {
    "codap_21apr": "codap_arbor_21april_audio",
    "codap_28apr": "codap_arbor_28april_audio",
    "colab_05may": "colab_python_audio",
}

ALIGNMENT_METHOD = "ordinal_proportional_heuristic"

LOGGER = logging.getLogger("finalize_2026_gold_alignment")


# ─────────────────────────────────────────────────────────────
# Frame index loading
# ─────────────────────────────────────────────────────────────

def sorted_frame_paths(student: str, session: str) -> list[Path]:
    subdir = SESSION_FRAME_DIRS.get(session, "")
    if not subdir:
        return []
    frames_dir = DATA_2026 / subdir / student / f"{student}_frames"
    if not frames_dir.is_dir():
        return []
    jpgs = sorted(frames_dir.glob("*.jpg"))
    pngs = sorted(frames_dir.glob("*.png"))
    return sorted(jpgs + pngs, key=lambda p: p.name)


def load_manifest(student: str, session: str) -> dict[str, Any] | None:
    subdir = SESSION_FRAME_DIRS.get(session, "")
    if not subdir:
        return None
    path = DATA_2026 / subdir / student / f"{student}_video_extraction_manifest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def frame_timestamp_ms(
    frame_path: Path,
    manifest: dict[str, Any] | None,
    frame_paths: list[Path],
    total_duration_ms: int | None,
) -> int | None:
    """Return timestamp_ms for a frame from the manifest or by ordinal interpolation."""
    if manifest is None:
        if total_duration_ms is None:
            return None
        n = len(frame_paths)
        idx = frame_paths.index(frame_path)
        return round(idx / max(n - 1, 1) * total_duration_ms)

    # Manifest may have per-frame records or a source_timestamp_seconds list.
    frames_meta = manifest.get("frames") or []
    stem = frame_path.stem

    # Try by filename match in manifest frames list
    for entry in frames_meta:
        if entry.get("frame_id") == stem or entry.get("filename") == frame_path.name:
            ts_s = entry.get("source_timestamp_seconds") or entry.get("timestamp_s")
            if ts_s is not None:
                return round(float(ts_s) * 1000)

    # Fallback: use ordinal index * (total_duration / n_frames)
    n = len(frame_paths)
    if n == 0:
        return None
    idx = frame_paths.index(frame_path)
    duration_ms = manifest.get("duration_ms") or (
        (manifest.get("duration_s") or 0) * 1000
    )
    if not duration_ms:
        return None
    return round(idx / max(n - 1, 1) * duration_ms)


# ─────────────────────────────────────────────────────────────
# Observation steps loading
# ─────────────────────────────────────────────────────────────

def load_observation_steps(student: str, session: str) -> list[dict[str, Any]]:
    path = (
        OUT_ROOT
        / student
        / session
        / "intermediate"
        / f"{student}_observation_steps.json"
    )
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("observation_steps") or []


# ─────────────────────────────────────────────────────────────
# Ordinal-proportional alignment
# ─────────────────────────────────────────────────────────────

def ordinal_proportional_align(
    steps: list[dict[str, Any]],
    frame_paths: list[Path],
    manifest: dict[str, Any] | None,
    total_duration_ms: int | None,
) -> list[dict[str, Any]]:
    """Assign one frame per step using ordinal-proportional mapping.

    step i → frame at round(i / (n_steps-1) * (n_frames-1)).
    For a single step, always assigns frame_0 (index 0).
    """
    n_steps = len(steps)
    n_frames = len(frame_paths)

    rows: list[dict[str, Any]] = []
    for i, step in enumerate(steps):
        if n_frames == 0:
            ideal_frame_idx = 0
            matched_frame_id = None
            timestamp_ms = None
            confidence = 0.0
        elif n_steps == 1:
            ideal_frame_idx = 0
            matched_frame_path = frame_paths[0]
            matched_frame_id = matched_frame_path.stem
            timestamp_ms = frame_timestamp_ms(
                matched_frame_path, manifest, frame_paths, total_duration_ms
            )
            confidence = 0.5
        else:
            ideal_frame_idx = round(i / (n_steps - 1) * (n_frames - 1))
            ideal_frame_idx = max(0, min(ideal_frame_idx, n_frames - 1))
            matched_frame_path = frame_paths[ideal_frame_idx]
            matched_frame_id = matched_frame_path.stem
            timestamp_ms = frame_timestamp_ms(
                matched_frame_path, manifest, frame_paths, total_duration_ms
            )
            confidence = 0.5

        rows.append({
            "metadata": {
                "observation_step_index": i,
                "uzman_nitel_gozlemi_snippet": (
                    step.get("uzman_nitel_gozlemi") or step.get("uzman_nitel_gözlemi") or ""
                )[:120],
                "bilissel_davranis_kategorisi": (
                    step.get("labels", {}).get("bilişsel_davranış_kategorisi")
                    or step.get("labels", {}).get("bilissel_davranis_kategorisi")
                    or "EXPLORE"
                ),
            },
            "silver_video": {
                "matched_frame_id": matched_frame_id,
                "ideal_frame_idx": ideal_frame_idx if n_frames > 0 else None,
                "timestamp_ms": timestamp_ms,
                "confidence": confidence,
                "alignment_method": ALIGNMENT_METHOD,
            },
        })

    return rows


# ─────────────────────────────────────────────────────────────
# Optional Claude Vision verification
# ─────────────────────────────────────────────────────────────

def vision_verify(
    rows: list[dict[str, Any]],
    frame_paths: list[Path],
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Optionally verify frame assignments via Claude Vision API.

    For each row, sends top_k frames near the ideal_frame_idx to Claude and
    asks which best matches the step description. Updates matched_frame_id and
    confidence if Claude's choice differs.
    """
    try:
        import anthropic
        import base64
    except ImportError:
        LOGGER.warning("anthropic package not found — skipping vision verification")
        return rows

    client = anthropic.Anthropic()
    n_frames = len(frame_paths)

    for row in rows:
        ideal_idx = row["silver_video"].get("ideal_frame_idx")
        if ideal_idx is None or n_frames == 0:
            continue

        snippet = row["metadata"].get("uzman_nitel_gozlemi_snippet", "")
        category = row["metadata"].get("bilissel_davranis_kategorisi", "")

        # Candidate frames within top_k window
        half = top_k // 2
        lo = max(0, ideal_idx - half)
        hi = min(n_frames - 1, lo + top_k - 1)
        candidates = frame_paths[lo : hi + 1]

        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    f"Expert observation step: \"{snippet}\"\n"
                    f"Cognitive category: {category}\n\n"
                    f"Which of the following {len(candidates)} frames best matches "
                    f"the state described above? Reply with only the frame number "
                    f"(1-{len(candidates)})."
                ),
            }
        ]
        for fp in candidates:
            ext = fp.suffix.lower().lstrip(".")
            media_type = f"image/{'jpeg' if ext in {'jpg', 'jpeg'} else 'png'}"
            data = fp.read_bytes()
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": __import__("base64").b64encode(data).decode(),
                },
            })

        try:
            resp = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=8,
                messages=[{"role": "user", "content": content}],
            )
            answer = resp.content[0].text.strip()
            choice = int(re.sub(r"\D", "", answer)) - 1
            if 0 <= choice < len(candidates):
                chosen = candidates[choice]
                if chosen != frame_paths[ideal_idx]:
                    row["silver_video"]["matched_frame_id"] = chosen.stem
                    row["silver_video"]["confidence"] = 0.75
                    row["silver_video"]["vision_verified"] = True
                    LOGGER.debug(
                        "Step %d: vision chose %s over %s",
                        row["metadata"]["observation_step_index"],
                        chosen.name,
                        frame_paths[ideal_idx].name,
                    )
                else:
                    row["silver_video"]["vision_verified"] = True
        except Exception as exc:
            LOGGER.warning("Vision API call failed for step %d: %s", row["metadata"]["observation_step_index"], exc)

    return rows


# ─────────────────────────────────────────────────────────────
# Cost matrix meta (for compatibility with downstream readers)
# ─────────────────────────────────────────────────────────────

def write_cost_matrix_npy(
    out_dir: Path,
    student: str,
    n_steps: int,
    n_frames: int,
) -> Path | None:
    """Write ordinal-proportional distance matrix as float32 .npy binary.

    Shape: (n_steps, n_frames). Entry [i, j] = |ideal_j_for_step_i - j| / n_frames,
    where ideal_j = round(i / (n_steps-1) * (n_frames-1)).
    Returns the written path, or None when either dimension is zero.
    """
    if n_steps == 0:
        return None
    if n_frames == 0:
        # Write a placeholder so downstream checks find the file; shape=(n_steps, 0)
        out_dir.mkdir(parents=True, exist_ok=True)
        npy_path = out_dir / f"{student}_silver_cost_matrix.npy"
        np.save(str(npy_path), np.empty((n_steps, 0), dtype=np.float32))
        LOGGER.info("Wrote placeholder cost matrix .npy (no frames): %s  shape=(%d, 0)", npy_path, n_steps)
        return npy_path

    matrix = np.zeros((n_steps, n_frames), dtype=np.float32)
    for i in range(n_steps):
        ideal = round(i / max(n_steps - 1, 1) * (n_frames - 1))
        for j in range(n_frames):
            matrix[i, j] = abs(ideal - j) / n_frames

    out_dir.mkdir(parents=True, exist_ok=True)
    npy_path = out_dir / f"{student}_silver_cost_matrix.npy"
    np.save(str(npy_path), matrix)
    LOGGER.info(
        "Wrote cost matrix .npy: %s  shape=%s  dtype=%s",
        npy_path, matrix.shape, matrix.dtype,
    )
    return npy_path


def write_cost_matrix_meta(
    out_dir: Path,
    student: str,
    n_steps: int,
    n_frames: int,
    session: str,
    npy_path: Path | None = None,
) -> None:
    meta = {
        "alignment_method": ALIGNMENT_METHOD,
        "n_steps": n_steps,
        "n_frames": n_frames,
        "student_id": student,
        "session": session,
        "note": (
            "Ordinal-proportional heuristic. "
            "Frame index = round(step_i / (n_steps-1) * (n_frames-1))."
        ),
        "binary_cost_matrix": str(npy_path.relative_to(out_dir.parent.parent.parent)) if npy_path else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{student}_silver_cost_matrix_meta.json"
    path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Wrote cost matrix meta: %s", path)


# ─────────────────────────────────────────────────────────────
# Core processing
# ─────────────────────────────────────────────────────────────

def process(
    student: str,
    session: str,
    vision_verify_flag: bool = False,
    dry_run: bool = False,
) -> None:
    steps = load_observation_steps(student, session)
    frame_paths = sorted_frame_paths(student, session)
    manifest = load_manifest(student, session)

    total_duration_ms: int | None = None
    if manifest:
        total_duration_ms = manifest.get("duration_ms") or (
            int(manifest.get("duration_s", 0) * 1000) or None
        )

    n_steps = len(steps)
    n_frames = len(frame_paths)

    if n_steps == 0:
        LOGGER.warning(
            "%s/%s: 0 observation steps — alignment skipped (run build_2026_mmla_training_dataset.py first)",
            student, session,
        )
        if dry_run:
            print(f"[DRY-RUN] {student}/{session}: 0 steps — skipped")
        return

    if n_frames == 0:
        LOGGER.warning(
            "%s/%s: 0 frames found in %s/%s/%s_frames/ — writing null alignment",
            student, session,
            SESSION_FRAME_DIRS.get(session, ""), student, student,
        )

    rows = ordinal_proportional_align(steps, frame_paths, manifest, total_duration_ms)

    if vision_verify_flag and n_frames > 0:
        rows = vision_verify(rows, frame_paths)

    if dry_run:
        span_ms = None
        valid = [r for r in rows if r["silver_video"]["timestamp_ms"] is not None]
        if valid:
            ts_vals = [r["silver_video"]["timestamp_ms"] for r in valid]
            span_ms = max(ts_vals) - min(ts_vals)
        print(
            f"[DRY-RUN] {student}/{session}: {n_steps} steps, {n_frames} frames, "
            f"span_ms={span_ms}"
        )
        return

    # Write JSONL
    annotations_dir = OUT_ROOT / student / session / "annotations"
    annotations_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = annotations_dir / f"{student}_gold_behavior_alignment.v1.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    LOGGER.info("Wrote alignment JSONL: %s (%d rows)", jsonl_path, len(rows))

    # Write binary cost matrix (.npy) then the JSON meta with a pointer to it
    intermediate_dir = OUT_ROOT / student / session / "intermediate"
    npy_path = write_cost_matrix_npy(intermediate_dir, student, n_steps, n_frames)
    write_cost_matrix_meta(intermediate_dir, student, n_steps, n_frames, session, npy_path=npy_path)

    # Compute span for reporting
    valid_ts = [r["silver_video"]["timestamp_ms"] for r in rows if r["silver_video"]["timestamp_ms"] is not None]
    span_ms = (max(valid_ts) - min(valid_ts)) if len(valid_ts) >= 2 else 0
    linkage_tier = (
        "L1" if (total_duration_ms and span_ms / total_duration_ms >= 0.90) else
        "L2" if (total_duration_ms and span_ms / total_duration_ms >= 0.70) else
        "L3"
    )

    print(
        f"  {student}/{session}: {n_steps} steps, {n_frames} frames, "
        f"span={span_ms}ms, tier={linkage_tier} → {jsonl_path}"
    )


def discover_students() -> list[str]:
    dirs = [d.name for d in OUT_ROOT.iterdir() if d.is_dir()] if OUT_ROOT.is_dir() else []
    return sorted(dirs)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main() -> None:
    import re as _re

    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    parser = argparse.ArgumentParser(
        description="Produce 2026 gold_behavior_alignment.v1.jsonl via ordinal-proportional heuristic."
    )
    parser.add_argument("--student", "-s", help="Pseudonym (e.g. Amy).")
    parser.add_argument("--session", choices=SESSIONS, help="Session ID.")
    parser.add_argument(
        "--all",
        action="store_true",
        dest="all_students",
        help="Process all students under training_datasets/2026/ for all sessions.",
    )
    parser.add_argument(
        "--vision-verify",
        action="store_true",
        help="Send candidate frames to Claude Vision API for confirmation. Requires ANTHROPIC_API_KEY.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.all_students:
        students = discover_students()
        if not students:
            LOGGER.warning("No student directories found under %s", OUT_ROOT)
        for stu in students:
            for ses in SESSIONS:
                process(stu, ses, vision_verify_flag=args.vision_verify, dry_run=args.dry_run)
    else:
        if not args.student:
            parser.error("--student is required when not using --all")
        if not args.session:
            parser.error("--session is required when not using --all")
        process(
            args.student,
            args.session,
            vision_verify_flag=args.vision_verify,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
