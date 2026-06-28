"""
schema_json_validate.py — JSON Schema (draft 2020-12) validation for repo artifacts.

Complements schema_validate.py (hand-written domain rules). Bundle and framework
instances are validated against schema/*.schema.json via the jsonschema library.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterator

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource
import referencing.jsonschema

REPO_ROOT = Path(__file__).resolve().parent
SCHEMA_DIR = REPO_ROOT / "schema"
WORKSHEETS_DIR = REPO_ROOT / "worksheets"
FRAMEWORK_DIR = REPO_ROOT / "framework"
MAPPINGS_DIR = REPO_ROOT / "mappings"

BUNDLE_FILE_SCHEMA: dict[str, str] = {
    "answer_key.json": "answer_key_v1.schema.json",
    "behaviour_opportunities.json": "behaviour_opportunities_v1.schema.json",
    "extraction_schema.json": "extraction_schema_v1.schema.json",
    "validity_notes.json": "validity_notes_v1.schema.json",
    "rubric.json": "rubric_v3.schema.json",
}

FRAMEWORK_FILE_SCHEMA: dict[str, str] = {
    "Observable_Behaviours.json": "observable_behaviours_v1.schema.json",
    "Learning_Objects.json": "learning_objects_v1.schema.json",
    "Behaviour_to_ILO.json": "behaviour_to_ilo_v1.schema.json",
    "Domain_to_AI_CFT.json": "domain_to_ai_cft_v1.schema.json",
    "Domain_Understanding.json": "domain_understanding_v1.schema.json",
    "LO_to_Domain_Understanding.json": "lo_to_domain_understanding_v1.schema.json",
}

STUDENT_ARTIFACT_SCHEMA: dict[str, str] = {
    "extraction": "student_extraction_v1.schema.json",
    "scoring": "scoring_v1.schema.json",
    "evidence": "evidence_v1.schema.json",
    "validation": "validation_v1.schema.json",
}


def _schema_uri(path: Path, doc: dict[str, Any]) -> str:
    return str(doc.get("$id") or path.name)


@lru_cache(maxsize=1)
def schema_registry() -> Registry:
    """Load all schema/*.schema.json into a shared referencing registry."""
    resources: list[tuple[str, Resource]] = []
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        uri = _schema_uri(path, doc)
        resource = Resource.from_contents(
            doc,
            default_specification=referencing.jsonschema.DRAFT202012,
        )
        resources.append((uri, resource))
        resources.append((path.name, resource))
    return Registry().with_resources(resources)


@lru_cache(maxsize=None)
def validator_for(schema_filename: str) -> Draft202012Validator:
    path = SCHEMA_DIR / schema_filename
    if not path.is_file():
        raise FileNotFoundError(f"schema not found: {path}")
    doc = json.loads(path.read_text(encoding="utf-8"))
    return Draft202012Validator(doc, registry=schema_registry())


def _format_errors(
    errors: Iterator[Any],
    *,
    prefix: str = "",
) -> list[str]:
    out: list[str] = []
    for err in sorted(errors, key=lambda e: list(e.path)):
        loc = ".".join(str(p) for p in err.path) if err.path else "(root)"
        out.append(f"{prefix}{loc}: {err.message}")
    return out


def validate_against_schema(
    instance: Any,
    schema_filename: str,
    *,
    prefix: str = "",
) -> list[str]:
    """Return human-readable JSON Schema validation errors (empty if valid)."""
    try:
        validator = validator_for(schema_filename)
    except SchemaError as exc:
        return [f"{prefix}schema {schema_filename!r} invalid: {exc.message}"]
    return _format_errors(validator.iter_errors(instance), prefix=prefix)


def validate_bundle_file(
    worksheet: str,
    filename: str,
    data: dict[str, Any],
) -> list[str]:
    schema_name = BUNDLE_FILE_SCHEMA.get(filename)
    if not schema_name:
        return [f"{worksheet}/{filename}: no JSON Schema mapping"]
    prefix = f"{worksheet}/{filename}: "
    return validate_against_schema(data, schema_name, prefix=prefix)


def validate_worksheet_bundle(worksheet: str) -> list[str]:
    """Validate all five files under worksheets/<WS>/."""
    bundle_dir = WORKSHEETS_DIR / worksheet
    if not bundle_dir.is_dir():
        return [f"{worksheet}: missing bundle directory"]
    errors: list[str] = []
    for filename in BUNDLE_FILE_SCHEMA:
        path = bundle_dir / filename
        if not path.is_file():
            errors.append(f"{worksheet}/{filename}: missing")
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{worksheet}/{filename}: invalid JSON — {exc}")
            continue
        errors.extend(validate_bundle_file(worksheet, filename, data))
    return errors


def validate_all_worksheet_bundles_jsonschema(worksheets: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    for ws in worksheets:
        errors.extend(validate_worksheet_bundle(ws))
    return errors


def validate_framework_jsonschema() -> list[str]:
    errors: list[str] = []
    for filename, schema_name in FRAMEWORK_FILE_SCHEMA.items():
        path = FRAMEWORK_DIR / filename
        if not path.is_file():
            errors.append(f"framework/{filename}: missing")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        errors.extend(
            validate_against_schema(data, schema_name, prefix=f"framework/{filename}: ")
        )
    return errors


def validate_mapping_file(path: Path) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return validate_against_schema(data, "mapping_v2.schema.json", prefix=f"{path.name}: ")


def validate_all_mappings_jsonschema() -> list[str]:
    errors: list[str] = []
    for path in sorted(MAPPINGS_DIR.glob("*_AICFT_mapping.json")):
        errors.extend(validate_mapping_file(path))
    return errors


def validate_student_artifact(
    stage: str,
    data: dict[str, Any],
    *,
    prefix: str = "",
) -> list[str]:
    schema_name = STUDENT_ARTIFACT_SCHEMA.get(stage)
    if not schema_name:
        return []
    return validate_against_schema(data, schema_name, prefix=prefix)


def validate_layout_roi_manifest(data: dict[str, Any], *, prefix: str = "") -> list[str]:
    return validate_against_schema(data, "layout_roi_v1.schema.json", prefix=prefix)


def validate_all_schemas_wellformed() -> list[str]:
    """Ensure every schema file compiles."""
    errors: list[str] = []
    for path in sorted(SCHEMA_DIR.glob("*.schema.json")):
        try:
            validator_for(path.name)
        except (SchemaError, json.JSONDecodeError, FileNotFoundError) as exc:
            errors.append(f"{path.name}: {exc}")
    return errors
