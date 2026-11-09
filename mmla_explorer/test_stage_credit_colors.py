"""Regression checks for score → website boolean conversion, without rebuilding data."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("site_builder_color_test", Path(__file__).with_name("build_site_data.py"))
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class StageCreditColors(unittest.TestCase):
    def render(self, score, maximum):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder).resolve()
            base = root / "students" / "Fixture" / "WS12"
            base.mkdir(parents=True)
            (root / "rubrics").mkdir()
            (root / "rubrics/WS12_rubric.json").write_text(json.dumps({"items": {"WS12_R5": {"max_score": maximum}}}))
            (base / "extraction.json").write_text(json.dumps({"gate_1_extraction": {"items": {"WS12_test": "written"}}}))
            (base / "scoring.json").write_text(json.dumps({"items": [{"item": "WS12_R5", "score": score}]}))
            with patch.object(builder, "ROOT", root):
                return builder.read_stage_as_ocr("Fixture", {"key": "WS12", "code": "WS12", "raw": None})["checks"][0]["correct"]

    def test_one_of_two_is_partial(self):
        self.assertIsNone(self.render(1, 2))

    def test_two_of_two_is_correct(self):
        self.assertIs(self.render(2, 2), True)

    def test_zero_is_incorrect(self):
        self.assertIs(self.render(0, 2), False)

    def test_missing_score_has_no_verdict(self):
        self.assertIsNone(self.render(None, 2))

    def test_one_point_item_still_correct(self):
        self.assertIs(self.render(1, 1), True)

    def test_fractional_credit_is_partial(self):
        self.assertIsNone(self.render(.5, 1))

    def test_real_affected_students(self):
        for student in ["Bruno", "Irma"]:
            checks = builder.read_stage_as_ocr(student, {"key": "WS12", "code": "WS12", "raw": None})["checks"]
            entry = next(c for c in checks if c["check"] == "item_checks.WS12_R5")
            self.assertEqual(entry["detail"]["score"], 1)
            self.assertIsNone(entry["correct"])


if __name__ == "__main__":
    unittest.main()
