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
from datetime import datetime, timezone
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

ITEM_IDS_WS1: list[str] = [f"WS1_B{i}" for i in range(1, 12)]   # 11 blanks
ITEM_IDS_WS3: list[str] = [f"WS3_B{i}" for i in range(1, 9)]    # 8 blanks
ITEM_IDS_WS4: list[str] = [f"WS4_B{i}" for i in range(1, 6)]    # 5 blanks
ITEM_IDS_WS5: list[str] = [f"WS5_B{i}" for i in range(1, 26)]   # 25 blanks
ITEM_IDS_WS6: list[str] = [f"WS6_B{i}" for i in range(1, 14)]   # 13 blanks
ITEM_IDS_WS7: list[str] = [f"WS7_B{i}" for i in range(1, 8)]    # 7 blanks
ITEM_IDS_WS10: list[str] = [f"WS10_B{i}" for i in range(1, 9)]  # 8 blanks

ITEM_IDS_WS: list[str] = (
    ITEM_IDS_WS1 + ITEM_IDS_WS3 + ITEM_IDS_WS4 +
    ITEM_IDS_WS5 + ITEM_IDS_WS6 + ITEM_IDS_WS7 + ITEM_IDS_WS10
)

ITEM_IDS_WS11: list[str] = (
    [f"WS11_B{i}" for i in range(1, 8)]         # B1-B7: open-ended
    + ["WS11_B8a", "WS11_B8b", "WS11_B9"]       # classification task + definition
    + [f"WS11_L10_{i}" for i in range(1, 9)]    # Likert group 10 (8 items)
    + [f"WS11_L11_{i}" for i in range(1, 4)]    # Likert group 11 (3 items)
    + [f"WS11_L12_{i}" for i in range(1, 6)]    # Likert/demographic group 12 (5 items)
)

ALL_ITEM_IDS: list[str] = ITEM_IDS_DT + ITEM_IDS_WS + ITEM_IDS_WS11

PDF_ITEM_IDS: dict[str, list[str]] = {
    "WorksheetDT.pdf": ITEM_IDS_DT,
    "Worksheets1-10.pdf": ITEM_IDS_WS,
    "Worksheet11_ Feedbacks.pdf": ITEM_IDS_WS11,
}

# Worksheet-level grouping: each worksheet gets its own JSON file.
WORKSHEET_ITEM_IDS: dict[str, list[str]] = {
    "WS_DT":  ITEM_IDS_DT,
    "WS1":    ITEM_IDS_WS1,
    "WS3":    ITEM_IDS_WS3,
    "WS4":    ITEM_IDS_WS4,
    "WS5":    ITEM_IDS_WS5,
    "WS6":    ITEM_IDS_WS6,
    "WS7":    ITEM_IDS_WS7,
    "WS10":   ITEM_IDS_WS10,
    "WS11":   ITEM_IDS_WS11,
}

WORKSHEET_PDF_SOURCE: dict[str, str] = {
    "WS_DT": "WorksheetDT.pdf",
    "WS1":   "Worksheets1-10.pdf",
    "WS3":   "Worksheets1-10.pdf",
    "WS4":   "Worksheets1-10.pdf",
    "WS5":   "Worksheets1-10.pdf",
    "WS6":   "Worksheets1-10.pdf",
    "WS7":   "Worksheets1-10.pdf",
    "WS10":  "Worksheets1-10.pdf",
    "WS11":  "Worksheet11_ Feedbacks.pdf",
}

# WS6 uses dt_vision_pipeline for structural tree extraction in addition to text OCR.
WS6_VISION_ENABLED: bool = True

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
Your task: transcribe every blank from ProDaBi decision tree worksheets WS1, WS3, WS4, WS5,
WS6, WS7, and WS10. You will receive multiple page images belonging to ONE student.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WORKSHEET STRUCTURE — each worksheet is a printed form with numbered blanks.
Read each worksheet header and its numbered blanks. Extract exactly what the student wrote
in each blank. Do not interpret or summarise — transcribe verbatim.

BLANKS TO EXTRACT:

--- WORKSHEET 1: Önemli Terimler (Important Terms) ---
WS1 has 11 numbered blanks asking students to define or give examples of key concepts.
"WS1_B1"  Blank 1 — definition or example for the FIRST concept (typically "nesne" / object)
"WS1_B2"  Blank 2 — second concept (typically "özellik" / feature or variable)
"WS1_B3"  Blank 3 — third concept (typically "etiket" / label)
"WS1_B4"  Blank 4 — fourth concept (typically "eşik değeri" / threshold value)
"WS1_B5"  Blank 5 — fifth concept
"WS1_B6"  Blank 6 — sixth concept
"WS1_B7"  Blank 7 — seventh concept
"WS1_B8"  Blank 8 — eighth concept
"WS1_B9"  Blank 9 — ninth concept
"WS1_B10" Blank 10 — tenth concept
"WS1_B11" Blank 11 — eleventh concept (typically "karar ağacı" / decision tree)

--- WORKSHEET 3: Eşik Uygulama (Applying Thresholds) ---
WS3 has 8 blanks. Students apply a threshold rule to classify foods as recommended/not.
"WS3_B1"  Blank 1 — first classification result or rule
"WS3_B2"  Blank 2
"WS3_B3"  Blank 3
"WS3_B4"  Blank 4
"WS3_B5"  Blank 5
"WS3_B6"  Blank 6
"WS3_B7"  Blank 7 — likely involves threshold notation (≤, ≥, <, >)
"WS3_B8"  Blank 8 — likely involves threshold notation

--- WORKSHEET 4: En İyi Eşik (Best Threshold) ---
WS4 has 5 blanks about identifying and justifying the optimal threshold value.
"WS4_B1"  Blank 1 — threshold value or variable chosen
"WS4_B2"  Blank 2 — criterion used (accuracy, MCR, etc.)
"WS4_B3"  Blank 3 — comparison of threshold options
"WS4_B4"  Blank 4 — written justification or calculation
"WS4_B5"  Blank 5 — conclusion or Pia's statement evaluation

--- WORKSHEET 5: Eşik Dene (Try Thresholds — 25 blanks) ---
WS5 is a systematic exploration worksheet. Students test multiple threshold values.
It contains a table or sequence of 25 numbered blanks. For threshold/comparison entries
transcribe any threshold notation EXACTLY (≤, ≥, <, >) as written — do not normalise.
"WS5_B1"  Blank 1
"WS5_B2"  Blank 2
"WS5_B3"  Blank 3
"WS5_B4"  Blank 4
"WS5_B5"  Blank 5
"WS5_B6"  Blank 6
"WS5_B7"  Blank 7
"WS5_B8"  Blank 8
"WS5_B9"  Blank 9
"WS5_B10" Blank 10
"WS5_B11" Blank 11
"WS5_B12" Blank 12
"WS5_B13" Blank 13
"WS5_B14" Blank 14
"WS5_B15" Blank 15
"WS5_B16" Blank 16
"WS5_B17" Blank 17
"WS5_B18" Blank 18
"WS5_B19" Blank 19
"WS5_B20" Blank 20
"WS5_B21" Blank 21
"WS5_B22" Blank 22
"WS5_B23" Blank 23
"WS5_B24" Blank 24
"WS5_B25" Blank 25

--- WORKSHEET 6: Karar Ağacı Çiz (Draw a Decision Tree — 13 blanks) ---
WS6 has 13 blanks. The student DRAWS a decision tree and labels its components.
Transcribe ONLY the written labels, threshold values, and annotations in the 13 blanks.
The tree drawing itself will be analysed separately by a vision pipeline.
For threshold/inequality expressions transcribe EXACTLY as written.
"WS6_B1"  Blank 1 — root node label or feature name
"WS6_B2"  Blank 2 — root threshold value or inequality
"WS6_B3"  Blank 3 — first branch label or condition
"WS6_B4"  Blank 4 — second branch label or condition
"WS6_B5"  Blank 5 — result/leaf node on left branch
"WS6_B6"  Blank 6 — result/leaf node on right branch
"WS6_B7"  Blank 7
"WS6_B8"  Blank 8
"WS6_B9"  Blank 9
"WS6_B10" Blank 10
"WS6_B11" Blank 11
"WS6_B12" Blank 12
"WS6_B13" Blank 13

--- WORKSHEET 7: Kurallar (Decision Rules — 7 blanks) ---
WS7 has 7 blanks. Students write if-then rules for each path in a given decision tree.
Transcribe the full if-then rule the student wrote for each blank.
"WS7_B1"  Blank 1 — decision rule for path/branch 1
"WS7_B2"  Blank 2 — decision rule for path/branch 2
"WS7_B3"  Blank 3
"WS7_B4"  Blank 4
"WS7_B5"  Blank 5
"WS7_B6"  Blank 6
"WS7_B7"  Blank 7

--- WORKSHEET 10: Sistematik (Systematic Approach — 8 blanks) ---
WS10 has 8 blanks about understanding systematic search for the best threshold.
"WS10_B1" Blank 1
"WS10_B2" Blank 2
"WS10_B3" Blank 3
"WS10_B4" Blank 4
"WS10_B5" Blank 5
"WS10_B6" Blank 6
"WS10_B7" Blank 7
"WS10_B8" Blank 8

--- WORKSHEET SNAPSHOT ---
"ws_snapshot"
  Write 2-3 sentences summarising what this student's worksheets REVEAL about their
  understanding of decision trees. Focus on:
  - Completion level (which worksheets are fully vs. partially answered)
  - Key strengths visible from their written responses
  - Recurring errors or gaps (e.g. always omits inequality direction, only writes numbers
    without context, leaves threshold questions blank)
  - Notable features (e.g. "uses both English and Turkish terms", "writes complete sentences")
  This snapshot is for the researcher — be specific and evidence-based, not generic.

"page_notes"
  Brief note about scan quality, pages that were very hard to read, or unusual layout.
  Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "WS1_B1": "...", "WS1_B2": "...", "WS1_B3": "...", "WS1_B4": "...", "WS1_B5": "...",
  "WS1_B6": "...", "WS1_B7": "...", "WS1_B8": "...", "WS1_B9": "...", "WS1_B10": "...",
  "WS1_B11": "...",
  "WS3_B1": "...", "WS3_B2": "...", "WS3_B3": "...", "WS3_B4": "...",
  "WS3_B5": "...", "WS3_B6": "...", "WS3_B7": "...", "WS3_B8": "...",
  "WS4_B1": "...", "WS4_B2": "...", "WS4_B3": "...", "WS4_B4": "...", "WS4_B5": "...",
  "WS5_B1": "...", "WS5_B2": "...", "WS5_B3": "...", "WS5_B4": "...", "WS5_B5": "...",
  "WS5_B6": "...", "WS5_B7": "...", "WS5_B8": "...", "WS5_B9": "...", "WS5_B10": "...",
  "WS5_B11": "...", "WS5_B12": "...", "WS5_B13": "...", "WS5_B14": "...", "WS5_B15": "...",
  "WS5_B16": "...", "WS5_B17": "...", "WS5_B18": "...", "WS5_B19": "...", "WS5_B20": "...",
  "WS5_B21": "...", "WS5_B22": "...", "WS5_B23": "...", "WS5_B24": "...", "WS5_B25": "...",
  "WS6_B1": "...", "WS6_B2": "...", "WS6_B3": "...", "WS6_B4": "...", "WS6_B5": "...",
  "WS6_B6": "...", "WS6_B7": "...", "WS6_B8": "...", "WS6_B9": "...", "WS6_B10": "...",
  "WS6_B11": "...", "WS6_B12": "...", "WS6_B13": "...",
  "WS7_B1": "...", "WS7_B2": "...", "WS7_B3": "...", "WS7_B4": "...",
  "WS7_B5": "...", "WS7_B6": "...", "WS7_B7": "...",
  "WS10_B1": "...", "WS10_B2": "...", "WS10_B3": "...", "WS10_B4": "...",
  "WS10_B5": "...", "WS10_B6": "...", "WS10_B7": "...", "WS10_B8": "...",
  "ws_snapshot": "...",
  "page_notes": "..."
}}"""

PROMPT_WS11 = f"""You are an expert at reading handwritten Turkish university student worksheets.
Your task: transcribe every blank from Worksheet 11 (evaluation + feedback form).

You will receive multiple page images belonging to ONE student.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WORKSHEET 11 STRUCTURE:
- Blanks B1-B7: open-ended evaluation questions (written answers)
- Blanks B8a, B8b: classification task
- Blank B9: open-ended definition
- Likert group L10 (8 items): students CIRCLE a number 1-5 on a printed scale
- Likert group L11 (3 items): same format
- Group L12 (5 items): may include demographic or self-assessment items

For Likert/circled-number items, transcribe the number the student circled.
If the scale shows options and the student ticked/circled one, write just that value.
If the student wrote text instead of circling, transcribe the text.

BLANKS TO EXTRACT:

"student_name"

--- Open-ended evaluation blanks ---
"WS11_B1"  Blank 1 — first open-ended evaluation question
"WS11_B2"  Blank 2
"WS11_B3"  Blank 3
"WS11_B4"  Blank 4
"WS11_B5"  Blank 5
"WS11_B6"  Blank 6
"WS11_B7"  Blank 7

--- Classification and definition task ---
"WS11_B8a" Blank 8a — classify a food item using the printed decision tree (student's result)
"WS11_B8b" Blank 8b — write the decision RULE used for 8a (the if-then path the student traced)
"WS11_B9"  Blank 9 — define a decision tree in the student's own words (full written text)

--- Likert group 10 (items 10.1 – 10.8) ---
Each is a 1-5 scale item. Transcribe the circled/ticked number exactly.
"WS11_L10_1"  Item 10.1 — circled scale value (1-5)
"WS11_L10_2"  Item 10.2
"WS11_L10_3"  Item 10.3
"WS11_L10_4"  Item 10.4
"WS11_L10_5"  Item 10.5
"WS11_L10_6"  Item 10.6
"WS11_L10_7"  Item 10.7
"WS11_L10_8"  Item 10.8

--- Likert group 11 (items 11.1 – 11.3) ---
"WS11_L11_1"  Item 11.1 — circled scale value
"WS11_L11_2"  Item 11.2
"WS11_L11_3"  Item 11.3

--- Group 12 (items 12.1 – 12.5, may include demographic or self-assessment) ---
"WS11_L12_1"  Item 12.1 — selected or written value
"WS11_L12_2"  Item 12.2
"WS11_L12_3"  Item 12.3
"WS11_L12_4"  Item 12.4
"WS11_L12_5"  Item 12.5

--- Snapshot ---
"ws_snapshot"
  Write 2-3 sentences summarising what Worksheet 11 reveals about this student.
  Note engagement with the evaluation (did they answer all Likert items? any notable
  patterns in their circled values?), quality of their definition in B9, and anything
  distinctive about their responses (strong language, contradictions, unusually short/long).

"page_notes"
  Brief note about scan quality or layout issues. Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "WS11_B1": "...", "WS11_B2": "...", "WS11_B3": "...", "WS11_B4": "...",
  "WS11_B5": "...", "WS11_B6": "...", "WS11_B7": "...",
  "WS11_B8a": "...", "WS11_B8b": "...", "WS11_B9": "...",
  "WS11_L10_1": "...", "WS11_L10_2": "...", "WS11_L10_3": "...", "WS11_L10_4": "...",
  "WS11_L10_5": "...", "WS11_L10_6": "...", "WS11_L10_7": "...", "WS11_L10_8": "...",
  "WS11_L11_1": "...", "WS11_L11_2": "...", "WS11_L11_3": "...",
  "WS11_L12_1": "...", "WS11_L12_2": "...", "WS11_L12_3": "...",
  "WS11_L12_4": "...", "WS11_L12_5": "...",
  "ws_snapshot": "...",
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
    if pdf_name not in PDF_ITEM_IDS:
        raise KeyError(
            f"extract_item_responses: unknown pdf_name {pdf_name!r}. "
            f"Known names: {sorted(PDF_ITEM_IDS)}"
        )
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

    # 8. Sentinel-like but malformed (e.g. "bos" instead of "(bos)", "(missing )" with space)
    # Only flag short values (<=25 chars) that look like a sentinel attempt, not real sentences.
    _SENTINEL_CORES = ("bos", "missing", "okunamiyor", "not extracted", "transcription_error")
    sentinel_lower = {s.lower() for s in NO_ANSWER_SENTINELS}
    malformed = []
    for item_id, v in responses.items():
        if not is_answered(v):
            continue  # it is already a valid sentinel
        stripped = v.strip().lower()
        if len(stripped) > 25:
            continue  # real answer — too long to be a mistyped sentinel
        if any(core == stripped or stripped in (f"({core})", f"({core} )", core)
               for core in _SENTINEL_CORES) and stripped not in sentinel_lower:
            malformed.append(item_id)
    if malformed:
        warnings.append(
            f"Items with sentinel-like but malformed values (check for typos): {malformed}"
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


def _extract_ws6_tree(
    client: anthropic.Anthropic,
    student_dir: Path,
    ocr_model: str,
) -> dict[str, Any]:
    """
    Run dt_vision_pipeline on the saved WS6 page image for this student.
    Returns the tree_structure dict to embed in WS6.json gate_1_extraction.
    Returns {} with a warning if image not found or pipeline fails.
    """
    try:
        import dt_vision_pipeline as dvp
    except ImportError:
        return {"error": "dt_vision_pipeline not available"}

    images_dir = student_dir / "_images"
    ws6_candidates = sorted(images_dir.glob("ws6_*.jpg")) if images_dir.exists() else []
    if not ws6_candidates:
        return {"warning": "No WS6 page image found under _images/. Run dry_run first."}

    warnings: list[str] = []
    try:
        result = dvp.run_pipeline(str(ws6_candidates[0]))
        val_warnings = dvp.validate_pipeline_output(result)
        tree_json = json.loads(result.to_json())
        return {
            "root_feature": tree_json.get("tree", {}).get("feature") if tree_json.get("tree") else None,
            "root_operator": tree_json.get("tree", {}).get("operator") if tree_json.get("tree") else None,
            "root_threshold": tree_json.get("tree", {}).get("threshold") if tree_json.get("tree") else None,
            "full_tree": tree_json.get("tree"),
            "raw_texts": result.raw_texts,
            "pipeline_warnings": result.warnings + val_warnings,
            "vision_model": ocr_model,
        }
    except Exception as exc:
        return {"error": str(exc)}


def save_worksheet_jsons(
    student_name: str,
    all_responses: dict[str, str],
    raw_by_pdf: dict[str, dict],
    student_dir: Path,
    ocr_model: str = "claude-sonnet-4-6",
    client: Optional[anthropic.Anthropic] = None,
) -> None:
    """
    Write one JSON file per worksheet under student_dir using a 4-gate structure.

    Gate 1 — Extraction:  OCR items + raw_ocr + ws_snapshot from LLM
    Gate 2 — Validation:  item_coverage metrics + warnings
    Gate 3 — Scoring:     pending (filled by worksheet_assessor.py)
    Gate 4 — AI-CFT:      pending (filled by competency assignment step)

    Output files: WS_DT.json, WS1.json, WS3.json, WS4.json, WS5.json,
                  WS6.json, WS7.json, WS10.json, WS11.json
    """
    extracted_at = datetime.now(timezone.utc).isoformat()

    # Build raw_ocr lookup: pdf_name -> raw dict from OCR
    raw_ws    = raw_by_pdf.get("Worksheets1-10.pdf", {})
    raw_ws11  = raw_by_pdf.get("Worksheet11_ Feedbacks.pdf", {})
    raw_dt    = raw_by_pdf.get("WorksheetDT.pdf", {})

    ws_snapshot_ws    = raw_ws.get("ws_snapshot", "")
    ws_snapshot_ws11  = raw_ws11.get("ws_snapshot", "")

    for ws_label, item_ids in WORKSHEET_ITEM_IDS.items():
        if not item_ids:
            continue

        items = {iid: all_responses.get(iid, "(not_extracted)") for iid in item_ids}
        answered          = sum(1 for v in items.values() if is_answered(v))
        blank_or_illegible = sum(1 for v in items.values() if v in {"(bos)", "(okunamiyor)"})
        missing           = sum(1 for v in items.values() if v in {"(missing)", "(not_extracted)"})
        total             = len(item_ids)
        completion_rate   = round(answered / total, 3) if total else 0.0

        # Choose raw OCR source for this worksheet
        if ws_label == "WS_DT":
            raw_source  = raw_dt
            ws_snapshot = raw_dt.get("ws_snapshot", "")
        elif ws_label == "WS11":
            raw_source  = raw_ws11
            ws_snapshot = ws_snapshot_ws11
        else:
            raw_source  = raw_ws
            ws_snapshot = ws_snapshot_ws

        # Gate 2 validation warnings
        ocr_warnings = validate_ocr_output({
            "student_name": student_name,
            "responses": items,
        })

        # Determine gate_1 status
        if missing == total:
            g1_status = "fail"
        elif missing > 0 or blank_or_illegible > answered:
            g1_status = "partial"
        else:
            g1_status = "pass"

        # Gate 2 status
        g2_status = "fail" if completion_rate < 0.3 else ("partial" if completion_rate < 0.7 else "pass")

        record: dict[str, Any] = {
            "student_name": student_name,
            "worksheet":    ws_label,
            "pdf_source":   WORKSHEET_PDF_SOURCE[ws_label],

            "gate_1_extraction": {
                "status":       g1_status,
                "extracted_at": extracted_at,
                "ocr_model":    ocr_model,
                "items":        items,
                "raw_ocr":      {k: v for k, v in raw_source.items()
                                 if k not in ("student_name", "page_notes", "ws_snapshot")},
            },

            "gate_2_validation": {
                "status": g2_status,
                "item_coverage": {
                    "answered":           answered,
                    "total":              total,
                    "blank_or_illegible": blank_or_illegible,
                    "missing":            missing,
                    "completion_rate":    completion_rate,
                },
                "warnings": ocr_warnings,
                "student_snapshot": {
                    "completion_rate":       completion_rate,
                    "engagement_level":      ("high" if completion_rate >= 0.7
                                              else "medium" if completion_rate >= 0.4
                                              else "low"),
                    "llm_observations":      ws_snapshot,
                    "page_quality_notes":    raw_source.get("page_notes", ""),
                },
            },

            "gate_3_scoring": {
                "status":        "pending",
                "scored_at":     None,
                "scoring_model": None,
                "items":         {},
            },

            "gate_4_aicft": {
                "status":   "pending",
                "level":    None,
                "evidence": None,
            },
        }

        # WS6 — add structural tree extraction from dt_vision_pipeline
        if ws_label == "WS6" and WS6_VISION_ENABLED and client is not None:
            record["gate_1_extraction"]["tree_structure"] = _extract_ws6_tree(
                client, student_dir, ocr_model
            )

        out_path = student_dir / f"{ws_label}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)


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

    print("\n=== Building per-student JSON files ===")
    for key, raw_by_pdf in sorted(all_raw.items()):
        record = build_responses(key, raw_by_pdf)
        student_dir = OUT_DIR / key
        student_dir.mkdir(exist_ok=True)

        # Combined file — all items in one record
        out_path = student_dir / "responses.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        # Per-worksheet files — one gated JSON per worksheet
        save_worksheet_jsons(
            student_name=key,
            all_responses=record["responses"],
            raw_by_pdf=raw_by_pdf,
            student_dir=student_dir,
            client=client,
        )

        cov = record["item_coverage"]
        ws_files = ", ".join(f"{ws}.json" for ws in WORKSHEET_ITEM_IDS)
        print(f"  {key}: {cov['answered']}/{cov['total']} answered "
              f"| {cov['blank_or_illegible']} blank "
              f"| {cov['missing_from_model']} missing "
              f"| saved: responses.json + {ws_files}")

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
