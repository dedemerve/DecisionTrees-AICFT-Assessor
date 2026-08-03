"""Unit tests for dynamic video visual deduplication and non-task filtering."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from dynamic_video_analytics import (
    DEFAULT_CODAP_TASK_TEMPLATE_DIR,
    DEFAULT_MOTION_PREVIEW_WIDTH,
    DEFAULT_NON_TASK_TEMPLATE_DIR,
    CodapContentAnalyzer,
    CodapTaskGuard,
    NonTaskScreenFilter,
    VisualDeduplicator,
    parse_args,
)


class VisualDeduplicatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.base = np.zeros((120, 160, 3), dtype=np.uint8)
        self.changed = self.base.copy()
        self.changed[20:100, 50:110] = 255

    def test_phash_rejects_duplicate_and_accepts_structural_change(self) -> None:
        deduplicator = VisualDeduplicator("phash", phash_threshold=4)

        self.assertTrue(deduplicator.should_save(self.base))
        self.assertFalse(deduplicator.should_save(self.base.copy()))
        self.assertTrue(deduplicator.should_save(self.changed))

    def test_mse_rejects_duplicate_and_accepts_change(self) -> None:
        deduplicator = VisualDeduplicator("mse", mse_threshold=5.0)

        self.assertTrue(deduplicator.should_save(self.base))
        self.assertFalse(deduplicator.should_save(self.base.copy()))
        self.assertTrue(deduplicator.should_save(self.changed))

    def test_invalid_or_empty_frames_are_rejected(self) -> None:
        deduplicator = VisualDeduplicator("mse")

        self.assertFalse(deduplicator.should_save(np.array([], dtype=np.uint8)))

    def test_cli_accepts_explicit_boolean_values(self) -> None:
        enabled = parse_args(["Amy", "--enable-dedup", "True"])
        disabled = parse_args(["Amy", "--enable-dedup", "False"])

        self.assertTrue(enabled.enable_dedup)
        self.assertFalse(disabled.enable_dedup)

    def test_single_pass_defaults_on(self) -> None:
        args = parse_args(["Amy"])
        self.assertTrue(args.single_pass)
        self.assertEqual(args.motion_preview_width, DEFAULT_MOTION_PREVIEW_WIDTH)

    def test_motion_preview_detects_large_change(self) -> None:
        from dynamic_video_analytics import motion_change_fraction, motion_preview_gray

        base = np.zeros((1080, 1920, 3), dtype=np.uint8)
        changed = base.copy()
        changed[200:800, 400:1500] = 255
        prev = motion_preview_gray(base, DEFAULT_MOTION_PREVIEW_WIDTH)
        curr = motion_preview_gray(changed, DEFAULT_MOTION_PREVIEW_WIDTH)
        self.assertGreater(motion_change_fraction(prev, curr), 0.05)


class CodapContentAnalyzerTests(unittest.TestCase):
    def test_codap_template_has_content_signals(self) -> None:
        if not DEFAULT_CODAP_TASK_TEMPLATE_DIR.is_dir():
            self.skipTest("CODAP task templates not installed")
        template_path = next(DEFAULT_CODAP_TASK_TEMPLATE_DIR.glob("*.jpg"), None)
        if template_path is None:
            self.skipTest("CODAP task templates missing")

        frame = cv2.imread(str(template_path))
        self.assertIsNotNone(frame)
        signals = CodapContentAnalyzer.analyze(frame)
        self.assertTrue(CodapContentAnalyzer.is_codap_task(signals))

    def test_google_drive_template_is_not_codap_task(self) -> None:
        template_path = DEFAULT_NON_TASK_TEMPLATE_DIR / "google_drive_folder.png"
        if not template_path.is_file():
            self.skipTest("google drive template missing")

        frame = cv2.imread(str(template_path))
        self.assertIsNotNone(frame)
        signals = CodapContentAnalyzer.analyze(frame)
        self.assertFalse(CodapContentAnalyzer.is_codap_task(signals))


class NonTaskScreenFilterTests(unittest.TestCase):
    def test_template_whatsapp_is_filtered(self) -> None:
        if not DEFAULT_NON_TASK_TEMPLATE_DIR.is_dir():
            self.skipTest("non-task templates not installed")
        template_path = DEFAULT_NON_TASK_TEMPLATE_DIR / "whatsapp_web.png"
        if not template_path.is_file():
            self.skipTest("whatsapp template missing")

        frame = cv2.imread(str(template_path))
        self.assertIsNotNone(frame)
        filt = NonTaskScreenFilter(DEFAULT_NON_TASK_TEMPLATE_DIR, phash_threshold=10)
        self.assertTrue(filt.should_skip(frame))

    def test_template_google_drive_is_filtered(self) -> None:
        if not DEFAULT_NON_TASK_TEMPLATE_DIR.is_dir():
            self.skipTest("non-task templates not installed")
        template_path = DEFAULT_NON_TASK_TEMPLATE_DIR / "google_drive_folder.png"
        if not template_path.is_file():
            self.skipTest("google drive template missing")

        frame = cv2.imread(str(template_path))
        self.assertIsNotNone(frame)
        filt = NonTaskScreenFilter(DEFAULT_NON_TASK_TEMPLATE_DIR, phash_threshold=10)
        self.assertTrue(filt.should_skip(frame))

    def test_synthetic_codap_like_frame_is_not_filtered(self) -> None:
        frame = np.full((720, 1280, 3), 245, dtype=np.uint8)
        frame[80:640, 120:1160] = (30, 120, 220)
        codap_guard = CodapTaskGuard(DEFAULT_CODAP_TASK_TEMPLATE_DIR, use_heuristics=True)
        filt = NonTaskScreenFilter(
            DEFAULT_NON_TASK_TEMPLATE_DIR,
            codap_guard=codap_guard,
            phash_threshold=10,
            require_codap_content=False,
        )
        self.assertFalse(filt.should_skip(frame))

    def test_codap_template_frame_is_never_filtered(self) -> None:
        if not DEFAULT_CODAP_TASK_TEMPLATE_DIR.is_dir():
            self.skipTest("CODAP task templates not installed")
        template_paths = list(DEFAULT_CODAP_TASK_TEMPLATE_DIR.glob("*.jpg"))
        if not template_paths:
            self.skipTest("CODAP task templates missing")

        codap_guard = CodapTaskGuard(DEFAULT_CODAP_TASK_TEMPLATE_DIR, phash_threshold=12)
        filt = NonTaskScreenFilter(
            DEFAULT_NON_TASK_TEMPLATE_DIR,
            codap_guard=codap_guard,
            phash_threshold=10,
        )
        for path in template_paths:
            frame = cv2.imread(str(path))
            self.assertIsNotNone(frame)
            self.assertFalse(filt.should_skip(frame), msg=f"CODAP template blocked: {path.name}")

    def test_synthetic_desktop_is_filtered_without_codap_guard(self) -> None:
        desk = Path(
            "data_sources_2026/codap_arbor_21april_audio/Amy/"
            "Amy_frames_427_precodapguard_backup_20260710_223804/frame_0194.jpg"
        )
        if not desk.is_file():
            self.skipTest("reference desktop frame missing")

        frame = cv2.imread(str(desk))
        self.assertIsNotNone(frame)
        filt = NonTaskScreenFilter(DEFAULT_NON_TASK_TEMPLATE_DIR, phash_threshold=10)
        match = filt.classify_without_guard(frame)
        self.assertTrue(match.is_non_task)
        self.assertIn("windows_desktop", match.reason)

    def test_motion_without_codap_content_is_skipped(self) -> None:
        frame = np.full((720, 1280, 3), 245, dtype=np.uint8)
        filt = NonTaskScreenFilter(
            DEFAULT_NON_TASK_TEMPLATE_DIR,
            codap_guard=CodapTaskGuard(DEFAULT_CODAP_TASK_TEMPLATE_DIR, use_heuristics=False),
            require_codap_content=True,
            phash_threshold=10,
        )
        self.assertTrue(
            filt.should_skip(frame, trigger_reason="motion_threshold_exceeded"),
        )
        self.assertTrue(
            filt.should_skip(frame, trigger_reason="speech_anchor_midpoint"),
        )

    def test_template_only_match_without_content_is_rejected(self) -> None:
        if not DEFAULT_CODAP_TASK_TEMPLATE_DIR.is_dir():
            self.skipTest("CODAP task templates not installed")
        drive = DEFAULT_NON_TASK_TEMPLATE_DIR / "google_drive_folder.png"
        if not drive.is_file():
            self.skipTest("google drive template missing")

        frame = cv2.imread(str(drive))
        self.assertIsNotNone(frame)
        guard = CodapTaskGuard(DEFAULT_CODAP_TASK_TEMPLATE_DIR, phash_threshold=12)
        match = guard.classify(frame)
        self.assertFalse(match.is_task)
        self.assertIn("not_codap", match.reason)

    def test_codap_guard_blocks_desktop_heuristic_on_real_templates(self) -> None:
        if not DEFAULT_CODAP_TASK_TEMPLATE_DIR.is_dir():
            self.skipTest("CODAP task templates not installed")
        template_paths = list(DEFAULT_CODAP_TASK_TEMPLATE_DIR.glob("*.jpg"))
        if not template_paths:
            self.skipTest("CODAP task templates missing")

        codap_guard = CodapTaskGuard(DEFAULT_CODAP_TASK_TEMPLATE_DIR, phash_threshold=12)
        filt = NonTaskScreenFilter(
            DEFAULT_NON_TASK_TEMPLATE_DIR,
            codap_guard=codap_guard,
            phash_threshold=10,
        )
        for path in template_paths:
            frame = cv2.imread(str(path))
            self.assertIsNotNone(frame)
            match = filt.classify(frame)
            self.assertFalse(match.is_non_task)
            self.assertTrue(
                match.reason.startswith(("codap_task_guard", "task_screen_guard")),
                msg=f"{path.name}: {match.reason}",
            )


if __name__ == "__main__":
    unittest.main()
