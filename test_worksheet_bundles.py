"""Unit tests for Phase 2 worksheet bundle engineering."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from pipeline_schema import WORKSHEETS_DIR, load_rubric  # noqa: E402
from validate_worksheet_bundles import validate_all_bundles  # noqa: E402
from worksheet_bundle_data import (  # noqa: E402
    ALL_WORKSHEETS,
    BUNDLE_FILES,
    DEPLOYED_WORKSHEETS,
)


@pytest.fixture(scope="module", autouse=True)
def build_bundles_once() -> None:
    subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "build_worksheet_bundles.py")],
        check=True,
        cwd=REPO_ROOT,
    )


def test_all_worksheet_directories_exist() -> None:
    for ws in ALL_WORKSHEETS:
        assert (WORKSHEETS_DIR / ws).is_dir(), f"missing {ws}"


def test_bundle_contains_exactly_five_files() -> None:
    for ws in ALL_WORKSHEETS:
        files = {p.name for p in (WORKSHEETS_DIR / ws).iterdir() if p.is_file()}
        assert files == set(BUNDLE_FILES), f"{ws}: {files}"


def test_validate_all_bundles_passes() -> None:
    errors = validate_all_bundles()
    assert errors == [], "\n".join(errors)


def test_deployed_rubrics_load_from_bundle() -> None:
    for ws in sorted(DEPLOYED_WORKSHEETS):
        rubric = load_rubric(ws)
        assert rubric["worksheet"] == ws
        assert rubric.get("items"), f"{ws} should have rubric items"
        assert rubric.get("curriculum_status") != "not_deployed"


def test_behaviour_opportunities_reference_only_ob_ids() -> None:
    ob_data = json.loads(
        (REPO_ROOT / "framework" / "Observable_Behaviours.json").read_text(encoding="utf-8")
    )
    ob_ids = set(ob_data["behaviours"].keys())
    for ws in DEPLOYED_WORKSHEETS:
        bo = json.loads(
            (WORKSHEETS_DIR / ws / "behaviour_opportunities.json").read_text(encoding="utf-8")
        )
        for item_id, entry in bo["items"].items():
            for opp in entry["opportunities"]:
                assert opp["behaviour_id"] in ob_ids, f"{ws}/{item_id}: {opp['behaviour_id']}"


def test_extraction_schema_prohibits_interpretation() -> None:
    for ws in ALL_WORKSHEETS:
        schema = json.loads(
            (WORKSHEETS_DIR / ws / "extraction_schema.json").read_text(encoding="utf-8")
        )
        assert schema["interpretation_prohibited"] is True
        assert schema["pipeline_stage"] == "extraction_only"
