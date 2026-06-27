# Assessment pipeline

Each stage produces only its own output. JSON holds student data, not workflow state. The same files are read by different models, so each one is kept minimal.

## Stages

| Stage | Producer | Folder | Job |
|-------|----------|--------|-----|
| 1. Extraction | Claude Sonnet 4.6 Vision (WS6 uses Opus 4.8) | `ocr_output/<student>/WSx.json` | Transcribe what is on the page. No interpretation. |
| 2. Validation | Python | `validation/<student>/WSx.json` | Deterministic checks: answered, blank, illegible, missing, formula and arithmetic verification. |
| 3. Scoring | Claude Haiku 4.5 or Sonnet 4.6 | `scoring/<student>/WSx.json` | Score each item against the rubric: score, confidence, matched, review. |
| 4. Worksheet summary | Python | `summary/<student>/WSx.json` | total_score, max_score, and the learning outcomes the worksheet evidenced. |
| 5. Portfolio | AI-CFT assessor (after all worksheets) | `portfolio/<student>.json` | Aggregate LO evidence, propose an AI-CFT level. Researcher makes the final call. |

## Rules

1. A single worksheet never assigns an AI-CFT level. It only reports which learning outcomes it measured. Level assignment is cumulative and happens only at the portfolio stage.
2. The portfolio proposal is not final. `is_final: false`, `decision_owner: researcher`. The system presents evidence and a suggestion; the researcher decides.
3. Extraction never interprets. No snapshots, no observations, no completion judgments. That avoids hallucinated commentary and keeps the OCR output small.
4. Numeric and formula items are verified in Python at stage 2, never scored by an LLM.
5. Rubrics carry only what the scoring model needs: `max_score`, key concept lists (`rubric.full` / `rubric.partial`), `need` count, and `AI_CFT` outcomes. Formula and numeric items carry an `answer` and a `check`.

## Models

- Extraction: Sonnet 4.6 Vision for short symbolic worksheets, Opus 4.8 for the WS6 tree drawing.
- Validation and summary: Python only.
- Scoring: Haiku 4.5 for short binary or single-concept items, Sonnet 4.6 for partial-credit and free-text items.
- Portfolio: an AI-CFT assessor that proposes a level from aggregated evidence; the researcher finalizes.
