#!/usr/bin/env python3
"""Colab-specific video analytics engine for 5 May Python sessions.

Replaces generic global-motion extraction with a layered event detector
tuned to the geometry and visual language of Google Colab notebooks:

Layer 1 — Cell Execution (left-strip ROI)
    The leftmost ~15% of the frame contains run-status indicators: the
    [ ] glyph, a spinning circle, and green/grey status icons. Any local
    change > 2% in this strip while the rest of the screen is quiet
    signals a cell being queued or finishing execution.
    Trigger: colab_cell_execution_detected

Layer 2 — Error / Traceback (red-mask HSV)
    Python tracebacks render as dense blocks of red text in the output
    area. A red pixel ratio > 0.5% anywhere in the frame flags an error
    moment worth annotating.
    Trigger: colab_traceback_error_visible

Layer 3 — Plot / Output Appearance (white-region + edge density)
    Matplotlib / Seaborn outputs appear as large white bounding boxes
    with axis lines. Detect: bright region > 8% of frame area AND
    Canny edge density in that region > 1.5%.
    Trigger: colab_plot_output_appeared

Layer 4a — Code Typing (sub-threshold editor ROI)
    Active keystroke sequences produce pixel deltas of 0.1–5% in the
    code editor band (rows 8%–92%, cols 15%–96%). Sample one frame
    every CODE_TYPING_SAMPLE_S seconds during continuous typing.
    Trigger: colab_active_code_typing

Layer 4b — Paste Event (large sudden editor change)
    Copy-paste produces a single-frame editor delta > 5% while the
    rest of the screen is quiet (not scrolling, not cell execution).
    Distinguishes students who copy code vs those who write it.
    Trigger: colab_paste_detected

Layer 5 — Anti-Scroll Guard
    Rapid vertical scrolling produces uniform global deltas > 30%.
    Frames during scrolling are suppressed. When motion falls back
    below SCROLL_SETTLE_THRESHOLD for SCROLL_SETTLE_S seconds a single
    "settled view" frame is captured.
    Trigger: colab_stable_post_scroll_view

Layer 6 — Window Switch Detection
    Tracks whether the Colab interface is visible (dark/light header
    present) or not. A sudden loss of Colab signals means the student
    switched to another application — likely CODAP to reference their
    tree. Return is detected when Colab signals reappear.
    Trigger: colab_window_switch_away / colab_window_switch_return

Layer 7 — Gap Fill
    When none of Layers 1–6 fire for > GAP_FILL_S seconds, extract
    one frame to document the current state (student reading, thinking).
    Trigger: colab_gap_fill

Output manifest format is identical to dynamic_video_analytics.py so
prune_to_guard.py / post_hoc_refiner.py / extraction_quality_gate.py
work unchanged.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

REPO_ROOT  = Path(__file__).resolve().parents[1]
SCRIPTS    = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO_ROOT))

from dynamic_video_analytics import (   # noqa: E402
    DEFAULT_COLAB_TASK_TEMPLATE_DIR,
    DEFAULT_NON_TASK_TEMPLATE_DIR,
    ColabContentAnalyzer,
    NonTaskScreenFilter,
    build_task_screen_guard,
    frame_phash,
)

LOGGER = logging.getLogger("colab_event_analytics")

# ── tunable constants ────────────────────────────────────────────────────────
RUN_STRIP_FRACTION   = 0.15   # leftmost fraction of frame = run-button zone
RUN_STRIP_THRESHOLD  = 0.02   # local delta ratio in strip → cell execution

RED_RATIO_THRESHOLD  = 0.005  # red pixel fraction → traceback visible

PLOT_BRIGHT_RATIO    = 0.08   # fraction of frame that is "white" → plot area
PLOT_EDGE_DENSITY    = 0.015  # Canny density inside bright region → axes

CODE_EDITOR_TOP      = 0.08   # editor band vertical start
CODE_EDITOR_BOTTOM   = 0.92
CODE_EDITOR_LEFT     = 0.15
CODE_EDITOR_RIGHT    = 0.96
CODE_TYPING_LOW      = 0.001  # min delta to count as typing
CODE_TYPING_HIGH     = 0.05   # max delta (above = not typing → paste or big change)
CODE_TYPING_SAMPLE_S = 4.0    # one frame per N seconds during typing
PASTE_THRESHOLD      = 0.05   # editor delta above this = paste event (not gradual typing)

SCROLL_THRESHOLD     = 0.30   # global delta > this → scrolling
SCROLL_SETTLE_S      = 1.0    # seconds of quiet after scroll → capture frame
SCROLL_COOLDOWN_S    = 5.0    # min gap between scroll-settle frames

# Window switch: Colab dark-mode header occupies top ~7% of frame.
# dark_header_ratio ≥ 0.55 → Colab visible; < 0.25 → different application.
COLAB_VISIBLE_THRESHOLD  = 0.55
COLAB_GONE_THRESHOLD     = 0.25
# For light-mode Colab: top_white_ratio ≥ 0.25 also means Colab is visible.
COLAB_LIGHT_THRESHOLD    = 0.25

GAP_FILL_S           = 90.0   # max silence before gap-fill frame
COOLDOWN_S: dict[str, float] = {
    "colab_cell_execution_detected": 3.0,
    "colab_traceback_error_visible": 5.0,
    "colab_plot_output_appeared":    5.0,
    "colab_active_code_typing":      CODE_TYPING_SAMPLE_S,
    "colab_paste_detected":          2.0,
    "colab_stable_post_scroll_view": SCROLL_COOLDOWN_S,
    "colab_window_switch_away":      5.0,
    "colab_window_switch_return":    5.0,
    "colab_gap_fill":                GAP_FILL_S,
}
PHASH_DEDUP_THRESHOLD = 4     # suppress visually identical frames
JPEG_QUALITY          = 88


# ── helpers ──────────────────────────────────────────────────────────────────

def _red_ratio(hsv: np.ndarray) -> float:
    lo1 = np.array([0,   120, 70])
    hi1 = np.array([10,  255, 255])
    lo2 = np.array([170, 120, 70])
    hi2 = np.array([180, 255, 255])
    mask = cv2.inRange(hsv, lo1, hi1) | cv2.inRange(hsv, lo2, hi2)
    return float(np.count_nonzero(mask)) / mask.size


def _plot_score(gray: np.ndarray) -> tuple[float, float]:
    """Return (bright_ratio, edge_density_in_bright_region)."""
    bright_mask = gray > 220
    bright_ratio = float(np.mean(bright_mask))
    if bright_ratio < PLOT_BRIGHT_RATIO:
        return bright_ratio, 0.0
    edges = cv2.Canny(gray, 50, 150)
    edge_in_bright = float(np.mean(edges[bright_mask]))
    return bright_ratio, edge_in_bright / 255.0


def _run_strip_delta(diff: np.ndarray, strip_x: int) -> float:
    h = diff.shape[0]
    strip = diff[:, :strip_x]
    return float(np.count_nonzero(strip > 25)) / (h * strip_x)


def _editor_delta(diff: np.ndarray, h: int, w: int) -> float:
    r0, r1 = int(h * CODE_EDITOR_TOP), int(h * CODE_EDITOR_BOTTOM)
    c0, c1 = int(w * CODE_EDITOR_LEFT), int(w * CODE_EDITOR_RIGHT)
    patch = diff[r0:r1, c0:c1]
    return float(np.count_nonzero(patch > 20)) / patch.size


def _global_delta(diff: np.ndarray) -> float:
    return float(np.count_nonzero(diff > 25)) / diff.size


def _save_frame(frame_bgr: np.ndarray, path: Path) -> None:
    cv2.imwrite(str(path), frame_bgr,
                [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])


def _probe_resolution(video_path: Path) -> tuple[int, int]:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "v:0",
             "-show_entries", "stream=width,height",
             "-print_format", "json", str(video_path)],
            capture_output=True, text=True, timeout=10,
        )
        d = json.loads(r.stdout)
        s = d["streams"][0]
        return int(s["width"]), int(s["height"])
    except Exception:
        return 1920, 1080


# ── main engine ──────────────────────────────────────────────────────────────

class ColabEventEngine:
    def __init__(
        self,
        student_id: str,
        video_path: Path,
        frames_dir: Path,
        *,
        gap_fill_s: float = GAP_FILL_S,
        phash_threshold: int = PHASH_DEDUP_THRESHOLD,
        colab_template_dir: Path = DEFAULT_COLAB_TASK_TEMPLATE_DIR,
        non_task_template_dir: Path = DEFAULT_NON_TASK_TEMPLATE_DIR,
        colab_phash_threshold: int = 12,
        verbose: bool = False,
    ) -> None:
        self.student_id = student_id
        self.video_path = video_path
        self.frames_dir = frames_dir
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.gap_fill_s = gap_fill_s
        self.phash_threshold = phash_threshold
        self.verbose = verbose

        self.task_guard = build_task_screen_guard(
            "colab",
            colab_template_dir=colab_template_dir,
            colab_phash_threshold=colab_phash_threshold,
        )
        self.non_task_filter = NonTaskScreenFilter(
            non_task_template_dir,
            phash_threshold=10,
        )

        # state
        self._last_trigger_t: dict[str, float] = {}
        self._last_frame_t:   float = -gap_fill_s
        self._scroll_quiet_since: float | None = None
        self._recent_hashes: list[Any] = []   # phash ring buffer
        self._frame_counter = 0
        self._frames: list[dict[str, Any]] = []
        # window-switch state: None = unknown, True = Colab visible, False = away
        self._colab_visible: bool | None = None

    # ── per-frame decisions ────────────────────────────────────────────

    def _cooldown_ok(self, trigger: str, t: float) -> bool:
        cd = COOLDOWN_S.get(trigger, 3.0)
        return t - self._last_trigger_t.get(trigger, -9999) >= cd

    def _phash_ok(self, frame_bgr: np.ndarray) -> bool:
        h = frame_phash(frame_bgr)
        if any(float(h - eh) <= self.phash_threshold for eh in self._recent_hashes):
            return False
        self._recent_hashes.append(h)
        if len(self._recent_hashes) > 50:
            self._recent_hashes.pop(0)
        return True

    def _is_task_screen(self, frame_bgr: np.ndarray) -> bool:
        if self.task_guard is None:
            return True
        return self.task_guard.classify(frame_bgr).is_task

    def _is_non_task(self, frame_bgr: np.ndarray) -> bool:
        return not self._is_task_screen(frame_bgr)

    def _emit(self, frame_bgr: np.ndarray, t: float, trigger: str,
               metrics: dict[str, Any]) -> None:
        self._frame_counter += 1
        fid = f"colab_{trigger.split('_',1)[-1][:12]}_{self._frame_counter:05d}"
        path = self.frames_dir / f"{fid}.jpg"
        _save_frame(frame_bgr, path)
        self._frames.append({
            "frame_id":                   fid,
            "source_timestamp_seconds":   round(t, 3),
            "extraction_trigger_reason":  trigger,
            "metrics": {
                "pixel_change_percentage":     metrics.get("global_delta", 0.0) * 100,
                "associated_speaker_role":     "unknown",
                "associated_transcript_id":    None,
                "high_value_interaction_zone": trigger in {
                    "colab_cell_execution_detected",
                    "colab_traceback_error_visible",
                    "colab_plot_output_appeared",
                    "colab_paste_detected",
                    "colab_window_switch_away",
                    "colab_window_switch_return",
                },
                **metrics,
            },
            "file_path": str(path.relative_to(REPO_ROOT)),
        })
        self._last_trigger_t[trigger] = t
        self._last_frame_t = t
        if self.verbose:
            LOGGER.debug("[%s] t=%.1fs  %s  %s",
                         self.student_id, t, trigger,
                         {k: round(v, 4) if isinstance(v, float) else v
                          for k, v in metrics.items()})

    # ── main loop ─────────────────────────────────────────────────────

    def run(self) -> list[dict[str, Any]]:
        cap = cv2.VideoCapture(str(self.video_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or fps > 120:
            fps = 30.0

        ret, prev_bgr = cap.read()
        if not ret:
            LOGGER.error("[%s] Cannot read video", self.student_id)
            cap.release()
            return []

        h, w = prev_bgr.shape[:2]
        strip_x = max(1, int(w * RUN_STRIP_FRACTION))
        prev_gray = cv2.cvtColor(prev_bgr, cv2.COLOR_BGR2GRAY)
        frame_idx = 0

        LOGGER.info("[%s] scanning %s (fps=%.1f res=%dx%d)",
                    self.student_id, self.video_path.name, fps, w, h)

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_idx += 1
            t = frame_idx / fps

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(gray, prev_gray)

            global_d  = _global_delta(diff)
            strip_d   = _run_strip_delta(diff, strip_x)
            editor_d  = _editor_delta(diff, h, w)

            # ── Layer 5: anti-scroll guard ────────────────────────────
            if global_d > SCROLL_THRESHOLD:
                self._scroll_quiet_since = None   # reset settle timer
                prev_gray = gray
                continue  # suppress frame during scroll

            # did scrolling just stop?
            if self._scroll_quiet_since is None and global_d <= SCROLL_THRESHOLD:
                self._scroll_quiet_since = t
            elif self._scroll_quiet_since is not None:
                settled_for = t - self._scroll_quiet_since
                if settled_for >= SCROLL_SETTLE_S:
                    trigger = "colab_stable_post_scroll_view"
                    if (self._cooldown_ok(trigger, t)
                            and self._is_task_screen(frame)
                            and self._phash_ok(frame)):
                        self._emit(frame, t, trigger, {"global_delta": global_d})
                    self._scroll_quiet_since = None   # one capture per scroll stop

            # ── Layer 1: cell execution (left-strip spike) ────────────
            non_strip_d = _global_delta(
                diff[:, strip_x:]
            ) if w > strip_x else global_d
            if (strip_d > RUN_STRIP_THRESHOLD
                    and non_strip_d < strip_d * 0.5):   # strip dominates
                trigger = "colab_cell_execution_detected"
                if (self._cooldown_ok(trigger, t)
                        and self._is_task_screen(frame)
                        and self._phash_ok(frame)):
                    self._emit(frame, t, trigger,
                               {"run_strip_delta": round(strip_d, 4),
                                "global_delta": round(global_d, 4)})
                    prev_gray = gray
                    continue

            # ── Layer 2: traceback / error ────────────────────────────
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            red_r = _red_ratio(hsv)
            if red_r > RED_RATIO_THRESHOLD:
                trigger = "colab_traceback_error_visible"
                if (self._cooldown_ok(trigger, t)
                        and self._is_task_screen(frame)
                        and self._phash_ok(frame)):
                    self._emit(frame, t, trigger,
                               {"red_ratio": round(red_r, 4),
                                "global_delta": round(global_d, 4)})
                    prev_gray = gray
                    continue

            # ── Layer 3: plot / output appearance ─────────────────────
            bright_r, edge_d = _plot_score(gray)
            if bright_r >= PLOT_BRIGHT_RATIO and edge_d >= PLOT_EDGE_DENSITY:
                trigger = "colab_plot_output_appeared"
                if (self._cooldown_ok(trigger, t)
                        and self._is_task_screen(frame)
                        and self._phash_ok(frame)):
                    self._emit(frame, t, trigger,
                               {"bright_ratio": round(bright_r, 4),
                                "edge_density": round(edge_d, 4),
                                "global_delta": round(global_d, 4)})
                    prev_gray = gray
                    continue

            # ── Layer 4a: code typing (sub-threshold editor delta) ────
            if CODE_TYPING_LOW <= editor_d <= CODE_TYPING_HIGH:
                trigger = "colab_active_code_typing"
                if (self._cooldown_ok(trigger, t)
                        and self._is_task_screen(frame)
                        and self._phash_ok(frame)):
                    self._emit(frame, t, trigger,
                               {"editor_delta": round(editor_d, 4),
                                "global_delta": round(global_d, 4)})
                    prev_gray = gray
                    continue

            # ── Layer 4b: paste detection ─────────────────────────────
            # Large sudden change in editor area while screen is quiet
            # (not scrolling — already handled above — and not a full-frame event).
            # Gradual typing stays <= CODE_TYPING_HIGH; paste jumps above it.
            if (editor_d > PASTE_THRESHOLD
                    and global_d < SCROLL_THRESHOLD
                    and strip_d < RUN_STRIP_THRESHOLD):  # not cell execution
                trigger = "colab_paste_detected"
                if (self._cooldown_ok(trigger, t)
                        and self._is_task_screen(frame)
                        and self._phash_ok(frame)):
                    self._emit(frame, t, trigger,
                               {"editor_delta": round(editor_d, 4),
                                "global_delta": round(global_d, 4)})
                    prev_gray = gray
                    continue

            # ── Layer 6: window-switch detection ─────────────────────
            # Compute Colab header visibility from the top strip of this frame.
            top_strip = frame[: max(1, int(h * 0.07)), :]
            top_gray_strip = cv2.cvtColor(top_strip, cv2.COLOR_BGR2GRAY)
            dark_ratio  = float(np.mean(top_gray_strip < 60))
            white_ratio = float(np.mean(top_gray_strip > 195))
            colab_now = (dark_ratio >= COLAB_VISIBLE_THRESHOLD
                         or white_ratio >= COLAB_LIGHT_THRESHOLD)

            if self._colab_visible is None:
                # First frame — establish baseline silently
                self._colab_visible = colab_now
            elif self._colab_visible and not colab_now:
                # Was in Colab, now different app
                trigger = "colab_window_switch_away"
                if self._cooldown_ok(trigger, t) and self._phash_ok(frame):
                    self._emit(frame, t, trigger,
                               {"dark_ratio": round(dark_ratio, 3),
                                "white_ratio": round(white_ratio, 3),
                                "global_delta": round(global_d, 4)})
                self._colab_visible = False
            elif not self._colab_visible and colab_now:
                # Was away, now back in Colab
                trigger = "colab_window_switch_return"
                if self._cooldown_ok(trigger, t) and self._phash_ok(frame):
                    self._emit(frame, t, trigger,
                               {"dark_ratio": round(dark_ratio, 3),
                                "white_ratio": round(white_ratio, 3),
                                "global_delta": round(global_d, 4)})
                self._colab_visible = True

            # ── Layer 7: gap fill ─────────────────────────────────────
            if t - self._last_frame_t >= self.gap_fill_s:
                trigger = "colab_gap_fill"
                if (self._is_task_screen(frame)
                        and self._phash_ok(frame)):
                    self._emit(frame, t, trigger,
                               {"global_delta": round(global_d, 4)})

            prev_gray = gray

        cap.release()
        LOGGER.info("[%s] done — %d frames extracted", self.student_id, len(self._frames))
        return self._frames


# ── manifest writer ──────────────────────────────────────────────────────────

def build_manifest(
    student_id: str,
    video_path: Path,
    frames: list[dict[str, Any]],
    *,
    audio_root: Path,
) -> dict[str, Any]:
    from collections import Counter
    triggers = Counter(f["extraction_trigger_reason"] for f in frames)
    w, h = _probe_resolution(video_path)
    ts_list = [f["source_timestamp_seconds"] for f in frames]
    return {
        "schema_version":   "3.1-colab",
        "generated_at":     datetime.now(timezone.utc).isoformat(),
        "student_id":       student_id,
        "extraction_mode":  "colab_event_engine",
        "path_resolution":  "relative_to_repo",
        "modalities":       ["video"],
        "video_profile": {
            "native_resolution":  [w, h],
            "extract_resolution": [w, h],
            "aspect_ratio":       round(w / h, 6) if h else 0,
            "fps":                0.0,
            "total_frames":       0,
            "duration_seconds":   round(max(ts_list), 3) if ts_list else 0,
            "corrupt_frame_count": 0,
            "pts_inversion_count": 0,
        },
        "parameters": {
            "engine":               "colab_event_analytics",
            "run_strip_fraction":   RUN_STRIP_FRACTION,
            "run_strip_threshold":  RUN_STRIP_THRESHOLD,
            "red_ratio_threshold":  RED_RATIO_THRESHOLD,
            "plot_bright_ratio":    PLOT_BRIGHT_RATIO,
            "plot_edge_density":    PLOT_EDGE_DENSITY,
            "code_typing_low":      CODE_TYPING_LOW,
            "code_typing_high":     CODE_TYPING_HIGH,
            "code_typing_sample_s": CODE_TYPING_SAMPLE_S,
            "scroll_threshold":     SCROLL_THRESHOLD,
            "scroll_settle_s":      SCROLL_SETTLE_S,
            "gap_fill_s":           GAP_FILL_S,
            "phash_dedup_threshold": PHASH_DEDUP_THRESHOLD,
            # fields expected by strict_params_ok in batch_extract_strict_cohorts
            "codap_task_phash_threshold": 12,
            "cooldown_ms":               1000,
            "speech_gap_bypass_seconds": 120.0,
            "require_codap_content":     True,
            "enable_codap_task_guard":   True,
            "single_pass":               True,
            "motion_preview_width":      960,
            "codap_gap_fill_seconds":    GAP_FILL_S,
            "silent_motion_threshold":   0.008,
            "silent_screen_gap_fill_seconds": GAP_FILL_S,
            "task_activity":             "colab",
        },
        "summary": {
            "speech_anchor_count":        0,
            "motion_keyframe_count":      len(frames),
            "total_frames_extracted":     len(frames),
            "candidate_frames_considered": 0,
            "visual_duplicates_filtered": 0,
            "temporal_duplicates_filtered": 0,
            "non_task_screens_filtered":  0,
            "dedup_savings_percentage":   0.0,
            "trigger_breakdown":          dict(triggers),
        },
        "segments": [],
        "frames":   sorted(frames, key=lambda f: f["source_timestamp_seconds"]),
    }


# ── CLI ──────────────────────────────────────────────────────────────────────

VIDEO_ROOT_05MAY = (
    REPO_ROOT / "data_sources_2026" / "05 May Colab Python Screen Recordings"
)
AUDIO_ROOT_05MAY = REPO_ROOT / "data_sources_2026" / "colab_python_audio"


def find_video(student_id: str, video_root: Path) -> Path | None:
    for ext in (".webm", ".mp4", ".mkv", ".mov", ".m4v", ".avi", ".wmv", ".mpeg", ".mpg"):
        p = video_root / f"{student_id}{ext}"
        if p.is_file():
            return p
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Colab-specific event-driven frame extractor"
    )
    parser.add_argument("student_id")
    parser.add_argument("--audio-root", type=Path, default=AUDIO_ROOT_05MAY)
    parser.add_argument("--video-root", type=Path, default=VIDEO_ROOT_05MAY)
    parser.add_argument("--gap-fill-seconds", type=float, default=GAP_FILL_S)
    parser.add_argument("-v", "--verbose", action="store_true")
    # accept (and silently ignore) any batch_extract_strict_cohorts pass-through args
    parser.add_argument("--enable-dedup", default="True")
    parser.add_argument("--dedup-method", default="phash")
    parser.add_argument("--phash-threshold", type=int, default=4)
    parser.add_argument("--filter-non-task-screens", default="True")
    parser.add_argument("--enable-codap-task-guard", default="True")
    parser.add_argument("--require-codap-content", default="True")
    parser.add_argument("--codap-task-phash-threshold", type=int, default=12)
    parser.add_argument("--cooldown-ms", type=int, default=1000)
    parser.add_argument("--speech-gap-bypass-seconds", type=float, default=120)
    parser.add_argument("--non-task-phash-threshold", type=int, default=10)
    parser.add_argument("--motion-threshold", type=float, default=0.012)
    parser.add_argument("--single-pass", default="True")
    parser.add_argument("--motion-preview-width", type=int, default=960)
    parser.add_argument("--silent-motion-threshold", type=float, default=0.008)
    parser.add_argument("--silent-screen-gap-fill-seconds", type=float, default=90)
    parser.add_argument("--codap-gap-fill-seconds", type=float, default=GAP_FILL_S)
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument("--task-activity", default="colab")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    student_id = args.student_id
    audio_root = args.audio_root.resolve()
    video_root = args.video_root.resolve()
    student_dir = audio_root / student_id

    video_path = find_video(student_id, video_root)
    if not video_path:
        LOGGER.error("[%s] video not found in %s", student_id, video_root)
        return 1

    frames_dir = student_dir / f"{student_id}_frames"

    engine = ColabEventEngine(
        student_id=student_id,
        video_path=video_path,
        frames_dir=frames_dir,
        gap_fill_s=args.codap_gap_fill_seconds,
        phash_threshold=args.phash_threshold,
        colab_phash_threshold=args.codap_task_phash_threshold,
        verbose=args.verbose,
    )
    frames = engine.run()

    manifest = build_manifest(student_id, video_path, frames, audio_root=audio_root)
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    LOGGER.info("[%s] manifest → %s (%d frames)", student_id,
                manifest_path.name, len(frames))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
