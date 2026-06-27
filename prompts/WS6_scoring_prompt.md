# WS6 scoring context

This file is injected alongside `stage3_scoring.md` when scoring WS6.

## Files to load

- Rubric: `rubrics/WS6_rubric.json`
- Mapping: `mappings/WS6_AICFT_mapping.json`
- Responses: `ocr_output/<student>/WS6.json`

## Worksheet description

WS6 asks students to draw a decision tree. The tree is evaluated structurally (tree_structure) and by the correctness of branch labels (branch_labels).

## Scoring notes

- tree_structure: validated deterministically in Stage 2. Check that the tree has at least 2 levels, uses different features at different nodes, has labeled leaves (tavsiye edilir / edilemez or equivalent), and uses consistent comparison operators.
- branch_labels: the student must label branches with evet/hayır (or equivalent true/false), and at least one node must show a threshold operator (≤ or >).
- If the OCR extraction captures a description of the tree rather than a structural representation, apply the rubric to the described structure and set confidence lower.
