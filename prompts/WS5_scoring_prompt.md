# WS5 scoring context

This file is injected alongside `stage3_scoring.md` when scoring WS5.

## Files to load

- Rubric: `rubrics/WS5_rubric.json`
- Mapping: `mappings/WS5_AICFT_mapping.json`
- Responses: `students/<student>.json → worksheets.WS5.extraction`

## Worksheet description

WS5 is a threshold grid. Students fill rows in a table: each row has a candidate threshold, TP/FP/FN/TN counts, and an MCR. B25 is the final threshold choice with a written justification.

## Scoring notes

- row1-row5: each row is scored for internal consistency (TP+FP+FN+TN = dataset size, MCR = (FP+FN)/N). Validated deterministically in Stage 2; use that result for the numeric check. Award partial credit if the threshold and direction are correct but one count is off by 1.
- B25: requires a specific numeric threshold AND a data-based justification (e.g., "MCR is lowest at this value"). A threshold without justification is partial credit.
