# WS7 scoring context

This file is injected alongside `stage3_scoring.md` when scoring WS7.

## Files to load

- Rubric: `rubrics/WS7_rubric.json`
- Mapping: `mappings/WS7_AICFT_mapping.json`
- Responses: `ocr_output/<student>/WS7.json`

## Worksheet description

WS7 has two parts. Part 1 (P1_box1-box3): match three given if-then rules to labeled tree paths A, B, C. Part 2 (B1-B3): write original if-then rules consistent with the student's WS6 tree.

## Scoring notes

- P1_box1-box3: exact-answer items (B, A, C). If Part 1 is flagged as not captured in validation, set score null and review:true for all three items.
- B1-B3: check rule consistency with WS6. A rule is correct if it names the right feature, the right comparison operator, and the right outcome label. Accept different threshold values if the student used a valid threshold in WS6.
- B4-B7 are not applicable when the student's WS6 tree has 3 or fewer leaf paths. Do not score them.
