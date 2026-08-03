"""Unit tests for speaker_merge v2."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from speaker_merge import (
    MergeRules,
    RoleMapping,
    build_role_mapping,
    is_focal_student_text,
    is_likely_teacher_text,
    merge_transcript_segments,
)


class SpeakerMergeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.rules = MergeRules()
        self.mapping = RoleMapping(
            teacher_speaker="SPEAKER_01",
            focal_speaker="SPEAKER_03",
            focal_pt_student_id="Amy",
            speaker_roles={
                "SPEAKER_01": "teacher",
                "SPEAKER_03": "student",
                "SPEAKER_07": "classmate",
            },
        )
        self.hybrid = {
            "speaker_labeling": {
                "teacher_speaker": "SPEAKER_01",
                "focal_student_speaker": "SPEAKER_03",
                "profiles": {
                    "SPEAKER_01": {"resolved_role": "teacher"},
                    "SPEAKER_03": {"resolved_role": "student"},
                    "SPEAKER_07": {"resolved_role": "classmate"},
                },
            }
        }
        self.hybrid_v2 = {
            "schema_version": "hybrid_diarization_v2",
            "speaker_labeling": {
                "teacher_speaker": "SPEAKER_01",
                "focal_student_speaker": "SPEAKER_03",
                "speakers": [
                    {"speaker_id": "SPEAKER_01", "role": "teacher"},
                    {"speaker_id": "SPEAKER_03", "role": "student"},
                    {"speaker_id": "SPEAKER_07", "role": "classmate"},
                ],
            },
            "timeline": [
                {"start": 200.0, "end": 202.0, "speaker_id": "SPEAKER_07"},
                {"start": 250.0, "end": 260.0, "speaker_id": "SPEAKER_01"},
            ],
        }

    def test_build_role_mapping(self) -> None:
        mapping = build_role_mapping(self.hybrid, "Amy")
        self.assertEqual(mapping.teacher_speaker, "SPEAKER_01")
        self.assertEqual(mapping.focal_speaker, "SPEAKER_03")

    def test_focal_hocam_priority(self) -> None:
        self.assertTrue(is_focal_student_text("Başlatmak hocam.", self.rules))
        self.assertFalse(is_likely_teacher_text("Başlatmak hocam.", self.rules))

    def test_instructional_teacher_block(self) -> None:
        transcript = [
            {"id": 100, "start": 209.12, "end": 211.12, "text": "Şimdi ne yapmamız lazım?"},
            {
                "id": 101,
                "start": 211.12,
                "end": 214.12,
                "text": "Sonuçta makine öğrencisi ya da yakay zekalı olsa",
            },
            {
                "id": 102,
                "start": 214.12,
                "end": 217.12,
                "text": "en temelki ne zaman bizim yaptığımız nedir bu işler?",
            },
            {"id": 103, "start": 217.12, "end": 218.12, "text": "Veri."},
        ]
        hybrid_segments = [
            {"start": 200.0, "end": 202.0, "speaker_id": "SPEAKER_07"},
            {"start": 250.0, "end": 260.0, "speaker_id": "SPEAKER_01", "text": "x"},
        ]
        merged = merge_transcript_segments(transcript, hybrid_segments, self.mapping, self.rules)
        roles = {s["id"]: s["speaker_role"] for s in merged}
        self.assertEqual(roles[100], "teacher")
        self.assertEqual(roles[101], "teacher")
        self.assertIn(roles[102], {"teacher", "unknown"})
        self.assertEqual(roles[103], "teacher")

    def test_gelmedi_hocam_is_student(self) -> None:
        transcript = [
            {"id": 1, "start": 10.0, "end": 12.0, "text": "Gelmedi hocam."},
        ]
        hybrid_segments = [
            {"start": 9.0, "end": 13.0, "speaker_id": "SPEAKER_01"},
        ]
        merged = merge_transcript_segments(transcript, hybrid_segments, self.mapping, self.rules)
        self.assertEqual(merged[0]["speaker_role"], "student")
        self.assertEqual(merged[0]["focal_pt_student_id"], "Amy")

    def test_build_role_mapping_v2(self) -> None:
        mapping = build_role_mapping(self.hybrid_v2, "Amy")
        self.assertEqual(mapping.teacher_speaker, "SPEAKER_01")
        self.assertEqual(mapping.speaker_roles["SPEAKER_07"], "classmate")

    def test_needs_review_flag(self) -> None:
        transcript = [
            {"id": 1, "start": 50.0, "end": 52.0, "text": "..."},
        ]
        merged = merge_transcript_segments(transcript, [], self.mapping, self.rules)
        self.assertTrue(merged[0].get("needs_review"))


if __name__ == "__main__":
    unittest.main()
