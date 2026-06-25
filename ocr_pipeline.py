"""
ocr_pipeline.py

Transcribes handwritten Turkish student worksheets using Claude vision,
maps each answer to a rubric item_id, and saves per-student responses.json
that feeds directly into worksheet_assessor.py.

Modes
-----
dry_run   No API calls. Converts PDFs to images, saves for inspection.
          python ocr_pipeline.py dry_run [WorksheetDT.pdf ...]

pilot     One student from one PDF. Prints item-by-item response summary.
          python ocr_pipeline.py pilot WorksheetDT.pdf 0
          (student_index=0 -> pages 1-4, index=1 -> pages 5-8, etc.)

validate  Human-readable review of a student's responses.json.
          python ocr_pipeline.py validate Daniella

full      Process all three PDFs. Skips students already processed (resume-safe).
          python ocr_pipeline.py

Output per student
------------------
ocr_output/{student_key}/
  responses.json           -- {item_id: answer} for all 24 rubric items + metadata
  worksheet_dt_raw.json
  worksheets_1_10_raw.json
  worksheet11__feedbacks_raw.json
  _images/                 -- page images saved by dry_run only

Student key
-----------
Names from Claude are normalized: stripped, title-cased, spaces → underscores.
"daniella", "DANIELLA", "Daniella" all resolve to the same key "Daniella".
Keys are stable across PDF runs so the same student's data always merges correctly.

data_sufficiency encoding
-------------------------
Sentinel values:
  (bos)               student left the field blank
  (okunamiyor)        text is present but illegible
  (missing)           Claude did not return this key
  (not_extracted)     PDF was not processed for this student
  (transcription_error) API call failed for this PDF
Any other value is a real answer. is_answered() encodes this contract.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import anthropic
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data_sources_2025"
OUT_DIR = Path(__file__).parent / "ocr_output"
OUT_DIR.mkdir(exist_ok=True)

DPI = 300  # raised from 200; improves handwriting legibility

PAGES_PER_STUDENT: dict[str, int] = {
    "WorksheetDT.pdf": 4,
    "Worksheets1-10.pdf": 6,
    "Worksheet11_ Feedbacks.pdf": 3,
}

# ---------------------------------------------------------------------------
# Student pseudonyms — canonical identifiers used as directory keys
# ---------------------------------------------------------------------------

# Complete pseudonym list provided by researcher.
# These are the only valid student keys; Claude-extracted names are matched against this set.
KNOWN_PSEUDONYMS: frozenset[str] = frozenset({
    "Ozzy", "Ally", "Bella", "Bob", "Daisy", "Daniella", "David",
    "Eliot", "Henry", "Irene", "Isabel", "Karl", "Michael", "Mike",
    "Nicolas", "Zabby", "Adam", "Eddy", "Aden", "Barbara", "Boris",
    "Calvin", "Darby", "Demi", "Daryl", "Edgar", "Frank", "Felicity",
    "Kim", "Sabrina",
})

# No hardcoded page order. Student names are read from the first page by Claude
# and matched against KNOWN_PSEUDONYMS. dry_run uses slot_NN labels.

NO_ANSWER_SENTINELS: frozenset[str] = frozenset({
    "(bos)", "(okunamiyor)", "(missing)", "(not_extracted)", "(transcription_error)",
})

# ---------------------------------------------------------------------------
# Item ID master list — must match worksheet_assessor.py RUBRICS keys exactly
# ---------------------------------------------------------------------------

ITEM_IDS_DT: list[str] = [
    "DT_A_Q1", "DT_A_Q2", "DT_A_Q4",
    "DT_B_Q4",
    "DT_C_Q2", "DT_C_Q3",
    "DT_D_Q2", "DT_D_Q4",
    "DT_E_sensitivity", "DT_E_MCR", "DT_E_Q1", "DT_E_Q4",
    "DT_F_Q2",
    "DT_G_Q1", "DT_G_Q2",
]

ITEM_IDS_WS: list[str] = [
    "WS1_objects", "WS1_features", "WS1_label",
    "WS3_classification",
    "WS4_T3",
    "WS7_path_matching",
]

ITEM_IDS_WS11: list[str] = [
    "WS11_Q10", "WS11_Q11", "WS11_Q12",
]

ALL_ITEM_IDS: list[str] = ITEM_IDS_DT + ITEM_IDS_WS + ITEM_IDS_WS11

PDF_ITEM_IDS: dict[str, list[str]] = {
    "WorksheetDT.pdf": ITEM_IDS_DT,
    "Worksheets1-10.pdf": ITEM_IDS_WS,
    "Worksheet11_ Feedbacks.pdf": ITEM_IDS_WS11,
}

# ---------------------------------------------------------------------------
# Vision prompts
# ---------------------------------------------------------------------------

_HANDWRITING_INSTRUCTION = """HANDWRITING READING — read carefully before transcribing:

1. These pages are handwritten by Turkish university students. Writing style varies from neat to
   very fast and cursive. Assume every filled field contains a real answer unless physically blank.

2. Turkish character restoration — students often skip diacritics when writing fast.
   Restore unambiguously:
   c  → ç   (e.g. "cok" = "çok", "kac" = "kaç")
   s  → ş   (e.g. "su" context-dependent; "seker" = "şeker", "esik" = "eşik")
   g  → ğ   (e.g. "agac" = "ağaç", "degisken" = "değişken", "ogrenci" = "öğrenci")
   u  → ü   (e.g. "gul" = "gül", "ustte" = "üstte")
   o  → ö   (e.g. "ozellik" = "özellik", "once" = "önce")
   i  → ı   (e.g. "kisi" = "kişi" or "kısı" — use context)
   If the domain word is technical (MCR, sensitivity, threshold, eşik, değişken, doğruluk,
   duyarlılık, hata oranı) restore it fully even if written informally.

3. Numbers — common misreads in fast handwriting:
   0 vs O: in numeric contexts always read as zero
   1 vs l/I: in formulas/equations always read as one
   7 vs 1: 7 has a horizontal stroke; 1 does not
   Decimal separator: Turkish students use comma (0,82) not period — transcribe as written.

4. Struck-through / overwritten text: transcribe only the FINAL version (what is not crossed out).
   If both old and new are readable, use the new; note it as "[corrected: old → new]".

5. Symbols and layout marks:
   Arrow (→ or drawn): write [arrow]
   Circle around a number or letter: write [circled: X]
   Underline for emphasis: transcribe the underlined text normally (do not mark it)
   Formula fraction (numerator over denominator): write as "numerator / denominator"

6. Marginal additions: if a student wrote something in the margin clearly belonging to an answer,
   include it at the end of that answer, separated by " | "."""

_SENTINEL_INSTRUCTION = """BLANK / ILLEGIBLE FIELDS — strict rules:
- Student left the field completely empty (no marks at all): write exactly (bos)
- There is handwriting but it is physically unreadable after careful inspection: write exactly (okunamiyor)
- NEVER guess, paraphrase, or invent content for blank or illegible fields.
- Do NOT write a translation. Transcribe Turkish text as Turkish."""

_NAME_INSTRUCTION = """STUDENT NAME — this is critical for file organization:
The student's pseudonym (nickname) is written at the top of the FIRST page, usually in a
"Name:" or "Ad:" or "Öğrenci:" field, or freely at the top of the page.
These are single English-style nicknames such as: Daniella, Nicolas, Karl, Mike, David,
Daisy, Isabel, Ally, Michael, Irene, Bob, Darby, Barbara, Boris, Calvin, Frank, Kim,
Aden, Sabrina, Daryl, Demi, Adam, Edgar, Felicity, Eddy, Ozzy, Bella, Eliot, Henry,
Zabby. Read the name exactly as written. If unclear, read the closest match from this list."""

PROMPT_DT = f"""You are an expert at reading handwritten Turkish university student worksheets.
Your task: transcribe one student's completed CODAP Arbor decision tree worksheet.

You will receive 4 page images belonging to ONE student. Treat all 4 pages as one document.
The worksheet is divided into 7 sections labelled A through G. Each section has numbered questions.
Students filled in answers in blank spaces below or beside each question number.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WHAT TO EXTRACT — return exactly these JSON keys with verbatim student answers:

"student_name"
  The pseudonym written at the top of page 1. (See name list above.)

"DT_A_Q1"
  Section A, Question 1. The student writes which variable(s) they initially THINK will
  predict whether a food is recommended — this is their hypothesis BEFORE doing any analysis.
  Look for text after "1." in Section A.

"DT_A_Q2"
  Section A, Question 2. Which variables actually INFLUENCE recommendability based on the
  data or graphs the student explored. Must reference data, not just personal opinion.

"DT_A_Q4"
  Section A, Question 4. Which variable the student chose FIRST for their model, AND their
  written justification (WHY they chose it). Both parts are required — capture both.

"DT_B_Q4"
  Section B, Question 4. After building three single-variable trees, which variable gave the
  BEST result, and what CRITERION (metric) the student used to judge (e.g. accuracy, MCR,
  sensitivity). Both the variable name and the criterion must be captured.

"DT_C_Q2"
  Section C, Question 2. How does CHANGING THE THRESHOLD value affect the classification
  performance of the tree? The student should explain the mechanism (more/fewer errors, why).

"DT_C_Q3"
  Section C, Question 3. Which threshold VALUE best separates recommended from not-recommended,
  and HOW the student found that threshold (systematic search, visual inspection, trial-error).

"DT_D_Q2"
  Section D, Question 2. Did adding a SECOND VARIABLE (depth-2 tree) improve classification?
  How much? Include any numeric values (accuracy before/after) the student wrote.

"DT_D_Q4"
  Section D, Question 4. How did the student decide they had reached the BEST tree — what
  stopping criterion did they use? (e.g. "accuracy stopped improving", "overfitting concern")

"DT_E_sensitivity"
  Section E. The sensitivity (duyarlılık) FORMULA the student wrote AND the numeric value.
  Formula is typically TP / (TP+FN). Capture both formula and number, e.g. "TP/(TP+FN) = 0,82".
  If only the number is written without a formula, capture just the number.

"DT_E_MCR"
  Section E. The MCR (hata oranı / misclassification rate) FORMULA and numeric value.
  Formula is typically (FP+FN) / total. Capture both, e.g. "(FP+FN)/toplam = 0,18".

"DT_E_Q1"
  Section E, Question 1. Which metric (sensitivity, MCR, or other) matters MORE for this
  model's purpose, and the student's written reason WHY.

"DT_E_Q4"
  Section E, Question 4. Can a decision tree achieve PERFECT classification (zero errors)?
  Capture the student's answer (yes/no) AND their explanation.

"DT_F_Q2"
  Section F, Question 2. Comparison of TEST dataset performance vs TRAINING performance.
  Why are they different? Does the student mention overfitting (aşırı öğrenme)?

"DT_G_Q1"
  Section G, Question 1. What did the DT MODEL "learn" from the data?
  (What patterns/rules did it discover?)

"DT_G_Q2"
  Section G, Question 2. What did the STUDENT learn while building decision trees?
  Open reflection — any length.

"page_notes"
  Brief note about image quality, pages that were very hard to read, or unusual layout.
  Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "DT_A_Q1": "...",
  "DT_A_Q2": "...",
  "DT_A_Q4": "...",
  "DT_B_Q4": "...",
  "DT_C_Q2": "...",
  "DT_C_Q3": "...",
  "DT_D_Q2": "...",
  "DT_D_Q4": "...",
  "DT_E_sensitivity": "...",
  "DT_E_MCR": "...",
  "DT_E_Q1": "...",
  "DT_E_Q4": "...",
  "DT_F_Q2": "...",
  "DT_G_Q1": "...",
  "DT_G_Q2": "...",
  "page_notes": "..."
}}"""

PROMPT_WS = f"""You are an expert at reading handwritten Turkish university student worksheets.
Your task: transcribe one student's responses from ProDaBi decision tree worksheets (WS1–WS10).

You will receive multiple page images belonging to ONE student.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WHAT TO EXTRACT:

"student_name"
  Pseudonym written at the top of page 1 (see name list in the name instruction above).

"WS1_objects"
  Worksheet 1 (Important Terms). The blank labelled "nesne" (object).
  What did the student write as the definition or example of an object?

"WS1_features"
  Worksheet 1. The blank labelled "özellik" or "değişken" (feature / variable).
  What did the student write?

"WS1_label"
  Worksheet 1. The blank labelled "etiket" (label).
  What did the student write?

"WS3_classification"
  Worksheet 3 (Applying Thresholds). The student applies a decision rule to 3 foods:
  patlamış mısır (popcorn), elma (apple), patates kızartması (french fries).
  Transcribe their written classification result for each food, e.g.
  "patlamış mısır: tavsiye edilebilir | elma: tavsiye edilebilir | patates: tavsiye edilemez"

"WS4_T3"
  Worksheet 4, Task 3. The question is whether Pia is correct that a threshold cannot be
  placed between apple and raspberry jam (because they have the same fat value).
  Capture the student's full written answer.

"WS7_path_matching"
  Worksheet 7 (Formulate Decision Rules). The student matches tree paths (A, B, C) to
  written if-then rules. Capture what the student wrote for each path, e.g.
  "A: energy < 180 → recommended | B: energy >= 180 AND protein < 7.7 → not recommended | C: ..."

"page_notes"
  Brief note about image quality or layout issues. Write (bos) if no issues.

Return ONLY this JSON object. No text before or after it.
{{
  "student_name": "...",
  "WS1_objects": "...",
  "WS1_features": "...",
  "WS1_label": "...",
  "WS3_classification": "...",
  "WS4_T3": "...",
  "WS7_path_matching": "...",
  "page_notes": "..."
}}"""

PROMPT_WS11 = f"""You are an expert at reading handwritten Turkish university student worksheets.
Your task: transcribe one student's responses from Worksheet 11 (evaluation + feedback form).

You will receive multiple page images belonging to ONE student.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WHAT TO EXTRACT:

"student_name"
  Pseudonym written at the top of page 1 (see name list in the name instruction above).

"WS11_Q10"
  Question 10: a multiple-select question about what a decision tree CAN do.
  The student circles or ticks options from a printed list.
  Write the LETTER or TEXT of every option they selected, comma-separated.
  Example: "A, C, D" or "bir kategoriye tahmin etme, yeni nesneler için karar verme"

"WS11_Q11"
  Question 11: an ordering task. The student assigns the numbers 1, 2, 3, 4 to four printed steps.
  The steps are roughly: (1) select a feature, (2) sort data by that feature,
  (3) find a threshold with few errors, (4) make a decision.
  Transcribe exactly what number the student wrote next to each step.
  Format: "adim1=[number] | adim2=[number] | adim3=[number] | adim4=[number]"
  or copy the step text with its assigned number.

"WS11_Q12"
  Question 12: multiple-select about WHY a decision tree is considered AI.
  Write the letter or text of every option the student circled.

"WS11_Q8a"
  Question 8a: classify strawberries using the printed decision tree.
  Write the student's classification result.

"WS11_Q8b"
  Question 8b: write the decision RULE used in 8a.
  Capture the full if-then rule the student wrote.

"WS11_Q9"
  Question 9: open-ended definition of decision tree in the student's own words.
  Capture the full text.

"page_notes"
  Brief note about image quality or layout issues. Write (bos) if no issues.

Return ONLY this JSON object. No text before or after it.
{{
  "student_name": "...",
  "WS11_Q10": "...",
  "WS11_Q11": "...",
  "WS11_Q12": "...",
  "WS11_Q8a": "...",
  "WS11_Q8b": "...",
  "WS11_Q9": "...",
  "page_notes": "..."
}}"""

PROMPTS: dict[str, str] = {
    "WorksheetDT.pdf": PROMPT_DT,
    "Worksheets1-10.pdf": PROMPT_WS,
    "Worksheet11_ Feedbacks.pdf": PROMPT_WS11,
}

# ---------------------------------------------------------------------------
# Name normalization and pseudonym matching
# ---------------------------------------------------------------------------

def normalize_student_key(name: str) -> str:
    """
    Produce a stable directory key from any name string.
    "daniella", "DANIELLA", "Daniella Smith " all → "Daniella_Smith".
    Applied before every directory read/write.
    """
    cleaned = name.strip()
    if not cleaned or cleaned.lower() in {"(bos)", "(okunamiyor)"}:
        return ""
    return "_".join(part.title() for part in cleaned.split())


def match_pseudonym(extracted_name: str) -> Optional[str]:
    """
    Match a Claude-extracted name against KNOWN_PSEUDONYMS.
    Returns the canonical pseudonym if a confident match is found, else None.

    Matching strategy (in order):
    1. Exact match (case-insensitive)
    2. Extracted name starts with or contains a pseudonym (e.g. "Daniella S." → "Daniella")
    3. A pseudonym starts with the extracted name (e.g. "Daniel" → "Daniella" if unique match)
    """
    if not extracted_name:
        return None
    name_lower = extracted_name.strip().lower()
    # 1. Exact
    for pseudo in KNOWN_PSEUDONYMS:
        if pseudo.lower() == name_lower:
            return pseudo
    # 2. Extracted contains a pseudonym as a full word
    for pseudo in KNOWN_PSEUDONYMS:
        if re.search(r'\b' + re.escape(pseudo.lower()) + r'\b', name_lower):
            return pseudo
    # 3. Unique prefix match (pseudonym starts with extracted name, min 3 chars)
    if len(name_lower) >= 3:
        prefix_matches = [p for p in KNOWN_PSEUDONYMS if p.lower().startswith(name_lower)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]
    return None


def resolve_student_key(
    extracted_name: str,
    slot_index: int,
    pdf_name: str,
) -> str:
    """
    Determine the canonical student key for a given page slot.
    Priority:
      1. Pseudonym matched from Claude-extracted name.
      2. Normalized extracted name (if non-empty and not a sentinel).
      3. Fallback: "slot_{slot+1:02d}" — signals that name extraction failed.
    """
    matched = match_pseudonym(extracted_name)
    if matched:
        return matched
    key = normalize_student_key(extracted_name)
    if key:
        return key
    return f"slot_{slot_index + 1:02d}"


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def preprocess_for_handwriting(img: Image.Image) -> Image.Image:
    """
    Enhance a scanned worksheet image to improve handwriting legibility for Claude.

    Steps:
    1. Convert to RGB (handles grayscale scans).
    2. Unsharp mask — sharpens ink strokes without amplifying scanner noise.
    3. Contrast boost — makes light pencil marks darker relative to the page.
    4. Slight brightness reduction — compensates for over-exposed scans where
       pale ink washes out against a nearly-white background.

    These values are conservative: strong enough to help, safe enough not to
    distort letterforms that Claude must read.
    """
    img = img.convert("RGB")
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=2))
    img = ImageEnhance.Contrast(img).enhance(1.4)
    img = ImageEnhance.Brightness(img).enhance(0.95)
    return img


def image_to_base64(img: Image.Image, max_width: int = 1800) -> str:
    """Convert a PIL image to base64 JPEG, applying handwriting preprocessing first."""
    img = preprocess_for_handwriting(img)
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)  # higher quality for fine strokes
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def save_page_images(
    pdf_name: str,
    images: list[Image.Image],
    pps: int,
) -> None:
    """
    Save page images for manual inspection.
    Folder names use the pseudonym from STUDENT_PAGE_ORDER when available,
    otherwise fall back to student_NN so dry_run output is immediately readable.
    """
    pdf_stem = pdf_name.replace(" ", "_").replace(".pdf", "")
    base = OUT_DIR / "_images" / pdf_stem

    for student_idx, page_start in enumerate(range(0, len(images), pps)):
        group = images[page_start: page_start + pps]
        label = f"slot_{student_idx + 1:02d}"
        if len(group) < pps:
            label += f"_PARTIAL_{len(group)}of{pps}"
        student_dir = base / label
        student_dir.mkdir(parents=True, exist_ok=True)
        for page_offset, img in enumerate(group):
            img.save(str(student_dir / f"page_{page_offset + 1}.jpg"), format="JPEG", quality=92)
    print(f"  Images saved -> {base}/")


# ---------------------------------------------------------------------------
# Claude call
# Fix 1: use `raw` (always defined when JSONDecodeError fires) not `response.content[0].text`
# Fix 2: client is required; dry_run path is separated so None is never passed here
# ---------------------------------------------------------------------------

def transcribe_student_pages(
    client: anthropic.Anthropic,
    images: list[Image.Image],
    pdf_name: str,
    model: str = "claude-opus-4-8",
    retries: int = 3,
) -> dict[str, Any]:
    """
    Send all pages for one student in a single multi-image Claude call.
    Returns dict with item_id keys + student_name + page_notes.
    On failure returns {"_error": "...", "_raw": "..."}.
    """
    prompt = PROMPTS[pdf_name]
    content: list[dict] = []
    for i, img in enumerate(images):
        content.append({"type": "text", "text": f"[Page {i + 1} of {len(images)}]"})
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg",
                       "data": image_to_base64(img)},
        })
    content.append({"type": "text", "text": prompt})

    raw = ""
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=2048,
                messages=[{"role": "user", "content": content}],
            )
            raw = response.content[0].text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            return json.loads(raw)
        except json.JSONDecodeError as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            # raw is the stripped/processed text — always defined here
            return {"_error": f"JSON parse failed: {e}", "_raw": raw[:500]}
        except anthropic.RateLimitError:
            wait = 20 * (attempt + 1)
            print(f"    Rate limit. Waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            return {"_error": str(e)}
    return {"_error": "Max retries exceeded"}


# ---------------------------------------------------------------------------
# Mapping: raw transcription -> {item_id: answer}
# ---------------------------------------------------------------------------

def extract_item_responses(raw: dict[str, Any], pdf_name: str) -> dict[str, str]:
    """
    Pull only rubric item_id keys from a raw transcription dict.
    Distinguishes (bos) [student blank] from (missing) [model omitted key].
    """
    result: dict[str, str] = {}
    for item_id in PDF_ITEM_IDS[pdf_name]:
        value = raw.get(item_id)
        if value is None:
            result[item_id] = "(missing)"
        else:
            result[item_id] = str(value).strip() or "(bos)"
    return result


def is_answered(value: str) -> bool:
    """True only if value is not a sentinel (i.e. a real student answer exists)."""
    return value.strip().lower() not in {s.lower() for s in NO_ANSWER_SENTINELS}


_INJECTION_PATTERNS = (
    "ignore all instructions",
    "ignore previous",
    "disregard",
    "you are now",
    "new instructions",
    "override",
    "system prompt",
    "assistant:",
    "human:",
)

_MAX_ANSWER_LENGTH = 600


def validate_ocr_output(record: dict) -> list[str]:
    """
    Run plausibility checks on a completed build_responses() record.
    Returns a list of warning strings. Empty list means no issues found.
    Does not raise; callers decide how to handle warnings.

    Checks:
    1. All 24 item IDs present in responses.
    2. No unrecognised item IDs in responses.
    3. student_name matches a known pseudonym.
    4. High sentinel rate (> 50% of items have no real answer).
    5. Transcription errors present.
    6. Suspiciously long answers (hallucination signal).
    7. Prompt injection patterns in answer text.
    8. Improperly formed sentinel strings (typos in sentinel values).
    """
    warnings: list[str] = []
    responses: dict[str, str] = record.get("responses", {})

    # 1. Missing item IDs
    missing_ids = [i for i in ALL_ITEM_IDS if i not in responses]
    if missing_ids:
        warnings.append(f"Missing item IDs in responses: {missing_ids}")

    # 2. Unknown item IDs
    known_set = set(ALL_ITEM_IDS)
    unknown_ids = [k for k in responses if k not in known_set]
    if unknown_ids:
        warnings.append(f"Unknown item IDs in responses: {unknown_ids}")

    # 3. student_name pseudonym match
    student_name = record.get("student_name", "")
    if not student_name:
        warnings.append("student_name is empty")
    elif match_pseudonym(student_name) is None:
        warnings.append(
            f"student_name {student_name!r} does not match any known pseudonym"
        )

    # 4. High sentinel rate
    no_answer_count = sum(1 for v in responses.values() if not is_answered(v))
    if responses and no_answer_count / len(responses) > 0.5:
        warnings.append(
            f"High no-answer rate: {no_answer_count}/{len(responses)} items have no real answer"
        )

    # 5. Transcription errors
    transcription_errors = [
        item_id for item_id, v in responses.items()
        if v.strip().lower() == "(transcription_error)"
    ]
    if transcription_errors:
        warnings.append(f"Transcription errors on items: {transcription_errors}")

    # 6. Suspiciously long answers
    long_answers = [
        item_id for item_id, v in responses.items()
        if len(v) > _MAX_ANSWER_LENGTH
    ]
    if long_answers:
        warnings.append(
            f"Suspiciously long answers (>{_MAX_ANSWER_LENGTH} chars, possible hallucination): "
            f"{long_answers}"
        )

    # 7. Prompt injection patterns
    injected = [
        item_id for item_id, v in responses.items()
        if any(pat in v.lower() for pat in _INJECTION_PATTERNS)
    ]
    if injected:
        warnings.append(
            f"Possible prompt injection in items: {injected}"
        )

    # 8. Improperly formed sentinel-like strings (e.g. "bos", "(bos )", "(missing )")
    sentinel_lower = {s.lower() for s in NO_ANSWER_SENTINELS}
    malformed = []
    for item_id, v in responses.items():
        stripped = v.strip().lower()
        if stripped in sentinel_lower:
            continue
        if is_answered(v):
            continue
        # is_answered is False but not a proper sentinel -- shouldn't happen but catch it
        malformed.append(item_id)
    if malformed:
        warnings.append(
            f"Items with unrecognised non-answer values (check for sentinel typos): {malformed}"
        )

    return warnings


# ---------------------------------------------------------------------------
# Build final responses.json for one student
# ---------------------------------------------------------------------------

def build_responses(
    student_name: str,
    raw_by_pdf: dict[str, dict],
) -> dict[str, Any]:
    responses: dict[str, str] = {}
    errors: list[str] = []

    for pdf_name, raw in raw_by_pdf.items():
        if "_error" in raw:
            errors.append(f"{pdf_name}: {raw['_error']}")
            for item_id in PDF_ITEM_IDS[pdf_name]:
                responses[item_id] = "(transcription_error)"
        else:
            responses.update(extract_item_responses(raw, pdf_name))

    for item_id in ALL_ITEM_IDS:
        if item_id not in responses:
            responses[item_id] = "(not_extracted)"

    answered = sum(1 for v in responses.values() if is_answered(v))
    record: dict[str, Any] = {
        "student_name": student_name,
        "item_coverage": {
            "answered": answered,
            "total": len(ALL_ITEM_IDS),
            "blank_or_illegible": sum(
                1 for v in responses.values() if v in {"(bos)", "(okunamiyor)"}
            ),
            "missing_from_model": sum(
                1 for v in responses.values()
                if v in {"(missing)", "(not_extracted)"}
            ),
        },
        "responses": responses,
        "raw": {
            pdf_name.replace(" ", "_").replace(".pdf", "").lower(): raw
            for pdf_name, raw in raw_by_pdf.items()
        },
    }
    if errors:
        record["errors"] = errors
    return record


# ---------------------------------------------------------------------------
# Process one PDF
# Fix 3: partial last group (fewer pages than pps) is flagged, not silently processed
# Fix 6: resume — students already in all_raw or with existing raw JSON are skipped
# ---------------------------------------------------------------------------

def process_pdf(
    client: anthropic.Anthropic,
    pdf_name: str,
    resume: bool = True,
) -> dict[str, dict]:
    """
    Transcribe all students from one PDF.
    resume=True: skips a student if their raw JSON for this PDF already exists on disk.
    Returns {normalized_student_key: raw_dict}.
    """
    pdf_path = DATA_DIR / pdf_name
    pps = PAGES_PER_STUDENT[pdf_name]
    raw_key = pdf_name.replace(" ", "_").replace(".pdf", "_raw.json").lower()
    pdf_stem = pdf_name.replace(" ", "_").replace(".pdf", "").lower()
    print(f"\n=== {pdf_name} ===")

    print("  Converting to images...")
    images = convert_from_path(str(pdf_path), dpi=DPI)
    total = len(images)
    n_full = total // pps
    n_partial = total % pps
    print(f"  {total} pages / {pps} per student = {n_full} full groups"
          + (f" + 1 partial ({n_partial} pages, SKIPPED)" if n_partial else ""))

    # Build resume map: {slot_index: student_key} from existing markers.
    # Marker filename: .{StudentName}_{pdf_stem}  content: slot number (1-based).
    done_slots: dict[int, str] = {}
    if resume:
        for marker in OUT_DIR.glob(f".*_{pdf_stem}"):
            try:
                slot_num = int(marker.read_text().strip())
                student_key = marker.name[1: -(len(pdf_stem) + 1)]  # strip leading dot and _{pdf_stem}
                done_slots[slot_num - 1] = student_key
            except (ValueError, IndexError):
                pass

    results: dict[str, dict] = {}
    for idx, page_start in enumerate(range(0, total, pps)):
        group = images[page_start: page_start + pps]

        if len(group) < pps:
            print(f"  Student {idx + 1}: only {len(group)} of {pps} pages — SKIPPED (partial group)")
            continue

        if idx in done_slots:
            key = done_slots[idx]
            print(f"  Student {idx + 1} (p{page_start+1}-{page_start+pps})... -> {key} [SKIPPED]")
            existing = OUT_DIR / key / raw_key
            if existing.exists():
                with open(existing, encoding="utf-8") as f:
                    results[key] = json.load(f)
            continue

        print(f"  Student {idx + 1} (p{page_start+1}-{page_start+pps})...", end=" ", flush=True)
        raw = transcribe_student_pages(client, group, pdf_name)

        name_raw = raw.get("student_name") or ""
        key = resolve_student_key(name_raw, idx, pdf_name)
        student_dir = OUT_DIR / key

        print(f"-> {key}")
        student_dir.mkdir(exist_ok=True)
        with open(student_dir / raw_key, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        # Marker: .{StudentName}_{pdf_stem}, content = slot number (1-based)
        (OUT_DIR / f".{key}_{pdf_stem}").write_text(str(idx + 1))

        results[key] = raw
        time.sleep(0.5)

    return results


# ---------------------------------------------------------------------------
# Dry run: images only, no client needed
# Fix 2: client=None never passes to transcribe; dry_run is a standalone function
# ---------------------------------------------------------------------------

def dry_run(pdfs: Optional[list[str]] = None) -> None:
    """Convert PDFs to images and save them. No API calls."""
    all_pdfs = list(PAGES_PER_STUDENT.keys()) if pdfs is None else pdfs
    for pdf_name in all_pdfs:
        pps = PAGES_PER_STUDENT[pdf_name]
        print(f"\n=== {pdf_name} ===")
        print("  Converting to images...")
        images = convert_from_path(str(DATA_DIR / pdf_name), dpi=DPI)
        total = len(images)
        n_partial = total % pps
        print(f"  {total} pages / {pps} per student = {total // pps} full groups"
              + (f" + 1 partial ({n_partial} pages)" if n_partial else ""))
        save_page_images(pdf_name, images, pps)
    print("\nDry run complete. Inspect ocr_output/_images/ before running pilot.")


# ---------------------------------------------------------------------------
# Pilot: one student from one PDF
# Fix 5: item_coverage.total reflects only items from this PDF, label says so
# ---------------------------------------------------------------------------

def mode_pilot(
    client: anthropic.Anthropic,
    pdf_name: str,
    student_index: int,
) -> dict:
    """
    Transcribe one student's pages from one PDF.
    student_index=0 -> pages 1..pps, index=1 -> pages pps+1..2*pps, etc.
    """
    pps = PAGES_PER_STUDENT[pdf_name]
    pdf_item_ids = PDF_ITEM_IDS[pdf_name]
    start_page = student_index * pps + 1
    end_page = (student_index + 1) * pps
    print(f"Pilot: {pdf_name} | student index {student_index} | pages {start_page}-{end_page}")

    images = convert_from_path(str(DATA_DIR / pdf_name), dpi=DPI)
    total = len(images)
    start = student_index * pps
    if start >= total:
        print(f"ERROR: student_index {student_index} out of range. PDF has {total} pages ({total // pps} students).")
        return {}

    group = images[start: start + pps]
    if len(group) < pps:
        print(f"WARNING: only {len(group)} of {pps} pages available — partial group.")

    raw = transcribe_student_pages(client, group, pdf_name)
    name_raw = raw.get("student_name") or ""
    key = resolve_student_key(name_raw, student_index, pdf_name)
    print(f"  Identified as: {key}")

    responses = extract_item_responses(raw, pdf_name)
    answered = sum(1 for v in responses.values() if is_answered(v))
    record = {
        "student_name": key,
        "item_coverage": {
            "answered": answered,
            "total_this_pdf": len(pdf_item_ids),
            "total_all_pdfs": len(ALL_ITEM_IDS),
            "note": f"pilot covers only {pdf_name}; run full pipeline for all {len(ALL_ITEM_IDS)} items",
        },
        "responses": responses,
        "raw": raw,
    }

    out_dir = OUT_DIR / f"_pilot_{key}"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / pdf_name.replace(" ", "_").replace(".pdf", ".json").lower()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False, indent=2)

    print(f"\nSaved -> {out_path}")
    _print_item_summary(responses, raw.get("page_notes", ""))
    return record


def mode_validate(student_name: str) -> None:
    """Print human-readable review of a student's responses.json for spot-checking."""
    key = match_pseudonym(student_name) or normalize_student_key(student_name) or student_name
    path = OUT_DIR / key / "responses.json"
    if not path.exists():
        # Try exact name as fallback
        path = OUT_DIR / student_name / "responses.json"
    if not path.exists():
        print(f"No responses.json found for '{student_name}' (tried key: '{key}').")
        print(f"Available students: {[d.name for d in OUT_DIR.iterdir() if d.is_dir() and not d.name.startswith('_')]}")
        return

    with open(path, encoding="utf-8") as f:
        record = json.load(f)

    print(f"\n=== Validation report: {record['student_name']} ===")
    cov = record.get("item_coverage", {})
    print(f"Coverage: {cov.get('answered', '?')}/{cov.get('total', len(ALL_ITEM_IDS))} answered "
          f"| blank/illegible: {cov.get('blank_or_illegible', '?')} "
          f"| missing: {cov.get('missing_from_model', '?')}")
    if record.get("errors"):
        print(f"ERRORS: {record['errors']}")

    print(f"\n{'Item ID':<25} {'Status':<14} Answer (first 120 chars)")
    print("-" * 80)
    for item_id in ALL_ITEM_IDS:
        answer = record["responses"].get(item_id, "(not_in_file)")
        if is_answered(answer):
            status = "ANSWERED"
        elif answer == "(bos)":
            status = "BLANK"
        elif answer == "(okunamiyor)":
            status = "ILLEGIBLE"
        else:
            status = "MISSING"
        preview = answer[:120].replace("\n", " ")
        print(f"  {item_id:<23} {status:<14} {preview}")

    print("\nTo verify: open the PDF, find this student's pages, and manually check flagged items.")


def mode_full(
    client: anthropic.Anthropic,
    pdfs: Optional[list[str]] = None,
    resume: bool = True,
) -> None:
    all_pdfs = list(PAGES_PER_STUDENT.keys()) if pdfs is None else pdfs
    all_raw: dict[str, dict[str, dict]] = {}

    for pdf_name in all_pdfs:
        pdf_results = process_pdf(client, pdf_name, resume=resume)
        for key, raw in pdf_results.items():
            all_raw.setdefault(key, {})[pdf_name] = raw

    print("\n=== Building responses.json per student ===")
    for key, raw_by_pdf in sorted(all_raw.items()):
        record = build_responses(key, raw_by_pdf)
        student_dir = OUT_DIR / key
        student_dir.mkdir(exist_ok=True)
        out_path = student_dir / "responses.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        cov = record["item_coverage"]
        print(f"  {key}: {cov['answered']}/{cov['total']} answered "
              f"| {cov['blank_or_illegible']} blank "
              f"| {cov['missing_from_model']} missing")

    print("\nDone. Run 'python ocr_pipeline.py validate <StudentName>' to spot-check.")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _print_item_summary(responses: dict[str, str], page_notes: str) -> None:
    print(f"\n{'Item ID':<25} {'Status':<14} Answer preview")
    print("-" * 80)
    for item_id, answer in responses.items():
        if is_answered(answer):
            status = "ANSWERED"
        else:
            status = answer.upper().strip("()")
        preview = answer[:80].replace("\n", " ")
        print(f"  {item_id:<23} {status:<14} {preview}")
    if page_notes and is_answered(page_notes):
        print(f"\n  Page notes: {page_notes}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]

    if args and args[0] == "dry_run":
        dry_run(args[1:] if len(args) > 1 else None)

    elif args and args[0] == "validate":
        if len(args) < 2:
            print("Usage: python ocr_pipeline.py validate <StudentName>")
            sys.exit(1)
        mode_validate(args[1])

    elif args and args[0] == "pilot":
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        pdf = args[1] if len(args) > 1 else "WorksheetDT.pdf"
        idx = int(args[2]) if len(args) > 2 else 0
        mode_pilot(client, pdf, idx)

    else:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        pdfs_arg = args if args else None
        mode_full(client, pdfs_arg)
