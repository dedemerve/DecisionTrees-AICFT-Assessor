#!/usr/bin/env python3
"""Write the evaluation tables. Read-only with respect to student and source data."""
from __future__ import annotations

import json
from pathlib import Path

from analysis import (
    alignment_feasibility,
    architecture_record,
    evaluation_matrix,
    frame_labels,
    log_sequences,
    notebook_coverage,
    rule_reproducibility,
    score_history,
    triangulation,
)

OUT = Path(__file__).resolve().parent / "results"
SITE = Path(__file__).resolve().parent.parent / "mmla_explorer" / "site" / "data" / "evaluation.js"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    scores = score_history()
    rules = rule_reproducibility()
    frames = frame_labels()
    logs = log_sequences()
    alignment = alignment_feasibility(logs, frames)
    notebooks = notebook_coverage()
    cross = triangulation(frames, logs, notebooks, scores)
    matrix = evaluation_matrix(scores, rules, frames, logs, alignment, notebooks, cross)
    architecture = architecture_record()
    summary = {
        "architecture": architecture["classification"],
        "scored_items": scores["scored_items"],
        "accepted_overrides": scores["accepted_overrides"],
        "review_without_override": scores["review_without_override"],
        "rule_exact": f"{rules['exact_agreement']}/{rules['compared']}",
        "labelled_frames": frames["labelled_frames"],
        "alignment_methods": frames["sessions_alignment_method"],
        "log_csv_used": frames["sessions_log_csv_used"],
        "timestamp_ms_reset_sessions": logs["sessions_with_timestamp_ms_reset"],
        "interval_count_disagreements": logs["sessions_whose_interval_counts_differ_by_clock"],
        "interval_sequence_disagreements": logs["sessions_whose_interval_sequence_differs"],
        "paired_sessions": cross["paired_sessions"],
    }
    payloads = {
        "score_history.json": scores,
        "rule_reproducibility.json": rules,
        "frame_labels.json": frames,
        "log_sequences.json": logs,
        "alignment.json": alignment,
        "notebooks.json": notebooks,
        "triangulation.json": cross,
        "evaluation_matrix.json": matrix,
        "architecture.json": architecture,
        "summary.json": summary,
    }
    for name, payload in payloads.items():
        (OUT / name).write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    public = {
        "architecture": architecture["classification"],
        "flow": architecture["flow"],
        "summary": summary,
        "overrides": scores["override_rows"],
        "b25": scores["b25_rows"],
        "scored_items": scores["scored_items"],
        "review_flags": scores["review_flags"],
        "review_without_override": scores["review_without_override"],
        "review_flags_all_files": scores["review_flags_all_files"],
        "review_by_credit": scores["review_by_credit"],
        "items_by_scope": scores["items_by_scope"],
        "review_only_by_worksheet": scores["review_only_by_worksheet"],
        "rules": {
            "compared": rules["compared"],
            "exact_agreement": rules["exact_agreement"],
            "mae": rules["mae"],
            "by_worksheet": rules["by_worksheet"],
            "mismatch_count": len(rules["mismatches"]),
            "mismatches": rules["mismatches"],
        },
        "frames": {
            "labelled_frames": frames["labelled_frames"],
            "label_counts": frames["label_counts"],
            "majority_label": frames["majority_label"],
            "majority_count": frames["majority_count"],
            "build_plus_tune_share": frames["build_plus_tune_share"],
            "model_confidence": frames["model_confidence"],
            "low_confidence_frames": frames["low_confidence_frames"],
            "sessions_alignment_method": frames["sessions_alignment_method"],
            "sessions_log_csv_used": frames["sessions_log_csv_used"],
            "independent_coder": False,
        },
        "logs": {
            "sessions": logs["sessions"],
            "sessions_with_timestamp_ms_reset": logs["sessions_with_timestamp_ms_reset"],
            "sessions_whose_interval_counts_differ_by_clock": logs["sessions_whose_interval_counts_differ_by_clock"],
            "sessions_whose_interval_sequence_differs": logs["sessions_whose_interval_sequence_differs"],
            "interval_sequence_difference_sessions": logs["interval_sequence_difference_sessions"],
            "timestamp_ms_totals": logs["timestamp_ms_totals"],
            "wall_clock_totals": logs["wall_clock_totals"],
            "only_threshold_wall": logs["only_threshold_wall"],
            "only_threshold_wall_with_no_other_config_action": logs["only_threshold_wall_with_no_other_config_action"],
            "only_threshold_wall_with_changed_numeric_emit_field": logs["only_threshold_wall_with_changed_numeric_emit_field"],
            "numeric_emit_fields_that_changed": logs["numeric_emit_fields_that_changed"],
            "action_class_counts": logs["action_class_counts"],
        },
        "alignment": {
            "defensible_frame_match": alignment["defensible_frame_match"],
            "matches_emitted": alignment["matches_emitted"],
            "decision": alignment["decision"],
        },
        "notebooks": {
            "submissions": notebooks["submissions"],
            "notebooks": notebooks["notebooks"],
            "reports": notebooks["reports"],
            "task_found": notebooks["task_found"],
            "task_denominator": notebooks["task_denominator"],
            "models": notebooks["models"],
            "models_with_stored_test_mcr": notebooks["models_with_stored_test_mcr"],
            "split_recorded": notebooks["split_recorded"],
            "synthetic_flags": notebooks["synthetic_flags"],
        },
        "triangulation": {
            "participants": cross["participants"],
            "participants_with_a_worksheet_extraction": cross["participants_with_a_worksheet_extraction"],
            "paired_sessions": cross["paired_sessions"],
            "paired_with_both_threshold_signals": cross["paired_with_both_threshold_signals"],
            "paired_tune_label_without_threshold_event": cross["paired_tune_label_without_threshold_event"],
            "paired_threshold_event_without_tune_label": cross["paired_threshold_event_without_tune_label"],
            "paired_with_neither_threshold_signal": cross["paired_with_neither_threshold_signal"],
            "paired_sessions_without_labels": cross["paired_sessions_without_labels"],
            "select_target_labels": cross["select_target_labels"],
            "target_setting_events": cross["target_setting_events"],
            "matrix": cross["matrix"],
        },
        "matrix": [
            {
                "component": row["component"],
                "status": row["analysis_status"],
                "result": row["result"],
                "limitations": row["limitations"],
            }
            for row in matrix
        ],
    }
    SITE.write_text("window.EVALUATION = " + json.dumps(public, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
