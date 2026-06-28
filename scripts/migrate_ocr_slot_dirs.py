#!/usr/bin/env python3
"""
Rename ocr_output/_images/{pdf_stem}/slot_NN folders to student pseudonyms.

Uses calibration/pdf_student_order.json. Safe to re-run (skips existing targets).

  python scripts/migrate_ocr_slot_dirs.py
  python scripts/migrate_ocr_slot_dirs.py --pdf WorksheetDT.pdf
  python scripts/migrate_ocr_slot_dirs.py --calibration-only
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pipeline_schema import (  # noqa: E402
    OCR_IMAGES_DIR,
    OCR_OUTPUT_DIR,
    calibration_bundle_dir,
    dry_run_folder_name,
    load_pdf_student_order_doc,
    pdf_to_images_stem,
)


def migrate_pdf(pdf_name: str, *, dry_run: bool = False) -> list[str]:
    pdf_stem = pdf_to_images_stem(pdf_name)
    base = OCR_IMAGES_DIR / pdf_stem
    if not base.is_dir():
        return []

    actions: list[str] = []
    slot_dirs = sorted(base.glob("slot_*"))
    for slot_dir in slot_dirs:
        if not slot_dir.is_dir():
            continue
        try:
            slot_num = int(slot_dir.name.replace("slot_", "").split("_")[0])
        except ValueError:
            continue
        target_name = dry_run_folder_name(pdf_name, slot_num - 1)
        if target_name == slot_dir.name:
            continue
        target = base / target_name
        if target.exists():
            actions.append(f"SKIP {slot_dir.name} -> {target_name} (exists)")
            continue
        actions.append(f"MOVE {slot_dir} -> {target}")
        if not dry_run:
            shutil.move(str(slot_dir), str(target))
            marker = OCR_OUTPUT_DIR / f".{target_name}_{pdf_stem}"
            marker.write_text(str(slot_num))
    return actions


def migrate_calibration_bundle(*, dry_run: bool = False) -> list[str]:
    doc = load_pdf_student_order_doc()
    cal = doc.get("calibration_bundle", {})
    legacy = OCR_IMAGES_DIR / cal.get("legacy_dir", "_slot31_check")
    if not legacy.is_dir():
        return []

    pdf_name = cal.get("pdf", "Worksheets1-10.pdf")
    student_key = cal.get("student_key", "Felicity")
    target = OCR_IMAGES_DIR / pdf_to_images_stem(pdf_name) / student_key
    if target.exists():
        return [f"SKIP calibration {legacy} -> {target} (exists)"]
    action = f"MOVE {legacy} -> {target}"
    if not dry_run:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(legacy), str(target))
        marker = OCR_OUTPUT_DIR / f".{student_key}_{pdf_to_images_stem(pdf_name)}"
        marker.write_text(cal.get("slot_overrides", {}).get(pdf_name, {}).get("31", "31"))
    return [action]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rename OCR slot_* dirs to pseudonyms")
    parser.add_argument("--pdf", action="append", help="PDF name (repeatable)")
    parser.add_argument("--calibration-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    actions: list[str] = []
    if args.calibration_only:
        actions.extend(migrate_calibration_bundle(dry_run=args.dry_run))
    else:
        actions.extend(migrate_calibration_bundle(dry_run=args.dry_run))
        pdfs = args.pdf or list(load_pdf_student_order_doc().get("pdfs", {}).keys())
        for pdf_name in pdfs:
            actions.extend(migrate_pdf(pdf_name, dry_run=args.dry_run))

    if not actions:
        print("Nothing to migrate.")
        return 0

    for line in actions:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
