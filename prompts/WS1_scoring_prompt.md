# WS1 scoring context

This file is injected alongside `stage3_scoring.md` when scoring WS1.

## Files to load

- Rubric: `rubrics/WS1_rubric.json`
- Mapping: `mappings/WS1_AICFT_mapping.json`
- Responses: `students/<student>.json → worksheets.WS1.extraction`

## Worksheet description

WS1 is a vocabulary worksheet. Students define 11 machine learning terms: instance, attribute, label, threshold, decision rule, true positive, false positive, sensitivity, MCR, overfitting, decision tree.

B8 (sensitivity) and B9 (MCR) are formula items validated deterministically in Stage 2. Use the validation output; do not re-evaluate the formula arithmetic.

## Scoring notes

- B1-B7, B10, B11: semantic matching against rubric.full concepts. Accept paraphrases and equivalent terminology.
- B10 (overfitting): a one-sided answer that names only "good training performance" without mentioning "poor generalization" is partial credit. This item carries an early-indicator signal for LO3.2.3 only when both components are expressed.
- B11: student must reference at least 2 of the structural concepts (nodes, branches, leaves, recursive learning) for full credit.
