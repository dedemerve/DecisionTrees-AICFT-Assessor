# WS_DT scoring context

This file is injected alongside `stage3_scoring.md` when scoring WS_DT.

## Files to load

- Rubric: `rubrics/WS_DT_rubric.json`
- Mapping: `mappings/WS_DT_AICFT_mapping.json`
- Responses: `students/<student>.json → worksheets.WS_DT.extraction`

## Worksheet description

WS_DT is the CODAP Arbor plugged activity. Students build a decision tree interactively and answer open-ended questions in sections A through G. Section E includes sensitivity and MCR formula items (deterministic). Section F includes an overfitting reflection item (DT_F_Q2). Section G is a final consolidation reflection.

## Scoring notes

- Sections A-G: match each answer to the rubric item_id using section headings and question text, not page position alone. Section C printed Q2 → DT_C_Q2; Section C action/EMIT block → DT_C_Q1. Section D action block → DT_D_Q1.
- EMIT action items (B_Q1–Q3, C_Q1, D_Q1, F_Q1): capture variable, threshold, TP/FP/TN/FN when written. Partial metric-only notes are valid transcription.
- DT_E_sensitivity and DT_E_MCR: numeric values from Section E metric blanks. Stage 2 validates consistency only when confusion counts are also present.
- If a field is blank on the worksheet, transcribe as (bos) — do not infer from other sections.
- DT_E_Q1: metric preference question. Credit requires naming a metric AND giving a purpose-based justification (e.g., "sensitivity matters more because a false negative is more harmful").
- DT_E_Q4: perfect classification impossibility. Credit requires the student to identify data overlap or inseparability as the reason.
- DT_F_Q2 (overfitting): this is the strongest Create-level signal in the entire sequence. Award full credit only when the student explicitly names the train/test performance gap (good training, poor test). A partial answer that names overfitting without explaining the gap is partial credit.
- DT_G_Q1, DT_G_Q2: reflective items. Accept any evidence of metacognitive awareness. Set confidence lower than for factual items.
