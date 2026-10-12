"""Read-only evaluation of the 2026 DecisionTrees-AICFT archive.

Reads scoring files, validation files, frame analyses, CODAP logs, and the
notebook-evidence table. Writes nothing except through run_evaluation.py.
Does not modify student records, frozen source data, or existing splits.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT / "mmla_explorer") not in sys.path:
    sys.path.insert(0, str(ROOT / "mmla_explorer"))

from audit_data_quality import (  # noqa: E402
    PUBLISHED_OCR,
    SESSIONS,
    STUDENTS,
    WORKSHEETS,
    load_json,
    resolved_log_rows,
)
from compute_b15_from_logs import compute_votat, parse_params  # noqa: E402

RULE_WORKSHEETS = ("WS5", "WS6", "WS7", "WS10")
LEARNER_DECISION = {
    "drop_attribute",
    "change_split_values",
    "set_dependent_variable",
    "change_tree_type",
    "swap_focus_split",
    "refresh_tree",
    "emit_tree_data",
}
INTERFACE_EVENTS = {
    "session_start",
    "codap_document_change",
    "codap_component_change",
    "dragstart",
    "dragenter",
    "dragleave",
    "dragend",
}
OTHER_CONFIG = LEARNER_DECISION - {"drop_attribute", "change_split_values", "emit_tree_data"}
PRIOR_SCORE_KEYS = (
    "previous_score",
    "original_score",
    "automated_score",
    "score_before_override",
    "initial_score",
)


def item_class(score):
    if score is None:
        return "unavailable"
    if score == 0:
        return "no_credit"
    if 0 < score < 1:
        return "partial"
    if score >= 1:
        return "full_credit"
    return "unavailable"


def scoring_items(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    data = load_json(path)
    items = data.get("items")
    if isinstance(items, dict):
        return [{"item": key, **(val if isinstance(val, dict) else {"score": val})} for key, val in items.items()]
    if isinstance(items, list):
        return [row for row in items if isinstance(row, dict)]
    return []


def validation_scores(path: Path) -> dict[str, float]:
    if not path.is_file():
        return {}
    data = load_json(path)
    checks = data.get("deterministic_checks")
    out = {}
    if isinstance(checks, dict):
        for item_id, rec in checks.items():
            if isinstance(rec, dict) and isinstance(rec.get("score"), (int, float)):
                out[str(item_id)] = float(rec["score"])
    return out


def score_history() -> dict:
    """Separate review requests from accepted score changes.

    A review flag is a request to look. researcher_override with a rationale
    is the stored accepted change. The pre-override score is recorded only
    when a prior-score field exists.
    """
    rows = []
    by_worksheet = {}
    missing_extraction = []
    for student in STUDENTS:
        for worksheet in WORKSHEETS:
            base = ROOT / "students" / student / worksheet
            extraction = base / "extraction.json"
            items = scoring_items(base / "scoring.json")
            if not extraction.is_file():
                if items:
                    missing_extraction.append({"student": student, "worksheet": worksheet, "scored_items": len(items)})
                continue
            published = (
                (ROOT / "ocr_output" / student / f"{student}_{PUBLISHED_OCR[worksheet]}.json").is_file()
                if worksheet in PUBLISHED_OCR else True
            )
            scope = "score_summary"
            if worksheet == "WS11" or not published:
                scope = "excluded_unused_or_unpublished"
            elif (base / "scoring.json").is_file():
                payload = load_json(base / "scoring.json")
                zero_confidence = bool(items) and all(
                    (it.get("score") in (0, 0.0)) and (it.get("confidence") in (0, 0.0))
                    for it in items
                )
                if payload.get("blocked"):
                    scope = "blocked"
                elif zero_confidence:
                    scope = "all_zero_confidence"
            bucket = by_worksheet.setdefault(worksheet, Counter())
            for item in items:
                score = item.get("score")
                score_num = float(score) if isinstance(score, (int, float)) else None
                review = bool(item.get("review"))
                override = bool(item.get("researcher_override"))
                rationale = (item.get("override_rationale") or "").strip()
                prior = {key: item.get(key) for key in PRIOR_SCORE_KEYS if key in item}
                row = {
                    "student": student,
                    "worksheet": worksheet,
                    "scope": scope,
                    "item": item.get("item"),
                    "score": score_num,
                    "credit": item_class(score_num),
                    "review": review,
                    "researcher_override": override,
                    "rationale": rationale,
                    "prior_score_fields": prior,
                    "confidence": item.get("confidence"),
                }
                rows.append(row)
                if scope != "score_summary":
                    continue
                bucket["scored_items"] += 1
                bucket[item_class(score_num)] += 1
                if review:
                    bucket["review"] += 1
                if override:
                    bucket["override"] += 1
                if review and not override:
                    bucket["review_without_override"] += 1
                if review and override:
                    bucket["review_and_override"] += 1
    overrides = [r for r in rows if r["researcher_override"]]
    used = [r for r in rows if r["scope"] == "score_summary"]
    review_only = [r for r in used if r["review"] and not r["researcher_override"]]
    review_by_credit = {}
    for credit in ("full_credit", "partial", "no_credit", "unavailable"):
        group = [r for r in used if r["credit"] == credit]
        review_by_credit[credit] = {
            "items": len(group),
            "review_flag": sum(1 for r in group if r["review"]),
        }
    b25 = [r for r in rows if r["worksheet"] == "WS5" and r["item"] == "WS5_B25"]
    return {
        "unit": "scored item whose worksheet is in the score summary: published extraction, not WS11, not blocked, and not an all-zero confidence file",
        "participants": len(STUDENTS),
        "scored_items_all_files": len(rows),
        "scored_items": len(used),
        "items_by_scope": dict(Counter(r["scope"] for r in rows)),
        "review_flags_all_files": sum(1 for r in rows if r["review"]),
        "review_flags": sum(1 for r in used if r["review"]),
        "accepted_overrides": len(overrides),
        "review_without_override": len(review_only),
        "review_by_credit": review_by_credit,
        "review_and_override": sum(1 for r in rows if r["review"] and r["researcher_override"]),
        "overrides_missing_rationale": sum(1 for r in overrides if not r["rationale"]),
        "overrides_with_prior_score": sum(1 for r in overrides if r["prior_score_fields"]),
        "override_rows": [
            {
                "student": r["student"],
                "worksheet": r["worksheet"],
                "item": r["item"],
                "final_score": r["score"],
                "review_flag_still_set": r["review"],
                "rationale": r["rationale"],
                "prior_score_stored": bool(r["prior_score_fields"]),
            }
            for r in overrides
        ],
        "review_only_by_worksheet": dict(Counter(r["worksheet"] for r in review_only)),
        "b25_rows": [
            {
                "student": r["student"],
                "final_score": r["score"],
                "review": r["review"],
                "accepted_change": r["researcher_override"],
                "rationale": r["rationale"],
            }
            for r in b25
        ],
        "by_worksheet": {ws: dict(counts) for ws, counts in by_worksheet.items()},
        "scoring_without_extraction": missing_extraction,
        "note": "The final_score on an override row is the stored score after the change. The automated score that was replaced is not in the file unless a prior-score field is present.",
    }


def rule_reproducibility(history: dict | None = None) -> dict:
    """Exact agreement between scoring.json and validation.json on rule worksheets.

    Both files are pipeline artifacts. Agreement is internal consistency.
    It is not agreement with an independent human rater.
    """
    compared = 0
    exact = 0
    abs_err = 0.0
    mismatches = []
    missing_validation = []
    only_validation = []
    per_sheet = {}
    for student in STUDENTS:
        for worksheet in RULE_WORKSHEETS:
            base = ROOT / "students" / student / worksheet
            if not (base / "extraction.json").is_file():
                continue
            scored = {row["item"]: row for row in scoring_items(base / "scoring.json") if row.get("item")}
            checked = validation_scores(base / "validation.json")
            sheet = per_sheet.setdefault(worksheet, Counter())
            if not checked:
                missing_validation.append({"student": student, "worksheet": worksheet})
                continue
            for item_id, expected in checked.items():
                if item_id not in scored or not isinstance(scored[item_id].get("score"), (int, float)):
                    only_validation.append({"student": student, "worksheet": worksheet, "item": item_id})
                    continue
                got = float(scored[item_id]["score"])
                compared += 1
                sheet["compared"] += 1
                err = abs(got - expected)
                abs_err += err
                if err < 1e-9:
                    exact += 1
                    sheet["exact"] += 1
                else:
                    sheet["mismatch"] += 1
                    mismatches.append({
                        "student": student,
                        "worksheet": worksheet,
                        "item": item_id,
                        "scoring": got,
                        "validation": expected,
                    })
    return {
        "question": "Do stored rule scores match the stored deterministic checks?",
        "unit": "item present in both scoring.json and validation.json, for a student worksheet that has an extraction",
        "reference": "validation.json deterministic_checks.score. This is the same pipeline's rule output, not an independent human score.",
        "worksheets": list(RULE_WORKSHEETS),
        "compared": compared,
        "exact_agreement": exact,
        "exact_agreement_rate": (exact / compared) if compared else None,
        "mae": (abs_err / compared) if compared else None,
        "mismatches": mismatches,
        "students_missing_validation": missing_validation,
        "validation_items_without_score": only_validation,
        "by_worksheet": {ws: dict(counts) for ws, counts in per_sheet.items()},
        "human_reference_available": False,
    }


def _session_events() -> dict[tuple[str, str], list[dict]]:
    _path, _rows, kept, _excluded = resolved_log_rows()
    grouped = defaultdict(list)
    session_days = {day: name for _sid, name, day, _folder in SESSIONS}
    for row in kept:
        day = (row.get("created_at") or "")[:10]
        if day not in session_days:
            continue
        grouped[(row["student_id"], session_days[day])].append(row)
    return grouped


def timestamp_resets(events: list[dict]) -> int:
    ordered = sorted(events, key=lambda row: row.get("created_at") or "")
    previous = None
    resets = 0
    for row in ordered:
        try:
            current = int(row.get("timestamp_ms") or 0)
        except (TypeError, ValueError):
            continue
        if previous is not None and current < previous:
            resets += 1
        previous = current
    return resets


def wall_intervals(events: list[dict]) -> list[dict]:
    """Intervals between consecutive emits ordered by created_at.

    Events between two emits are those that fall between them in wall-clock
    order. timestamp_ms is not used.
    """
    ordered = sorted(events, key=lambda row: row.get("created_at") or "")
    emit_at = [i for i, row in enumerate(ordered) if row.get("action") == "emit_tree_data"]
    intervals = []
    for left, right in zip(emit_at, emit_at[1:]):
        between = ordered[left + 1:right]
        pred = sum(1 for row in between if row.get("action") == "drop_attribute")
        thresh = sum(1 for row in between if row.get("action") == "change_split_values")
        other = sum(1 for row in between if row.get("action") in OTHER_CONFIG)
        if pred and not thresh:
            kind = "only_attribute"
        elif thresh and not pred:
            kind = "only_threshold"
        else:
            kind = "both_or_neither"
        strict_threshold = kind == "only_threshold" and other == 0
        intervals.append({
            "kind": kind,
            "predictor_changes": pred,
            "threshold_changes": thresh,
            "other_config_actions": other,
            "strict_only_threshold": strict_threshold,
            "emit_before": parse_params(ordered[left].get("parameters", "{}")),
            "emit_after": parse_params(ordered[right].get("parameters", "{}")),
        })
    return intervals


def _numeric_changes(before: dict, after: dict) -> list[str]:
    changed = []
    keys = set(before) & set(after)
    for key in sorted(keys):
        left, right = before[key], after[key]
        if isinstance(left, (int, float)) and isinstance(right, (int, float)) and left != right:
            changed.append(key)
    return changed


def log_sequences() -> dict:
    grouped = _session_events()
    ms_totals = Counter()
    wall_totals = Counter()
    sessions = []
    reset_sessions = 0
    count_disagreements = 0
    sequence_disagreements = 0
    sequence_difference_sessions = []
    strict_threshold = 0
    threshold_with_numeric_change = 0
    threshold_intervals = 0
    changed_fields = Counter()
    action_counts = Counter()
    for (student, session), events in sorted(grouped.items()):
        action_counts.update(row.get("action") or "" for row in events)
        resets = timestamp_resets(events)
        if resets:
            reset_sessions += 1
        ms = compute_votat(events)
        wall = wall_intervals(events)
        ms_kinds = Counter(
            "only_attribute" if row["dimension_changed"] == "predictor"
            else "only_threshold" if row["dimension_changed"] == "threshold"
            else "both_or_neither"
            for row in ms["votat_intervals"]
        )
        wall_kinds = Counter(row["kind"] for row in wall)
        ms_sequence = [
            "only_attribute" if row["dimension_changed"] == "predictor"
            else "only_threshold" if row["dimension_changed"] == "threshold"
            else "both_or_neither"
            for row in ms["votat_intervals"]
        ]
        wall_sequence = [row["kind"] for row in wall]
        count_same = (
            dict(ms_kinds) == dict(wall_kinds)
            and len(ms["votat_intervals"]) == len(wall)
        )
        sequence_same = ms_sequence == wall_sequence
        if not count_same:
            count_disagreements += 1
        if not sequence_same:
            sequence_disagreements += 1
            sequence_difference_sessions.append({"student": student, "session": session})
        same = sequence_same
        for key in ("only_attribute", "only_threshold", "both_or_neither"):
            ms_totals[key] += ms_kinds[key]
            wall_totals[key] += wall_kinds[key]
        ms_totals["intervals"] += len(ms["votat_intervals"])
        wall_totals["intervals"] += len(wall)
        for interval in wall:
            if interval["kind"] != "only_threshold":
                continue
            threshold_intervals += 1
            if interval["strict_only_threshold"]:
                strict_threshold += 1
            changed = _numeric_changes(interval["emit_before"], interval["emit_after"])
            if changed:
                threshold_with_numeric_change += 1
                changed_fields.update(changed)
        sessions.append({
            "student": student,
            "session": session,
            "events": len(events),
            "timestamp_ms_resets": resets,
            "emits": ms["total_emits"],
            "ms_intervals": dict(ms_kinds),
            "wall_intervals": dict(wall_kinds),
            "classification_matches": same,
        })
    learner = sum(action_counts[name] for name in LEARNER_DECISION)
    interface = sum(action_counts[name] for name in INTERFACE_EVENTS)
    other = sum(count for name, count in action_counts.items() if name not in LEARNER_DECISION and name not in INTERFACE_EVENTS)
    return {
        "question": "How do recorded actions sit between model submissions, and does that description depend on timestamp_ms?",
        "unit": "gap between two consecutive emit_tree_data events in one participant session",
        "inclusion": "CODAP session 1 and session 2 rows that resolve to the 15 pseudonyms",
        "sessions": len(sessions),
        "sessions_with_timestamp_ms_reset": reset_sessions,
        "sessions_whose_interval_counts_differ_by_clock": count_disagreements,
        "sessions_whose_interval_sequence_differs": sequence_disagreements,
        "interval_sequence_difference_sessions": sequence_difference_sessions,
        "timestamp_ms_definition": "Events sorted by timestamp_ms. An event is between two emits when its timestamp_ms is strictly inside that numeric range. This is the published VOTAT procedure.",
        "wall_clock_definition": "Events ordered by created_at. An event is between two emits when it sits between them in that order.",
        "timestamp_ms_totals": dict(ms_totals),
        "wall_clock_totals": dict(wall_totals),
        "only_threshold_wall": threshold_intervals,
        "only_threshold_wall_with_no_other_config_action": strict_threshold,
        "only_threshold_wall_with_changed_numeric_emit_field": threshold_with_numeric_change,
        "numeric_emit_fields_that_changed": dict(changed_fields),
        "action_class_counts": {
            "learner_decision_rows": learner,
            "interface_rows": interface,
            "other_rows": other,
        },
        "session_rows": sessions,
        "interpretation_limit": "A threshold-only interval records which logged actions occurred. A later emit with a different numeric field shows that the submitted payload changed. It does not show why the learner made the change.",
    }


def frame_labels() -> dict:
    label_counts = Counter()
    confidence = Counter()
    confidence_by_label = defaultdict(Counter)
    secondary = 0
    labelled = 0
    listed = 0
    files_ok = 0
    files_missing = 0
    log_context_frames = 0
    log_csv_used = Counter()
    alignment_method = Counter()
    keys = Counter()
    unlabelled = []
    for student in STUDENTS:
        for _sid, name, _date, folder in SESSIONS:
            base = ROOT / "data_sources_2026" / folder / student
            manifest = base / f"{student}_video_extraction_manifest.json"
            analysis = base / f"{student}_codap_frame_analyses.json"
            if not manifest.is_file():
                continue
            frames = load_json(manifest).get("frames") or []
            listed += len(frames)
            if not analysis.is_file():
                files_missing += 1
                unlabelled.append({"student": student, "session": name, "listed": len(frames), "labelled": 0})
                continue
            files_ok += 1
            raw = load_json(analysis)
            if isinstance(raw, dict):
                if "log_csv_used" in raw:
                    log_csv_used[str(bool(raw.get("log_csv_used")))] += 1
                else:
                    log_csv_used["field_absent"] += 1
                if "alignment" in raw:
                    alignment_method[str((raw.get("alignment") or {}).get("method") or "missing")] += 1
                else:
                    alignment_method["field_absent"] += 1
            else:
                log_csv_used["field_absent"] += 1
                alignment_method["field_absent"] += 1
            codes = raw if isinstance(raw, list) else raw.get("frame_analyses") or []
            session_labels = 0
            for row in codes:
                if isinstance(row, dict):
                    keys.update(row.keys())
                    if row.get("log_context") or row.get("log_window"):
                        log_context_frames += 1
                label = row.get("primary_behavior") if isinstance(row, dict) else None
                if not label:
                    continue
                session_labels += 1
                labelled += 1
                label_counts[label] += 1
                conf = (row.get("analysis_confidence") or "MISSING").upper()
                confidence[conf] += 1
                confidence_by_label[label][conf] += 1
                if row.get("secondary_behavior"):
                    secondary += 1
            if session_labels == 0:
                unlabelled.append({"student": student, "session": name, "listed": len(frames), "labelled": 0})
            elif session_labels < len(frames):
                unlabelled.append({
                    "student": student,
                    "session": name,
                    "listed": len(frames),
                    "labelled": session_labels,
                    "partial": True,
                })
    low_excluded = Counter(label_counts)
    # Sensitivity: drop LOW-confidence frames from the share, without treating confidence as accuracy.
    low_remaining = sum(confidence_by_label[label]["LOW"] for label in label_counts)
    for label, counts in confidence_by_label.items():
        low_excluded[label] -= counts.get("LOW", 0)
    build_tune = label_counts.get("BUILD_TREE", 0) + label_counts.get("TUNE_THRESHOLD", 0)
    return {
        "question": "What behaviour labels are stored, and what would an independent coder still have to establish?",
        "unit": "frame analysis record with a primary_behavior",
        "listed_frames": listed,
        "labelled_frames": labelled,
        "analysis_files": files_ok,
        "sessions_without_analysis_file": files_missing,
        "label_counts": dict(label_counts),
        "majority_label": label_counts.most_common(1)[0][0] if label_counts else None,
        "majority_count": label_counts.most_common(1)[0][1] if label_counts else 0,
        "build_plus_tune": build_tune,
        "build_plus_tune_share": (build_tune / labelled) if labelled else None,
        "secondary_behavior_present": secondary,
        "model_confidence": dict(confidence),
        "labels_excluding_low_confidence": {k: v for k, v in low_excluded.items() if v},
        "low_confidence_frames": low_remaining,
        "frames_storing_log_context": log_context_frames,
        "sessions_log_csv_used": dict(log_csv_used),
        "sessions_alignment_method": dict(alignment_method),
        "record_keys": sorted(keys),
        "unlabelled_or_partial": unlabelled,
        "image_files_checked_via_manifest_paths": "Manifest image paths were not re-hashed here. The quality audit already compared listed frames with nonempty files.",
        "independent_coder": False,
        "note": "analysis_confidence is the model's own rating. The coding prompt tells the model to reconsider when BUILD_TREE plus TUNE_THRESHOLD is under 30 percent and to prefer the more common code when unsure. That instruction is not a measured base rate.",
    }


def alignment_feasibility(logs: dict, frames: dict) -> dict:
    """Decide whether a frame-to-event join is defensible. Do not emit matches."""
    video_hits = []
    for folder in ("codap_arbor_21april_audio", "codap_arbor_28april_audio"):
        base = ROOT / "data_sources_2026" / folder
        if not base.is_dir():
            continue
        for pattern in ("*.webm", "*.mp4"):
            for path in base.glob(f"*/*{pattern[1:]}"):
                video_hits.append(str(path.relative_to(ROOT)))
                if len(video_hits) >= 5:
                    break
    return {
        "question": "Do frame times and log times share a clock that can support a frame-level match?",
        "frame_clock": "source_timestamp_seconds, seconds from the start of the recording",
        "log_clocks": [
            "timestamp_ms, which the alignment module documents as resetting on page reload",
            "created_at, UTC wall time of the log row",
        ],
        "stored_frame_event_join": False,
        "matching_window_used": None,
        "matches_emitted": 0,
        "sessions_with_timestamp_ms_reset": logs["sessions_with_timestamp_ms_reset"],
        "stored_alignment_method": frames.get("sessions_alignment_method"),
        "stored_log_csv_used": frames.get("sessions_log_csv_used"),
        "video_start_fallback": "scripts/codap_alignment.py sets the recording start to the first log created_at when ffprobe has no creation_time. That makes the offset depend on the log, so it is not an independent clock.",
        "sample_video_paths_seen": video_hits,
        "defensible_frame_match": False,
        "decision": "Participant-session comparison only. No frame was paired with a log row.",
    }


def notebook_coverage() -> dict:
    raw = (ROOT / "mmla_explorer" / "site" / "data" / "notebook_evidence.js").read_text(encoding="utf-8")
    data = json.loads(raw.split("=", 1)[1].rstrip().rstrip(";"))
    tasks = [task["id"] for task in data["tasks"]]
    found = Counter()
    rows = []
    for row in data["rows"]:
        inspection = row["inspection"]
        task_map = inspection.get("tasks") or {}
        for task in tasks:
            if task_map.get(task) == "found":
                found[task] += 1
        models = (inspection.get("checks") or {}).get("models") or inspection.get("models") or []
        with_mcr = sum(1 for model in models if model.get("test_mcr_stored"))
        rows.append({
            "student": row["student"],
            "kind": row["kind"],
            "tasks_found": sum(1 for task in tasks if task_map.get(task) == "found"),
            "tasks_not_found": [task for task in tasks if task_map.get(task) != "found"],
            "models": len(models),
            "models_with_stored_test_mcr": with_mcr,
            "split_recorded": task_map.get("split") == "found",
            "test_size": inspection.get("test_size"),
            "stratify": inspection.get("stratify"),
            "synthetic_flag": inspection.get("synthetic"),
            "cell_count_matches_file": None if row.get("file") is None else row["file"].get("cell_count_matches_inspection"),
        })
    return {
        "question": "Which assignment dimensions are present in the final submission file?",
        "unit": "final submission",
        "submissions": len(rows),
        "notebooks": sum(1 for row in rows if row["kind"] == "notebook"),
        "reports": [row["student"] for row in rows if row["kind"] != "notebook"],
        "task_found": {task: found[task] for task in tasks},
        "task_denominator": len(rows),
        "models": sum(row["models"] for row in rows),
        "models_with_stored_test_mcr": sum(row["models_with_stored_test_mcr"] for row in rows),
        "split_recorded": sum(1 for row in rows if row["split_recorded"]),
        "synthetic_flags": [row["student"] for row in rows if row["synthetic_flag"]],
        "cell_count_disagreements": [row["student"] for row in rows if row["cell_count_matches_file"] is False],
        "rows": rows,
        "note": "A task marked not_found means that evidence was not in the inspected file. It is not a score of zero. Stored test misclassification rates were not recomputed.",
    }


def triangulation(frames: dict, logs: dict, notebooks: dict, scores: dict) -> dict:
    frame_sessions = {}
    for student in STUDENTS:
        for _sid, name, _date, folder in SESSIONS:
            manifest = ROOT / "data_sources_2026" / folder / student / f"{student}_video_extraction_manifest.json"
            analysis = ROOT / "data_sources_2026" / folder / student / f"{student}_codap_frame_analyses.json"
            if not manifest.is_file():
                continue
            labels = Counter()
            if analysis.is_file():
                raw = load_json(analysis)
                codes = raw if isinstance(raw, list) else raw.get("frame_analyses") or []
                labels.update(row.get("primary_behavior") for row in codes if isinstance(row, dict) and row.get("primary_behavior"))
            frame_sessions[(student, name)] = labels
    tune_and_threshold = 0
    tune_without_threshold_event = 0
    threshold_event_without_tune_label = 0
    neither = 0
    unlabelled_paired = 0
    grouped = _session_events()
    paired_rows = []
    for key in sorted(frame_sessions):
        if key not in grouped:
            continue
        labels = frame_sessions[key]
        events = grouped[key]
        threshold_events = sum(1 for row in events if row.get("action") == "change_split_values")
        tune = labels.get("TUNE_THRESHOLD", 0)
        labelled = sum(labels.values())
        if labelled == 0:
            relation = "insufficient"
            unlabelled_paired += 1
        elif tune and threshold_events:
            relation = "complementary"
            tune_and_threshold += 1
        elif tune and not threshold_events:
            relation = "conflicting"
            tune_without_threshold_event += 1
        elif threshold_events and not tune:
            relation = "complementary"
            threshold_event_without_tune_label += 1
        else:
            relation = "insufficient"
            neither += 1
        paired_rows.append({
            "student": key[0],
            "session": key[1],
            "tune_threshold_frames": tune,
            "change_split_values": threshold_events,
            "relation": relation,
        })
    worksheet_students = set()
    for student in STUDENTS:
        if any((ROOT / "students" / student / ws / "extraction.json").is_file() for ws in WORKSHEETS):
            worksheet_students.add(student)
    matrix = []
    nb_index = {row["student"]: row for row in notebooks["rows"]}
    for student in STUDENTS:
        frame_n = sum(1 for (name, _session) in frame_sessions if name == student)
        log_n = sum(1 for (name, _session) in grouped if name == student)
        paired_n = sum(1 for row in paired_rows if row["student"] == student)
        matrix.append({
            "student": student,
            "worksheet_extraction": student in worksheet_students,
            "frame_sessions": frame_n,
            "log_sessions": log_n,
            "sessions_with_both": paired_n,
            "final_submission": nb_index.get(student, {}).get("kind"),
            "final_tasks_found": nb_index.get(student, {}).get("tasks_found"),
        })
    return {
        "question": "Where do the four evidence sources cover the same participant, and where do frame labels and log actions describe related activity?",
        "unit_coverage": "participant",
        "unit_session": "participant-session with both a frame manifest and a CODAP session log",
        "participants": len(STUDENTS),
        "participants_with_a_worksheet_extraction": len(worksheet_students),
        "paired_sessions": len(paired_rows),
        "paired_with_both_threshold_signals": tune_and_threshold,
        "paired_tune_label_without_threshold_event": tune_without_threshold_event,
        "paired_threshold_event_without_tune_label": threshold_event_without_tune_label,
        "paired_with_neither_threshold_signal": neither,
        "paired_sessions_without_labels": unlabelled_paired,
        "relation_rule": "Complementary when labelled frames and the log both speak to threshold activity, or when labelled frames do not use TUNE_THRESHOLD while the log still records change_split_values. A session with no behaviour labels is insufficient: missing labels are not a count of zero tuning. Conflicting would require TUNE_THRESHOLD labels and no change_split_values rows. The sources are not time-matched.",
        "select_target_labels": frames["label_counts"].get("SELECT_TARGET", 0),
        "target_setting_events": sum(1 for events in grouped.values() for row in events if row.get("action") == "set_dependent_variable"),
        "accepted_score_changes": scores["accepted_overrides"],
        "matrix": matrix,
        "paired_rows": paired_rows,
        "chain": "A count of frames or log rows is an observable record. Calling both 'threshold activity' is an analytical indicator. It is not evidence that the same moment was observed twice, and it is not a claim about intention.",
    }


def evaluation_matrix(scores, rules, frames, logs, alignment, notebooks, cross) -> list[dict]:
    b25 = scores["b25_rows"]
    override_n = scores["accepted_overrides"]
    return [
        {
            "component": "Architecture",
            "research_question": "Does a retrieval stage supply evidence to a generation stage?",
            "evaluation_unit": "pipeline",
            "reference_standard": "Lewis et al. (2020): retrieval of external documents, then generation conditioned on those documents",
            "metric": "Component inspection",
            "available_data": "Source modules listed in the architecture record",
            "analysis_status": "Completed",
            "result": "No retrieval index and no ranked passage set. Rubrics and few-shot examples are written into prompts. A log-window helper can attach nearby log lines when a video start is estimated, and the stored frame records do not keep that window.",
            "interpretation": "The system is an extraction, rule-scoring, and vision-coding pipeline. RAG metrics do not apply.",
            "limitations": "Inspection covers the active code paths. Unused scripts in trash/ and archive/ were not treated as the current system.",
            "output": "evaluation/results/summary.json",
        },
        {
            "component": "Worksheet transcription",
            "research_question": "Do extracted responses match the handwriting?",
            "evaluation_unit": "extracted response",
            "reference_standard": "Researcher comparison with the original pages",
            "metric": "Researcher report of reading agreement",
            "available_data": "Researcher report. No stored comparison log.",
            "analysis_status": "Completed",
            "result": "The researcher reports that every extracted response was checked and that the reading matched the handwriting in every case.",
            "interpretation": "This is transcription fidelity. It does not establish that the answer is conceptually correct or that a later score is right.",
            "limitations": "No item-level comparison file is stored, so the check cannot be recomputed from the archive.",
            "output": "mmla_explorer/derived/quality_audit.json",
        },
        {
            "component": "Rule scoring",
            "research_question": "Do stored item scores match the stored deterministic checks?",
            "evaluation_unit": "item in both scoring.json and validation.json",
            "reference_standard": "validation.json score for WS5, WS6, WS7, and WS10",
            "metric": f"Exact agreement {rules['exact_agreement']}/{rules['compared']}; MAE {rules['mae']}",
            "available_data": f"{rules['compared']} paired items",
            "analysis_status": "Completed",
            "result": f"{rules['exact_agreement']} of {rules['compared']} paired items agree exactly.",
            "interpretation": "The two pipeline files are consistent with each other. This is not an independent human rescore.",
            "limitations": "Items without a validation score are excluded. Missing responses are not coded as zero by this comparison.",
            "output": "evaluation/results/rule_reproducibility.json",
        },
        {
            "component": "WS5 B25 score changes",
            "research_question": "Which stored scores are accepted changes, and which flags are only review requests?",
            "evaluation_unit": "WS5_B25 item, then every scored item",
            "reference_standard": "researcher_override plus override_rationale",
            "metric": "Count of accepted changes; count of review flags without an override",
            "available_data": f"{len(b25)} WS5_B25 rows; {scores['scored_items']} scored items",
            "analysis_status": "Completed",
            "result": (
                f"{override_n} accepted changes, all WS5_B25, each with a rationale. "
                f"In the score summary, {scores['review_without_override']} of {scores['scored_items']} items have a review flag and no override. "
                f"Across every scoring file, including blocked and unused files, {scores['review_flags_all_files']} items have a review flag. "
                f"{scores['overrides_with_prior_score']} accepted changes store the score they replaced."
            ),
            "interpretation": "The rationale records why the final score was set. The review flag on those same rows remains a flag; it is not a second decision.",
            "limitations": "The automated score before the change is not stored, so agreement between the first score and the accepted score cannot be calculated.",
            "output": "evaluation/results/score_history.json",
        },
        {
            "component": "Rubric scoring",
            "research_question": "Do rubric scores match an independent human score?",
            "evaluation_unit": "rubric item",
            "reference_standard": "Independent human scores",
            "metric": "MAE, exact agreement, weighted kappa",
            "available_data": "Stored rubric scores. No second rater file.",
            "analysis_status": "Requires human validation",
            "result": "Not calculated.",
            "interpretation": "A stored rubric score is a model application of the rubric. The transcription check does not validate it.",
            "limitations": "Needs a human score on a defined item set, kept separate from the model score.",
            "output": "evaluation/results/evaluation_matrix.json",
        },
        {
            "component": "Retrieval",
            "research_question": "Are the retrieved passages the relevant ones?",
            "evaluation_unit": "query",
            "reference_standard": "Judged relevant passages",
            "metric": "Precision@k, Recall@k, MRR, nDCG@k",
            "available_data": "No query set and no relevance judgements",
            "analysis_status": "Not applicable",
            "result": "Not calculated.",
            "interpretation": "There is no retrieval component to score.",
            "limitations": "Building a relevance set would evaluate a system this archive does not run.",
            "output": "evaluation/results/evaluation_matrix.json",
        },
        {
            "component": "Frame behaviour labels",
            "research_question": "How are the stored labels distributed, and what is their agreement with a second coder?",
            "evaluation_unit": "labelled frame",
            "reference_standard": "Researcher inspection of the images; no second coder",
            "metric": "Label counts; Cohen's kappa not calculated",
            "available_data": f"{frames['labelled_frames']} labelled frames",
            "analysis_status": "Partially completed",
            "result": f"{frames['labelled_frames']} labels. Majority label {frames['majority_label']} has {frames['majority_count']}. SELECT_TARGET has {frames['label_counts'].get('SELECT_TARGET', 0)}. LOW confidence has {frames['low_confidence_frames']}.",
            "interpretation": "The researcher has inspected the frames. That inspection is not an inter-rater statistic. Model confidence is not accuracy.",
            "limitations": "The prompt tells the coder to prefer common labels when unsure, so the distribution is not a pure observation of the screen.",
            "output": "evaluation/results/frame_labels.json",
        },
        {
            "component": "CODAP sequences",
            "research_question": "Does the between-submission description stay the same if events are ordered by wall clock?",
            "evaluation_unit": "interval between two emits",
            "reference_standard": "Same action rules, two clocks",
            "metric": "Interval counts under timestamp_ms and under created_at",
            "available_data": f"{logs['sessions']} sessions; {logs['timestamp_ms_totals'].get('intervals', 0)} timestamp_ms intervals; {logs['wall_clock_totals'].get('intervals', 0)} wall-clock intervals",
            "analysis_status": "Completed",
            "result": f"{logs['sessions_with_timestamp_ms_reset']} of {logs['sessions']} sessions contain a timestamp_ms decrease along created_at. Category totals stay {logs['timestamp_ms_totals'].get('only_attribute')} / {logs['timestamp_ms_totals'].get('only_threshold')} / {logs['timestamp_ms_totals'].get('both_or_neither')} under both clocks. The interval sequence differs in {logs['sessions_whose_interval_sequence_differs']} sessions.",
            "interpretation": "The published VOTAT counts use timestamp_ms. Where that clock resets, wall-clock order is the sequence the log's own timestamps support.",
            "limitations": "created_at orders rows. It does not align them to frames. A VOTAT interval is not a learning strategy.",
            "output": "evaluation/results/log_sequences.json",
        },
        {
            "component": "Frame-log alignment",
            "research_question": "Can a frame be matched to the log event at the same moment?",
            "evaluation_unit": "frame",
            "reference_standard": "A shared clock or a measured offset",
            "metric": "Matches inside a declared window",
            "available_data": "Video-relative frame times; resetting timestamp_ms; created_at",
            "analysis_status": "Not established",
            "result": "No frame-to-log matches were established. The diagnostic ran. The available offset estimator uses the first log event as the recording start when the video has no creation time.",
            "interpretation": "A finished diagnostic is not a completed alignment. Session-level comparison is the supported grain.",
            "limitations": "A future join needs an independent recording start time and a stated tolerance.",
            "output": "evaluation/results/alignment.json",
        },
        {
            "component": "Final submissions",
            "research_question": "Which required traces are in the final file?",
            "evaluation_unit": "final submission",
            "reference_standard": "Assignment traces used by the notebook inspection",
            "metric": "Presence of each trace, with the submission as the denominator",
            "available_data": f"{notebooks['submissions']} final files",
            "analysis_status": "Completed",
            "result": f"Split recorded in {notebooks['split_recorded']} of {notebooks['submissions']}. Stored test misclassification rate on {notebooks['models_with_stored_test_mcr']} of {notebooks['models']} described models.",
            "interpretation": "Presence means the file contains the trace. It does not mean the model was appropriate or that the rate was recomputed.",
            "limitations": "Notebooks were not executed again. One submission is a written report.",
            "output": "evaluation/results/notebooks.json",
        },
        {
            "component": "Multimodal coverage",
            "research_question": "Which participants have which sources, and do threshold signals co-occur at session level?",
            "evaluation_unit": "participant, then paired session",
            "reference_standard": "File presence; TUNE_THRESHOLD labels; change_split_values rows",
            "metric": "Coverage counts and the complementary/conflicting/insufficient classification",
            "available_data": f"{cross['participants']} participants; {cross['paired_sessions']} paired sessions",
            "analysis_status": "Completed",
            "result": f"{cross['paired_with_both_threshold_signals']} paired sessions have both a TUNE_THRESHOLD label and a change_split_values row. {cross['paired_tune_label_without_threshold_event']} have the label without the event. {cross['paired_threshold_event_without_tune_label']} have the event without the label. {cross['paired_sessions_without_labels']} paired session has frames and a log but no behaviour labels, so it is not treated as a zero.",
            "interpretation": "Co-occurrence is complementary evidence of related activity in the session. It is not a matched event and not an intention.",
            "limitations": "Fifteen participants, incomplete session coverage, and no shared frame-log clock.",
            "output": "evaluation/results/triangulation.json",
        },
    ]


def architecture_record() -> dict:
    return {
        "classification": "not_rag",
        "reason": "Generation is conditioned on a supplied page image, a pasted rubric, few-shot examples, or a supplied frame. Nothing queries a retrieval index and returns ranked passages for the generator to cite.",
        "flow": [
            "Source worksheets, recordings, CODAP logs, and final notebooks",
            "Vision transcription and deterministic normalisation",
            "Rule checks or few-shot rubric scoring",
            "Researcher review flags and accepted score changes",
            "Frame selection and vision behaviour labels",
            "Log sequence summaries at session level",
            "Notebook file inspection",
            "Public archive tables",
        ],
        "components": [
            {
                "name": "Worksheet vision extraction",
                "location": "ocr_pipeline.py",
                "llm": True,
                "retrieval": False,
                "deterministic": False,
                "reference": "Researcher transcription check",
            },
            {
                "name": "Mechanical normalisation",
                "location": "ws_extraction_normalize.py",
                "llm": False,
                "retrieval": False,
                "deterministic": True,
                "reference": "Character-level rewrite rules",
            },
            {
                "name": "Rule validation and scoring",
                "location": "ws5_validation.py, ws6_validation.py, ws7_validation.py, ws10_validation.py",
                "llm": False,
                "retrieval": False,
                "deterministic": True,
                "reference": "Food-card table and fixed answers",
            },
            {
                "name": "Rubric scoring",
                "location": "worksheet_assessor.py",
                "llm": True,
                "retrieval": False,
                "deterministic": False,
                "reference": "Rubric text and few-shot examples embedded in the prompt",
            },
            {
                "name": "Accepted score changes",
                "location": "students/*/WS5/scoring.json researcher_override",
                "llm": False,
                "retrieval": False,
                "deterministic": True,
                "reference": "Stored rationale",
            },
            {
                "name": "Frame behaviour coding",
                "location": "scripts/codap_session_analyzer.py and prompts/MMLA_CODAP_video_system_prompt.md",
                "llm": True,
                "retrieval": False,
                "deterministic": False,
                "reference": "Codebook in the prompt. Researcher inspected the images. No second coder.",
            },
            {
                "name": "CODAP log summary",
                "location": "scripts/compute_b15_from_logs.py and mmla_explorer/audit_data_quality.py",
                "llm": False,
                "retrieval": False,
                "deterministic": True,
                "reference": "Action names in the log",
            },
            {
                "name": "Final notebook inspection",
                "location": "scripts/extract_notebook_evidence.py",
                "llm": False,
                "retrieval": False,
                "deterministic": True,
                "reference": "Traces in the submitted file",
            },
        ],
    }
