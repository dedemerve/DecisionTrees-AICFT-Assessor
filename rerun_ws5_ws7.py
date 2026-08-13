#!/usr/bin/env python3
"""
rerun_ws5_ws7.py — Re-extract WS5 and WS7 for all students.

PREREQUISITES
  export ANTHROPIC_API_KEY="sk-..."
  pip install anthropic pypdf pdf2image

WHAT THIS SCRIPT DOES
  WS5  "24 Mart 2026 Çalışma Kâğıdı 5.pdf"
        • Text layer detected: Bruno=p1, Helena=p2, …, Zara=p13 (13 students)
        • Amy and Marco are absent from this PDF (real absence — no fix possible)
        • PAGES_PER_STUDENT entry added to ocr_pipeline.py (already fixed)
        • Runs OCR extraction for all 13 present students, writes extraction.json

  WS7  "31 Mart 2026 Çalışma Kâğıdı 7.pdf"
        • Text layer detected: Amy=p1, Bruno=p2, …, Zara=p13 (13 students)
        • Melinda, Serena, Shana absent from this PDF
        • Page detection works correctly; prior extraction had raw_ocr={} (OCR never ran)
        • Re-runs OCR extraction for all 13 present students

  WS1  "24 Mart 2026 Çalışma Kâğıdı 1.pdf"
        • Bruno=p1 (text layer), pages 2-13 covered by page_name_overrides.json
        • Amy and Marco genuinely absent from this PDF
        • Existing overrides already cover 12 other students (Helena…Zara)
        • No re-run needed for WS1 — existing data is correct.

USAGE
  # Dry run first (no API calls — just image conversion + page detection)
  python3 rerun_ws5_ws7.py --dry-run

  # Full re-extraction (uses Anthropic API)
  python3 rerun_ws5_ws7.py

  # Only WS5 or only WS7
  python3 rerun_ws5_ws7.py --ws5-only
  python3 rerun_ws5_ws7.py --ws7-only

  # Force re-extract even if extraction.json already has gate_status=pass
  python3 rerun_ws5_ws7.py --force
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Repo root is this file's directory
REPO = Path(__file__).parent
sys.path.insert(0, str(REPO))

TARGET_PDFS = {
    "WS5": "24 Mart 2026 Çalışma Kâğıdı 5.pdf",
    "WS7": "31 Mart 2026 Çalışma Kâğıdı 7.pdf",
}

ABSENT_STUDENTS = {
    "WS5": {"Amy", "Marco"},   # not in the 13-page PDF
    "WS7": {"Melinda", "Serena", "Shana"},
    "WS1": {"Amy", "Marco"},
}


def _verify_fixes() -> None:
    """Check that the two code fixes required before re-running are present."""
    pipeline_src = (REPO / "ocr_pipeline.py").read_text()
    if '"24 Mart 2026 Çalışma Kâğıdı 5.pdf": 1' not in pipeline_src:
        print("ERROR: ocr_pipeline.py still missing WS5 entry in PAGES_PER_STUDENT.")
        print("  Fix: add  '\"24 Mart 2026 Çalışma Kâğıdı 5.pdf\": 1'  to the dict.")
        sys.exit(1)

    ws_val_src = (REPO / "worksheet_validation.py").read_text()
    if "WS6_B10" not in ws_val_src:
        print("ERROR: worksheet_validation.py WS6 fix not applied.")
        sys.exit(1)

    print("✓ Code fixes verified (PAGES_PER_STUDENT + worksheet_validation).")


def _dry_run(pdfs: list[str]) -> None:
    # Lazy import — ocr_pipeline imports anthropic at module level;
    # run detect_student_page_ranges standalone to avoid that dependency.
    import re
    import json
    from pypdf import PdfReader

    data_dir = REPO / "data_sources_2026" / "All Documents"
    overrides_path = REPO / "calibration" / "page_name_overrides.json"
    known = frozenset({"Amy","Bruno","Helena","Isabel","Irma","Iris","Marco","Marcus",
                       "Melinda","Nadia","Serena","Sheila","Shana","Ulysses","Zara"})

    try:
        all_overrides = json.loads(overrides_path.read_text())
    except Exception:
        all_overrides = {}

    for pdf_name in pdfs:
        print(f"\n=== DRY RUN: {pdf_name} ===")
        pdf_path = data_dir / pdf_name
        if not pdf_path.exists():
            print(f"  ERROR: PDF not found at {pdf_path}")
            continue
        reader = PdfReader(str(pdf_path))
        overrides = {int(k): v for k, v in all_overrides.get(pdf_name, {}).items()}
        names_by_length = sorted(known, key=lambda n: (-len(n), n))
        page_owner: list[str | None] = []
        for i, page in enumerate(reader.pages, 1):
            if i in overrides:
                page_owner.append(overrides[i])
                continue
            text = page.extract_text() or ""
            fused = re.sub(r"[^A-Za-z]", "", text)
            found = [n for n in names_by_length if n in fused]
            page_owner.append(found[0] if len(found) == 1 else None)
        # Build groups
        groups: list[dict] = []
        cur = None; start = 1
        for i, owner in enumerate(page_owner, 1):
            name = owner or cur
            if cur is not None and name != cur:
                groups.append({"student": cur, "start": start, "end": i-1})
                start = i
            cur = name
        if cur:
            groups.append({"student": cur, "start": start, "end": len(page_owner)})
        print(f"  {len(reader.pages)} pages → {len(groups)} detected student groups:")
        for g in groups:
            print(f"    {g['student']:12}  pages {g['start']}–{g['end']}")
    print("\nDry run complete. No API calls made.")


def _full_run(
    pdfs: list[str],
    *,
    force: bool = False,
    resume: bool = True,
) -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.")
        sys.exit(1)

    import anthropic
    import ocr_pipeline as op

    client = anthropic.Anthropic(api_key=api_key)

    for pdf_name in pdfs:
        ws_label = next((ws for ws, p in TARGET_PDFS.items() if p == pdf_name), pdf_name)
        print(f"\n{'='*60}")
        print(f"Processing {ws_label}: {pdf_name}")

        if force:
            # Clear existing extraction.json gate_status so pipeline re-runs
            for student_dir in sorted((REPO / "students").iterdir()):
                if student_dir.name == "Sample_Student":
                    continue
                ext_path = student_dir / ws_label / "extraction.json"
                if ext_path.exists():
                    import json
                    d = json.loads(ext_path.read_text())
                    g = d.get("gate_1_extraction", {})
                    if isinstance(g, dict) and g.get("status") == "pass":
                        g["status"] = "pending_reextract"
                        ext_path.write_text(json.dumps(d, indent=2, ensure_ascii=False))
            print(f"  (--force: cleared pass statuses for {ws_label})")

        result = op.process_pdf(client, pdf_name, resume=(resume and not force))
        print(f"  Processed {len(result)} student groups.")

    print("\n✓ Re-extraction complete. Run validation + scoring pipeline next.")
    print("  python3 -c \"")
    print("    import sys; sys.path.insert(0,'.')")
    print("    from pipeline_integration import integrate_student")
    print("    for s in ['Amy','Bruno','Helena',...]:  # all students")
    print("        integrate_student(s)")
    print("  \"")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Page detection only, no API calls")
    parser.add_argument("--ws5-only", action="store_true", help="Only process WS5 PDF")
    parser.add_argument("--ws7-only", action="store_true", help="Only process WS7 PDF")
    parser.add_argument("--force", action="store_true", help="Re-extract even if gate_status=pass")
    parser.add_argument("--no-resume", action="store_true", help="Disable resume (re-extract all pages)")
    args = parser.parse_args()

    _verify_fixes()

    if args.ws5_only:
        pdfs = [TARGET_PDFS["WS5"]]
    elif args.ws7_only:
        pdfs = [TARGET_PDFS["WS7"]]
    else:
        pdfs = list(TARGET_PDFS.values())

    if args.dry_run:
        _dry_run(pdfs)
    else:
        _full_run(pdfs, force=args.force, resume=not args.no_resume)

    # Print absent-student summary
    print("\n── Absent students (genuinely not in these PDFs) ──────────────")
    for ws, pdf in TARGET_PDFS.items():
        absent = ABSENT_STUDENTS.get(ws, set())
        if absent:
            print(f"  {ws}: {', '.join(sorted(absent))}  — no pages in {pdf}")
    print("  WS1: Amy, Marco — not in '24 Mart 2026 Çalışma Kâğıdı 1.pdf'")


if __name__ == "__main__":
    main()
