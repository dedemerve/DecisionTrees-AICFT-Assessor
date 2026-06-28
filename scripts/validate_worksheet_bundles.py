#!/usr/bin/env python3
"""
validate_worksheet_bundles.py

Validate worksheet bundles (unplugged WS1, WS3–WS11, plus CODAP WS_DT) against
JSON Schema and framework constraints.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from pipeline_schema import validate_rubric_v3  # noqa: E402
from schema_json_validate import validate_bundle_file  # noqa: E402
from worksheet_bundle_data import (  # noqa: E402
    BEHAVIOUR_MAP,
    BUNDLE_FILES,
    BUNDLE_WORKSHEETS,
    CODAP_WORKSHEETS,
    DEPLOYED_WORKSHEETS,
    FORBIDDEN_SUBSTRINGS,
    OB_REF,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

WORKSHEETS_DIR = REPO_ROOT / "worksheets"
FRAMEWORK_OB = REPO_ROOT / "framework" / "Observable_Behaviours.json"

OB_ID_PATTERN = re.compile(r"^OB_[A-Z]{3}_\d{3}$")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_ob_ids() -> set[str]:
    data = _load_json(FRAMEWORK_OB)
    behaviours = data.get("behaviours", data.get("observable_behaviours", {}))
    if isinstance(behaviours, dict):
        return {b.get("id", k) for k, b in behaviours.items() if isinstance(b, dict)}
    return set()


def _forbidden_scan(obj: Any, path: str = "") -> list[str]:
    errors: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key_lower = str(k).lower()
            for forbidden in FORBIDDEN_SUBSTRINGS:
                if forbidden in key_lower:
                    errors.append(f"{path}.{k}: forbidden key fragment {forbidden!r}")
            errors.extend(_forbidden_scan(v, f"{path}.{k}" if path else str(k)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            errors.extend(_forbidden_scan(v, f"{path}[{i}]"))
    elif isinstance(obj, str):
        lower = obj.lower()
        for term in ("lo3.", "lo3_", "competency_id", "domain_understanding_id"):
            if term in lower:
                errors.append(f"{path}: forbidden value fragment {term!r} in string")
    return errors


def validate_bundle_directory(worksheet: str, ob_ids: set[str]) -> list[str]:
    errors: list[str] = []
    bundle_dir = WORKSHEETS_DIR / worksheet
    prefix = f"{worksheet}"
    codap = worksheet in CODAP_WORKSHEETS

    if not bundle_dir.is_dir():
        return [f"{prefix}: missing bundle directory {bundle_dir}"]

    present = {p.name for p in bundle_dir.iterdir() if p.is_file()}
    missing = set(BUNDLE_FILES) - present
    extra = present - set(BUNDLE_FILES)
    if missing:
        errors.append(f"{prefix}: missing files {sorted(missing)}")
    if extra:
        errors.append(f"{prefix}: extraneous files {sorted(extra)}")

    payloads: dict[str, Any] = {}
    for name in BUNDLE_FILES:
        path = bundle_dir / name
        if not path.exists():
            continue
        try:
            payloads[name] = _load_json(path)
        except json.JSONDecodeError as exc:
            errors.append(f"{prefix}/{name}: invalid JSON — {exc}")
            return errors
        errors.extend(_forbidden_scan(payloads[name], f"{prefix}/{name}"))
        errors.extend(validate_bundle_file(worksheet, name, payloads[name]))

    rubric = payloads.get("rubric.json", {})
    extraction = payloads.get("extraction_schema.json", {})
    behaviour = payloads.get("behaviour_opportunities.json", {})
    validity = payloads.get("validity_notes.json", {})
    answer_key = payloads.get("answer_key.json", {})

    if rubric.get("worksheet") != worksheet:
        errors.append(f"{prefix}: rubric worksheet mismatch")
    if extraction.get("interpretation_prohibited") is not True:
        errors.append(f"{prefix}: extraction_schema must set interpretation_prohibited=true")
    if behaviour.get("behaviour_ontology_reference") != OB_REF:
        errors.append(f"{prefix}: behaviour_ontology_reference must be {OB_REF!r}")

    deployed = worksheet in DEPLOYED_WORKSHEETS
    for artifact_name, artifact in (
        ("extraction_schema.json", extraction),
        ("behaviour_opportunities.json", behaviour),
        ("validity_notes.json", validity),
        ("answer_key.json", answer_key),
    ):
        status = artifact.get("curriculum_status")
        expected = "deployed" if deployed else "not_deployed"
        if status != expected:
            errors.append(
                f"{prefix}/{artifact_name}: curriculum_status={status!r}, expected {expected!r}"
            )

    if deployed:
        errors.extend(validate_rubric_v3(rubric, f"{prefix}/rubric.json"))
        rubric_items = set(rubric.get("items", {}))
        if not rubric_items:
            errors.append(f"{prefix}: deployed worksheet must have rubric items")

        bo_items = behaviour.get("items", {})
        missing_bo = rubric_items - set(bo_items)
        extra_bo = set(bo_items) - rubric_items
        if missing_bo:
            errors.append(f"{prefix}: behaviour_opportunities missing items {sorted(missing_bo)}")
        if extra_bo:
            errors.append(f"{prefix}: behaviour_opportunities extra items {sorted(extra_bo)}")

        if not codap:
            for item_id, entry in bo_items.items():
                opps = entry.get("opportunities", [])
                if not opps:
                    errors.append(f"{prefix}: {item_id} has no behaviour opportunities")
                for opp in opps:
                    bid = opp.get("behaviour_id", "")
                    if not OB_ID_PATTERN.match(bid):
                        errors.append(f"{prefix}: {item_id} invalid behaviour_id {bid!r}")
                    elif bid not in ob_ids:
                        errors.append(f"{prefix}: {item_id} unknown behaviour_id {bid!r}")

        ak_items = set(answer_key.get("items", {}))
        if ak_items != rubric_items:
            missing_ak = rubric_items - ak_items
            if missing_ak:
                errors.append(f"{prefix}: answer_key missing items {sorted(missing_ak)}")

        field_ids = {f["field_id"] for f in extraction.get("fields", []) if "field_id" in f}
        if not field_ids:
            errors.append(f"{prefix}: extraction_schema has no fields")

        if not codap and worksheet in BEHAVIOUR_MAP:
            for item_id in rubric_items:
                if item_id not in BEHAVIOUR_MAP.get(worksheet, {}):
                    errors.append(f"{prefix}: BEHAVIOUR_MAP missing definition for {item_id}")
    else:
        if rubric.get("items"):
            errors.append(f"{prefix}: not_deployed worksheet must have empty rubric items")
        if behaviour.get("items"):
            errors.append(f"{prefix}: not_deployed worksheet must have empty behaviour items")

    return errors


def validate_all_bundles() -> list[str]:
    ob_ids = _load_ob_ids()
    if not ob_ids:
        return ["framework/Observable_Behaviours.json: no behaviour IDs loaded"]
    errors: list[str] = []
    for ws in BUNDLE_WORKSHEETS:
        errors.extend(validate_bundle_directory(ws, ob_ids))
    return errors


def main() -> int:
    errors = validate_all_bundles()
    if errors:
        for err in errors:
            log.error("%s", err)
        log.error("Validation FAILED (%d errors)", len(errors))
        return 1
    log.info("All %d worksheet bundles valid", len(BUNDLE_WORKSHEETS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
