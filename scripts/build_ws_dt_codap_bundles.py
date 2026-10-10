#!/usr/bin/env python3
"""Build worksheets/WS14 and worksheets/WS15 bundles."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from build_worksheet_bundles import (  # noqa: E402
    BUNDLE_FILES,
    build_answer_key,
    build_extraction_schema,
)
from pipeline_schema import (  # noqa: E402
    ITEM_IDS_DT_TITANIC,
    ITEM_IDS_DT_XENO,
    RUBRICS_DIR,
    WORKSHEETS_DIR,
)
from worksheet_bundle_data import BEHAVIOUR_ONTOLOGY_PROVENANCE, OB_REF  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

XENO_EMIT_IDS = frozenset({
    "DTI_10", "DTI_12", "DTI_14", "DTI_16", "DTI_18",
    "DTI_20", "DTI_22", "DTI_24", "DTI_26", "DTI_32",
})

TITANIC_EMIT_IDS = frozenset({
    f"DTI_{i:02d}" for i in range(1, 41)
})


def load_rubric(worksheet: str) -> dict[str, Any]:
    path = RUBRICS_DIR / f"{worksheet}_rubric.json"
    rubric = json.loads(path.read_text(encoding="utf-8"))
    rubric.pop("schema_version", None)
    return rubric


def build_behaviour_stub(worksheet: str, rubric: dict[str, Any]) -> dict[str, Any]:
    return {
        "worksheet": worksheet,
        "curriculum_status": "deployed",
        "behaviour_ontology_reference": OB_REF,
        "note": (
            f"{BEHAVIOUR_ONTOLOGY_PROVENANCE} "
            f"{worksheet} is a CODAP Arbor worksheet; behaviour map maintained at "
            "portfolio layer. Worksheet bundle lists rubric item IDs only."
        ),
        "items": {
            item_id: {"extraction_fields": [item_id]}
            for item_id in rubric.get("items", {})
        },
    }


def build_xeno_validity_notes() -> dict[str, Any]:
    return {
        "worksheet": "WS14",
        "curriculum_status": "deployed",
        "construct_threats": [
            "Xeno numeric fields have NO fixed key — the dataset is randomly "
            "assigned per student. Score on internal consistency and structural "
            "invariants (blue=0% sick, pink=100% sick, FP=FN=0), not canonical numbers.",
            "Interpretive items have no single correct answer — scorer drift if "
            "treated as keyed responses.",
        ],
        "leakage_risks": [],
        "evidence_limitations": [
            "After auto-run, N may be 20 or 30 (multiples of 10), not only 10.",
            "Interpretive sections require semantic scoring on rubric components.",
        ],
        "cross_worksheet_dependencies": [],
    }


def build_titanic_validity_notes() -> dict[str, Any]:
    return {
        "worksheet": "WS15",
        "curriculum_status": "deployed",
        "construct_threats": [
            "Titanic numeric fields share fixed CSVs — canonical values exist; "
            "tolerate hand-reading / rounding (±0.02).",
            "VS2 test interpretation items DTI_43–DTI_44 copy VS1 wording with "
            "contradictory premises (trap questions).",
        ],
        "leakage_risks": [],
        "evidence_limitations": [
            "VS2 test set may show survived/died column swap in class scans; "
            "operator correction policy applies.",
            "Interpretive sections require semantic scoring, not example matching.",
        ],
        "cross_worksheet_dependencies": [],
    }


def build_extraction_schema_for(
    worksheet: str,
    rubric: dict[str, Any],
    item_ids: list[str],
    emit_ids: frozenset[str],
    note: str,
) -> dict[str, Any]:
    base = build_extraction_schema("WS1", {"worksheet": "WS1", "items": {}})
    items = rubric.get("items", {})
    base.update({
        "worksheet": worksheet,
        "curriculum_status": "deployed",
        "note": note,
        "fields": [
            {
                "field_id": fid,
                "rubric_item_id": fid,
                "type": "emit_record" if fid in emit_ids else "free_text",
                "required": True,
                "location_hint": f"{worksheet} {items.get(fid, {}).get('region', 'field')}",
            }
            for fid in item_ids
        ],
    })
    return base


def write_bundle(worksheet: str, rubric: dict[str, Any], extras: dict[str, Any]) -> Path:
    out_dir = WORKSHEETS_DIR / worksheet
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "rubric.json": rubric,
        **extras,
        "answer_key.json": build_answer_key(worksheet, rubric),
    }
    for name, payload in artifacts.items():
        if name not in BUNDLE_FILES:
            continue
        path = out_dir / name
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        log.info("Wrote %s", path.relative_to(REPO_ROOT))
    return out_dir


def build_xeno_bundle() -> Path:
    worksheet = "WS14"
    rubric = load_rubric(worksheet)
    return write_bundle(
        worksheet,
        rubric,
        {
            "extraction_schema.json": build_extraction_schema_for(
                worksheet,
                rubric,
                ITEM_IDS_DT_XENO,
                XENO_EMIT_IDS,
                "CODAP Arbor Xeno worksheet — transcribe verbatim. 33 blanks; DTI_01 … DTI_33.",
            ),
            "behaviour_opportunities.json": build_behaviour_stub(worksheet, rubric),
            "validity_notes.json": build_xeno_validity_notes(),
        },
    )


def build_titanic_bundle() -> Path:
    worksheet = "WS15"
    rubric = load_rubric(worksheet)
    return write_bundle(
        worksheet,
        rubric,
        {
            "extraction_schema.json": build_extraction_schema_for(
                worksheet,
                rubric,
                ITEM_IDS_DT_TITANIC,
                TITANIC_EMIT_IDS,
                "CODAP Arbor Titanic worksheet — transcribe verbatim. 47 blanks; DTI_01 … DTI_47.",
            ),
            "behaviour_opportunities.json": build_behaviour_stub(worksheet, rubric),
            "validity_notes.json": build_titanic_validity_notes(),
        },
    )


def main() -> int:
    build_xeno_bundle()
    build_titanic_bundle()
    log.info("Built WS14 and WS15 bundles under %s", WORKSHEETS_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
