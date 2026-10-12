"""Checks for the read-only evaluation calculations."""
from __future__ import annotations

import json
from pathlib import Path

from evaluation.analysis import (
    alignment_feasibility,
    frame_labels,
    item_class,
    log_sequences,
    rule_reproducibility,
    score_history,
    wall_intervals,
)

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {
    "Completed",
    "Partially completed",
    "Requires human validation",
    "Not applicable",
}


def test_item_class_does_not_treat_missing_as_zero():
    assert item_class(None) == "unavailable"
    assert item_class(0) == "no_credit"
    assert item_class(0.5) == "partial"
    assert item_class(1) == "full_credit"


def test_accepted_changes_are_five_ws5_b25_rows():
    history = score_history()
    overrides = history["override_rows"]
    assert history["accepted_overrides"] == 5
    assert history["scored_items"] == 2367
    assert {row["item"] for row in overrides} == {"WS5_B25"}
    assert {row["worksheet"] for row in overrides} == {"WS5"}
    assert all(row["rationale"] for row in overrides)
    assert history["overrides_with_prior_score"] == 0
    assert history["review_and_override"] == 5
    assert all(row["review_flag_still_set"] for row in overrides)


def test_review_flag_without_override_is_counted_separately():
    history = score_history()
    assert history["review_without_override"] == 1565
    assert history["review_flags"] == history["review_without_override"] + history["review_and_override"]
    partial = history["review_by_credit"]["partial"]
    assert partial["review_flag"] <= partial["items"]
    assert partial["items"] == 891


def test_rule_agreement_uses_paired_items_only():
    rules = rule_reproducibility()
    assert rules["compared"] == 201
    assert rules["exact_agreement"] == 189
    assert rules["exact_agreement"] <= rules["compared"]
    gap = sum(abs(row["scoring"] - row["validation"]) for row in rules["mismatches"])
    assert abs(rules["mae"] - gap / rules["compared"]) < 1e-9
    b25_gaps = [row for row in rules["mismatches"] if row["item"] == "WS5_B25"]
    assert len(b25_gaps) == 6
    assert all(row["scoring"] == 0 and row["validation"] == 1 for row in b25_gaps)
    changed = {"Bruno", "Helena", "Isabel", "Melinda", "Ulysses"}
    assert changed.isdisjoint({row["student"] for row in b25_gaps})


def test_wall_clock_interval_sees_a_reset_that_timestamp_order_can_miss():
    events = [
        {"action": "emit_tree_data", "timestamp_ms": "100", "created_at": "2026-04-21T10:00:00+00:00", "parameters": "{}"},
        {"action": "change_split_values", "timestamp_ms": "10", "created_at": "2026-04-21T10:00:05+00:00", "parameters": "{}"},
        {"action": "emit_tree_data", "timestamp_ms": "40", "created_at": "2026-04-21T10:00:10+00:00", "parameters": "{}"},
    ]
    kinds = [row["kind"] for row in wall_intervals(events)]
    assert kinds == ["only_threshold"]


def test_no_frame_is_matched_to_a_log_row():
    frames = frame_labels()
    logs = log_sequences()
    alignment = alignment_feasibility(logs, frames)
    assert frames["labelled_frames"] == 5248
    assert frames["label_counts"].get("SELECT_TARGET", 0) == 0
    assert logs["sessions_whose_interval_counts_differ_by_clock"] == 0
    assert logs["sessions_whose_interval_sequence_differs"] == 2
    assert alignment["matches_emitted"] == 0
    assert alignment["defensible_frame_match"] is False


def test_published_matrix_uses_only_allowed_statuses():
    matrix = json.loads((ROOT / "evaluation" / "results" / "evaluation_matrix.json").read_text(encoding="utf-8"))
    assert {row["analysis_status"] for row in matrix} <= ALLOWED
    retrieval = next(row for row in matrix if row["component"] == "Retrieval")
    assert retrieval["analysis_status"] == "Not applicable"
    site = (ROOT / "mmla_explorer" / "site" / "data" / "evaluation.js").read_text(encoding="utf-8")
    assert site.startswith("window.EVALUATION = ")
    payload = json.loads(site.split("=", 1)[1].rstrip().rstrip(";"))
    assert payload["summary"]["accepted_overrides"] == 5
    assert payload["rules"]["exact_agreement"] == 189
    assert payload["alignment"]["matches_emitted"] == 0
