#!/usr/bin/env python3
"""Dynamic keyframe extraction for long-form student screen recordings (MMLA).

Four-layer pipeline per student directory:
  1. Video meta-analysis, corruption guards, adaptive 1080p-width downscale
  2. Transcript-guided speech anchors from hybrid diarization (midpoint rule)
  3. Otsu-thresholded pixel-delta motion keyframes
  4. Cooldown saturation guard + manifest bundling

Cross-modal alignment:
  --audio-root  transcript / hybrid diarization + frame output destination
  --video-root  decoupled screen-recording search (flat or per-student subdirs)

Usage:
  python scripts/dynamic_video_analytics.py Amy Helena \\
    --audio-root data_sources_2026/codap_arbor_21april_audio \\
    --video-root "data_sources_2026/21 April CODAP Arbor Screen Recordings"

  python scripts/dynamic_video_analytics.py --audio-root data_sources_2026/colab_may_audio
"""

from __future__ import annotations

import argparse
import gc
import json
import logging
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speaker_merge import build_role_mapping, get_hybrid_timeline
from transcript_quality import DEFAULT_AUDIO_ROOT, REPO_ROOT

LOGGER = logging.getLogger("dynamic_video_analytics")

DEFAULT_MAX_WIDTH = 1920
DEFAULT_MOTION_THRESHOLD = 0.005  # 0.5% of frame area
DEFAULT_COOLDOWN_MS = 1000
DEFAULT_SPEECH_GAP_BYPASS_SECONDS = 120
DEFAULT_BOUNDARY_EPSILON_S = 0.05
DEFAULT_JPEG_QUALITY = 88
DEFAULT_SINGLE_PASS = True
DEFAULT_MOTION_PREVIEW_WIDTH = 960
DEFAULT_SILENT_MOTION_THRESHOLD = 0.008
DEFAULT_SILENT_SCREEN_GAP_FILL_SECONDS = 90.0
DEFAULT_CODAP_GAP_FILL_SECONDS = 90.0
SILENT_SCREEN_TRIGGERS = frozenset({"motion_only_fallback", "silent_screen_gap_fill"})
CODAP_GAP_FILL_TRIGGERS = frozenset({"silent_screen_gap_fill", "codap_static_gap_fill"})
GAP_FILL_TRIGGERS = CODAP_GAP_FILL_TRIGGERS
EXTRACTED_DEDUP_MS = 150
DEFAULT_DEDUP_METHOD = "phash"
DEFAULT_PHASH_THRESHOLD = 4
DEFAULT_MSE_THRESHOLD = 5.0
DEFAULT_NON_TASK_TEMPLATE_DIR = REPO_ROOT / "calibration" / "non_task_screen_templates"
DEFAULT_CODAP_TASK_TEMPLATE_DIR = REPO_ROOT / "calibration" / "codap_task_templates"
DEFAULT_COLAB_TASK_TEMPLATE_DIR = REPO_ROOT / "calibration" / "colab_task_templates"
DEFAULT_NON_TASK_PHASH_THRESHOLD = 10
DEFAULT_CODAP_TASK_PHASH_THRESHOLD = 12
DEFAULT_COLAB_TASK_PHASH_THRESHOLD = 12
DEFAULT_TASK_ACTIVITY = "codap"
GAP_FILL_MIN_CONTENT_SCORE = 3
NON_TASK_HASH_SIZE = (320, 180)

TaskActivity = Literal["codap", "colab", "both"]

# Lowercase only — always compare via path.suffix.lower().
VIDEO_EXTENSIONS = (
    ".webm",
    ".mp4",
    ".mkv",
    ".mov",
    ".m4v",
    ".avi",
    ".wmv",
    ".mpeg",
    ".mpg",
)

# Exact-name candidates for tiered video resolve (student_id + suffix).
# Includes common screen-recording naming and mixed-case filesystem suffixes.
CANONICAL_VIDEO_SUFFIXES = (
    ".video.webm",
    ".video.mp4",
    ".video.mkv",
    ".video.mov",
    ".video.m4v",
    ".webm",
    ".mp4",
    ".MP4",
    ".mkv",
    ".mov",
    ".MOV",
    ".m4v",
    ".M4V",
    ".avi",
    ".AVI",
    ".wmv",
    ".WMV",
    ".mpeg",
    ".mpg",
    "_Screen_Recording.webm",
    "_Screen_Recording.mp4",
    "_Screen_Recording.MP4",
    "_Screen_Recording.mov",
    "_Screen_Recording.MOV",
    "_Screen_Recording.mkv",
    "_Screen_Recording.m4v",
    "_Screen_Recording.avi",
    "_screen_recording.webm",
    "_screen_recording.mp4",
    "_screen_recording.mov",
)

HYBRID_SUFFIXES = (
    "_hybrid_diarization.json",
    "_hybrid_diarization_segments.json",
)

MatchStrategy = Literal[
    "audio_root_exact",
    "video_root_subdir_exact",
    "video_root_subdir_fuzzy",
    "video_root_flat_exact",
    "video_root_flat_fuzzy",
    "unresolved",
]

ExtractionMode = Literal["full_multimodal", "motion_only_fallback", "speech_only"]


@dataclass
class VideoProfile:
    source_path: Path
    native_width: int
    native_height: int
    native_fps: float
    total_frames: int
    duration_seconds: float
    aspect_ratio: float
    extract_width: int
    extract_height: int
    corrupt_frame_count: int = 0
    pts_inversion_count: int = 0


@dataclass
class VideoResolutionResult:
    path: Path | None
    strategy: MatchStrategy
    searched_roots: list[str] = field(default_factory=list)
    candidate_count: int = 0

    @property
    def resolved(self) -> bool:
        return self.path is not None and self.path.is_file()


@dataclass
class ModalityAssessment:
    has_video: bool
    has_hybrid_diarization: bool
    has_transcript_segments: bool
    hybrid_segment_count: int
    transcript_segment_count: int
    extraction_mode: ExtractionMode

    @property
    def has_usable_transcript_modality(self) -> bool:
        return self.has_hybrid_diarization and self.hybrid_segment_count > 0


@dataclass
class SpeechAnchor:
    timestamp_seconds: float
    speaker_id: str
    speaker_role: str
    diarization_start: float
    diarization_end: float
    transcript_id: int | None = None
    high_value_interaction_zone: bool = False


@dataclass
class FrameRecord:
    frame_id: str
    source_timestamp_seconds: float
    extraction_trigger_reason: str
    metrics: dict[str, Any]
    file_path: str

    def to_json(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "source_timestamp_seconds": round(self.source_timestamp_seconds, 3),
            "extraction_trigger_reason": self.extraction_trigger_reason,
            "metrics": self.metrics,
            "file_path": self.file_path,
        }

    def to_segment_json(self) -> dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "source_timestamp_seconds": round(self.source_timestamp_seconds, 3),
            "extraction_trigger_reason": self.extraction_trigger_reason,
            "associated_transcript_id": self.metrics.get("associated_transcript_id"),
            "associated_speaker_role": self.metrics.get("associated_speaker_role"),
            "pixel_change_percentage": self.metrics.get("pixel_change_percentage"),
            "high_value_interaction_zone": self.metrics.get("high_value_interaction_zone"),
        }


@dataclass
class ExtractionState:
    extracted: list[FrameRecord] = field(default_factory=list)
    extracted_times: list[float] = field(default_factory=list)
    last_extract_ms: float = -1e18
    frame_counter: int = 0
    candidate_frames_seen: int = 0
    visual_dedup_skipped: int = 0
    temporal_dedup_skipped: int = 0
    non_task_skipped: int = 0

    def already_extracted_near(self, timestamp_s: float, window_ms: float = EXTRACTED_DEDUP_MS) -> bool:
        window = window_ms / 1000.0
        return any(abs(timestamp_s - t) <= window for t in self.extracted_times)

    def seconds_since_last_extracted(self, timestamp_s: float) -> float | None:
        if not self.extracted_times:
            return None
        return timestamp_s - max(self.extracted_times)

    def register(self, record: FrameRecord) -> None:
        self.extracted.append(record)
        self.extracted_times.append(record.source_timestamp_seconds)
        self.last_extract_ms = record.source_timestamp_seconds * 1000.0
        self.frame_counter += 1


class VisualDeduplicator:
    """Filter frames that are visually equivalent to the last accepted frame."""

    def __init__(
        self,
        method: Literal["phash", "mse"] = DEFAULT_DEDUP_METHOD,
        phash_threshold: int = DEFAULT_PHASH_THRESHOLD,
        mse_threshold: float = DEFAULT_MSE_THRESHOLD,
    ) -> None:
        if method not in ("phash", "mse"):
            raise ValueError(f"Unsupported dedup method: {method}")
        if phash_threshold < 0:
            raise ValueError("phash_threshold must be >= 0")
        if mse_threshold < 0:
            raise ValueError("mse_threshold must be >= 0")

        self.method = method
        self.phash_threshold = phash_threshold
        self.mse_threshold = mse_threshold
        self.last_saved_frame_hash: Any | None = None
        self.last_saved_frame_gray: np.ndarray | None = None
        self.last_distance: float | None = None

    def should_save(self, frame_bgr: np.ndarray) -> bool:
        """Return True only when ``frame_bgr`` differs from the last accepted frame."""
        if frame_bgr is None or frame_bgr.size == 0:
            self.last_distance = None
            return False

        import cv2

        if self.method == "phash":
            import imagehash
            from PIL import Image

            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            current_hash = imagehash.phash(Image.fromarray(rgb))
            del rgb

            if self.last_saved_frame_hash is None:
                self.last_saved_frame_hash = current_hash
                self.last_distance = None
                return True

            distance = float(current_hash - self.last_saved_frame_hash)
            self.last_distance = distance
            if distance > self.phash_threshold:
                self.last_saved_frame_hash = current_hash
                return True
            return False

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        if self.last_saved_frame_gray is None:
            self.last_saved_frame_gray = gray.copy()
            self.last_distance = None
            return True

        if gray.shape != self.last_saved_frame_gray.shape:
            gray = cv2.resize(
                gray,
                (self.last_saved_frame_gray.shape[1], self.last_saved_frame_gray.shape[0]),
                interpolation=cv2.INTER_AREA,
            )
        delta = gray.astype(np.float32) - self.last_saved_frame_gray.astype(np.float32)
        error = float(np.mean(delta * delta))
        del delta
        self.last_distance = error
        if error > self.mse_threshold:
            self.last_saved_frame_gray = gray.copy()
            return True
        return False

    def accept_frame(self, frame_bgr: np.ndarray) -> None:
        """Record frame as the dedup baseline without applying the similarity threshold."""
        if frame_bgr is None or frame_bgr.size == 0:
            return

        import cv2

        if self.method == "phash":
            import imagehash
            from PIL import Image

            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            self.last_saved_frame_hash = imagehash.phash(Image.fromarray(rgb))
            self.last_distance = None
            return

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        self.last_saved_frame_gray = gray.copy()
        self.last_distance = None


@dataclass
class NonTaskMatch:
    is_non_task: bool
    reason: str
    distance: float | None = None


@dataclass
class CodapTaskMatch:
    is_task: bool
    reason: str
    distance: float | None = None


@dataclass(frozen=True)
class CodapContentSignals:
    """Visual content features for CODAP/Arbor workspaces (no brightness gating)."""

    colored_ratio: float
    left_colored_ratio: float
    left_to_canvas_ratio: float
    hue_std: float
    hue_entropy: float
    axis_score: float
    tiny_blobs: int
    medium_blobs: int
    spread: float
    toolbar_edge_density: float
    left_icon_saturation: float
    bottom_taskbar_dark: float
    content_score: int
    matched_signals: tuple[str, ...]


class CodapContentAnalyzer:
    """Classify CODAP task screens from canvas structure, markers, and UI chrome."""

    MOTION_TRIGGERS = frozenset(
        {
            "motion_threshold_exceeded",
            "motion_only_fallback",
            "silent_screen_gap_fill",
            "codap_static_gap_fill",
        }
    )

    @classmethod
    def analyze(cls, frame_bgr: np.ndarray) -> CodapContentSignals:
        import cv2

        height, width = frame_bgr.shape[:2]
        full_hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        full_colored = (full_hsv[:, :, 1] > 48) & (full_hsv[:, :, 2] > 55)
        left_colored_ratio = float(np.mean(full_colored[:, : max(1, width // 8)]))

        canvas = frame_bgr[height // 8 : int(height * 0.86), width // 7 : int(width * 0.95)]
        canvas_h, canvas_w = canvas.shape[:2]
        gray = cv2.cvtColor(canvas, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(canvas, cv2.COLOR_BGR2HSV)
        saturation = hsv[:, :, 1]
        value = hsv[:, :, 2]
        hue = hsv[:, :, 0]

        colored_mask = (saturation > 48) & (value > 55)
        colored_ratio = float(np.mean(colored_mask))
        left_to_canvas_ratio = left_colored_ratio / max(colored_ratio, 1e-6)
        colored_hues = hue[colored_mask]
        if colored_hues.size > 80:
            hue_std = float(colored_hues.std())
            hue_bins = np.bincount((colored_hues // 10).astype(np.int32), minlength=18)
            probs = hue_bins[hue_bins > 0] / hue_bins.sum()
            hue_entropy = float(-np.sum(probs * np.log(probs + 1e-9)))
        else:
            hue_std = 0.0
            hue_entropy = 0.0

        edges = cv2.Canny(gray, 45, 130)
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (35, 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 35))
        axis_score = float(
            cv2.morphologyEx(edges, cv2.MORPH_OPEN, h_kernel).mean()
            + cv2.morphologyEx(edges, cv2.MORPH_OPEN, v_kernel).mean()
        ) / (2.0 * 255.0)

        marker_mask = colored_mask.astype(np.uint8) * 255
        component_count, _, stats, centroids = cv2.connectedComponentsWithStats(marker_mask, connectivity=8)
        areas = [stats[i, cv2.CC_STAT_AREA] for i in range(1, component_count)]
        tiny_blobs = sum(1 for area in areas if 4 <= area < 20)
        medium_blobs = sum(1 for area in areas if 20 <= area < 6000)

        spread = 0.0
        if centroids is not None and len(centroids) > 1:
            points = centroids[1:]
            spread = float(
                (np.std(points[:, 0]) / max(canvas_w, 1) + np.std(points[:, 1]) / max(canvas_h, 1)) / 2.0
            )

        toolbar_band = frame_bgr[: height // 10, width // 8 :]
        toolbar_edge_density = float(
            cv2.Canny(cv2.cvtColor(toolbar_band, cv2.COLOR_BGR2GRAY), 40, 120).mean()
        ) / 255.0
        left_icon_saturation = float(
            np.mean(cv2.cvtColor(frame_bgr[:, : max(1, width // 8)], cv2.COLOR_BGR2HSV)[:, :, 1] > 40)
        )
        bottom_taskbar_dark = float(
            np.mean(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)[int(height * 0.93) :, :] < 90)
        )

        matched: list[str] = []
        if colored_ratio >= 0.055:
            matched.append("data_markers")
        if tiny_blobs >= 80 or medium_blobs >= 25:
            matched.append("scatter_or_table_blobs")
        if hue_std >= 10.0 or hue_entropy >= 1.0:
            matched.append("hue_diversity")
        if axis_score >= 0.006:
            matched.append("axis_grid")
        if spread >= 0.16:
            matched.append("spatial_spread")
        if toolbar_edge_density >= 0.07:
            matched.append("codap_toolbar")

        content_score = len(matched)
        return CodapContentSignals(
            colored_ratio=colored_ratio,
            left_colored_ratio=left_colored_ratio,
            left_to_canvas_ratio=left_to_canvas_ratio,
            hue_std=hue_std,
            hue_entropy=hue_entropy,
            axis_score=axis_score,
            tiny_blobs=tiny_blobs,
            medium_blobs=medium_blobs,
            spread=spread,
            toolbar_edge_density=toolbar_edge_density,
            left_icon_saturation=left_icon_saturation,
            bottom_taskbar_dark=bottom_taskbar_dark,
            content_score=content_score,
            matched_signals=tuple(matched),
        )

    @classmethod
    def is_codap_task(cls, signals: CodapContentSignals) -> bool:
        if (
            signals.left_to_canvas_ratio < 1.0
            and signals.colored_ratio < 0.12
            and signals.left_icon_saturation < 0.22
            and signals.tiny_blobs < 200
            and signals.medium_blobs < 80
        ):
            return False
        if signals.content_score >= 4:
            return True
        if signals.colored_ratio >= 0.055 and (
            "scatter_or_table_blobs" in signals.matched_signals or "axis_grid" in signals.matched_signals
        ):
            return True
        if (
            signals.toolbar_edge_density >= 0.07
            and signals.axis_score >= 0.008
            and signals.colored_ratio >= 0.02
        ):
            return True
        return False

    @classmethod
    def is_windows_desktop(cls, signals: CodapContentSignals) -> bool:
        wallpaper_desktop = (
            signals.bottom_taskbar_dark >= 0.30
            and signals.left_to_canvas_ratio < 1.2
            and signals.left_icon_saturation < 0.22
            and signals.colored_ratio < 0.12
            and signals.tiny_blobs < 150
            and signals.medium_blobs < 80
        )
        if wallpaper_desktop:
            return True
        if cls.is_codap_task(signals):
            return False
        return (
            signals.bottom_taskbar_dark >= 0.30
            and signals.left_to_canvas_ratio < 1.2
            and signals.left_icon_saturation < 0.22
            and signals.colored_ratio < 0.12
        )

    @classmethod
    def is_google_drive_folder(cls, signals: CodapContentSignals, *, template_distance: float | None) -> bool:
        if cls.is_codap_task(signals):
            return False
        if template_distance is None or template_distance > DEFAULT_NON_TASK_PHASH_THRESHOLD:
            return False
        return signals.colored_ratio < 0.012 and signals.tiny_blobs < 12 and signals.axis_score < 0.012


def frame_phash(frame_bgr: np.ndarray, hash_size: tuple[int, int] = NON_TASK_HASH_SIZE) -> Any:
    """Compute perceptual hash on a downscaled BGR frame."""
    import cv2
    import imagehash
    from PIL import Image

    height, width = frame_bgr.shape[:2]
    if width != hash_size[0] or height != hash_size[1]:
        frame_bgr = cv2.resize(frame_bgr, hash_size, interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    return imagehash.phash(Image.fromarray(rgb))


class CodapTaskGuard:
    """Positive guard: CODAP/Arbor workspaces must never be classified as non-task."""

    def __init__(
        self,
        template_dir: Path,
        *,
        phash_threshold: int = DEFAULT_CODAP_TASK_PHASH_THRESHOLD,
        use_heuristics: bool = True,
    ) -> None:
        self.phash_threshold = phash_threshold
        self.use_heuristics = use_heuristics
        self.templates: list[tuple[str, Any]] = []
        self.last_match: CodapTaskMatch | None = None
        self._load_templates(template_dir)

    def _load_templates(self, template_dir: Path) -> None:
        if not template_dir.is_dir():
            LOGGER.warning("CODAP task template directory missing: %s", template_dir)
            return
        for path in sorted(template_dir.iterdir()):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            import cv2

            bgr = cv2.imread(str(path))
            if bgr is None:
                LOGGER.warning("Could not read CODAP task template: %s", path)
                continue
            self.templates.append((path.stem, frame_phash(bgr)))
        if self.templates:
            LOGGER.info(
                "CODAP task guard: loaded %d template(s) from %s",
                len(self.templates),
                template_dir,
            )

    @staticmethod
    def _heuristic_codap_workspace(frame_bgr: np.ndarray) -> tuple[bool, str]:
        signals = CodapContentAnalyzer.analyze(frame_bgr)
        if CodapContentAnalyzer.is_codap_task(signals) and signals.content_score >= 4:
            reason = (
                "heuristic:codap_content:"
                + ",".join(signals.matched_signals)
                + f";score={signals.content_score}"
            )
            return True, reason
        return False, "not_codap_content"

    def classify(self, frame_bgr: np.ndarray) -> CodapTaskMatch:
        if frame_bgr is None or frame_bgr.size == 0:
            return CodapTaskMatch(False, "empty_frame")

        signals = CodapContentAnalyzer.analyze(frame_bgr)
        is_content_valid = CodapContentAnalyzer.is_codap_task(signals)

        best_name: str | None = None
        best_dist = 999.0
        current = frame_phash(frame_bgr)
        for name, template_hash in self.templates:
            distance = float(current - template_hash)
            if distance < best_dist:
                best_dist = distance
                best_name = name

        template_matched = best_name is not None and best_dist <= self.phash_threshold

        if template_matched and is_content_valid:
            return CodapTaskMatch(
                True,
                f"template+content:{best_name}",
                best_dist,
            )

        if is_content_valid and signals.content_score >= 4:
            return CodapTaskMatch(
                True,
                (
                    "content_score:"
                    + ",".join(signals.matched_signals)
                    + f";score={signals.content_score}"
                ),
                best_dist if best_name else None,
            )

        if template_matched and not is_content_valid:
            return CodapTaskMatch(False, f"template_only_rejected:{best_name}", best_dist)

        return CodapTaskMatch(False, "not_codap", best_dist if best_name else None)

    def is_task_screen(self, frame_bgr: np.ndarray) -> bool:
        match = self.classify(frame_bgr)
        self.last_match = match
        return match.is_task


@dataclass(frozen=True)
class ColabContentSignals:
    top_orange_ratio: float
    top_white_ratio: float
    gray_band_score: float
    text_edge_density: float
    top_dark_ratio: float       # dark mode: fraction of header pixels with value < 60
    dark_cell_band_score: float # dark mode: fraction of rows with mean brightness 20–80
    content_score: int
    matched_signals: tuple[str, ...]


class ColabContentAnalyzer:
    """Heuristic detector for Google Colab notebook workspace frames."""

    @classmethod
    def analyze(cls, frame_bgr: np.ndarray) -> ColabContentSignals:
        import cv2

        height, width = frame_bgr.shape[:2]
        top = frame_bgr[: max(1, int(height * 0.07)), :]
        hsv_top = cv2.cvtColor(top, cv2.COLOR_BGR2HSV)
        orange = cv2.inRange(hsv_top, (8, 90, 140), (32, 255, 255))
        top_orange_ratio = float(np.count_nonzero(orange)) / orange.size
        white = cv2.inRange(hsv_top, (0, 0, 195), (180, 45, 255))
        top_white_ratio = float(np.count_nonzero(white)) / white.size

        # dark mode: header is uniformly dark (value < 60)
        top_gray = cv2.cvtColor(top, cv2.COLOR_BGR2GRAY)
        top_dark_ratio = float(np.mean(top_gray < 60))

        mid = frame_bgr[int(height * 0.08) : int(height * 0.92), int(width * 0.04) : int(width * 0.96)]
        gray = cv2.cvtColor(mid, cv2.COLOR_BGR2GRAY)
        row_mean = np.mean(gray, axis=1)

        # light mode: bright code cell rows (205–250)
        gray_band_score = float(np.mean((row_mean >= 205) & (row_mean <= 250)))
        # dark mode: dark code cell rows (20–80)
        dark_cell_band_score = float(np.mean((row_mean >= 20) & (row_mean <= 80)))

        edges = cv2.Canny(gray, 45, 140)
        text_edge_density = float(np.count_nonzero(edges)) / edges.size

        matched: list[str] = []
        if top_orange_ratio >= 0.015:
            matched.append("colab_header_orange")
        if top_white_ratio >= 0.30:
            matched.append("colab_header_white")
        if gray_band_score >= 0.06:
            matched.append("code_cell_bands")
        if text_edge_density >= 0.022:
            matched.append("editor_text_edges")
        # dark mode signals
        if top_dark_ratio >= 0.60:
            matched.append("dark_header")
        if dark_cell_band_score >= 0.15:
            matched.append("dark_code_cells")

        return ColabContentSignals(
            top_orange_ratio=top_orange_ratio,
            top_white_ratio=top_white_ratio,
            gray_band_score=gray_band_score,
            text_edge_density=text_edge_density,
            top_dark_ratio=top_dark_ratio,
            dark_cell_band_score=dark_cell_band_score,
            content_score=len(matched),
            matched_signals=tuple(matched),
        )

    @classmethod
    def is_colab_task(cls, signals: ColabContentSignals) -> bool:
        # light mode paths
        if signals.content_score >= 3:
            return True
        if signals.top_orange_ratio >= 0.012 and signals.gray_band_score >= 0.045:
            return True
        if signals.top_white_ratio >= 0.35 and signals.text_edge_density >= 0.028:
            return True
        # dark mode path: dark header + text edges (sufficient for identification)
        if signals.top_dark_ratio >= 0.60 and signals.text_edge_density >= 0.022:
            return True
        # dark mode path: dark cells + text edges
        if signals.dark_cell_band_score >= 0.15 and signals.text_edge_density >= 0.022:
            return True
        return False


class ColabTaskGuard:
    """Positive guard for Google Colab Python notebook workspaces."""

    def __init__(
        self,
        template_dir: Path,
        *,
        phash_threshold: int = DEFAULT_COLAB_TASK_PHASH_THRESHOLD,
        use_heuristics: bool = True,
    ) -> None:
        self.phash_threshold = phash_threshold
        self.use_heuristics = use_heuristics
        self.templates: list[tuple[str, Any]] = []
        self.last_match: CodapTaskMatch | None = None
        self._load_templates(template_dir)

    def _load_templates(self, template_dir: Path) -> None:
        if not template_dir.is_dir():
            LOGGER.warning("Colab task template directory missing: %s", template_dir)
            return
        for path in sorted(template_dir.iterdir()):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            import cv2

            bgr = cv2.imread(str(path))
            if bgr is None:
                continue
            self.templates.append((path.stem, frame_phash(bgr)))
        if self.templates:
            LOGGER.info(
                "Colab task guard: loaded %d template(s) from %s",
                len(self.templates),
                template_dir,
            )

    def classify(self, frame_bgr: np.ndarray) -> CodapTaskMatch:
        if frame_bgr is None or frame_bgr.size == 0:
            return CodapTaskMatch(False, "empty_frame")

        signals = ColabContentAnalyzer.analyze(frame_bgr)
        is_content_valid = ColabContentAnalyzer.is_colab_task(signals)

        best_name: str | None = None
        best_dist = 999.0
        current = frame_phash(frame_bgr)
        for name, template_hash in self.templates:
            distance = float(current - template_hash)
            if distance < best_dist:
                best_dist = distance
                best_name = name

        template_matched = best_name is not None and best_dist <= self.phash_threshold
        if template_matched and is_content_valid:
            return CodapTaskMatch(True, f"colab_template+content:{best_name}", best_dist)
        if is_content_valid and signals.content_score >= 3:
            return CodapTaskMatch(
                True,
                "colab_content:" + ",".join(signals.matched_signals) + f";score={signals.content_score}",
                best_dist if best_name else None,
            )
        if template_matched:
            return CodapTaskMatch(False, f"colab_template_only_rejected:{best_name}", best_dist)
        return CodapTaskMatch(False, "not_colab", best_dist if best_name else None)

    def is_task_screen(self, frame_bgr: np.ndarray) -> bool:
        match = self.classify(frame_bgr)
        self.last_match = match
        return match.is_task


@dataclass
class TaskScreenGuard:
    """Route positive task classification to CODAP and/or Colab guards."""

    activity: TaskActivity
    codap_guard: CodapTaskGuard
    colab_guard: ColabTaskGuard | None = None
    last_match: CodapTaskMatch | None = None

    def classify(self, frame_bgr: np.ndarray) -> CodapTaskMatch:
        if self.activity == "colab" and self.colab_guard is not None:
            match = self.colab_guard.classify(frame_bgr)
            self.last_match = match
            return match
        if self.activity in ("codap", "both"):
            match = self.codap_guard.classify(frame_bgr)
            if match.is_task:
                self.last_match = match
                return match
        if self.activity == "both" and self.colab_guard is not None:
            match = self.colab_guard.classify(frame_bgr)
            self.last_match = match
            return match
        self.last_match = CodapTaskMatch(False, "not_task")
        return self.last_match

    def is_task_screen(self, frame_bgr: np.ndarray) -> bool:
        return self.classify(frame_bgr).is_task


def build_task_screen_guard(
    task_activity: TaskActivity,
    *,
    codap_template_dir: Path = DEFAULT_CODAP_TASK_TEMPLATE_DIR,
    colab_template_dir: Path = DEFAULT_COLAB_TASK_TEMPLATE_DIR,
    codap_phash_threshold: int = DEFAULT_CODAP_TASK_PHASH_THRESHOLD,
    colab_phash_threshold: int = DEFAULT_COLAB_TASK_PHASH_THRESHOLD,
    use_heuristics: bool = True,
) -> TaskScreenGuard | None:
    if task_activity == "codap":
        return TaskScreenGuard(
            "codap",
            CodapTaskGuard(
                codap_template_dir,
                phash_threshold=codap_phash_threshold,
                use_heuristics=use_heuristics,
            ),
            None,
        )
    if task_activity == "colab":
        return TaskScreenGuard(
            "colab",
            CodapTaskGuard(
                codap_template_dir,
                phash_threshold=codap_phash_threshold,
                use_heuristics=use_heuristics,
            ),
            ColabTaskGuard(
                colab_template_dir,
                phash_threshold=colab_phash_threshold,
                use_heuristics=use_heuristics,
            ),
        )
    return TaskScreenGuard(
        "both",
        CodapTaskGuard(
            codap_template_dir,
            phash_threshold=codap_phash_threshold,
            use_heuristics=use_heuristics,
        ),
        ColabTaskGuard(
            colab_template_dir,
            phash_threshold=colab_phash_threshold,
            use_heuristics=use_heuristics,
        ),
    )


def task_activity_from_params(params: dict) -> TaskActivity:
    activity = params.get("task_activity", "codap")
    if activity in ("codap", "colab", "both"):
        return activity
    return "codap"


def gap_fill_content_accepts(frame_bgr: np.ndarray, task_activity: TaskActivity) -> bool:
    """Allow gap-fill when task heuristics pass at slightly lower threshold."""
    if task_activity in ("codap", "both"):
        codap_signals = CodapContentAnalyzer.analyze(frame_bgr)
        if (
            CodapContentAnalyzer.is_codap_task(codap_signals)
            and codap_signals.content_score >= GAP_FILL_MIN_CONTENT_SCORE
            and not CodapContentAnalyzer.is_windows_desktop(codap_signals)
        ):
            return True
    if task_activity in ("colab", "both"):
        colab_signals = ColabContentAnalyzer.analyze(frame_bgr)
        if ColabContentAnalyzer.is_colab_task(colab_signals) and colab_signals.content_score >= GAP_FILL_MIN_CONTENT_SCORE:
            return True
    return False


def frame_kept_by_pipeline_guard(
    frame_bgr: np.ndarray,
    *,
    filt: "NonTaskScreenFilter | None",
    task_guard: TaskScreenGuard | CodapTaskGuard | None,
    trigger_reason: str,
    task_activity: TaskActivity,
) -> bool:
    """Mirror save_keyframe accept/reject rules for prune and quality-gate checks."""
    relaxed_gap_fill = (
        trigger_reason in GAP_FILL_TRIGGERS
        and gap_fill_content_accepts(frame_bgr, task_activity)
    )

    if filt is not None:
        if filt.should_skip(frame_bgr, trigger_reason=trigger_reason):
            if not relaxed_gap_fill:
                return False
            if filt.classify_non_task(frame_bgr).is_non_task:
                return False

    if task_guard is not None:
        if task_guard.classify(frame_bgr).is_task:
            return True
        if relaxed_gap_fill:
            return True
        return False

    return True


class NonTaskScreenFilter:
    """Skip frames dominated by WhatsApp, RecordFlow, Google Drive, desktop, or other non-CODAP UIs."""

    def __init__(
        self,
        template_dir: Path,
        *,
        task_guard: TaskScreenGuard | CodapTaskGuard | None = None,
        codap_guard: CodapTaskGuard | None = None,
        phash_threshold: int = DEFAULT_NON_TASK_PHASH_THRESHOLD,
        use_heuristics: bool = True,
        require_codap_content: bool = True,
        policy: Literal["skip", "attenuate"] = "skip",
        attenuate_phash_threshold: int = 2,
    ) -> None:
        self.phash_threshold = phash_threshold
        self.use_heuristics = use_heuristics
        self.require_codap_content = require_codap_content
        self.policy = policy
        self.attenuate_phash_threshold = attenuate_phash_threshold
        if task_guard is not None:
            self.task_guard: TaskScreenGuard | CodapTaskGuard | None = task_guard
        elif codap_guard is not None:
            self.task_guard = TaskScreenGuard("codap", codap_guard, None)
        else:
            self.task_guard = None
        self.templates: list[tuple[str, Any]] = []
        self.last_match: NonTaskMatch | None = None
        self._load_templates(template_dir)

    @property
    def codap_guard(self) -> CodapTaskGuard | None:
        if isinstance(self.task_guard, TaskScreenGuard):
            return self.task_guard.codap_guard
        if isinstance(self.task_guard, CodapTaskGuard):
            return self.task_guard
        return None

    @property
    def task_activity(self) -> TaskActivity:
        if isinstance(self.task_guard, TaskScreenGuard):
            return self.task_guard.activity
        return "codap"

    def _load_templates(self, template_dir: Path) -> None:
        if not template_dir.is_dir():
            LOGGER.warning("Non-task template directory missing: %s", template_dir)
            return
        for path in sorted(template_dir.iterdir()):
            if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                continue
            try:
                import cv2

                bgr = cv2.imread(str(path))
                if bgr is None:
                    LOGGER.warning("Could not read non-task template: %s", path)
                    continue
                self.templates.append((path.stem, frame_phash(bgr)))
            except Exception as exc:
                LOGGER.warning("Failed to load non-task template %s: %s", path.name, exc)
        if self.templates:
            LOGGER.info(
                "Non-task filter: loaded %d template(s) from %s",
                len(self.templates),
                template_dir,
            )

    @staticmethod
    def _heuristic_whatsapp_web(frame_bgr: np.ndarray) -> bool:
        import cv2

        height, width = frame_bgr.shape[:2]
        left = frame_bgr[:, : max(1, width // 4)]
        hsv = cv2.cvtColor(left, cv2.COLOR_BGR2HSV)
        # WhatsApp Web sidebar green/teal in dark mode.
        mask = cv2.inRange(hsv, (35, 35, 25), (95, 255, 170))
        green_ratio = float(np.count_nonzero(mask)) / mask.size
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        return green_ratio >= 0.08 and float(np.mean(gray)) < 115.0

    @staticmethod
    def _heuristic_recordflow(frame_bgr: np.ndarray) -> bool:
        import cv2

        height, width = frame_bgr.shape[:2]
        top = frame_bgr[: max(1, height // 8), :]
        center = frame_bgr[height // 4 : 3 * height // 4, width // 4 : 3 * width // 4]
        top_gray = cv2.cvtColor(top, cv2.COLOR_BGR2GRAY)
        center_gray = cv2.cvtColor(center, cv2.COLOR_BGR2GRAY)
        top_bright_ratio = float(np.mean(top_gray > 175))
        center_dark_ratio = float(np.mean(center_gray < 95))
        # RecordFlow uses a dark canvas with bright browser chrome and a central card.
        return top_bright_ratio >= 0.04 and center_dark_ratio >= 0.45

    @staticmethod
    def _heuristic_windows_desktop(frame_bgr: np.ndarray) -> bool:
        """Detect Windows desktop views from taskbar/icons and absent CODAP canvas content."""
        signals = CodapContentAnalyzer.analyze(frame_bgr)
        return CodapContentAnalyzer.is_windows_desktop(signals)

    def classify_non_task(self, frame_bgr: np.ndarray) -> NonTaskMatch:
        if frame_bgr is None or frame_bgr.size == 0:
            return NonTaskMatch(False, "empty_frame")

        signals = CodapContentAnalyzer.analyze(frame_bgr)
        current = frame_phash(frame_bgr)
        best_name: str | None = None
        best_dist = 999.0
        drive_template_distance: float | None = None
        for name, template_hash in self.templates:
            distance = float(current - template_hash)
            if name == "google_drive_folder":
                drive_template_distance = distance
            if distance < best_dist:
                best_dist = distance
                best_name = name

        if best_name is not None and best_dist <= self.phash_threshold:
            if best_name == "google_drive_folder" and not CodapContentAnalyzer.is_google_drive_folder(
                signals,
                template_distance=drive_template_distance,
            ):
                pass
            else:
                return NonTaskMatch(True, f"template:{best_name}", best_dist)

        if self.use_heuristics:
            if self._heuristic_whatsapp_web(frame_bgr):
                return NonTaskMatch(True, "heuristic:whatsapp_web", best_dist if best_name else None)
            if self._heuristic_recordflow(frame_bgr):
                return NonTaskMatch(True, "heuristic:recordflow", best_dist if best_name else None)
            if CodapContentAnalyzer.is_google_drive_folder(
                signals,
                template_distance=drive_template_distance,
            ):
                return NonTaskMatch(True, "heuristic:google_drive_content", drive_template_distance)
            if self._heuristic_windows_desktop(frame_bgr):
                return NonTaskMatch(True, "heuristic:windows_desktop", best_dist if best_name else None)

        return NonTaskMatch(False, "task_screen", best_dist if best_name else None)

    def classify(self, frame_bgr: np.ndarray) -> NonTaskMatch:
        if frame_bgr is None or frame_bgr.size == 0:
            return NonTaskMatch(False, "empty_frame")

        if self.task_guard is not None and self.task_guard.is_task_screen(frame_bgr):
            task_match = self.task_guard.last_match
            return NonTaskMatch(
                False,
                f"task_screen_guard:{task_match.reason if task_match else 'unknown'}",
                task_match.distance if task_match else None,
            )

        return self.classify_non_task(frame_bgr)

    def classify_without_guard(self, frame_bgr: np.ndarray) -> NonTaskMatch:
        """Classify without CODAP allowlist — used only in tests/diagnostics."""
        return self.classify_non_task(frame_bgr)

    def should_skip(self, frame_bgr: np.ndarray, *, trigger_reason: str | None = None) -> bool:
        match = self.classify(frame_bgr)
        if (
            not match.is_non_task
            and self.require_codap_content
            and not match.reason.startswith("task_screen_guard")
            and not match.reason.startswith("codap_task_guard")
        ):
            match = NonTaskMatch(True, "missing_codap_content", match.distance)
        self.last_match = match
        if not match.is_non_task:
            return False
        if self.policy == "skip":
            return True
        return match.reason.startswith("template:") and (
            match.distance is not None and match.distance <= self.attenuate_phash_threshold
        )


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Expected a boolean value, got {value!r}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Dynamic keyframe extraction with cross-root video/transcript alignment.",
    )
    p.add_argument("students", nargs="*", help="Student IDs (default: all dirs under --audio-root)")
    p.add_argument(
        "--audio-root",
        type=Path,
        default=DEFAULT_AUDIO_ROOT,
        help="Transcript/hybrid root and frame output destination",
    )
    p.add_argument(
        "--video-root",
        type=Path,
        default=None,
        help="Decoupled screen-recording search root (flat or per-student subdirs)",
    )
    p.add_argument("--max-width", type=int, default=DEFAULT_MAX_WIDTH)
    p.add_argument("--motion-threshold", type=float, default=DEFAULT_MOTION_THRESHOLD)
    p.add_argument("--cooldown-ms", type=int, default=DEFAULT_COOLDOWN_MS)
    p.add_argument("--boundary-epsilon", type=float, default=DEFAULT_BOUNDARY_EPSILON_S)
    p.add_argument("--jpeg-quality", type=int, default=DEFAULT_JPEG_QUALITY)
    p.add_argument("--max-frames", type=int, default=0, help="Safety cap (0 = unlimited)")
    p.add_argument("--speech-only", action="store_true", help="Skip motion scan; extract speech anchors only")
    p.add_argument("--dry-run", action="store_true", help="Plan extractions without writing JPEGs")
    p.add_argument(
        "--enable-dedup",
        type=parse_bool,
        nargs="?",
        const=True,
        default=True,
        metavar="BOOL",
        help="Enable visual deduplication (default: true; accepts true/false)",
    )
    p.add_argument(
        "--dedup-method",
        choices=("phash", "mse"),
        default=DEFAULT_DEDUP_METHOD,
        help="Visual similarity method (default: phash)",
    )
    p.add_argument(
        "--phash-threshold",
        type=int,
        default=DEFAULT_PHASH_THRESHOLD,
        help="Maximum pHash Hamming distance treated as duplicate (default: 4)",
    )
    p.add_argument(
        "--mse-threshold",
        type=float,
        default=DEFAULT_MSE_THRESHOLD,
        help="Maximum grayscale MSE treated as duplicate (default: 5.0)",
    )
    p.add_argument(
        "--filter-non-task-screens",
        type=parse_bool,
        nargs="?",
        const=True,
        default=True,
        metavar="BOOL",
        help="Skip WhatsApp / RecordFlow / Google Drive / desktop / non-CODAP frames (default: true)",
    )
    p.add_argument(
        "--non-task-templates",
        type=Path,
        default=DEFAULT_NON_TASK_TEMPLATE_DIR,
        help="Directory of reference screenshots for non-task UI filtering",
    )
    p.add_argument(
        "--enable-codap-task-guard",
        type=parse_bool,
        nargs="?",
        const=True,
        default=True,
        metavar="BOOL",
        help="Always keep CODAP/Arbor task screens even if they resemble Drive/desktop (default: true)",
    )
    p.add_argument(
        "--codap-task-templates",
        type=Path,
        default=DEFAULT_CODAP_TASK_TEMPLATE_DIR,
        help="Directory of positive CODAP task screenshots for allowlist guard",
    )
    p.add_argument(
        "--colab-task-templates",
        type=Path,
        default=DEFAULT_COLAB_TASK_TEMPLATE_DIR,
        help="Directory of positive Colab notebook screenshots for May cohort guard",
    )
    p.add_argument(
        "--task-activity",
        choices=("codap", "colab", "both"),
        default=DEFAULT_TASK_ACTIVITY,
        help="Task screen type: codap (April), colab (May Python), or both",
    )
    p.add_argument(
        "--codap-task-phash-threshold",
        type=int,
        default=DEFAULT_CODAP_TASK_PHASH_THRESHOLD,
        help="pHash distance for CODAP task template allowlist (default: 12)",
    )
    p.add_argument(
        "--speech-gap-bypass-seconds",
        type=float,
        default=DEFAULT_SPEECH_GAP_BYPASS_SECONDS,
        help="Bypass visual dedup on speech anchors after this many seconds without a saved frame (default: 120)",
    )
    p.add_argument(
        "--codap-task-heuristics",
        type=parse_bool,
        nargs="?",
        const=True,
        default=True,
        metavar="BOOL",
        help="Enable CODAP workspace heuristics in task guard (default: true)",
    )
    p.add_argument(
        "--require-codap-content",
        type=parse_bool,
        nargs="?",
        const=True,
        default=True,
        metavar="BOOL",
        help="Keyframes must show CODAP canvas content (speech + motion; default: true)",
    )
    p.add_argument(
        "--non-task-phash-threshold",
        type=int,
        default=DEFAULT_NON_TASK_PHASH_THRESHOLD,
        help="pHash distance for template match as non-task screen (default: 10)",
    )
    p.add_argument(
        "--non-task-policy",
        choices=("skip", "attenuate"),
        default="skip",
        help="skip=drop frame entirely; attenuate=only hard-skip strong matches, tighten dedup otherwise",
    )
    p.add_argument(
        "--non-task-heuristics",
        type=parse_bool,
        nargs="?",
        const=True,
        default=True,
        metavar="BOOL",
        help="Enable lightweight WhatsApp/RecordFlow/desktop heuristics (default: true)",
    )
    p.add_argument(
        "--compute-type",
        default="int8",
        choices=("int8", "float32"),
        help="M4 unified-memory backend: int8 keeps OpenCV/NumPy paths in low-precision uint8 space",
    )
    p.add_argument(
        "--single-pass",
        type=parse_bool,
        nargs="?",
        const=True,
        default=DEFAULT_SINGLE_PASS,
        metavar="BOOL",
        help="Speech anchors + motion in one video decode pass (default: true; same output quality)",
    )
    p.add_argument(
        "--motion-preview-width",
        type=int,
        default=DEFAULT_MOTION_PREVIEW_WIDTH,
        help="Width for motion-change detection only; saved JPEGs stay at --max-width (default: 960, 0=full)",
    )
    p.add_argument(
        "--silent-motion-threshold",
        type=float,
        default=DEFAULT_SILENT_MOTION_THRESHOLD,
        help="Lower motion threshold for silent screen recordings (default: 0.008)",
    )
    p.add_argument(
        "--silent-screen-gap-fill-seconds",
        type=float,
        default=DEFAULT_SILENT_SCREEN_GAP_FILL_SECONDS,
        help="On CODAP task screens without audio, save a frame after this gap (default: 100)",
    )
    p.add_argument(
        "--codap-gap-fill-seconds",
        type=float,
        default=DEFAULT_CODAP_GAP_FILL_SECONDS,
        help="On static CODAP screens (all students), save after this gap (default: 100)",
    )
    p.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip students that already have a valid video_extraction_manifest.json",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def manifest_is_complete(manifest_path: Path) -> bool:
    if not manifest_path.is_file():
        return False
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if payload.get("status") == "skipped":
        return False
    frames = payload.get("frames") or []
    if not frames:
        return False
    sample = frames[0]
    for key in ("frame_id", "source_timestamp_seconds", "extraction_trigger_reason", "file_path"):
        if key not in sample or sample[key] in (None, ""):
            return False
    return True


def configure_compute_backend(compute_type: str) -> None:
    """Tune OpenCV/BLAS threading for Apple Silicon unified memory."""
    import os

    thread_cap = str(min(8, os.cpu_count() or 4))
    os.environ.setdefault("OMP_NUM_THREADS", thread_cap)
    os.environ.setdefault("OPENBLAS_NUM_THREADS", thread_cap)
    os.environ.setdefault("VECLIB_MAXIMUM_THREADS", thread_cap)
    os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")
    os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "loglevel;error")
    try:
        import cv2

        cv2.setUseOptimized(True)
        cv2.setNumThreads(int(thread_cap))
    except ImportError:
        pass
    LOGGER.info("Compute backend: %s (OpenCV optimized, BLAS threads=%s)", compute_type, thread_cap)


def repo_relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(resolved)


def _is_video_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS


def _canonical_video_names(student_id: str) -> list[str]:
    names: list[str] = []
    for suffix in CANONICAL_VIDEO_SUFFIXES:
        names.append(f"{student_id}{suffix}")
    return names


def _fuzzy_video_match_score(path: Path, student_id: str) -> int:
    """Return match score (0 = no match). Higher is better."""
    if not _is_video_file(path):
        return 0

    stem = path.stem.lower()
    sid = student_id.lower()
    if not sid:
        return 0

    if stem == sid:
        return 100

    if stem.startswith(f"{sid}.") or stem.startswith(f"{sid}_") or stem.startswith(f"{sid}-"):
        return 90

    if stem.startswith(sid):
        remainder = stem[len(sid) :]
        if not remainder or remainder[0] in "._-":
            return 85

    index = stem.find(sid)
    if index >= 0:
        before_ok = index == 0 or not stem[index - 1].isalnum()
        after_index = index + len(sid)
        after_ok = after_index == len(stem) or not stem[after_index].isalnum()
        if before_ok and after_ok:
            return 50

    return 0


def _find_exact_in_directory(directory: Path, student_id: str) -> Path | None:
    """Exact / case-insensitive match of known student video filenames."""
    if not directory.is_dir():
        return None
    for name in _canonical_video_names(student_id):
        candidate = directory / name
        if candidate.is_file():
            return candidate

    # Case-insensitive fallback for mixed-case suffixes (.MP4 / .MOV).
    wanted = {n.lower() for n in _canonical_video_names(student_id)}
    case_hits = [
        p for p in directory.iterdir()
        if p.is_file() and p.name.lower() in wanted
    ]
    if case_hits:
        return sorted(case_hits, key=lambda p: p.name.lower())[0]

    # Numbered screen recordings: Student_Screen_Recording1.mp4
    sid = student_id.lower()
    numbered: list[Path] = []
    for path in directory.iterdir():
        if not path.is_file() or path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        stem_l = path.stem.lower()
        if (
            stem_l.startswith(f"{sid}_screen_recording")
            or stem_l.startswith(f"{sid}.screen_recording")
            or stem_l.startswith(f"{sid}-screen-recording")
        ):
            numbered.append(path)
    if numbered:
        return sorted(numbered, key=lambda p: p.name.lower())[0]
    return None


def _find_fuzzy_in_directory(directory: Path, student_id: str) -> tuple[Path | None, int]:
    if not directory.is_dir():
        return None, 0

    best_path: Path | None = None
    best_score = 0
    candidate_count = 0

    for path in directory.iterdir():
        if not _is_video_file(path):
            continue
        score = _fuzzy_video_match_score(path, student_id)
        if score <= 0:
            continue
        candidate_count += 1
        if score > best_score:
            best_score = score
            best_path = path
        elif score == best_score and best_path is not None:
            # Prefer earlier part / shorter name when scores tie
            if path.name.lower() < best_path.name.lower():
                best_path = path

    return best_path, candidate_count


def resolve_video_path_tiered(
    student_dir: Path,
    student_id: str,
    video_root: Path | None,
) -> VideoResolutionResult:
    """3-tier cross-root resolution: audio co-location → video subdir → flat fuzzy."""
    searched: list[str] = []
    candidate_count = 0

    searched.append(repo_relative(student_dir))
    exact_audio = _find_exact_in_directory(student_dir, student_id)
    if exact_audio is not None:
        return VideoResolutionResult(
            path=exact_audio.resolve(),
            strategy="audio_root_exact",
            searched_roots=searched,
            candidate_count=1,
        )

    if video_root is None:
        return VideoResolutionResult(
            path=None,
            strategy="unresolved",
            searched_roots=searched,
            candidate_count=0,
        )

    video_root = video_root.resolve()
    searched.append(repo_relative(video_root))

    student_video_subdir = video_root / student_id
    if student_video_subdir.is_dir():
        searched.append(repo_relative(student_video_subdir))
        exact_subdir = _find_exact_in_directory(student_video_subdir, student_id)
        if exact_subdir is not None:
            return VideoResolutionResult(
                path=exact_subdir.resolve(),
                strategy="video_root_subdir_exact",
                searched_roots=searched,
                candidate_count=1,
            )

        fuzzy_subdir, sub_count = _find_fuzzy_in_directory(student_video_subdir, student_id)
        candidate_count += sub_count
        if fuzzy_subdir is not None:
            return VideoResolutionResult(
                path=fuzzy_subdir.resolve(),
                strategy="video_root_subdir_fuzzy",
                searched_roots=searched,
                candidate_count=candidate_count,
            )

    exact_flat = _find_exact_in_directory(video_root, student_id)
    if exact_flat is not None:
        return VideoResolutionResult(
            path=exact_flat.resolve(),
            strategy="video_root_flat_exact",
            searched_roots=searched,
            candidate_count=candidate_count + 1,
        )

    fuzzy_flat, flat_count = _find_fuzzy_in_directory(video_root, student_id)
    candidate_count += flat_count
    if fuzzy_flat is not None:
        return VideoResolutionResult(
            path=fuzzy_flat.resolve(),
            strategy="video_root_flat_fuzzy",
            searched_roots=searched,
            candidate_count=candidate_count,
        )

    return VideoResolutionResult(
        path=None,
        strategy="unresolved",
        searched_roots=searched,
        candidate_count=candidate_count,
    )


def resolve_hybrid_path(student_dir: Path, student_id: str) -> Path | None:
    for suffix in HYBRID_SUFFIXES:
        path = student_dir / f"{student_id}{suffix}"
        if path.is_file():
            return path
    return None


def load_labeled_transcript(student_dir: Path, student_id: str) -> list[dict]:
    labeled = student_dir / f"{student_id}_transcript_labeled.json"
    if labeled.is_file():
        payload = json.loads(labeled.read_text(encoding="utf-8"))
        return payload.get("segments") or []
    transcript = student_dir / f"{student_id}_transcript.json"
    if transcript.is_file():
        payload = json.loads(transcript.read_text(encoding="utf-8"))
        return payload.get("segments") or []
    return []


def count_hybrid_segments(student_dir: Path, student_id: str) -> int:
    hybrid_path = resolve_hybrid_path(student_dir, student_id)
    if not hybrid_path:
        return 0
    hybrid = json.loads(hybrid_path.read_text(encoding="utf-8"))
    if hybrid.get("status") == "no_speech":
        return 0
    timeline = get_hybrid_timeline(hybrid)
    return len(timeline)


def is_silent_screen_recording(student_dir: Path, student_id: str) -> bool:
    """True when audio was not captured but screen recording may still show CODAP work."""
    hybrid_path = resolve_hybrid_path(student_dir, student_id)
    if not hybrid_path:
        return False
    hybrid = json.loads(hybrid_path.read_text(encoding="utf-8"))
    if hybrid.get("speech_status") == "silent_recording":
        return True
    if hybrid.get("status") == "no_speech":
        return True
    return count_hybrid_segments(student_dir, student_id) == 0


def assess_modalities(
    student_dir: Path,
    student_id: str,
    video_resolution: VideoResolutionResult,
    *,
    speech_only: bool,
) -> ModalityAssessment:
    transcript_segments = load_labeled_transcript(student_dir, student_id)
    hybrid_segment_count = count_hybrid_segments(student_dir, student_id)
    has_hybrid = hybrid_segment_count > 0 or resolve_hybrid_path(student_dir, student_id) is not None
    has_transcript_segments = len(transcript_segments) > 0
    has_usable = has_hybrid and hybrid_segment_count > 0

    if speech_only and has_usable:
        mode: ExtractionMode = "speech_only"
    elif has_usable:
        mode = "full_multimodal"
    else:
        mode = "motion_only_fallback"

    return ModalityAssessment(
        has_video=video_resolution.resolved,
        has_hybrid_diarization=has_hybrid,
        has_transcript_segments=has_transcript_segments,
        hybrid_segment_count=hybrid_segment_count,
        transcript_segment_count=len(transcript_segments),
        extraction_mode=mode,
    )


def ffprobe_video_meta(path: Path) -> dict[str, float | int]:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=width,height,r_frame_rate,avg_frame_rate,nb_frames,duration",
        "-show_entries",
        "format=duration",
        "-select_streams",
        "v:0",
        "-of",
        "json",
        str(path),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        payload = json.loads(proc.stdout)
        streams = payload.get("streams") or []
        stream = streams[0] if streams else {}
        fmt = payload.get("format") or {}

        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
        fps = _parse_fps(stream.get("avg_frame_rate") or stream.get("r_frame_rate", "0/1"))
        if fps <= 0 or fps > 120:
            fps = 0.0

        duration = float(stream.get("duration") or fmt.get("duration") or 0.0)
        nb_frames = int(stream.get("nb_frames") or 0)
        if nb_frames <= 0 and duration > 0 and fps > 0:
            nb_frames = int(duration * fps)

        return {
            "width": width,
            "height": height,
            "fps": fps,
            "nb_frames": nb_frames,
            "duration": duration,
        }
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError):
        return {}


def _parse_fps(rate: str) -> float:
    if "/" in rate:
        num, den = rate.split("/", 1)
        den_f = float(den)
        return float(num) / den_f if den_f else 0.0
    return float(rate)


def compute_extract_dimensions(native_w: int, native_h: int, max_width: int) -> tuple[int, int]:
    if native_w <= 0 or native_h <= 0:
        return native_w, native_h
    if native_w <= max_width:
        return native_w, native_h
    scale = max_width / native_w
    extract_w = max_width
    extract_h = max(1, int(round(native_h * scale)))
    return extract_w, extract_h


def profile_video(path: Path, max_width: int) -> VideoProfile:
    import cv2

    meta = ffprobe_video_meta(path)
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV cannot open video: {path}")

    native_w = int(meta.get("width") or cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    native_h = int(meta.get("height") or cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    fps = float(meta.get("fps") or cap.get(cv2.CAP_PROP_FPS) or 0.0)
    if fps <= 0 or fps > 120:
        fps = 0.0
    total_frames = int(meta.get("nb_frames") or cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration = float(meta.get("duration") or 0.0)
    if duration <= 0 and fps > 0 and total_frames > 0:
        duration = total_frames / fps
    if total_frames <= 0 and duration > 0 and fps > 0:
        total_frames = int(duration * fps)
    if fps <= 0:
        total_frames = 0
    if total_frames < 0:
        total_frames = 0

    extract_w, extract_h = compute_extract_dimensions(native_w, native_h, max_width)
    aspect = round(native_w / native_h, 6) if native_h else 0.0
    cap.release()

    return VideoProfile(
        source_path=path,
        native_width=native_w,
        native_height=native_h,
        native_fps=fps,
        total_frames=total_frames,
        duration_seconds=duration,
        aspect_ratio=aspect,
        extract_width=extract_w,
        extract_height=extract_h,
    )


def transcript_id_at(segments: list[dict], timestamp_s: float) -> int | None:
    for seg in segments:
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start))
        if start <= timestamp_s <= end:
            seg_id = seg.get("id")
            return int(seg_id) if seg_id is not None else None
    return None


def speaker_role_at(segments: list[dict], timestamp_s: float) -> str | None:
    for seg in segments:
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start))
        if start <= timestamp_s <= end:
            role = seg.get("speaker_role")
            return str(role) if role is not None else None
    return None


def load_speech_anchors(
    student_dir: Path,
    student_id: str,
    transcript_segments: list[dict],
) -> tuple[list[SpeechAnchor], list[float]]:
    hybrid_path = resolve_hybrid_path(student_dir, student_id)
    if not hybrid_path:
        return [], []

    hybrid = json.loads(hybrid_path.read_text(encoding="utf-8"))
    role_map = build_role_mapping(hybrid, student_id)
    timeline = get_hybrid_timeline(hybrid)
    if not timeline:
        return [], []

    anchors: list[SpeechAnchor] = []
    boundaries: list[float] = []
    seen_ms: set[int] = set()

    for slice_ in timeline:
        start = float(slice_["start"])
        end = float(slice_["end"])
        if end <= start:
            continue
        midpoint = start + (end - start) / 2.0
        ms_key = int(round(midpoint * 1000))
        if ms_key in seen_ms:
            continue
        seen_ms.add(ms_key)

        speaker_id = str(slice_.get("speaker_id", ""))
        role = role_map.speaker_roles.get(speaker_id, "classmate")
        tid = transcript_id_at(transcript_segments, midpoint)
        anchors.append(
            SpeechAnchor(
                timestamp_seconds=midpoint,
                speaker_id=speaker_id,
                speaker_role=role,
                diarization_start=start,
                diarization_end=end,
                transcript_id=tid,
                high_value_interaction_zone=(role == "student"),
            )
        )
        boundaries.extend([start, end])

    boundaries = sorted(set(round(b, 3) for b in boundaries))
    return anchors, boundaries


def resize_frame(frame: np.ndarray, profile: VideoProfile) -> np.ndarray:
    import cv2

    if frame.shape[1] == profile.extract_width and frame.shape[0] == profile.extract_height:
        return frame
    return cv2.resize(
        frame,
        (profile.extract_width, profile.extract_height),
        interpolation=cv2.INTER_CUBIC,
    )


def motion_preview_gray(frame_bgr: np.ndarray, preview_width: int) -> np.ndarray:
    """Downscaled grayscale for motion detection; saved frames remain full resolution."""
    import cv2

    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    if preview_width <= 0 or frame_bgr.shape[1] <= preview_width:
        return gray
    scale = preview_width / frame_bgr.shape[1]
    height = max(1, int(round(frame_bgr.shape[0] * scale)))
    return cv2.resize(gray, (preview_width, height), interpolation=cv2.INTER_AREA)


def motion_change_fraction(prev_gray: np.ndarray, curr_gray: np.ndarray) -> float:
    import cv2

    if prev_gray.shape != curr_gray.shape:
        curr_gray = cv2.resize(curr_gray, (prev_gray.shape[1], prev_gray.shape[0]))
    blurred_prev = cv2.GaussianBlur(prev_gray, (5, 5), 0)
    blurred_curr = cv2.GaussianBlur(curr_gray, (5, 5), 0)
    delta = cv2.absdiff(blurred_prev, blurred_curr)
    _, binary = cv2.threshold(delta, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    changed = int(np.count_nonzero(binary))
    total = binary.size
    return changed / total if total else 0.0


def is_boundary_crossing(timestamp_s: float, boundaries: list[float], epsilon: float) -> bool:
    for boundary in boundaries:
        if abs(timestamp_s - boundary) <= epsilon:
            return True
    return False


def cooldown_allows(
    timestamp_s: float,
    state: ExtractionState,
    cooldown_ms: int,
    boundaries: list[float],
    boundary_epsilon: float,
) -> bool:
    if is_boundary_crossing(timestamp_s, boundaries, boundary_epsilon):
        return True
    if state.last_extract_ms < 0:
        return True
    return (timestamp_s * 1000.0 - state.last_extract_ms) >= cooldown_ms


def read_frame_with_recovery(
    cap: Any,
    last_good_bgr: np.ndarray | None,
    profile: VideoProfile,
    *,
    compute_gray: bool = True,
) -> tuple[np.ndarray | None, np.ndarray | None, float]:
    """Return (bgr, gray, timestamp_s). Uses look-ahead linear fill on corrupt reads."""
    import cv2

    ok, frame = cap.read()
    frame_idx = cap.get(cv2.CAP_PROP_POS_FRAMES)
    timestamp_s = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

    if ok and frame is not None and frame.size > 0:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if compute_gray else None
        return frame, gray, timestamp_s

    profile.corrupt_frame_count += 1
    ok2, frame2 = cap.read()
    if ok2 and frame2 is not None and frame2.size > 0:
        if last_good_bgr is not None:
            filled = last_good_bgr.copy()
            gray = cv2.cvtColor(filled, cv2.COLOR_BGR2GRAY) if compute_gray else None
            return filled, gray, timestamp_s
        gray = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY) if compute_gray else None
        return frame2, gray, timestamp_s

    if last_good_bgr is not None:
        filled = last_good_bgr.copy()
        gray = cv2.cvtColor(filled, cv2.COLOR_BGR2GRAY) if compute_gray else None
        return filled, gray, timestamp_s

    LOGGER.debug("unrecoverable frame at idx=%s t=%.2fs", frame_idx, timestamp_s)
    return None, None, timestamp_s


def reopen_video_capture(video_path: Path) -> Any:
    """Fresh OpenCV handle — required after many WebM/VP9 seeks."""
    import cv2

    cap = cv2.VideoCapture(str(video_path.resolve()))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV cannot reopen video: {video_path}")
    return cap


def seek_frame(cap: Any, timestamp_s: float) -> None:
    import cv2

    cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp_s) * 1000.0)


def save_keyframe(
    frame_bgr: np.ndarray,
    profile: VideoProfile,
    out_dir: Path,
    state: ExtractionState,
    deduplicator: VisualDeduplicator | None,
    non_task_filter: NonTaskScreenFilter | None,
    timestamp_s: float,
    trigger_reason: str,
    metrics: dict[str, Any],
    jpeg_quality: int,
    dry_run: bool,
    *,
    bypass_dedup: bool = False,
) -> FrameRecord | None:
    state.candidate_frames_seen += 1
    if state.already_extracted_near(timestamp_s):
        state.temporal_dedup_skipped += 1
        return None

    resized = resize_frame(frame_bgr, profile)
    if non_task_filter is not None and non_task_filter.should_skip(resized, trigger_reason=trigger_reason):
        state.non_task_skipped += 1
        match = non_task_filter.last_match
        LOGGER.debug(
            "[NON-TASK ATLANDI] Timestamp: %.2f trigger=%s reason=%s distance=%s",
            timestamp_s,
            trigger_reason,
            match.reason if match else "unknown",
            (
                f"{match.distance:.1f}"
                if match and match.distance is not None
                else "n/a"
            ),
        )
        return None

    if non_task_filter is not None and non_task_filter.task_guard is not None:
        guard_match = non_task_filter.task_guard.classify(resized)
        if not guard_match.is_task:
            activity = non_task_filter.task_activity
            if trigger_reason in GAP_FILL_TRIGGERS and gap_fill_content_accepts(resized, activity):
                LOGGER.debug(
                    "[GAP-FILL RELAX] Timestamp: %.2f trigger=%s activity=%s",
                    timestamp_s,
                    trigger_reason,
                    activity,
                )
            else:
                state.non_task_skipped += 1
                LOGGER.debug(
                    "[NON-TASK ATLANDI] Timestamp: %.2f trigger=%s reason=final_guard:%s",
                    timestamp_s,
                    trigger_reason,
                    guard_match.reason,
                )
                return None

    if deduplicator is not None:
        if bypass_dedup:
            deduplicator.accept_frame(resized)
            LOGGER.debug(
                "[DEDUP BYPASS] Timestamp: %.2f trigger=%s gap_fill_static_snapshot",
                timestamp_s,
                trigger_reason,
            )
        elif not deduplicator.should_save(resized):
            state.visual_dedup_skipped += 1
            LOGGER.debug(
                "[DEDUP ATLANDI] Timestamp: %.2f trigger=%s method=%s distance=%s",
                timestamp_s,
                trigger_reason,
                deduplicator.method,
                (
                    f"{deduplicator.last_distance:.4f}"
                    if deduplicator.last_distance is not None
                    else "n/a"
                ),
            )
            return None

    frame_id = f"frame_{state.frame_counter + 1:04d}"
    out_path = out_dir / f"{frame_id}.jpg"

    if not dry_run:
        import cv2

        out_dir.mkdir(parents=True, exist_ok=True)
        written = cv2.imwrite(
            str(out_path),
            resized,
            [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
        )
        if not written:
            raise OSError(f"OpenCV failed to write keyframe: {out_path}")

    record = FrameRecord(
        frame_id=frame_id,
        source_timestamp_seconds=timestamp_s,
        extraction_trigger_reason=trigger_reason,
        metrics=metrics,
        file_path=repo_relative(out_path),
    )
    state.register(record)
    return record


def extract_speech_anchors(
    cap: Any,
    profile: VideoProfile,
    anchors: list[SpeechAnchor],
    out_dir: Path,
    state: ExtractionState,
    deduplicator: VisualDeduplicator | None,
    non_task_filter: NonTaskScreenFilter | None,
    jpeg_quality: int,
    dry_run: bool,
    max_frames: int,
    speech_gap_bypass_seconds: float,
) -> int:
    """Single forward pass — avoids VP9/WebM seek failures on screen recordings."""
    import cv2

    if not anchors:
        return 0

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    sorted_anchors = sorted(anchors, key=lambda a: a.timestamp_seconds)
    anchor_idx = 0
    count = 0
    last_good_bgr: np.ndarray | None = None
    duration_limit = profile.duration_seconds + 0.25 if profile.duration_seconds > 0 else None
    consecutive_failures = 0

    while anchor_idx < len(sorted_anchors):
        if max_frames and len(state.extracted) >= max_frames:
            break

        bgr, _, timestamp_s = read_frame_with_recovery(cap, last_good_bgr, profile)
        if bgr is None:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                break
            continue
        consecutive_failures = 0
        last_good_bgr = bgr

        if duration_limit is not None and timestamp_s > duration_limit:
            break

        while anchor_idx < len(sorted_anchors):
            anchor = sorted_anchors[anchor_idx]
            if anchor.timestamp_seconds > timestamp_s + 0.05:
                break
            metrics = {
                "pixel_change_percentage": None,
                "associated_speaker_role": anchor.speaker_role,
                "associated_transcript_id": anchor.transcript_id,
                "associated_speaker_id": anchor.speaker_id,
                "high_value_interaction_zone": anchor.high_value_interaction_zone,
                "diarization_start": anchor.diarization_start,
                "diarization_end": anchor.diarization_end,
            }
            anchor_ts = timestamp_s if timestamp_s > 0 else anchor.timestamp_seconds
            gap_since_last = state.seconds_since_last_extracted(anchor_ts)
            bypass_dedup = (
                gap_since_last is not None and gap_since_last > speech_gap_bypass_seconds
            )
            record = save_keyframe(
                bgr,
                profile,
                out_dir,
                state,
                deduplicator,
                non_task_filter,
                anchor_ts,
                "speech_anchor_midpoint",
                metrics,
                jpeg_quality,
                dry_run,
                bypass_dedup=bypass_dedup,
            )
            if record:
                count += 1
                if count == 1 or count % 100 == 0 or count == len(sorted_anchors):
                    LOGGER.info(
                        "Anchor: %s @ %.2fs role=%s (%d/%d)",
                        record.frame_id,
                        record.source_timestamp_seconds,
                        anchor.speaker_role,
                        count,
                        len(sorted_anchors),
                    )
            anchor_idx += 1

    if anchor_idx < len(sorted_anchors):
        LOGGER.warning(
            "Anchor: %d/%d anchors not reached before scan end",
            anchor_idx,
            len(sorted_anchors),
        )
    return count


def _process_speech_anchors_at_timestamp(
    *,
    bgr: np.ndarray,
    profile: VideoProfile,
    timestamp_s: float,
    sorted_anchors: list[SpeechAnchor],
    anchor_idx: int,
    out_dir: Path,
    state: ExtractionState,
    deduplicator: VisualDeduplicator | None,
    non_task_filter: NonTaskScreenFilter | None,
    jpeg_quality: int,
    dry_run: bool,
    max_frames: int,
    speech_gap_bypass_seconds: float,
    total_anchors: int,
) -> tuple[int, int]:
    """Consume anchors due at ``timestamp_s``; return (new_anchor_idx, saves_this_step)."""
    count = 0
    while anchor_idx < len(sorted_anchors):
        if max_frames and len(state.extracted) >= max_frames:
            break
        anchor = sorted_anchors[anchor_idx]
        if anchor.timestamp_seconds > timestamp_s + 0.05:
            break
        metrics = {
            "pixel_change_percentage": None,
            "associated_speaker_role": anchor.speaker_role,
            "associated_transcript_id": anchor.transcript_id,
            "associated_speaker_id": anchor.speaker_id,
            "high_value_interaction_zone": anchor.high_value_interaction_zone,
            "diarization_start": anchor.diarization_start,
            "diarization_end": anchor.diarization_end,
        }
        anchor_ts = timestamp_s if timestamp_s > 0 else anchor.timestamp_seconds
        gap_since_last = state.seconds_since_last_extracted(anchor_ts)
        bypass_dedup = gap_since_last is not None and gap_since_last > speech_gap_bypass_seconds
        record = save_keyframe(
            bgr,
            profile,
            out_dir,
            state,
            deduplicator,
            non_task_filter,
            anchor_ts,
            "speech_anchor_midpoint",
            metrics,
            jpeg_quality,
            dry_run,
            bypass_dedup=bypass_dedup,
        )
        if record:
            count += 1
            if count == 1 or count % 100 == 0 or anchor_idx + 1 == total_anchors:
                LOGGER.info(
                    "Anchor: %s @ %.2fs role=%s (%d/%d)",
                    record.frame_id,
                    record.source_timestamp_seconds,
                    anchor.speaker_role,
                    anchor_idx + 1,
                    total_anchors,
                )
        anchor_idx += 1
    return anchor_idx, count


def _is_vp9_eof_rewind(timestamp_s: float, last_pts: float, duration_limit: float | None) -> bool:
    """VP9/WebM often reports PTS ~0 after the final decoded frame."""
    if last_pts < 60.0 or timestamp_s >= 1.0:
        return False
    if duration_limit is not None and last_pts >= duration_limit * 0.85:
        return True
    return last_pts > 3600.0


def process_motion_at_timestamp(
    *,
    bgr: np.ndarray,
    profile: VideoProfile,
    out_dir: Path,
    state: ExtractionState,
    deduplicator: VisualDeduplicator | None,
    non_task_filter: NonTaskScreenFilter | None,
    boundaries: list[float],
    transcript_segments: list[dict],
    timestamp_s: float,
    prev_motion_gray: np.ndarray | None,
    motion_gray: np.ndarray,
    motion_threshold: float,
    silent_motion_threshold: float,
    silent_screen_gap_fill_seconds: float,
    codap_gap_fill_seconds: float,
    cooldown_ms: int,
    boundary_epsilon: float,
    jpeg_quality: int,
    dry_run: bool,
    motion_only_fallback: bool,
) -> tuple[int, bool]:
    """Apply motion threshold + silent CODAP gap-fill; returns (saves, logged_milestone)."""
    saves = 0
    logged = False
    effective_threshold = silent_motion_threshold if motion_only_fallback else motion_threshold

    gap_limit = (
        silent_screen_gap_fill_seconds
        if motion_only_fallback
        else codap_gap_fill_seconds
    )
    if gap_limit > 0:
        gap = state.seconds_since_last_extracted(timestamp_s)
        if gap is not None and gap >= gap_limit:
            if cooldown_allows(timestamp_s, state, cooldown_ms, boundaries, boundary_epsilon):
                gap_trigger = (
                    "silent_screen_gap_fill"
                    if motion_only_fallback
                    else "codap_static_gap_fill"
                )
                gap_metrics = {
                    "pixel_change_percentage": None,
                    "associated_speaker_role": "unknown",
                    "associated_transcript_id": None,
                    "high_value_interaction_zone": False,
                    "codap_gap_seconds": round(gap, 2),
                }
                record = save_keyframe(
                    bgr,
                    profile,
                    out_dir,
                    state,
                    deduplicator,
                    non_task_filter,
                    timestamp_s,
                    gap_trigger,
                    gap_metrics,
                    jpeg_quality,
                    dry_run,
                    bypass_dedup=True,
                )
                if record:
                    saves += 1
                    if saves == 1 or saves % 50 == 0:
                        LOGGER.info(
                            "Gap-fill: %s @ %.2fs gap=%.0fs trigger=%s",
                            record.frame_id,
                            record.source_timestamp_seconds,
                            gap,
                            gap_trigger,
                        )
                        logged = True

    if prev_motion_gray is not None:
        change_frac = motion_change_fraction(prev_motion_gray, motion_gray)
        if (
            change_frac >= effective_threshold
            and cooldown_allows(timestamp_s, state, cooldown_ms, boundaries, boundary_epsilon)
        ):
            if motion_only_fallback:
                trigger_reason = "motion_only_fallback"
                role: str | None = "unknown"
                tid: int | None = None
                high_value = False
            else:
                trigger_reason = "motion_threshold_exceeded"
                tid = transcript_id_at(transcript_segments, timestamp_s)
                role = speaker_role_at(transcript_segments, timestamp_s)
                high_value = role == "student"

            metrics = {
                "pixel_change_percentage": round(change_frac * 100.0, 4),
                "associated_speaker_role": role,
                "associated_transcript_id": tid,
                "high_value_interaction_zone": high_value,
            }
            record = save_keyframe(
                bgr,
                profile,
                out_dir,
                state,
                deduplicator,
                non_task_filter,
                timestamp_s,
                trigger_reason,
                metrics,
                jpeg_quality,
                dry_run,
            )
            if record:
                saves += 1
                if not logged and (saves == 1 or saves % 50 == 0):
                    tag = "Fallback" if motion_only_fallback else "Motion"
                    LOGGER.info(
                        "%s: %s @ %.2fs change=%.2f%% (total=%d)",
                        tag,
                        record.frame_id,
                        record.source_timestamp_seconds,
                        metrics.get("pixel_change_percentage") or 0.0,
                        saves,
                    )
                    logged = True
    return saves, logged


def scan_combined_keyframes(
    cap: Any,
    profile: VideoProfile,
    anchors: list[SpeechAnchor],
    out_dir: Path,
    state: ExtractionState,
    deduplicator: VisualDeduplicator | None,
    non_task_filter: NonTaskScreenFilter | None,
    boundaries: list[float],
    transcript_segments: list[dict],
    motion_threshold: float,
    cooldown_ms: int,
    boundary_epsilon: float,
    jpeg_quality: int,
    dry_run: bool,
    max_frames: int,
    *,
    motion_only_fallback: bool,
    motion_preview_width: int,
    speech_gap_bypass_seconds: float,
    silent_motion_threshold: float,
    silent_screen_gap_fill_seconds: float,
    codap_gap_fill_seconds: float,
    enable_speech: bool,
    enable_motion: bool,
) -> tuple[int, int]:
    """Single forward decode: speech anchors + motion keyframes (output JPEGs stay full-res)."""
    import cv2

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    sorted_anchors = sorted(anchors, key=lambda a: a.timestamp_seconds) if enable_speech else []
    anchor_idx = 0
    speech_count = 0
    motion_count = 0
    prev_motion_gray: np.ndarray | None = None
    last_good_bgr: np.ndarray | None = None
    last_pts = -1.0
    stuck_at_timestamp = 0
    consecutive_failures = 0
    last_progress_log_t = -1.0
    duration_limit = profile.duration_seconds + 0.25 if profile.duration_seconds > 0 else None

    while True:
        if max_frames and len(state.extracted) >= max_frames:
            break

        bgr, _, timestamp_s = read_frame_with_recovery(
            cap, last_good_bgr, profile, compute_gray=False
        )
        if bgr is None:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                break
            continue
        consecutive_failures = 0

        if duration_limit is not None and timestamp_s > duration_limit:
            break

        if abs(timestamp_s - last_pts) < 1e-3:
            stuck_at_timestamp += 1
            if stuck_at_timestamp >= 30:
                if _is_vp9_eof_rewind(timestamp_s, last_pts, duration_limit):
                    LOGGER.info(
                        "Combined-scan: VP9 end-of-file at t=%.2fs (last=%.2fs)",
                        timestamp_s,
                        last_pts,
                    )
                else:
                    LOGGER.warning(
                        "Combined-scan stuck at t=%.2fs — stopping (VP9 decode limit)",
                        timestamp_s,
                    )
                break
        else:
            stuck_at_timestamp = 0

        if timestamp_s + 1e-6 < last_pts:
            profile.pts_inversion_count += 1
        last_pts = timestamp_s
        last_good_bgr = bgr

        if enable_speech and anchor_idx < len(sorted_anchors):
            anchor_idx, step_saves = _process_speech_anchors_at_timestamp(
                bgr=bgr,
                profile=profile,
                timestamp_s=timestamp_s,
                sorted_anchors=sorted_anchors,
                anchor_idx=anchor_idx,
                out_dir=out_dir,
                state=state,
                deduplicator=deduplicator,
                non_task_filter=non_task_filter,
                jpeg_quality=jpeg_quality,
                dry_run=dry_run,
                max_frames=max_frames,
                speech_gap_bypass_seconds=speech_gap_bypass_seconds,
                total_anchors=len(sorted_anchors),
            )
            speech_count += step_saves

        if enable_motion:
            motion_gray = motion_preview_gray(bgr, motion_preview_width)
            step_saves, _ = process_motion_at_timestamp(
                bgr=bgr,
                profile=profile,
                out_dir=out_dir,
                state=state,
                deduplicator=deduplicator,
                non_task_filter=non_task_filter,
                boundaries=boundaries,
                transcript_segments=transcript_segments,
                timestamp_s=timestamp_s,
                prev_motion_gray=prev_motion_gray,
                motion_gray=motion_gray,
                motion_threshold=motion_threshold,
                silent_motion_threshold=silent_motion_threshold,
                silent_screen_gap_fill_seconds=silent_screen_gap_fill_seconds,
                codap_gap_fill_seconds=codap_gap_fill_seconds,
                cooldown_ms=cooldown_ms,
                boundary_epsilon=boundary_epsilon,
                jpeg_quality=jpeg_quality,
                dry_run=dry_run,
                motion_only_fallback=motion_only_fallback,
            )
            motion_count += step_saves
            prev_motion_gray = motion_gray

        if timestamp_s - last_progress_log_t >= 60.0:
            LOGGER.info(
                "Combined-scan: t=%.0fs speech=%d motion=%d total=%d",
                timestamp_s,
                speech_count,
                motion_count,
                len(state.extracted),
            )
            last_progress_log_t = timestamp_s

    if enable_speech and anchor_idx < len(sorted_anchors):
        LOGGER.warning(
            "Anchor: %d/%d anchors not reached before scan end",
            anchor_idx,
            len(sorted_anchors),
        )
    return speech_count, motion_count


def scan_motion_keyframes(
    cap: Any,
    profile: VideoProfile,
    out_dir: Path,
    state: ExtractionState,
    deduplicator: VisualDeduplicator | None,
    non_task_filter: NonTaskScreenFilter | None,
    boundaries: list[float],
    transcript_segments: list[dict],
    motion_threshold: float,
    cooldown_ms: int,
    boundary_epsilon: float,
    jpeg_quality: int,
    dry_run: bool,
    max_frames: int,
    *,
    motion_only_fallback: bool,
    motion_preview_width: int = DEFAULT_MOTION_PREVIEW_WIDTH,
    silent_motion_threshold: float = DEFAULT_SILENT_MOTION_THRESHOLD,
    silent_screen_gap_fill_seconds: float = DEFAULT_SILENT_SCREEN_GAP_FILL_SECONDS,
    codap_gap_fill_seconds: float = DEFAULT_CODAP_GAP_FILL_SECONDS,
) -> int:
    import cv2

    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    prev_motion_gray: np.ndarray | None = None
    last_good_bgr: np.ndarray | None = None
    last_pts = -1.0
    count = 0
    duration_limit = profile.duration_seconds + 0.25 if profile.duration_seconds > 0 else None
    consecutive_failures = 0
    last_progress_log_t = -1.0
    stuck_at_timestamp = 0

    while True:
        if max_frames and len(state.extracted) >= max_frames:
            break

        bgr, _, timestamp_s = read_frame_with_recovery(
            cap, last_good_bgr, profile, compute_gray=False
        )
        if bgr is None:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                break
            continue
        consecutive_failures = 0

        if duration_limit is not None and timestamp_s > duration_limit:
            break

        if abs(timestamp_s - last_pts) < 1e-3:
            stuck_at_timestamp += 1
            if stuck_at_timestamp >= 30:
                if _is_vp9_eof_rewind(timestamp_s, last_pts, duration_limit):
                    LOGGER.info(
                        "Motion-scan: VP9 end-of-file at t=%.2fs (last=%.2fs)",
                        timestamp_s,
                        last_pts,
                    )
                else:
                    LOGGER.warning(
                        "Motion-scan stuck at t=%.2fs — stopping scan (VP9 seek/decode limit)",
                        timestamp_s,
                    )
                break
        else:
            stuck_at_timestamp = 0

        if timestamp_s + 1e-6 < last_pts:
            profile.pts_inversion_count += 1
        last_pts = timestamp_s
        last_good_bgr = bgr

        motion_gray = motion_preview_gray(bgr, motion_preview_width)
        step_saves, _ = process_motion_at_timestamp(
            bgr=bgr,
            profile=profile,
            out_dir=out_dir,
            state=state,
            deduplicator=deduplicator,
            non_task_filter=non_task_filter,
            boundaries=boundaries,
            transcript_segments=transcript_segments,
            timestamp_s=timestamp_s,
            prev_motion_gray=prev_motion_gray,
            motion_gray=motion_gray,
            motion_threshold=motion_threshold,
            silent_motion_threshold=silent_motion_threshold,
            silent_screen_gap_fill_seconds=silent_screen_gap_fill_seconds,
            codap_gap_fill_seconds=codap_gap_fill_seconds,
            cooldown_ms=cooldown_ms,
            boundary_epsilon=boundary_epsilon,
            jpeg_quality=jpeg_quality,
            dry_run=dry_run,
            motion_only_fallback=motion_only_fallback,
        )
        count += step_saves
        prev_motion_gray = motion_gray

        if timestamp_s - last_progress_log_t >= 120.0:
            tag = "Fallback-scan" if motion_only_fallback else "Motion-scan"
            LOGGER.info("%s: t=%.0fs extracted=%d", tag, timestamp_s, count)
            last_progress_log_t = timestamp_s

    return count


def build_manifest(
    *,
    student_id: str,
    video_path: Path,
    video_resolution: VideoResolutionResult,
    audio_root: Path,
    video_root: Path | None,
    profile: VideoProfile,
    modalities: ModalityAssessment,
    state: ExtractionState,
    speech_count: int,
    motion_count: int,
    parameters: dict[str, Any],
) -> dict[str, Any]:
    frames_json = [record.to_json() for record in state.extracted]
    segments_json = [record.to_segment_json() for record in state.extracted]

    return {
        "schema_version": "video_extraction_manifest_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "student_id": student_id,
        "extraction_mode": modalities.extraction_mode,
        "path_resolution": {
            "audio_root": repo_relative(audio_root),
            "video_root": repo_relative(video_root) if video_root else None,
            "video_match_strategy": video_resolution.strategy,
            "searched_roots": video_resolution.searched_roots,
            "candidate_count": video_resolution.candidate_count,
            "source_video": repo_relative(video_path),
            "source_video_absolute": str(video_path.resolve()),
            "output_frames_dir": repo_relative(audio_root / student_id / f"{student_id}_frames"),
        },
        "modalities": {
            "has_video": modalities.has_video,
            "has_hybrid_diarization": modalities.has_hybrid_diarization,
            "has_transcript_segments": modalities.has_transcript_segments,
            "hybrid_segment_count": modalities.hybrid_segment_count,
            "transcript_segment_count": modalities.transcript_segment_count,
            "has_usable_transcript_modality": modalities.has_usable_transcript_modality,
        },
        "video_profile": {
            "native_resolution": [profile.native_width, profile.native_height],
            "extract_resolution": [profile.extract_width, profile.extract_height],
            "aspect_ratio": profile.aspect_ratio,
            "fps": round(profile.native_fps, 4),
            "total_frames": profile.total_frames,
            "duration_seconds": round(profile.duration_seconds, 3),
            "corrupt_frame_count": profile.corrupt_frame_count,
            "pts_inversion_count": profile.pts_inversion_count,
        },
        "parameters": parameters,
        "summary": {
            "speech_anchor_count": speech_count,
            "motion_keyframe_count": motion_count,
            "total_frames_extracted": len(state.extracted),
            "candidate_frames_considered": state.candidate_frames_seen,
            "visual_duplicates_filtered": state.visual_dedup_skipped,
            "temporal_duplicates_filtered": state.temporal_dedup_skipped,
            "non_task_screens_filtered": state.non_task_skipped,
            "dedup_savings_percentage": round(
                (
                    (state.candidate_frames_seen - len(state.extracted))
                    / state.candidate_frames_seen
                    * 100.0
                ),
                2,
            )
            if state.candidate_frames_seen
            else 0.0,
        },
        "segments": segments_json,
        "frames": frames_json,
    }


def write_manifest(manifest_path: Path, manifest: dict[str, Any], *, dry_run: bool) -> None:
    if dry_run:
        return
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def process_student(
    student_dir: Path,
    *,
    audio_root: Path,
    video_root: Path | None,
    max_width: int,
    motion_threshold: float,
    cooldown_ms: int,
    boundary_epsilon: float,
    jpeg_quality: int,
    speech_only: bool,
    dry_run: bool,
    max_frames: int,
    compute_type: str,
    enable_dedup: bool,
    dedup_method: Literal["phash", "mse"],
    phash_threshold: int,
    mse_threshold: float,
    filter_non_task_screens: bool,
    non_task_templates: Path,
    non_task_phash_threshold: int,
    non_task_policy: Literal["skip", "attenuate"],
    non_task_heuristics: bool,
    enable_codap_task_guard: bool,
    codap_task_templates: Path,
    colab_task_templates: Path,
    task_activity: TaskActivity,
    codap_task_phash_threshold: int,
    codap_task_heuristics: bool,
    require_codap_content: bool,
    speech_gap_bypass_seconds: float,
    single_pass: bool,
    motion_preview_width: int,
    silent_motion_threshold: float,
    silent_screen_gap_fill_seconds: float,
    codap_gap_fill_seconds: float,
) -> dict[str, Any]:
    student_id = student_dir.name
    video_resolution = resolve_video_path_tiered(student_dir, student_id, video_root)

    if not video_resolution.resolved:
        LOGGER.warning(
            "%s: no video found (strategy=%s, searched=%s) — skipping visual extraction",
            student_id,
            video_resolution.strategy,
            ", ".join(video_resolution.searched_roots) or "none",
        )
        return {
            "student_id": student_id,
            "status": "skipped",
            "reason": "missing_video",
            "video_match_strategy": video_resolution.strategy,
        }

    modalities = assess_modalities(student_dir, student_id, video_resolution, speech_only=speech_only)
    video_path = video_resolution.path
    assert video_path is not None

    if modalities.extraction_mode == "motion_only_fallback":
        LOGGER.warning(
            "%s: Fallback mode — no_speech/incomplete hybrid (hybrid_segments=%d, transcript_segments=%d); "
            "pure motion scan only",
            student_id,
            modalities.hybrid_segment_count,
            modalities.transcript_segment_count,
        )
    elif modalities.extraction_mode == "full_multimodal":
        LOGGER.info(
            "%s: Multimodal — speech Anchor + Motion overlay (video=%s, hybrid_segments=%d)",
            student_id,
            video_resolution.strategy,
            modalities.hybrid_segment_count,
        )
    if single_pass and not speech_only:
        LOGGER.info(
            "%s: Performance — single-pass decode, motion preview width=%d (JPEG output unchanged)",
            student_id,
            motion_preview_width,
        )
    if modalities.extraction_mode == "motion_only_fallback":
        LOGGER.info(
            "%s: Silent screen recording — motion threshold=%.4f, gap-fill=%.0fs",
            student_id,
            silent_motion_threshold,
            silent_screen_gap_fill_seconds,
        )

    profile = profile_video(video_path, max_width)
    transcript_segments = load_labeled_transcript(student_dir, student_id)

    anchors: list[SpeechAnchor] = []
    boundaries: list[float] = []
    if modalities.has_usable_transcript_modality:
        anchors, boundaries = load_speech_anchors(student_dir, student_id, transcript_segments)

    frames_dir = student_dir / f"{student_id}_frames"
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    state = ExtractionState()
    deduplicator = (
        VisualDeduplicator(
            method=dedup_method,
            phash_threshold=phash_threshold,
            mse_threshold=mse_threshold,
        )
        if enable_dedup
        else None
    )
    non_task_filter = None
    if filter_non_task_screens:
        task_guard = None
        if enable_codap_task_guard:
            task_guard = build_task_screen_guard(
                task_activity,
                codap_template_dir=codap_task_templates,
                colab_template_dir=colab_task_templates,
                codap_phash_threshold=codap_task_phash_threshold,
                use_heuristics=codap_task_heuristics,
            )
        non_task_filter = NonTaskScreenFilter(
            non_task_templates,
            task_guard=task_guard,
            phash_threshold=non_task_phash_threshold,
            use_heuristics=non_task_heuristics,
            require_codap_content=require_codap_content,
            policy=non_task_policy,
        )

    cap: Any | None = None
    speech_count = 0
    motion_count = 0

    try:
        cap = reopen_video_capture(video_path)

        use_combined = single_pass and not speech_only
        if use_combined:
            speech_count, motion_count = scan_combined_keyframes(
                cap,
                profile,
                anchors,
                frames_dir,
                state,
                deduplicator,
                non_task_filter,
                boundaries,
                transcript_segments,
                motion_threshold,
                cooldown_ms,
                boundary_epsilon,
                jpeg_quality,
                dry_run,
                max_frames,
                motion_only_fallback=(modalities.extraction_mode == "motion_only_fallback"),
                motion_preview_width=motion_preview_width,
                speech_gap_bypass_seconds=speech_gap_bypass_seconds,
                silent_motion_threshold=silent_motion_threshold,
                silent_screen_gap_fill_seconds=silent_screen_gap_fill_seconds,
                codap_gap_fill_seconds=codap_gap_fill_seconds,
                enable_speech=modalities.has_usable_transcript_modality,
                enable_motion=True,
            )
        elif modalities.has_usable_transcript_modality:
            speech_count = extract_speech_anchors(
                cap,
                profile,
                anchors,
                frames_dir,
                state,
                deduplicator,
                non_task_filter,
                jpeg_quality,
                dry_run,
                max_frames if speech_only else max_frames,
                speech_gap_bypass_seconds,
            )

        if not use_combined and not speech_only:
            cap.release()
            cap = None
            gc.collect()
            cap = reopen_video_capture(video_path)
            motion_count = scan_motion_keyframes(
                cap,
                profile,
                frames_dir,
                state,
                deduplicator,
                non_task_filter,
                boundaries,
                transcript_segments,
                motion_threshold,
                cooldown_ms,
                boundary_epsilon,
                jpeg_quality,
                dry_run,
                max_frames,
                motion_only_fallback=(modalities.extraction_mode == "motion_only_fallback"),
                motion_preview_width=motion_preview_width,
                silent_motion_threshold=silent_motion_threshold,
                silent_screen_gap_fill_seconds=silent_screen_gap_fill_seconds,
                codap_gap_fill_seconds=codap_gap_fill_seconds,
            )
        elif speech_only:
            motion_count = 0

        parameters = {
            "max_width": max_width,
            "motion_threshold_fraction": motion_threshold,
            "cooldown_ms": cooldown_ms,
            "boundary_epsilon_seconds": boundary_epsilon,
            "speech_only": speech_only,
            "compute_type": compute_type,
            "visual_dedup_enabled": enable_dedup,
            "dedup_method": dedup_method if enable_dedup else None,
            "phash_threshold": phash_threshold if enable_dedup and dedup_method == "phash" else None,
            "mse_threshold": mse_threshold if enable_dedup and dedup_method == "mse" else None,
            "filter_non_task_screens": filter_non_task_screens,
            "non_task_policy": non_task_policy if filter_non_task_screens else None,
            "non_task_phash_threshold": non_task_phash_threshold if filter_non_task_screens else None,
            "non_task_templates": repo_relative(non_task_templates) if filter_non_task_screens else None,
            "enable_codap_task_guard": enable_codap_task_guard if filter_non_task_screens else None,
            "codap_task_phash_threshold": codap_task_phash_threshold
            if filter_non_task_screens and enable_codap_task_guard
            else None,
            "codap_task_templates": repo_relative(codap_task_templates)
            if filter_non_task_screens and enable_codap_task_guard
            else None,
            "codap_task_heuristics": codap_task_heuristics
            if filter_non_task_screens and enable_codap_task_guard
            else None,
            "task_activity": task_activity if filter_non_task_screens else None,
            "colab_task_templates": repo_relative(colab_task_templates)
            if filter_non_task_screens and enable_codap_task_guard
            else None,
            "require_codap_content": require_codap_content if filter_non_task_screens else None,
            "speech_gap_bypass_seconds": speech_gap_bypass_seconds if filter_non_task_screens else None,
            "single_pass": single_pass,
            "motion_preview_width": motion_preview_width,
            "silent_motion_threshold": silent_motion_threshold,
            "silent_screen_gap_fill_seconds": silent_screen_gap_fill_seconds,
            "codap_gap_fill_seconds": codap_gap_fill_seconds,
            "silent_screen_recording": is_silent_screen_recording(student_dir, student_id),
        }
        manifest = build_manifest(
            student_id=student_id,
            video_path=video_path,
            video_resolution=video_resolution,
            audio_root=audio_root,
            video_root=video_root,
            profile=profile,
            modalities=modalities,
            state=state,
            speech_count=speech_count,
            motion_count=motion_count,
            parameters=parameters,
        )
        write_manifest(manifest_path, manifest, dry_run=dry_run)

        LOGGER.info(
            "%s: %d frames (%d speech, %d motion, mode=%s) -> %s",
            student_id,
            len(state.extracted),
            speech_count,
            motion_count,
            modalities.extraction_mode,
            manifest_path.name,
        )
        LOGGER.info(
            "%s: visual dedup filtered=%d, non-task filtered=%d, temporal filtered=%d, candidates=%d, savings=%.2f%%",
            student_id,
            state.visual_dedup_skipped,
            state.non_task_skipped,
            state.temporal_dedup_skipped,
            state.candidate_frames_seen,
            manifest["summary"]["dedup_savings_percentage"],
        )
        return {
            "student_id": student_id,
            "status": "ok",
            "extraction_mode": modalities.extraction_mode,
            "video_match_strategy": video_resolution.strategy,
            "frames_extracted": len(state.extracted),
            "visual_duplicates_filtered": state.visual_dedup_skipped,
            "non_task_screens_filtered": state.non_task_skipped,
            "dedup_savings_percentage": manifest["summary"]["dedup_savings_percentage"],
            "manifest": repo_relative(manifest_path),
        }

    finally:
        if cap is not None:
            cap.release()
        gc.collect()


def student_dirs(audio_root: Path, students: list[str]) -> list[Path]:
    if students:
        dirs: list[Path] = []
        for student_id in students:
            student_path = audio_root / student_id
            if student_path.is_dir():
                dirs.append(student_path)
            else:
                LOGGER.warning("Student directory missing under audio-root: %s", student_path)
        return dirs
    return sorted([d for d in audio_root.iterdir() if d.is_dir()], key=lambda p: p.name.lower())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    try:
        import cv2  # noqa: F401
    except ImportError:
        LOGGER.error("opencv-python-headless is required: pip install -r requirements-layout.txt")
        return 1
    if args.enable_dedup and args.dedup_method == "phash":
        try:
            import imagehash  # noqa: F401
            from PIL import Image  # noqa: F401
        except ImportError:
            LOGGER.error(
                "ImageHash and Pillow are required for --dedup-method phash: "
                "pip install ImageHash Pillow"
            )
            return 1
    if args.phash_threshold < 0:
        LOGGER.error("--phash-threshold must be >= 0")
        return 1
    if args.mse_threshold < 0:
        LOGGER.error("--mse-threshold must be >= 0")
        return 1
    if args.motion_preview_width < 0:
        LOGGER.error("--motion-preview-width must be >= 0")
        return 1

    audio_root = args.audio_root.resolve()
    video_root = args.video_root.resolve() if args.video_root else None
    configure_compute_backend(args.compute_type)

    if video_root is not None and not video_root.is_dir():
        LOGGER.error("--video-root is not a directory: %s", video_root)
        return 1

    dirs = student_dirs(audio_root, args.students)
    if not dirs:
        LOGGER.error("No student directories under %s", audio_root)
        return 1

    results: list[dict[str, Any]] = []
    for student_dir in dirs:
        student_id = student_dir.name
        manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
        if args.skip_existing and manifest_is_complete(manifest_path):
            LOGGER.info("%s: skipping — existing manifest (%s)", student_id, manifest_path.name)
            results.append(
                {
                    "student_id": student_id,
                    "status": "skipped",
                    "reason": "existing_manifest",
                    "manifest": repo_relative(manifest_path),
                }
            )
            continue
        try:
            result = process_student(
                student_dir,
                audio_root=audio_root,
                video_root=video_root,
                max_width=args.max_width,
                motion_threshold=args.motion_threshold,
                cooldown_ms=args.cooldown_ms,
                boundary_epsilon=args.boundary_epsilon,
                jpeg_quality=args.jpeg_quality,
                speech_only=args.speech_only,
                dry_run=args.dry_run,
                max_frames=args.max_frames,
                compute_type=args.compute_type,
                enable_dedup=args.enable_dedup,
                dedup_method=args.dedup_method,
                phash_threshold=args.phash_threshold,
                mse_threshold=args.mse_threshold,
                filter_non_task_screens=args.filter_non_task_screens,
                non_task_templates=args.non_task_templates.resolve(),
                non_task_phash_threshold=args.non_task_phash_threshold,
                non_task_policy=args.non_task_policy,
                non_task_heuristics=args.non_task_heuristics,
                enable_codap_task_guard=args.enable_codap_task_guard,
                codap_task_templates=args.codap_task_templates.resolve(),
                colab_task_templates=args.colab_task_templates.resolve(),
                task_activity=args.task_activity,
                codap_task_phash_threshold=args.codap_task_phash_threshold,
                codap_task_heuristics=args.codap_task_heuristics,
                require_codap_content=args.require_codap_content,
                speech_gap_bypass_seconds=args.speech_gap_bypass_seconds,
                single_pass=args.single_pass,
                motion_preview_width=args.motion_preview_width,
                silent_motion_threshold=args.silent_motion_threshold,
                silent_screen_gap_fill_seconds=args.silent_screen_gap_fill_seconds,
                codap_gap_fill_seconds=args.codap_gap_fill_seconds,
            )
            results.append(result)
        except Exception as exc:
            LOGGER.error(
                "%s: isolated processing failure (%s: %s)",
                student_id,
                type(exc).__name__,
                exc,
            )
            if args.verbose:
                LOGGER.debug(traceback.format_exc())
            results.append(
                {
                    "student_id": student_id,
                    "status": "error",
                    "reason": type(exc).__name__,
                    "message": str(exc),
                }
            )
            gc.collect()

    ok = sum(1 for r in results if r.get("status") == "ok")
    skipped = sum(1 for r in results if r.get("status") == "skipped")
    errors = sum(1 for r in results if r.get("status") == "error")
    print(f"Processed {len(results)} students: ok={ok} skipped={skipped} errors={errors}")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
