"""
ocr_pipeline.py

Transcribes handwritten Turkish student worksheets using Claude vision,
maps each answer to a rubric item_id, and saves a single student bundle JSON
that feeds directly into worksheet_assessor.py.

Modes
-----
dry_run   No API calls. Converts PDFs to images, saves for inspection.
          python ocr_pipeline.py dry_run [WorksheetDT.pdf ...]

pilot     One student from one PDF. Prints item-by-item response summary.
          python ocr_pipeline.py pilot WorksheetDT.pdf 0
          (student_index=0 -> pages 1-4, index=1 -> pages 5-8, etc.)

validate  Human-readable review of a student's bundle (combined responses).
          python ocr_pipeline.py validate Daniella

full      Process all three PDFs. Skips students already processed (resume-safe).
          python ocr_pipeline.py

Output per student
------------------
students/{student_key}/
  WS1.json, WS3.json, ... WS_DT.json   — per-worksheet pipeline sections
  portfolio.json                       — AI-CFT rollup
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

from pipeline_schema import (
    ALL_ITEM_IDS,
    ITEM_IDS_DT,
    ITEM_IDS_WS,
    ITEM_IDS_WS1,
    ITEM_IDS_WS11,
    PDF_ITEM_IDS,
    WORKSHEET_ITEM_IDS,
    WORKSHEET_PDF_SOURCE,
    WORKSHEETS_1_10_PAGE_INDEX,
    calibration_bundle_dir,
    dry_run_folder_name,
    layout_manifest_path,
    pdf_to_images_stem,
)

# ---------------------------------------------------------------------------
# Item ID master list — defined in pipeline_schema.py (single source of truth)
# ---------------------------------------------------------------------------

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
The worksheet has 7 sections labelled A through G (4 pages total).

CRITICAL — printed question numbers do NOT always equal rubric item suffixes.
Use the section headings and question text below to assign each answer to the correct key.
Never shift an answer from one section into another item_id.

Page layout (typical):
  Page 1 — Section A (Q1–Q4), Section B begins (Q1–Q2)
  Page 2 — Section B continues (Q3–Q4), Section C (action + Q2–Q3), Section D begins (Q1)
  Page 3 — Section D continues (Q2–Q4), Section E (metric blanks + Q1–Q3)
  Page 4 — Section E Q4, Section F (test EMIT Q1–Q2), Section G (reflection Q1–Q2)

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WHAT TO EXTRACT — return exactly these JSON keys with verbatim student answers:

"student_name"
  The pseudonym written at the top of page 1.

--- SECTION A (prior beliefs and data exploration) ---
"DT_A_Q1"  Section A Q1 — which variable(s) might predict recommendation BEFORE analysis (prior belief).
"DT_A_Q2"  Section A Q2 — which variable(s) affect recommendation based on data/graphs explored in CODAP.
"DT_A_Q3"  Section A Q3 — is there a meaningful difference between recommended and not-recommended foods? Explain.
"DT_A_Q4"  Section A Q4 — which variable would you use FIRST in a model AND why (both choice and justification).

--- SECTION B (three single-level trees) ---
"DT_B_Q1"  Section B Q1 — EMIT output after first single-variable tree (variable, threshold, TP, FP, TN, FN, metrics).
"DT_B_Q2"  Section B Q2 — EMIT output after second single-variable tree (different variable from B_Q1).
"DT_B_Q3"  Section B Q3 — EMIT output after third single-variable tree (different variable from B_Q1 and B_Q2).
"DT_B_Q4"  Section B Q4 — which variable performed best and what criteria were used to decide.

--- SECTION C (threshold tuning on best single-level tree) ---
"DT_C_Q1"  Section C action block — EMIT output after recalling the best tree and varying its threshold.
             Look for recorded counts/metrics near the Section C instructions, before printed Q2.
"DT_C_Q2"  Section C printed Q2 — how changing threshold values affects tree performance.
"DT_C_Q3"  Section C printed Q3 — which threshold value best separates classes and how you found it.

--- SECTION D (two-level tree) ---
"DT_D_Q1"  Section D action block — EMIT output after adding a second variable to create a 2-level tree.
"DT_D_Q2"  Section D printed Q2 — did the second variable improve classification? How?
"DT_D_Q3"  Section D printed Q3 — which variable combination gave the best result?
"DT_D_Q4"  Section D printed Q4 — how did you decide you reached the best tree (stopping criterion)?

--- SECTION E (evaluate best 2-level tree) ---
"DT_E_TP"                  Section E — true positive (TP) definition if written on the sheet.
"DT_E_FP"                  Section E — false positive (FP) definition if written on the sheet.
"DT_E_sensitivity_formula" Section E — sensitivity formula as text (e.g. TP/(TP+FN)).
"DT_E_MCR_formula"         Section E — MCR formula as text (e.g. (FP+FN)/N).
"DT_E_sensitivity"         Numeric sensitivity (duyarlılık) value filled in the Section E metric blank.
"DT_E_MCR"                 Numeric MCR (hata oranı) value filled in the Section E metric blank.
"DT_E_Q1"  Section E Q1 — which metric matters most for this model's purpose and why.
"DT_E_Q2"  Section E Q2 — did the model make more false positives or false negatives?
"DT_E_Q3"  Section E Q3 — when should software stop building the tree?
"DT_E_Q4"  Section E Q4 — can decision trees achieve perfect classification (zero errors)? Answer + reason.

--- SECTION F (apply tree to test data) ---
"DT_F_Q1"  Section F Q1 — EMIT output when applying the best tree to the TEST dataset.
"DT_F_Q2"  Section F Q2 — compare test vs training performance; explain any difference (overfitting).

--- SECTION G (reflection) ---
"DT_G_overfitting"    Section G — overfitting definition if written on the sheet.
"DT_G_DT_definition"  Section G — decision tree definition if written on the sheet.
"DT_G_Q1"  Section G Q1 — what did the decision tree MODEL learn from the data?
"DT_G_Q2"  Section G Q2 — what did the STUDENT learn while building decision trees?

"page_notes"
  Brief note about image quality, pages that were very hard to read, or unusual layout.
  Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "DT_A_Q1": "...",
  "DT_A_Q2": "...",
  "DT_A_Q3": "...",
  "DT_A_Q4": "...",
  "DT_B_Q1": "...",
  "DT_B_Q2": "...",
  "DT_B_Q3": "...",
  "DT_B_Q4": "...",
  "DT_C_Q1": "...",
  "DT_C_Q2": "...",
  "DT_C_Q3": "...",
  "DT_D_Q1": "...",
  "DT_D_Q2": "...",
  "DT_D_Q3": "...",
  "DT_D_Q4": "...",
  "DT_E_TP": "...",
  "DT_E_FP": "...",
  "DT_E_sensitivity_formula": "...",
  "DT_E_MCR_formula": "...",
  "DT_E_sensitivity": "...",
  "DT_E_MCR": "...",
  "DT_E_Q1": "...",
  "DT_E_Q2": "...",
  "DT_E_Q3": "...",
  "DT_E_Q4": "...",
  "DT_F_Q1": "...",
  "DT_F_Q2": "...",
  "DT_G_overfitting": "...",
  "DT_G_DT_definition": "...",
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
WS1 is a nutrition-label fill-in worksheet. Extract the seven paragraph blanks (printed blanks 5–11).
Transcribe short answers verbatim — not full definitions.
"WS1_B1"  Blank 5 — variable/label term (değişken / etiket; typically "etiket")
"WS1_B2"  Blank 6 — object/feature term (nesne / özellik; typically "nesne")
"WS1_B3"  Blank 7 — feature term; accepts nesne|özellik OR değişken|etiket equivalents
"WS1_B4"  Blank 8 — number of features (7 or yedi only)
"WS1_B5"  Blank 9 — list of nutrient/feature names from the table
"WS1_B6"  Blank 10 — example food object name (e.g. Fındıklı Gofret)
"WS1_B7"  Blank 11 — label/variable role (değişken / etiket; e.g. "etiket" or tavsiye edilemez/edilir)

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
  "WS1_B1": "...", "WS1_B2": "...", "WS1_B3": "...", "WS1_B4": "...",
  "WS1_B5": "...", "WS1_B6": "...", "WS1_B7": "...",
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

--- Q10: true/false sub-items (8 statements; transcribe Doğru or Yanlış per row) ---
"WS11_Q10_1" through "WS11_Q10_8" — one answer per statement row

--- Q11: ordering steps 2-4 (step 1 is pre-printed; transcribe the number 2, 3, or 4 the student wrote) ---
"WS11_Q11_2"  Step 2 position
"WS11_Q11_3"  Step 3 position
"WS11_Q11_4"  Step 4 position

--- Q12: multiselect sub-items (transcribe checked/unchecked or mark presence) ---
"WS11_Q12_1" through "WS11_Q12_5" — one entry per option row

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
  "WS11_Q10_1": "...", "WS11_Q10_2": "...", "WS11_Q10_3": "...", "WS11_Q10_4": "...",
  "WS11_Q10_5": "...", "WS11_Q10_6": "...", "WS11_Q10_7": "...", "WS11_Q10_8": "...",
  "WS11_Q11_2": "...", "WS11_Q11_3": "...", "WS11_Q11_4": "...",
  "WS11_Q12_1": "...", "WS11_Q12_2": "...", "WS11_Q12_3": "...", "WS11_Q12_4": "...",
  "WS11_Q12_5": "...",
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
    Folder names use pseudonyms from calibration/pdf_student_order.json when known,
    otherwise fall back to slot_{NN}. Also writes resume markers .{name}_{pdf_stem}.
    """
    pdf_stem = pdf_to_images_stem(pdf_name)

    base = OUT_DIR / "_images" / pdf_stem

    for student_idx, page_start in enumerate(range(0, len(images), pps)):
        group = images[page_start: page_start + pps]
        label = dry_run_folder_name(pdf_name, student_idx)
        if len(group) < pps:
            label += f"_PARTIAL_{len(group)}of{pps}"
        student_dir = base / label
        student_dir.mkdir(parents=True, exist_ok=True)
        for page_offset, img in enumerate(group):
            img.save(str(student_dir / f"page_{page_offset + 1}.jpg"), format="JPEG", quality=92)
        if not label.startswith("slot_") and "_PARTIAL_" not in label:
            (OUT_DIR / f".{label}_{pdf_stem}").write_text(str(student_idx + 1))
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
# Build combined response record for one student (in-memory; saved via student_bundle)
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

def _run_layout_after_dry_run() -> None:
    """Phase 1 layout on calibration pages when OpenCV is available."""
    try:
        from layout_isolator import LayoutIsolator
    except ImportError:
        return
    cal_dir = calibration_bundle_dir("Worksheets1-10.pdf")
    if cal_dir is None or not any(cal_dir.glob("page_*.jpg")):
        return
    isolator = LayoutIsolator()
    for ws in ("WS10", "WS5"):
        page_idx = WORKSHEETS_1_10_PAGE_INDEX.get(ws)
        if not page_idx:
            continue
        page = cal_dir / f"page_{page_idx}.jpg"
        if page.exists():
            result = isolator.process_worksheet_page(page, "Sample_Student", ws)
            result.save()
            print(f"  Layout {ws}: {result.status} ({result.zone_count} zones)")


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
        if pdf_name == "Worksheets1-10.pdf":
            _run_layout_after_dry_run()
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
    """Print human-readable review of a student's combined responses for spot-checking."""
    from student_bundle import (
        artifact_payload,
        extraction_responses,
        list_student_ids,
        list_worksheets,
        load_artifact,
        student_dir,
        STUDENTS_DIR,
    )

    key = match_pseudonym(student_name) or normalize_student_key(student_name) or student_name
    sid = key if student_dir(key).is_dir() else student_name

    if not student_dir(sid).is_dir():
        print(f"No student output found for '{student_name}' (tried key: '{key}').")
        from student_bundle import list_student_ids, STUDENTS_DIR
        if STUDENTS_DIR.exists():
            print(f"Available students: {list_student_ids()}")
        return

    responses: dict[str, str] = {}
    for ws in list_worksheets(sid):
        ext = load_artifact(sid, ws, "extraction")
        responses.update(extraction_responses(ext))

    answered = sum(1 for iid in ALL_ITEM_IDS if is_answered(responses.get(iid, "")))
    blank = sum(1 for iid in ALL_ITEM_IDS if responses.get(iid) in {"(bos)", "(okunamiyor)"})
    missing = sum(1 for iid in ALL_ITEM_IDS if responses.get(iid, "(not_in_file)") in {"(missing)", "(not_extracted)", "(not_in_file)"})

    print(f"\n=== Validation report: {sid} ===")
    print(f"Coverage: {answered}/{len(ALL_ITEM_IDS)} answered "
          f"| blank/illegible: {blank} "
          f"| missing: {missing}")

    print(f"\n{'Item ID':<25} {'Status':<14} Answer (first 120 chars)")
    print("-" * 80)
    for item_id in ALL_ITEM_IDS:
        answer = responses.get(item_id, "(not_in_file)")
        if is_answered(answer):
            status = "ANSWERED"
        elif answer == "(bos)":
            status = "BLANK"
        elif answer == "(okunamiyor)":
            status = "ILLEGIBLE"
        else:
            status = "MISSING"
        preview = str(answer)[:120].replace("\n", " ")
        print(f"  {item_id:<23} {status:<14} {preview}")

    print("\nTo verify: open the PDF, find this student's pages, and manually check flagged items.")


def _extract_ws6_tree(
    client: anthropic.Anthropic,
    student_dir: Path,
    ocr_model: str,
) -> dict[str, Any]:
    """
    Run dt_vision_pipeline on a WS6 tree crop when available.

    Priority:
      1. layout_rois/<student>/WS6_layout.json tree_diagram crop
      2. layout_rois tree_diagram from WS5 (not used for WS6)
      3. Legacy ws6_*.jpg under student _images/
    """
    try:
        import dt_vision_pipeline as dvp
    except ImportError:
        return {"error": "dt_vision_pipeline not available"}

    student_key = student_dir.name
    image_path: Optional[str] = None

    try:
        from layout_isolator import LayoutIsolator
        crop = LayoutIsolator().tree_diagram_crop_path(student_key, "WS6")
        if crop:
            image_path = str(crop)
    except ImportError:
        pass

    if not image_path:
        images_dir = student_dir / "_images"
        ws6_candidates = sorted(images_dir.glob("ws6_*.jpg")) if images_dir.exists() else []
        if ws6_candidates:
            image_path = str(ws6_candidates[0])

    if not image_path:
        return {
            "warning": (
                "No WS6 tree image. WS6 draw canvas is not on the 6-page "
                "Worksheets1-10 bundle; run layout isolation on a supplemental scan."
            )
        }

    try:
        result = dvp.run_pipeline(image_path)
        val_warnings = dvp.validate_pipeline_output(result)
        tree_json = json.loads(result.to_json())
        return {
            "source_image": image_path,
            "root_feature": tree_json.get("tree", {}).get("feature") if tree_json.get("tree") else None,
            "root_operator": tree_json.get("tree", {}).get("operator") if tree_json.get("tree") else None,
            "root_threshold": tree_json.get("tree", {}).get("threshold") if tree_json.get("tree") else None,
            "full_tree": tree_json.get("tree"),
            "raw_texts": result.raw_texts,
            "pipeline_warnings": result.warnings + val_warnings,
            "vision_model": ocr_model,
        }
    except Exception as exc:
        return {"error": str(exc), "source_image": image_path}


def save_worksheet_jsons(
    student_name: str,
    all_responses: dict[str, str],
    raw_by_pdf: dict[str, dict],
    output_dir: Path | None = None,
    ocr_model: str = "claude-sonnet-4-6",
    client: Optional[anthropic.Anthropic] = None,
) -> Path:
    """
    Write one JSON per worksheet under students/<student_name>/.

    Each file holds an ``extraction`` section (4-gate structure) initially.
    """
    from student_bundle import STUDENTS_DIR, save_artifact, student_dir as sb_student_dir

    base = output_dir or STUDENTS_DIR
    extracted_at = datetime.now(timezone.utc).isoformat()
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

        # WS6 — add structural tree extraction + layout manifest
        if ws_label == "WS6" and WS6_VISION_ENABLED:
            ws6_manifest = layout_manifest_path(student_name, "WS6")
            if ws6_manifest.exists():
                record["gate_1_extraction"]["layout_roi"] = json.loads(
                    ws6_manifest.read_text(encoding="utf-8")
                )
            if client is not None:
                image_root = OCR_OUTPUT_DIR / student_name
                record["gate_1_extraction"]["tree_structure"] = _extract_ws6_tree(
                    client, image_root, ocr_model
                )

        # WS10 / WS5 — attach layout manifest when Phase 1 has run
        if ws_label in {"WS10", "WS5"}:
            manifest_path = layout_manifest_path(student_name, ws_label)
            if manifest_path.exists():
                record["gate_1_extraction"]["layout_roi"] = json.loads(
                    manifest_path.read_text(encoding="utf-8")
                )

        save_artifact(student_name, ws_label, "extraction", record, base_dir=base)

    return sb_student_dir(student_name, base)


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

    print("\n=== Building student bundles ===")
    for key, raw_by_pdf in sorted(all_raw.items()):
        record = build_responses(key, raw_by_pdf)
        student_dir = OUT_DIR / key
        student_dir.mkdir(exist_ok=True)

        out_dir = save_worksheet_jsons(
            student_name=key,
            all_responses=record["responses"],
            raw_by_pdf=raw_by_pdf,
            client=client,
        )

        cov = record["item_coverage"]
        print(f"  {key}: {cov['answered']}/{cov['total']} answered "
              f"| {cov['blank_or_illegible']} blank "
              f"| {cov['missing_from_model']} missing "
              f"| saved: {out_dir.relative_to(Path(__file__).parent)}/")

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
