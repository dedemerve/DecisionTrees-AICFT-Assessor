#!/usr/bin/env python3
"""Split legacy combined Xeno+Titanic ocr_output into separate worksheet files."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from ws_dt_intro_validation import export_split_ocr_output, load_split_items  # noqa: E402
from extract_ws_dt_intro import (  # noqa: E402
    build_extraction_record,
    save_record,
    XENO_PDF,
    TITANIC_PDF,
)


def materialize_student_records(student_id: str) -> None:
    """Create students/{id}/WS_DT_XENO|TITANIC/extraction.json from split sources."""
    xeno_items, titanic_items, xeno_snap, titanic_snap, xeno_notes, titanic_notes = (
        load_split_items(student_id)
    )
    xeno_record = build_extraction_record(
        student_id, "WS_DT_XENO", XENO_PDF, xeno_items,
        ws_snapshot=xeno_snap, page_notes=xeno_notes,
    )
    titanic_record = build_extraction_record(
        student_id, "WS_DT_TITANIC", TITANIC_PDF, titanic_items,
        ws_snapshot=titanic_snap, page_notes=titanic_notes,
    )
    save_record(student_id, "WS_DT_XENO", xeno_record)
    save_record(student_id, "WS_DT_TITANIC", titanic_record)


def main() -> int:
    args = sys.argv[1:]
    students = args or ["Amy", "Bruno"]
    materialize = "--records-only" in students
    if materialize:
        students = [s for s in students if not s.startswith("--")]

    for student in students:
        if materialize:
            materialize_student_records(student)
            print(f"{student}: wrote students/*/WS_DT_XENO|TITANIC/extraction.json")
        else:
            xeno_path, titanic_path = export_split_ocr_output(student)
            print(f"{student}: {xeno_path.relative_to(REPO_ROOT)}")
            print(f"{student}: {titanic_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
