#!/usr/bin/env python3
"""Remove version metadata from existing student pipeline JSON outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from evidence_unit_runtime import build_and_save_evidence_units
from portfolio_builder import build_and_save_portfolio
from student_bundle import STUDENTS_DIR, list_student_ids, write_student_manifest

TOP_LEVEL_DROP = frozenset({
    "schema_version",
    "assessment_framework_version",
    "portfolio_builder_version",
    "updated_at",
    "definition",
    "note",
    "artifact",
    "pipeline_stage",
    "source_stage",
})

UNIT_DROP = frozenset({
    "evidence_unit_id",
    "field_id",
    "evidence_origin",
    "source_family",
    "source_file",
    "source_quality",
    "observability",
    "timestamp",
    "provenance",
    "raw_content",
    "normalized_content",
    "uncertainty",
    "alternative_interpretations",
    "review_level",
    "requires_human_review",
})


def _strip_unit(unit: dict) -> dict:
    out = {k: _strip_obj(v) for k, v in unit.items() if k not in UNIT_DROP}
    if "content" not in out:
        out["content"] = out.get("normalized_content") or out.get("raw_content", "")
    conf = out.get("confidence")
    if isinstance(conf, dict) and conf.get("ocr") is None:
        conf = {k: v for k, v in conf.items() if v is not None}
        out["confidence"] = conf
    return out


def _strip_obj(obj: object) -> object:
    if isinstance(obj, dict):
        if "item_id" in obj and "evidence_unit_type" in obj:
            return _strip_unit(obj)
        out = {k: _strip_obj(v) for k, v in obj.items() if k not in TOP_LEVEL_DROP}
        if "methodology" in out and isinstance(out["methodology"], dict):
            meth = dict(out["methodology"])
            meth.pop("assessment_framework_version", None)
            meth.pop("portfolio_builder_version", None)
            out["methodology"] = meth
        if out.get("worksheet_id") and isinstance(out.get("evidence_units"), list):
            out["evidence_units"] = [
                {k: v for k, v in u.items() if k not in ("student_id", "worksheet_id")}
                if isinstance(u, dict) else u
                for u in out["evidence_units"]
            ]
        return out
    if isinstance(obj, list):
        return [_strip_obj(x) for x in obj]
    return obj


def strip_file(path: Path) -> bool:
    if not path.is_file():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    cleaned = _strip_obj(data)
    if cleaned == data:
        return False
    path.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def strip_student(student_id: str) -> int:
    root = STUDENTS_DIR / student_id
    changed = 0
    for path in sorted(root.rglob("*.json")):
        if strip_file(path):
            changed += 1
    return changed


def main() -> int:
    students = sys.argv[1:] or list_student_ids()
    for student_id in students:
        build_and_save_portfolio(student_id)
        build_and_save_evidence_units(student_id)
        n = strip_student(student_id)
        write_student_manifest(student_id)
        print(f"{student_id}: rebuilt portfolio + evidence_units; stripped {n} json file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
