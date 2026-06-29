# Assessment pipeline (schema 3.0)

Per-student output lives under `students/<student_id>/` — **modular stage artifacts per worksheet**, plus a portfolio file.

## Layout

```
students/Sample_Student/
  WS1/
    extraction.json
    scoring.json
    evidence.json
  WS5/
    extraction.json
    validation.json    # Group B only (WS5, WS6, WS7)
    scoring.json
    evidence.json
  ...
  portfolio.json
```

### Worksheet groups

| Group | Worksheets | `validation.json` |
|-------|------------|-------------------|
| A — LLM scoring sufficient | WS1, WS3, WS4, WS10, WS11 | No (optional for WS10) |
| B — deterministic checks | WS5, WS6, WS7 | Yes (technical only) |

Central blank → field mapping and scoring modes: `worksheet_blank_registry.py` (enriched into each `worksheets/<WS>/extraction_schema.json` at bundle build time).

**WS4 (Group A):** B2 (`unordered_token_set`, four foods) and B5 (`numeric_range` 160–2223) are scored deterministically in Python; B1, B3, B4 are interpretive. After OCR, run `python scripts/build_evidence_units.py <student_id>` so `evidence_units.json` matches `extraction.json`.

**WS10 (Group A):** Fixed energy table — printed blanks **1–8** (red on worksheet); B1–B7 misclassification counts `[4,3,2,3,2,1,2]`; B8 optimum **408**. Exact integer match via `ws10_validation.py`. HTR: `ws10_table_extractor` maps table column → B1–B7. Optional: `python scripts/validate_ws10.py <student_id>` and `python scripts/score_ws10.py <student_id>`.

**WS5 (Group B):** Row checks use `data/prodabi_food_cards.csv` (N=11). Pipeline: **vision OCR → `ws_extraction_normalize` (mechanical fixes) → `ws5_validation` (deterministic rules)**. Run `python scripts/validate_ws5.py <student_id>` after extraction; `python scripts/score_ws5.py <student_id>` for scores. Complementary operator pairs (≤↔>, <↔≥, ≥↔<, >↔≤); counts and MCR are rule-checked — not ML-scored.

**WS6 (Group B):** Same 11 cards, two-level tree. **OCR fields B1–B13 are sufficient** for validation/scoring; optional `dt_vision_pipeline` crop is supplementary extraction only. Same hybrid: vision extracts, Python validates. MCR=0 with two levels is valid.

**WS7 (Group B):** Part 1 — fixed enerji/protein sample tree; single correct path letter per `WS7_P1_box1`–`box3` (B, A, C). Part 2 — if-then rules vs student's WS6 tree; operators `<` `>` `≤` `≥` must match exactly. Run `python scripts/validate_ws7.py <student_id>` and `python scripts/score_ws7.py <student_id>`.

### Blank numbering and scoring modes (by worksheet)

| Worksheet | Blank model | `scoring_mode` | Validation |
|-----------|-------------|----------------|------------|
| WS10 | Printed 1–8 → fixed integers | `fixed_exact` | `ws10_validation.py` |
| WS7 P1 | Boxes 1–3 → B, A, C | `fixed_exact` | `ws7_validation.py` |
| WS7 B1–B3 | Cross-ref student WS6 tree | `cross_worksheet` | `ws7_validation.py` |
| WS5 / WS6 | B-fields → computed from 11 cards + tree | `computed` | `ws5_validation.py` / `ws6_validation.py` |
| WS1 | Printed blanks 5–11 | `equivalence` / `fixed_exact` | rubric checks / LLM |
| WS3 / WS4 | B1…Bn aligned to rubric items | mixed | LLM + partial Python (WS4 B2, B5) |
| WS11 | Q1–Q5 survey + Q6–Q7 demographics | `survey` / `demographic` | LLM (cognitive B8–Q12 only) |
| WS_DT | Section A/Q items | `interpretive` | LLM |

### WS5 / WS6: hybrid extraction + rules (no ML scoring)

| Stage | Technology | Role |
|-------|------------|------|
| Extraction | Claude vision (`ocr_pipeline`) | Transcribe B-fields verbatim from scan |
| Normalize | `ws_extraction_normalize.py` | Fix mechanical OCR typos (`=<` → `<=`); raw `extraction.json` unchanged |
| Validate + score | `ws5_validation.py` / `ws6_validation.py` | Your rubric rules: 11 cards, complementary operators, MCR |

Scoring logic stays deterministic — vision models do not assign points. Optional `dt_vision_pipeline` for WS6 tree crops is extraction-only.

### Stage artifacts

| File | Role |
|------|------|
| `extraction.json` | OCR / layout / HTR responses |
| `validation.json` | Pipeline health: parse success, tree detection, deterministic checks (Group B only) |
| `scoring.json` | Item scores, confidence, review flags, totals (`total_score`, `max_score`) |
| `evidence.json` | Per-item LO evidence (input to portfolio builder) |

Worksheet scorecard views (`review_items`, `blocked`) are derived in memory from `scoring.json` (and `validation.json` for technical `blocked`) — not persisted.

`portfolio.json` — AI-CFT rollup across all worksheets (LO peaks, proposal, data gaps). Worksheet scorecards do **not** assign AI-CFT levels.

Envelope fields (`schema_version`, `stage`, `student_id`, `worksheet`, `updated_at`) appear once per artifact file.

## Competency framework (v2.0)

Performance-based assessment mappings live in:

| File | Role |
|------|------|
| `mappings/AICFT_assessment_framework.json` | Canonical framework: competency definitions, worksheet profiles, item→competency priors with rationale |
| `mappings/AICFT_LO_definitions.json` | Inverted index: LO → worksheet evidence |
| `mappings/<WS>_AICFT_mapping.json` | Per-worksheet scorer view (schema 2.0) |
| `schema/portfolio.schema.json` | Portfolio rollup contract |
| `schema/mapping.schema.json` | Competency mapping contract |
| `schema/README.md` | Full schema ↔ instance catalog |

Regenerate worksheet bundles after rubric or registry changes:

```bash
python scripts/build_worksheet_bundles.py
python scripts/refresh_sample_student.py Sample_Student
```

Install validation dependency and run JSON Schema checks:

```bash
pip install -r requirements.txt
python validate_schemas.py
```

Regenerate all mapping artifacts after editing competency logic:

```bash
python scripts/build_aicft_framework.py
```

Worksheet-specific scorer context (edge cases, Section A/Q11 rules):

| Prompt | Covers |
|--------|--------|
| `prompts/WS4_scoring_prompt.md` | B1 threshold line, B2 four foods, B3 improvement, B4 Pia/same fat, B5 energy range |
| `prompts/WS11_scoring_prompt.md` | Q11 ordering → LO3.1.2 procedural workflow |
| `prompts/WS_DT_scoring_prompt.md` | Section A Q1 baseline vs Q2–Q4 data interpretation |

## Supporting artifacts

| Path | Purpose |
|------|---------|
| `worksheet_blank_registry.py` | Printed blank → field_id → scoring_mode for all deployed worksheets |
| `data/ws10_energy_reference.json` | WS10 blank 1–8 → fixed responses |
| `data/ws7_sample_tree.json` | WS7 Part 1 reference tree (P1 = B, A, C) |
| `data/ws11_feedback_reference.json` | WS11 printed Q1–Q7 question text and allowed responses |
| `data/prodabi_food_cards.csv` | WS5/WS6 card counts and MCR ground truth |
| `ocr_output/<student>/` | Raw OCR dumps + page images |
| `layout_rois/<student>/` | OpenCV crops and layout manifests |

## Commands

```bash
python ocr_pipeline.py full
python run_phase2.py Sample_Student
python calibrate_scoring.py Sample_Student
python validate_schemas.py
python validate_pipeline_outputs.py
```

Migrate legacy combined `students/<id>/WS*.json` (v2.1):

```bash
python -c "from student_bundle import migrate_student_worksheets; migrate_student_worksheets('Sample_Student')"
```

Build portfolio from all worksheet evidence (AI-CFT level proposal):

```bash
python run_portfolio_builder.py Sample_Student
```

Typical pipeline order:

```bash
python ocr_pipeline.py full              # extraction
python run_phase2.py Sample_Student      # layout + HTR + WS6
# scoring + evidence (LLM or deterministic modules)
python calibrate_scoring.py Sample_Student
python run_portfolio_builder.py Sample_Student
python run_research_dashboard.py Sample_Student
python validate_pipeline_outputs.py
```
