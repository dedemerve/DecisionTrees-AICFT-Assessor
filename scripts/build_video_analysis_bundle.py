#!/usr/bin/env python3
"""Build process/pipeline video analysis bundles (scoring OUT OF SCOPE).

Active Q1 scope: pipeline / process data / methods — not B0-B13 construct scoring.

  1. {student}_expert_process_narrative.json (+ .jsonl)
  2. {student}_process_codes.json (+ tabular/)
  3. {student}_log_process_metadata.json
  4. {student}_video_analysis_bundle.json

Construct scoring artifacts live under trash/scoring_out_of_scope_2026-07-20/.

Usage:
  python scripts/build_video_analysis_bundle.py Ally Boris
  python scripts/build_video_analysis_bundle.py --all-2025
  python scripts/build_video_analysis_bundle.py --year 2026 Amy --session codap_21apr
  python scripts/build_video_analysis_bundle.py --year 2026 --all
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
OUT_2025 = REPO / "training_datasets" / "2025"
OUT_2026 = REPO / "training_datasets" / "2026"
def _gaps_path(cohort_year: int) -> Path:
    return REPO / f"data_sources_{cohort_year}" / f"rubric_gaps_{cohort_year}.json"


def _load_gaps(path: Path, cohort_year: int) -> tuple[dict[str, Any], bool]:
    """Load rubric gaps JSON. Returns (doc, loaded_ok).

    Logs an explicit WARNING when the file is missing so the absence is
    never silently swallowed. The caller propagates loaded_ok into the
    session_manifest data_availability block.
    """
    if path.is_file():
        return load_json(path), True
    LOGGER.warning(
        "WARNING: Rubric gaps file for %d not found at %s. "
        "Falling back to default empty schema. "
        "Run with --init-missing-gaps to scaffold the file.",
        cohort_year,
        path,
    )
    return {"gaps": [], "document_id": f"rubric_gaps_{cohort_year}_MISSING", "schema_version": "4.1"}, False


def _init_gaps_file(path: Path, cohort_year: int) -> None:
    """Write an empty rubric_gaps scaffold, borrowing schema from 2025 if available."""
    reference = _gaps_path(2025)
    if reference.is_file():
        base = load_json(reference)
    else:
        base = {"schema_version": "4.1", "gaps": []}

    scaffold: dict[str, Any] = {
        "document_id": f"rubric_gaps_{cohort_year}_codap_arbor",
        "schema_version": base.get("schema_version", "4.1"),
        "source_cohort": str(cohort_year),
        "derived_from": f"Behavioral observation transcripts for {cohort_year} cohort (scaffold — populate before use)",
        "note": "Auto-generated empty scaffold. Add gap entries before running analysis.",
        "gaps": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scaffold, indent=2, ensure_ascii=False))
    LOGGER.info("Scaffolded empty gaps file: %s", path)
BUNDLE_VERSION = "2.0-process-only"

_SKIP_DIRS = {"adjudication", "hf_export"}

LOGGER = logging.getLogger("video_analysis_bundle")

sys_path = Path(__file__).resolve().parent
import sys

if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

sys_path = Path(__file__).resolve().parent
import sys

if str(sys_path) not in sys.path:
    sys.path.insert(0, str(sys_path))

from export_process_codes_tables import export_student_tables
from video_process_codes import (
    build_process_codes_artifact,
    extract_verbatim_utterances,
    infer_process_code_hints,
)
from video_log_process_metadata import build_log_unavailable_metadata


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_alignment(path: Path) -> dict[str, Any]:
    """Load a gold_behavior_alignment file.

    Accepts both:
    - .v1.json  : single JSON object with {"alignments": [...]} structure
    - .v1.jsonl : one alignment row per line (produced by finalize_2026_gold_alignment.py)

    Always returns a dict with an "alignments" list so callers are uniform.
    """
    text = path.read_text(encoding="utf-8").strip()
    if path.suffix == ".jsonl" or "\n{" in text:
        rows = [json.loads(line) for line in text.splitlines() if line.strip()]
        return {"alignments": rows}
    doc = json.loads(text)
    if "alignments" not in doc and isinstance(doc, list):
        return {"alignments": doc}
    return doc


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def student_gaps(gaps_doc: dict[str, Any], student_id: str) -> list[dict[str, Any]]:
    out = []
    for g in gaps_doc.get("gaps") or []:
        if student_id in (g.get("students") or []):
            out.append({
                "gap_id": g.get("gap_id"),
                "label": g.get("label"),
                "why_not_covered": g.get("why_not_covered"),
            })
    return out


def episode_groups(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Group steps into narrative episodes by EXPLORE/TUNE/EVALUATE shifts."""
    if not steps:
        return []
    episodes: list[dict[str, Any]] = []
    cur_ids: list[int] = []
    cur_cat: str | None = None
    ep_i = 0

    def flush() -> None:
        nonlocal ep_i, cur_ids, cur_cat
        if not cur_ids:
            return
        episodes.append({
            "episode_id": f"ep_{ep_i:04d}",
            "step_indices": list(cur_ids),
            "dominant_category": cur_cat,
            "step_count": len(cur_ids),
        })
        ep_i += 1
        cur_ids = []

    for st in steps:
        cat = (st.get("labels") or {}).get("bilişsel_davranış_kategorisi", "EXPLORE")
        if cur_cat is None:
            cur_cat = cat
        if cat != cur_cat and cur_ids:
            flush()
            cur_cat = cat
        cur_ids.append(int(st["step_index"]))
    flush()
    return episodes


def build_expert_narrative(
    student_id: str,
    obs_doc: dict[str, Any],
    align_by_step: dict[int, dict[str, Any]],
    student_gap_list: list[dict[str, Any]],
    cohort_year: int = 2025,
) -> dict[str, Any]:
    _cohort_year = cohort_year
    steps = obs_doc.get("observation_steps") or []
    timeline: list[dict[str, Any]] = []

    for st in steps:
        si = int(st["step_index"])
        text = st.get("uzman_nitel_gözlemi") or ""
        align = align_by_step.get(si) or {}
        gold = align.get("gold") or {}
        silver = align.get("silver_video") or {}

        timeline.append({
            "step_index": si,
            "paragraph_index": st.get("paragraph_index"),
            "uzman_nitel_gözlemi": text,
            "verbatim_utterances": extract_verbatim_utterances(text),
            "labels": st.get("labels"),
            "sequence_pattern": st.get("sequence_pattern"),
            "ai_cft_evidence_justification": st.get("ai_cft_evidence_justification"),
            "visual_anchors": {
                "gold_screenshot": gold.get("expert_screenshot"),
                "docx_shot_index": st.get("docx_shot_index"),
                "silver_frame_id": silver.get("matched_frame_id"),
                "silver_frame_image": silver.get("matched_frame_image"),
                "timestamp_ms": silver.get("timestamp_ms"),
                "silver_confidence": silver.get("confidence"),
            },
            "process_code_hints": infer_process_code_hints(text),
            "behavior_codes_linked": gold.get("behavior_code_list") or [],
            "rubric_gap_flags": student_gap_list,
        })

    episodes = episode_groups(steps)
    step_to_ep = {}
    for ep in episodes:
        for si in ep["step_indices"]:
            step_to_ep[si] = ep["episode_id"]
    for row in timeline:
        row["episode_id"] = step_to_ep.get(row["step_index"])

    return {
        "$schema": "schema/video_expert_process_narrative.schema.json",
        "artifact": "expert_process_narrative",
        "student_id": student_id,
        "cohort_year": _cohort_year,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "analysis_docx": obs_doc.get("source_docx"),
            "video_file": obs_doc.get("video_source"),
            "parsed_at": obs_doc.get("parsed_at"),
        },
        "session_notes": (obs_doc.get("session_rubric") or {}).get("notes"),
        "timeline": timeline,
        "episodes": episodes,
        "docx_screenshot_count": obs_doc.get("docx_screenshot_count"),
        "interpretation_rule": (
            "This file preserves the full expert observation stream. "
            "process_code_hints are heuristic V-layer suggestions only. "
            "No proficiency scoring is attached to this artifact."
        ),
    }


def coverage_audit(
    obs_doc: dict[str, Any],
    align_doc: dict[str, Any],
    student_gap_list: list[dict[str, Any]],
) -> dict[str, Any]:
    steps = obs_doc.get("observation_steps") or []
    frames = align_doc.get("frame_behavior_coverage") or []
    alignments = align_doc.get("alignments") or []

    steps_with_shot = sum(1 for s in steps if s.get("docx_shot_index") is not None)
    steps_with_silver = sum(
        1
        for a in alignments
        if (a.get("silver_video") or {}).get("matched_frame_id")
        and (a.get("silver_video") or {}).get("confidence") not in ("none", "unavailable")
    )
    frames_inherited = sum(1 for f in frames if f.get("inherited_from_step") is not None)

    ts_list = [
        (a.get("silver_video") or {}).get("timestamp_ms")
        for a in alignments
        if (a.get("silver_video") or {}).get("timestamp_ms") is not None
    ]
    frame_ts = [f.get("timestamp_ms") for f in frames if f.get("timestamp_ms") is not None]
    video_end = max(frame_ts) if frame_ts else None
    silver_span = (max(ts_list) - min(ts_list)) if len(ts_list) >= 2 else 0
    low_silver = bool(
        video_end and video_end > 300_000 and silver_span < 0.30 * video_end
    )

    flags: list[str] = []
    if steps_with_shot < len(steps):
        flags.append(f"text_only_steps:{len(steps) - steps_with_shot}")
    if steps_with_silver < steps_with_shot:
        flags.append(f"weak_silver_steps:{steps_with_shot - steps_with_silver}")
    if low_silver:
        flags.append("low_silver_temporal_coverage")
    if student_gap_list:
        flags.append(f"rubric_gaps:{len(student_gap_list)}")
    frozen = any(
        (a.get("silver_video") or {}).get("confidence") == "unavailable"
        for a in alignments
    )
    if frozen:
        flags.append("frozen_or_still_video")

    return {
        "steps_total": len(steps),
        "steps_with_gold_shot": steps_with_shot,
        "steps_with_silver_anchor": steps_with_silver,
        "frames_total": len(frames),
        "frames_with_step_inheritance": frames_inherited,
        "video_duration_ms": video_end,
        "silver_timestamp_span_ms": silver_span if ts_list else None,
        "low_silver_coverage": low_silver,
        "gaps_flagged": flags,
        "rubric_gaps_for_student": student_gap_list,
    }


def process_student(
    student_id: str,
    gaps_doc: dict[str, Any],
    cohort_year: int = 2025,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Build all process-layer artifacts for one student (and session in v2).

    cohort_year=2025: v1 flat layout under training_datasets/2025/<student>/
    cohort_year=2026: v2 layered layout under training_datasets/2026/<student>/<session>/
    """
    if cohort_year == 2026:
        if not session_id:
            raise ValueError("--session SESSION_ID is required for --year 2026")
        layout = "v2"
        out_dir = OUT_2026 / student_id / session_id
        obs_path = out_dir / "intermediate" / f"{student_id}_observation_steps.json"
        _align_json = out_dir / "annotations" / f"{student_id}_gold_behavior_alignment.v1.json"
        _align_jsonl = out_dir / "annotations" / f"{student_id}_gold_behavior_alignment.v1.jsonl"
        align_path = _align_jsonl if _align_jsonl.is_file() else _align_json
        annotations_dir = out_dir / "annotations"
        metadata_dir = out_dir / "metadata"
    else:
        layout = "v1"
        out_dir = OUT_2025 / student_id
        obs_path = out_dir / f"{student_id}_observation_steps.json"
        align_path = out_dir / f"{student_id}_gold_behavior_alignment.json"
        annotations_dir = out_dir
        metadata_dir = out_dir

    if not obs_path.is_file():
        LOGGER.warning("[%s] observation_steps.json not found — skipping (blocked_missing_raw_data)", student_id)
        return {
            "student_id": student_id,
            "session_id": session_id,
            "status": "blocked_missing_raw_data",
            "data_availability": {
                "observation_steps": False,
                "gold_alignment": align_path.is_file(),
                "status": "blocked_missing_raw_data",
            },
        }
    if not align_path.is_file():
        LOGGER.warning("[%s] gold_behavior_alignment not found — skipping (blocked_missing_raw_data)", student_id)
        return {
            "student_id": student_id,
            "session_id": session_id,
            "status": "blocked_missing_raw_data",
            "data_availability": {
                "observation_steps": True,
                "gold_alignment": False,
                "status": "blocked_missing_raw_data",
            },
        }

    obs_doc = load_json(obs_path)
    align_doc = load_alignment(align_path)
    align_by_step = {
        int((a.get("metadata") or {}).get("observation_step_index")): a
        for a in (align_doc.get("alignments") or [])
        if (a.get("metadata") or {}).get("observation_step_index") is not None
    }

    gap_list = student_gaps(gaps_doc, student_id)
    narrative = build_expert_narrative(
        student_id, obs_doc, align_by_step, gap_list, cohort_year=cohort_year
    )
    audit = coverage_audit(obs_doc, align_doc, gap_list)

    session_rubric = obs_doc.get("session_rubric") or {}
    audio_available = session_rubric.get("audio")

    log_meta = build_log_unavailable_metadata(
        student_id,
        cohort_year,
        audio_available=audio_available,
        video_duration_ms=audit.get("video_duration_ms"),
    )
    gap_ids = [g["gap_id"] for g in gap_list if g.get("gap_id")]
    process_codes = build_process_codes_artifact(
        student_id,
        cohort_year,
        narrative["episodes"],
        narrative["timeline"],
        log_metadata=log_meta,
        rubric_gap_ids=gap_ids,
    )
    audit["log_available"] = log_meta["log_available"]
    audit["log_video_sync_status"] = (log_meta.get("video_log_sync") or {}).get("status")

    if layout == "v2":
        narrative_path = annotations_dir / f"{student_id}_expert_process_narrative.v1.jsonl"
        process_codes_path = annotations_dir / f"{student_id}_process_codes.v1.json"
        log_meta_path = metadata_dir / f"{student_id}_log_process_metadata.json"
        bundle_path = metadata_dir / f"{student_id}_video_analysis_bundle.json"

        write_jsonl(narrative_path, narrative["timeline"])
        write_json(process_codes_path, process_codes)
        write_json(log_meta_path, log_meta)

        tables_manifest = export_student_tables(
            student_id, out_dir, write_parquet_files=True, layout="v2"
        )
        tab_key = "parquet"
        tab_prefix = "exports/tabular"
        bundle_artifacts = {
            "expert_process_narrative": f"annotations/{narrative_path.name}",
            "process_codes": f"annotations/{process_codes_path.name}",
            "log_process_metadata": f"metadata/{log_meta_path.name}",
            "gold_behavior_alignment": f"annotations/{student_id}_gold_behavior_alignment.v1.json",
            "observation_steps": f"intermediate/{student_id}_observation_steps.json",
            "tables_manifest": f"metadata/{student_id}_tables_manifest.json",
        }
        bundle_tabular = {
            name: f"{tab_prefix}/{student_id}_{name}.parquet"
            for name in ("episodes", "episode_process_codes", "session_ml_features")
        }
        if session_id:
            bundle_extra = {"session_id": session_id}
        else:
            bundle_extra = {}
    else:
        narrative_path = out_dir / f"{student_id}_expert_process_narrative.json"
        process_codes_path = out_dir / f"{student_id}_process_codes.json"
        log_meta_path = out_dir / f"{student_id}_log_process_metadata.json"
        bundle_path = out_dir / f"{student_id}_video_analysis_bundle.json"

        write_json(narrative_path, narrative)
        write_json(process_codes_path, process_codes)
        write_json(log_meta_path, log_meta)
        write_jsonl(out_dir / f"{student_id}_expert_process_narrative.jsonl", narrative["timeline"])

        tables_manifest = export_student_tables(student_id, out_dir, layout="v1")
        bundle_artifacts = {
            "expert_process_narrative": narrative_path.name,
            "expert_process_narrative_jsonl": f"{student_id}_expert_process_narrative.jsonl",
            "process_codes": process_codes_path.name,
            "log_process_metadata": log_meta_path.name,
            "gold_behavior_alignment": align_path.name,
            "observation_steps_source": obs_path.name,
            "process_codes_tables_manifest": f"tabular/{student_id}_process_codes_tables_manifest.json",
        }
        bundle_tabular = {
            "episodes": tables_manifest["tables"]["episodes"]["jsonl"],
            "episode_process_codes": tables_manifest["tables"]["episode_process_codes"]["jsonl"],
            "session_ml_features": tables_manifest["tables"]["session_ml_features"]["jsonl"],
        }
        bundle_extra = {}

    bundle = {
        "$schema": "schema/video_analysis_bundle.schema.json",
        "student_id": student_id,
        "cohort_year": cohort_year,
        "bundle_version": BUNDLE_VERSION,
        "layout_version": layout,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "process_pipeline_methods_only",
        "scoring_out_of_scope": True,
        **bundle_extra,
        "artifacts": bundle_artifacts,
        "tabular_exports": bundle_tabular,
        "measurement_layers": {
            "process_narrative": "Full uzman_nitel_gözlemi timeline (qualitative)",
            "process_codes": "Episode-level V1-V8 process codes (non-scored)",
            "log_metadata": "Task-4 chronology and log-only variables (null when no CSV)",
        },
        "coverage_audit": audit,
        "dual_artifact_model": {
            "process_layer": "Expert narrative + episode V-codes",
            "log_layer": "Objective event chronology when CODAP CSV available",
            "scoring_layer": "OUT OF SCOPE — see trash/scoring_out_of_scope_2026-07-20/",
            "reference": "framework/VIDEO_PROCESS_CODEBOOK_v1.md",
        },
    }
    write_json(bundle_path, bundle)

    label = f"{student_id}/{session_id}" if session_id else student_id
    LOGGER.info(
        "[%s] process-bundle ok — steps=%d narrative=%d episodes=%d log=%s gaps=%s",
        label,
        audit["steps_total"],
        len(narrative["timeline"]),
        len(process_codes["episodes"]),
        log_meta["log_available"],
        audit["gaps_flagged"],
    )
    return {
        "student_id": student_id,
        "session_id": session_id,
        "status": "ok",
        "bundle": str(bundle_path),
        "coverage_audit": audit,
    }


def list_2025_students() -> list[str]:
    if not OUT_2025.is_dir():
        return []
    return sorted(
        p.name
        for p in OUT_2025.iterdir()
        if p.is_dir()
        and p.name not in _SKIP_DIRS
        and (p / f"{p.name}_observation_steps.json").is_file()
    )


def list_2026_sessions() -> list[tuple[str, str]]:
    """Return (student_id, session_id) pairs that have observation_steps.json."""
    pairs: list[tuple[str, str]] = []
    if not OUT_2026.is_dir():
        return pairs
    for student_dir in sorted(OUT_2026.iterdir()):
        if not student_dir.is_dir() or student_dir.name in _SKIP_DIRS:
            continue
        for session_dir in sorted(student_dir.iterdir()):
            if not session_dir.is_dir() or session_dir.name == "metadata":
                continue
            obs = session_dir / "intermediate" / f"{student_dir.name}_observation_steps.json"
            if obs.is_file():
                pairs.append((student_dir.name, session_dir.name))
    return pairs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Build process-only video analysis bundles (no scoring)")
    ap.add_argument("students", nargs="*", help="Student IDs")
    ap.add_argument("--year", type=int, default=2025, choices=[2025, 2026],
                    help="Cohort year (default: 2025)")
    ap.add_argument("--session", metavar="SESSION_ID",
                    help="Session to process, e.g. codap_21apr (required for --year 2026 single student)")
    ap.add_argument("--all", dest="all_cohort", action="store_true",
                    help="Process all students/sessions in the cohort")
    ap.add_argument("--all-2025", action="store_true",
                    help="Shorthand for --year 2025 --all (backward compat)")
    ap.add_argument(
        "--init-missing-gaps",
        action="store_true",
        help=(
            "If rubric_gaps_{year}.json is absent, create an empty scaffold "
            "using the 2025 file's schema and exit"
        ),
    )
    args = ap.parse_args()

    if args.all_2025:
        args.year = 2025
        args.all_cohort = True

    gaps_path = _gaps_path(args.year)

    if args.init_missing_gaps and not gaps_path.is_file():
        _init_gaps_file(gaps_path, args.year)
        return

    gaps_doc, rubric_gaps_loaded = _load_gaps(gaps_path, args.year)

    ok = 0
    summaries: list[dict[str, Any]] = []

    if args.year == 2025:
        students = list_2025_students() if args.all_cohort else list(args.students)
        if not students:
            ap.error("Provide student IDs, --all, or --all-2025")
        for sid in students:
            try:
                result = process_student(sid, gaps_doc, cohort_year=2025)
                summaries.append(result)
                ok += 1
            except Exception as exc:
                LOGGER.error("[%s] failed: %s", sid, exc)
                summaries.append({"student_id": sid, "status": "error", "error": str(exc)})

        if (args.all_cohort or args.all_2025) and summaries:
            cohort_path = OUT_2025 / "cohort_video_analysis_bundle_summary.json"
            write_json(cohort_path, {
                "$schema": "schema/video_analysis_bundle.schema.json",
                "cohort_year": 2025,
                "bundle_version": BUNDLE_VERSION,
                "layout_version": "v1",
                "scope": "process_pipeline_methods_only",
                "scoring_out_of_scope": True,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "students": summaries,
                "artifact_layout": {
                    "expert_process_narrative": "<id>_expert_process_narrative.json",
                    "process_codes": "<id>_process_codes.json",
                    "log_process_metadata": "<id>_log_process_metadata.json",
                    "bundle_manifest": "<id>_video_analysis_bundle.json",
                },
                "scoring_quarantine": "trash/scoring_out_of_scope_2026-07-20/",
            })
            LOGGER.info("Cohort summary → %s", cohort_path)
        total = len(students)

    else:  # 2026
        if args.all_cohort:
            pairs = list_2026_sessions()
        elif args.students:
            pairs = []
            for sid in args.students:
                student_dir = OUT_2026 / sid
                if not student_dir.is_dir():
                    LOGGER.error("Student dir not found: %s", student_dir)
                    continue
                if args.session:
                    pairs.append((sid, args.session))
                else:
                    for sess_dir in sorted(student_dir.iterdir()):
                        if sess_dir.is_dir() and sess_dir.name != "metadata":
                            pairs.append((sid, sess_dir.name))
        else:
            ap.error("Provide student IDs (with optional --session) or --all")
            pairs = []

        for sid, session_id in pairs:
            try:
                result = process_student(sid, gaps_doc, cohort_year=2026, session_id=session_id)
                summaries.append(result)
                ok += 1
            except Exception as exc:
                LOGGER.error("[%s/%s] failed: %s", sid, session_id, exc)
                summaries.append({
                    "student_id": sid, "session_id": session_id,
                    "status": "error", "error": str(exc),
                })

        if args.all_cohort and summaries:
            cohort_path = OUT_2026 / "cohort_video_analysis_bundle_summary.json"
            write_json(cohort_path, {
                "$schema": "schema/video_analysis_bundle.schema.json",
                "cohort_year": 2026,
                "bundle_version": BUNDLE_VERSION,
                "layout_version": "v2",
                "scope": "process_pipeline_methods_only",
                "scoring_out_of_scope": True,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "sessions": summaries,
                "artifact_layout": {
                    "expert_process_narrative": "<student>/<session>/annotations/<id>_expert_process_narrative.v1.jsonl",
                    "process_codes": "<student>/<session>/annotations/<id>_process_codes.v1.json",
                    "log_process_metadata": "<student>/<session>/metadata/<id>_log_process_metadata.json",
                    "bundle_manifest": "<student>/<session>/metadata/<id>_video_analysis_bundle.json",
                },
                "scoring_quarantine": "trash/scoring_out_of_scope_2026-07-20/",
            })
            LOGGER.info("Cohort summary → %s", cohort_path)
        total = len(pairs)

    LOGGER.info("Done %d/%d", ok, total)

    blocked = [s for s in summaries if s.get("status") == "blocked_missing_raw_data"]
    errors = [s for s in summaries if s.get("status") == "error"]
    if args.all_cohort or args.all_2025:
        health = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "cohort_year": args.year,
            "total": total,
            "complete": ok,
            "blocked_missing_raw_data": len(blocked),
            "errors": len(errors),
            "data_availability": {
                "rubric_gaps_loaded": rubric_gaps_loaded,
                "rubric_gaps_path": str(gaps_path),
            },
            "blocked_students": [
                {"student_id": s.get("student_id"), "session_id": s.get("session_id"),
                 "data_availability": s.get("data_availability")}
                for s in blocked
            ],
        }
        health_path = REPO / "pipeline_data_health.json"
        write_json(health_path, health)
        LOGGER.info("Health report → %s", health_path)


if __name__ == "__main__":
    main()
