"""Tests for CODAP screen-recording transcript QA helpers."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts"))

from transcript_quality import (  # noqa: E402
    AudioAnalysis,
    assess_transcript,
    clean_segments,
    filter_segments,
    is_colloquial_preserved,
    is_hallucination_text,
    is_repetitive_hallucination_text,
)


def test_detects_subtitle_hallucination():
    assert is_hallucination_text("Altyazı M.K.")
    assert is_hallucination_text("Chinese Chinese Chinese")
    assert is_hallucination_text("Bational Chinese Chinese")
    assert is_hallucination_text("Chinese")
    assert is_hallucination_text("Bational")


def test_removes_burst_runs_and_invalid_timestamps():
    segments = [
        {"id": 1, "start": 0.0, "end": 1.0, "start_hms": "00:00:00.000", "end_hms": "00:00:01.000", "text": "Merhaba."},
        {"id": 2, "start": 1.0, "end": 1.5, "start_hms": "00:00:01.000", "end_hms": "00:00:01.500", "text": "Chinese"},
        {"id": 3, "start": 1.5, "end": 2.0, "start_hms": "00:00:01.500", "end_hms": "00:00:02.000", "text": "Chinese"},
        {"id": 4, "start": 2.0, "end": 2.5, "start_hms": "00:00:02.000", "end_hms": "00:00:02.500", "text": "Chinese"},
        {"id": 5, "start": 2.5, "end": 3.0, "start_hms": "00:00:02.500", "end_hms": "00:00:03.000", "text": "Chinese"},
        {"id": 6, "start": 3.0, "end": 2.5, "start_hms": "00:00:03.000", "end_hms": "00:00:02.500", "text": "Chinese"},
        {"id": 7, "start": 4.0, "end": 5.0, "start_hms": "00:00:04.000", "end_hms": "00:00:05.000", "text": "Emit fonksiyonu."},
    ]
    cleaned, stats = clean_segments(segments)
    assert stats["removed_total"] == 5
    assert len(cleaned) == 2
    assert cleaned[0]["text"] == "Merhaba."
    assert cleaned[1]["text"] == "Emit fonksiyonu."


def test_detects_massive_repetition_in_one_segment():
    text = "B Chinese Chinese Chinese " * 20
    assert is_hallucination_text(text)
    assert is_repetitive_hallucination_text("Bationalationalationalational")


def test_keeps_real_speech():
    assert not is_hallucination_text("Şimdi hedef değişkenimizi en üste koymamız lazım.")
    assert not is_hallucination_text("Emit fonksiyonunu çalıştırdınız mı?")
    assert not is_hallucination_text("Biri bir sınıf da sağlıklı alamayacak.")
    assert is_colloquial_preserved("Allah Allah.")
    assert is_colloquial_preserved("Dur dur!")


def test_spec_example_pipeline():
    """Canonical anomaly mix from the ASR post-processor spec."""
    segments = [
        {"id": 1, "start": 0.0, "end": 2.5, "text": "Allah Allah."},
        {"id": 2, "start": 2.5, "end": 32.5, "text": "Chinese Chinese Chinese"},
        {"id": 3, "start": 35.0, "end": 33.0, "text": "Bational"},
        {"id": 4, "start": 38.2, "end": 41.5, "text": "Biri bir sınıf da sağlıklı alamayacak."},
    ]
    cleaned, stats = clean_segments(segments)
    assert len(cleaned) == 2
    assert cleaned[0]["text"] == "Allah Allah."
    assert cleaned[1]["text"] == "Biri bir sınıf da sağlıklı alamayacak."
    assert stats["removed_total"] == 2


def test_shana_style_vacuum_after_valid_phrase():
    segments = [
        {"id": 1, "start": 88.0, "end": 89.5, "text": "Allah Allah."},
        {"id": 2, "start": 95.5, "end": 96.0, "text": "Chinese"},
        {"id": 3, "start": 96.0, "end": 96.5, "text": "Chinese"},
        {"id": 4, "start": 96.5, "end": 97.0, "text": "Chinese"},
        {"id": 5, "start": 96.5, "end": 97.0, "text": "Chinese"},
        {"id": 6, "start": 176.7, "end": 178.5, "text": "Biri bir sınıf da sağlıklı alamayacak."},
    ]
    cleaned, _ = clean_segments(segments)
    texts = [s["text"] for s in cleaned]
    assert "Allah Allah." in texts
    assert "Biri bir sınıf da sağlıklı alamayacak." in texts
    assert not any("Chinese" in t for t in texts)


def test_filter_segments_removes_hallucinations_and_renumbers():
    segments = [
        {"id": 1, "start": 0.0, "end": 2.0, "start_hms": "00:00:00.000", "end_hms": "00:00:02.000", "text": "Altyazı M.K."},
        {"id": 2, "start": 2.0, "end": 5.0, "start_hms": "00:00:02.000", "end_hms": "00:00:05.000", "text": "Threshold değerini değiştirdim."},
    ]
    cleaned, removed = filter_segments(segments)
    assert removed == 1
    assert len(cleaned) == 1
    assert cleaned[0]["id"] == 1
    assert "Threshold" in cleaned[0]["text"]


def test_assess_silent_transcript_as_no_speech():
    audio = AudioAnalysis(duration_seconds=5000, mean_volume_db=-50, silence_fraction=1.0, speech_fraction=0.0)
    transcript = {
        "duration_seconds": 5000,
        "segments": [{"id": 1, "start": 0, "end": 30, "text": "Altyazı M.K."}],
    }
    assessment = assess_transcript("Nadia", transcript, audio)
    assert assessment.status == "no_speech"
    assert "no_speech_in_audio" in assessment.issues


def test_assess_good_transcript_as_ok():
    audio = AudioAnalysis(duration_seconds=5000, mean_volume_db=-22, silence_fraction=0.01, speech_fraction=0.99)
    segments = [
        {"id": i, "start": i * 2.0, "end": i * 2.0 + 1.5, "text": f"Segment {i}"}
        for i in range(1, 700)
    ]
    transcript = {"duration_seconds": 5000, "segments": segments}
    assessment = assess_transcript("Amy", transcript, audio)
    assert assessment.status == "ok"
