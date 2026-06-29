#!/usr/bin/env python3
"""Build canonical evidence_units.json for one or more students."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evidence_unit_runtime import build_and_save_evidence_units, generate_sample_evidence_unit
from schema_validate import validate_evidence_units
from student_bundle import list_student_ids

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical evidence_units.json")
    parser.add_argument("student_id", nargs="?", help="Student directory key")
    parser.add_argument("--all", action="store_true", help="Build for every student")
    parser.add_argument("--sample", action="store_true", help="Print one sample EU and exit")
    args = parser.parse_args()

    if args.sample:
        import json
        print(json.dumps(generate_sample_evidence_unit(), indent=2, ensure_ascii=False))
        return 0

    targets: list[str] = []
    if args.all:
        targets = list_student_ids()
    elif args.student_id:
        targets = [args.student_id]
    else:
        targets = ["Sample_Student"]

    if not targets:
        log.error("No students found")
        return 1

    failed = 0
    for student_id in targets:
        path = build_and_save_evidence_units(student_id)
        doc = __import__("json").loads(path.read_text(encoding="utf-8"))
        errors = validate_evidence_units(doc, str(path.relative_to(REPO_ROOT)))
        if errors:
            failed += 1
            for err in errors:
                log.error("%s", err)
        else:
            log.info("Validated %s (%d units)", path.name, len(doc["evidence_units"]))

        from student_bundle import write_student_manifest
        write_student_manifest(student_id)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
