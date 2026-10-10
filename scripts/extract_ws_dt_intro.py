#!/usr/bin/env python3
"""
Extract WS14 + WS15 (07 Nisan PDFs) for one or more students.

Each student's 10-page Xeno block and 10-page Titanic block are sent to Claude
separately. Results are saved as two worksheets:
  students/{student}/WS14/extraction.json
  students/{student}/WS15/extraction.json

Usage:
    python scripts/extract_ws_dt_intro.py Amy Bruno
    python scripts/extract_ws_dt_intro.py --remaining
    python scripts/extract_ws_dt_intro.py --all

Requires ANTHROPIC_API_KEY in the environment.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import anthropic
from pdf2image import convert_from_path

from ocr_pipeline import (
    DATA_DIR,
    DPI,
    PROMPT_DT_TITANIC,
    PROMPT_DT_XENO,
    NO_ANSWER_SENTINELS,
    detect_student_page_ranges,
    preprocess_for_handwriting,
)
from pipeline_schema import ITEM_IDS_DT_TITANIC, ITEM_IDS_DT_XENO, OCR_OUTPUT_DIR
from student_bundle import STUDENTS_DIR
from ws_dt_titanic_validation import export_ocr_output as export_titanic_ocr
from ws_dt_xeno_validation import export_ocr_output as export_xeno_ocr

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

XENO_PDF = "07 Nisan 2026 Çalışma Kâğıdı Xeno.pdf"
TITANIC_PDF = "07 Nisan 2026 Çalışma Kâğıdı Titanic.pdf"
OCR_MODEL = "claude-opus-4-8"
RUBRIC_BY_WORKSHEET = {
    "WS14": "rubrics/WS14_rubric.json",
    "WS15": "rubrics/WS15_rubric.json",
}
DONE_STUDENTS = frozenset({"Amy", "Bruno", "Helena", "Irma"})


def is_student_extracted(student_id: str) -> bool:
    """True when split Xeno + Titanic ocr_output files already exist."""
    xeno = OCR_OUTPUT_DIR / student_id / f"{student_id}_Worksheet_Xeno.json"
    titanic = OCR_OUTPUT_DIR / student_id / f"{student_id}_Worksheet_Titanic.json"
    return xeno.is_file() and titanic.is_file()


def remaining_students() -> list[str]:
    xeno_index = build_page_index(XENO_PDF)
    titanic_index = build_page_index(TITANIC_PDF)
    in_both = set(xeno_index) & set(titanic_index)
    return sorted(s for s in in_both if s not in DONE_STUDENTS and not is_student_extracted(s))


def is_answered(v: str) -> bool:
    return bool(v) and v not in NO_ANSWER_SENTINELS


def _images_to_b64(images) -> list[dict]:
    import base64
    from io import BytesIO
    content = []
    for img in images:
        proc = preprocess_for_handwriting(img)
        buf = BytesIO()
        proc.save(buf, format="JPEG", quality=92)
        b64 = base64.b64encode(buf.getvalue()).decode()
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
        })
    return content


def call_claude(client: anthropic.Anthropic, images, prompt: str) -> dict[str, Any]:
    content = _images_to_b64(images)
    content.append({"type": "text", "text": prompt})
    msg = client.messages.create(
        model=OCR_MODEL,
        max_tokens=4096,
        messages=[{"role": "user", "content": content}],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("json"):
            text = text[4:]
        text = text.rsplit("```", 1)[0].strip()
    return json.loads(text)


def build_page_index(pdf_name: str) -> dict[str, tuple[int, int]]:
    groups = detect_student_page_ranges(pdf_name)
    return {
        g["student"]: (g["start"], g["end"])
        for g in groups
        if g["student"] and not g["student"].startswith("unresolved")
    }


def extract_student(
    client: anthropic.Anthropic,
    student: str,
    xeno_index: dict[str, tuple[int, int]],
    titanic_index: dict[str, tuple[int, int]],
    xeno_images: list,
    titanic_images: list,
) -> Optional[tuple[dict[str, str], dict[str, str], dict[str, str]]]:
    if student not in titanic_index or student not in xeno_index:
        log.warning("Student %s missing from Xeno/Titanic PDF — skipping", student)
        return None

    xs, xe = xeno_index[student]
    ts, te = titanic_index[student]

    log.info("%s — Xeno pages %d-%d", student, xs, xe)
    xeno_raw = call_claude(client, xeno_images[xs - 1:xe], PROMPT_DT_XENO)
    time.sleep(1.0)

    log.info("%s — Titanic pages %d-%d", student, ts, te)
    titanic_raw = call_claude(client, titanic_images[ts - 1:te], PROMPT_DT_TITANIC)

    xeno_items = {iid: xeno_raw.get(iid, "(not_extracted)") for iid in ITEM_IDS_DT_XENO}
    titanic_items = {iid: titanic_raw.get(iid, "(not_extracted)") for iid in ITEM_IDS_DT_TITANIC}
    meta = {
        "xeno_snapshot": xeno_raw.get("ws_snapshot", ""),
        "titanic_snapshot": titanic_raw.get("ws_snapshot", ""),
        "xeno_page_notes": xeno_raw.get("page_notes", ""),
        "titanic_page_notes": titanic_raw.get("page_notes", ""),
    }
    return xeno_items, titanic_items, meta


def _coverage(items: dict[str, str]) -> dict[str, Any]:
    answered = sum(1 for v in items.values() if is_answered(v))
    blank_or_illegible = sum(1 for v in items.values() if v in {"(bos)", "(okunamiyor)"})
    missing = sum(1 for v in items.values() if v in {"(missing)", "(not_extracted)"})
    total = len(items)
    completion_rate = round(answered / total, 3) if total else 0.0
    g1_status = "fail" if missing == total else ("partial" if missing > 0 else "pass")
    g2_status = "fail" if completion_rate < 0.3 else ("partial" if completion_rate < 0.7 else "pass")
    return {
        "answered": answered,
        "total": total,
        "blank_or_illegible": blank_or_illegible,
        "missing": missing,
        "completion_rate": completion_rate,
        "g1_status": g1_status,
        "g2_status": g2_status,
    }


def build_extraction_record(
    student: str,
    worksheet: str,
    pdf_source: str,
    items: dict[str, str],
    *,
    ws_snapshot: str = "",
    page_notes: str = "(bos)",
) -> dict[str, Any]:
    cov = _coverage(items)
    return {
        "stage": "extraction",
        "student_id": student,
        "worksheet": worksheet,
        "student_name": student,
        "pdf_source": pdf_source,
        "rubric_ref": RUBRIC_BY_WORKSHEET.get(worksheet, ""),
        "gate_1_extraction": {
            "status": cov["g1_status"],
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "ocr_model": OCR_MODEL,
            "items": items,
            "raw_ocr": {},
        },
        "gate_2_validation": {
            "status": cov["g2_status"],
            "item_coverage": {k: cov[k] for k in ("answered", "total", "blank_or_illegible", "missing", "completion_rate")},
            "warnings": [],
            "student_snapshot": {
                "completion_rate": cov["completion_rate"],
                "engagement_level": (
                    "high" if cov["completion_rate"] >= 0.7
                    else "medium" if cov["completion_rate"] >= 0.4
                    else "low"
                ),
                "llm_observations": ws_snapshot,
                "page_notes": page_notes,
            },
        },
        "gate_3_scoring": {"status": "pending", "scored_at": None, "scoring_model": None, "items": {}},
        "gate_4_aicft": {"status": "pending", "level": None, "evidence": None},
    }


def save_record(student: str, worksheet: str, record: dict[str, Any]) -> Path:
    out_dir = STUDENTS_DIR / student / worksheet
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "extraction.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _require_api_key() -> None:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        log.error(
            "ANTHROPIC_API_KEY is not set. Export your key, then re-run:\n"
            "  export ANTHROPIC_API_KEY='...'\n"
            "  .venv/bin/python scripts/extract_ws_dt_intro.py --remaining"
        )
        raise SystemExit(1)


def run(students: list[str]) -> None:
    _require_api_key()
    client = anthropic.Anthropic()

    log.info("Converting Xeno PDF to images (DPI=%d)...", DPI)
    xeno_images = convert_from_path(str(DATA_DIR / XENO_PDF), dpi=DPI)
    log.info("Converting Titanic PDF to images (DPI=%d)...", DPI)
    titanic_images = convert_from_path(str(DATA_DIR / TITANIC_PDF), dpi=DPI)

    xeno_index = build_page_index(XENO_PDF)
    titanic_index = build_page_index(TITANIC_PDF)
    log.info("Xeno students: %s", sorted(xeno_index))
    log.info("Titanic students: %s", sorted(titanic_index))

    for student in students:
        log.info("=== %s ===", student)
        result = extract_student(
            client, student, xeno_index, titanic_index, xeno_images, titanic_images,
        )
        if result is None:
            continue
        xeno_items, titanic_items, meta = result

        xeno_record = build_extraction_record(
            student, "WS14", XENO_PDF, xeno_items,
            ws_snapshot=meta["xeno_snapshot"],
            page_notes=meta["xeno_page_notes"] or "(bos)",
        )
        titanic_record = build_extraction_record(
            student, "WS15", TITANIC_PDF, titanic_items,
            ws_snapshot=meta["titanic_snapshot"],
            page_notes=meta["titanic_page_notes"] or "(bos)",
        )

        xeno_path = save_record(student, "WS14", xeno_record)
        titanic_path = save_record(student, "WS15", titanic_record)
        log.info("Saved %s", xeno_path.relative_to(REPO_ROOT))
        log.info("Saved %s", titanic_path.relative_to(REPO_ROOT))

        export_xeno_ocr(
            student,
            xeno_items,
            ws_snapshot=meta["xeno_snapshot"],
            page_notes=meta["xeno_page_notes"] or "(bos)",
        )
        export_titanic_ocr(
            student,
            titanic_items,
            ws_snapshot=meta["titanic_snapshot"],
            page_notes=meta["titanic_page_notes"] or "(bos)",
        )
        log.info("Exported ocr_output (Xeno + Titanic only)")
        time.sleep(0.5)


def main() -> int:
    args = sys.argv[1:]
    if not args:
        pending = remaining_students()
        print("Usage: python scripts/extract_ws_dt_intro.py Amy Bruno  OR  --all  OR  --remaining")
        print(f"Pending ({len(pending)}): {', '.join(pending)}")
        return 1

    if "--remaining" in args:
        students = remaining_students()
        if not students:
            log.info("No remaining students to extract.")
            return 0
        log.info("Extracting %d remaining students: %s", len(students), students)
    elif "--all" in args:
        groups = detect_student_page_ranges(XENO_PDF)
        students = [
            g["student"]
            for g in groups
            if g["student"] and not g["student"].startswith("unresolved")
        ]
    else:
        students = [a for a in args if not a.startswith("--")]

    if not students:
        log.info("No students to process.")
        return 0

    run(students)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
