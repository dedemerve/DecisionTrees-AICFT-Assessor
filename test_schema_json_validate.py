"""JSON Schema validation tests."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from schema_json_validate import (
    validate_all_mappings_jsonschema,
    validate_all_schemas_wellformed,
    validate_all_worksheet_bundles_jsonschema,
    validate_against_schema,
    validate_framework_jsonschema,
)
from worksheet_bundle_data import BUNDLE_WORKSHEETS


class TestSchemaJsonValidate(unittest.TestCase):
    def test_schemas_wellformed(self) -> None:
        self.assertEqual(validate_all_schemas_wellformed(), [])

    def test_all_bundle_worksheets_jsonschema(self) -> None:
        errors = validate_all_worksheet_bundles_jsonschema(BUNDLE_WORKSHEETS)
        self.assertEqual(errors, [], "\n".join(errors[:20]))

    def test_framework_jsonschema(self) -> None:
        errors = validate_framework_jsonschema()
        self.assertEqual(errors, [], "\n".join(errors[:20]))

    def test_mappings_jsonschema(self) -> None:
        errors = validate_all_mappings_jsonschema()
        self.assertEqual(errors, [], "\n".join(errors[:20]))

    def test_ws_dt_worksheet_id_accepted(self) -> None:
        sample = json.loads(
            (REPO / "worksheets" / "WS_DT" / "validity_notes.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            validate_against_schema(sample, "validity_notes.schema.json"),
            [],
        )

    def test_sample_student_extraction_envelope(self) -> None:
        data = json.loads(
            (REPO / "students" / "Sample_Student" / "WS1" / "extraction.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            validate_against_schema(data, "student_extraction.schema.json"),
            [],
        )


if __name__ == "__main__":
    unittest.main()
