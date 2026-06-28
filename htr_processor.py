"""
htr_processor.py — Phase 2: Handwritten Text Recognition with HTR confidence.

Transcribes cropped answer zones. Numeric/table cells use digit-focused OCR;
handwriting zones use optional TrOCR or contour heuristics.

HTR confidence < HTR_REVIEW_THRESHOLD (0.85) → review_required=True, text=(okunamiyor).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

logger = logging.getLogger(__name__)

HTR_REVIEW_THRESHOLD = 0.85
ILLEGIBLE = "(okunamiyor)"
BLANK = "(bos)"

ZoneKind = Literal["digits", "handwriting", "formula"]


@dataclass
class HtrResult:
    text: str
    confidence: float
    review_required: bool
    method: str

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "review_required": self.review_required,
            "method": self.method,
        }


def _auto_rotate_upright(image: np.ndarray) -> np.ndarray:
    """Rotate so width >= height (table rows read top-to-bottom)."""
    h, w = image.shape[:2]
    if h > w * 1.05:
        return cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    return image


def _preprocess_digit_crop(bgr: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr.ndim == 3 else bgr
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    return binary


def _ink_ratio(binary: np.ndarray) -> float:
    return float(np.count_nonzero(binary)) / max(binary.size, 1)


def _digit_templates(size: int = 32) -> dict[str, np.ndarray]:
    templates: dict[str, np.ndarray] = {}
    for d in "0123456789":
        canvas = np.zeros((size, size), dtype=np.uint8)
        cv2.putText(canvas, d, (4, size - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.9, 255, 2, cv2.LINE_AA)
        templates[d] = canvas
    return templates


_DIGIT_TEMPLATES = _digit_templates()


def _normalize_digit_roi(binary: np.ndarray) -> np.ndarray:
    coords = cv2.findNonZero(binary)
    if coords is None:
        return np.zeros((32, 32), dtype=np.uint8)
    x, y, w, h = cv2.boundingRect(coords)
    roi = binary[y : y + h, x : x + w]
    side = max(w, h, 1)
    pad = np.zeros((side, side), dtype=np.uint8)
    y0 = (side - h) // 2
    x0 = (side - w) // 2
    pad[y0 : y0 + h, x0 : x0 + w] = roi
    return cv2.resize(pad, (32, 32), interpolation=cv2.INTER_AREA)


def _template_match_digit(binary: np.ndarray) -> tuple[str, float]:
    norm = _normalize_digit_roi(binary)
    if float(np.count_nonzero(norm)) / max(norm.size, 1) < 0.02:
        return BLANK, 1.0
    best_d, best_s = ILLEGIBLE, 0.0
    for d, tmpl in _DIGIT_TEMPLATES.items():
        score = float(cv2.matchTemplate(norm, tmpl, cv2.TM_CCOEFF_NORMED).max())
        if score > best_s:
            best_s, best_d = score, d
    if best_s < 0.32:
        return ILLEGIBLE, best_s
    return best_d, min(0.95, best_s + 0.18)


def _template_match_digits_sequence(binary: np.ndarray) -> tuple[str, float]:
    """Match one or more digits in a cell (e.g. 408)."""
    coords = cv2.findNonZero(binary)
    if coords is None:
        return BLANK, 1.0
    x, y, w, h = cv2.boundingRect(coords)
    roi = binary[y : y + h, x : x + w]
    # Single blob — one template pass
    if w < h * 1.8:
        return _template_match_digit(roi)

    # Multiple digits: vertical projection split
    col_sum = roi.sum(axis=0)
    gaps = [i for i in range(1, len(col_sum) - 1) if col_sum[i] < max(2, 0.05 * col_sum.max())]
    if not gaps:
        return _template_match_digit(roi)

    splits = [0] + gaps + [w]
    digits = []
    scores = []
    for a, b in zip(splits, splits[1:]):
        if b - a < 4:
            continue
        piece = roi[:, a:b]
        d, s = _template_match_digit(piece)
        if d in "0123456789":
            digits.append(d)
            scores.append(s)
    if not digits:
        return _template_match_digit(roi)
    text = "".join(digits)
    conf = sum(scores) / len(scores)
    return text, min(0.95, conf + 0.1)


def _best_rotation_numeric(bgr: np.ndarray) -> tuple[np.ndarray, str, float]:
    rotations = [
        ("none", bgr),
        ("90cw", cv2.rotate(bgr, cv2.ROTATE_90_CLOCKWISE)),
        ("180", cv2.rotate(bgr, cv2.ROTATE_180)),
        ("90ccw", cv2.rotate(bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)),
    ]
    best_text, best_conf, best_img = ILLEGIBLE, 0.0, bgr
    for _, img in rotations:
        binary = _preprocess_digit_crop(img)
        text, conf = _template_match_digits_sequence(binary)
        if conf > best_conf and text not in {ILLEGIBLE, BLANK}:
            best_text, best_conf, best_img = text, conf, img
        elif text == BLANK and best_conf == 0.0:
            best_text, best_conf, best_img = text, conf, img
    return best_img, best_text, best_conf


def _try_pytesseract(bgr: np.ndarray, *, digits_only: bool) -> tuple[str, float] | None:
    try:
        import pytesseract
    except ImportError:
        return None
    config = "--psm 7"
    if digits_only:
        config += " -c tessedit_char_whitelist=0123456789.,"
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY) if bgr.ndim == 3 else bgr
    data = pytesseract.image_to_data(gray, config=config, output_type=pytesseract.Output.DICT)
    texts = [t.strip() for t, conf in zip(data["text"], data["conf"]) if t.strip() and int(conf) > 0]
    confs = [int(c) for c in data["conf"] if int(c) > 0]
    if not texts:
        return None
    text = " ".join(texts)
    confidence = (sum(confs) / len(confs)) / 100.0
    return text, confidence


def _try_trocr(bgr: np.ndarray) -> tuple[str, float] | None:
    try:
        from dt_vision_pipeline import TrOCRRecognizer
        from PIL import Image
    except ImportError:
        return None
    try:
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)
        rec = TrOCRRecognizer()
        text = rec.recognize(pil).strip()
        if not text:
            return None
        return text, 0.88
    except Exception as exc:
        logger.debug("TrOCR failed: %s", exc)
        return None


def _normalize_numeric(text: str) -> str:
    text = text.strip().replace(",", ".")
    text = re.sub(r"[^\d.]", "", text)
    return text


class HTRProcessor:
    """Phase 2 transcription for layout RoI crops."""

    def __init__(self, review_threshold: float = HTR_REVIEW_THRESHOLD) -> None:
        self.review_threshold = review_threshold

    def transcribe(
        self,
        image_path: str | Path,
        *,
        kind: ZoneKind = "handwriting",
    ) -> HtrResult:
        path = Path(image_path)
        bgr = cv2.imread(str(path))
        if bgr is None:
            return HtrResult(ILLEGIBLE, 0.0, True, "missing_file")

        if kind in ("digits", "formula"):
            return self.transcribe_numeric(bgr)
        return self.transcribe_handwriting(bgr)

    def transcribe_numeric(self, bgr: np.ndarray) -> HtrResult:
        for name, fn in (
            ("pytesseract", lambda: _try_pytesseract(bgr, digits_only=True)),
            ("trocr", lambda: _try_trocr(bgr)),
        ):
            out = fn()
            if out:
                text, conf = out
                text = _normalize_numeric(text) or text.strip()
                if not text:
                    continue
                review = conf < self.review_threshold
                return HtrResult(
                    ILLEGIBLE if review else text,
                    round(conf, 3),
                    review,
                    name,
                )

        _, text, conf = _best_rotation_numeric(bgr)
        if text == BLANK:
            return HtrResult(BLANK, 1.0, False, "template")
        review = conf < self.review_threshold
        return HtrResult(
            ILLEGIBLE if review else text,
            round(conf, 3),
            review,
            "template",
        )

    def transcribe_handwriting(self, bgr: np.ndarray) -> HtrResult:
        bgr = _auto_rotate_upright(bgr)
        out = _try_trocr(bgr) or _try_pytesseract(bgr, digits_only=False)
        if out:
            text, conf = out
            review = conf < self.review_threshold
            return HtrResult(
                ILLEGIBLE if review or not text.strip() else text.strip(),
                round(conf, 3),
                review,
                "trocr" if out else "pytesseract",
            )
        binary = _preprocess_digit_crop(bgr)
        if _ink_ratio(binary) < 0.01:
            return HtrResult(BLANK, 1.0, False, "empty")
        return HtrResult(ILLEGIBLE, 0.35, True, "heuristic")
