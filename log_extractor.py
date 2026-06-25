"""
log_extractor.py

Extracts structured behavioural features from CODAP Arbor CSV log files.
One LogDerivedFeatures record is produced per canonical student identity.

Key design decisions
--------------------
- Identity normalisation uses Unicode NFC + casefold + Turkish dotted-I
  transliteration to merge case/encoding variants of the same name.
- Noise actions (drag events, UI bookkeeping, session events) are excluded
  from all computed ratios. Only pedagogically meaningful actions contribute
  to exploration_index and related metrics.
- Zero-value emit snapshots (TP=TN=FP=FN=0, model not yet built) are excluded
  from accuracy statistics but retained in the full snapshot list for audit.
- Train/test detection is dataset-name-based. When dataset naming does not
  unambiguously encode train vs. test (e.g. Food datasets), the result is
  flagged as indeterminate rather than silently misclassified.
- set_dependent_variable fires automatically in CODAP on every tree refresh.
  It is NOT a reliable signal of the user deliberately changing the target.
  It is counted for completeness but not used in flags or sufficiency logic.
- Multi-session students (same identity, multiple calendar dates) have
  duration summed per day to avoid inflated single-session estimates.
"""

from __future__ import annotations

import json
import logging
import unicodedata
from datetime import datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────

MEANINGFUL_ACTIONS: frozenset[str] = frozenset({
    "change_split_values",
    "drop_attribute",
    "set_dependent_variable",
    "emit_tree_data",
    "refresh_tree",
    "change_tree_type",
    "swap_focus_split",
    "set_focus_node",
})

# Dataset name fragments that unambiguously signal a test split.
# Only applies when the researcher used explicit train/test labelling
# in dataset names (e.g. titanic_egitim vs titanic_test).
# Food dataset variants do NOT follow this convention — flagged separately.
TRAIN_DATASET_FRAGMENTS: frozenset[str] = frozenset({"egitim", "train", "trn"})
TEST_DATASET_FRAGMENTS: frozenset[str] = frozenset({"test", "tst", "val"})

# Dataset name prefixes where train/test cannot be determined from the name alone.
# These require researcher annotation.
AMBIGUOUS_DATASET_PREFIXES: frozenset[str] = frozenset({"food_dataset_turkish"})

# Turkish capital dotted-I (İ) does not round-trip through .lower() in Python.
# İ → lower → i̇ (i + U+0307 combining dot above), not plain i.
# This mapping corrects that before normalisation.
_TURKISH_I_MAP = str.maketrans({"İ": "i", "I": "ı"})

# Researcher-confirmed identity overrides.
# Key: normalised raw_id that should be merged into the value (canonical target).
# Add new entries here when the researcher confirms two IDs are the same person.
# Format: _normalise_id(raw) -> canonical_id to merge into
IDENTITY_OVERRIDES: dict[str, str] = {
    "merve": "merve dede",
    # "şeyda": "şeyda demirci",  # PENDING researcher decision
}


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _parse_parameters(raw: str) -> dict:
    """Return parsed JSON parameters. Returns empty dict on any failure."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return {}


def _normalise_id(raw_id: str) -> str:
    """
    Produce a canonical identity key from a raw student_id string.

    Steps:
    1. Strip leading/trailing whitespace.
    2. Apply Turkish dotted-I transliteration (İ→i, I→ı) before casefolding.
    3. NFC Unicode normalisation to collapse combining characters.
    4. Casefold (Unicode-aware lowercase).
    """
    s = str(raw_id).strip()
    s = s.translate(_TURKISH_I_MAP)
    s = unicodedata.normalize("NFC", s)
    return s.casefold()


def _classify_dataset(dataset_name: str) -> str:
    """
    Return 'train', 'test', or 'ambiguous' based on the dataset name.

    'ambiguous' is returned when the naming convention does not encode
    train/test membership. Callers must not infer train_test_applied=True
    from ambiguous datasets.
    """
    name = dataset_name.lower()
    if any(f in name for f in AMBIGUOUS_DATASET_PREFIXES):
        return "ambiguous"
    if any(f in name for f in TEST_DATASET_FRAGMENTS):
        return "test"
    if any(f in name for f in TRAIN_DATASET_FRAGMENTS):
        return "train"
    return "ambiguous"


def _threshold_value(params: dict) -> Optional[str]:
    """
    Return a canonical string for a threshold split value.
    Numeric splits use new_value; categorical splits use new_categories.
    Returns None when neither field is populated.
    """
    if params.get("new_value") is not None:
        return str(params["new_value"])
    categories = params.get("new_categories")
    if categories is not None:
        return f"cat:{categories}"
    return None


def _is_valid_emit(params: dict) -> bool:
    """
    Return True only when the emit snapshot represents a fully built model.
    Emits where all confusion-matrix cells are zero indicate the model has
    not been constructed yet. These must not contribute to accuracy stats.
    """
    return not (
        params.get("TP", 0) == 0
        and params.get("TN", 0) == 0
        and params.get("FP", 0) == 0
        and params.get("FN", 0) == 0
    )


def _session_duration_minutes(student_df: pd.DataFrame) -> float:
    """
    Sum active duration across all calendar dates for one student.
    Per-day duration = last_event_time - first_event_time for that day.
    Avoids inflating duration when a student returns on multiple days.
    """
    df = student_df.copy()
    df["_dt"] = pd.to_datetime(df["created_at"], utc=True)
    df["_date"] = df["_dt"].dt.date
    total_seconds = sum(
        (g["_dt"].max() - g["_dt"].min()).total_seconds()
        for _, g in df.groupby("_date")
    )
    return round(total_seconds / 60, 2)


# ─────────────────────────────────────────────────────────────
# IDENTITY RESOLUTION
# ─────────────────────────────────────────────────────────────

def _apply_overrides(canonical: str) -> str:
    """Apply researcher-confirmed identity overrides after normalisation."""
    return IDENTITY_OVERRIDES.get(canonical, canonical)


def resolve_identities(df: pd.DataFrame) -> dict[str, list[str]]:
    """
    Group raw student_id strings by their canonical form.
    Logs a warning for every canonical identity with more than one raw variant,
    and adds an additional warning when short-name vs full-name ambiguity is
    detected (e.g. 'şeyda' and 'şeyda demirci' share the same first token).

    Returns: canonical_id -> list[raw_id]
    """
    mapping: dict[str, list[str]] = {}
    for raw_id in df["student_id"].unique():
        canonical = _apply_overrides(_normalise_id(str(raw_id)))
        mapping.setdefault(canonical, []).append(str(raw_id))

    for canonical, variants in mapping.items():
        if len(variants) > 1:
            logger.warning(
                "Identity merge: canonical='%s' <- variants=%s",
                canonical, variants,
            )

    # Detect possible first-name-only vs full-name conflicts.
    # Only flag when one canonical key is a strict prefix of another
    # (e.g. 'şeyda' vs 'şeyda demirci'). Two people sharing a first name
    # with different surnames (e.g. 'irem ilze' vs 'irem damar') are not flagged.
    canonical_list = sorted(mapping.keys())
    for i, a in enumerate(canonical_list):
        for b in canonical_list[i + 1:]:
            if b.startswith(a + " ") or a.startswith(b + " "):
                logger.warning(
                    "Possible same-person split: '%s' is a name prefix of '%s' — "
                    "requires researcher validation before merging.",
                    a, b,
                )

    return mapping


# ─────────────────────────────────────────────────────────────
# FEATURE EXTRACTION
# ─────────────────────────────────────────────────────────────

def extract_log_features(
    df: pd.DataFrame,
    canonical_id: str,
    raw_ids: list[str],
    log_file_id: str,
) -> dict:
    """
    Extract behavioural features for one canonical pre-service teacher.

    Returns a plain dict matching the LogDerivedFeatures schema fields.
    Keeps this function schema-agnostic so it can be tested without
    importing the Pydantic model.
    """
    student_df = df[df["_canonical_id"] == canonical_id].copy()
    student_df = student_df.sort_values("timestamp_ms").reset_index(drop=True)

    if student_df.empty:
        logger.warning("No rows found for canonical_id='%s'", canonical_id)
        return _empty_record(log_file_id, canonical_id)

    student_df["_params"] = student_df["parameters"].apply(_parse_parameters)

    # ── Session metadata ──────────────────────────────────────
    session_start_utc = pd.to_datetime(
        student_df["created_at"].iloc[0], utc=True
    ).to_pydatetime()
    session_end_utc = pd.to_datetime(
        student_df["created_at"].iloc[-1], utc=True
    ).to_pydatetime()
    session_duration = _session_duration_minutes(student_df)
    session_date_count = student_df.assign(
        _dt=pd.to_datetime(student_df["created_at"], utc=True)
    )["_dt"].dt.date.nunique()

    # ── Action counts ─────────────────────────────────────────
    total_actions = len(student_df)
    meaningful_df = student_df[student_df["action"].isin(MEANINGFUL_ACTIONS)]
    meaningful_action_count = len(meaningful_df)

    # ── Threshold changes ─────────────────────────────────────
    threshold_df = student_df[student_df["action"] == "change_split_values"]
    threshold_change_count = len(threshold_df)
    unique_thresholds = (
        threshold_df["_params"]
        .apply(_threshold_value)
        .dropna()
        .nunique()
    )

    # ── Feature drops ─────────────────────────────────────────
    feature_df = student_df[student_df["action"] == "drop_attribute"]
    feature_drop_count = len(feature_df)
    unique_features = (
        feature_df["_params"]
        .apply(lambda p: p.get("attribute", ""))
        .replace("", pd.NA)
        .dropna()
        .nunique()
    )

    # ── Target variable ───────────────────────────────────────
    # set_dependent_variable fires automatically on every tree refresh in CODAP.
    # This count reflects CODAP internal events, not deliberate user actions.
    # Stored for completeness only — not used in flags or sufficiency logic.
    target_set_count = len(student_df[student_df["action"] == "set_dependent_variable"])

    # ── Emit snapshots ────────────────────────────────────────
    emit_df = student_df[student_df["action"] == "emit_tree_data"]
    emit_count = len(emit_df)
    all_snapshots: list[dict] = []
    valid_snapshots: list[dict] = []

    for _, row in emit_df.iterrows():
        p = row["_params"]
        accuracy = float(p.get("accuracy", 0.0))
        dataset = p.get("dataset", "")
        classification = _classify_dataset(dataset)
        snap = {
            "emitted_at_ms": int(row["timestamp_ms"]),
            "dataset": dataset,
            "dataset_classification": classification,
            "is_test_dataset": classification == "test",
            "accuracy": accuracy,
            "misclassification_rate": round(1.0 - accuracy, 4),
            "tp": int(p.get("TP", 0)),
            "tn": int(p.get("TN", 0)),
            "fp": int(p.get("FP", 0)),
            "fn": int(p.get("FN", 0)),
            "depth": int(p.get("depth", 0)),
            "node_count": max(int(p.get("node_count", 1)), 1),
            "sample_size": max(int(p.get("sample_size", 1)), 1),
            "dependent_variable": p.get("dependent_variable", ""),
        }
        all_snapshots.append(snap)
        if _is_valid_emit(p):
            valid_snapshots.append(snap)

    # Train/test analysis — only meaningful when dataset names are unambiguous.
    has_ambiguous_datasets = any(
        s["dataset_classification"] == "ambiguous" for s in valid_snapshots
    )
    train_snaps = [s for s in valid_snapshots if s["dataset_classification"] == "train"]
    test_snaps = [s for s in valid_snapshots if s["dataset_classification"] == "test"]

    # train_test_applied is True only when both a labelled training AND a labelled
    # test dataset were emitted with a valid (non-zero) model.
    train_test_applied = bool(train_snaps) and bool(test_snaps)

    last_train_acc: Optional[float] = train_snaps[-1]["accuracy"] if train_snaps else None
    last_test_acc: Optional[float] = test_snaps[-1]["accuracy"] if test_snaps else None
    first_train_acc: Optional[float] = train_snaps[0]["accuracy"] if train_snaps else None
    first_test_acc: Optional[float] = test_snaps[0]["accuracy"] if test_snaps else None

    gap: Optional[float] = None
    if last_train_acc is not None and last_test_acc is not None:
        gap = round(last_train_acc - last_test_acc, 4)

    max_depth = max((s["depth"] for s in valid_snapshots), default=None)

    # ── Other counts ──────────────────────────────────────────
    refresh_count = len(student_df[student_df["action"] == "refresh_tree"])
    tree_type_change_count = len(student_df[student_df["action"] == "change_tree_type"])

    # Detect regression switches: flag only when student ended on regression
    regression_events = student_df[student_df["action"] == "change_tree_type"]["_params"].apply(
        lambda p: p.get("tree_type", "")
    ).tolist()
    ended_on_regression = bool(regression_events) and regression_events[-1] == "regression"

    # ── Exploration index ─────────────────────────────────────
    # Denominator: meaningful actions only (excludes UI noise).
    # undo_count excluded by design: error correction is a distinct construct.
    exploration_index: Optional[float] = None
    if meaningful_action_count > 0:
        exploration_index = round(
            (threshold_change_count + feature_drop_count) / meaningful_action_count,
            4,
        )

    # ── Analyst flags ─────────────────────────────────────────
    analyst_flags: list[str] = []

    if len(raw_ids) > 1:
        analyst_flags.append(f"identity_variants_merged:{len(raw_ids)}")

    if ended_on_regression:
        analyst_flags.append("session_ended_on_regression_tree")
    elif tree_type_change_count > 0:
        analyst_flags.append("switched_to_regression_then_back")

    if has_ambiguous_datasets:
        analyst_flags.append("train_test_indeterminate:ambiguous_dataset_names")

    if emit_count > 0 and len(valid_snapshots) == 0:
        analyst_flags.append("all_emits_were_zero_model")

    # Detect the case where the student emitted on both datasets but
    # the training emit was a zero model (model not yet built at emit time).
    # train_test_applied is correctly False in this case, but the flag
    # gives the researcher context rather than leaving it unexplained.
    labelled_train_emits = [s for s in all_snapshots if s["dataset_classification"] == "train"]
    if labelled_train_emits and not train_snaps:
        analyst_flags.append("train_dataset_emitted_but_model_was_empty")

    if gap is not None and gap > 0.15:
        analyst_flags.append(f"high_train_test_gap:{gap}")

    if session_date_count > 1:
        analyst_flags.append(f"multi_session:{session_date_count}_dates")

    # ── Data sufficiency ──────────────────────────────────────
    if emit_count == 0 and threshold_change_count == 0 and feature_drop_count == 0:
        sufficiency = "insufficient"
    elif has_ambiguous_datasets and not train_test_applied:
        # Student emitted but we cannot confirm train/test was done.
        sufficiency = "partial"
    elif not train_test_applied:
        sufficiency = "partial"
    else:
        sufficiency = "sufficient"

    return {
        "log_file_id": log_file_id,
        "student_id": canonical_id,
        "raw_id_variants": raw_ids,
        "session_start_utc": session_start_utc,
        "session_end_utc": session_end_utc,
        "session_duration_minutes": session_duration,
        "session_date_count": session_date_count,
        "total_actions": total_actions,
        "meaningful_action_count": meaningful_action_count,
        "threshold_change_count": threshold_change_count,
        "unique_thresholds_tried": unique_thresholds,
        "feature_drop_count": feature_drop_count,
        "unique_features_tried": unique_features,
        "target_variable_set_count": target_set_count,
        "emit_count": emit_count,
        "valid_emit_count": len(valid_snapshots),
        "emit_function_used": emit_count >= 1,
        "train_test_applied": train_test_applied,
        "train_test_indeterminate": has_ambiguous_datasets and not train_test_applied,
        "emit_snapshots": all_snapshots,
        "first_train_accuracy": first_train_acc,
        "last_train_accuracy": last_train_acc,
        "first_test_accuracy": first_test_acc,
        "last_test_accuracy": last_test_acc,
        "train_test_accuracy_gap": gap,
        "max_tree_depth_reached": max_depth,
        "refresh_count": refresh_count,
        "tree_type_change_count": tree_type_change_count,
        "ended_on_regression": ended_on_regression,
        "exploration_index": exploration_index,
        "data_sufficiency": sufficiency,
        "analyst_flags": analyst_flags,
    }


def _empty_record(log_file_id: str, student_id: str) -> dict:
    return {
        "log_file_id": log_file_id,
        "student_id": student_id,
        "raw_id_variants": [student_id],
        "session_start_utc": None,
        "session_end_utc": None,
        "session_duration_minutes": 0.0,
        "session_date_count": 0,
        "total_actions": 0,
        "meaningful_action_count": 0,
        "threshold_change_count": 0,
        "unique_thresholds_tried": 0,
        "feature_drop_count": 0,
        "unique_features_tried": 0,
        "target_variable_set_count": 0,
        "emit_count": 0,
        "valid_emit_count": 0,
        "emit_function_used": False,
        "train_test_applied": False,
        "train_test_indeterminate": False,
        "emit_snapshots": [],
        "first_train_accuracy": None,
        "last_train_accuracy": None,
        "first_test_accuracy": None,
        "last_test_accuracy": None,
        "train_test_accuracy_gap": None,
        "max_tree_depth_reached": None,
        "refresh_count": 0,
        "tree_type_change_count": 0,
        "ended_on_regression": False,
        "exploration_index": None,
        "data_sufficiency": "insufficient",
        "analyst_flags": ["no_data_found"],
    }


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

def run(csv_path: str, log_file_id: str) -> list[dict]:
    """
    Load the CSV, resolve identities, and extract features for every student.
    Returns a list of feature dicts sorted by canonical student_id.
    """
    df = pd.read_csv(csv_path)
    identity_map = resolve_identities(df)
    df["_canonical_id"] = df["student_id"].apply(
        lambda x: _apply_overrides(_normalise_id(str(x)))
    )

    results = []
    for canonical_id, raw_ids in sorted(identity_map.items()):
        record = extract_log_features(df, canonical_id, raw_ids, log_file_id)
        results.append(record)

    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    records = run(
        csv_path="/Users/mrved/Downloads/28 Nisan 2026 CODAP Arbor Food Log File.csv",
        log_file_id="codap_food_log_28apr2026",
    )

    header = (
        f"{'student_id':<30} {'dur':>6} {'dates':>5} {'tot':>5} {'mean':>5} "
        f"{'thr':>4} {'uthr':>5} {'fd':>4} {'uft':>4} "
        f"{'emit':>5} {'vem':>4} {'tt':>5} {'indet':>6} "
        f"{'gap':>7} {'dep':>4} {'exp':>6} {'suff':<14} flags"
    )
    print(header)
    print("-" * 180)

    for r in records:
        print(
            f"{r['student_id']:<30} "
            f"{r['session_duration_minutes']:>6.1f} "
            f"{r['session_date_count']:>5} "
            f"{r['total_actions']:>5} "
            f"{r['meaningful_action_count']:>5} "
            f"{r['threshold_change_count']:>4} "
            f"{r['unique_thresholds_tried']:>5} "
            f"{r['feature_drop_count']:>4} "
            f"{r['unique_features_tried']:>4} "
            f"{r['emit_count']:>5} "
            f"{r['valid_emit_count']:>4} "
            f"{str(r['train_test_applied']):>5} "
            f"{str(r['train_test_indeterminate']):>6} "
            f"{str(r['train_test_accuracy_gap']):>7} "
            f"{str(r['max_tree_depth_reached']):>4} "
            f"{str(r['exploration_index']):>6} "
            f"{r['data_sufficiency']:<14} "
            f"{r['analyst_flags']}"
        )
