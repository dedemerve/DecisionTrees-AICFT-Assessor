#!/usr/bin/env python3
"""
codap_session_analyzer.py  —  v2 oturum bazlı MMLA analiz motoru.

v1 (codap_frame_analyzer.py) kare başına bir API çağrısı yapıyordu.
Bu modül tüm seçilmiş kareleri tek bir oturum çağrısında gönderir:
  - 13 öğrenci × 3 oturum = ~39 API çağrısı (v1'de 156×13 ≈ 2000+)
  - Çıktı: 7 bölümlü JSON (Görev A–G, system prompt v3.0)
  - Gate/extraction sistemi değişmedi — sadece analiz zamanlaması farklı

Görüntü bütçesi (MAX_IMAGE_FRAMES):
  Yüksek öncelikli frame'ler (emit, drop_attribute, set_dependent) her zaman gönderilir.
  Kalan bütçe speech_anchor ve high_value frame'lere dağıtılır.
  frame=null olan olaylar log+transkript bağlamıyla modele yine iletilir.

Kullanım:
    python scripts/codap_session_analyzer.py Amy Bruno
    python scripts/codap_session_analyzer.py --audio-root PATH --dry-run Amy
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from codap_alignment import (
    estimate_video_start_utc,
    log_window_text_aligned,
    meaningful_event_timestamps_s,
)
from codap_log_window import (
    format_student_stats,
    load_log_dataframe,
    student_log_rows,
    student_session_stats,
)
from multimodal_cognitive_assessor import DEFAULT_AUDIO_ROOT, load_json

# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_PROMPT   = REPO_ROOT / "prompts" / "MMLA_CODAP_session_prompt_v3.md"
DEFAULT_MODEL    = "claude-sonnet-4-6"
DEFAULT_VIDEO_ROOT = REPO_ROOT / "data_sources_2026" / "21 April CODAP Arbor Screen Recordings"

# Frame budget per session call.
# Emit + high-priority frames always included; remainder fills up to this limit.
MAX_IMAGE_FRAMES = 30

# Triggers that always get their image sent regardless of budget
ALWAYS_SEND_IMAGE = frozenset({
    "emit_tree_data_targeted",
    "drop_attribute_targeted",
    "set_dependent_variable_targeted",
    "set_dependent_targeted",
})

# Triggers eligible for image budget allocation (in priority order)
BUDGET_ELIGIBLE = (
    "speech_anchor_midpoint",
    "set_focus_node_targeted",
    "change_split_values_targeted",
    "motion_threshold_exceeded",
    "codap_static_gap_fill",
)

LOGGER = logging.getLogger("codap_session_analyzer")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _pil_to_b64(path: Path, max_width: int = 1280) -> str:
    """Resize if needed and encode as base64 JPEG."""
    from PIL import Image
    img = Image.open(path).convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _load_system_prompt(path: Path | None = None) -> str:
    p = path or DEFAULT_PROMPT
    if not p.is_file():
        raise FileNotFoundError(f"System prompt not found: {p}")
    return p.read_text(encoding="utf-8")


def _load_labeled_transcript(student_dir: Path, student_id: str) -> list[dict]:
    """Return segments list from labeled transcript, falling back to plain."""
    for name in (f"{student_id}_transcript_labeled.json", f"{student_id}_transcript.json"):
        p = student_dir / name
        if p.is_file():
            data = load_json(p)
            return (data or {}).get("segments") or []
    return []


def _nearest_transcript(
    segments: list[dict],
    ts_s: float,
    window_s: float = 5.0,
) -> str | None:
    """Return transcript text of the closest student segment within window_s."""
    best: dict | None = None
    best_delta = window_s + 1
    for seg in segments:
        role = seg.get("speaker_role", "")
        if role not in ("student", ""):
            continue
        mid = (float(seg.get("start", 0)) + float(seg.get("end", 0))) / 2
        delta = abs(mid - ts_s)
        if delta < best_delta:
            best_delta = delta
            best = seg
    return best.get("text") if best else None


def _build_emit_sequence(log_df: Any, student_id: str, session_date: str) -> list[dict]:
    """Extract emit_tree_data rows as a structured sequence."""
    import pandas as pd
    rows = student_log_rows(log_df, student_id)
    if rows.empty:
        return []
    rows = rows.copy()
    rows["_dt"] = pd.to_datetime(rows["created_at"], utc=True)
    rows = rows[rows["_dt"].dt.date.astype(str) == session_date]
    emit_rows = rows[rows["action"] == "emit_tree_data"].sort_values("_dt")

    seq = []
    for i, (_, row) in enumerate(emit_rows.iterrows(), start=1):
        try:
            params = json.loads(row.get("parameters") or "{}")
        except (json.JSONDecodeError, TypeError):
            params = {}
        seq.append({
            "emit_no": i,
            "timestamp_ms": int(row.get("timestamp_ms") or 0),
            "accuracy": params.get("accuracy"),
            "depth": params.get("depth"),
            "node_count": params.get("node_count"),
            "TP": params.get("TP"),
            "TN": params.get("TN"),
            "FP": params.get("FP"),
            "FN": params.get("FN"),
            "dataset": params.get("dataset"),
            "tree_type": params.get("tree_type"),
            "dependent_variable": params.get("dependent_variable"),
        })
    return seq


def _build_log_summary(log_df: Any, student_id: str, session_date: str) -> dict:
    """Summarise the student's log for the session header."""
    import pandas as pd
    rows = student_log_rows(log_df, student_id)
    if rows.empty:
        return {}
    rows = rows.copy()
    rows["_dt"] = pd.to_datetime(rows["created_at"], utc=True)
    rows = rows[rows["_dt"].dt.date.astype(str) == session_date]
    if rows.empty:
        return {}

    action_counts: dict[str, int] = rows["action"].value_counts().to_dict()
    ts_vals = rows["timestamp_ms"].dropna().astype(int)
    return {
        "total_records": len(rows),
        "emit_tree_data_count": int(action_counts.get("emit_tree_data", 0)),
        "action_distribution": {k: int(v) for k, v in action_counts.items()},
        "first_timestamp_ms": int(ts_vals.min()) if not ts_vals.empty else None,
        "last_timestamp_ms": int(ts_vals.max()) if not ts_vals.empty else None,
    }


def _select_image_budget(selected_frames: list[dict]) -> set[str]:
    """
    Return the set of frame_ids that will have their image sent to the API.

    Always-send triggers fill first; remaining budget allocated to eligible
    triggers in priority order.
    """
    always: list[dict] = []
    eligible: list[dict] = []
    for f in selected_frames:
        tr = f.get("extraction_trigger_reason") or ""
        if tr in ALWAYS_SEND_IMAGE:
            always.append(f)
        else:
            eligible.append(f)

    budget = max(0, MAX_IMAGE_FRAMES - len(always))

    # Sort eligible by trigger priority then by high_value flag
    def _priority(f: dict) -> tuple[int, int]:
        tr = f.get("extraction_trigger_reason") or ""
        try:
            idx = BUDGET_ELIGIBLE.index(tr)
        except ValueError:
            idx = len(BUDGET_ELIGIBLE)
        hv = 0 if (f.get("metrics") or {}).get("high_value_interaction_zone") else 1
        return (idx, hv)

    eligible_sorted = sorted(eligible, key=_priority)
    chosen = always + eligible_sorted[:budget]
    return {f["frame_id"] for f in chosen}


# ── Session input builder ──────────────────────────────────────────────────────

def build_session_input(
    *,
    student_id: str,
    session_label: str,
    manifest: dict,
    selected_frames: list[dict],
    frames_dir: Path,
    log_df: Any | None,
    video_start_utc: Any | None,
    session_date: str,
    transcript_segments: list[dict],
    emit_sequence: list[dict],
    log_summary: dict,
    session_stats: dict,
    image_frame_ids: set[str],
) -> str:
    """
    Build the structured text block sent as the user message.
    Images are injected as separate content blocks by the caller.
    This function returns the text portion only.
    """
    total_ms = log_summary.get("last_timestamp_ms") or 0

    lines = [
        f"ÖĞRENCİ: {student_id}",
        f"OTURUM: {session_label}",
        f"TOPLAM_SÜRE_MS: {total_ms}",
        f"TOPLAM_MANIFEST_KARE: {len(manifest.get('frames', []))}",
        "",
        "LOG_ÖZETİ:",
        f"- Toplam kayıt: {log_summary.get('total_records', 0)}",
        f"- emit_tree_data sayısı: {log_summary.get('emit_tree_data_count', 0)}",
        f"- Aksiyon dağılımı: {json.dumps(log_summary.get('action_distribution', {}), ensure_ascii=False)}",
        f"- İlk timestamp_ms: {log_summary.get('first_timestamp_ms')}",
        f"- Son timestamp_ms: {log_summary.get('last_timestamp_ms')}",
        "",
        "EMIT_SEKANSİ:",
        json.dumps(emit_sequence, ensure_ascii=False, indent=2),
        "",
        "ANALİZ EDİLECEK OLAYLAR:",
    ]

    events_payload: list[dict] = []
    for idx, frame_entry in enumerate(selected_frames):
        frame_id = frame_entry["frame_id"]
        ts_s = float(frame_entry["source_timestamp_seconds"])
        trigger = frame_entry.get("extraction_trigger_reason") or "unknown"

        # Log window
        if log_df is not None and video_start_utc is not None:
            log_window_raw = log_window_text_aligned(
                log_df, student_id, ts_s, video_start_utc,
                window_s=10.0, session_date=session_date,
            )
        elif log_df is not None:
            from codap_log_window import log_window_text
            ts_ms = int(round(ts_s * 1000))
            log_window_raw = log_window_text(log_df, student_id, ts_ms)
        else:
            log_window_raw = "(log CSV sağlanmadı)"

        # Parse log_window lines into structured list
        log_window_lines = [l for l in log_window_raw.splitlines() if l.strip()]

        transcript_text = _nearest_transcript(transcript_segments, ts_s)

        event: dict[str, Any] = {
            "event_index": idx,
            "timestamp_seconds": round(ts_s, 3),
            "trigger": trigger,
            "log_window": log_window_lines,
            "transcript_text": transcript_text,
            # Images are sent as separate content blocks; mark which ones have frames
            "frame": f"[IMAGE_{frame_id}]" if frame_id in image_frame_ids else None,
        }
        events_payload.append(event)

    lines.append(json.dumps(events_payload, ensure_ascii=False, indent=2))
    return "\n".join(lines)


# ── API call ──────────────────────────────────────────────────────────────────

def _call_anthropic_session(
    client: Any,
    model: str,
    system_prompt: str,
    text_block: str,
    image_map: dict[str, str],
    *,
    max_retries: int = 3,
) -> dict[str, Any]:
    """
    Send one multi-image session analysis request.
    image_map: {frame_id: base64_jpeg_string}
    Images are inserted as content blocks before the text block so the model
    sees each image immediately before the event that references it.
    """
    import re as _re

    # Build interleaved content: for each [IMAGE_<frame_id>] marker in text,
    # split text and inject image block inline.
    content: list[dict] = []
    remaining = text_block
    pattern = _re.compile(r'\[IMAGE_([^\]]+)\]')

    pos = 0
    for match in pattern.finditer(text_block):
        fid = match.group(1)
        before = text_block[pos:match.start()]
        if before.strip():
            content.append({"type": "text", "text": before})
        b64 = image_map.get(fid)
        if b64:
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
            })
        pos = match.end()

    tail = text_block[pos:]
    if tail.strip():
        content.append({"type": "text", "text": tail})

    if not content:
        content = [{"type": "text", "text": text_block}]

    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=8192,
                temperature=0.0,
                system=system_prompt,
                messages=[{"role": "user", "content": content}],
            )
            raw = response.content[0].text
            # Strip markdown fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
            raw = re.sub(r"\s*```$", "", raw)
            return json.loads(raw)
        except Exception as exc:
            last_err = exc
            LOGGER.warning("Attempt %d/%d failed: %s", attempt + 1, max_retries, exc)
            time.sleep(2 ** attempt)

    raise RuntimeError(
        f"Session analysis failed after {max_retries} attempts: {last_err}"
    )


# ── Mock for dry-run ──────────────────────────────────────────────────────────

def _mock_session_result(
    student_id: str,
    session_label: str,
    selected_frames: list[dict],
    emit_sequence: list[dict],
) -> dict[str, Any]:
    """Structurally complete dry-run placeholder mirroring v3 schema."""
    n = len(selected_frames)
    n_emit = len(emit_sequence)

    events = []
    for idx, f in enumerate(selected_frames):
        ts_s = float(f["source_timestamp_seconds"])
        events.append({
            "event_index": idx,
            "timestamp_seconds": round(ts_s, 3),
            "timestamp_minutes": round(ts_s / 60, 1),
            "trigger": f.get("extraction_trigger_reason") or "unknown",
            "is_on_task": True,
            "off_task_reason": None,
            "frame_quality": {
                "frame_provided": False,
                "is_transition": False,
                "is_duplicate_candidate": False,
                "occlusion": False,
                "usable": True,
                "unusable_reason": None,
            },
            "screen_state": {k: None for k in (
                "arbor_visible", "tree_visible", "node_count_visible",
                "dependent_variable", "dependent_variable_appears_valid",
                "accuracy_visible", "accuracy_value",
                "split_attribute_visible", "split_value_visible",
                "confusion_matrix_visible", "dataset_name",
            )},
            "log_context": {
                "window_events": [],
                "critical_action": None,
                "log_screen_match": "no_log",
                "mismatch_note": None,
            },
            "transcript_context": {
                "text": None,
                "is_task_relevant": False,
                "cognitive_signal": "none",
                "signal_note": None,
                "peer_interaction_signal": False,
                "peer_signal_note": None,
            },
            "decision_rationale": {
                "what": "DRY_RUN — not analyzed.",
                "why_inferred": "DRY_RUN — not analyzed.",
                "why_source": "unclear",
                "threshold_decision_type": None,
            },
            "behavioral_classification": {
                "primary": "IDLE_THINKING",
                "secondary": None,
                "confidence": "low",
                "evidence_sources": [],
                "evidence_note": "DRY_RUN — no analysis performed.",
            },
            "cognitive_indicators": {k: None for k in (
                "systematic_variable_selection", "threshold_reasoning",
                "accuracy_interpretation", "overfitting_awareness",
                "train_test_distinction", "confusion_matrix_reading",
                "domain_knowledge_applied", "iterative_refinement",
                "active_indicator",
            )},
            "aicft_snapshot": {
                "LO3_1_score": None,
                "LO3_2_score": None,
                "LO3_3_score": None,
                "snapshot_interpretation": "Bu skor bu ANDAki kanıtı yansıtır — oturum geneli değil.",
                "scoring_basis": "DRY_RUN",
                "strongest_evidence": None,
            },
            "flags": {
                "aha_moment": False, "aha_note": None,
                "misconception": False, "misconception_note": None,
                "technical_difficulty": False, "technical_note": None,
                "post_accuracy_reaction_observed": False,
                "post_accuracy_reaction_note": None,
                "needs_human_review": True, "review_reason": "DRY_RUN placeholder",
            },
        })

    acc_prog = []
    prev_acc = None
    for e in emit_sequence:
        cur_acc = e.get("accuracy")
        tp, tn, fp, fn = (
            e.get("TP"), e.get("TN"), e.get("FP"), e.get("FN")
        )
        if tp is not None and fp is not None and fn is not None and tn is not None:
            precision = tp / (tp + fp) if (tp + fp) > 0 else None
            recall    = tp / (tp + fn) if (tp + fn) > 0 else None
            f1        = (2 * precision * recall / (precision + recall)
                         if precision and recall else None)
            fpr       = fp / (fp + tn) if (fp + tn) > 0 else None
            calc_note = ("precision=TP/(TP+FP); recall=TP/(TP+FN); "
                         "f1=2*P*R/(P+R); FPR=FP/(FP+TN)")
        else:
            precision = recall = f1 = fpr = None
            calc_note = "TP/TN/FP/FN not in log — metrics unavailable."
        delta = round(cur_acc - prev_acc, 3) if (cur_acc is not None and prev_acc is not None) else None
        acc_prog.append({
            "emit_no": e["emit_no"],
            "timestamp_min": round(e["timestamp_ms"] / 60000, 1),
            "accuracy": cur_acc,
            "depth": e.get("depth"),
            "node_count": e.get("node_count"),
            "delta_accuracy": delta,
            "regression_type": None,
            "regression_note": None,
            "duplicate_emit": False,
            "duplicate_note": None,
            "emit_derived_metrics": {
                "precision": round(precision, 3) if precision is not None else None,
                "recall": round(recall, 3) if recall is not None else None,
                "f1_score": round(f1, 3) if f1 is not None else None,
                "false_positive_rate": round(fpr, 3) if fpr is not None else None,
                "calculation_note": calc_note,
            },
        })
        prev_acc = cur_acc

    lo_stub = {
        "score": 0,
        "modal_evidence_events": [],
        "peak_evidence_event": None,
        "insufficient_evidence": True,
        "peer_interaction_caveat": None,
        "rationale": "DRY_RUN — vision API not invoked.",
    }
    dim_stub = {
        "score": 0,
        "supporting_events": [],
        "rationale": "DRY_RUN.",
    }

    return {
        "student_id": student_id,
        "session_id": session_label,
        "scoring_engine": f"DRY_RUN_{DEFAULT_MODEL}",
        "prompt_version": "v3.0",
        "assessed_at": datetime.now(timezone.utc).isoformat(),
        "modality_status": "full_multimodal_sync",
        "session_preprocessing": {
            "total_duration_minutes": None,
            "emit_count": n_emit,
            "accuracy_progression": acc_prog,
            "accuracy_peak": None,
            "accuracy_final": None,
            "accuracy_regression_detected": False,
            "regression_events": [],
            "regression_summary": "DRY_RUN — not analyzed.",
            "target_variable_validity": {
                "variable_name": None,
                "appears_meaningful": None,
                "validity_note": "DRY_RUN — not analyzed.",
            },
            "overfitting_risk": False,
            "dataset_switches": 0,
            "dominant_dataset": None,
            "unobserved_periods": [],
            "peer_interaction_summary": {
                "detected": False,
                "evidence": None,
                "independence_note": "DRY_RUN — not analyzed.",
            },
            "total_audited_frames": n,
            "total_manifest_frames": None,
            "coverage_ratio": None,
            "coverage_note": "DRY_RUN",
            "pilot_contamination_detected": False,
            "pilot_ids_found": [],
        },
        "events": events,
        "aicft_aggregate": {
            "LO3_1_acquire": lo_stub,
            "LO3_2_deepen": dict(lo_stub),
            "LO3_3_create": dict(lo_stub),
        },
        "dimensional_scores": {
            "conceptual": dim_stub,
            "software_interaction": dict(dim_stub),
            "argumentation": {
                "score": 0,
                "argumentation_data_sufficient": False,
                "transcript_event_count": 0,
                "data_limitation_note": "DRY_RUN — transcript not analyzed.",
                "supporting_events": [],
                "rationale": "DRY_RUN.",
            },
            "weighting_matrix": {
                "conceptual": 0.35,
                "software_interaction": 0.35,
                "argumentation": 0.30,
            },
            "final_weighted_index": 0.0,
            "weighted_index_check": "0*0.35 + 0*0.35 + 0*0.30 = 0.0",
        },
        "reliability": {
            "total_manifest_frames": None,
            "total_audited_frames": n,
            "coverage_ratio": None,
            "coverage_note": "DRY_RUN",
            "mean_visual_evidence_rate": 0.0,
            "multi_source_events": 0,
            "single_source_events": 0,
            "no_source_events": n,
            "gap_analysis": {
                "gaps_over_5min": 0,
                "all_gaps": [],
                "largest_gap_minutes": 0.0,
                "largest_gap_start_min": 0.0,
                "largest_gap_end_min": 0.0,
                "gap_coverage_note": "DRY_RUN",
            },
            "pilot_data_excluded": False,
            "inter_rater_available": False,
            "cohen_kappa_lexical": None,
            "cohen_kappa_human": None,
            "reliability_verdict": "insufficient",
            "reliability_rationale": "DRY_RUN — no analysis performed.",
        },
        "learning_trajectory": {
            "phase_sequence": [],
            "trajectory_pattern": "insufficient_data",
            "cognitive_arc": "DRY_RUN — not analyzed.",
            "turning_points": [],
            "unresolved_questions": ["DRY_RUN — not analyzed."],
            "final_state_summary": "DRY_RUN — no analysis performed.",
        },
        "quality_flags": {
            "skor_tutarsizligi": False,
            "coverage_dusuk": True,
            "buyuk_bosluk_var": False,
            "kritik_bosluk_var": False,
            "pilot_contamination": False,
            "single_source_dominant": True,
            "emit_log_eksik": False,
            "argumentation_olculemedi": True,
            "peer_interaction_detected": False,
            "target_variable_gecersiz": False,
            "duplicate_emit_detected": False,
            "lo3_snapshot_aggregate_divergence": False,
            "warnings": ["DRY_RUN — all fields are placeholders."],
        },
    }


# ── Per-student orchestrator ──────────────────────────────────────────────────

def analyze_session(
    student_dir: Path,
    student_id: str,
    *,
    session_date: str,
    session_label: str,
    log_df: Any | None,
    video_path: Path | None,
    system_prompt: str,
    provider: str,
    model_override: str | None,
    max_frames: int,
    dry_run: bool,
) -> dict[str, Any]:
    from codap_frame_analyzer import select_frames_log_anchored, GAP_FILL_SECONDS

    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = load_json(manifest_path)

    frames_dir = student_dir / f"{student_id}_frames"
    if not frames_dir.is_dir():
        raise FileNotFoundError(frames_dir)

    # Alignment
    import pandas as pd
    log_df_safe = log_df if log_df is not None else pd.DataFrame()
    video_start_utc, alignment_method = estimate_video_start_utc(
        video_path, log_df_safe, student_id, session_date,
    )
    LOGGER.info(
        "[%s] video_start_utc=%s (method=%s)",
        student_id,
        video_start_utc.isoformat() if video_start_utc else "unavailable",
        alignment_method,
    )

    # Frame selection (reuse v1 logic — extraction unchanged)
    selected = select_frames_log_anchored(
        manifest, log_df, student_id, video_start_utc,
        session_date, gap_fill_seconds=GAP_FILL_SECONDS,
        max_frames=max_frames,
    )
    if not selected:
        raise ValueError(f"No frames selected for {student_id}")
    LOGGER.info("[%s] %d frames selected from %d total", student_id, len(selected), len(manifest.get("frames", [])))

    # Context assembly
    transcript_segments = _load_labeled_transcript(student_dir, student_id)
    emit_sequence = _build_emit_sequence(log_df, student_id, session_date) if log_df is not None else []
    log_summary = _build_log_summary(log_df, student_id, session_date) if log_df is not None else {}
    session_stats = (
        student_session_stats(log_df, student_id)
        if log_df is not None
        else {"total_emit_tree_data": 0, "last_accuracy": None,
              "max_duration_minutes": None, "total_actions": 0}
    )

    if dry_run:
        result = _mock_session_result(student_id, session_label, selected, emit_sequence)
    else:
        # Decide image budget
        image_frame_ids = _select_image_budget(selected)
        LOGGER.info(
            "[%s] %d/%d frames will include images (budget=%d)",
            student_id, len(image_frame_ids), len(selected), MAX_IMAGE_FRAMES,
        )

        # Load images
        image_map: dict[str, str] = {}
        for frame_entry in selected:
            fid = frame_entry["frame_id"]
            if fid not in image_frame_ids:
                continue
            img_path = frames_dir / f"{fid}.jpg"
            if not img_path.is_file():
                LOGGER.warning("[%s] Missing image: %s", student_id, img_path)
                image_frame_ids.discard(fid)
                continue
            image_map[fid] = _pil_to_b64(img_path)

        text_block = build_session_input(
            student_id=student_id,
            session_label=session_label,
            manifest=manifest,
            selected_frames=selected,
            frames_dir=frames_dir,
            log_df=log_df,
            video_start_utc=video_start_utc,
            session_date=session_date,
            transcript_segments=transcript_segments,
            emit_sequence=emit_sequence,
            log_summary=log_summary,
            session_stats=session_stats,
            image_frame_ids=image_frame_ids,
        )

        model = model_override or DEFAULT_MODEL
        if provider == "anthropic":
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise EnvironmentError("ANTHROPIC_API_KEY is not set")
            client = anthropic.Anthropic(api_key=api_key)
            result = _call_anthropic_session(client, model, system_prompt, text_block, image_map)
        else:
            raise NotImplementedError(f"Provider '{provider}' not supported in v2 session analyzer")

        # Inject pipeline metadata if model omitted them
        result.setdefault("student_id", student_id)
        result.setdefault("session_id", session_label)
        result["scoring_engine"] = f"{model}-vision"
        result["prompt_version"] = "v2.0"
        result.setdefault("assessed_at", datetime.now(timezone.utc).isoformat())

    # Persist
    out_path = student_dir / f"{student_id}_mmla_session_analysis_v2.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("[%s] Wrote %s (%d events)", student_id, out_path.name, len(result.get("events", [])))

    return result


# ── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="MMLA v2 session analyzer (one API call per student)")
    p.add_argument("students", nargs="*", help="Student IDs (default: all with manifests)")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--video-root", type=Path, default=DEFAULT_VIDEO_ROOT)
    p.add_argument("--log-csv",    type=Path)
    p.add_argument("--session-date",  default="2026-04-21")
    p.add_argument("--session-label", default="21_Nisan_2026_CODAP")
    p.add_argument("--provider",  choices=("anthropic",), default="anthropic")
    p.add_argument("--model",     default=None)
    p.add_argument("--max-frames", type=int, default=0,
                   help="Cap on selected frames per student (0 = unlimited)")
    p.add_argument("--skip-existing", action="store_true",
                   help="Skip students whose v2 output already exists")
    p.add_argument("--dry-run", action="store_true",
                   help="Build input and write placeholder output without calling API")
    p.add_argument("--prompt", type=Path, default=None,
                   help="Override system prompt path")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    audio_root: Path = args.audio_root.resolve()
    video_root: Path = args.video_root.resolve()

    # Discover students
    if args.students:
        student_ids = args.students
    else:
        student_ids = sorted(
            p.name for p in audio_root.iterdir()
            if p.is_dir()
            and (p / f"{p.name}_video_extraction_manifest.json").is_file()
        )

    if not student_ids:
        LOGGER.error("No students found under %s", audio_root)
        return 1

    # Load log CSV once
    log_df = None
    if args.log_csv and args.log_csv.is_file():
        LOGGER.info("Loading log CSV: %s", args.log_csv)
        log_df = load_log_dataframe(args.log_csv)
    elif not args.dry_run:
        LOGGER.warning("No --log-csv provided. Log context will be empty.")

    system_prompt = _load_system_prompt(args.prompt)

    errors: list[str] = []
    for sid in student_ids:
        student_dir = audio_root / sid
        out_path = student_dir / f"{sid}_mmla_session_analysis_v2.json"

        if args.skip_existing and out_path.is_file():
            LOGGER.info("[%s] Output exists — skipping", sid)
            continue

        video_path = video_root / f"{sid}.webm" if video_root.is_dir() else None
        if video_path and not video_path.is_file():
            video_path = None

        LOGGER.info("[%s] Starting session analysis (dry_run=%s)", sid, args.dry_run)
        try:
            analyze_session(
                student_dir, sid,
                session_date=args.session_date,
                session_label=args.session_label,
                log_df=log_df,
                video_path=video_path,
                system_prompt=system_prompt,
                provider=args.provider,
                model_override=args.model,
                max_frames=args.max_frames,
                dry_run=args.dry_run,
            )
        except Exception as exc:
            LOGGER.error("[%s] FAILED: %s", sid, exc)
            errors.append(f"{sid}: {exc}")

    if errors:
        LOGGER.error("Completed with %d error(s):", len(errors))
        for e in errors:
            LOGGER.error("  %s", e)
        return 1

    LOGGER.info("All %d student(s) complete.", len(student_ids))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
