# WS11 scoring context

This file is injected alongside `stage3_scoring.md` when scoring WS11.

## Files to load

- Rubric: `rubrics/WS11_rubric.json`
- Mapping: `mappings/WS11_AICFT_mapping.json`
- Responses: `students/<student>.json → worksheets.WS11.extraction`

## Worksheet description

WS11 is the final reflection worksheet. B8a-B8b are classification and reasoning items. B9 asks for a general definition of decision trees. Q10 has 8 true/false sub-items (WS11_Q10_1..8). Q11 has 3 ordering sub-items for steps 2-4 (WS11_Q11_2..4; step 1 is pre-filled). Q12 has 5 multiselect sub-items (WS11_Q12_1..5). Likert and demographic items (L10, L11, L12) are descriptive and not scored.

## Scoring notes

- B8a: exact answer (tavsiye edilmez or equivalent).
- B8b: requires both the condition (şeker > 10) and the outcome (tavsiye edilmez). A student who gives only the rule or only the outcome is partial credit.
- B9: semantic match. Accept any description that conveys recursive learning from data and a tree-like structure. "It looks like a tree" alone is not sufficient.
- Q10_1..8: deterministic true/false checks per statement. Q11_2..4: ordering steps 2-4. Q12_1..5: multiselect sub-items (credit for correct mark/unmark). Score each sub-item independently. If any sub-item is missing from extraction, set score null and review:true for that sub-item.
