#!/usr/bin/env python3
"""
Refresh Sample_Student artifacts from canonical answer keys.

1. Patch extractions where fields were blank or outdated
2. Re-run deterministic validate/score (WS5–7, WS10–11)
3. Rebuild evidence_units.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sample_student_reference import SAMPLE_STUDENT_EXTRACTION_PATCHES
from student_bundle import (
    STUDENTS_DIR,
    artifact_payload,
    extraction_responses,
    load_artifact,
    save_artifact,
)

DEFAULT_STUDENT = "Sample_Student"
SCRIPTS = REPO_ROOT / "scripts"


def _patch_extractions(student_id: str) -> list[str]:
    updated: list[str] = []
    for worksheet, patches in SAMPLE_STUDENT_EXTRACTION_PATCHES.items():
        art = load_artifact(student_id, worksheet, "extraction", STUDENTS_DIR)
        if not art:
            continue
        payload = artifact_payload(art)
        responses = dict(payload.get("responses") or {})
        changed = False
        for fid, value in patches.items():
            if responses.get(fid) != value:
                responses[fid] = value
                changed = True
        if changed:
            payload["responses"] = responses
            save_artifact(student_id, worksheet, "extraction", payload, STUDENTS_DIR)
            updated.append(worksheet)
    return updated


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh sample student from answer keys")
    parser.add_argument("student_id", nargs="?", default=DEFAULT_STUDENT)
    parser.add_argument("--skip-evidence", action="store_true")
    args = parser.parse_args()

    patched = _patch_extractions(args.student_id)
    if patched:
        print(f"Patched extractions: {', '.join(patched)}")
    else:
        print("Extractions already aligned with reference patches.")

    for script in ("score_ws5.py", "score_ws6.py", "score_ws7.py", "score_ws10.py", "score_ws11.py"):
        _run([sys.executable, str(SCRIPTS / script), args.student_id])

    if not args.skip_evidence:
        _run([sys.executable, str(SCRIPTS / "build_evidence_units.py"), args.student_id])

    print(f"Done — refreshed deterministic artifacts for {args.student_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
