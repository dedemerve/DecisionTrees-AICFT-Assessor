# Process Log — DecisionTrees AI-CFT Assessor

All decisions, findings, and code changes are recorded here in chronological order.
Each entry has a type tag: DECISION, FINDING, CODE, SCHEMA, TEST, PENDING.

---

## Session 1 — Schema Design (Phase 0)

### DECISION — Framework selection
UNESCO AI Competency Framework for Teachers (AI-CFT) selected over Kilpatrick framework.
Focus dimension: "AI foundations and applications" (Section 3).
Levels: Acquire / Deepen / Create.
Rationale: Prior year codebook used Kilpatrick; this year re-coded with AI-CFT.
Two-layer analysis structure confirmed:
- Layer 1: researcher/instructional design — all 5 AI-CFT dimensions
- Layer 2: pre-service teacher performance — AI foundations dimension only

### DECISION — Architecture: few-shot + multi-agent, not RAG
Sample size ~20-40 pre-service teachers. RAG adds complexity and reduces transparency
at this scale. Pydantic schema enforcement used to prevent hallucination.
LLMs never compute numerical fields — Python/Pandas only.

### SCHEMA — StudentPortfolio v1 proposed
Fields: WorksheetAssessment, ScreenRecordingObservations, LogDerivedFeatures, AICFTLevel.

### DECISION — All code must be English only
No Turkish in variable names, comments, field descriptions, Literal values, or docstrings.
Prose responses to the user may be in Turkish.

### DECISION — Writing style
No em dashes. Short, simple sentences. Humanized tone.

### SCHEMA — Round 1 fixes (user review)
- misclassification_count_candidate: int → Optional[int]
  Reason: blank worksheets caused Pydantic validation crash.
- justification: str → kept as summary; IndicatorEvidence sub-schema added
  Reason: single string could not trace which evidence supported which indicator.
- AICFTLevel indicators: free str → Literal type
  Reason: LLM could invent non-existent indicator codes.
- assigned_level validator added: Deepen requires Acquire, Create requires both.
  Reason: level-skipping was silently allowed.

### SCHEMA — Round 2 fixes (red teaming)
- concept_items: List → Field(min_length=1)
  Reason: empty list silently accepted, causing score with zero items.
- IndicatorEvidence.indicator: str → ValidIndicator Literal
  Reason: even with Literal on the three lists, the evidence trace used str.
- StudentPortfolio validator: insufficient + ai_cft_level not None → error
  Reason: "no level when data insufficient" rule was not enforced at schema level.
- data_availability vs content consistency validator added
  Reason: data_availability=False but list populated caused silent mismatch.
- evidence_quote: str → Field(min_length=10)
  Reason: empty string passed validation silently.
- processing_timestamp: str → datetime
  Reason: freeform strings like "bugün" were accepted.
- cohort_year: int → Field(ge=2020, le=2035)
  Reason: no bounds meant year=0 or year=9999 passed validation.

### TEST — All 10 stress scenarios passed after Round 2 fixes

### SCHEMA — AI-CFT indicator revision (source verification)
Indicators replaced with UNESCO-sourced LO references.
Source: UNESCO AI Competency Framework for Teachers (2024), Table 4, pp. 38-39.
- Acquire: LO3.1.2 basic_concept_recognition, LO3.1.3 tool_operation_basic,
           LO3.1.4 appropriateness_assessment
- Deepen:  LO3.2.1 proficient_independent_operation, LO3.2.2 workflow_visualisation,
           LO3.2.3 transferable_problem_solving
- Create:  LO3.3.1 limitation_analysis, LO3.3.2 tool_customisation,
           LO3.3.3 self_defined_test_criteria
Prior indicators (novel_threshold_strategy etc.) were researcher-invented and removed.

---

## Session 2 — CSV Log Analysis

### FINDING — CSV structure
File: 28 Nisan 2026 CODAP Arbor Food Log File.csv
Rows: 11,831 | Unique raw student_ids: 32 | Action types: 16
Noise actions (drag, UI, session): 61.8% of rows
Meaningful pedagogical actions: 38.2% (4,523 rows)

Key action types and schema mappings:
- change_split_values     → threshold_change_count, unique_thresholds_tried
- drop_attribute          → feature_drop_count, unique_features_tried
- set_dependent_variable  → target_variable_set_count (NOTE: auto-fired by CODAP, not reliable user signal)
- emit_tree_data          → emit_snapshots, accuracy, TP/TN/FP/FN, depth, dataset name
- change_tree_type        → tree_type_change_count, ended_on_regression
- refresh_tree            → refresh_count

emit_tree_data parameters include: FN, FP, TN, TP, depth, dataset, accuracy,
ss_model, ss_total, explained, node_count, sample_size, dependent_variable.

### FINDING — Identity problems (7 confirmed merges, 2 pending)

Confirmed merges (researcher-stated same person):
- merve dede: ['Merve Dede', 'merve dede', 'Merve DEDE', 'Merve dede', 'Merve']
  Note: 'Merve' has 3 rows only (25 Apr), no meaningful actions — same person confirmed.
- umut uzun: ['Umut Uzun', 'umut uzun']
- irem ilze: ['irem ilze', 'İrem İlze']  — Turkish dotted-İ issue
- irem damar: ['irem damar', 'İrem Damar']  — Turkish dotted-İ issue
- batuhan özger: ['Batuhan Özger', 'batuhan özger']
- mahmut öztürk: ['MAHMUT ÖZTÜRK', 'mahmut öztürk']
- nisa altaş: ['Nisa Altaş', 'Nisa ALTAŞ', 'NİSA ALTAŞ']  — Turkish İ issue

PENDING researcher decision:
- şeyda (107 rows, 7 Apr) vs şeyda demirci (398 rows, 21 Apr)
  Different dates, different session lengths. Possibly same person (surname added later).

Insufficient records (no meaningful activity):
- muhammet şahal: 1 row
- sahal: 4 rows
- şeyma peltelk: 3 rows (typo of şeyma peltek)
- ni̇sa altaş: 3 rows (encoding variant, merged into nisa altaş)

### FINDING — Train/test detection

Only mahsum yasan used explicitly labelled train/test datasets:
- titanic_egitim_veri_seti1_3 → classified as TRAIN
- titanic_test_veri_seti2 → classified as TEST
- mahsum's training emit was a zero model (TP=TN=FP=FN=0) → excluded from valid snapshots
- Result: train_test_applied=False, flag: train_dataset_emitted_but_model_was_empty

All other students used Food_Dataset_Turkish_55 variants:
- Naming: Food_Dataset_Turkish_55, Food_Dataset_Turkish_55 (1), Food_Dataset_Turkish_55Tavsiye, etc.
- These are CODAP copies, not labelled train/test splits.
- train_test_applied=False for all, flag: train_test_indeterminate:ambiguous_dataset_names
- Researcher must annotate which copy was designated as train vs test.

### FINDING — Zero-model emits
13 emit events across 5 students had TP=TN=FP=FN=0 (model not yet built).
These are excluded from accuracy statistics but retained in emit_snapshots for audit.

### FINDING — Conceptual errors flagged
Students who switched tree type to regression (classification task):
- merve dede: session ended on regression (session_ended_on_regression_tree)
- sena çiçek: session ended on regression
- batuhan özger: switched then returned to classification (switched_to_regression_then_back)
- zeynep ortakaya: switched then returned

### FINDING — Data sufficiency (22 canonical students)
- insufficient: 5 students (no meaningful actions at all)
- partial: 17 students (emit present but train/test indeterminate from log alone)
- sufficient: 0 students
Interpretation: log data alone cannot support AI-CFT level assignment.
Worksheet and screen recording data are required for all students.

### CODE — log_extractor.py
File: /Users/mrved/Desktop/DecisionTrees-AICFT-Assessor/log_extractor.py

Key design decisions in code:
- Turkish İ fix: _TURKISH_I_MAP + unicodedata.normalize("NFC") + casefold()
  Reason: Python .lower() on İ produces i + combining dot (2 chars), not plain i.
- Noise exclusion: exploration_index denominator = meaningful_action_count only
  Reason: drag/UI events are 61.8% of rows, inflating all ratios if included.
- Zero-model emit filter: _is_valid_emit() excludes TP=TN=FP=FN=0
  Reason: model not yet built; including these distorts accuracy statistics.
- Multi-session duration: summed per calendar date, not total span
  Reason: students returned on 2-3 different days; span would be ~2 weeks.
- Dataset classification: explicit allow-lists, not substring heuristics
  Reason: heuristic "test" in name matched unrelated strings.
- set_dependent_variable: counted but not flagged
  Reason: CODAP auto-fires this event hundreds of times per session.
- First-name prefix detection: strict prefix only (a startswith b+" ")
  Reason: sharing a first name (irem ilze, irem damar) is not a merge signal.

### TEST — 42/42 stress tests passed
Test coverage:
- T01: Turkish İ normalisation (3 cases)
- T02: Dataset classification (5 cases)
- T03: Zero-model emit filter (3 cases)
- T04: Threshold value canonicalisation (4 cases)
- T05: Multi-session duration calculation
- T06: Exploration index bounds for all 17 active students
- T07: First-token prefix detection (true positive + true negative)
- T08: Empty student dataframe handling
- T09: Malformed JSON parameters — no crash
- T10: Data sufficiency logic (3 cases)

---

---

## Session 3 — Pattern Analysis (Log Data)

### FINDING — Three learning profiles identified
threshold_heavy: nisa altaş (287 changes, 90 unique), irem ilze (84 changes, 79 unique), şeyda demirci
feature_heavy: mahmut öztürk, batuhan özger, mahsum yasan, oğuz köklü, merve dede
balanced: hatice sennur ayyıldız, ikbal balaban, irem damar, melike öztürk, sena çiçek, umut uzun, zeynep ortakaya

### FINDING — Accuracy trajectory groups
UP (improved): ayşe merve karataş, batuhan özger, mahsum yasan, melike öztürk, oğuz köklü, zeynep ortakaya, şeyda demirci
DOWN (degraded): irem ilze, nisa altaş, sena çiçek
FLAT (no change): hatice sennur ayyıldız, ikbal balaban, irem damar, mahmut öztürk, umut uzun, şeyma peltek

### FINDING — High threshold search does not predict better accuracy
nisa altaş: 287 threshold changes, 90 unique values, accuracy went DOWN (0.836 → 0.778)
irem ilze: 84 changes, 79 unique values, accuracy went DOWN (0.727 → 0.591)
Hypothesis: excessive threshold search without feature reconsideration leads to overfitting or local-minimum trapping.

### FINDING — Depth escalation patterns
depth_stable (max=2): mahsum yasan, merve dede, oğuz köklü
depth_moderate (max=3): ayşe merve karataş, batuhan özger, hatice sennur ayyıldız, ikbal balaban,
                         irem ilze, mahmut öztürk, sena çiçek (final), zeynep ortakaya, şeyda demirci, şeyma peltek
depth_escalated (max=4): irem damar, melike öztürk, nisa altaş, sena çiçek (peak), umut uzun
Note: melike öztürk reached depth 4 with best final accuracy (0.900). irem damar reached depth 4
      but accuracy dropped — depth escalation alone is not a positive signal.

### FINDING — Volatility (accuracy std across emits)
High volatility (std > 0.15): ikbal balaban (0.233), zeynep ortakaya (0.185), irem damar (0.142), mahsum yasan (0.142)
Low volatility (std < 0.08): nisa altaş (0.070), oğuz köklü (0.057), şeyma peltek (0.063)
High volatility with UP trend = exploratory recovery (zeynep ortakaya)
High volatility with FLAT trend = undirected search (ikbal balaban, irem damar)

### FINDING — Regression switch as confusion signal
Ended on regression (classification task): sena çiçek, merve dede
Switched then returned: batuhan özger, zeynep ortakaya

### FINDING — Session duration does not predict accuracy
Longest session: oğuz köklü (227 min) → final accuracy 0.773
Shortest active session: sena çiçek (86 min) → final accuracy 0.477
Best accuracy: melike öztürk (95 min) → 0.900

### FINDING — Best performing students profile
melike öztürk: balanced profile, 27 emits, progressive depth escalation (2→4), accuracy 0.689→0.900
batuhan özger: feature_heavy, 7 valid emits, accuracy 0.545→0.818
oğuz köklü: feature_heavy, minimal actions, consistent accuracy around 0.70-0.77

---

## Pending Items

### PENDING — Researcher decision required
1. merve vs merve dede: RESOLVED — same person confirmed. Added to IDENTITY_OVERRIDES.
2. şeyda vs şeyda demirci: same person? If yes, uncomment line in IDENTITY_OVERRIDES in log_extractor.py.
3. Food dataset train/test annotation: which copy number was designated as train,
   which as test? Required before train_test_applied can be computed for 17 students.

### COMPLETE — Phase 1 (framework built, real prior-year examples loaded)
File: worksheet_assessor.py
Rubrics defined for 21 items across WS1, WS3, WS4, WS7, WS11, and WS DT (all 7 sections).
Few-shot examples: placeholder examples written for DT_A_Q4, DT_C_Q2, DT_F_Q2, DT_E_Q4.
COMPLETE: FEW_SHOT_EXAMPLES updated with real prior-year student responses (n=30 cohort, Code Schemes.xlsx).
  Source: CODAP Analiz sheet (qualitative coded notes with verbatim student quotes).
  Items covered by real examples: DT_A_Q2, DT_A_Q4, DT_B_Q4, DT_C_Q2, DT_C_Q3, DT_D_Q2, DT_D_Q4,
  DT_E_Q1, DT_E_Q4, DT_E_sensitivity, DT_E_MCR, DT_F_Q2, DT_G_Q1, DT_G_Q2.
  Note: student responses are in Turkish — expected and handled correctly.
PENDING: researcher must confirm correct answers for WS10 (energy threshold optimal value)
         since it depends on which physical food cards were used in class.
Assessment logic:
  - LLM scores open-ended items per rubric
  - Python arithmetic verifiers run independently for DT_E_sensitivity and DT_E_MCR
  - Log cross-checking built into assess_worksheet_dt() for DT items
  - Output: WorksheetAssessment Pydantic object with ItemScore per item

### TEST — worksheet_assessor.py red-team + stress test (38/38 passed)

File: test_worksheet_assessor.py

Vulnerabilities found and fixed:

1. _verify_sensitivity / _verify_mcr used positional-only args — keyword calls raised TypeError.
   Fix: renamed parameters to tp/fn/fp to accept both positional and keyword.

2. Turkish characters in 3 rubric fields:
   - DT_E_sensitivity.prompt_description: "duyarlılık" → "true positive rate"
   - WS1_objects.full_credit_criteria: "patlamış mısır" → "popcorn, apple, french fries"
   - WS1_features.prompt_description: "özellikler/değişkenler" → "variables / characteristics"
   Fix: replaced with English equivalents.

Red-team scenarios covered (RT-01 to RT-10):
- Prompt injection in student response: system enforces item_id and credit independently of response content
- LLM returning wrong item_id: caller's item_id always overrides LLM output
- LLM inventing invalid credit level: Pydantic raises ValidationError
- Empty/short llm_rationale: Pydantic min_length=10 enforces minimum
- Keyword stuffing: reaches LLM normally; rubric decision is LLM's
- Turkish student responses: pass through without crash
- Log contradiction flagging: flag value preserved correctly
- Numeric override: Python arithmetic verifier sets numeric_mismatch flag even when LLM says full credit
- Sensitivity written as percentage (82.4%): float() try/except catches gracefully, no crash

Stress scenarios covered (ST-01 to ST-25):
- Malformed JSON: json.JSONDecodeError propagates correctly
- Code-fenced JSON (```json and plain ```): both stripped
- Extra LLM fields: ignored by Pydantic
- Unknown item_id: silently skipped
- All blank responses: overall = not_attempted
- All full responses: overall = full
- Empty responses dict: ValidationError (min_length=1)
- Zero denominator in sensitivity/MCR: specific flags returned
- None inputs in arithmetic verifiers: return None cleanly
- System prompt: no Turkish characters
- Rubrics: no Turkish characters after fix

### DECISION — OCR approach: Claude multimodal vision, not Tesseract

Problem is two separate tasks:
1. Text reading (OCR): pixels → characters
2. Layout / structure understanding: which character block belongs to which question field

Tesseract solves only (1). It outputs a flat text stream with no notion of "this text is the answer to Question 3." Recovering that mapping requires additional coordinate extraction and template matching code — fragile and error-prone for handwritten worksheets where students write outside printed boxes.

Options evaluated:
A. Claude vision (multimodal) — chosen
   Claude reads the image AND understands visual-spatial context simultaneously.
   Single API call per page. No separate coordinate mapping needed.
   Works for handwritten Turkish without extra training.
   Fits naturally into existing Claude-based pipeline.
B. Document AI / layout-aware OCR (Google Document AI, Amazon Textract, Azure Form Recognizer)
   Designed for form field extraction. Would also solve the layout problem.
   Rejected: external service dependency, additional API cost, integration overhead
   not justified at 20-40 student scale.
C. Fixed template + coordinate map
   Most reliable if worksheet layout is identical across all students.
   Rejected for now: fragile if any student wrote outside printed areas.
   Can fall back to this if Claude vision struggles with specific pages.

Decision rationale:
- Scale is 20-40 students × 3 PDF sources = ~400-450 pages total.
- Claude vision API cost at this scale is acceptable.
- Zero additional infrastructure (no Tesseract install, no coordinate mapping code).
- Prompt directly encodes worksheet structure, so Claude returns pre-parsed JSON
  (section A Q1, section B threshold_1, etc.) in a single call per page.

### COMPLETE — OCR pipeline built with item-to-question mapping
File: ocr_pipeline.py
Model: claude-opus-4-8 (highest accuracy for handwritten Turkish)
DPI: 200 (1655x2340 px per page, confirmed working)
Output: ocr_output/{student}/worksheet_dt.json, worksheets_1-10.json, worksheet_11.json, composite.json

ALL_ITEM_IDS (24 total):
  DT: DT_A_Q1/Q2/Q4, DT_B_Q4, DT_C_Q2/Q3, DT_D_Q2/Q4,
      DT_E_sensitivity, DT_E_MCR, DT_E_Q1/Q4, DT_F_Q2, DT_G_Q1/Q2
  WS: WS1_objects/features/label, WS3_classification, WS4_T3, WS7_path_matching
  WS11: WS11_Q10/Q11/Q12

Output per student: ocr_output/{student}/responses.json
  {
    "student_name": "Daniella",
    "responses": { "DT_A_Q1": "...", "DT_A_Q2": "...", ... },  // 24 items
    "raw": { "worksheet_dt": {...}, "worksheets_1_10": {...}, "worksheet_11": {...} }
  }
  responses.json feeds directly into worksheet_assessor.py assess_item() calls.
  raw transcription retained for audit and re-mapping without re-calling API.

Two-layer architecture:
  Layer 1: transcribe_student_pages() — sends ALL student pages in ONE Claude call
           (multi-image message), returns item-keyed JSON directly
  Layer 2: extract_item_responses() — filters only rubric item_id keys from raw,
           flags "(missing)" for any item Claude did not return
  Layer 3: build_responses() — merges all three PDFs into one record per student,
           ensures all 24 item_ids are present in output

Design decisions:
- Multi-image single call (not per-page): avoids merge ambiguity when student
  answer spans across two pages; Claude sees full context
- Prompt directly asks for rubric item_ids by name: Claude maps text to question
  in one step, no post-hoc coordinate matching needed
- Page grouping: fixed stride (4 pages DT, 6 WS1-10, 3 WS11)
- Raw transcription kept: can re-run mapping without re-calling API
- Incremental save: each student saved immediately; safe to interrupt and resume
- JSON parse failures: returned as {_error: ...} so pipeline never crashes
- Rate limit: 20s * attempt backoff on RateLimitError

Usage:
  python ocr_pipeline.py pilot WorksheetDT.pdf 0       # single student pilot
  python ocr_pipeline.py WorksheetDT.pdf                # one PDF
  python ocr_pipeline.py                                 # all three PDFs

### TEST — ocr_pipeline.py red-team + stress test (64/64 passed after bug fixes)
File: test_ocr_pipeline.py

Red-team scenarios (RT-01 to RT-14):
- RT-01: Claude returns wrong item_id key (DT_A_Q3 instead of DT_A_Q2) — flagged as missing
- RT-02: Claude adds extra keys not in rubric — silently dropped, real items still present
- RT-03: Sentinel with wrong case ("(Bos)", "(OKUNAMIYOR)") — correctly treated as no-answer
- RT-04: Code-fenced JSON (```json) — stripped before parse
- RT-05: Student name with Turkish chars (Seyda Demirci) — dir creation does not crash
- RT-06: Claude returns nested dict for an item — converted to string
- RT-07: Claude returns empty string for item — normalized to (bos)
- RT-08: Claude guesses plausible answer for blank field (hallucination) — classified as
         ANSWERED so it surfaces in validate step for human review; not silently accepted
- RT-09: All items illegible — pipeline does not crash; all flagged as no-answer
- RT-10: Claude returns null/None for item — flagged as (missing)
- RT-11: Claude returns float (0.82) for formula field — converted to string
- RT-12: One PDF fails, other two succeed — error logged, other items still extracted
- RT-13: student_name key missing from model output — falls back to "student_NN"
- RT-14: Prompt injection in student answer — preserved verbatim, not acted on by OCR layer
- RT-15: Malformed JSON error dict — _raw contains stripped text, not response.content reference
- RT-16: _raw in error dict is post-strip text (no backtick fences)
- RT-17/18: Name collision across PDFs resolved by normalize_student_key() — "daniella" == "DANIELLA"
- RT-19: Partial last page group (101 pages / 4) — skipped, not silently processed as fake student
- RT-20: student_index out of range in pilot — returns {} not crash

Stress scenarios (ST-01 to ST-34):
- ST-01/02: ALL_ITEM_IDS = 24, all unique
- ST-03/04: PDF_ITEM_IDS union = ALL_ITEM_IDS, no item in multiple PDFs
- ST-05: PAGES_PER_STUDENT / PROMPTS / PDF_ITEM_IDS keys are identical sets
- ST-06/07/08: Each prompt contains all its item_id names; sentinel contract present
- ST-09: NO_ANSWER_SENTINELS all case-insensitive
- ST-10 to ST-15: extract_item_responses edge cases (empty dict, None, whitespace, multiline, Turkish)
- ST-16 to ST-20: build_responses invariants (24 items always present, coverage counts, error propagation)
- ST-21 to ST-23: image_to_base64 (rescale wide, preserve narrow, valid base64)
- ST-24 to ST-28: transcribe_student_pages mocked (code fence strip, malformed JSON, multi-image,
                  page labels, correct model = claude-opus-4-8)
- ST-29 to ST-31: is_answered edge cases ("0", "A", Turkish text — all ANSWERED)
- ST-32: Sentinels (bos)/(okunamiyor) present in all three prompts
- ST-33/34: No Turkish chars in item_id strings; all item_ids ASCII-only

Bugs fixed (discovered by tests):
1. raw_text reference bug: JSONDecodeError handler used "response" in dir() — unreliable.
   Fixed: raw variable (always defined when json.loads raises) used directly.
2. dry_run passed client=None to process_pdf — type violation.
   Fixed: dry_run() is a standalone function that never accepts or uses a client.
3. Partial last page group was silently processed as a fake student.
   Fixed: groups with len < pps are skipped with a printed warning.
4. Student name variants from different PDFs (daniella vs DANIELLA) created separate dirs.
   Fixed: normalize_student_key() applies title-case + underscore to all names before dir I/O.
5. mode_pilot item_coverage.total was len(responses) = 15 (DT only) — looked like 15/15 complete.
   Fixed: total_this_pdf and total_all_pdfs separate fields; note explains incomplete coverage.
6. No resume capability — crashed pipeline restarted from scratch.
   Fixed: process_pdf(resume=True) reloads from disk if raw JSON already exists for student.
   Added RT-40, ST-41, ST-42 tests covering these fixes.

---

## Session 4 — HTR Extraction Schema & Prompt Engineering

### DECISION — Slot marker filename format change
Old format: `.slot_{n:02d}_{pdf_stem}` (content = student name)
New format: `.{StudentName}_{pdf_stem}` (content = slot number, 1-based)
Rationale: filename communicates student identity at a glance in the filesystem;
content (slot number) allows resume logic to rebuild the slot→name map by scanning
`OUT_DIR.glob(f".*_{pdf_stem}")` before the processing loop begins.
Resume logic rewritten: pre-loop scan builds `done_slots: dict[int, str]`; loop
checks `if idx in done_slots` before calling API.
Test updated: PS20 now creates `.Daniella_worksheetdt` with content `"1"`.

### SCHEMA — DecisionTreeExtraction v1 added to worksheet_assessor.py

New models integrated into worksheet_assessor.py for structured HTR extraction
of student-drawn decision trees from handwritten worksheets.

Models added:
- `DataQuality`: `illegible_fields_found` (bool) + `bilingual_mapping_used` (list of correction strings)
- `RootNode`: `node_type` (default "Root"), `variable_feature`, `threshold_value` (float, comma-decimal aware)
- `SplitMetrics`: three separate fields -- `mcr_rate`, `accuracy_dogruluk`, `impurity_info`
- `DecisionTreeSplit`: `level` (ge=1), `parent_feature`, `path_direction` ("True/Yes"/"False/No"),
  `condition`, `result_node`, `metrics`
- `TreeExtraction`: `root_node` + `splits[]` with topology validator
- `DecisionTreeExtraction`: top-level object with `student_id`, `data_quality`, `tree_extraction`

Normalization helpers:
- `_coerce_threshold()`: float coercion with Turkish comma-decimal support ("10,5" -> 10.5)
- `_normalize_target()`: case-insensitive TARGET_CLASSES matching
- `_normalize_result_node()`: matches all three RESULT_NODE_CLASSES + Turkish alternates via `_RESULT_TR_ALTS`
- `_normalize_path_direction()`: accepts Turkish (evet/hayır/doğru/yanlış) and English variants
- `FEATURE_TR_TO_EN`: bilingual feature map including abbreviations (Sgr, Cal, Sod) and
  common misspellings (karbonidrat, egnergy)

### SCHEMA — DecisionTreeExtraction v2-v4: iterative improvements

Four rounds of prompt engineering with cumulative schema upgrades:

v1 (Prompt 1): basic extraction, no bilingual support, no pipeline, single MCR string
v2 (Prompt 2): CDR strategy added, 5-step chain-of-thought pipeline, data_quality block
v3 (Prompt 3): reinforcement_summary with correction audit trail, metric on root node,
               "Next Split Node" as valid result, Turkish framing in system prompt
v4 (Prompt 4 -- current): full bilingual dictionary with tree structure terms and
               abbreviation autocorrection, path_direction per branch, parent_feature per split,
               SplitMetrics sub-object with mcr_rate/accuracy_dogruluk/impurity_info,
               illegible_fields_found bool, bilingual_mapping_used audit trail

Prompt quality scores (peer evaluation):
  Prompt 1: 5.5/10 -- no bilingual support, no pipeline, no metrics sub-object
  Prompt 2: 6.5/10 -- good pipeline but no Turkish terms, no path_direction
  Prompt 3: 7.5/10 -- Turkish framing, correction audit, but no path_direction/parent_feature
  Prompt 4: 8.5/10 -- all structural gaps closed; remaining gap: no few-shot examples

### CODE — Final prompt upgrade: few-shot examples + 4 gap closures

Remaining gaps from Prompt 4 evaluation closed:

1. Few-shot JSON examples added to user template (not system prompt, so model sees
   examples alongside the actual worksheet image):
   - Example A: 1-level tree with Türkçe terms and MCR annotation
   - Example B: 2-level tree showing level 2 splits with parent_feature tracking
   - Example C: crossed-out threshold rewritten -- "revised: threshold old=5 new=8" log format
   - Example D: illegible leaf + unlabelled branch direction -- null fields with illegible=True

2. Deep tree coverage: Examples B and C demonstrate level 2/3 splits.
   Output rule added: "Include ALL split levels -- do not stop at level 1."

3. Threshold disambiguation rule (Section 2, Step 4d):
   "If ambiguous between integer and decimal (e.g. '8' vs '0.8'), prefer integer
   unless feature's known value range makes it implausible. Log ambiguity."

4. Crossed-out field handling (Section 2, Step 5):
   - Blank / single strikethrough -> null; log "crossed_out: <field_name>"
   - Written, crossed out, rewritten -> use rewritten value; log "revised: <field_name> old=X new=Y"
   - Smudged with >60% dictionary match -> use match; log correction
   - Smudged with <60% confidence -> null; set illegible_fields_found=True

Bug discovered and fixed during prompt implementation:
   `_normalize_result_node` did not map Turkish leaf alternates (Önerilir, Önerilmez,
   Tavsiye Edilebilir, Tavsiye Edilemez). Added `_RESULT_TR_ALTS` dict with 10 entries.

### CODE — Topology validator + validate_extraction()

`TreeExtraction.validate_topology()` (Pydantic model_validator, mode="after"):
  Enforces structural rule: every level-1 split's parent_feature must match root_node.variable_feature.
  Raises ValidationError if violated. Runs automatically on model construction.

`validate_extraction(ext: DecisionTreeExtraction) -> list[str]`:
  Post-construction plausibility checker. Returns warning strings, does not raise.
  8 checks:
  1. Root feature not in KNOWN_FEATURES
  2. Threshold outside plausible range for that feature (_THRESHOLD_PLAUSIBLE_RANGES)
  3. Level-1 split count != 2 (binary tree expectation)
  4. Both level-1 branches have the same path_direction
  5. result_node="Next Split Node" but no deeper splits exist
  6. Leaf result_node but deeper splits reference same parent_feature (topology contradiction)
  7. null result_node but illegible_fields_found=False (inconsistency)
  8. Prompt injection keywords in student_id or bilingual_mapping_used

_THRESHOLD_PLAUSIBLE_RANGES defined for all 12 features:
  Energy [50, 900], Fat [0, 80], Saturated Fat [0, 40], Carbohydrates [0, 120],
  Sugar [0, 80], Protein [0, 50], Salt [0, 10], Sodium [0, 3000],
  Fibre [0, 30], Price [0, 50], Taste Score [0, 10], Calories [50, 900]

### TEST — test_worksheet_assessor.py (70/70 passed)

New test file: test_worksheet_assessor.py
3 classes, 70 tests total.

TestHTRRedTeam (RT01-RT25) -- adversarial model outputs:
- RT01: Extra hallucinated keys ignored by Pydantic
- RT02/03: result_node case normalization (lowercase, ALL CAPS)
- RT04: Hallucinated feature not in KNOWN_FEATURES -> validate_extraction warning
- RT05/06: String "null" / "None" threshold -> None
- RT07: Both branches same path_direction -> warning
- RT08/09: level=0 / level=-1 -> ValidationError
- RT10: "next split node" lowercase -> "Next Split Node"
- RT11/12: Turkish path labels (evet, Hayır) -> canonical
- RT13: Unrecognized path_direction -> None (not crash)
- RT14/15: Prompt injection in student_id / bilingual_mapping_used -> warning
- RT16: Salt threshold 9999 -> plausible range warning
- RT17: null result but illegible=False -> inconsistency warning
- RT18: Next Split Node with no deeper splits -> warning
- RT19: Turkish comma threshold "10,5" -> 10.5
- RT20: DataQuality without illegible_fields_found -> ValidationError
- RT21: String "true" coerces to bool True
- RT22: Level-1 wrong parent_feature -> topology ValidationError
- RT23: Only 1 level-1 split -> binary tree warning
- RT24: student_id=None valid
- RT25: All-null SplitMetrics valid

TestHTRStress (ST01-ST35) -- handwriting edge cases:
- ST01-ST10: _coerce_threshold (integer, float, comma, zero, None, illegible,
             empty, small decimal, negative, large energy value)
- ST11-ST15: _normalize_path_direction (all True/Yes variants, all False/No variants,
             None, arrow symbol, question mark)
- ST16-ST21: _normalize_result_node (Turkish Önerilir/Önerilmez/Tavsiye Edilebilir,
             Next Split Node case variants, None, unknown passthrough)
- ST22-ST24: Multi-level trees (2-level, 3-level, empty splits)
- ST25-ST27: Null splits, empty bilingual list, 4-correction-type bilingual list
- ST28-ST31: SplitMetrics (fraction, percentage, decimal, all three populated)
- ST32: JSON round-trip lossless
- ST33-ST35: KNOWN_FEATURES frozenset, TARGET_CLASSES frozenset, node_type default

TestHTRQuality (QA01-QA10) -- validate_extraction checks:
- QA01: Clean extraction -> zero warnings
- QA02: Unknown feature warned
- QA03: Implausible Salt threshold warned
- QA04/05: Plausible Fat/Energy thresholds -> no warning
- QA06: Both directions same -> warned
- QA07: Next Split Node no deeper -> warned
- QA08: null result illegible=False -> warned
- QA09: Prompt injection student_id -> warned
- QA10: 3 level-1 splits -> warned

Bugs discovered by tests and fixed:
1. `_normalize_result_node` did not handle Turkish alternates.
   Fix: `_RESULT_TR_ALTS` dict added with 10 Turkish -> canonical mappings.
2. `make_ext` test helper used hardcoded "Fat" parent_feature regardless of root_feature.
   Fix: sentinel pattern (`_SENTINEL`) distinguishes default-splits from explicit empty list;
   default splits now use `root_feature` dynamically.
3. `splits=[]` was treated as falsy and replaced by default splits.
   Fix: sentinel object distinguishes explicit `[]` from "no argument given".

Total test count across both files: 153 (83 ocr_pipeline + 70 worksheet_assessor), 0 failures.

### PENDING — Phase 2 (pilot)
Screen recording + log analysis for 2-3 students.
Requires: researcher's prior-year Word notes.
Screen recording coding guide: screen_recording_analysis_guide.md (17 signal types, priority order defined)

### PENDING — Phase 3
Log CSV feature extraction — COMPLETE for CODAP log.
Pending: Python/Colab log files if they exist.

### PENDING — Phase 4
AI-CFT level assignment + pattern discovery.
Requires: Phases 1-3 complete for pilot cohort.
