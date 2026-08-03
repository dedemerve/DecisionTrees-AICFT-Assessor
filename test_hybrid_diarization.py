"""Unit tests for hybrid_diarization role matrix (no WhisperX required)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from hybrid_diarization import (
    apply_hybrid_roles,
    build_speaker_profiles,
    compute_hybrid_role_matrix,
)


class HybridRoleMatrixTests(unittest.TestCase):
    def test_teacher_duration_and_lexical_win(self) -> None:
        segments = [
            {
                "start": 0.0,
                "end": 120.0,
                "text": "Arkadaşlar şimdi birinci soruya geçelim bakalım.",
                "speaker_id": "SPEAKER_00",
            },
            {
                "start": 120.5,
                "end": 121.2,
                "text": "Evet hocam.",
                "speaker_id": "SPEAKER_01",
            },
            {
                "start": 130.0,
                "end": 140.0,
                "text": "Hocam ben yapamadım çalışmıyor bende.",
                "speaker_id": "SPEAKER_01",
            },
        ]
        profiles = build_speaker_profiles(segments)
        matrix = compute_hybrid_role_matrix(profiles)
        self.assertEqual(matrix.teacher_speaker, "SPEAKER_00")
        self.assertEqual(matrix.focal_student_speaker, "SPEAKER_01")
        labeled = apply_hybrid_roles(segments, matrix)
        self.assertEqual(labeled[0]["speaker_role"], "teacher")
        self.assertEqual(labeled[1]["speaker_role"], "student")
        self.assertEqual(labeled[1]["speaker_method"], "hybrid_matrix_duration_and_lexical")
        self.assertGreater(labeled[0]["speaker_confidence"], 0.5)

    def test_no_unknown_after_global_binding(self) -> None:
        segments = [
            {"start": 0.0, "end": 5.0, "text": "Tamam.", "speaker_id": "SPEAKER_00"},
            {"start": 6.0, "end": 8.0, "text": "Hocam.", "speaker_id": "SPEAKER_01"},
        ]
        matrix = compute_hybrid_role_matrix(build_speaker_profiles(segments))
        labeled = apply_hybrid_roles(segments, matrix)
        for seg in labeled:
            self.assertIn(seg["speaker_role"], {"teacher", "student", "classmate"})
            self.assertNotEqual(seg["speaker_role"], "unknown")


if __name__ == "__main__":
    unittest.main()
