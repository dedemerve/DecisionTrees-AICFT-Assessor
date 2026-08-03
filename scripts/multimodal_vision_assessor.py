#!/usr/bin/env python3
"""Multimodal vision assessor for CODAP/Arbor decision-tree screen recordings.

Bridges rule-based lexical scoring (multimodal_cognitive_assessor.py) with a
Multimodal LLM that audits synchronized keyframe JPEGs against student speech.

Pipeline stages:
  1. Contextual aggregation + modality-driven weight matrix
  2. Vision API payload construction (image + conversational scaffolding)
  3. Multi-axial semantic evaluation via structured vision prompt
  4. Consolidated cognitive schema output with reliability vs lexical baseline
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import math
import os
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from multimodal_cognitive_assessor import (  # noqa: E402
    DEFAULT_AUDIO_ROOT,
    DEFAULT_RUBRIC,
    build_timeline,
    load_json,
    marker_hits,
    resolve_transcript_path,
)
from multimodal_cognitive_assessor import TimelineEntry  # noqa: E402
from speaker_role import TEACHER_PATTERNS, pattern_score  # noqa: E402

LOGGER = logging.getLogger("multimodal_vision_assessor")

SCORING_ENGINE_LABEL = "Claude-3.5-Sonnet-Vision-v1"
DEFAULT_MODEL_ANTHROPIC = "claude-sonnet-5"
DEFAULT_MODEL_OPENAI = "gpt-4o"
CODAP_FRAME_SYSTEM_PROMPT = REPO_ROOT / "prompts" / "MMLA_CODAP_video_system_prompt.md"

# Legacy 3-dimension audit prompt. For full per-frame LO3 rubric analysis see
# scripts/codap_frame_analyzer.py + prompts/MMLA_CODAP_video_system_prompt.md

WEIGHTS_FULL_MULTIMODAL = {
    "conceptual": 0.35,
    "software": 0.35,
    "argumentation": 0.30,
}
WEIGHTS_MOTION_ONLY = {
    "conceptual": 0.50,
    "software": 0.50,
    "argumentation": 0.0,
}

VISION_SYSTEM_PROMPT = """You are a Principal AI Scientist auditing pre-service teacher performance on a CODAP/Arbor decision-tree classification task.

You receive:
1. A synchronized screen-recording keyframe (CODAP/Arbor UI).
2. Temporal dialogue context (preceding teacher remark, focal student utterance, succeeding segment).

Score ONLY what is empirically verifiable from the image + dialogue. Ignore classroom background noise.

Dimensions (each 0.0–3.0 in 0.25 increments):
- conceptual_score: Does the visible CODAP/Arbor state (tree nodes, attribute splits, thresholds, case tables, axes) support the student's verbal claim about classification or decision boundaries? Do NOT reward empty confidence markers ("eminiz hocam") without visual evidence of meaningful tree manipulation.
- software_interaction_score: Does the frame show strategic exploratory behavior (case tables, dragging attributes, pruning nodes, adjusting numeric split sliders) vs being trapped in an interface loop or idle screen?
- argumentation_score: Is the student's assertion grounded in empirical on-screen evidence? Null when no student speech is provided.

Return ONLY valid JSON (no markdown fences):
{
  "conceptual_score": <float>,
  "software_interaction_score": <float>,
  "argumentation_score": <float|null>,
  "vision_verification": {
    "visual_evidence_found": <bool>,
    "screen_state_analysis": "<concise description of CODAP/Arbor UI state>",
    "cognitive_validity": "<Valid|Partial|Invalid>. <one sentence linking speech to screen>"
  }
}"""


@dataclass
class VisionEvent:
    timestamp_seconds: float
    frame_id: str
    frame_path: Path
    trigger: str
    transcript_text: str
    speaker_role: str | None
    preceding_teacher: str
    succeeding_segment: str
    pixel_change_percentage: float | None = None
    selection_score: float = 0.0


@dataclass
class VisionEvaluation:
    conceptual_score: float
    software_interaction_score: float
    argumentation_score: float | None
    vision_verification: dict[str, Any]
    raw_response: dict[str, Any] = field(default_factory=dict)


def clamp_score(value: float, lo: float = 0.0, hi: float = 3.0) -> float:
    return round(max(lo, min(hi, value)) * 4) / 4


def modality_status_from_manifest(manifest: dict[str, Any]) -> str:
    mode = manifest.get("extraction_mode", "unknown")
    if mode == "full_multimodal":
        return "full_multimodal_sync"
    if mode == "motion_only_fallback":
        return "motion_only_fallback"
    return str(mode)


def frames_dir_from_manifest(manifest: dict[str, Any], student_dir: Path, student_id: str) -> Path:
    path_resolution = manifest.get("path_resolution", {})
    rel = path_resolution.get("output_frames_dir")
    if rel:
        candidate = (REPO_ROOT / rel).resolve()
        if candidate.is_dir():
            return candidate
    default = student_dir / f"{student_id}_frames"
    return default.resolve()


def transcript_segments_list(transcript_doc: dict[str, Any]) -> list[dict]:
    segments = transcript_doc.get("segments", transcript_doc if isinstance(transcript_doc, list) else [])
    if not isinstance(segments, list):
        raise ValueError("Transcript document missing segments list")
    return segments


def neighbor_context(
    segments: list[dict],
    timestamp_s: float,
    focal_text: str,
) -> tuple[str, str]:
    """Return (preceding_teacher_remark, succeeding_segment_text)."""
    ordered = sorted(segments, key=lambda s: float(s.get("start", 0)))
    preceding_teacher = ""
    succeeding = ""

    for i, seg in enumerate(ordered):
        start = float(seg.get("start", 0))
        if start >= timestamp_s:
            if i > 0:
                for j in range(i - 1, -1, -1):
                    if ordered[j].get("speaker_role") == "teacher":
                        preceding_teacher = str(ordered[j].get("text", "")).strip()
                        break
            for j in range(i, len(ordered)):
                nxt = str(ordered[j].get("text", "")).strip()
                if nxt and nxt != focal_text:
                    succeeding = nxt
                    break
            break
    else:
        for seg in reversed(ordered):
            if float(seg.get("start", 0)) < timestamp_s and seg.get("speaker_role") == "teacher":
                preceding_teacher = str(seg.get("text", "")).strip()
                break

    return preceding_teacher, succeeding


def classify_trigger(entry: TimelineEntry, rubric: dict[str, Any]) -> str:
    if entry.trigger in ("motion_threshold_exceeded", "motion_only_fallback"):
        return entry.trigger
    if entry.high_value_interaction_zone and entry.speaker_role == "student":
        cfg = rubric["dimensions"]["conceptual_understanding"]
        if marker_hits(entry.text, cfg["concept_markers"] + cfg["strategic_markers"]):
            return "student_speech_concept"
        if marker_hits(entry.text, rubric["dimensions"]["argumentation"]["justification_markers"]):
            return "student_justification"
        return "student_speech_high_value"
    return entry.trigger


def event_selection_score(entry: TimelineEntry, trigger: str, rubric: dict[str, Any]) -> float:
    score = 0.0
    if entry.high_value_interaction_zone:
        score += 2.0
    if entry.speaker_role == "student":
        score += 1.5
    if trigger == "motion_threshold_exceeded":
        score += 2.5
    if trigger == "student_speech_concept":
        score += 2.0
    if entry.pixel_change_percentage:
        score += min(float(entry.pixel_change_percentage) / 10.0, 1.5)
    score += entry.speaker_confidence * 0.5
    cfg = rubric["dimensions"]["conceptual_understanding"]
    score += marker_hits(entry.text, cfg["concept_markers"]) * 0.4
    return score


def select_vision_events(
    timeline: list[TimelineEntry],
    frames_dir: Path,
    transcript_segments: list[dict],
    rubric: dict[str, Any],
    *,
    max_events: int,
    modality_status: str,
) -> list[VisionEvent]:
    candidates: list[VisionEvent] = []

    for entry in timeline:
        if not entry.frame_id:
            continue
        frame_path = frames_dir / f"{entry.frame_id}.jpg"
        if not frame_path.is_file():
            continue

        trigger = classify_trigger(entry, rubric)
        is_motion = trigger in ("motion_threshold_exceeded", "motion_only_fallback")
        is_student_speech = entry.speaker_role == "student" and entry.high_value_interaction_zone

        if modality_status == "motion_only_fallback":
            if not is_motion:
                continue
        elif not (is_motion or is_student_speech):
            continue

        if is_student_speech:
            if not entry.text.strip():
                continue
            if pattern_score(entry.text, TEACHER_PATTERNS) >= 2:
                continue

        preceding, succeeding = neighbor_context(transcript_segments, entry.timestamp_seconds, entry.text)
        candidates.append(
            VisionEvent(
                timestamp_seconds=entry.timestamp_seconds,
                frame_id=entry.frame_id,
                frame_path=frame_path,
                trigger=trigger,
                transcript_text=entry.text,
                speaker_role=entry.speaker_role,
                preceding_teacher=preceding,
                succeeding_segment=succeeding,
                pixel_change_percentage=entry.pixel_change_percentage,
                selection_score=event_selection_score(entry, trigger, rubric),
            )
        )

    # Diversity: prefer spread across session timeline
    candidates.sort(key=lambda e: e.selection_score, reverse=True)
    if len(candidates) <= max_events:
        chosen = candidates
    else:
        chosen = []
        used_buckets: set[int] = set()
        bucket_size = max(60.0, (candidates[-1].timestamp_seconds - candidates[0].timestamp_seconds) / max_events)
        for event in candidates:
            bucket = int(event.timestamp_seconds // bucket_size)
            if bucket in used_buckets and len(chosen) < max_events - 2:
                continue
            chosen.append(event)
            used_buckets.add(bucket)
            if len(chosen) >= max_events:
                break
        if len(chosen) < max_events:
            for event in candidates:
                if event not in chosen:
                    chosen.append(event)
                if len(chosen) >= max_events:
                    break

    chosen.sort(key=lambda e: e.timestamp_seconds)
    return chosen


def pil_to_base64_jpeg(path: Path, max_width: int = 1600) -> str:
    from PIL import Image

    img = Image.open(path).convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def build_user_prompt(event: VisionEvent, modality_status: str) -> str:
    speech_block = event.transcript_text or "(silent UI interaction — no student speech at this timestamp)"
    return f"""## Session context
modality_status: {modality_status}
timestamp_seconds: {event.timestamp_seconds:.2f}
trigger: {event.trigger}
speaker_role: {event.speaker_role or "unknown"}
pixel_change_percentage: {event.pixel_change_percentage}

## Conversational scaffolding
Preceding teacher remark: {event.preceding_teacher or "(none)"}
Focal student utterance: {speech_block}
Succeeding segment: {event.succeeding_segment or "(none)"}

Audit whether the student's logic (if any) matches the CODAP/Arbor UI in the attached keyframe.
Return the JSON schema specified in the system prompt."""


def parse_vision_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def mock_vision_evaluation(event: VisionEvent, modality_status: str) -> VisionEvaluation:
    has_speech = bool(event.transcript_text.strip())
    arg_score: float | None
    if modality_status == "motion_only_fallback":
        arg_score = None
    else:
        arg_score = 1.0 if has_speech and len(event.transcript_text.split()) > 6 else 0.5

    return VisionEvaluation(
        conceptual_score=1.25,
        software_interaction_score=1.5,
        argumentation_score=arg_score,
        vision_verification={
            "visual_evidence_found": False,
            "screen_state_analysis": "DRY_RUN — vision API not invoked; placeholder analysis.",
            "cognitive_validity": "DRY_RUN — no model verification performed.",
        },
        raw_response={"dry_run": True},
    )


def call_anthropic_vision(
    client: Any,
    model: str,
    event: VisionEvent,
    modality_status: str,
    *,
    max_retries: int = 3,
) -> VisionEvaluation:
    b64 = pil_to_base64_jpeg(event.frame_path)
    user_prompt = build_user_prompt(event, modality_status)

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=800,
                temperature=0.0,
                system=VISION_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": user_prompt},
                        ],
                    }
                ],
            )
            raw = response.content[0].text
            parsed = parse_vision_json(raw)
            arg = parsed.get("argumentation_score")
            if modality_status == "motion_only_fallback":
                arg = None
            return VisionEvaluation(
                conceptual_score=clamp_score(float(parsed.get("conceptual_score", 0))),
                software_interaction_score=clamp_score(float(parsed.get("software_interaction_score", 0))),
                argumentation_score=clamp_score(float(arg)) if arg is not None else None,
                vision_verification=dict(parsed.get("vision_verification", {})),
                raw_response=parsed,
            )
        except Exception as exc:
            last_err = exc
            sleep_s = 2**attempt
            LOGGER.warning("Anthropic vision attempt %d failed: %s — retry in %ds", attempt + 1, exc, sleep_s)
            time.sleep(sleep_s)
    raise RuntimeError(f"Anthropic vision failed after {max_retries} attempts: {last_err}")


def call_openai_vision(
    client: Any,
    model: str,
    event: VisionEvent,
    modality_status: str,
    *,
    max_retries: int = 3,
) -> VisionEvaluation:
    b64 = pil_to_base64_jpeg(event.frame_path)
    user_prompt = build_user_prompt(event, modality_status)
    data_url = f"data:image/jpeg;base64,{b64}"

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=800,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": VISION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            parsed = parse_vision_json(raw)
            arg = parsed.get("argumentation_score")
            if modality_status == "motion_only_fallback":
                arg = None
            return VisionEvaluation(
                conceptual_score=clamp_score(float(parsed.get("conceptual_score", 0))),
                software_interaction_score=clamp_score(float(parsed.get("software_interaction_score", 0))),
                argumentation_score=clamp_score(float(arg)) if arg is not None else None,
                vision_verification=dict(parsed.get("vision_verification", {})),
                raw_response=parsed,
            )
        except Exception as exc:
            last_err = exc
            sleep_s = 2**attempt
            LOGGER.warning("OpenAI vision attempt %d failed: %s — retry in %ds", attempt + 1, exc, sleep_s)
            time.sleep(sleep_s)
    raise RuntimeError(f"OpenAI vision failed after {max_retries} attempts: {last_err}")


def aggregate_dimension_scores(
    evaluations: list[VisionEvaluation],
    dimension: Literal["conceptual", "software", "argumentation"],
) -> float | None:
    values: list[float] = []
    for ev in evaluations:
        if dimension == "conceptual":
            val = ev.conceptual_score
        elif dimension == "software":
            val = ev.software_interaction_score
        else:
            val = ev.argumentation_score
        if val is not None:
            values.append(float(val))
    if not values:
        return None
    values.sort()
    mid = len(values) // 2
    if len(values) % 2:
        return round(values[mid] * 4) / 4
    return round(((values[mid - 1] + values[mid]) / 2) * 4) / 4


def compute_weighted_index(
    conceptual: float,
    software: float,
    argumentation: float | None,
    modality_status: str,
) -> float:
    weights = WEIGHTS_FULL_MULTIMODAL if modality_status == "full_multimodal_sync" else WEIGHTS_MOTION_ONLY
    total = conceptual * weights["conceptual"] + software * weights["software"]
    if argumentation is not None and weights["argumentation"] > 0:
        total += argumentation * weights["argumentation"]
    return round(total * 100) / 100


def score_to_bin(score: float, step: float = 0.5) -> float:
    return round(score / step) * step


def cohen_kappa(labels_a: list[float], labels_b: list[float], categories: list[float]) -> float | None:
    if not labels_a or len(labels_a) != len(labels_b):
        return None
    n = len(labels_a)
    agree = sum(1 for a, b in zip(labels_a, labels_b) if a == b)
    p_o = agree / n
    dist_a = defaultdict(int)
    dist_b = defaultdict(int)
    for a in labels_a:
        dist_a[a] += 1
    for b in labels_b:
        dist_b[b] += 1
    p_e = sum((dist_a[c] / n) * (dist_b[c] / n) for c in categories)
    if math.isclose(1.0 - p_e, 0.0):
        return None
    return round((p_o - p_e) / (1.0 - p_e), 4)


def load_lexical_baseline(student_dir: Path, student_id: str) -> dict[str, Any] | None:
    path = student_dir / f"{student_id}_mmla_cognitive_assessment.json"
    if path.is_file():
        return load_json(path)
    return None


def load_validation_gold(path: Path) -> dict[str, Any] | None:
    if path.is_file():
        return load_json(path)
    return None


def compute_reliability_index(
    vision_metrics: dict[str, float | None],
    lexical: dict[str, Any] | None,
    gold: dict[str, Any] | None,
    student_id: str,
    events_evaluated: int,
    timeline_len: int,
    evidence_rate: float,
) -> dict[str, Any]:
    categories = [i * 0.5 for i in range(7)]  # 0.0 .. 3.0
    lexical_bins: list[float] = []
    vision_bins: list[float] = []
    per_dimension_kappa: dict[str, float | None] = {}

    dim_keys = (
        ("conceptual", "conceptual_score"),
        ("software", "software_interaction_score"),
        ("argumentation", "argumentation_score"),
    )

    if lexical:
        lem = lexical.get("evaluation_metrics", {})
        for dim, key in dim_keys:
            lv = lem.get(key)
            vv = vision_metrics.get(key)
            if lv is None or vv is None:
                continue
            lb = score_to_bin(float(lv))
            vb = score_to_bin(float(vv))
            lexical_bins.append(lb)
            vision_bins.append(vb)
            per_dimension_kappa[dim] = cohen_kappa([lb], [vb], categories)

    kappa_lexical = cohen_kappa(lexical_bins, vision_bins, categories) if lexical_bins else None

    gold_student = (gold or {}).get("students", {}).get(student_id, {})
    gold_metrics = gold_student.get("evaluation_metrics", {})
    gold_bins: list[float] = []
    vision_for_gold: list[float] = []
    if gold_metrics:
        for _, key in dim_keys:
            gv = gold_metrics.get(key)
            vv = vision_metrics.get(key)
            if gv is None or vv is None:
                continue
            gold_bins.append(score_to_bin(float(gv)))
            vision_for_gold.append(score_to_bin(float(vv)))
    kappa_gold = (
        cohen_kappa(vision_for_gold, gold_bins, categories)
        if gold_bins and len(vision_for_gold) == len(gold_bins)
        else None
    )

    return {
        "rule_lexical_baseline_available": lexical is not None,
        "validation_gold_available": bool(gold_metrics),
        "cohen_kappa_vs_lexical_baseline": kappa_lexical,
        "cohen_kappa_vs_validation_gold": kappa_gold,
        "per_dimension_kappa_vs_lexical": per_dimension_kappa,
        "vision_event_coverage": round(events_evaluated / max(timeline_len, 1), 4),
        "mean_visual_evidence_rate": round(evidence_rate, 4),
        "events_vision_audited": events_evaluated,
    }


def make_vision_client(provider: str) -> tuple[Any, str, str]:
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set")
        from openai import OpenAI

        return OpenAI(api_key=api_key), DEFAULT_MODEL_OPENAI, "GPT-4o-Vision-v1"
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set")
    import anthropic

    return anthropic.Anthropic(api_key=api_key), DEFAULT_MODEL_ANTHROPIC, SCORING_ENGINE_LABEL


def assess_student_vision(
    student_dir: Path,
    student_id: str,
    rubric: dict[str, Any],
    *,
    provider: str,
    max_events: int,
    dry_run: bool,
    model_override: str | None,
    validation_gold: dict[str, Any] | None,
) -> dict[str, Any]:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")

    manifest = load_json(manifest_path)
    transcript_path = resolve_transcript_path(student_dir, student_id)
    if not transcript_path:
        raise FileNotFoundError(f"Missing transcript for {student_id}")

    transcript_doc = load_json(transcript_path)
    transcript_segments = transcript_segments_list(transcript_doc)
    timeline = build_timeline(manifest, transcript_segments)
    modality_status = modality_status_from_manifest(manifest)
    frames_dir = frames_dir_from_manifest(manifest, student_dir, student_id)

    events = select_vision_events(
        timeline,
        frames_dir,
        transcript_segments,
        rubric,
        max_events=max_events,
        modality_status=modality_status,
    )
    if not events:
        raise ValueError(f"No auditable vision events for {student_id} (frames_dir={frames_dir})")

    client = None
    model = model_override or ""
    scoring_engine = SCORING_ENGINE_LABEL

    if not dry_run:
        client, model, scoring_engine = make_vision_client(provider)
        if model_override:
            model = model_override

    verified_moments: list[dict[str, Any]] = []
    evaluations: list[VisionEvaluation] = []
    evidence_found = 0

    for idx, event in enumerate(events, start=1):
        LOGGER.info(
            "[%s] Vision audit %d/%d — %s @ %.1fs (%s)",
            student_id,
            idx,
            len(events),
            event.frame_id,
            event.timestamp_seconds,
            event.trigger,
        )
        if dry_run:
            evaluation = mock_vision_evaluation(event, modality_status)
        elif provider == "openai":
            assert client is not None
            evaluation = call_openai_vision(client, model, event, modality_status)
        else:
            assert client is not None
            evaluation = call_anthropic_vision(client, model, event, modality_status)

        evaluations.append(evaluation)
        if evaluation.vision_verification.get("visual_evidence_found"):
            evidence_found += 1

        verified_moments.append(
            {
                "timestamp_seconds": round(event.timestamp_seconds, 2),
                "frame_reference": f"{event.frame_id}.jpg",
                "trigger": event.trigger,
                "transcript_text": event.transcript_text,
                "vision_verification": evaluation.vision_verification,
                "_vision_scores": {
                    "conceptual_score": evaluation.conceptual_score,
                    "software_interaction_score": evaluation.software_interaction_score,
                    "argumentation_score": evaluation.argumentation_score,
                },
            }
        )

    conceptual = aggregate_dimension_scores(evaluations, "conceptual") or 0.0
    software = aggregate_dimension_scores(evaluations, "software") or 0.0
    argumentation = aggregate_dimension_scores(evaluations, "argumentation")
    if modality_status == "motion_only_fallback":
        argumentation = None

    final_index = compute_weighted_index(conceptual, software, argumentation, modality_status)
    vision_metrics = {
        "conceptual_score": conceptual,
        "software_interaction_score": software,
        "argumentation_score": argumentation,
    }

    lexical = load_lexical_baseline(student_dir, student_id)
    reliability = compute_reliability_index(
        vision_metrics,
        lexical,
        validation_gold,
        student_id,
        len(events),
        len(timeline),
        evidence_found / max(len(events), 1),
    )

    # Strip internal score echoes from public moments
    for moment in verified_moments:
        moment.pop("_vision_scores", None)

    payload: dict[str, Any] = {
        "student_id": student_id,
        "modality_status": modality_status,
        "scoring_engine": scoring_engine if not dry_run else f"{scoring_engine}-DRY-RUN",
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "calibrated_metrics": {
            "conceptual_score": conceptual,
            "software_interaction_score": software,
            "argumentation_score": argumentation,
            "final_weighted_index": final_index,
        },
        "weighting_matrix": (
            WEIGHTS_FULL_MULTIMODAL if modality_status == "full_multimodal_sync" else WEIGHTS_MOTION_ONLY
        ),
        "verified_interaction_moments": verified_moments,
        "empirical_reliability_index": reliability,
        "quantitative_summary": (
            f"Vision-audited {len(events)} high-value events from {len(timeline)} timeline entries. "
            f"Visual evidence confirmed in {evidence_found}/{len(events)} moments. "
            f"Final weighted index={final_index:.2f} under {modality_status} calibration."
        ),
    }
    return payload


def discover_students(audio_root: Path) -> list[str]:
    out: list[str] = []
    for child in sorted(audio_root.iterdir()):
        if child.is_dir() and (child / f"{child.name}_video_extraction_manifest.json").is_file():
            out.append(child.name)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Multimodal vision assessor (CODAP DT sessions)")
    parser.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    parser.add_argument("--student", action="append", dest="students")
    parser.add_argument("--rubric", type=Path, default=DEFAULT_RUBRIC)
    parser.add_argument("--provider", choices=("anthropic", "openai"), default="anthropic")
    parser.add_argument("--model", help="Override default vision model ID")
    parser.add_argument("--max-events", type=int, default=12, help="Max vision API calls per student")
    parser.add_argument("--validation-gold", type=Path, default=REPO_ROOT / "calibration" / "mmla_vision_gold.json")
    parser.add_argument("--dry-run", action="store_true", help="Skip API; emit schema with placeholders")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("--stdout", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    rubric = load_json(args.rubric)
    validation_gold = load_validation_gold(args.validation_gold)
    audio_root = args.audio_root.resolve()
    targets = args.students or discover_students(audio_root)
    if not targets:
        LOGGER.error("No students with video extraction manifests under %s", audio_root)
        return 1

    exit_code = 0
    for student_id in targets:
        student_dir = audio_root / student_id
        out_path = student_dir / f"{student_id}_mmla_vision_assessment.json"
        if args.skip_existing and out_path.is_file():
            LOGGER.info("Skipping %s — %s exists", student_id, out_path.name)
            continue
        try:
            payload = assess_student_vision(
                student_dir,
                student_id,
                rubric,
                provider=args.provider,
                max_events=args.max_events,
                dry_run=args.dry_run,
                model_override=args.model,
                validation_gold=validation_gold,
            )
        except Exception as exc:
            LOGGER.error("%s: %s", student_id, exc)
            exit_code = 1
            continue

        if args.stdout:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            LOGGER.info("Wrote %s", out_path)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
