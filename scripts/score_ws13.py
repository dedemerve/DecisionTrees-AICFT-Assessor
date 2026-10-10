"""
Score WS13 for all students using assess_worksheet_dt().

WS13 (Food dataset CODAP session) requires behavioural log features derived
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
from worksheet_assessor import assess_worksheet_dt, scoring_item_ids, load_rubric
from rubric_deterministic import score_from_credit
import log_extractor

STUDENTS_DIR = REPO / "students"
FOOD_LOG_CSV = (
    REPO
    / "data_sources_2026"
    / "All Documents"
    / "21 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv"
)
WORKSHEET = "WS13"
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
    Return {canonical_folder_name: log_features_dict} for WS13 students.

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
    Score WS13 for one student. Returns a status string.
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
            "%s WS13: log features present but final_accuracy=None "
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

    assessment = assess_worksheet_dt(
        client=client,
        candidate_id=student_id,
        responses=responses,
        model=model,
        log_features=log_features,
    )

    rubric_items = load_rubric(WORKSHEET).get("items", {})
    items_out = []
    total = 0.0
    max_total = 0.0
    for item in assessment.item_scores:
        cfg = rubric_items.get(item.item_id, {})
        max_score = float(cfg.get("max_score", 1))
        max_total += max_score
        score = score_from_credit({"credit": item.credit}, max_score)
        total += score
        items_out.append({
            "item": item.item_id,
            "score": score,
            "max_score": max_score,
            "confidence": 1.0 if item.credit == "full" and not item.flag else 0.6,
            "review": item.credit in {"partial", "zero"} or item.flag is not None,
            "credit": item.credit,
            "rationale": item.llm_rationale,
            "evidence": item.evidence_quote,
            "flag": item.flag,
        })

    scoring = {
        "stage": "scoring",
        "student_id": student_id,
        "worksheet": WORKSHEET,
        "total_score": round(total, 2),
        "max_score": round(max_total, 2),
        "items": items_out,
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "scoring_model": model,
    }
    save_scoring_bundle(student_id, WORKSHEET, scoring, base_dir=STUDENTS_DIR)
    return f"SCORED: {len(items_out)} items"


def _load_api_key() -> str:
    """
    Return a clean ASCII API key.
    Checks ANTHROPIC_API_KEY env var first; if it contains non-ASCII chars
    (e.g. bullet placeholders from a masked copy-paste), falls back to the
    .env file in the repo root. Creates .env with instructions if missing.
    """
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    try:
        key.encode("ascii")
        if key:
            return key
    except UnicodeEncodeError:
        logger.warning(
            "ANTHROPIC_API_KEY in environment contains non-ASCII characters "
            "(probably copied while masked). Falling back to .env file."
        )

    env_path = REPO / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("ANTHROPIC_API_KEY="):
                candidate = line.split("=", 1)[1].strip().strip("'\"")
                try:
                    candidate.encode("ascii")
                    if candidate:
                        return candidate
                except UnicodeEncodeError:
                    pass
    else:
        env_path.write_text(
            "# Add your Anthropic API key here (paste the real key, not a masked copy)\n"
            "ANTHROPIC_API_KEY=\n",
            encoding="utf-8",
        )
        logger.error(
            "Created %s — paste your real API key there, then re-run.", env_path
        )
    return ""


def main():
    parser = argparse.ArgumentParser(description="Score WS13 using CODAP log features.")
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

    api_key = _load_api_key()
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set. Add it to .env or export it.")
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
            logger.error("%s WS13 failed: %s", student, traceback.format_exc())

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
