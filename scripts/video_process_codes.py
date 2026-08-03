#!/usr/bin/env python3
"""Heuristic V-layer process codes from expert observation text (video narrative).

See framework/VIDEO_PROCESS_CODEBOOK_v1.md. These are hints for analysts/ML —
they do not replace human coding and are not proficiency scores.
"""

from __future__ import annotations

import re
from typing import Any

# Full codebook matrix (always emitted per episode). Heuristics are optional.
# Codes without a PROCESS_HINT_RULES entry stay not_observed unless human-coded later.
CODEBOOK_PROCESS_CODE_IDS: list[str] = [
    "V1A_systematic_iteration",
    "V1B_chaotic_iteration",
    "V2A_hesitation_disorientation",
    "V2B_interface_cycling",
    "V3A_sustained_engagement",
    "V3B_disengagement_passivity",
    "V4A_productive_recovery",
    "V4B_dead_end_loop",
    "V5A_productive_help_seeking",
    "V5B_dependent_execution",
    "V6A_mcr_zero_targeting",
    "V6B_label_inversion",
    "V6C_metric_scope_awareness",
    "V7A_no_metric_inspection",
    "V7B_no_graph_reading",
    "V7C_no_comparison_despite_opportunity",
    "V8A_multi_instance_benchmarking",
    "V8B_table_sort_threshold",
    "V8C_ctr_in_place_edit",
    "V8D_import_failure_recovery",
]

# (code_id, label, pattern) — auto-hints from narrative text
PROCESS_HINT_RULES: list[tuple[str, str, re.Pattern[str]]] = [
    (
        "V1A_systematic_iteration",
        "Systematic one-at-a-time iteration",
        re.compile(
            r"her seferinde|tek tek|sırayla|önce.*sonra|incelen(?:ir|mesi)"
            r"|movable value.*güncellen|threshold.*yerine",
            re.I,
        ),
    ),
    (
        "V1B_chaotic_iteration",
        "Chaotic multi-control changes",
        re.compile(
            r"rastgele|deneme yanılma|hem .* hem .* sürüklenir"
            r"|aynı anda|her şeyi",
            re.I,
        ),
    ),
    (
        "V2A_hesitation_disorientation",
        "Hesitation / disorientation",
        re.compile(r"karar veremedim|bilmiyorum|nerede|bulunamadı|hata alınır", re.I),
    ),
    (
        "V2B_interface_cycling",
        "Interface cycling without progress",
        re.compile(
            r"açıp kapat|panel.*tekrar|aynı.*(pencere|panel).*tekrar|toggle",
            re.I,
        ),
    ),
    (
        "V3A_sustained_engagement",
        "Sustained task engagement",
        re.compile(
            r"devam eder|yeniden dener|zorluk.*sonra.*çalış|persistent|ısran",
            re.I,
        ),
    ),
    (
        "V3B_disengagement_passivity",
        "Disengagement or minimal session",
        re.compile(
            r"başka bir şey yoktur|ses bulunmamaktadır|dataset yüklenmeden"
            r"|hiçbir ses",
            re.I,
        ),
    ),
    (
        "V4A_productive_recovery",
        "Productive error recovery",
        re.compile(
            r"düzelt|geri al|temizlenir.*yeniden|yanlış.*sonra|recogniz|fark ed",
            re.I,
        ),
    ),
    (
        "V4B_dead_end_loop",
        "Dead-end repetition",
        re.compile(r"tekrar.*emit|yeniden.*aynı|import edilir.*import", re.I),
    ),
    (
        "V5A_productive_help_seeking",
        "Productive help / peer challenge with ownership",
        re.compile(
            r"öğrenci.*savun|itiraz|neden.*yaptın|sorgular|açıklar",
            re.I,
        ),
    ),
    (
        "V5B_dependent_execution",
        "Teacher/peer-directed execution",
        re.compile(
            r"öğretmen|hoca|merve|oğuz|arkadaşı.*yaptım|öğrenciye.*söylen",
            re.I,
        ),
    ),
    (
        "V6A_mcr_zero_targeting",
        "MCR=0 optimization target",
        re.compile(r"MCR\s*0|0'a ulaş|sıfır.*hata|mcr=0", re.I),
    ),
    (
        "V6B_label_inversion",
        "Label inversion / same-class leaves",
        re.compile(
            r"recommendable or not.*yanlış|aynı.*etiket|ters|sensitivity=0",
            re.I,
        ),
    ),
    (
        "V6C_metric_scope_awareness",
        "Awareness of metrics beyond CTR",
        re.compile(r"precision|kesinlik|recall|hangi metrik", re.I),
    ),
    (
        "V7A_no_metric_inspection",
        "Emit/output without metric follow-up (narrative gap)",
        re.compile(r"emit function çalıştırılır\.?$", re.I),
    ),
    (
        "V7B_no_graph_reading",
        "No graph reading despite opportunity",
        re.compile(
            r"grafik.*(bakılmad|okunmad)|graph.*(not|never).*read|grafiğe bakmaz",
            re.I,
        ),
    ),
    (
        "V7C_no_comparison_despite_opportunity",
        "No model comparison despite opportunity",
        re.compile(
            r"karşılaştırılmad|comparison.*(yok|yoktur)|karşılaştırma yapılmaz",
            re.I,
        ),
    ),
    (
        "V8A_multi_instance_benchmarking",
        "Multi-instance CODAP strategy",
        re.compile(r"birden fazla.*codap|ayrı.*pencere|7.*instance", re.I),
    ),
    (
        "V8B_table_sort_threshold",
        "Table sort for threshold estimation",
        re.compile(r"sıralanır|sort|küçükten büyüğe", re.I),
    ),
    (
        "V8C_ctr_in_place_edit",
        "In-place CTR record edit",
        re.compile(r"classification tree records.*\d+\.\s*dt|satır.*değiştir|ctr.*seçilir", re.I),
    ),
    (
        "V8D_import_failure_recovery",
        "Import/session continuity failure",
        re.compile(r"import edilir|404|ip adresi|sunucu.*bulunamadı", re.I),
    ),
]

QUOTE_RE = re.compile(r"[“\"]([^”\"]{2,200})[”\"]")


def extract_verbatim_utterances(text: str) -> list[dict[str, Any]]:
    """Pull quoted speech from expert narrative (learner/teacher/peer)."""
    out: list[dict[str, Any]] = []
    for m in QUOTE_RE.finditer(text):
        quote = m.group(1).strip()
        if not quote:
            continue
        speaker = "learner"
        lo = max(0, m.start() - 80)
        ctx = text[lo:m.start()].lower()
        if any(x in ctx for x in ("öğretmen", "hoca", "merve", "oğuz")):
            speaker = "teacher_or_researcher"
        elif "arkadaş" in ctx or "peer" in ctx:
            speaker = "peer"
        out.append({"speaker_role": speaker, "quote": quote})
    return out


def infer_process_code_hints(text: str) -> list[dict[str, str]]:
    hints: list[dict[str, str]] = []
    seen: set[str] = set()
    for code, label, pat in PROCESS_HINT_RULES:
        if pat.search(text) and code not in seen:
            seen.add(code)
            hints.append({"code": code, "label": label})
    return hints


ALL_PROCESS_CODE_IDS: list[str] = list(CODEBOOK_PROCESS_CODE_IDS)

PROCESS_CODE_LABELS: dict[str, str] = {code: label for code, label, _ in PROCESS_HINT_RULES}
for _code in CODEBOOK_PROCESS_CODE_IDS:
    PROCESS_CODE_LABELS.setdefault(_code, _code)


def v_code_family(v_code: str) -> str:
    """V1A_systematic_iteration -> V1; V8D_import_failure_recovery -> V8."""
    import re
    m = re.match(r"^(V\d+)", v_code)
    if m:
        return m.group(1)
    return v_code.split("_", 1)[0]

ML_FEATURE_MAP: dict[str, str] = {
    "V1A_systematic_iteration": "systematic_iteration_present",
    "V1B_chaotic_iteration": "chaotic_iteration_present",
    "V2A_hesitation_disorientation": "hesitation_episode_present",
    "V2B_interface_cycling": "interface_cycling_present",
    "V3A_sustained_engagement": "sustained_engagement_present",
    "V3B_disengagement_passivity": "disengagement_present",
    "V4A_productive_recovery": "productive_recovery_present",
    "V4B_dead_end_loop": "dead_end_loop_present",
    "V5A_productive_help_seeking": "productive_help_seeking_present",
    "V5B_dependent_execution": "dependent_execution_present",
    "V6A_mcr_zero_targeting": "mcr_zero_targeting_present",
    "V6B_label_inversion": "label_inversion_present",
    "V6C_metric_scope_awareness": "metric_scope_awareness_present",
    "V7A_no_metric_inspection": "metric_inspection_absent_after_emit",
    "V7B_no_graph_reading": "graph_reading_absent",
    "V7C_no_comparison_despite_opportunity": "comparison_absent_despite_opportunity",
    "V8A_multi_instance_benchmarking": "multi_instance_strategy_present",
    "V8B_table_sort_threshold": "table_sort_threshold_present",
    "V8C_ctr_in_place_edit": "ctr_in_place_edit_present",
    "V8D_import_failure_recovery": "import_failure_recovery_present",
}


def _assistance_status(episode_codes: dict[str, dict[str, Any]]) -> str:
    if episode_codes.get("V5B_dependent_execution", {}).get("decision") == "observed":
        return "peer" if any(
            "peer" in e.lower() or "arkadaş" in e.lower()
            for e in episode_codes.get("V5B_dependent_execution", {}).get("evidence", [])
        ) else "instructor"
    if episode_codes.get("V5A_productive_help_seeking", {}).get("decision") == "observed":
        return "peer"
    return "independent"


def _anchor_event(behavior_codes: list[str]) -> str | None:
    priority = ("EMIT_TREE", "emit", "CHANGE_SPLIT", "DROP_ATTRIBUTE", "SET_TARGET")
    upper = [b.upper() for b in behavior_codes]
    for p in priority:
        for b in upper:
            if p in b:
                return b
    return behavior_codes[0] if behavior_codes else None


def _log_corroboration(
    code: str,
    log_metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not log_metadata or not log_metadata.get("log_available"):
        return None
    task4 = log_metadata.get("task4_process_variables") or {}
    notes: list[str] = []

    if code == "V1A_systematic_iteration" and (task4.get("threshold_change_count") or 0) >= 2:
        notes.append("log: multiple threshold changes")
    if code == "V1B_chaotic_iteration" and (task4.get("feature_change_count") or 0) >= 3:
        notes.append("log: high feature churn")
    if code == "V4B_dead_end_loop" and (task4.get("emit_count") or 0) >= 5:
        notes.append("log: repeated emits")
    if code == "V6A_mcr_zero_targeting" and task4.get("max_tree_depth"):
        if (task4.get("max_tree_depth") or 0) >= 4:
            notes.append("log: deep tree depth")
    if code == "V8D_import_failure_recovery":
        flags = log_metadata.get("analyst_flags") or []
        if any("import" in f.lower() for f in flags):
            notes.append("log analyst flag")

    if not notes:
        return {"present": False, "note": "no log signal for this code"}
    return {"present": True, "note": "; ".join(notes)}


def build_process_codes_artifact(
    student_id: str,
    cohort_year: int,
    episodes: list[dict[str, Any]],
    timeline: list[dict[str, Any]],
    log_metadata: dict[str, Any] | None = None,
    rubric_gap_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Roll narrative hints into episode-level V-code decisions."""
    from datetime import datetime, timezone

    timeline_by_step = {int(r["step_index"]): r for r in timeline}
    episode_rows: list[dict[str, Any]] = []
    session_observed: set[str] = set()

    for ep in episodes:
        step_indices = [int(s) for s in ep.get("step_indices") or []]
        ep_codes: dict[str, dict[str, Any]] = {}
        code_evidence: dict[str, list[str]] = {}
        code_steps: dict[str, list[int]] = {}

        for si in step_indices:
            row = timeline_by_step.get(si) or {}
            text = row.get("uzman_nitel_gözlemi") or ""
            for hint in row.get("process_code_hints") or infer_process_code_hints(text):
                code = hint["code"]
                code_evidence.setdefault(code, []).append(text.strip())
                code_steps.setdefault(code, []).append(si)

        for code in ALL_PROCESS_CODE_IDS:
            if code in code_evidence:
                ep_codes[code] = {
                    "decision": "observed",
                    "evidence": code_evidence[code],
                    "evidence_sources": ["expert_narrative", "heuristic"],
                    "step_indices": sorted(set(code_steps.get(code, []))),
                    "log_corroboration": _log_corroboration(code, log_metadata),
                }
                session_observed.add(code)
            else:
                ep_codes[code] = {
                    "decision": "not_observed",
                    "evidence": [],
                    "evidence_sources": [],
                    "step_indices": [],
                    "log_corroboration": _log_corroboration(code, log_metadata),
                }

        timestamps = [
            (timeline_by_step.get(si) or {}).get("visual_anchors", {}).get("timestamp_ms")
            for si in step_indices
        ]
        timestamps = [t for t in timestamps if isinstance(t, (int, float))]

        behavior_codes: list[str] = []
        for si in step_indices:
            behavior_codes.extend((timeline_by_step.get(si) or {}).get("behavior_codes_linked") or [])

        episode_rows.append({
            "episode_id": ep.get("episode_id"),
            "step_indices": step_indices,
            "dominant_category": ep.get("dominant_category"),
            "anchor_event": _anchor_event(behavior_codes),
            "start_ms": min(timestamps) if timestamps else None,
            "end_ms": max(timestamps) if timestamps else None,
            "assistance_status": _assistance_status(ep_codes),
            "process_codes": ep_codes,
            "notes": None,
        })

    not_observed = [c for c in ALL_PROCESS_CODE_IDS if c not in session_observed]
    ml_flags = {
        flag: (code in session_observed)
        for code, flag in ML_FEATURE_MAP.items()
    }

    return {
        "$schema": "schema/video_process_codes.schema.json",
        "artifact": "process_codes",
        "student_id": student_id,
        "cohort_year": cohort_year,
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "codebook_id": "VIDEO_PROCESS_CODEBOOK_v1",
        "interpretation_rule": (
            "Episode-level V-codes support process interpretation and ML feature "
            "engineering. They are not proficiency scores. Heuristic decisions from "
            "expert narrative require human adjudication."
        ),
        "episodes": episode_rows,
        "session_summary": {
            "episode_count": len(episode_rows),
            "codes_observed": sorted(session_observed),
            "codes_not_observed": not_observed,
            "codes_not_measurable": [],
            "rubric_gap_ids": rubric_gap_ids or [],
        },
        "ml_feature_flags": ml_flags,
    }


def flatten_process_codes_tables(
    process_codes_doc: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Normalize process_codes.json into three analysis-ready tables (lossless fields).

    Returns:
        episodes: one row per student × episode
        episode_process_codes: one row per student × episode × v_code (full matrix)
        session_ml_features: one row per student (wide ML flags + session summary)
    """
    student_id = process_codes_doc["student_id"]
    cohort_year = int(process_codes_doc["cohort_year"])
    generated_at = process_codes_doc.get("generated_at")
    codebook_id = process_codes_doc.get("codebook_id")
    schema_version = process_codes_doc.get("schema_version")
    summary = process_codes_doc.get("session_summary") or {}
    ml_flags = process_codes_doc.get("ml_feature_flags") or {}

    episodes_rows: list[dict[str, Any]] = []
    code_rows: list[dict[str, Any]] = []

    for ep_index, ep in enumerate(process_codes_doc.get("episodes") or []):
        episode_id = ep["episode_id"]
        step_indices = [int(s) for s in (ep.get("step_indices") or [])]
        start_ms = ep.get("start_ms")
        end_ms = ep.get("end_ms")
        duration_ms = None
        if isinstance(start_ms, (int, float)) and isinstance(end_ms, (int, float)):
            duration_ms = int(end_ms) - int(start_ms)

        ep_codes = ep.get("process_codes") or {}
        observed_in_ep = [
            c for c, entry in ep_codes.items()
            if (entry or {}).get("decision") == "observed"
        ]

        episodes_rows.append({
            "student_id": student_id,
            "cohort_year": cohort_year,
            "episode_id": episode_id,
            "episode_index": ep_index,
            "dominant_category": ep.get("dominant_category"),
            "anchor_event": ep.get("anchor_event"),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": duration_ms,
            "step_count": len(step_indices),
            "step_indices": step_indices,
            "step_indices_min": min(step_indices) if step_indices else None,
            "step_indices_max": max(step_indices) if step_indices else None,
            "assistance_status": ep.get("assistance_status"),
            "notes": ep.get("notes"),
            "codes_observed_count": len(observed_in_ep),
            "codes_observed": observed_in_ep,
            "codebook_id": codebook_id,
            "schema_version": schema_version,
            "source_generated_at": generated_at,
        })

        for v_code in ALL_PROCESS_CODE_IDS:
            entry = ep_codes.get(v_code) or {
                "decision": "not_observed",
                "evidence": [],
                "evidence_sources": [],
                "step_indices": [],
                "log_corroboration": None,
            }
            log_corr = entry.get("log_corroboration")
            evidence = entry.get("evidence") or []
            step_idxs = entry.get("step_indices") or []

            code_rows.append({
                "student_id": student_id,
                "cohort_year": cohort_year,
                "episode_id": episode_id,
                "episode_index": ep_index,
                "row_id": f"{student_id}:{episode_id}:{v_code}",
                "v_code": v_code,
                "v_code_family": v_code_family(v_code),
                "v_code_label": PROCESS_CODE_LABELS.get(v_code),
                "ml_feature_name": ML_FEATURE_MAP.get(v_code),
                "decision": entry.get("decision", "not_observed"),
                "evidence_count": len(evidence),
                "evidence": evidence,
                "evidence_sources": entry.get("evidence_sources") or [],
                "step_indices": step_idxs,
                "log_corroboration_present": (
                    None if log_corr is None else bool(log_corr.get("present"))
                ),
                "log_corroboration_note": (
                    None if log_corr is None else log_corr.get("note")
                ),
                "codebook_id": codebook_id,
                "schema_version": schema_version,
                "source_generated_at": generated_at,
            })

    session_row: dict[str, Any] = {
        "student_id": student_id,
        "cohort_year": cohort_year,
        "episode_count": summary.get("episode_count", len(episodes_rows)),
        "codes_observed": summary.get("codes_observed") or [],
        "codes_not_observed": summary.get("codes_not_observed") or [],
        "codes_not_measurable": summary.get("codes_not_measurable") or [],
        "rubric_gap_ids": summary.get("rubric_gap_ids") or [],
        "codebook_id": codebook_id,
        "schema_version": schema_version,
        "source_generated_at": generated_at,
        "interpretation_rule": process_codes_doc.get("interpretation_rule"),
    }
    for flag_name, flag_val in ml_flags.items():
        session_row[flag_name] = bool(flag_val)

    return {
        "episodes": episodes_rows,
        "episode_process_codes": code_rows,
        "session_ml_features": [session_row],
    }
