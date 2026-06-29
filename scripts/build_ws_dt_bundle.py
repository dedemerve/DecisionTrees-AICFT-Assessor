#!/usr/bin/env python3
"""Build worksheets/WS_DT bundle (CODAP plugged inquiry worksheet)."""

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
from pipeline_schema import ITEM_IDS_DT, RUBRICS_DIR, WORKSHEETS_DIR  # noqa: E402
from worksheet_bundle_data import BEHAVIOUR_ONTOLOGY_PROVENANCE, OB_REF  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

WORKSHEET = "WS_DT"


def load_rubric() -> dict[str, Any]:
    path = RUBRICS_DIR / "WS_DT_rubric.json"
    rubric = json.loads(path.read_text(encoding="utf-8"))
    rubric.pop("schema_version", None)
    return rubric


def build_behaviour_opportunities_stub(rubric: dict[str, Any]) -> dict[str, Any]:
    return {
        "worksheet": WORKSHEET,
        "curriculum_status": "deployed",
        "behaviour_ontology_reference": OB_REF,
        "note": (
            f"{BEHAVIOUR_ONTOLOGY_PROVENANCE} "
            "WS_DT behaviour map maintained in mappings/WS_DT_AICFT_mapping.json "
            "at portfolio layer; worksheet bundle lists rubric item IDs only."
        ),
        "items": {
            item_id: {"extraction_fields": [item_id]}
            for item_id in rubric.get("items", {})
        },
    }


def build_validity_notes() -> dict[str, Any]:
    return {
        "worksheet": WORKSHEET,
        "curriculum_status": "deployed",
        "construct_threats": [
            "Open interpretive items have no single correct answer — scorer drift if treated as keyed responses.",
            "EMIT numeric fields depend on each student's CODAP choices.",
        ],
        "leakage_risks": [],
        "evidence_limitations": [
            "Interpretive sections require semantic scoring on rubric components, not example-answer matching.",
            "Train/test comparison (F) may need log corroboration when available.",
        ],
        "cross_worksheet_dependencies": [],
    }


def build_ws_dt_extraction_schema(rubric: dict[str, Any]) -> dict[str, Any]:
    base = build_extraction_schema("WS1", {"worksheet": "WS1", "items": {}})
    base.update({
        "worksheet": WORKSHEET,
        "curriculum_status": "deployed",
        "note": (
            "CODAP Arbor worksheet DT — transcribe student text and EMIT fields verbatim. "
            "Sections A–G; item IDs DT_A_Q1 … DT_G_Q2."
        ),
        "fields": [
            {
                "field_id": fid,
                "rubric_item_id": fid,
                "type": "emit_record" if fid in {
                    "DT_B_Q1", "DT_B_Q2", "DT_B_Q3",
                    "DT_C_Q1", "DT_D_Q1", "DT_F_Q1",
                } else "free_text",
                "required": True,
                "location_hint": f"{WORKSHEET} section field",
            }
            for fid in ITEM_IDS_DT
        ],
    })
    return base


def write_bundle() -> Path:
    out_dir = WORKSHEETS_DIR / WORKSHEET
    out_dir.mkdir(parents=True, exist_ok=True)
    rubric = load_rubric()

    artifacts = {
        "rubric.json": rubric,
        "extraction_schema.json": build_ws_dt_extraction_schema(rubric),
        "behaviour_opportunities.json": build_behaviour_opportunities_stub(rubric),
        "validity_notes.json": build_validity_notes(),
        "answer_key.json": build_answer_key(WORKSHEET, rubric),
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


def main() -> int:
    write_bundle()
    log.info("Built WS_DT bundle under %s", WORKSHEETS_DIR / WORKSHEET)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
