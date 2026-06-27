"""
dt_vision_pipeline.py

Two-stage end-to-end pipeline for digitizing handwritten decision-tree worksheets.

Stage 1 (Vision):   OpenCV preprocessing -> contour detection -> crop each node.
Stage 2 (Language): TrOCR recognizes raw text -> fuzzy NLP maps to schema -> JSON.

Designed for Google Colab. Install once at the top of your notebook:
    !pip install opencv-python-headless transformers torch torchvision pillow rapidfuzz

Usage (Colab):
    from dt_vision_pipeline import run_pipeline
    result = run_pipeline("student_worksheet.jpg")
    print(result.to_json(indent=2))
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from PIL import Image

# TrOCR
from transformers import TrOCRProcessor, VisionEncoderDecoderModel

# Fuzzy matching
from rapidfuzz import fuzz, process as rf_process

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants: bilingual domain vocabulary
# ---------------------------------------------------------------------------

FEATURE_VOCAB: dict[str, str] = {
    # English forms
    "energy": "Energy",
    "fat": "Fat",
    "salt": "Salt",
    "protein": "Protein",
    "saturated fat": "Saturated Fat",
    "carbohydrates": "Carbohydrates",
    "carbs": "Carbohydrates",
    "sugar": "Sugar",
    "calories": "Calories",
    "sodium": "Sodium",
    "fibre": "Fibre",
    "fiber": "Fibre",
    "price": "Price",
    "taste score": "Taste Score",
    # Turkish forms
    "enerji": "Energy",
    "yag": "Fat",
    "yağ": "Fat",
    "doymus yag": "Saturated Fat",
    "doymuş yağ": "Saturated Fat",
    "tuz": "Salt",
    "karbonhidrat": "Carbohydrates",
    "karbonidrat": "Carbohydrates",
    "seker": "Sugar",
    "şeker": "Sugar",
    "kalori": "Calories",
    "sodyum": "Sodium",
    "lif": "Fibre",
    "fiyat": "Price",
    "tat puani": "Taste Score",
    "tat puanı": "Taste Score",
    # Common OCR misreads
    "egnergy": "Energy",
    "sgr": "Sugar",
    "cal": "Calories",
    "sod": "Sodium",
    "prot": "Protein",
}

OPERATOR_MAP: dict[str, str] = {
    ">": ">",
    "<": "<",
    ">=": ">=",
    "<=": "<=",
    "=": "=",
    "=>": ">=",
    "=<": "<=",
    "büyük": ">",
    "küçük": "<",
    "buyuk": ">",
    "kucuk": "<",
}

RESULT_VOCAB: dict[str, str] = {
    "recommendable": "Recommendable",
    "not recommendable": "Not Recommendable",
    "recommended": "Recommendable",
    "not recommended": "Not Recommendable",
    "onerilir": "Recommendable",
    "önerilir": "Recommendable",
    "tavsiye edilebilir": "Recommendable",
    "tavsiye edilir": "Recommendable",
    "evet": "Recommendable",
    "onerilmez": "Not Recommendable",
    "önerilmez": "Not Recommendable",
    "tavsiye edilemez": "Not Recommendable",
    "hayir": "Not Recommendable",
    "hayır": "Not Recommendable",
}

# Canonical feature names for fuzzy matching
CANONICAL_FEATURES = list({v for v in FEATURE_VOCAB.values()})
CANONICAL_RESULTS = ["Recommendable", "Not Recommendable"]

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class BoundingBox:
    x: int
    y: int
    w: int
    h: int

    @property
    def area(self) -> int:
        return self.w * self.h

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2


@dataclass
class DetectedNode:
    box: BoundingBox
    crop: Image.Image
    raw_text: str = ""
    node_type: str = "unknown"  # "decision" | "result" | "text"


@dataclass
class SplitNode:
    feature: Optional[str]
    operator: Optional[str]
    threshold: Optional[float]
    raw_condition: str
    true_branch: Optional["SplitNode | ResultNode"] = None
    false_branch: Optional["SplitNode | ResultNode"] = None


@dataclass
class ResultNode:
    label: str  # "Recommendable" or "Not Recommendable"
    raw_text: str = ""


@dataclass
class PipelineResult:
    student_image_path: str
    nodes: list[DetectedNode] = field(default_factory=list)
    tree: Optional[SplitNode | ResultNode] = None
    warnings: list[str] = field(default_factory=list)
    raw_texts: list[str] = field(default_factory=list)

    def to_json(self, indent: int = 2) -> str:
        def _serialize(obj):
            if obj is None:
                return None
            if isinstance(obj, SplitNode):
                return {
                    "type": "split",
                    "feature": obj.feature,
                    "operator": obj.operator,
                    "threshold": obj.threshold,
                    "raw_condition": obj.raw_condition,
                    "true_branch": _serialize(obj.true_branch),
                    "false_branch": _serialize(obj.false_branch),
                }
            if isinstance(obj, ResultNode):
                return {"type": "result", "label": obj.label, "raw_text": obj.raw_text}
            return str(obj)

        return json.dumps(
            {
                "student_image": self.student_image_path,
                "tree": _serialize(self.tree),
                "raw_texts_detected": self.raw_texts,
                "warnings": self.warnings,
            },
            ensure_ascii=False,
            indent=indent,
        )


# ---------------------------------------------------------------------------
# Module 1: OpenCV Preprocessing
# ---------------------------------------------------------------------------

def preprocess_for_htr(image: np.ndarray) -> np.ndarray:
    """
    Convert a raw worksheet scan into a clean binary image for HTR.

    Pipeline:
    1. Grayscale conversion strips color noise.
    2. Gaussian blur reduces scanner grain without blurring ink strokes.
    3. Adaptive thresholding handles uneven lighting across the page.
    4. Morphological closing fills gaps in faint pencil strokes.
    5. Morphological opening removes isolated speckle noise.

    Returns a binary uint8 image (0 or 255 per pixel).
    """
    # 1. Grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 2. Gaussian blur (kernel 3x3 keeps fine strokes intact)
    blurred = cv2.GaussianBlur(gray, (3, 3), sigmaX=0)

    # 3. Adaptive thresholding
    #    Block size 31: large enough to handle shadow gradients across a page.
    #    C=10: subtract 10 from local mean so lightly inked text survives.
    binary = cv2.adaptiveThreshold(
        blurred,
        maxValue=255,
        adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        thresholdType=cv2.THRESH_BINARY_INV,
        blockSize=31,
        C=10,
    )

    # 4. Close small gaps inside letter strokes (faint pencil marks)
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_kernel, iterations=1)

    # 5. Open to remove isolated noise pixels smaller than 2x2
    open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    cleaned = cv2.morphologyEx(closed, cv2.MORPH_OPEN, open_kernel, iterations=1)

    return cleaned


def enhance_crop_for_trocr(crop: np.ndarray) -> np.ndarray:
    """
    Secondary cleanup applied to individual node crops before TrOCR.
    Dilates strokes slightly so the model sees bolder ink.
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 2))
    return cv2.dilate(crop, kernel, iterations=1)


# ---------------------------------------------------------------------------
# Module 2: Detection and Cropping
# ---------------------------------------------------------------------------

_MIN_NODE_AREA = 500          # pixels: ignore tiny noise blobs
_MAX_NODE_AREA_FRAC = 0.25   # ignore regions covering > 25% of page (whole-page false positives)
_ASPECT_RATIO_RANGE = (0.1, 15.0)  # width/height ratio bounds for valid text regions


def detect_nodes(
    binary: np.ndarray,
    original_bgr: np.ndarray,
    min_area: int = _MIN_NODE_AREA,
    max_area_frac: float = _MAX_NODE_AREA_FRAC,
) -> list[DetectedNode]:
    """
    Find all decision-tree nodes (boxes, ovals, text blobs) in the binary image.

    Strategy: external contour detection with bounding-box merging.
    Returns DetectedNode objects with PIL crops from the ORIGINAL color image
    (TrOCR performs better on color/grayscale than pure binary).
    """
    page_area = binary.shape[0] * binary.shape[1]
    max_area = int(page_area * max_area_frac)

    # binary is already THRESH_BINARY_INV: ink pixels = 255, background = 0.
    # findContours expects white objects on black, so use binary directly.
    contours, _ = cv2.findContours(
        binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    boxes: list[BoundingBox] = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        area = w * h
        if area < min_area or area > max_area:
            continue
        ratio = w / max(h, 1)
        if not (_ASPECT_RATIO_RANGE[0] <= ratio <= _ASPECT_RATIO_RANGE[1]):
            continue
        boxes.append(BoundingBox(x, y, w, h))

    merged = _merge_overlapping_boxes(boxes, padding=8)
    merged.sort(key=lambda b: (b.center[1], b.center[0]))  # top-to-bottom, left-to-right

    nodes: list[DetectedNode] = []
    for box in merged:
        x, y, w, h = box.x, box.y, box.w, box.h
        roi = original_bgr[y: y + h, x: x + w]
        if roi.size == 0:
            continue
        pil_crop = Image.fromarray(cv2.cvtColor(roi, cv2.COLOR_BGR2RGB))
        nodes.append(DetectedNode(box=box, crop=pil_crop))

    logger.info("Detected %d candidate nodes", len(nodes))
    return nodes


def _merge_overlapping_boxes(
    boxes: list[BoundingBox], padding: int = 8
) -> list[BoundingBox]:
    """
    Merge bounding boxes that overlap or touch (with padding).
    Uses a single-pass union-find approach via repeated merging until stable.
    """
    if not boxes:
        return []

    def expand(b: BoundingBox, p: int) -> tuple[int, int, int, int]:
        return b.x - p, b.y - p, b.x + b.w + p, b.y + b.h + p

    def overlaps(a: BoundingBox, b: BoundingBox) -> bool:
        ax1, ay1, ax2, ay2 = expand(a, padding)
        bx1, by1, bx2, by2 = expand(b, padding)
        return ax1 < bx2 and ax2 > bx1 and ay1 < by2 and ay2 > by1

    def merge_two(a: BoundingBox, b: BoundingBox) -> BoundingBox:
        x = min(a.x, b.x)
        y = min(a.y, b.y)
        x2 = max(a.x + a.w, b.x + b.w)
        y2 = max(a.y + a.h, b.y + b.h)
        return BoundingBox(x, y, x2 - x, y2 - y)

    changed = True
    result = list(boxes)
    while changed:
        changed = False
        merged: list[BoundingBox] = []
        used = [False] * len(result)
        for i, a in enumerate(result):
            if used[i]:
                continue
            combined = a
            for j in range(i + 1, len(result)):
                if not used[j] and overlaps(combined, result[j]):
                    combined = merge_two(combined, result[j])
                    used[j] = True
                    changed = True
            merged.append(combined)
        result = merged

    return result


# ---------------------------------------------------------------------------
# Module 3: TrOCR Recognition
# ---------------------------------------------------------------------------

class TrOCRRecognizer:
    """
    Wraps the microsoft/trocr-base-handwritten model.
    Loads once and reuses across many crops (Colab-friendly).
    """

    MODEL_ID = "microsoft/trocr-base-handwritten"

    def __init__(self, device: Optional[str] = None):
        import torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("Loading TrOCR on %s ...", self.device)
        self.processor = TrOCRProcessor.from_pretrained(self.MODEL_ID)
        self.model = VisionEncoderDecoderModel.from_pretrained(self.MODEL_ID)
        self.model.to(self.device)
        self.model.eval()
        logger.info("TrOCR ready.")

    def recognize_batch(
        self,
        crops: list[Image.Image],
        batch_size: int = 8,
    ) -> list[str]:
        """
        Run TrOCR on a list of PIL crops. Returns raw text predictions (one per crop).
        """
        import torch

        results: list[str] = []
        for start in range(0, len(crops), batch_size):
            batch = crops[start: start + batch_size]
            # TrOCR expects RGB PIL images
            rgb_batch = [img.convert("RGB") for img in batch]
            pixel_values = self.processor(
                images=rgb_batch, return_tensors="pt"
            ).pixel_values.to(self.device)

            with torch.no_grad():
                generated_ids = self.model.generate(pixel_values)

            texts = self.processor.batch_decode(
                generated_ids, skip_special_tokens=True
            )
            results.extend(texts)

        return results


def recognize_nodes(
    nodes: list[DetectedNode],
    recognizer: TrOCRRecognizer,
) -> list[DetectedNode]:
    """
    Fill node.raw_text by running TrOCR on each crop.
    Modifies nodes in-place and returns them.
    """
    crops = [n.crop for n in nodes]
    texts = recognizer.recognize_batch(crops)
    for node, text in zip(nodes, texts):
        node.raw_text = text.strip()
    return nodes


# ---------------------------------------------------------------------------
# Module 4: NLP Post-processing
# ---------------------------------------------------------------------------

def _fuzzy_match_feature(text: str, threshold: int = 72) -> Optional[str]:
    """
    Match a raw text token against canonical feature names.
    Returns canonical name if score >= threshold, else None.
    """
    text_lower = text.lower().strip()
    # Direct dict lookup first (exact or normalized)
    if text_lower in FEATURE_VOCAB:
        return FEATURE_VOCAB[text_lower]
    # Fuzzy fallback
    match = rf_process.extractOne(
        text_lower,
        list(FEATURE_VOCAB.keys()),
        scorer=fuzz.token_sort_ratio,
    )
    if match and match[1] >= threshold:
        return FEATURE_VOCAB[match[0]]
    return None


def _fuzzy_match_result(text: str, threshold: int = 72) -> Optional[str]:
    """Match raw text to Recommendable / Not Recommendable."""
    text_lower = text.lower().strip()
    if text_lower in RESULT_VOCAB:
        return RESULT_VOCAB[text_lower]
    match = rf_process.extractOne(
        text_lower,
        list(RESULT_VOCAB.keys()),
        scorer=fuzz.token_sort_ratio,
    )
    if match and match[1] >= threshold:
        return RESULT_VOCAB[match[0]]
    return None


# Matches patterns like:
#   "Fat < 8"  "Tuz > 5.0"  "Protein >= 7,5"  "Energy <= 300"
_CONDITION_RE = re.compile(
    r"(?P<feature>[A-Za-zÇçĞğİıÖöŞşÜü ]+?)"
    r"\s*(?P<op>[<>]=?|=>|=<|=)\s*"
    r"(?P<threshold>[0-9]+[,.]?[0-9]*)",
    re.UNICODE,
)


def parse_condition(raw: str) -> tuple[Optional[str], Optional[str], Optional[float]]:
    """
    Extract (feature, operator, threshold) from a raw OCR string.
    Returns (None, None, None) if the string does not look like a condition.
    """
    m = _CONDITION_RE.search(raw)
    if not m:
        return None, None, None

    feat_raw = m.group("feature").strip()
    op_raw = m.group("op").strip()
    thresh_raw = m.group("threshold").replace(",", ".")

    feature = _fuzzy_match_feature(feat_raw)
    operator = OPERATOR_MAP.get(op_raw, op_raw)
    try:
        threshold = float(thresh_raw)
    except ValueError:
        threshold = None

    return feature, operator, threshold


def classify_node_type(raw_text: str) -> str:
    """
    Heuristic: decide whether a detected text region is a split condition,
    a result label, or unclassified.
    """
    if _CONDITION_RE.search(raw_text):
        return "decision"
    if _fuzzy_match_result(raw_text) is not None:
        return "result"
    return "text"


def build_tree_from_nodes(
    nodes: list[DetectedNode],
    warnings: list[str],
) -> Optional[SplitNode | ResultNode]:
    """
    Reconstruct the decision tree from spatially-ordered DetectedNodes.

    Heuristic layout rules:
    - Nodes are already sorted top-to-bottom, left-to-right.
    - The topmost decision node is the root.
    - Each decision node's left child is its nearest result/decision node
      to the lower-left; right child to the lower-right.

    For complex trees this heuristic may be wrong. The raw_texts and
    warnings give the researcher everything needed to manually correct.
    """
    decision_nodes = [n for n in nodes if n.node_type == "decision"]
    result_nodes = [n for n in nodes if n.node_type == "result"]

    if not decision_nodes:
        warnings.append("No decision/condition nodes detected. Tree not reconstructed.")
        return None

    # Build SplitNode objects
    split_map: dict[int, SplitNode] = {}
    for i, dn in enumerate(decision_nodes):
        feature, operator, threshold = parse_condition(dn.raw_text)
        if feature is None:
            warnings.append(
                f"Node {i} raw_text={dn.raw_text!r} did not parse to a condition"
            )
        split_map[i] = SplitNode(
            feature=feature,
            operator=operator,
            threshold=threshold,
            raw_condition=dn.raw_text,
        )

    # Build ResultNode objects
    result_objs: list[ResultNode] = []
    for rn in result_nodes:
        label = _fuzzy_match_result(rn.raw_text) or rn.raw_text
        result_objs.append(ResultNode(label=label, raw_text=rn.raw_text))

    # Assign children by spatial proximity (naive: alternating left/right)
    # For a 1-level tree: root has exactly 2 result children.
    # For a 2-level tree: root has 1 result + 1 split child, etc.
    root = split_map[0]
    remaining_results = list(result_objs)
    remaining_splits = [split_map[i] for i in range(1, len(split_map))]

    def _assign_children(node: SplitNode) -> None:
        # Assign true (left/low-threshold) branch first
        if node.true_branch is None:
            if remaining_splits:
                child = remaining_splits.pop(0)
                node.true_branch = child
                _assign_children(child)
            elif remaining_results:
                node.true_branch = remaining_results.pop(0)
        if node.false_branch is None:
            if remaining_results:
                node.false_branch = remaining_results.pop(0)
            elif remaining_splits:
                child = remaining_splits.pop(0)
                node.false_branch = child
                _assign_children(child)

    _assign_children(root)

    if remaining_results:
        warnings.append(
            f"{len(remaining_results)} result node(s) could not be attached to the tree"
        )
    if remaining_splits:
        warnings.append(
            f"{len(remaining_splits)} split node(s) could not be attached to the tree"
        )

    # Warn when any split node ends up with a None branch (indicates missing nodes)
    def _collect_null_branches(node: "SplitNode | ResultNode | None", count: list) -> None:
        if node is None or isinstance(node, ResultNode):
            return
        if node.true_branch is None:
            count.append("true_branch")
        if node.false_branch is None:
            count.append("false_branch")
        _collect_null_branches(node.true_branch, count)
        _collect_null_branches(node.false_branch, count)

    null_branches: list[str] = []
    _collect_null_branches(root, null_branches)
    if null_branches:
        warnings.append(
            f"{len(null_branches)} branch(es) could not be filled — tree may be incomplete"
        )

    return root


def postprocess_nodes(
    nodes: list[DetectedNode],
    warnings: list[str],
) -> list[DetectedNode]:
    """
    Classify each node and normalize its raw text.
    Modifies nodes in-place.
    """
    for node in nodes:
        node.node_type = classify_node_type(node.raw_text)
    return nodes


# ---------------------------------------------------------------------------
# Full pipeline entry point
# ---------------------------------------------------------------------------

def run_pipeline(
    image_path: str,
    recognizer: Optional[TrOCRRecognizer] = None,
    save_debug_image: bool = False,
) -> PipelineResult:
    """
    Run the complete two-stage pipeline on a single worksheet image.

    Args:
        image_path: Path to the JPG/PNG scan.
        recognizer: Pre-loaded TrOCRRecognizer (pass one to reuse across calls).
        save_debug_image: If True, save a copy with bounding boxes drawn.

    Returns:
        PipelineResult with tree structure, raw texts, and warnings.
    """
    result = PipelineResult(student_image_path=image_path)

    # Load image
    bgr = cv2.imread(image_path)
    if bgr is None:
        result.warnings.append(f"Could not read image: {image_path}")
        return result

    # Stage 1a: preprocess
    binary = preprocess_for_htr(bgr)

    # Stage 1b: detect and crop nodes
    nodes = detect_nodes(binary, bgr)
    if not nodes:
        result.warnings.append("No nodes detected. Check image quality or thresholds.")
        return result

    # Stage 2a: recognize text with TrOCR
    if recognizer is None:
        recognizer = TrOCRRecognizer()
    nodes = recognize_nodes(nodes, recognizer)

    # Stage 2b: classify and post-process
    nodes = postprocess_nodes(nodes, result.warnings)

    result.nodes = nodes
    result.raw_texts = [n.raw_text for n in nodes]

    # Stage 2c: build tree structure
    result.tree = build_tree_from_nodes(nodes, result.warnings)

    # Optional: debug visualization
    if save_debug_image:
        _save_debug_image(bgr, nodes, image_path)

    return result


def _save_debug_image(
    bgr: np.ndarray,
    nodes: list[DetectedNode],
    source_path: str,
) -> None:
    """Draw bounding boxes and labels onto the original image for inspection."""
    COLOR = {"decision": (0, 128, 255), "result": (0, 200, 0), "text": (180, 180, 0)}
    vis = bgr.copy()
    for node in nodes:
        b = node.box
        color = COLOR.get(node.node_type, (128, 128, 128))
        cv2.rectangle(vis, (b.x, b.y), (b.x + b.w, b.y + b.h), color, 2)
        label = node.raw_text[:30]
        cv2.putText(
            vis, label, (b.x, b.y - 6),
            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA,
        )
    out = Path(source_path).with_suffix(".debug.jpg")
    cv2.imwrite(str(out), vis)
    logger.info("Debug image saved -> %s", out)


# ---------------------------------------------------------------------------
# Colab convenience wrapper
# ---------------------------------------------------------------------------

def colab_run(image_path: str, show_tree: bool = True) -> PipelineResult:
    """
    One-call entry for Colab cells.
    Loads TrOCR, runs the pipeline, prints the JSON tree.

    Example:
        result = colab_run("student_scan.jpg")
    """
    recognizer = TrOCRRecognizer()
    result = run_pipeline(image_path, recognizer=recognizer, save_debug_image=True)
    if show_tree:
        print(result.to_json(indent=2))
    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"  - {w}")
    return result


# ---------------------------------------------------------------------------
# Standalone validation (no API, no TrOCR)
# ---------------------------------------------------------------------------

def validate_pipeline_output(result: PipelineResult) -> list[str]:
    """
    Quality checks on a PipelineResult without re-running the pipeline.
    Returns a list of warning strings.

    Checks:
    1. Tree was reconstructed (not None).
    2. Root node has a recognized feature.
    3. At least one branch leads to a result node.
    4. No raw text exceeds 300 chars (TrOCR hallucination signal).
    5. At least one Recommendable and one Not Recommendable leaf.
    """
    warnings: list[str] = []

    if result.tree is None:
        warnings.append("Tree is None: pipeline failed to reconstruct any structure.")
        return warnings

    if isinstance(result.tree, SplitNode) and result.tree.feature is None:
        warnings.append(
            f"Root node feature not recognized. raw_condition={result.tree.raw_condition!r}"
        )

    long_texts = [t for t in result.raw_texts if len(t) > 300]
    if long_texts:
        warnings.append(
            f"{len(long_texts)} TrOCR output(s) exceed 300 chars (possible hallucination)"
        )

    def _collect_leaves(node) -> list[ResultNode]:
        if node is None:
            return []
        if isinstance(node, ResultNode):
            return [node]
        leaves = []
        if isinstance(node, SplitNode):
            leaves += _collect_leaves(node.true_branch)
            leaves += _collect_leaves(node.false_branch)
        return leaves

    leaves = _collect_leaves(result.tree)
    labels = {leaf.label for leaf in leaves}
    if "Recommendable" not in labels:
        warnings.append("No leaf node classified as Recommendable.")
    if "Not Recommendable" not in labels:
        warnings.append("No leaf node classified as Not Recommendable.")

    return warnings


# ---------------------------------------------------------------------------
# Entry point (direct script execution)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 2:
        print("Usage: python dt_vision_pipeline.py <image_path> [--debug]")
        sys.exit(1)

    img_path = sys.argv[1]
    debug = "--debug" in sys.argv

    rec = TrOCRRecognizer()
    res = run_pipeline(img_path, recognizer=rec, save_debug_image=debug)
    print(res.to_json(indent=2))

    issues = validate_pipeline_output(res)
    if issues:
        print("\nValidation warnings:")
        for issue in issues:
            print(f"  - {issue}")
