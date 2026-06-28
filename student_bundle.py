"""
student_bundle.py — Single JSON output per student.

Canonical path: students/<student_id>.json

Structure (schema 2.0):
  {
    "schema_version": "2.0",
    "student_id": "...",
    "worksheets": {
      "WS1": {
        "extraction": { ... },   # OCR / layout / HTR
        "validation": { ... },
        "scoring":    { ... },
        "summary":    { ... }
      }
    },
    "portfolio": { ... }          # AI-CFT rollup (learning outcomes, data gaps)
  }
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline_schema import (
    OCR_OUTPUT_DIR,
    REPO_ROOT,
    WORKSHEET_ITEM_IDS,
)

STUDENTS_DIR = REPO_ROOT / "students"
STUDENT_BUNDLE_SCHEMA_VERSION = "2.0"
WORKSHEET_SECTIONS = ("extraction", "validation", "scoring", "summary")

LEGACY_DIRS = {
    "extraction": OCR_OUTPUT_DIR,
    "validation": REPO_ROOT / "validation",
    "scoring": REPO_ROOT / "scoring",
    "summary": REPO_ROOT / "summary",
}
LEGACY_PORTFOLIO_DIR = REPO_ROOT / "portfolio"


def bundle_path(student_id: str, base_dir: Path | None = None) -> Path:
    return (base_dir or STUDENTS_DIR) / f"{student_id}.json"


def new_bundle(student_id: str) -> dict[str, Any]:
    return {
        "schema_version": STUDENT_BUNDLE_SCHEMA_VERSION,
        "student_id": student_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "worksheets": {},
        "portfolio": {},
    }


def load_bundle(student_id: str, base_dir: Path | None = None) -> dict[str, Any]:
    path = bundle_path(student_id, base_dir)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return new_bundle(student_id)


def save_bundle(bundle: dict[str, Any], base_dir: Path | None = None) -> Path:
    student_id = bundle["student_id"]
    bundle["schema_version"] = STUDENT_BUNDLE_SCHEMA_VERSION
    bundle["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = bundle_path(student_id, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def worksheet_entry(bundle: dict[str, Any], worksheet: str) -> dict[str, Any]:
    return bundle.setdefault("worksheets", {}).setdefault(worksheet, {})


def get_section(
    bundle: dict[str, Any],
    worksheet: str,
    section: str,
) -> dict[str, Any] | None:
    ws = bundle.get("worksheets", {}).get(worksheet, {})
    data = ws.get(section)
    return data if isinstance(data, dict) else None


def set_section(
    bundle: dict[str, Any],
    worksheet: str,
    section: str,
    data: dict[str, Any],
) -> None:
    if section not in WORKSHEET_SECTIONS:
        raise ValueError(f"Unknown section {section!r}; expected one of {WORKSHEET_SECTIONS}")
    entry = worksheet_entry(bundle, worksheet)
    entry[section] = data


def extraction_responses(bundle: dict[str, Any], worksheet: str) -> dict[str, str]:
    """Flat item_id → answer from extraction (gated or legacy flat)."""
    ext = get_section(bundle, worksheet, "extraction")
    if not ext:
        return {}
    if "responses" in ext and isinstance(ext["responses"], dict):
        return ext["responses"]
    gate1 = ext.get("gate_1_extraction", {})
    items = gate1.get("items", {})
    if isinstance(items, dict):
        return items
    return {}


def iter_scoring_worksheets(bundle: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for ws, sections in sorted(bundle.get("worksheets", {}).items()):
        scoring = sections.get("scoring")
        if isinstance(scoring, dict):
            out.append((ws, scoring))
    return out


def set_combined_responses(bundle: dict[str, Any], responses: dict[str, str]) -> None:
    bundle["combined_responses"] = responses


def migrate_legacy_student(
    student_id: str,
    base_dir: Path | None = None,
    *,
    save: bool = True,
) -> dict[str, Any]:
    """Merge legacy per-worksheet JSON dirs into one student bundle."""
    bundle = new_bundle(student_id)

    worksheets: set[str] = set(WORKSHEET_ITEM_IDS)
    for section, root in LEGACY_DIRS.items():
        student_dir = root / student_id
        if not student_dir.is_dir():
            continue
        for path in sorted(student_dir.glob("*.json")):
            if path.name == "responses.json":
                continue
            ws = path.stem
            worksheets.add(ws)
            data = json.loads(path.read_text(encoding="utf-8"))
            set_section(bundle, ws, section, data)

    portfolio_path = LEGACY_PORTFOLIO_DIR / f"{student_id}.json"
    if portfolio_path.exists():
        portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))
        bundle["portfolio"] = {
            k: v for k, v in portfolio.items()
            if k not in ("schema_version", "student_id")
        }
        if portfolio.get("framework"):
            bundle["framework"] = portfolio["framework"]
        if portfolio.get("aspect"):
            bundle["aspect"] = portfolio["aspect"]

    responses_path = OCR_OUTPUT_DIR / student_id / "responses.json"
    if responses_path.exists():
        combined = json.loads(responses_path.read_text(encoding="utf-8"))
        if isinstance(combined.get("responses"), dict):
            set_combined_responses(bundle, combined["responses"])

    if save:
        save_bundle(bundle, base_dir)
    return bundle


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Student bundle utilities")
    parser.add_argument("command", choices=["migrate"], help="migrate: merge legacy JSON into students/")
    parser.add_argument("student_id", help="e.g. Sample_Student")
    args = parser.parse_args()

    if args.command == "migrate":
        bundle = migrate_legacy_student(args.student_id)
        out = bundle_path(args.student_id)
        print(f"Migrated {args.student_id} → {out}")
        print(f"  worksheets: {len(bundle.get('worksheets', {}))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
