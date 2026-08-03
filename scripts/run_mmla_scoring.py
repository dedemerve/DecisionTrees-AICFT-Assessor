#!/usr/bin/env python3
"""run_mmla_scoring.py — Resume-capable wrapper around mmla_scorer.py.

Adds per-frame JSONL checkpointing so long scoring runs survive interruption.
Each scored frame is immediately appended to:
    logs/pipeline_runs/{student}_{session}_frames.jsonl

On restart, already-processed frame IDs are loaded and skipped.
Output format of frame_observations.json and final_scored.json is unchanged.

Usage:
    python scripts/run_mmla_scoring.py --session 21apr --students Helena
    python scripts/run_mmla_scoring.py --session 21apr   # all students
    python scripts/run_mmla_scoring.py --session 28apr --students Bruno Irma
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Patch and import mmla_scorer from trash (fixes REPO_ROOT path)
# ---------------------------------------------------------------------------

_SCORER_SRC = (REPO_ROOT / "trash/scoring_out_of_scope_2026-07-20/mmla_scorer.py").read_text()
_SCORER_SRC = _SCORER_SRC.replace(
    "REPO_ROOT = Path(__file__).parent",
    f"REPO_ROOT = Path('{REPO_ROOT}')",
)
_scorer_mod = types.ModuleType("mmla_scorer_patched")
_scorer_mod.__file__ = str(REPO_ROOT / "trash/scoring_out_of_scope_2026-07-20/mmla_scorer.py")
exec(compile(_SCORER_SRC, "mmla_scorer.py", "exec"), _scorer_mod.__dict__)

MMLAScorer = _scorer_mod.MMLAScorer
SESSION_STUDENTS: dict[str, list[str]] = _scorer_mod.SESSION_STUDENTS

# ---------------------------------------------------------------------------
# Resume helpers
# ---------------------------------------------------------------------------

LOG_DIR = REPO_ROOT / "logs" / "pipeline_runs"


def _ckpt_path(student: str, session: str) -> Path:
    return LOG_DIR / f"{student}_{session}_frames.jsonl"


def _load_done_ids(student: str, session: str) -> set[str]:
    p = _ckpt_path(student, session)
    if not p.exists():
        return set()
    done: set[str] = set()
    for line in p.read_text(encoding="utf-8").splitlines():
        try:
            done.add(json.loads(line)["frame_id"])
        except Exception:
            pass
    return done


def _append_frame(student: str, session: str, result: dict) -> None:
    p = _ckpt_path(student, session)
    with p.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(result, ensure_ascii=False) + "\n")
        fh.flush()


# ---------------------------------------------------------------------------
# Patched score_student with resume + progress printing
# ---------------------------------------------------------------------------

def _score_student_resumable(scorer: MMLAScorer, student: str) -> tuple[Path | None, Path | None]:
    import pipeline_schema as ps

    DATA_ROOT = REPO_ROOT / "data_sources_2026"
    SESSION_AUDIO_DIRS: dict[str, str] = _scorer_mod.SESSION_AUDIO_DIRS
    _build_final_scored_json = _scorer_mod._build_final_scored_json

    audio_dir = DATA_ROOT / SESSION_AUDIO_DIRS[scorer.session_key] / student
    manifest_path = audio_dir / f"{student}_video_extraction_manifest.json"
    frame_obs_path = ps.mmla_frame_obs_path(student, scorer.session_key)
    final_path = ps.mmla_final_scored_path(student, scorer.session_key)

    if not manifest_path.exists():
        print(f"  [{student}] Manifest not found: {manifest_path}")
        return None, None

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frames_key = "segments" if scorer.session_type == "codap_arbor" else "frames"
    frame_entries = manifest.get(frames_key, [])

    if not frame_entries:
        print(f"  [{student}] No frame entries in manifest")
        return None, None

    transcript = scorer._load_transcript(student, audio_dir)
    has_audio = transcript is not None

    # Resume: load already-done frames from checkpoint JSONL
    done_ids = _load_done_ids(student, scorer.session_key)
    if done_ids:
        print(f"  [{student}] Resuming — {len(done_ids)} frames already done, skipping")

    # Load existing results from checkpoint
    ckpt = _ckpt_path(student, scorer.session_key)
    frame_results: list[dict] = []
    if ckpt.exists():
        for line in ckpt.read_text(encoding="utf-8").splitlines():
            try:
                frame_results.append(json.loads(line))
            except Exception:
                pass

    frames_skipped = 0
    session_context: dict = {
        "previous_dependent_variable": None,
        "previous_split_value": None,
        "previous_code_state": None,
        "error_in_previous_frame": False,
        "emit_count_so_far": 0,
    }

    # Rebuild session_context from already-done frames
    for past in frame_results:
        scorer._update_session_context(session_context, past, {})

    total = len(frame_entries)
    new_this_run = 0
    t_start = time.monotonic()

    for i, entry in enumerate(frame_entries):
        ts = entry.get("source_timestamp_seconds", 0.0)
        frame_id = f"{student}_{scorer.session_key}_t{int(ts):05d}s"

        if frame_id in done_ids:
            continue

        result = scorer._score_frame(student, entry, session_context, transcript, audio_dir)
        if result is None:
            frames_skipped += 1
            continue

        frame_results.append(result)
        done_ids.add(frame_id)
        _append_frame(student, scorer.session_key, result)
        scorer._update_session_context(session_context, result, entry)
        new_this_run += 1

        completed = len(frame_results)
        if completed % 50 == 0 or completed == total:
            elapsed = time.monotonic() - t_start
            rate = new_this_run / elapsed if elapsed > 0 else 0
            remaining = (total - completed) / rate if rate > 0 else 0
            print(
                f"  [{student}] {completed}/{total} frames done "
                f"({completed/total*100:.0f}%)  "
                f"+{new_this_run} this run  "
                f"eta ~{remaining/60:.0f} min"
            )

    raw_duration = (manifest.get("video_profile") or {}).get("duration_seconds") or 0.0
    if raw_duration <= 0.0 and frame_entries:
        raw_duration = max(e.get("source_timestamp_seconds", 0.0) for e in frame_entries)

    # Write frame_observations.json
    frame_obs = {
        "student_id": student,
        "session_key": scorer.session_key,
        "schema_version": "4.1",
        "audio_available": has_audio,
        "frames_total": len(frame_results),
        "frames_skipped": frames_skipped,
        "duration_seconds": raw_duration,
        "frames": frame_results,
    }
    frame_obs_path.write_text(json.dumps(frame_obs, ensure_ascii=False, indent=2), encoding="utf-8")

    # Write final_scored.json
    final = _build_final_scored_json(student, scorer.session_key, frame_results, has_audio)
    final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")

    # Legacy summary
    summary = _scorer_mod.ps.mmla_session_summary(
        student, scorer.session_key, frame_results,
        frames_skipped=frames_skipped,
        duration_seconds=raw_duration,
    )
    legacy_path = _scorer_mod.ps.mmla_output_path(student, scorer.session_key)
    legacy_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  [{student}] DONE — {len(frame_results)} frames, {frames_skipped} skipped")
    print(f"  [{student}] frame_observations: {frame_obs_path}")
    print(f"  [{student}] final_scored:       {final_path}")
    return frame_obs_path, final_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Resume-capable MMLA scorer")
    parser.add_argument("--session", required=True, choices=("21apr", "28apr", "05may"))
    parser.add_argument("--students", nargs="*")
    parser.add_argument("--model", default="claude-haiku-4-5-20251001")
    args = parser.parse_args()

    students = args.students or SESSION_STUDENTS.get(args.session, [])
    if not students:
        print(f"No students for session {args.session}")
        sys.exit(1)

    print(f"Session  : {args.session}")
    print(f"Students : {students}")
    print(f"Model    : {args.model}")
    print()

    t0 = time.monotonic()
    ok, failed = [], []

    with MMLAScorer(args.session, model=args.model) as scorer:
        for student in students:
            ckpt = _ckpt_path(student, args.session)
            done_count = len(_load_done_ids(student, args.session))
            print(f"\n{'='*60}")
            print(f"Scoring {student}  (checkpoint: {done_count} frames already done)")
            print(f"{'='*60}")
            try:
                obs, final = _score_student_resumable(scorer, student)
                if final and final.exists():
                    ok.append(student)
                else:
                    failed.append(student)
            except Exception as exc:
                print(f"  [{student}] ERROR: {exc}")
                failed.append(student)

    elapsed = time.monotonic() - t0
    print(f"\n{'='*60}")
    print(f"Done in {elapsed/60:.1f} min — {len(ok)} OK, {len(failed)} failed")
    if ok:
        print(f"OK:     {ok}")
    if failed:
        print(f"FAILED: {failed}")


if __name__ == "__main__":
    main()
