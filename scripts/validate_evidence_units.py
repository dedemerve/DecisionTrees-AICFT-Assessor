#!/usr/bin/env python3
"""Validate students/*/evidence_units.json against canonical Layer 2 schema."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evidence_unit_runtime import evidence_units_path
from schema_validate import validate_evidence_units_v1
from student_bundle import STUDENTS_DIR, list_student_ids

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def validate_student(student_id: str, base_dir: Path | None = None) -> list[str]:
    path = evidence_units_path(student_id, base_dir)
    if not path.exists():
        return [f"{student_id}: missing {path}"]
    data = json.loads(path.read_text(encoding="utf-8"))
    return validate_evidence_units_v1(data, str(path.relative_to(REPO_ROOT)))


def main() -> int:
    students = list_student_ids()
    if not students:
        log.error("No students under %s", STUDENTS_DIR)
        return 1

    errors: list[str] = []
    checked = 0
    for student_id in students:
        path = evidence_units_path(student_id)
        if not path.exists():
            log.warning("%s: evidence_units.json not found — skipped", student_id)
            continue
        checked += 1
        errors.extend(validate_student(student_id))
        root = path.parent
        for ws_eu in sorted(root.glob("WS*/evidence_units.json")):
            data = json.loads(ws_eu.read_text(encoding="utf-8"))
            errors.extend(validate_evidence_units_v1(data, str(ws_eu.relative_to(REPO_ROOT))))

    if checked == 0:
        log.error("No evidence_units.json files found")
        return 1

    if errors:
        for err in errors:
            log.error("%s", err)
        log.error("Validation FAILED (%d errors, %d students)", len(errors), checked)
        return 1

    log.info("All evidence_units.json valid (%d students)", checked)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
