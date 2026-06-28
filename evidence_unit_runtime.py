"""
evidence_unit_runtime.py — Canonical Evidence Unit (Layer 2) runtime.

Transforms extraction adapter output into stable, descriptive evidence_units.json.
No behavioural, ILO, Domain, or AI-CFT inference is performed here.

An Evidence Unit is the smallest traceable assessment object representing an
interpretable piece of learner evidence while preserving provenance, uncertainty,
source quality, and review metadata.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from evidence_unit_metadata import derive_assessment_metadata
from pipeline_schema import (
    LAYOUT_ROIS_DIR,
    REPO_ROOT,
    WORKSHEET_DESCRIPTIVE_ONLY,
    WORKSHEET_PDF_SOURCE,
    WORKSHEETS_1_10_PAGE_INDEX,
    WORKSHEETS_DIR,
)
from student_bundle import (
    STUDENTS_DIR,
    artifact_path,
    extraction_responses,
    list_worksheets,
    load_artifact,
    worksheet_stage_dir,
)

log = logging.getLogger(__name__)

EVIDENCE_UNITS_SCHEMA_VERSION = "1.1"
PIPELINE_EVIDENCE_VERSION = "1.1"
ADAPTER_WORKSHEET_EXTRACTION_V1 = "worksheet_extraction_v1"

# Phase 2 M2 freeze gate — do not extend schema without construct-validity review.
M2_EVIDENCE_UNIT_FREEZE = {
    "status": "FROZEN",
    "schema_version": EVIDENCE_UNITS_SCHEMA_VERSION,
    "milestone": "Phase 2 — M2: Canonical Evidence Unit Runtime",
    "modification_policy": (
        "No Evidence Unit schema or runtime changes without explicit researcher "
        "approval and construct-validity justification."
    ),
}

ASSESSMENT_OBJECT_DEFINITION = (
    "The smallest traceable assessment object representing an interpretable piece "
    "of learner evidence while preserving provenance, uncertainty, source quality, "
    "and review metadata."
)

SOURCE_FAMILIES: frozenset[str] = frozenset({
    "worksheet",
    "codap",
    "screen_recording",
    "reflection",
    "observation",
    "interview",
})

BLANK_SENTINELS: frozenset[str] = frozenset({
    "(bos)",
    "(blank)",
    "(empty)",
})

ILLEGIBLE_SENTINELS: frozenset[str] = frozenset({
    "(okunamiyor)",
    "(illegible)",
})

MISSING_SENTINELS: frozenset[str] = frozenset({
    "(missing)",
    "(not_extracted)",
    "(transcription_error)",
})

ALL_SENTINELS: frozenset[str] = (
    BLANK_SENTINELS | ILLEGIBLE_SENTINELS | MISSING_SENTINELS
)

FORBIDDEN_EU_KEYS: frozenset[str] = frozenset({
    "behaviour_id",
    "observable_behaviour",
    "observable_behaviour_id",
    "ilo_id",
    "learning_object_id",
    "lo",
    "domain_id",
    "domain_understanding",
    "ai_cft",
    "competency",
    "competency_id",
    "strength",
    "interpretation",
    "inference",
})

FORBIDDEN_EU_VALUE_FRAGMENTS: tuple[str, ...] = (
    "lo3.",
    "lo3_",
    "ob_pro_",
    "ob_con_",
    "ob_str_",
    "ob_ref_",
    "competency_id",
    "domain_understanding_id",
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _artifact_reference(
    path: Path,
    *,
    base_dir: Path | None = None,
) -> str:
    """Repo-relative path when possible; otherwise students-root-relative."""
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        root = base_dir or STUDENTS_DIR
        try:
            return str(path.relative_to(root.parent if root.name == "students" else root))
        except ValueError:
            return str(path)


def evidence_units_path(student_id: str, base_dir: Path | None = None) -> Path:
    """Student-level aggregate of all worksheet evidence units."""
    return (base_dir or STUDENTS_DIR) / student_id / "evidence_units.json"


def worksheet_evidence_units_path(
    student_id: str,
    worksheet_id: str,
    base_dir: Path | None = None,
) -> Path:
    """Per-worksheet canonical output after OCR (one WS upload → this file)."""
    return worksheet_stage_dir(student_id, worksheet_id, base_dir) / "evidence_units.json"


def deterministic_evidence_unit_id(
    student_id: str,
    worksheet_id: str,
    field_id: str,
) -> str:
    """Stable EU id across rebuilds (same student/worksheet/field → same id)."""
    digest = hashlib.sha256(
        f"{student_id}|{worksheet_id}|{field_id}".encode("utf-8")
    ).hexdigest()
    serial = int(digest[:8], 16) % 1_000_000
    return f"EU_{serial:06d}"


@dataclass
class NormalizationResult:
    raw_content: str
    normalized_content: str
    uncertainty: str
    alternative_interpretations: list[dict[str, str]]
    extraction_confidence: float


def normalize_field_content(raw: str | None) -> NormalizationResult:
    """Normalize adapter output without semantic interpretation."""
    text = "" if raw is None else str(raw)
    stripped = text.strip()
    lower = stripped.lower()

    if not stripped:
        return NormalizationResult(
            raw_content=text,
            normalized_content="(bos)",
            uncertainty="Field left blank or empty after extraction.",
            alternative_interpretations=[],
            extraction_confidence=0.35,
        )

    if lower in BLANK_SENTINELS:
        return NormalizationResult(
            raw_content=text,
            normalized_content="(bos)",
            uncertainty="Explicit blank sentinel from extraction adapter.",
            alternative_interpretations=[],
            extraction_confidence=0.4,
        )

    if lower in ILLEGIBLE_SENTINELS:
        return NormalizationResult(
            raw_content=text,
            normalized_content="(okunamiyor)",
            uncertainty="Text present but illegible; transcription unreliable.",
            alternative_interpretations=[],
            extraction_confidence=0.25,
        )

    if lower in MISSING_SENTINELS:
        return NormalizationResult(
            raw_content=text,
            normalized_content=lower,
            uncertainty=f"Extraction adapter reported {lower}.",
            alternative_interpretations=[],
            extraction_confidence=0.1,
        )

    collapsed = re.sub(r"\s+", " ", stripped)
    alternatives: list[dict[str, str]] = []
    uncertainty = "none"
    confidence = 0.85

    if collapsed != stripped:
        alternatives.append({
            "interpretation": "whitespace-sensitive transcription",
            "basis": "Original spacing preserved as an alternative reading.",
        })
        uncertainty = "Whitespace normalization applied; original spacing may carry meaning."

    return NormalizationResult(
        raw_content=text,
        normalized_content=collapsed,
        uncertainty=uncertainty,
        alternative_interpretations=alternatives,
        extraction_confidence=confidence,
    )


def source_family_for_field(worksheet_id: str, field_id: str) -> str:
    if worksheet_id == "WS_DT":
        return "codap"
    descriptive = WORKSHEET_DESCRIPTIVE_ONLY.get(worksheet_id, [])
    if field_id in descriptive:
        return "reflection"
    return "worksheet"


def source_file_for_worksheet(worksheet_id: str) -> str:
    return WORKSHEET_PDF_SOURCE.get(worksheet_id, "unknown_source.pdf")


def page_for_worksheet(worksheet_id: str) -> int | None:
    return WORKSHEETS_1_10_PAGE_INDEX.get(worksheet_id)


@dataclass
class FieldExtractionInput:
    """Adapter-neutral input for one atomic extracted field."""

    field_id: str
    raw_content: str
    rubric_item_id: str | None = None
    ocr_confidence: float | None = None
    extraction_confidence: float | None = None
    uncertainty: str | None = None
    alternative_interpretations: list[dict[str, str]] = field(default_factory=list)
    provenance_extra: dict[str, Any] = field(default_factory=dict)


def _load_field_to_rubric_map(worksheet_id: str) -> dict[str, str]:
    path = WORKSHEETS_DIR / worksheet_id / "extraction_schema.json"
    if not path.exists():
        return {}
    schema = json.loads(path.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for fld in schema.get("fields", []):
        fid = fld.get("field_id")
        rid = fld.get("rubric_item_id")
        if fid and rid:
            mapping[str(fid)] = str(rid)
    return mapping


def _load_layout_zones(
    student_id: str,
    worksheet_id: str,
) -> dict[str, dict[str, Any]]:
    manifest = LAYOUT_ROIS_DIR / student_id / f"{worksheet_id}_layout.json"
    if not manifest.exists():
        return {}
    data = json.loads(manifest.read_text(encoding="utf-8"))
    zones: dict[str, dict[str, Any]] = {}
    for zone in data.get("zones", []):
        zid = zone.get("zone_id")
        if zid:
            zones[str(zid)] = zone
    return zones


def _bbox_for_field(
    field_id: str,
    zones: dict[str, dict[str, Any]],
) -> list[float] | None:
    zone = zones.get(field_id)
    if not zone:
        return None
    coords = zone.get("coordinates")
    if not isinstance(coords, dict):
        return None
    try:
        return [
            float(coords["x"]),
            float(coords["y"]),
            float(coords["w"]),
            float(coords["h"]),
        ]
    except (KeyError, TypeError, ValueError):
        return None


def build_evidence_unit(
    *,
    student_id: str,
    worksheet_id: str,
    field_input: FieldExtractionInput,
    timestamp: str,
    extraction_artifact: str,
    adapter: str = ADAPTER_WORKSHEET_EXTRACTION_V1,
    layout_zones: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Serialize one canonical Evidence Unit assessment object (descriptive only)."""
    norm = normalize_field_content(field_input.raw_content)
    if field_input.extraction_confidence is not None:
        norm.extraction_confidence = float(field_input.extraction_confidence)
    if field_input.uncertainty:
        norm.uncertainty = field_input.uncertainty

    alts = list(norm.alternative_interpretations)
    for alt in field_input.alternative_interpretations:
        if "interpretation" in alt:
            alts.append(alt)
        elif "content" in alt:
            alts.append({
                "interpretation": alt["content"],
                "basis": alt.get("rationale", "Adapter-supplied alternative."),
            })

    source_family = source_family_for_field(worksheet_id, field_input.field_id)
    source_file = source_file_for_worksheet(worksheet_id)
    meta = derive_assessment_metadata(
        worksheet_id=worksheet_id,
        field_id=field_input.field_id,
        rubric_item_id=field_input.rubric_item_id,
        source_family=source_family,
        raw_content=norm.raw_content,
        normalized_content=norm.normalized_content,
        extraction_confidence=norm.extraction_confidence,
        ocr_confidence=field_input.ocr_confidence,
        uncertainty=norm.uncertainty,
        alternative_interpretations=alts,
    )

    zones = layout_zones or {}
    bbox = _bbox_for_field(field_input.field_id, zones)
    page = page_for_worksheet(worksheet_id)
    if field_input.provenance_extra.get("page") is not None:
        page = field_input.provenance_extra.get("page")

    provenance: dict[str, Any] = {
        "adapter": adapter,
        "source_file": source_file,
        "worksheet": worksheet_id,
        "field": field_input.field_id,
        "timestamp": timestamp,
        "pipeline_version": PIPELINE_EVIDENCE_VERSION,
        "extraction_artifact": extraction_artifact,
    }
    if field_input.rubric_item_id:
        provenance["rubric_item_id"] = field_input.rubric_item_id
    if page is not None:
        provenance["page"] = page
    if bbox is not None:
        provenance["bbox"] = bbox
    for key, value in field_input.provenance_extra.items():
        if key not in provenance and value is not None:
            provenance[key] = value

    return {
        "evidence_unit_id": deterministic_evidence_unit_id(
            student_id, worksheet_id, field_input.field_id,
        ),
        "student_id": student_id,
        "worksheet_id": worksheet_id,
        "item_id": field_input.field_id,
        "field_id": field_input.field_id,
        "evidence_unit_type": meta.evidence_unit_type,
        "evidence_origin": meta.evidence_origin,
        "source_family": source_family,
        "source_file": source_file,
        "source_quality": meta.source_quality,
        "observability": meta.observability,
        "evidence_completeness": meta.evidence_completeness,
        "raw_content": norm.raw_content,
        "normalized_content": norm.normalized_content,
        "confidence": {
            "ocr": meta.ocr_confidence,
            "extraction": round(meta.extraction_confidence, 4),
            "evidence_quality": meta.evidence_quality_confidence,
        },
        "provenance": provenance,
        "uncertainty": meta.uncertainty,
        "alternative_interpretations": meta.alternative_interpretations,
        "review_level": meta.review_level,
        "requires_human_review": meta.requires_human_review,
        "timestamp": timestamp,
    }


def extraction_artifact_to_field_inputs(
    worksheet_id: str,
    extraction_payload: dict[str, Any],
) -> list[FieldExtractionInput]:
    """Convert worksheet extraction.json payload to adapter-neutral field inputs."""
    responses = extraction_responses(extraction_payload)
    if not responses and isinstance(extraction_payload.get("responses"), dict):
        responses = extraction_payload["responses"]

    field_map = _load_field_to_rubric_map(worksheet_id)
    inputs: list[FieldExtractionInput] = []
    for field_id in sorted(responses.keys()):
        meta = {}
        raw = responses[field_id]
        if isinstance(raw, dict):
            meta = raw
            raw = meta.get("text") or meta.get("content") or ""
        inputs.append(FieldExtractionInput(
            field_id=field_id,
            raw_content=str(raw),
            rubric_item_id=field_map.get(field_id),
            ocr_confidence=meta.get("ocr_confidence"),
            extraction_confidence=meta.get("extraction_confidence"),
            uncertainty=meta.get("uncertainty"),
            alternative_interpretations=list(meta.get("alternative_interpretations") or []),
            provenance_extra={
                k: meta[k] for k in ("page", "bbox", "source_image", "ocr_engine")
                if k in meta
            },
        ))
    return inputs


def build_evidence_units_from_worksheet(
    student_id: str,
    worksheet_id: str,
    *,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    """Build evidence units for a single worksheet (WS upload output)."""
    doc = build_evidence_units_from_student(
        student_id, base_dir=base_dir, worksheets=[worksheet_id],
    )
    units = doc.get("evidence_units", [])
    return {
        "schema_version": EVIDENCE_UNITS_SCHEMA_VERSION,
        "artifact": "worksheet_evidence_units",
        "pipeline_stage": "evidence_units",
        "source_stage": "extraction",
        "student_id": student_id,
        "worksheet_id": worksheet_id,
        "updated_at": doc["updated_at"],
        "definition": ASSESSMENT_OBJECT_DEFINITION,
        "note": (
            f"Canonical Layer 2 output for {worksheet_id} after OCR/extraction. "
            "Descriptive only — no behavioural, ILO, Domain, or AI-CFT inference."
        ),
        "evidence_units": units,
    }


def save_worksheet_evidence_units(
    student_id: str,
    worksheet_id: str,
    document: dict[str, Any],
    *,
    base_dir: Path | None = None,
) -> Path:
    out = dict(document)
    out["schema_version"] = EVIDENCE_UNITS_SCHEMA_VERSION
    out["artifact"] = "worksheet_evidence_units"
    out["student_id"] = student_id
    out["worksheet_id"] = worksheet_id
    out["updated_at"] = _now_iso()
    path = worksheet_evidence_units_path(student_id, worksheet_id, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log.info("Wrote %s (%d evidence units)", path, len(out.get("evidence_units", [])))
    return path


def process_worksheet_after_extraction(
    student_id: str,
    worksheet_id: str,
    *,
    base_dir: Path | None = None,
    refresh_student_aggregate: bool = True,
) -> Path:
    """
    WS upload pipeline step 2: extraction.json → worksheet evidence_units.json.

    Call this immediately after saving extraction.json for one worksheet.
    """
    ws_doc = build_evidence_units_from_worksheet(
        student_id, worksheet_id, base_dir=base_dir,
    )
    path = save_worksheet_evidence_units(
        student_id, worksheet_id, ws_doc, base_dir=base_dir,
    )
    if refresh_student_aggregate:
        build_and_save_evidence_units(student_id, base_dir=base_dir)
    return path


def build_evidence_units_from_student(
    student_id: str,
    *,
    base_dir: Path | None = None,
    worksheets: list[str] | None = None,
) -> dict[str, Any]:
    """Aggregate all worksheet extractions into one evidence_units.json document."""
    root = base_dir or STUDENTS_DIR
    ws_list = worksheets or list_worksheets(student_id, root)
    units: list[dict[str, Any]] = []
    built_at = _now_iso()

    for worksheet_id in sorted(ws_list):
        extraction = load_artifact(student_id, worksheet_id, "extraction", root)
        if not extraction:
            log.warning("%s/%s: no extraction artifact — skipped", student_id, worksheet_id)
            continue

        artifact_rel = _artifact_reference(
            artifact_path(student_id, worksheet_id, "extraction", root),
            base_dir=root,
        )
        layout_zones = _load_layout_zones(student_id, worksheet_id)
        for field_input in extraction_artifact_to_field_inputs(
            worksheet_id, extraction,
        ):
            units.append(build_evidence_unit(
                student_id=student_id,
                worksheet_id=worksheet_id,
                field_input=field_input,
                timestamp=extraction.get("updated_at") or built_at,
                extraction_artifact=artifact_rel,
                layout_zones=layout_zones,
            ))

    units.sort(key=lambda u: (u["worksheet_id"], u["item_id"]))
    return {
        "schema_version": EVIDENCE_UNITS_SCHEMA_VERSION,
        "student_id": student_id,
        "updated_at": built_at,
        "definition": ASSESSMENT_OBJECT_DEFINITION,
        "note": (
            "Canonical Layer 2 assessment objects. Descriptive metadata only — "
            "no behavioural, ILO, Domain, or AI-CFT inference."
        ),
        "evidence_units": units,
    }


def save_evidence_units(
    student_id: str,
    document: dict[str, Any],
    *,
    base_dir: Path | None = None,
) -> Path:
    out = dict(document)
    out["schema_version"] = EVIDENCE_UNITS_SCHEMA_VERSION
    out["student_id"] = student_id
    out["updated_at"] = _now_iso()
    path = evidence_units_path(student_id, base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    log.info("Wrote %s (%d evidence units)", path, len(out.get("evidence_units", [])))
    return path


def load_evidence_units(
    student_id: str,
    base_dir: Path | None = None,
) -> dict[str, Any] | None:
    path = evidence_units_path(student_id, base_dir)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_and_save_evidence_units(
    student_id: str,
    *,
    base_dir: Path | None = None,
    worksheets: list[str] | None = None,
    write_per_worksheet: bool = True,
) -> Path:
    document = build_evidence_units_from_student(
        student_id, base_dir=base_dir, worksheets=worksheets,
    )
    path = save_evidence_units(student_id, document, base_dir=base_dir)
    if write_per_worksheet:
        by_ws: dict[str, list[dict[str, Any]]] = {}
        for unit in document.get("evidence_units", []):
            by_ws.setdefault(unit["worksheet_id"], []).append(unit)
        for ws_id, units in sorted(by_ws.items()):
            ws_doc = {
                "schema_version": EVIDENCE_UNITS_SCHEMA_VERSION,
                "artifact": "worksheet_evidence_units",
                "pipeline_stage": "evidence_units",
                "source_stage": "extraction",
                "student_id": student_id,
                "worksheet_id": ws_id,
                "updated_at": document["updated_at"],
                "definition": ASSESSMENT_OBJECT_DEFINITION,
                "note": (
                    f"Canonical Layer 2 output for {ws_id} after OCR/extraction. "
                    "Descriptive only — no behavioural, ILO, Domain, or AI-CFT inference."
                ),
                "evidence_units": units,
            }
            save_worksheet_evidence_units(student_id, ws_id, ws_doc, base_dir=base_dir)
    return path


def generate_sample_evidence_unit() -> dict[str, Any]:
    """Return one illustrative Evidence Unit for documentation and tests."""
    return build_evidence_unit(
        student_id="Student_04",
        worksheet_id="WS3",
        field_input=FieldExtractionInput(
            field_id="WS3_B4",
            raw_content="Yağ değeri 8g eşiğinin altında olduğu için tavsiye edilebilir.",
            rubric_item_id="WS3_B4",
            ocr_confidence=0.97,
            extraction_confidence=0.95,
            provenance_extra={"page": 4, "ocr_engine": "claude_vision"},
        ),
        timestamp=_now_iso(),
        extraction_artifact="students/Student_04/WS3/extraction.json",
    )


def iter_evidence_units(document: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for unit in document.get("evidence_units", []):
        if isinstance(unit, dict):
            yield unit
