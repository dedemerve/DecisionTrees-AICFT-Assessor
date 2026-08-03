#!/usr/bin/env python3
"""Multimodal cognitive assessor for CODAP/Arbor decision-tree screen recordings.

Ingests {Student}_video_extraction_manifest.json + labeled transcript, scores three
behavioral dimensions (0–3), and emits a standardized evaluation payload.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUDIO_ROOT = REPO_ROOT / "data_sources_2026" / "codap_arbor_21april_audio"
DEFAULT_RUBRIC = REPO_ROOT / "rubrics" / "MMLA_DT_CODAP_rubric.json"


def normalize(text: str) -> str:
    return text.casefold().replace("â", "a").replace("î", "i").replace("û", "u")


def marker_hits(text: str, markers: list[str]) -> int:
    norm = normalize(text)
    return sum(1 for m in markers if normalize(m) in norm)


def clamp_score(value: float, lo: float = 0.0, hi: float = 3.0) -> float:
    return round(max(lo, min(hi, value)) * 2) / 2


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_transcript_path(student_dir: Path, student_id: str) -> Path | None:
    for name in (
        f"{student_id}_transcript_labeled.json",
        f"{student_id}_transcript_merged.json",
        f"{student_id}_transcript.json",
    ):
        candidate = student_dir / name
        if candidate.is_file():
            return candidate
    return None


def transcript_by_id(segments: list[dict]) -> dict[int, dict]:
    return {int(s["id"]): s for s in segments if "id" in s}


def segment_at_time(segments: list[dict], timestamp_s: float) -> dict | None:
    for seg in segments:
        start = float(seg.get("start", 0))
        end = float(seg.get("end", 0))
        if start <= timestamp_s <= end:
            return seg
    return None


@dataclass
class TimelineEntry:
    timestamp_seconds: float
    frame_id: str | None
    trigger: str
    speaker_role: str | None
    transcript_id: int | None
    text: str
    speaker_confidence: float
    high_value_interaction_zone: bool
    pixel_change_percentage: float | None = None


@dataclass
class DimensionScores:
    conceptual: float = 0.0
    software: float = 0.0
    argumentation: float = 0.0
    confidence: float = 0.0
    critical_moments: list[dict[str, Any]] = field(default_factory=list)
    diagnostics: dict[str, Any] = field(default_factory=dict)


def build_timeline(manifest: dict[str, Any], transcript_segments: list[dict]) -> list[TimelineEntry]:
    by_id = transcript_by_id(transcript_segments)
    entries: list[TimelineEntry] = []

    for seg in manifest.get("segments", []):
        tid = seg.get("associated_transcript_id")
        transcript = by_id.get(int(tid)) if tid is not None else None
        if transcript is None and seg.get("source_timestamp_seconds") is not None:
            transcript = segment_at_time(transcript_segments, float(seg["source_timestamp_seconds"]))

        text = str((transcript or {}).get("text", "")).strip()
        role = seg.get("associated_speaker_role") or (transcript or {}).get("speaker_role")
        conf = float((transcript or {}).get("speaker_confidence", 0.5) or 0.5)

        entries.append(
            TimelineEntry(
                timestamp_seconds=float(seg.get("source_timestamp_seconds", 0)),
                frame_id=seg.get("frame_id"),
                trigger=str(seg.get("extraction_trigger_reason", "unknown")),
                speaker_role=role,
                transcript_id=int(tid) if tid is not None else None,
                text=text,
                speaker_confidence=conf,
                high_value_interaction_zone=bool(seg.get("high_value_interaction_zone")),
                pixel_change_percentage=seg.get("pixel_change_percentage"),
            )
        )

    entries.sort(key=lambda e: e.timestamp_seconds)
    return entries


def student_segments(transcript_segments: list[dict], student_id: str) -> list[dict]:
    out: list[dict] = []
    for seg in transcript_segments:
        role = seg.get("speaker_role")
        focal = seg.get("focal_pt_student_id")
        if role == "student" or (focal and str(focal) == student_id):
            out.append(seg)
    return out


def score_conceptual(student_speech: list[dict], rubric: dict[str, Any]) -> tuple[float, list[dict], dict]:
    cfg = rubric["dimensions"]["conceptual_understanding"]
    concept_hits = 0
    strategic_hits = 0
    trial_hits = 0
    moments: list[tuple[float, dict]] = []

    for seg in student_speech:
        text = str(seg.get("text", ""))
        if not text:
            continue
        c = marker_hits(text, cfg["concept_markers"])
        s = marker_hits(text, cfg["strategic_markers"])
        t = marker_hits(text, cfg["trial_error_markers"])
        concept_hits += c
        strategic_hits += s
        trial_hits += t
        if c or s:
            moments.append(
                (
                    float(seg.get("start", 0)),
                    {
                        "timestamp_seconds": round(float(seg.get("start", 0)), 2),
                        "frame_reference": None,
                        "trigger": "student_speech_concept",
                        "behavioral_deduction": (
                            f"Student articulated decision-tree concepts ({c} concept, {s} strategic markers): "
                            f"{text[:120]}"
                        ),
                        "score_delta": 0.15 * c + 0.2 * s,
                    },
                )
            )

    n = max(len(student_speech), 1)
    concept_density = math.sqrt(concept_hits / n)
    strategic_ratio = min(1.0, strategic_hits / max(concept_hits + trial_hits, 1))

    raw = 0.5 + concept_density * 2.0 + strategic_ratio * 1.0 - min(trial_hits, 12) * 0.06
    score = clamp_score(raw)

    moments.sort(key=lambda m: m[1]["score_delta"], reverse=True)
    return score, [m[1] for m in moments[:5]], {
        "concept_hits": concept_hits,
        "strategic_hits": strategic_hits,
        "trial_hits": trial_hits,
        "student_segment_count": len(student_speech),
    }


def score_software(
    timeline: list[TimelineEntry],
    student_speech: list[dict],
    rubric: dict[str, Any],
) -> tuple[float, list[dict], dict]:
    cfg = rubric["dimensions"]["software_interaction"]
    help_hits = 0
    independent_hits = 0
    motion_frames = 0
    motion_student = 0
    moments: list[tuple[float, dict]] = []

    for seg in student_speech:
        text = str(seg.get("text", ""))
        h = marker_hits(text, cfg["help_request_markers"])
        i = marker_hits(text, cfg["independent_recovery_markers"])
        help_hits += h
        independent_hits += i
        if h:
            moments.append(
                (
                    float(seg.get("start", 0)),
                    {
                        "timestamp_seconds": round(float(seg.get("start", 0)), 2),
                        "frame_reference": None,
                        "trigger": "teacher_help_request",
                        "behavioral_deduction": f"Student requested teacher assistance: {text[:120]}",
                        "score_delta": -0.25,
                    },
                )
            )
        if i:
            moments.append(
                (
                    float(seg.get("start", 0)),
                    {
                        "timestamp_seconds": round(float(seg.get("start", 0)), 2),
                        "frame_reference": None,
                        "trigger": "independent_recovery_speech",
                        "behavioral_deduction": f"Student reported independent error recovery: {text[:120]}",
                        "score_delta": 0.35,
                    },
                )
            )

    for entry in timeline:
        if entry.trigger in ("motion_threshold_exceeded", "motion_only_fallback"):
            motion_frames += 1
            if entry.speaker_role == "student" or entry.high_value_interaction_zone:
                motion_student += 1
                moments.append(
                    (
                        entry.timestamp_seconds,
                        {
                            "timestamp_seconds": round(entry.timestamp_seconds, 2),
                            "frame_reference": entry.frame_id,
                            "trigger": entry.trigger,
                            "behavioral_deduction": (
                                "Student-timed UI interaction captured via motion keyframe "
                                f"(Δ={entry.pixel_change_percentage or 'n/a'}%)."
                            ),
                            "score_delta": 0.2,
                        },
                    )
                )

    n = max(len(student_speech), 1)
    help_rate = help_hits / n
    independent_rate = independent_hits / n
    motion_ratio = motion_student / max(motion_frames, 1) if motion_frames else 0.0

    raw = 1.5 + independent_rate * 2.0 - help_rate * 1.8 + motion_ratio * 0.8 + min(motion_frames, 20) * 0.02
    score = clamp_score(raw)

    moments.sort(key=lambda m: abs(m[1]["score_delta"]), reverse=True)
    return score, [m[1] for m in moments[:5]], {
        "help_request_hits": help_hits,
        "independent_recovery_hits": independent_hits,
        "motion_frames": motion_frames,
        "motion_student_aligned": motion_student,
    }


def score_argumentation(student_speech: list[dict], rubric: dict[str, Any]) -> tuple[float, list[dict], dict]:
    cfg = rubric["dimensions"]["argumentation"]
    justification_hits = 0
    bare_hits = 0
    substantive = 0
    conf_weighted_words = 0.0
    moments: list[tuple[float, dict]] = []

    for seg in student_speech:
        text = str(seg.get("text", ""))
        if not text:
            continue
        words = len(re.findall(r"\w+", text, flags=re.UNICODE))
        conf = float(seg.get("speaker_confidence", 0.5) or 0.5)
        conf_weighted_words += words * conf

        j = marker_hits(text, cfg["justification_markers"])
        b = marker_hits(text, cfg["bare_action_markers"])
        justification_hits += j
        bare_hits += b
        if words >= cfg["min_words_substantive"]:
            substantive += 1

        if j:
            moments.append(
                (
                    float(seg.get("start", 0)),
                    {
                        "timestamp_seconds": round(float(seg.get("start", 0)), 2),
                        "frame_reference": None,
                        "trigger": "student_justification",
                        "behavioral_deduction": f"Student provided causal/justificatory language: {text[:120]}",
                        "score_delta": 0.3 * j,
                    },
                )
            )
        elif b and words <= 6:
            moments.append(
                (
                    float(seg.get("start", 0)),
                    {
                        "timestamp_seconds": round(float(seg.get("start", 0)), 2),
                        "frame_reference": None,
                        "trigger": "bare_action_acknowledgment",
                        "behavioral_deduction": f"Minimal procedural acknowledgment without depth: {text[:120]}",
                        "score_delta": -0.1,
                    },
                )
            )

    n = max(len(student_speech), 1)
    justify_rate = justification_hits / n
    bare_rate = bare_hits / n
    substantive_rate = substantive / n
    avg_conf_words = conf_weighted_words / n

    raw = 0.3 + justify_rate * 2.2 + substantive_rate * 0.9 + min(avg_conf_words / 20.0, 1.0) - bare_rate * 0.6
    score = clamp_score(raw)

    moments.sort(key=lambda m: m[1]["score_delta"], reverse=True)
    return score, [m[1] for m in moments[:5]], {
        "justification_hits": justification_hits,
        "bare_action_hits": bare_hits,
        "substantive_segments": substantive,
        "avg_confidence_weighted_words": round(avg_conf_words, 2),
    }


def global_confidence_index(
    *,
    modality_status: str,
    manifest: dict[str, Any],
    student_speech: list[dict],
    rubric: dict[str, Any],
) -> float:
    weights = rubric["confidence_weights"]
    base = weights.get(modality_status, 0.5)

    modalities = manifest.get("modalities", {})
    hybrid_count = int(modalities.get("hybrid_segment_count", 0) or 0)
    extracted = int(manifest.get("summary", {}).get("total_frames_extracted", 0) or 0)
    coverage = extracted / hybrid_count if hybrid_count else (1.0 if extracted else 0.0)
    coverage = min(coverage, 1.0)
    coverage_penalty = (1.0 - coverage) * weights["partial_frame_coverage_penalty_per_missing_ratio"]

    confs = [float(s.get("speaker_confidence", 0.5) or 0.5) for s in student_speech]
    avg_conf = sum(confs) / len(confs) if confs else 0.4

    value = base * 0.45 + coverage * 0.35 + avg_conf * 0.2 - coverage_penalty
    return round(max(0.0, min(1.0, value)), 3)


def compute_error_bounds(
    scores: dict[str, float],
    rubric: dict[str, Any],
) -> dict[str, float]:
    baselines = rubric["grading_baselines"]
    mae_vals: list[float] = []
    rmse_vals: list[float] = []
    for key, baseline in baselines.items():
        dim_key = key.replace("_score", "")
        actual = scores.get(dim_key, scores.get(key.replace("_score", ""), 0))
        if dim_key == "conceptual":
            actual = scores["conceptual"]
        elif dim_key == "software_interaction":
            actual = scores["software"]
        elif dim_key == "argumentation":
            actual = scores["argumentation"]
        mean = baseline["mean"]
        diff = abs(actual - mean)
        mae_vals.append(diff)
        rmse_vals.append(diff**2)
    mae = sum(mae_vals) / len(mae_vals) if mae_vals else 0.0
    rmse = math.sqrt(sum(rmse_vals) / len(rmse_vals)) if rmse_vals else 0.0
    return {"mae_vs_baseline": round(mae, 3), "rmse_vs_baseline": round(rmse, 3)}


def assess_student(
    student_dir: Path,
    student_id: str,
    rubric: dict[str, Any],
) -> dict[str, Any]:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    manifest = load_json(manifest_path)
    transcript_path = resolve_transcript_path(student_dir, student_id)
    if not transcript_path:
        raise FileNotFoundError(f"Missing transcript for {student_id} in {student_dir}")

    transcript_doc = load_json(transcript_path)
    transcript_segments = transcript_doc.get("segments", transcript_doc if isinstance(transcript_doc, list) else [])
    if not isinstance(transcript_segments, list):
        raise ValueError(f"Unexpected transcript structure in {transcript_path}")

    timeline = build_timeline(manifest, transcript_segments)
    speech = student_segments(transcript_segments, student_id)

    c_score, c_moments, c_diag = score_conceptual(speech, rubric)
    s_score, s_moments, s_diag = score_software(timeline, speech, rubric)
    a_score, a_moments, a_diag = score_argumentation(speech, rubric)

    extraction_mode = manifest.get("extraction_mode", "unknown")
    if extraction_mode == "full_multimodal":
        modality_status = "full_multimodal_sync"
    elif extraction_mode == "motion_only_fallback":
        modality_status = "motion_only_fallback"
    else:
        modality_status = extraction_mode

    scores = {"conceptual": c_score, "software": s_score, "argumentation": a_score}
    gci = global_confidence_index(
        modality_status=modality_status,
        manifest=manifest,
        student_speech=speech,
        rubric=rubric,
    )

    frame_by_ts = {
        round(e.timestamp_seconds, 2): e.frame_id
        for e in timeline
        if e.frame_id
    }

    all_moments = c_moments + s_moments + a_moments
    for m in all_moments:
        m.pop("score_delta", None)
        if not m.get("frame_reference"):
            m["frame_reference"] = frame_by_ts.get(m["timestamp_seconds"])
    all_moments.sort(key=lambda m: m["timestamp_seconds"])
    # Deduplicate near-identical timestamps, keep strongest behavioral diversity
    seen_ts: set[float] = set()
    critical: list[dict] = []
    for m in sorted(all_moments, key=lambda x: -len(x.get("behavioral_deduction", ""))):
        ts = m["timestamp_seconds"]
        if ts in seen_ts:
            continue
        seen_ts.add(ts)
        critical.append(m)
        if len(critical) >= 8:
            break
    critical.sort(key=lambda m: m["timestamp_seconds"])

    bounds = compute_error_bounds(scores, rubric)
    hybrid_count = int(manifest.get("modalities", {}).get("hybrid_segment_count", 0) or 0)
    extracted = int(manifest.get("summary", {}).get("total_frames_extracted", 0) or 0)

    return {
        "student_id": student_id,
        "modality_status": modality_status,
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "manifest": str(manifest_path.relative_to(REPO_ROOT)),
            "transcript": str(transcript_path.relative_to(REPO_ROOT)),
            "timeline_entries": len(timeline),
            "student_speech_segments": len(speech),
            "frame_coverage_ratio": round(extracted / hybrid_count, 4) if hybrid_count else None,
        },
        "evaluation_metrics": {
            "conceptual_score": c_score,
            "software_interaction_score": s_score,
            "argumentation_score": a_score,
            "global_confidence_index": gci,
        },
        "dimension_diagnostics": {
            "conceptual": c_diag,
            "software_interaction": s_diag,
            "argumentation": a_diag,
            "baseline_error_bounds": bounds,
        },
        "critical_interaction_moments": critical,
        "quantitative_summary": (
            f"Processed {len(timeline)} timeline entries and {len(speech)} student speech segments. "
            f"Frame coverage {extracted}/{hybrid_count or 'n/a'}. "
            f"MAE={bounds['mae_vs_baseline']:.3f}, RMSE={bounds['rmse_vs_baseline']:.3f} "
            "mapped against MMLA_DT_CODAP standard grading baselines."
        ),
    }


def discover_students(audio_root: Path) -> list[str]:
    students: list[str] = []
    for child in sorted(audio_root.iterdir()):
        if not child.is_dir():
            continue
        sid = child.name
        if (child / f"{sid}_video_extraction_manifest.json").is_file():
            students.append(sid)
    return students


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Multimodal cognitive assessor (CODAP DT sessions)")
    parser.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    parser.add_argument("--student", action="append", dest="students", help="Student pseudonym (repeatable)")
    parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    parser.add_argument("--output-dir", type=Path, help="Override output directory (default: student audio dir)")
    parser.add_argument("--stdout", action="store_true", help="Print JSON to stdout instead of writing file")
    args = parser.parse_args(argv)

    rubric = load_json(args.rubric)
    audio_root = args.audio_root.resolve()
    targets = args.students or discover_students(audio_root)
    if not targets:
        print("No students with video extraction manifests found.", file=sys.stderr)
        return 1

    exit_code = 0
    for student_id in targets:
        student_dir = audio_root / student_id
        try:
            payload = assess_student(student_dir, student_id, rubric)
        except Exception as exc:
            print(f"[ERROR] {student_id}: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        if args.stdout:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            continue

        out_dir = (args.output_dir or student_dir).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{student_id}_mmla_cognitive_assessment.json"
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
