# WS4 scoring context

This file is injected alongside `stage3_scoring.md` when scoring WS4.

## Files to load

- Rubric: `rubrics/WS4_rubric.json`
- Mapping: `mappings/WS4_AICFT_mapping.json`
- Responses: `students/<student>/WS4.json → extraction`

## Worksheet description

WS4 asks the student to find the best threshold from a sorted value list by minimizing MCR. B1 is the optimal threshold value, B2 is the selection criterion, B3 is the comparison, B4 is the MCR formula, B5 is evaluation of a peer's answer.

## Scoring notes

- B1: accept any valid midpoint between two adjacent values that minimizes misclassification. Tolerance is defined in the rubric.
- B2: credit requires the student to name MCR or "minimum misclassification" as the criterion.
- B3: credit requires comparing two specific MCR values (not just listing one).
- B4: formula item. Deterministic check in Stage 2; use that result.
- B5 (Pia evaluation): award credit when the student identifies that Pia's answer is correct and names the supporting evidence (lowest error rate or equivalent).
