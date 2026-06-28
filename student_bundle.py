"""
student_bundle.py — Modular pipeline artifacts per worksheet.

Layout (schema 3.0) — WS upload (current focus):
  students/<student_id>/<WS>/extraction.json      ← step 1: OCR transcription
  students/<student_id>/<WS>/evidence_units.json ← step 2: canonical output (use this)
  students/<student_id>/evidence_units.json       ← all WS merged (portfolio input)

Legacy / optional per worksheet:
  students/<student_id>/<WS>/validation.json   # WS5, WS6, WS7 only
  students/<student_id>/<WS>/scoring.json
  students/<student_id>/<WS>/evidence.json     # legacy LO3 mapping (deprecated)
  students/<student_id>/<WS>/summary.json
  students/<student_id>/portfolio.json
  students/<student_id>/manifest.json          # pipeline contract for this student
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from pipeline_schema import (
    ARTIFACT_SCHEMA_VERSION,
    PIPELINE_STAGES,
    PORTFOLIO_SCHEMA_VERSION,
    REPO_ROOT,
    WORKSHEET_ITEM_IDS,
    WORKSHEETS_REQUIRING_VALIDATION,
)

STUDENTS_DIR = REPO_ROOT / "students"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def student_dir(student_id: str, base_dir: Path | None = None) -> Path:
    return (base_dir or STUDENTS_DIR) / student_id


def worksheet_stage_dir(
    student_id: str,
    worksheet: str,
    base_dir: Path | None = None,
) -> Path:
    return student_dir(student_id, base_dir) / worksheet


def artifact_path(
    student_id: str,
    worksheet: str,
    stage: str,
    base_dir: Path | None = None,
) -> Path:
    if stage not in PIPELINE_STAGES:
        raise ValueError(f"Unknown stage {stage!r}")
    return worksheet_stage_dir(student_id, worksheet, base_dir) / f"{stage}.json"


def portfolio_path(student_id: str, base_dir: Path | None = None) -> Path:
    return student_dir(student_id, base_dir) / "portfolio.json"


def manifest_path(student_id: str, base_dir: Path | None = None) -> Path:
    return student_dir(student_id, base_dir) / "manifest.json"


def save_extraction_and_build_evidence_units(
    student_id: str,
    worksheet: str,
    extraction_payload: dict[str, Any],
    *,
    base_dir: Path | None = None,
) -> tuple[Path, Path]:
    """
    WS upload handler: save OCR extraction, then produce worksheet evidence_units.json.

    Returns (extraction_path, worksheet_evidence_units_path).
    """
    from evidence_unit_runtime import process_worksheet_after_extraction

    ext_path = save_artifact(
        student_id, worksheet, "extraction", extraction_payload, base_dir=base_dir,
    )
    eu_path = process_worksheet_after_extraction(
        student_id, worksheet, base_dir=base_dir,
    )
    write_student_manifest(student_id, base_dir=base_dir)
    return ext_path, eu_path


def write_student_manifest(student_id: str, base_dir: Path | None = None) -> Path:
    """Document which JSON files a WS upload produces (for demos and UI)."""
    worksheets = list_worksheets(student_id, base_dir)
    manifest = {
        "schema_version": "1.0",
        "student_id": student_id,
        "updated_at": _now_iso(),
        "pipeline": "worksheet_upload_v1",
        "ws_upload_flow": {
            "step_1": {
                "file": "students/<student_id>/<WS>/extraction.json",
                "role": "OCR adapter output — raw field transcriptions",
                "interpretation": False,
            },
            "step_2": {
                "file": "students/<student_id>/<WS>/evidence_units.json",
                "role": "Canonical assessment output — use this after upload",
                "interpretation": False,
            },
            "aggregate": {
                "file": "students/<student_id>/evidence_units.json",
                "role": "All worksheets merged — input to Behaviour Engine (M3)",
                "interpretation": False,
            },
        },
        "worksheets": {},
    }
    root = student_dir(student_id, base_dir)
    for ws in worksheets:
        manifest["worksheets"][ws] = {
            "extraction": f"{ws}/extraction.json" if (root / ws / "extraction.json").exists() else None,
            "evidence_units": f"{ws}/evidence_units.json" if (root / ws / "evidence_units.json").exists() else None,
            "primary_output": f"{ws}/evidence_units.json",
        }
    path = manifest_path(student_id, base_dir)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _envelope(
    student_id: str,
    worksheet: str,
    stage: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "stage": stage,
        "student_id": student_id,
        "worksheet": worksheet,
        "updated_at": _now_iso(),
        **payload,
    }


def load_artifact(
    student_id: str,
    worksheet: str,
    stage: str,
    base_dir: Path | None = None,
) -> dict[str, Any] | None:
    path = artifact_path(student_id, worksheet, stage, base_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_artifact(
    student_id: str,
    worksheet: str,
    stage: str,
    payload: dict[str, Any],
    base_dir: Path | None = None,
) -> Path:
    data = _envelope(student_id, worksheet, stage, payload)
    path = artifact_path(student_id, worksheet, stage, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def load_portfolio(student_id: str, base_dir: Path | None = None) -> dict[str, Any]:
    path = portfolio_path(student_id, base_dir)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "schema_version": PORTFOLIO_SCHEMA_VERSION,
        "student_id": student_id,
        "updated_at": _now_iso(),
    }


def save_portfolio(
    student_id: str,
    data: dict[str, Any],
    base_dir: Path | None = None,
) -> Path:
    out = dict(data)
    out["schema_version"] = PORTFOLIO_SCHEMA_VERSION
    out["student_id"] = student_id
    out["updated_at"] = _now_iso()
    path = portfolio_path(student_id, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def list_worksheets(student_id: str, base_dir: Path | None = None) -> list[str]:
    root = student_dir(student_id, base_dir)
    if not root.is_dir():
        return []
    out: list[str] = []
    for p in sorted(root.iterdir()):
        if p.is_dir() and (p / "extraction.json").exists():
            out.append(p.name)
        elif p.is_file() and p.suffix == ".json" and p.stem not in (
            "portfolio", "evidence_units", "manifest",
        ):
            out.append(p.stem)
    return out


def extraction_responses(extraction: dict[str, Any] | None) -> dict[str, str]:
    if not extraction:
        return {}
    if isinstance(extraction.get("responses"), dict):
        return extraction["responses"]
    gate1 = extraction.get("gate_1_extraction", {})
    if isinstance(gate1.get("items"), dict):
        return gate1["items"]
    # v3.0 envelope: payload at top level after metadata keys
    meta = {"schema_version", "stage", "student_id", "worksheet", "updated_at"}
    if "responses" in extraction:
        return extraction["responses"]
    return {}


def load_extraction_responses(
    student_id: str,
    worksheet: str,
    base_dir: Path | None = None,
) -> dict[str, str]:
    ext = load_artifact(student_id, worksheet, "extraction", base_dir)
    return extraction_responses(ext)


def split_scoring_and_evidence(scoring_items: list[dict[str, Any]]) -> tuple[list[dict], list[dict]]:
    """Split combined scorer output into score-only and competency evidence records."""
    scores: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    for rec in scoring_items:
        if not isinstance(rec, dict) or "item" not in rec:
            continue
        comps = rec.get("competencies") or rec.get("learning_objects", [])
        scores.append({
            "item": rec["item"],
            "score": rec.get("score"),
            "confidence": rec.get("confidence"),
            "review": rec.get("review"),
        })
        if comps:
            normalized = []
            for c in comps:
                if not isinstance(c, dict):
                    continue
                entry = {
                    "lo": c.get("lo") or c.get("LO", ""),
                    "strength": c.get("strength") or c.get("evidence_strength", "none"),
                    "evidence_type": c.get("evidence_type", "direct"),
                    "rationale": c.get("rationale", ""),
                    "confidence": c.get("confidence"),
                    "evidence_present": c.get("evidence_present", True),
                }
                normalized.append(entry)
            evidence.append({"item": rec["item"], "competencies": normalized})
    return scores, evidence


def _worksheet_max_score(worksheet: str) -> float | None:
    from pipeline_schema import load_rubric
    rubric = load_rubric(worksheet)
    items = rubric.get("items", {})
    if not items:
        return None
    return sum(float(cfg.get("max_score", 0)) for cfg in items.values())


def build_summary_from_scoring(
    scoring: dict[str, Any],
    *,
    worksheet: str | None = None,
) -> dict[str, Any]:
    """Worksheet summary: scores + review queue only (no AI-CFT peaks)."""
    items = scoring.get("items", [])
    review_items = [
        rec["item"] for rec in items
        if isinstance(rec, dict) and rec.get("review")
    ]
    total = scoring.get("total_score")
    if total is None and items:
        total = sum(float(r.get("score") or 0) for r in items if isinstance(r, dict))
    max_score = scoring.get("max_score")
    if max_score is None and worksheet:
        max_score = _worksheet_max_score(worksheet)
    return {
        "total_score": total,
        "max_score": max_score,
        "review_items": review_items,
        "blocked": scoring.get("blocked", False),
    }


def save_scoring_bundle(
    student_id: str,
    worksheet: str,
    scoring: dict[str, Any],
    *,
    base_dir: Path | None = None,
) -> list[Path]:
    """Write scoring.json and derived evidence + summary artifacts."""
    meta = {"schema_version", "stage", "student_id", "worksheet", "updated_at", "learning_objects"}
    scoring_copy = dict(scoring)
    raw_items = scoring_copy.pop("items", [])
    score_items, evidence_items = split_scoring_and_evidence(raw_items)

    scoring_payload = {k: v for k, v in scoring_copy.items() if k not in meta}
    scoring_payload["items"] = score_items
    if scoring_payload.get("total_score") is None and score_items:
        scoring_payload["total_score"] = sum(float(r.get("score") or 0) for r in score_items)
    if scoring_payload.get("max_score") is None:
        scoring_payload["max_score"] = _worksheet_max_score(worksheet)

    summary_payload = build_summary_from_scoring(scoring_payload, worksheet=worksheet)
    written = [save_artifact(student_id, worksheet, "scoring", scoring_payload, base_dir)]
    if evidence_items:
        written.append(save_artifact(
            student_id, worksheet, "evidence", {"items": evidence_items}, base_dir,
        ))
    written.append(save_artifact(
        student_id, worksheet, "summary", summary_payload, base_dir,
    ))
    return written


def iter_scoring_artifacts(
    student_id: str,
    base_dir: Path | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any]]] = []
    for ws in list_worksheets(student_id, base_dir):
        data = load_artifact(student_id, ws, "scoring", base_dir)
        if data:
            out.append((ws, data))
    return out


def _strip_meta(section: dict[str, Any]) -> dict[str, Any]:
    skip = {"schema_version", "worksheet", "student_id", "stage", "updated_at"}
    return {k: v for k, v in section.items() if k not in skip}


def artifact_payload(artifact: dict[str, Any] | None) -> dict[str, Any]:
    """Return stage payload without envelope metadata."""
    if not artifact:
        return {}
    return _strip_meta(artifact)


def migrate_combined_worksheet_file(
    student_id: str,
    worksheet: str,
    combined: dict[str, Any],
    base_dir: Path | None = None,
) -> list[Path]:
    """Migrate v2.1 combined WS.json → modular stage directory."""
    from worksheet_validation import build_technical_validation

    written: list[Path] = []
    root = worksheet_stage_dir(student_id, worksheet, base_dir)
    root.mkdir(parents=True, exist_ok=True)

    extraction = combined.get("extraction")
    if extraction:
        payload = _strip_meta(extraction)
        written.append(save_artifact(student_id, worksheet, "extraction", payload, base_dir))

    old_validation = combined.get("validation")
    if worksheet in WORKSHEETS_REQUIRING_VALIDATION:
        ext_payload = _strip_meta(extraction or {})
        tech = build_technical_validation(worksheet, ext_payload, old_validation)
        written.append(save_artifact(student_id, worksheet, "validation", tech, base_dir))

    scoring = combined.get("scoring")
    score_items: list[dict[str, Any]] = []
    sc: dict[str, Any] = {}
    if scoring:
        sc = _strip_meta(scoring)
        items = sc.pop("items", [])
        score_items, evidence_items = split_scoring_and_evidence(items)
        sc["items"] = score_items
        written.append(save_artifact(student_id, worksheet, "scoring", sc, base_dir))
        if evidence_items:
            written.append(save_artifact(
                student_id, worksheet, "evidence", {"items": evidence_items}, base_dir,
            ))

    summary = combined.get("summary")
    if scoring or summary:
        sm = build_summary_from_scoring(sc, worksheet=worksheet) if scoring else _strip_meta(summary or {})
        if summary and summary.get("max_score") is not None:
            sm["max_score"] = summary["max_score"]
        sm.pop("learning_objects", None)
        written.append(save_artifact(student_id, worksheet, "summary", sm, base_dir))

    return written


def migrate_student_to_v30(student_id: str, base_dir: Path | None = None) -> list[Path]:
    """Migrate flat WS*.json files to students/<id>/<WS>/ stage artifacts."""
    root = student_dir(student_id, base_dir)
    if not root.is_dir():
        return []

    written: list[Path] = []
    for path in sorted(root.glob("*.json")):
        if path.name == "portfolio.json":
            continue
        combined = json.loads(path.read_text(encoding="utf-8"))
        ws = combined.get("worksheet", path.stem)
        written.extend(migrate_combined_worksheet_file(student_id, ws, combined, base_dir))
        path.unlink()

    pf = portfolio_path(student_id, base_dir)
    if pf.exists():
        pf_data = json.loads(pf.read_text(encoding="utf-8"))
        save_portfolio(student_id, pf_data, base_dir)
        written.append(pf)

    return written


def list_student_ids(base_dir: Path | None = None) -> list[str]:
    root = base_dir or STUDENTS_DIR
    if not root.is_dir():
        return []
    return sorted(
        d.name for d in root.iterdir()
        if d.is_dir() and (any(d.glob("*/extraction.json")) or any(d.glob("*.json")))
    )
