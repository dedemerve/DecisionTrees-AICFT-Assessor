# Evaluation of the DecisionTrees-AICFT archive

The archive can show what was recorded, and whether two pipeline files tell the same story. It cannot yet show that an automated score or a behaviour label is independently correct. It is not a retrieval-augmented generation system, so retrieval metrics were not calculated.

The sentence above is the result of inspecting the code and running `evaluation/run_evaluation.py` on the 2026 files. Literature recommendations in the last section are design reasons. They are not findings from these fifteen participants.

## What the system actually is

A language model transcribes worksheet pages and describes screen frames. Rubrics and few-shot examples are written into the prompt (`worksheet_assessor.py`, `prompts/MMLA_CODAP_video_system_prompt.md`). Python then applies fixed rules for worksheets 5, 6, 7, and 10. CODAP rows are counted and ordered. Final notebooks are read, not executed.

Lewis et al. (2020) define retrieval-augmented generation as a retriever over an external corpus followed by a generator conditioned on the retrieved passages. This repository has no retrieval index and no ranked passage set. A helper in `scripts/codap_alignment.py` can attach a time window of log lines to a frame prompt, but the stored 2026 frame files do not keep that window: eight session files record `log_csv_used: false` and alignment method `unavailable`, and twelve session files do not store those fields. No frame record contains `log_context`.

The flow that is implemented is:

1. Source worksheets, recordings, CODAP logs, and final submissions.
2. Vision transcription, then mechanical normalisation.
3. Rule checks, or few-shot rubric scoring.
4. Review flags and five accepted score changes.
5. Frame selection and vision behaviour labels.
6. Session-level log summaries.
7. Notebook file inspection.
8. The public archive.

There is no train, validation, or test split for the assessor. The Hugging Face frame card does not declare one. Nothing in this evaluation was treated as a trained model score on a held-out partition.

## What was measured

### Transcription

The researcher compared extracted worksheet responses with the original handwriting and reports that the reading matched in every case. No item-level comparison log is stored, so the check cannot be recomputed. The report is about transcription fidelity. It does not establish conceptual correctness, rubric accuracy, or the accuracy of a later score.

### Accepted score changes and review flags

Unit: a scored item in the score summary. The summary has **2,367** items. A file enters it when the extraction is the one the archive publishes, the worksheet is not WS11, the file is not blocked, and the scores are not all confidence zero. A further 325 items sit in unused or unpublished files.

Five items store `researcher_override` and a rationale. All five are WS5_B25.

| Student | Final score | Rationale stored with the change |
| --- | --- | --- |
| Bruno | 1.0 | Correct variable and minimum-error threshold. Scorer failure only; the prompt prefix was unparseable. |
| Helena | 1.0 | Named variable and a tied minimum-error threshold. The student cited the lower error count. Scorer failure only. |
| Isabel | 1.0 | Named variable and a tied minimum-error threshold. Scorer failure only. |
| Melinda | 1.0 | Named threshold with a unit, 29 g = 29.0. Unique minimum-error trial. Scorer failure only. |
| Ulysses | 0.5 | Threshold in the grid (protein ≤ 2.0) but the worst trial, 5 errors. Rubric partial credit for a non-minimum grid threshold. |

None of the five stores the score it replaced. The size of each change cannot be measured. On each of the five rows, `review` is still true. The flag is not the accepted decision. The override and the rationale are.

In the score summary, **1,570** items have a review flag and **1,565** of those have no override. The flag is on 878 of 891 partial-credit items, 667 of 815 no-credit items, and 25 of 661 full-credit items. Worksheet 13 sets the flag when credit is partial or zero or when the model raised its own flag (`scripts/score_ws13.py`). A review flag is a pipeline marker. It is not evidence that a person accepted the score, and it is not evidence that the score is wrong.

### Rule-file agreement

Unit: an item present in both `scoring.json` and `validation.json` for WS5, WS6, WS7, or WS10, where the student worksheet has an extraction.

**189 of 201** items agree exactly. Mean absolute error on the 201 pairs is **0.057**. The reference is the validation file from the same pipeline. This is internal consistency, not agreement with an independent rater. Missing validation scores are excluded. They are not coded as zero.

Twelve items disagree:

- Six are WS5_B25, for Iris, Irma, Marcus, Nadia, Shana, and Zara. The check awards 1 and the score file stores 0. None of these six is an accepted change. The five accepted B25 changes are absent from the disagreement list because their final scores match the validation file.
- Sheila, WS5 row 1: score 1.0, validation 0.5.
- Helena, WS10_B8: score 1.0, validation 0.0.
- Isabel, WS10_B4 through WS10_B7: score 1.0, validation 0.0. For B4 the extraction stores “3”, the expected value is 3, and the check says the item is blank.

The evaluation does not overwrite any of these files and does not pick a winning score.

Rubric items have no second human score. MAE, exact agreement, and weighted kappa against a human rater were not calculated. That comparison requires human validation.

### Frames

Unit: a frame analysis with a primary behaviour. **5,248** frames are labelled, out of **5,584** listed in manifests.

| Label | Frames | Share |
| --- | ---: | ---: |
| EXPLORE_DATA | 1,810 | 34.5% |
| TUNE_THRESHOLD | 1,018 | 19.4% |
| COMPARE_MODELS | 936 | 17.8% |
| OFF_TASK | 741 | 14.1% |
| EVALUATE_MODEL | 416 | 7.9% |
| BUILD_TREE | 296 | 5.6% |
| IDLE_THINKING | 30 | 0.6% |
| INTERPRET_RESULTS | 1 | <0.1% |
| SELECT_TARGET | 0 | 0 |

The researcher has inspected the images. That inspection is a completed visual check. It is not precision, recall, or kappa. No second coder is in the active archive, so chance-corrected agreement was not calculated. `analysis_confidence` is the model’s own rating: 2,326 high, 2,906 medium, 16 low. Removing the 16 low-confidence frames leaves EXPLORE_DATA as the majority label.

The coding prompt tells the model to prefer a more common label when it is unsure, and to code SELECT_TARGET only when the frame shows the target being placed. The log records **1,328** `set_dependent_variable` events in the two CODAP sessions. The zero SELECT_TARGET count and the 1,328 events are different instruments. The zero is not evidence that no target was set.

### Logs, and whether the clock matters

Unit: the gap between two consecutive `emit_tree_data` events in one participant session. Inclusion: the two CODAP sessions, rows that resolve to the fifteen pseudonyms. There are **22** such sessions and **279** intervals.

`timestamp_ms` decreases along `created_at` in all 22 sessions. That is the reload reset described in `scripts/codap_alignment.py`. The published interval rule sorts by `timestamp_ms` and keeps events whose millisecond value falls strictly between two emits.

Reordering by `created_at`, and taking events that sit between emits in that order, produces the same category totals:

| Interval class | timestamp_ms | created_at |
| --- | ---: | ---: |
| Only attribute | 99 | 99 |
| Only threshold | 82 | 82 |
| Both or neither | 98 | 98 |

The sequence of categories differs in two sessions: Irma, CODAP session 2, and Nadia, CODAP session 2. The totals are stable. The within-session order is not, for those two.

Of the 82 wall-clock intervals that contain a threshold change and no attribute placement, 41 also contain no other configuration action (target change, tree-type change, focus swap, or refresh). 75 of the 82 are followed by a submitted payload with at least one changed numeric field. Accuracy differs in 71. Depth differs in 2. A threshold change is often followed by a different accuracy in the next submission, usually without a change in depth. That is a temporal association in the log. Other logged actions are present in half of these intervals, and unlogged state can change as well. The association does not show why the learner acted.

Interface rows (5,093) outnumber decision-action rows (3,029) in these sessions. A drag or a component change is a logged software event. It is not a strategy.

### Frame-to-log time

Frame time is seconds from the start of the recording. Log `timestamp_ms` is not that clock, and it resets. `created_at` is UTC wall time. The alignment fallback sets the recording start to the first log event when the video has no creation time, which makes the offset depend on the log. No matching window was applied. **No frame was paired with a log row.**

### Final submissions

Unit: one final file for each of 15 pseudonyms. Fourteen are notebooks. Marco’s is a written report. Notebooks were not executed again.

A train/test split is recorded in 15 of 15 files. A stored test misclassification rate is present for 37 of 41 described models. Those rates belong to the saved run. They were not recomputed, and they are not a score for the archive. A written question was found in 4 of 15 files. Where a trace is absent, the inspection did not find it. Absence is not a score of zero.

The inspection record marks Ulysses as using synthetic data. This evaluation did not re-derive that flag by running the notebook.

### Across sources

Six participants have frame manifests for both CODAP sessions. Nine have one. All fifteen have a final submission and at least one worksheet extraction. Worksheet coverage is not complete for every sheet; the existing quality audit records which sheets are missing.

Twenty-one sessions have both a frame manifest and a log. Twenty of those have labels and contain both at least one TUNE_THRESHOLD frame and at least one `change_split_values` row. That is complementary evidence: both instruments recorded threshold-related activity somewhere in the session. The counts are not a matched pair. Iris’s first session, for example, has 4 such frames and 77 threshold events. Irma’s first session has frames and 17 threshold events but no behaviour labels, so it is insufficient for this comparison. Missing labels were not treated as a count of zero tuning. No labelled session has TUNE_THRESHOLD frames and zero threshold events.

No cross-source pattern in these files supports a claim about a learner’s intention or a learning gain.

## What was not calculated, and why

| Question | Status | Why |
| --- | --- | --- |
| Precision@k, recall@k, MRR, nDCG | Not applicable | No retriever and no relevance judgements |
| RAG faithfulness or answer relevance | Not applicable | No retrieved context and no reference answers for a RAG task |
| Rubric score versus an independent human | Requires human validation | Transcription was checked. Rubric application was not independently rescored |
| Cohen’s kappa for behaviour labels | Requires human validation | The images were inspected. A second coder has not coded a subset |
| Frame-level alignment | Not established | The diagnostic ran and emitted zero pairs. That is not a completed alignment: the clocks do not support a match |
| Learning gain or strategy | Not calculated | Event counts and co-occurrence do not identify intention |

The machine-readable matrix is `evaluation/results/evaluation_matrix.json`.

## Error analysis

The disagreements that can be named from the files are the twelve rule-file mismatches above, the two sessions whose interval order changes with the clock, and Irma’s unlabelled first session. The six WS5_B25 cases where the check says full credit and the score file says zero are pipeline disagreements without a stored human resolution. They are not additional accepted changes.

Class imbalance in the frame labels is large: one INTERPRET_RESULTS frame, thirty IDLE_THINKING frames, and no SELECT_TARGET frames. A future kappa should be planned so that rare labels are actually present in the double-coded subset. With fifteen participants and incomplete session coverage, a confidence interval on a cohort effect would overstate what the sample can support. None was calculated.

## Literature that shaped the design

Sources are listed with links in `evaluation/literature_mapping.json`.

- Lewis et al. (2020) supply the definition that kept this pipeline out of the RAG category.
- Gao et al. (2023), Es et al. (2024), and Saad-Falcon et al. (2024) separate retrieval quality from generation quality and warn that an automatic judge is not a reference. That is why no RAGAS or ARES score was produced.
- Di Mitri et al. (2018) separate observable signals from latent states. Log rows stay observable. Intentions are not inferred.
- Sharma and Giannakos (2020) ask multimodal work to say what each modality can show. Sources were validated separately, then compared only at session level.
- Ferguson and Clow (2017) argue that activity data are not evidence of improved learning. This report does not claim a learning gain.
- Cohen (1960) is the statistic a two-coder nominal study of the behaviour labels would use. It was not applied.

## What a person still has to do

1. Double-code a subset of frames that includes the rare labels, without seeing the model label, then compute raw agreement and Cohen’s kappa.
2. Rescore a defined set of rubric items independently of the model, and keep that score separate from the transcription check.
3. Resolve the twelve rule-file disagreements, especially the six WS5_B25 rows that have no accepted change.
4. If frame-level alignment is required, record an independent start time for each video and a tolerance. Do not estimate the start from the first log row and then treat the match as confirmed.

## How to reproduce

```bash
python3 evaluation/run_evaluation.py
python3 -m pytest tests/test_evaluation_analysis.py -q
```

Outputs are written to `evaluation/results/` and `mmla_explorer/site/data/evaluation.js`. The script reads student files, frame analyses, and the CODAP log. It does not modify them.

## Unmet gates

The report brief specified the evaluation and asked for results rather than a planning dialogue, so the editorial gates were not confirmed in a separate exchange.

- Gate 0. Working sentence, inferred from the brief: the archive can show record consistency and coverage, and it cannot yet show independent correctness of scores or labels.
- Gate 0.5. Audience inferred as a scientific reader of the public archive.
- Gate 1. Falsifiers were taken from the brief: a real retrieval stage would have made RAG metrics applicable; a second coder would have made kappa applicable; a shared clock would have made frame matches applicable. None of those conditions held.
- Closing test. The argument in the opening paragraph still stands if the tables are removed. The tables name the cases.
