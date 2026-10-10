"""
Score WS12 for all students using assess_worksheet_dt().

WS12 (Food dataset CODAP session) requires behavioural log features derived
from the April 21 CODAP event log. This script:

  1. Runs log_extractor.run() against the April 21 Food CSV.
  2. Bridges the emit_snapshots output to the final_accuracy / final_train_*
     fields expected by assess_worksheet_dt().
  3. Loads each student's existing extraction.json (never modified).
  4. Calls assess_worksheet_dt() to produce item-level scores.
  5. Saves via save_scoring_bundle() — only writes scoring.json + evidence.json,
     never touches extraction.json.

Guards:
  - Skips any student whose extraction.json is missing.
  - Skips (or errors) if scoring.json already exists, unless --force is passed.
  - Skips if log features are missing (Melinda, Serena).
  - Never converts missing responses to zero scores.

Run:
    python scripts/score_ws12.py [--dry-run] [--force] [--students Amy Bruno ...]
"""

import argparse
import json
import logging
import os
import sys
import traceback
import unicodedata
from pathlib import Path
from datetime import datetime, timezone

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from student_bundle import load_artifact, save_scoring_bundle, extraction_responses
from worksheet_assessor import assess_worksheet_dt
import log_extractor

STUDENTS_DIR = REPO / "students"
FOOD_LOG_CSV = (
    REPO
    / "data_sources_2026"
    / "All Documents"
    / "21 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv"
)
WORKSHEET = "WS12"
LOG_FILE_ID = "codap_food_log_21apr2026"

ALL_STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel",
    "Marco", "Marcus", "Nadia", "Shana", "Sheila", "Ulysses", "Zara",
]

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _normalise_id(raw: str) -> str:
    """Mirror log_extractor._normalise_id for canonical-key matching."""
    _TURKISH_I_MAP = str.maketrans({"I": "ı", "İ": "i"})
    s = str(raw).strip().translate(_TURKISH_I_MAP)
    s = unicodedata.normalize("NFC", s)
    return s.casefold()


def _bridge_log_features(record: dict) -> dict:
    """
    Build a log_features dict for assess_worksheet_dt() from a
    log_extractor record.

    final_accuracy and final_train_* are not top-level fields in the
    extractor output. They are derived here from the last non-zero
    emit_snapshot. When no valid snapshot exists, the values remain None.
    """
    snaps = record.get("emit_snapshots", [])
    valid_snaps = [s for s in snaps if s.get("accuracy", 0) > 0 or s.get("tp", 0) > 0]
    last = valid_snaps[-1] if valid_snaps else None

    return {
        "final_accuracy": last["accuracy"] if last else None,
        "max_tree_depth_reached": record.get("max_tree_depth_reached"),
        "train_test_applied": record.get("train_test_applied", False),
        "threshold_change_count": record.get("threshold_change_count", 0),
        "final_train_tp": last["tp"] if last else None,
        "final_train_tn": last["tn"] if last else None,
        "final_train_fp": last["fp"] if last else None,
        "final_train_fn": last["fn"] if last else None,
        # Extras kept for audit
        "emit_count": record.get("emit_count", 0),
        "valid_emit_count": record.get("valid_emit_count", 0),
        "train_test_indeterminate": record.get("train_test_indeterminate", False),
        "exploration_index": record.get("exploration_index"),
        "data_sufficiency": record.get("data_sufficiency"),
        "analyst_flags": record.get("analyst_flags", []),
    }


def _load_log_feature_map() -> dict[str, dict]:
    """
    Return {canonical_folder_name: log_features_dict} for WS12 students.

    Folder names use the raw pseudonym (Amy, Iris, …). The log uses Turkish
    I-normalised keys (ıris, ırma, ısabel). This function bridges the two
    by normalising both sides.
    """
    logger.info("Running log_extractor against %s", FOOD_LOG_CSV.name)
    records = log_extractor.run(
        csv_path=str(FOOD_LOG_CSV),
        log_file_id=LOG_FILE_ID,
    )
    # Build normalised_key -> record mapping
    raw_map: dict[str, dict] = {r["student_id"]: r for r in records}

    result: dict[str, dict] = {}
    for folder_name in ALL_STUDENTS:
        norm_key = _normalise_id(folder_name)
        if norm_key in raw_map:
            result[folder_name] = _bridge_log_features(raw_map[norm_key])
        else:
            # Try direct case-fold match
            for k, v in raw_map.items():
                if k == norm_key:
                    result[folder_name] = _bridge_log_features(v)
                    break
    return result


def score_student(
    student_id: str,
    client,
    log_features: dict,
    model: str,
    dry_run: bool,
    force: bool,
) -> str:
    """
    Score WS12 for one student. Returns a status string.
    """
    ext_path = STUDENTS_DIR / student_id / WORKSHEET / "extraction.json"
    scoring_path = STUDENTS_DIR / student_id / WORKSHEET / "scoring.json"

    if not ext_path.exists():
        return "SKIP_NO_EXTRACTION"

    if scoring_path.exists() and not force:
        return "SKIP_ALREADY_SCORED"

    if not log_features:
        return "SKIP_NO_LOG_FEATURES"

    if log_features.get("final_accuracy") is None:
        logger.warning(
            "%s WS12: log features present but final_accuracy=None "
            "(no valid emit snapshots). Scoring will proceed with None.",
            student_id,
        )

    if dry_run:
        extraction = load_artifact(student_id, WORKSHEET, "extraction", STUDENTS_DIR)
        responses = extraction_responses(extraction)
        non_extracted = sum(1 for v in responses.values() if "(not_extracted)" in str(v))
        return (
            f"DRY_RUN OK: {len(responses)} items, "
            f"{non_extracted} not_extracted, "
            f"final_acc={log_features.get('final_accuracy')}, "
            f"depth={log_features.get('max_tree_depth_reached')}"
        )

    extraction = load_artifact(student_id, WORKSHEET, "extraction", STUDENTS_DIR)
    responses = extraction_responses(extraction)

    scoring = assess_worksheet_dt(
        client=client,
        student_id=student_id,
        responses=responses,
        model=model,
        log_features=log_features,
    )

    save_scoring_bundle(student_id, WORKSHEET, scoring, base_dir=STUDENTS_DIR)
    item_count = len(scoring.get("items", {}))
    return f"SCORED: {item_count} items"


def main():
    parser = argparse.ArgumentParser(description="Score WS12 using CODAP log features.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="Re-score even if scoring.json already exists")
    parser.add_argument("--students", nargs="+", default=None,
                        metavar="STUDENT")
    parser.add_argument("--model", default="claude-opus-4-5")
    args = parser.parse_args()

    students = args.students if args.students else ALL_STUDENTS
    unknown = [s for s in students if s not in ALL_STUDENTS]
    if unknown:
        logger.error("Unknown students: %s", unknown)
        sys.exit(1)

    if not FOOD_LOG_CSV.exists():
        logger.error("Food log CSV not found: %s", FOOD_LOG_CSV)
        sys.exit(1)

    log_feature_map = _load_log_feature_map()

    if args.dry_run:
        print("\nDRY RUN — no files will be written.\n")
        for student in students:
            lf = log_feature_map.get(student, {})
            status = score_student(student, None, lf, args.model, dry_run=True, force=args.force)
            print(f"  {student:12s} {WORKSHEET}: {status}")
        print("\nDone (dry run).")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set. Cannot run LLM scoring.")
        sys.exit(1)

    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = REPO / "logs"
    log_dir.mkdir(exist_ok=True)
    audit_path = log_dir / f"score_ws12_{run_id}.jsonl"

    results = {}
    for student in students:
        lf = log_feature_map.get(student, {})
        try:
            status = score_student(
                student, client, lf, args.model, dry_run=False, force=args.force
            )
        except Exception as exc:
            status = f"ERROR: {exc}"
            logger.error("%s WS12 failed: %s", student, traceback.format_exc())

        results[student] = status
        print(f"  {student:12s} {WORKSHEET}: {status}")

        entry = {
            "run_id": run_id,
            "student": student,
            "worksheet": WORKSHEET,
            "status": status,
            "model": args.model,
            "log_features_summary": {
                "final_accuracy": lf.get("final_accuracy") if lf else None,
                "max_tree_depth_reached": lf.get("max_tree_depth_reached") if lf else None,
                "train_test_applied": lf.get("train_test_applied") if lf else None,
                "threshold_change_count": lf.get("threshold_change_count") if lf else None,
            },
        }
        with open(audit_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    scored = sum(1 for s in results.values() if s.startswith("SCORED"))
    skipped = sum(1 for s in results.values() if s.startswith("SKIP"))
    errors = sum(1 for s in results.values() if s.startswith("ERROR"))
    print(f"\nDone. scored={scored} skipped={skipped} errors={errors}")
    print(f"Audit log: {audit_path}")


if __name__ == "__main__":
    main()
