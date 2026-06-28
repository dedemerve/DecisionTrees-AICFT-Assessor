"""test_student_bundle.py — Student bundle schema tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from student_bundle import (
    STUDENT_BUNDLE_SCHEMA_VERSION,
    bundle_path,
    load_bundle,
    new_bundle,
    save_bundle,
    set_section,
)


class TestStudentBundle(unittest.TestCase):
    def test_new_bundle_schema(self):
        bundle = new_bundle("Test_Student")
        self.assertEqual(bundle["schema_version"], STUDENT_BUNDLE_SCHEMA_VERSION)
        self.assertEqual(bundle["student_id"], "Test_Student")
        self.assertIn("worksheets", bundle)
        self.assertIn("portfolio", bundle)

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle = new_bundle("Roundtrip")
            set_section(bundle, "WS1", "extraction", {
                "schema_version": "1.0",
                "worksheet": "WS1",
                "student_id": "Roundtrip",
                "responses": {"WS1_B1": "test"},
            })
            path = save_bundle(bundle, base_dir=base)
            self.assertTrue(path.exists())
            loaded = load_bundle("Roundtrip", base_dir=base)
            self.assertEqual(
                loaded["worksheets"]["WS1"]["extraction"]["responses"]["WS1_B1"],
                "test",
            )

    def test_sample_student_bundle_exists(self):
        path = bundle_path("Sample_Student")
        self.assertTrue(path.exists(), "Run: python student_bundle.py migrate Sample_Student")
        bundle = json.loads(path.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(bundle.get("worksheets", {})), 9)
        self.assertIn("portfolio", bundle)


if __name__ == "__main__":
    unittest.main()
