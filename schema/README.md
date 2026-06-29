# Schema catalog

JSON Schema (draft 2020-12) contracts under `schema/`. Instances are validated with:

```bash
pip install -r requirements.txt
python validate_schemas.py          # bundles + framework + mappings
python scripts/validate_worksheet_bundles.py  # bundles + OB cross-checks
python validate_pipeline_outputs.py # Sample_Student pipeline artifacts
```

`schema_json_validate.py` loads all `*.schema.json` files into a shared registry. `schema_validate.py` adds hand-written domain rules (portfolio policy, evidence-unit inferential guards).

## Worksheet bundles (`worksheets/<WS>/`)

| Schema | Instance file | Worksheets |
|--------|---------------|------------|
| `extraction_schema` | `extraction_schema.json` | WS1, WS3–WS7, WS10, WS11, **WS_DT** |
| `rubric` | `rubric.json` | same (+ legacy copy in `rubrics/`) |
| `behaviour_opportunities` | `behaviour_opportunities.json` | same |
| `validity_notes` | `validity_notes.json` | same |
| `answer_key` | `answer_key.json` | same |

Worksheet IDs use `common.schema.json#/$defs/worksheet_id` → `^(WS\d+|WS_DT)$`.

**WS_DT** is CODAP/plugged; behaviour opportunities may list extraction fields only (OB map lives in `mappings/WS_DT_AICFT_mapping.json`).

## Student pipeline (`students/<id>/<WS>/`)

| Schema | Instance | Notes |
|--------|----------|-------|
| `student_extraction` | `extraction.json` | Stage envelope + `responses` |
| `validation` | `validation.json` | WS5, WS6, WS7 required |
| `scoring` | `scoring.json` | |
| `evidence` | `evidence.json` | Legacy LO mapping (deprecated write path) |
| `summary` | *(not persisted)* | Derived from `scoring.json` in memory |

## Framework (`framework/`)

| Schema | Instance |
|--------|----------|
| `observable_behaviours` | `Observable_Behaviours.json` |
| `learning_objects` | `Learning_Objects.json` |
| `behaviour_to_ilo` | `Behaviour_to_ILO.json` |
| `domain_understanding` | `Domain_Understanding.json` |
| `lo_to_domain_understanding` | `LO_to_Domain_Understanding.json` |
| `domain_to_ai_cft` | `Domain_to_AI_CFT.json` |

Milestone validators (`scripts/validate_*.py`) enforce additional scientific rules beyond JSON Schema.

## Mappings & portfolio

| Schema | Instance |
|--------|----------|
| `mapping` | `mappings/*_AICFT_mapping.json` |
| `portfolio` | `students/<id>/portfolio.json` |
| `evidence_units` | `students/<id>/evidence_units.json` |

## Runtime / optional

| Schema | Instance | Notes |
|--------|----------|-------|
| `ocr_output` | `ocr_pipeline` gate checks | Simplified `{worksheet, student_id, responses}` |
| `layout_roi` | `layout_rois/<student>/*_layout.json` | Gitignored; may be embedded in extraction |

## Not in `schema/`

- `framework/architecture_spec.json` — meta spec
- `mappings/AICFT_assessment_framework.json` — canonical competency framework (generator output)
- `reports/milestone*_validation.json` — milestone analytics (different from `validation`)
