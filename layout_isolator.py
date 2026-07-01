"""
layout_isolator.py — Phase 1: Layout Parsing and RoI Isolation (ILSA-grade).

Project-aware layout parser for ProDaBi / DecisionTrees-AICFT-Assessor.

Uses pipeline_schema.WORKSHEETS_1_10_PAGE_INDEX for deterministic page routing
(WS10 = page 2, WS5 = page 6, etc.). WS6 draw-canvas is optional when a
supplemental scan exists; it is not on the 6-page Worksheets1-10.pdf bundle.

Output: layout_rois/<student_id>/<worksheet>_layout.json + cropped PNGs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Literal

import cv2
import numpy as np

from pipeline_schema import (
    LAYOUT_ISOLATION_WORKSHEETS,
    LAYOUT_ROIS_DIR,
    REPO_ROOT,
    WORKSHEETS_1_10_PAGE_INDEX,
    layout_manifest_path,
    slot_dir_for_student,
    worksheet_page_image,
)

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_DIR = LAYOUT_ROIS_DIR

# WS10: 7 data rows + header; 2 columns (threshold, misclassification count).
WS10_MIN_TABLE_CELLS = 12
WS10_ENERGY_ROW_COUNT = 7

ZoneType = Literal["handwriting", "table_grid", "table_cell", "tree_diagram"]


class ExtractionStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PARTIAL = "partial"


@dataclass(frozen=True)
class BoundingBox:
    x: int
    y: int
    w: int
    h: int

    @property
    def area(self) -> int:
        return self.w * self.h

    @property
    def aspect_ratio(self) -> float:
        return self.w / max(self.h, 1)

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}

    def crop(self, image: np.ndarray) -> np.ndarray:
        return image[self.y : self.y + self.h, self.x : self.x + self.w]


@dataclass
class RoiZone:
    zone_id: str
    zone_type: ZoneType
    bbox: BoundingBox
    file_path: str | None = None
    worksheet: str | None = None
    row: int | None = None
    col: int | None = None
    parent_zone_id: str | None = None
    item_id: str | None = None
    status: str = ExtractionStatus.SUCCESS.value
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "zone_id": self.zone_id,
            "type": self.zone_type,
            "coordinates": self.bbox.to_dict(),
            "status": self.status,
        }
        if self.file_path:
            d["file_path"] = self.file_path
        if self.worksheet:
            d["worksheet"] = self.worksheet
        if self.row is not None:
            d["row"] = self.row
        if self.col is not None:
            d["col"] = self.col
        if self.parent_zone_id:
            d["parent_zone_id"] = self.parent_zone_id
        if self.item_id:
            d["item_id"] = self.item_id
        if self.message:
            d["message"] = self.message
        return d


@dataclass
class LayoutResult:
    student_id: str
    worksheet: str
    source_image: str
    page_index: int | None = None
    status: str = ExtractionStatus.SUCCESS.value
    message: str | None = None
    zones: list[RoiZone] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "student_id": self.student_id,
            "worksheet": self.worksheet,
            "source_image": self.source_image,
            "page_index": self.page_index,
            "status": self.status,
            "message": self.message,
            "zone_count": len(self.zones),
            "zones": [z.to_dict() for z in self.zones],
        }

    def save(self, output_dir: Path | None = None) -> Path:
        out_dir = output_dir or (DEFAULT_OUTPUT_DIR / self.student_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{self.worksheet}_layout.json"
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return path

    @property
    def table_cell_count(self) -> int:
        return sum(1 for z in self.zones if z.zone_type == "table_cell")

    @property
    def zone_count(self) -> int:
        return len(self.zones)


def _line_positions(projection: np.ndarray, min_gap: int = 8) -> list[int]:
    thresh = max(10, int(0.4 * projection.max())) if projection.max() > 0 else 10
    active = projection >= thresh
    positions: list[int] = []
    i = 0
    n = len(active)
    while i < n:
        if not active[i]:
            i += 1
            continue
        start = i
        while i < n and active[i]:
            i += 1
        center = (start + i - 1) // 2
        if not positions or center - positions[-1] >= min_gap:
            positions.append(center)
    return positions


def _rel_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


class LayoutIsolator:
    """
    Deterministic layout parser aligned with ProDaBi worksheet geometry.

    Primary targets:
      WS10 page 2 — energy threshold table (feeds numeric_optimal / row_consistency)
      WS5  page 6 — three printed decision-tree templates (threshold trials)
      WS6  optional — large draw canvas for dt_vision_pipeline (supplemental scan)
    """

    def __init__(
        self,
        output_dir: Path | str | None = None,
        *,
        debug: bool = False,
        min_table_area_frac: float = 0.02,
        max_table_area_frac: float = 0.55,
        min_canvas_area_frac: float = 0.18,
        max_canvas_area_frac: float = 0.65,
    ) -> None:
        self.output_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
        self.debug = debug
        self.min_table_area_frac = min_table_area_frac
        self.max_table_area_frac = max_table_area_frac
        self.min_canvas_area_frac = min_canvas_area_frac
        self.max_canvas_area_frac = max_canvas_area_frac

    def load_image(self, image_path: str | Path) -> np.ndarray:
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {path}")
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError(f"Could not decode image: {path}")
        return image

    def preprocess_image(self, image: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        if image.ndim == 2:
            gray = image
            original = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        else:
            original = image
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        binary = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            15, 5,
        )
        return original, binary

    def _student_dir(self, student_id: str) -> Path:
        d = self.output_dir / student_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _save_crop(self, crop: np.ndarray, student_id: str, filename: str) -> str:
        path = self._student_dir(student_id) / filename
        cv2.imwrite(str(path), crop)
        return _rel_path(path)

    def _save_debug_overlay(
        self, image: np.ndarray, zones: list[RoiZone], student_id: str, tag: str,
    ) -> None:
        if not self.debug:
            return
        vis = image.copy()
        colors = {
            "table_grid": (0, 180, 0),
            "table_cell": (0, 255, 255),
            "tree_diagram": (255, 120, 0),
            "handwriting": (200, 0, 200),
        }
        for zone in zones:
            b = zone.bbox
            color = colors.get(zone.zone_type, (128, 128, 128))
            cv2.rectangle(vis, (b.x, b.y), (b.x + b.w, b.y + b.h), color, 2)
            cv2.putText(
                vis, zone.zone_id[:28], (b.x, max(12, b.y - 4)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1, cv2.LINE_AA,
            )
        cv2.imwrite(str(self._student_dir(student_id) / f"debug_{tag}.png"), vis)

    def _detect_table_mask(self, binary: np.ndarray, scale: float = 1.0) -> np.ndarray:
        h, w = binary.shape[:2]
        hk = max(15, int(40 * scale))
        vk = max(15, int(40 * scale))
        hk_el = cv2.getStructuringElement(cv2.MORPH_RECT, (hk, 1))
        vk_el = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vk))
        horizontal = cv2.morphologyEx(binary, cv2.MORPH_OPEN, hk_el, iterations=2)
        vertical = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vk_el, iterations=2)
        table_mask = cv2.addWeighted(horizontal, 0.5, vertical, 0.5, 0.0)
        _, table_mask = cv2.threshold(table_mask, 40, 255, cv2.THRESH_BINARY)
        return table_mask

    def _best_grid_contour(self, table_mask: np.ndarray, page_area: int) -> BoundingBox | None:
        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        min_area = int(self.min_table_area_frac * page_area)
        max_area = int(self.max_table_area_frac * page_area)
        candidates: list[BoundingBox] = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if area < min_area or area > max_area or w < 80 or h < 40:
                continue
            candidates.append(BoundingBox(x, y, w, h))
        return max(candidates, key=lambda b: b.area) if candidates else None

    def extract_table_cells(
        self,
        table_crop_bgr: np.ndarray,
        table_bbox: BoundingBox,
        *,
        student_id: str,
        worksheet: str,
        zone_prefix: str,
    ) -> list[RoiZone]:
        _, binary = self.preprocess_image(table_crop_bgr)
        h, w = binary.shape[:2]
        scale = min(h, w) / 400.0
        mask = self._detect_table_mask(binary, scale=scale)
        row_lines = _line_positions(mask.sum(axis=1), min_gap=max(6, h // 30))
        col_lines = _line_positions(mask.sum(axis=0), min_gap=max(6, w // 30))
        if len(row_lines) < 2:
            row_lines = [0, h - 1]
        if len(col_lines) < 2:
            col_lines = [0, w - 1]

        cells: list[RoiZone] = []
        for ri in range(len(row_lines) - 1):
            y1, y2 = row_lines[ri], row_lines[ri + 1]
            if y2 - y1 < 12:
                continue
            for ci in range(len(col_lines) - 1):
                x1, x2 = col_lines[ci], col_lines[ci + 1]
                if x2 - x1 < 12:
                    continue
                local = BoundingBox(x1, y1, x2 - x1, y2 - y1)
                crop = local.crop(table_crop_bgr)
                if crop.size == 0:
                    continue
                zone_id = f"{zone_prefix}_r{ri}c{ci}"
                cells.append(RoiZone(
                    zone_id=zone_id,
                    zone_type="table_cell",
                    bbox=BoundingBox(table_bbox.x + x1, table_bbox.y + y1, x2 - x1, y2 - y1),
                    file_path=self._save_crop(crop, student_id, f"{zone_id}.png"),
                    worksheet=worksheet,
                    row=ri,
                    col=ci,
                    parent_zone_id=zone_prefix,
                ))
        return cells

    def _extract_ws10_optimal_blank(
        self,
        original: np.ndarray,
        table_bbox: BoundingBox,
        *,
        student_id: str,
    ) -> RoiZone | None:
        """Crop the 'Optimum eşik değer' handwritten answer below the table (WS10_B8)."""
        h, w = original.shape[:2]
        y1 = min(h - 1, table_bbox.y + table_bbox.h + 8)
        y2 = min(h, y1 + int(0.12 * h))
        x1 = max(0, table_bbox.x - int(0.05 * w))
        x2 = min(w, table_bbox.x + int(0.55 * table_bbox.w))
        if y2 - y1 < 20 or x2 - x1 < 40:
            return None
        bbox = BoundingBox(x1, y1, x2 - x1, y2 - y1)
        crop = bbox.crop(original)
        zone_id = f"{student_id}_ws10_optimal_answer"
        return RoiZone(
            zone_id=zone_id,
            zone_type="handwriting",
            bbox=bbox,
            file_path=self._save_crop(crop, student_id, f"{zone_id}.png"),
            worksheet="WS10",
            item_id="WS10_B8",
        )

    def extract_ws10_table(
        self,
        image_path: str | Path,
        student_id: str,
        *,
        page_index: int | None = None,
    ) -> LayoutResult:
        """WS10 page 2: 7-row energy table + optimal-threshold blank."""
        path = Path(image_path)
        try:
            original, binary = self.preprocess_image(self.load_image(path))
        except (FileNotFoundError, ValueError) as exc:
            return LayoutResult(
                student_id=student_id, worksheet="WS10", source_image=str(path),
                page_index=page_index, status=ExtractionStatus.ERROR.value, message=str(exc),
            )

        page_area = original.shape[0] * original.shape[1]
        table_bbox = self._best_grid_contour(self._detect_table_mask(binary), page_area)
        if table_bbox is None:
            return LayoutResult(
                student_id=student_id, worksheet="WS10", source_image=str(path),
                page_index=page_index, status=ExtractionStatus.ERROR.value,
                message="WS10 numeric table not detected. Expected Worksheets1-10 page 2.",
            )

        table_crop = table_bbox.crop(original)
        prefix = f"{student_id}_ws10_table"
        zones: list[RoiZone] = [
            RoiZone(
                zone_id=prefix,
                zone_type="table_grid",
                bbox=table_bbox,
                file_path=self._save_crop(table_crop, student_id, f"{prefix}.png"),
                worksheet="WS10",
            )
        ]
        cells = self.extract_table_cells(
            table_crop, table_bbox,
            student_id=student_id, worksheet="WS10", zone_prefix=prefix,
        )
        zones.extend(cells)

        optimal = self._extract_ws10_optimal_blank(original, table_bbox, student_id=student_id)
        if optimal:
            zones.append(optimal)

        n_cells = len(cells)
        if n_cells >= WS10_MIN_TABLE_CELLS:
            status = ExtractionStatus.SUCCESS
            msg = None
        elif n_cells > 0:
            status = ExtractionStatus.PARTIAL
            msg = f"Table found but only {n_cells} cells (expected >= {WS10_MIN_TABLE_CELLS})."
        else:
            status = ExtractionStatus.PARTIAL
            msg = "Table bounding box found but cell grid could not be split."

        result = LayoutResult(
            student_id=student_id, worksheet="WS10", source_image=_rel_path(path),
            page_index=page_index or WORKSHEETS_1_10_PAGE_INDEX.get("WS10"),
            status=status.value, message=msg, zones=zones,
        )
        self._save_debug_overlay(original, zones, student_id, "WS10")
        return result

    def extract_ws5_tree_templates(
        self,
        image_path: str | Path,
        student_id: str,
        *,
        page_index: int | None = None,
    ) -> LayoutResult:
        """
        WS5 page 6: three stacked decision-tree trial templates.

        ProDaBi v4 prints three identical tree forms vertically. We use fixed
        horizontal bands (calibrated on Felicity bundle) rather than contour search.
        """
        path = Path(image_path)
        try:
            original, _ = self.preprocess_image(self.load_image(path))
        except (FileNotFoundError, ValueError) as exc:
            return LayoutResult(
                student_id=student_id, worksheet="WS5", source_image=str(path),
                page_index=page_index, status=ExtractionStatus.ERROR.value, message=str(exc),
            )

        h, w = original.shape[:2]
        # Content band excludes header/footer (ProDaBi v4, page 6).
        y_start = int(0.11 * h)
        y_end = int(0.90 * h)
        x_margin = int(0.05 * w)
        content_w = w - 2 * x_margin
        band_h = (y_end - y_start) // 3

        zones: list[RoiZone] = []
        for i in range(3):
            y1 = y_start + i * band_h
            y2 = y_start + (i + 1) * band_h - 6
            bbox = BoundingBox(x_margin, y1, content_w, y2 - y1)
            crop = bbox.crop(original)
            zone_id = f"{student_id}_ws5_tree_{i + 1}"
            zones.append(RoiZone(
                zone_id=zone_id,
                zone_type="tree_diagram",
                bbox=bbox,
                file_path=self._save_crop(crop, student_id, f"{zone_id}.png"),
                worksheet="WS5",
            ))

        result = LayoutResult(
            student_id=student_id, worksheet="WS5", source_image=_rel_path(path),
            page_index=page_index or WORKSHEETS_1_10_PAGE_INDEX.get("WS5"),
            status=ExtractionStatus.SUCCESS.value,
            zones=zones,
        )
        self._save_debug_overlay(original, zones, student_id, "WS5")
        return result

    def extract_ws6_tree_canvas(
        self,
        image_path: str | Path,
        student_id: str,
        *,
        page_index: int | None = None,
    ) -> LayoutResult:
        """
        WS6 draw canvas — only when a supplemental full-page scan is provided.

        Rejects small printed trees (WS3/WS7) by requiring a large lower-page frame.
        """
        path = Path(image_path)
        try:
            original, binary = self.preprocess_image(self.load_image(path))
        except (FileNotFoundError, ValueError) as exc:
            return LayoutResult(
                student_id=student_id, worksheet="WS6", source_image=str(path),
                page_index=page_index, status=ExtractionStatus.ERROR.value, message=str(exc),
            )

        h, w = original.shape[:2]
        img_area = h * w
        dilated = cv2.dilate(binary, np.ones((5, 5), np.uint8), iterations=1)
        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        canvas_bbox: BoundingBox | None = None
        best_score = 0.0
        min_area = int(self.min_canvas_area_frac * img_area)
        max_area = int(self.max_canvas_area_frac * img_area)

        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            area = bw * bh
            if area < min_area or area > max_area:
                continue
            ratio = bw / max(bh, 1)
            if not (0.6 <= ratio <= 2.2):
                continue
            # Prefer large frames in the lower two-thirds (draw canvas, not header tree).
            center_y = y + bh / 2
            if center_y < 0.25 * h:
                continue
            score = area * (1.0 + center_y / h)
            if score > best_score:
                best_score = score
                canvas_bbox = BoundingBox(x, y, bw, bh)

        if canvas_bbox is None:
            # ProDaBi v4 Worksheet 6 template: printed tree diagram (not a blank canvas).
            img_area = h * w
            fallback = BoundingBox(
                int(0.06 * w), int(0.20 * h),
                int(0.88 * w), int(0.62 * h),
            )
            if fallback.area >= int(0.15 * img_area):
                canvas_bbox = fallback

        if canvas_bbox is None:
            return LayoutResult(
                student_id=student_id, worksheet="WS6", source_image=_rel_path(path),
                page_index=page_index,
                status=ExtractionStatus.ERROR.value,
                message=(
                    "WS6 draw canvas not detected. The 6-page Worksheets1-10 bundle "
                    "does not include WS6; pass a supplemental WS6 scan."
                ),
            )

        crop = canvas_bbox.crop(original)
        zone_id = f"{student_id}_ws6_tree"
        zones = [RoiZone(
            zone_id=zone_id,
            zone_type="tree_diagram",
            bbox=canvas_bbox,
            file_path=self._save_crop(crop, student_id, f"{zone_id}.png"),
            worksheet="WS6",
        )]
        result = LayoutResult(
            student_id=student_id, worksheet="WS6", source_image=_rel_path(path),
            page_index=page_index, status=ExtractionStatus.SUCCESS.value, zones=zones,
        )
        self._save_debug_overlay(original, zones, student_id, "WS6")
        return result

    def process_worksheet_page(
        self,
        image_path: str | Path,
        student_id: str,
        worksheet: str,
    ) -> LayoutResult:
        worksheet = worksheet.upper()
        page_index = WORKSHEETS_1_10_PAGE_INDEX.get(worksheet)
        if worksheet == "WS10":
            return self.extract_ws10_table(image_path, student_id, page_index=page_index)
        if worksheet == "WS5":
            return self.extract_ws5_tree_templates(image_path, student_id, page_index=page_index)
        if worksheet == "WS6":
            return self.extract_ws6_tree_canvas(image_path, student_id, page_index=page_index)
        return LayoutResult(
            student_id=student_id, worksheet=worksheet, source_image=str(image_path),
            status=ExtractionStatus.ERROR.value,
            message=f"No layout extractor for {worksheet}.",
        )

    def process_student_worksheet(
        self,
        student_id: str,
        worksheet: str,
        *,
        image_path: str | Path | None = None,
    ) -> LayoutResult:
        """Resolve page from project image store, run extractor, save manifest."""
        worksheet = worksheet.upper()
        path = Path(image_path) if image_path else worksheet_page_image(student_id, worksheet)
        if path is None or not path.exists():
            return LayoutResult(
                student_id=student_id, worksheet=worksheet, source_image="",
                status=ExtractionStatus.ERROR.value,
                message=f"No page image for {worksheet}. Run ocr_pipeline dry_run first.",
            )
        result = self.process_worksheet_page(path, student_id, worksheet)
        result.save(self.output_dir / student_id)
        return result

    def process_student_bundle(self, student_id: str) -> dict[str, LayoutResult]:
        """Run layout isolation for all LAYOUT_ISOLATION_WORKSHEETS."""
        results: dict[str, LayoutResult] = {}
        for ws in sorted(LAYOUT_ISOLATION_WORKSHEETS):
            results[ws] = self.process_student_worksheet(student_id, ws)
        return results

    def load_manifest(self, student_id: str, worksheet: str) -> dict[str, Any] | None:
        path = layout_manifest_path(student_id, worksheet)
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def tree_diagram_crop_path(self, student_id: str, worksheet: str = "WS6") -> Path | None:
        """Return on-disk path to tree_diagram crop for dt_vision_pipeline."""
        manifest = self.load_manifest(student_id, worksheet)
        if not manifest:
            return None
        for zone in manifest.get("zones", []):
            if zone.get("type") == "tree_diagram" and zone.get("file_path"):
                p = REPO_ROOT / zone["file_path"]
                if p.exists():
                    return p
        return None


def find_worksheet_page(student_images_dir: Path, worksheet: str) -> Path | None:
    """Legacy helper: resolve page via WORKSHEETS_1_10_PAGE_INDEX inside a slot folder."""
    ws = worksheet.upper()
    page_idx = WORKSHEETS_1_10_PAGE_INDEX.get(ws)
    if page_idx is None:
        return None
    candidate = student_images_dir / f"page_{page_idx}.jpg"
    return candidate if candidate.exists() else None
