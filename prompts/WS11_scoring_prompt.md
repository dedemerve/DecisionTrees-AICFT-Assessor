# WS11 scoring context

This file is injected alongside `stage3_scoring.md` when scoring WS11.

## Files to load

- Rubric: `rubrics/WS11_rubric.json`
- Mapping: `mappings/WS11_AICFT_mapping.json`
- Responses: `ocr_output/<student>/WS11.json`

## Worksheet description

WS11 is the final reflection worksheet. B8a-B8b are classification and reasoning items. B9 asks for a general definition of decision trees. Q10 is a multi-select, Q11 is an ordering task, Q12 is a multi-select. Likert and demographic items (L10, L11, L12) are descriptive and not scored.

## Scoring notes

- B8a: exact answer (tavsiye edilmez or equivalent).
- B8b: requires both the condition (şeker > 10) and the outcome (tavsiye edilmez). A student who gives only the rule or only the outcome is partial credit.
- B9: semantic match. Accept any description that conveys recursive learning from data and a tree-like structure. "It looks like a tree" alone is not sufficient.
- Q10, Q11, Q12: deterministic multi-select and ordering checks. If any of these are missing from extraction, set score null and review:true.
