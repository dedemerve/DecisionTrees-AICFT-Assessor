#!/usr/bin/env python3
"""Build 2025 MMLA multimodal training samples from Word ground truth + motion frames.

Writes everything under training_datasets/2025/ (never mutates frozen data_sources_2025/).

Pipeline stages (independent, resume-friendly):
  1. parse-docx   — Analysis.docx → observation steps + deterministic labels
  2. emit-samples — align steps to extracted keyframes (provisional temporal;
                    optional --vision-align later)
  3. sequences    — stamp sequential learning-cycle patterns across steps

After finalize_2025_gold_alignment.py, run build_video_analysis_bundle.py to emit:
  - <id>_construct_scores.json        (B0-B13 session scoring)
  - <id>_expert_process_narrative.json (full uzman gözlem timeline)
  - <id>_video_analysis_bundle.json   (manifest + coverage audit)

Usage:
  python scripts/build_2025_mmla_training_dataset.py Ally Boris Henry
  python scripts/build_2025_mmla_training_dataset.py --all-with-video
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_2025 = REPO_ROOT / "data_sources_2025"
OUT_ROOT = REPO_ROOT / "training_datasets" / "2025"
SCORES_PATH = SRC_2025 / "all_students_2025_scores.json"

LOGGER = logging.getLogger("build_2025_mmla")

# ─────────────────────────────────────────────────────────────
# Deterministic label rules (Turkish observation language)
# ─────────────────────────────────────────────────────────────

STRATEGY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"rastgele|deneme yanılma|sırayla arttır|sırayla azalt|arttırılıp azalt", re.I), "Trial-and-error"),
    (re.compile(r"karar veremedim|hangisinin daha iyi|bilmiyorum", re.I), "Random guessing"),
    (re.compile(r"tuz|energy|enerji|protein|yağ|sugar|şeker|salt|fat|carbohydrate|doymuş|alan\s+bilgi|besin", re.I), "Domain-knowledge driven"),
]

COGNITIVE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"yanlış|hata|confusion|kavram\s*yanıl|recommendable or not.*yanlış", re.I), "MISCONCEPTION"),
    (re.compile(r"MCR|sensitivity|accuracy|confusion matrix|Classification Tree Records|metrik|performans", re.I), "EVALUATE"),
    (re.compile(r"threshold|movable value|Depth\s*\d|sürüklenir.*Depth|emit function", re.I), "TUNE"),
    (re.compile(r"grafik oluşturulur|x-eksen|y-eksen|Choosy|training ve test|dataset yüklen|keşf|incelen", re.I), "EXPLORE"),
]

LO_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"MCR.*sensitivity|neden.*seç|gerekçe|karşılaştır.*model|daha iyi.*model", re.I), "Deepen"),
    (re.compile(r"yeni bir karar ağacı|kendi|bağımsız|genellem", re.I), "Create"),
    (re.compile(r"yüklenir|sürüklenir|Emit function|Depth 1", re.I), "Acquire"),
]


def classify_observation(text: str) -> dict[str, str]:
    strategy = "Domain-knowledge driven"
    for pat, label in STRATEGY_RULES:
        if pat.search(text):
            strategy = label
            break

    cognitive = "EXPLORE"
    for pat, label in COGNITIVE_RULES:
        if pat.search(text):
            cognitive = label
            break

    lo = "None"
    for pat, label in LO_RULES:
        if pat.search(text):
            lo = label
            break

    return {
        "bilişsel_davranış_kategorisi": cognitive,
        "pedagojik_strateji": strategy,
        "unesco_ai_cft_level": lo,
    }


def stamp_sequence_patterns(steps: list[dict[str, Any]]) -> None:
    """Annotate contiguous Explore→Tune→Evaluate cycles across step indices."""
    cats = [s["labels"]["bilişsel_davranış_kategorisi"] for s in steps]
    for i, step in enumerate(steps):
        window = cats[max(0, i - 2) : i + 1]
        pattern = None
        if window == ["EXPLORE", "TUNE", "EVALUATE"]:
            pattern = "EXPLORE->TUNE->EVALUATE"
        elif len(window) >= 2 and window[-2:] == ["TUNE", "EVALUATE"]:
            pattern = "TUNE->EVALUATE"
        elif len(window) >= 2 and window[-2:] == ["EXPLORE", "TUNE"]:
            pattern = "EXPLORE->TUNE"
        step["sequence_pattern"] = pattern


def _docx_images_in_body_order(doc: Any) -> list[tuple[int, bytes, str]]:
    """Return (paragraph_index, blob, ext) for every embedded image in body order."""
    from docx.oxml.ns import qn

    out: list[tuple[int, bytes, str]] = []
    para_i = -1
    for child in doc.element.body.iterchildren():
        if child.tag != qn("w:p"):
            continue
        para_i += 1
        for blip in child.findall(".//" + qn("a:blip")):
            rid = blip.get(qn("r:embed"))
            if not rid or rid not in doc.part.rels:
                continue
            part = doc.part.rels[rid].target_part
            ctype = getattr(part, "content_type", "") or ""
            if "png" in ctype:
                ext = "png"
            elif "jpeg" in ctype or "jpg" in ctype:
                ext = "jpg"
            else:
                ext = "bin"
            out.append((para_i, part.blob, ext))
    return out


def extract_docx_screenshots(
    docx_path: Path,
    out_dir: Path,
    student_id: str,
) -> list[dict[str, Any]]:
    """Dump expert-embedded screenshots (gold visuals) next to training outputs."""
    from docx import Document

    doc = Document(str(docx_path))
    shot_dir = out_dir / f"{student_id}_docx_screenshots"
    shot_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for ord_i, (para_i, blob, ext) in enumerate(_docx_images_in_body_order(doc)):
        name = f"docx_shot_{ord_i:04d}.{ext}"
        path = shot_dir / name
        path.write_bytes(blob)
        records.append(
            {
                "shot_index": ord_i,
                "paragraph_index": para_i,
                "path": str(path.relative_to(out_dir)),
                "bytes": len(blob),
            }
        )
    return records


def parse_analysis_docx(path: Path) -> list[dict[str, Any]]:
    """Parse observation texts and attach each embedded image to the nearest preceding text.

    Analysis.docx layout is typically: narrative paragraph → screenshot → …
    Zip-by-order mis-assigns when some paragraphs have no image (dialogue-only).
    Preceding-text pairing keeps GOLD exact for every available screenshot.
    """
    from docx import Document
    from docx.oxml.ns import qn

    doc = Document(str(path))
    steps: list[dict[str, Any]] = []
    step_by_para: dict[int, int] = {}

    # Body-order walk: text paragraphs become steps; images bind to last text step.
    para_i = -1
    last_step_idx: int | None = None
    shot_ord = 0
    image_bindings: list[tuple[int, int]] = []  # (step_index, shot_ord)

    for child in doc.element.body.iterchildren():
        if child.tag != qn("w:p"):
            continue
        para_i += 1
        texts = [t.text for t in child.findall(".//" + qn("w:t")) if t.text]
        text = "".join(texts).strip()
        blips = child.findall(".//" + qn("a:blip"))

        if text:
            labels = classify_observation(text)
            step_idx = len(steps)
            steps.append(
                {
                    "step_index": step_idx,
                    "paragraph_index": para_i,
                    "uzman_nitel_gözlemi": text,
                    "labels": labels,
                    "docx_shot_index": None,
                    "docx_shot_indices": [],
                    "ai_cft_evidence_justification": (
                        f"Uzman gözlemi '{labels['bilişsel_davranış_kategorisi']}' "
                        f"/ '{labels['pedagojik_strateji']}' / LO={labels['unesco_ai_cft_level']} "
                        f"olarak kural tabanlı eşlendi; Word gömülü ekran görüntüsü birincil görsel GT."
                    ),
                }
            )
            step_by_para[para_i] = step_idx
            last_step_idx = step_idx

        for _blip in blips:
            if last_step_idx is None:
                continue
            image_bindings.append((last_step_idx, shot_ord))
            shot_ord += 1

    # Primary shot = first image bound to the step (document order).
    for step_idx, shot_i in image_bindings:
        step = steps[step_idx]
        step["docx_shot_indices"].append(shot_i)
        if step["docx_shot_index"] is None:
            step["docx_shot_index"] = shot_i

    stamp_sequence_patterns(steps)
    return steps


def load_scores(student_id: str) -> dict[str, Any] | None:
    if not SCORES_PATH.is_file():
        return None
    data = json.loads(SCORES_PATH.read_text(encoding="utf-8"))
    for row in data.get("students") or []:
        if row.get("student_id") == student_id:
            return row
    return None


def find_video(student_id: str) -> Path | None:
    sdir = SRC_2025 / student_id
    if not sdir.is_dir():
        return None
    video_exts = {".webm", ".mp4", ".mkv", ".mov", ".m4v", ".avi", ".wmv", ".mpeg", ".mpg"}
    cands: list[Path] = []
    for pat in (
        "*Screen_Recording*",
        "*screen_recording*",
        "*.webm",
        "*.mp4",
        "*.MP4",
        "*.mov",
        "*.MOV",
        "*.mkv",
        "*.m4v",
        "*.avi",
        "*.wmv",
    ):
        cands.extend(sdir.glob(pat))
    videos = sorted(
        {
            p.resolve()
            for p in cands
            if p.is_file() and p.suffix.lower() in video_exts
        }
    )
    return videos[0] if videos else None


def load_manifest(out_dir: Path, student_id: str) -> dict[str, Any] | None:
    path = out_dir / f"{student_id}_video_extraction_manifest.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def nearest_frame(frames: list[dict[str, Any]], target_s: float) -> dict[str, Any] | None:
    if not frames:
        return None
    return min(frames, key=lambda f: abs(float(f["source_timestamp_seconds"]) - target_s))


def infer_visual_stub(text: str) -> dict[str, Any]:
    active = "arbor_tree"
    if re.search(r"grafik|x-eksen|y-eksen|scatter", text, re.I):
        active = "codap_graph"
    elif re.search(r"Classification Tree Records|CTR|tablo", text, re.I):
        active = "codap_table"
    elements: list[str] = []
    for term, el in [
        (r"Emit function", "emit_button"),
        (r"movable value", "movable_value"),
        (r"threshold", "threshold_control"),
        (r"Confusion|accuracy|MCR|sensitivity", "performance_metrics"),
        (r"Depth\s*\d", "tree_depth_node"),
        (r"Choosy|training|test", "train_test_split"),
    ]:
        if re.search(term, text, re.I):
            elements.append(el)
    feat = None
    m = re.search(
        r"(of which Saturated Fat|of which Sugar|Energy|Fat|Salt|Protein|Carbohydrate|Label)",
        text,
        re.I,
    )
    if m:
        feat = m.group(1)
    return {
        "active_panel": active,
        "visible_elements": elements,
        "feature_selections": {"attribute": feat, "value": None},
        "visual_source": "observation_text_heuristic",
    }


def build_training_samples(
    student_id: str,
    steps: list[dict[str, Any]],
    video_path: Path,
    manifest: dict[str, Any] | None,
    scores: dict[str, Any] | None,
    docx_shots: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    frames = list((manifest or {}).get("frames") or [])
    duration = float((manifest or {}).get("video_duration_seconds") or 0.0)
    if duration <= 0 and frames:
        duration = max(float(f["source_timestamp_seconds"]) for f in frames) + 1.0
    docx_shots = docx_shots or []

    samples: list[dict[str, Any]] = []
    n = max(len(steps), 1)
    for step in steps:
        idx = step["step_index"]
        # Provisional temporal prior: spread steps evenly across the session,
        # then snap to nearest motion keyframe when available.
        target_s = (idx + 0.5) / n * duration if duration > 0 else float(idx)
        frame = nearest_frame(frames, target_s) if frames else None
        frame_id = frame.get("frame_id") if frame else f"step_{idx:04d}"
        ts_s = float(frame["source_timestamp_seconds"]) if frame else target_s
        frame_num = int(re.search(r"(\d+)$", str(frame_id)).group(1)) if frame and re.search(r"(\d+)$", str(frame_id)) else idx

        shot_i = step.get("docx_shot_index")
        docx_shot = docx_shots[shot_i] if isinstance(shot_i, int) and 0 <= shot_i < len(docx_shots) else None
        if docx_shot and frame:
            align = "docx_screenshot_primary+motion_temporal_secondary"
        elif docx_shot:
            align = "docx_screenshot_order_zip"
        elif frame:
            align = "provisional_temporal_nearest_motion"
        else:
            align = "observation_only"

        visual = infer_visual_stub(step["uzman_nitel_gözlemi"])
        visual["expert_screenshot"] = docx_shot["path"] if docx_shot else None
        sample = {
            "training_sample_id": f"2025_{student_id}_step_{idx:04d}",
            "metadata": {
                "cohort_year": 2025,
                "student_id": student_id,
                "video_source": video_path.name,
                "frame_number": frame_num,
                "timestamp_ms": int(round(ts_s * 1000)) if frame else None,
                "frame_id": frame_id if frame else None,
                "frame_image": (
                    f"{student_id}_frames/{frame_id}.jpg" if frame else None
                ),
                "expert_screenshot": docx_shot["path"] if docx_shot else None,
                "alignment_method": align,
                "observation_step_index": idx,
            },
            "multimodal_inputs": {
                "görsel_ekran_durumu": visual,
                "sistem_logu": {
                    "last_action": None,
                    "action_sequence_last_30s": [],
                    "note": "2025 CODAP event CSV yok; log alanları .codap / gelecek log hizasina birakildi.",
                },
            },
            "ground_truth_labels": {
                "uzman_nitel_gözlemi": step["uzman_nitel_gözlemi"],
                "bilişsel_davranış_kategorisi": step["labels"]["bilişsel_davranış_kategorisi"],
                "pedagojik_strateji": step["labels"]["pedagojik_strateji"],
                "unesco_ai_cft_level": step["labels"]["unesco_ai_cft_level"],
                "ai_cft_evidence_justification": step["ai_cft_evidence_justification"],
                "sequence_pattern": step.get("sequence_pattern"),
            },
            "session_rubric_scores": (scores or {}).get("scores"),
            "session_notes": (scores or {}).get("notes"),
        }
        samples.append(sample)
    return samples


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def process_student(student_id: str) -> dict[str, Any]:
    src = SRC_2025 / student_id
    docx = src / f"{student_id}_Analysis.docx"
    out_dir = OUT_ROOT / student_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if not docx.is_file():
        return {"student_id": student_id, "status": "skipped", "reason": "missing_analysis_docx"}

    video = find_video(student_id)
    if video is None:
        return {"student_id": student_id, "status": "skipped", "reason": "missing_video"}

    steps = parse_analysis_docx(docx)
    stamp_sequence_patterns(steps)
    scores = load_scores(student_id)
    manifest = load_manifest(out_dir, student_id)
    docx_shots = extract_docx_screenshots(docx, out_dir, student_id)

    steps_payload = {
        "student_id": student_id,
        "cohort_year": 2025,
        "source_docx": str(docx.relative_to(REPO_ROOT)),
        "video_source": video.name,
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "step_count": len(steps),
        "docx_screenshot_count": len(docx_shots),
        "steps_with_docx_shot": sum(1 for s in steps if s.get("docx_shot_index") is not None),
        "frames_in_manifest": len((manifest or {}).get("frames") or []),
        "session_rubric": scores,
        "docx_screenshots": docx_shots,
        "observation_steps": steps,
    }
    write_json(out_dir / f"{student_id}_observation_steps.json", steps_payload)

    samples = build_training_samples(
        student_id, steps, video, manifest, scores, docx_shots=docx_shots
    )
    write_json(out_dir / f"{student_id}_mmla_training_samples.json", {
        "student_id": student_id,
        "cohort_year": 2025,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sample_count": len(samples),
        "alignment_method": samples[0]["metadata"]["alignment_method"] if samples else None,
        "docx_screenshots_available": len(docx_shots),
        "frames_available": bool(manifest),
        "samples": samples,
    })
    write_jsonl(out_dir / f"{student_id}_mmla_training_samples.jsonl", samples)

    label_hist: dict[str, int] = {}
    for s in steps:
        k = s["labels"]["bilişsel_davranış_kategorisi"]
        label_hist[k] = label_hist.get(k, 0) + 1

    summary = {
        "student_id": student_id,
        "status": "ok",
        "steps": len(steps),
        "samples": len(samples),
        "docx_screenshots": len(docx_shots),
        "frames_available": len((manifest or {}).get("frames") or []),
        "cognitive_label_histogram": label_hist,
        "output_dir": str(out_dir.relative_to(REPO_ROOT)),
    }
    write_json(out_dir / f"{student_id}_training_build_summary.json", summary)
    LOGGER.info("[%s] %d steps → %d samples (frames=%s)", student_id, len(steps), len(samples), summary["frames_available"])
    return summary


def discover_students_with_video() -> list[str]:
    out: list[str] = []
    for p in sorted(SRC_2025.iterdir()):
        if not p.is_dir() or p.name.startswith("."):
            continue
        if find_video(p.name) and (p / f"{p.name}_Analysis.docx").is_file():
            out.append(p.name)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build 2025 MMLA training dataset from Word + frames")
    ap.add_argument("students", nargs="*", help="Student IDs (default: pilot list or --all-with-video)")
    ap.add_argument("--all-with-video", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.all_with_video:
        targets = discover_students_with_video()
    elif args.students:
        targets = args.students
    else:
        targets = ["Ally", "Boris", "Henry"]

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    results = [process_student(sid) for sid in targets]
    cohort = {
        "cohort_year": 2025,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "students": results,
        "note": (
            "Frame images live under training_datasets/2025/<id>/<id>_frames/. "
            "Alignment is provisional_temporal_nearest_motion until vision aligner runs."
        ),
    }
    write_json(OUT_ROOT / "cohort_training_build_summary.json", cohort)
    ok = sum(1 for r in results if r.get("status") == "ok")
    LOGGER.info("Done: %d/%d students ok → %s", ok, len(results), OUT_ROOT)
    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
