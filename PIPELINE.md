# Assessment pipeline

Each student has **one output file**: `students/<student_id>.json`. Worksheet stages are sections inside that file, not separate folders.

## Student bundle (`students/<student>.json`)

| Section | Producer | Job |
|---------|----------|-----|
| `worksheets.<WS>.extraction` | Claude Sonnet 4.6 Vision (WS6 tree: Opus 4.8) | Transcribe what is on the page. Layout/HTR for WS5, WS6, WS10. |
| `worksheets.<WS>.validation` | Python | Answered / blank / missing checks; formula and numeric verification. |
| `worksheets.<WS>.scoring` | Claude Haiku 4.5 or Sonnet 4.6 | Score each item: score, confidence, learning outcomes, review flag. |
| `worksheets.<WS>.summary` | Python | `total_score`, `max_score`, worksheet-level LO peaks. |
| `portfolio` | AI-CFT assessor | Aggregate LO evidence, propose an AI-CFT level. Researcher makes the final call. |
| `combined_responses` | OCR pipeline | Flat `item_id → answer` map across all worksheets. |

## Supporting artifacts (not per-worksheet JSON)

| Path | Purpose |
|------|---------|
| `ocr_output/<student>/` | Raw OCR dumps + page images from PDF conversion |
| `layout_rois/<student>/` | OpenCV crops and layout manifests (WS5, WS6, WS10) |

## Rules

1. A single worksheet never assigns an AI-CFT level. Level assignment is cumulative and happens only in `portfolio`.
2. The portfolio proposal is not final: `is_final: false`, `decision_owner: researcher`.
3. Extraction never interprets student ability — only transcribes.
4. Numeric and formula items are verified in Python at validation, not scored by an LLM.
5. Rubrics use Schema 3.0 (`components[].idea` for semantic items).

## Commands

```bash
python ocr_pipeline.py full              # OCR → students/<id>.json
python run_phase2.py Sample_Student      # layout + WS10 HTR → bundle
python calibrate_scoring.py Sample_Student # confidence calibration
python validate_pipeline_outputs.py      # CI contract check
```

Migrate old per-folder JSON (one-time):

```bash
python student_bundle.py migrate <student_id>
```
