"""
Recover WS3 and WS4 scoring from existing OCR json files.

Problem: extraction.json for WS3/WS4 was created with all items set to
(not_extracted). The correct responses are already in:
  ocr_output/<student>/<student>_Worksheet3.json
  ocr_output/<student>/<student>_Worksheet4.json

This script:
  1. Reads the OCR json for each student and worksheet.
  2. Builds an extraction record in memory (same structure as gate_1_extraction).
  3. Saves it to extraction_from_ocr.json (NEW file — never overwrites extraction.json).
  4. Calls assess_worksheet() for LLM scoring.
  5. Saves scoring.json via save_scoring_bundle().

Guards:
  - Skips if OCR json is missing (Amy, Marco — physically absent from PDFs).
  - Skips if scoring.json already exists, unless --force is passed.
  - Never touches the original extraction.json.
  - Never converts (not_extracted) values to zero scores.

Run:
    python scripts/recover_ws3_ws4_from_ocr.py [--dry-run] [--force]
      [--students Amy Bruno ...] [--worksheets WS3 WS4]
"""

import argparse
import json
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from student_bundle import save_scoring_bundle
from worksheet_assessor import assess_worksheet
from pipeline_schema import load_rubric, scoring_item_ids
from rubric_deterministic import score_from_credit

STUDENTS_DIR = REPO / "students"
OCR_OUTPUT_DIR = REPO / "ocr_output"

ALL_STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel",
    "Marco", "Marcus", "Melinda", "Nadia", "Serena", "Shana", "Sheila",
    "Ulysses", "Zara",
]

WS3_ITEM_IDS = ["WS3_B1", "WS3_B2", "WS3_B3", "WS3_B4",
                "WS3_B5", "WS3_B6", "WS3_B7", "WS3_B8"]
WS4_ITEM_IDS = ["WS4_B1", "WS4_B2", "WS4_B3", "WS4_B4", "WS4_B5"]

WORKSHEET_ITEMS = {
    "WS3": WS3_ITEM_IDS,
    "WS4": WS4_ITEM_IDS,
}

OCR_FILENAME = {
    "WS3": "{student}_Worksheet3.json",
    "WS4": "{student}_Worksheet4.json",
}

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _read_ocr_json(student: str, worksheet: str) -> dict | None:
    """
    Read the OCR json for a student/worksheet pair.
    Returns the raw dict, or None if the file does not exist.
    """
    filename = OCR_FILENAME[worksheet].format(student=student)
    path = OCR_OUTPUT_DIR / student / filename
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _extract_responses(ocr_data: dict, item_ids: list[str]) -> dict[str, str]:
    """
    Pull item responses from OCR json.

    WS3 stores items at top level (WS3_B1, WS3_B2, ...).
    WS4 stores items under an 'extraction' key.
    Falls back to top-level if 'extraction' key is absent.
    """
    source = ocr_data.get("extraction", ocr_data)
    responses = {}
    for iid in item_ids:
        val = source.get(iid)
        if val is None:
            val = ocr_data.get(iid)
        if val is not None:
            responses[iid] = str(val).strip() or "(bos)"
        else:
            responses[iid] = "(not_extracted)"
    return responses


def _build_extraction_record(
    student: str, worksheet: str, responses: dict[str, str], ocr_path: Path
) -> dict:
    """
    Build an extraction artifact in the gate_1_extraction format.
    This is written to extraction_from_ocr.json — NOT extraction.json.
    """
    return {
        "gate_1_extraction": {
            "status": "pass_from_ocr_recovery",
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "ocr_model": "recovered_from_ocr_output",
            "source_file": str(ocr_path.relative_to(REPO)),
            "items": responses,
            "raw_ocr": {},
        }
    }


def recover_student(
    student: str,
    worksheet: str,
    client,
    model: str,
    dry_run: bool,
    force: bool,
) -> str:
    ocr_data = _read_ocr_json(student, worksheet)
    if ocr_data is None:
        return "SKIP_NO_OCR_FILE"

    scoring_path = STUDENTS_DIR / student / worksheet / "scoring.json"
    if scoring_path.exists() and not force:
        return "SKIP_ALREADY_SCORED"

    item_ids = WORKSHEET_ITEMS[worksheet]
    responses = _extract_responses(ocr_data, item_ids)

    not_extracted = sum(1 for v in responses.values() if v == "(not_extracted)")
    populated = len(item_ids) - not_extracted

    ocr_filename = OCR_FILENAME[worksheet].format(student=student)
    ocr_path = OCR_OUTPUT_DIR / student / ocr_filename

    if dry_run:
        return (
            f"DRY_RUN OK: {populated}/{len(item_ids)} items populated, "
            f"{not_extracted} not_extracted"
        )

    # Save the bridged extraction record (new file — does not touch extraction.json)
    ws_dir = STUDENTS_DIR / student / worksheet
    ws_dir.mkdir(parents=True, exist_ok=True)
    extraction_record = _build_extraction_record(student, worksheet, responses, ocr_path)
    recovery_path = ws_dir / "extraction_from_ocr.json"
    with open(recovery_path, "w") as f:
        json.dump(extraction_record, f, ensure_ascii=False, indent=2)

    assessment = assess_worksheet(
        client=client,
        candidate_id=student,
        worksheet_id=worksheet,
        responses=responses,
        model=model,
    )

    rubric_items = load_rubric(worksheet).get("items", {})
    items_out = []
    total = 0.0
    max_total = 0.0
    n_review = 0

    for item in assessment.item_scores:
        cfg = rubric_items.get(item.item_id, {})
        max_score = float(cfg.get("max_score", 1))
        max_total += max_score
        score = score_from_credit({"credit": item.credit}, max_score)
        total += score
        needs_review = item.credit in {"partial", "zero"} or item.flag is not None
        if needs_review:
            n_review += 1
        items_out.append({
            "item": item.item_id,
            "score": score,
            "max_score": max_score,
            "confidence": 1.0 if item.credit == "full" and not item.flag else 0.6,
            "review": needs_review,
            "credit": item.credit,
            "rationale": item.llm_rationale,
            "evidence": item.evidence_quote,
            "flag": item.flag,
        })

    scoring = {
        "stage": "scoring",
        "student_id": student,
        "worksheet": worksheet,
        "total_score": round(total, 2),
        "max_score": round(max_total, 2),
        "items": items_out,
        "note": (
            f"LLM-scored via recover_ws3_ws4_from_ocr (model={model}); "
            f"{n_review} item(s) flagged for review. "
            f"Responses read from extraction_from_ocr.json."
        ),
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "scoring_model": model,
    }

    save_scoring_bundle(student, worksheet, scoring, base_dir=STUDENTS_DIR)
    return f"SCORED: {len(items_out)} items (extraction_from_ocr.json written)"


def main():
    parser = argparse.ArgumentParser(
        description="Recover WS3/WS4 scoring from OCR output files."
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="Re-score even if scoring.json already exists")
    parser.add_argument("--students", nargs="+", default=None, metavar="STUDENT")
    parser.add_argument(
        "--worksheets", nargs="+", default=["WS3", "WS4"],
        choices=["WS3", "WS4"], metavar="WS",
    )
    parser.add_argument("--model", default="claude-opus-4-5")
    args = parser.parse_args()

    students = args.students if args.students else ALL_STUDENTS
    unknown = [s for s in students if s not in ALL_STUDENTS]
    if unknown:
        logger.error("Unknown students: %s", unknown)
        sys.exit(1)

    if args.dry_run:
        print("\nDRY RUN — no files will be written.\n")
        for student in students:
            for ws in args.worksheets:
                status = recover_student(student, ws, None, args.model,
                                         dry_run=True, force=args.force)
                print(f"  {student:12s} {ws}: {status}")
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
    audit_path = log_dir / f"recover_ws3_ws4_{run_id}.jsonl"

    results = {}
    for student in students:
        for ws in args.worksheets:
            key = f"{student}/{ws}"
            try:
                status = recover_student(
                    student, ws, client, args.model,
                    dry_run=False, force=args.force,
                )
            except Exception as exc:
                status = f"ERROR: {exc}"
                logger.error("%s %s failed: %s", student, ws, traceback.format_exc())

            results[key] = status
            print(f"  {student:12s} {ws}: {status}")

            entry = {
                "run_id": run_id,
                "student": student,
                "worksheet": ws,
                "status": status,
                "model": args.model,
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
