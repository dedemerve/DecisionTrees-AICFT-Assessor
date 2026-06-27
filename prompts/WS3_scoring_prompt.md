# WS3 scoring context

This file is injected alongside `stage3_scoring.md` when scoring WS3.

## Files to load

- Rubric: `rubrics/WS3_rubric.json`
- Mapping: `mappings/WS3_AICFT_mapping.json`
- Responses: `ocr_output/<student>/WS3.json`

## Worksheet description

WS3 applies a pre-defined fat rule (threshold 8.0 g) to classify 3 foods (B1-B6), then asks the student to choose their own energy threshold (B7-B8).

## Scoring notes

- B1, B3, B5: exact-answer items. Accept minor spelling variation; reject if the classification direction is wrong.
- B2, B4, B6: reason items. Award credit when the student names the relevant feature and compares it to a threshold value. The specific number does not need to match exactly.
- B7-B8: the student defines their own threshold. Accept any defensible numeric value. Score on whether the student identifies the correct variable (enerji/energy) and uses the correct comparison operator (≤ for B7, > for B8). A wrong variable is zero credit regardless of operator.
