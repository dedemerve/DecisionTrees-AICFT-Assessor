"""
test_layout_isolator.py — Unit tests (synthetic + project calibration images).

Run:
  python test_layout_isolator.py -v
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from layout_isolator import LayoutIsolator, _line_positions
from pipeline_schema import (
    REPO_ROOT,
    WORKSHEETS_1_10_PAGE_INDEX,
    worksheet_page_image,
)


def _synthetic_table_image(h: int = 500, w: int = 600) -> np.ndarray:
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    x0, y0, x1, y1 = 80, 120, w - 80, h - 100
    cv2.rectangle(img, (x0, y0), (x1, y1), (0, 0, 0), 2)
    rows, cols = 5, 4
    for i in range(1, rows):
        y = y0 + i * (y1 - y0) // rows
        cv2.line(img, (x0, y), (x1, y), (0, 0, 0), 2)
    for j in range(1, cols):
        x = x0 + j * (x1 - x0) // cols
        cv2.line(img, (x, y0), (x, y1), (0, 0, 0), 2)
    return img


def _synthetic_tree_canvas(h: int = 800, w: int = 600) -> np.ndarray:
    img = np.full((h, w, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (60, 280), (w - 60, h - 120), (0, 0, 0), 3)
    return img


class TestLinePositions(unittest.TestCase):
    def test_finds_two_peaks(self):
        proj = np.zeros(100, dtype=np.int32)
        proj[10:15] = 100
        proj[50:55] = 100
        self.assertEqual(len(_line_positions(proj, min_gap=5)), 2)


class TestPageMap(unittest.TestCase):
    def test_ws10_is_page_2(self):
        self.assertEqual(WORKSHEETS_1_10_PAGE_INDEX["WS10"], 2)

    def test_sample_student_ws10_image_exists(self):
        path = worksheet_page_image("Sample_Student", "WS10")
        if path is None:
            self.skipTest("Calibration images not in repo")
        self.assertTrue(path.exists())
        self.assertIn("page_2.jpg", path.name)


class TestWS10Table(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.isolator = LayoutIsolator(output_dir=self.out, debug=False)
        self.img_path = self.out / "ws10_page.jpg"
        cv2.imwrite(str(self.img_path), _synthetic_table_image())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_detects_table_grid(self):
        result = self.isolator.extract_ws10_table(self.img_path, "test_std")
        self.assertIn(result.status, ("success", "partial"))
        self.assertIn("table_grid", {z.zone_type for z in result.zones})

    def test_emits_enough_cells(self):
        result = self.isolator.extract_ws10_table(self.img_path, "test_std")
        self.assertGreaterEqual(result.table_cell_count, 1)


class TestWS6Canvas(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.isolator = LayoutIsolator(output_dir=self.out)
        self.img_path = self.out / "ws6_page.jpg"
        cv2.imwrite(str(self.img_path), _synthetic_tree_canvas())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_detects_tree_canvas_lower_page(self):
        result = self.isolator.extract_ws6_tree_canvas(self.img_path, "test_std")
        self.assertEqual(result.status, "success")
        self.assertEqual(result.zones[0].zone_type, "tree_diagram")


class TestCalibrationIntegration(unittest.TestCase):
    """Real scan from ocr_output/_images/_slot31_check (Felicity bundle)."""

    def setUp(self) -> None:
        self.page = REPO_ROOT / "ocr_output/_images/_slot31_check/page_2.jpg"
        if not self.page.exists():
            self.skipTest("Calibration page_2.jpg not found")
        self.tmp = tempfile.TemporaryDirectory()
        self.isolator = LayoutIsolator(output_dir=Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_real_ws10_page_succeeds(self):
        result = self.isolator.extract_ws10_table(self.page, "calib")
        self.assertEqual(result.status, "success")
        self.assertGreaterEqual(result.table_cell_count, 12)
        self.assertEqual(result.page_index, 2)


class TestWS5Calibration(unittest.TestCase):
    def setUp(self) -> None:
        self.page = REPO_ROOT / "ocr_output/_images/_slot31_check/page_6.jpg"
        if not self.page.exists():
            self.skipTest("Calibration page_6.jpg not found")
        self.tmp = tempfile.TemporaryDirectory()
        self.isolator = LayoutIsolator(output_dir=Path(self.tmp.name))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_ws5_three_tree_bands(self):
        result = self.isolator.extract_ws5_tree_templates(self.page, "calib")
        self.assertEqual(result.status, "success")
        self.assertEqual(len(result.zones), 3)
        self.assertEqual(result.page_index, 6)


class TestErrors(unittest.TestCase):
    def test_missing_file_returns_error(self):
        isolator = LayoutIsolator(output_dir=tempfile.mkdtemp())
        result = isolator.extract_ws10_table("/nonexistent/page.jpg", "x")
        self.assertEqual(result.status, "error")


if __name__ == "__main__":
    unittest.main()
