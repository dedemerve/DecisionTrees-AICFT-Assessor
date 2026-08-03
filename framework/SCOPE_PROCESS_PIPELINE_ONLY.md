# Active research scope: process pipeline (no scoring)

Date: 2026-07-20

## Decision

Q1 target is **pipeline / process data / methods**, not measurement-instrument validation or student proficiency scoring.

## What was done

Scoring-related files were **moved** (not deleted) to:

`trash/scoring_out_of_scope_2026-07-20/`

Including: construct_scores, calibration/fewshot/IRR/validation packages, mmla_scorer, scoring rubrics, scoring prompts/schemas/scripts.

## What stayed active

- Expert process narratives  
- Process codes (V-layer) + tabular/HF export  
- Log process metadata  
- Video analysis bundles (rewritten process-only)  
- Video process codebook  

## Frozen path exception

`data_sources_2025/all_students_2025_scores.json` was **not moved** (frozen research tree). Treat as unused / out of scope for active claims.

## Restore

```bash
mv trash/scoring_out_of_scope_2026-07-20/<relative/path> <relative/path>
```

---

## NON-GOALS

These are **scope decisions**, not limitations. They protect the integrity of Q1 research claims and must not be reversed without a formal scope change decision.

1. **No proficiency scores or construct levels.** This dataset does not provide B0-B13 scores or AI-CFT construct levels. V-layer process codes are not proficiency scores and must not be interpreted as such.

2. **Not validated as a scorer training set.** The dataset has not been validated as training data for an automated proficiency scorer. Single-observer heuristic labels are not equivalent to adjudicated construct ratings.

3. **No IRR for proficiency constructs.** Inter-rater reliability has not been established for B0-B13 constructs. Any IRR figures in quarantined files apply to a prior scope and must not be cited as active validity evidence.

4. **Model outputs are not proficiency measures.** Results from process classifiers trained on this dataset cannot be interpreted as measures of student AI-CFT proficiency without independent validity evidence beyond Q1 scope.

5. **Not appropriate for high-stakes automated assessment.** The dataset is not appropriate for deployment in high-stakes automated assessment contexts without additional validity evidence, adversarial testing, and ethical review.

6. **Do not delete or move frozen research trees.** `data_sources_*`, `students/`, `ocr_output/`, and `answer_key_worksheets/` are frozen. Their contents may be out of scope but must not be deleted.

> Cross-referenced in: `DATASET_CARD.md` § Non-intended uses, `framework/VIDEO_PROCESS_CODEBOOK_v1.md` § Process-only scope note.
