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
| A — LLM scoring sufficient | WS1, WS3, WS4, WS10, WS11 | No |

**WS4 (Group A):** B2 (`unordered_token_set`, four foods) and B5 (`numeric_range` 160–2223) are scored deterministically in Python; B1, B3, B4 are interpretive. After OCR, run `python scripts/build_evidence_units.py <student_id>` so `evidence_units.json` matches `extraction.json`.
| B — deterministic checks | WS5, WS6, WS7 | Yes (technical only) |

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
| `schema/portfolio_v1.schema.json` | Portfolio rollup contract |
| `schema/mapping_v2.schema.json` | Competency mapping contract |
| `schema/README.md` | Full schema ↔ instance catalog |

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
python -c "from student_bundle import migrate_student_to_v30; migrate_student_to_v30('Sample_Student')"
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
