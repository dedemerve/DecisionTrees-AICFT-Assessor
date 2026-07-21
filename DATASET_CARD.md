# Dataset Card: CODAP Arbor Process Codes (2025 + 2026 Cohorts)

**Version:** 1.3 | **Date:** 2026-07-21 | **Scope:** process pipeline / methods (no proficiency scoring)

---

## (a) Task description

This dataset captures **video-observable learning process patterns** from CODAP Arbor screen recordings. Students used CODAP Arbor to build decision tree models on a classification task. The pipeline extracts expert process narratives, segments sessions into episodes, and assigns V-layer process codes (V1A–V8D) to each episode.

The unit of analysis is the **episode**: a meaningful behavioral segment defined by anchor-event transitions (typically 30–90 seconds). Each episode receives a binary decision (`observed` / `not_observed` / `not_measurable`) for each of 20 process codes.

This is a **sparse multi-label process dataset**, not a proficiency scoring dataset.

---

## (b) Source data

| Property | Value |
|---|---|
| Task | CODAP Arbor decision tree modeling (classification) |
| Recording type | Screen recordings (full-session video) |
| Cohort | 2025, n=17 students |
| Total sessions | 17 |
| Total episodes | 211 |
| Total decision cells | 4,220 (211 episodes × 20 codes) |
| Video duration | ~15 min per session (range varies) |
| Event log available | No (2025 cohort; planned for 2026) |
| Language of narratives | Turkish (uzman_nitel_gözlemi field) |

---

## (c) Annotation procedure

**Primary source:** Single expert observer per session. Observations were written as free-text `uzman_nitel_gözlemi` narrative steps, then converted to structured episode-level V-code decisions by the pipeline.

**Self-adjudication path (single researcher):** Dual-rater adjudication is **not** used. A frozen 30-episode calibration set is expert-coded twice (Pass 1 / Pass 2, ≥7-day washout), then reconciled with written rationales. See `training_datasets/2025/adjudication/`.

**Claim lock:** Expert-coded, self-adjudicated 2025 process training subset; pilot-model-ready for active V-codes. Not dual-rated; not all-20-codes training-ready.

**Label origin tiers** (field: `confidence_tier` in `exports/tabular/<id>_episode_process_codes.parquet`):

| Tier | Meaning | Count (observed cells) |
|---|---|---|
| T1 | Video-behavioral evidence: behavior directly visible, episode has gold screenshot frame anchor | 163 / 260 (63%) |
| T2 | Narrative-inferred: analyst inferred from text without direct frame anchor | 7 / 260 (3%) |
| T3 | Expert self-adjudicated: Pass 1 → Pass 2 → human evidence review; written rationale for all 9 disagreements | 90 / 260 (35%) |

**Gold tier** (field: `gold_tier`): 600 calibration cells carry `expert_adjudicated` (30 episodes × 20 codes). Remaining 3,620 cells are `single_observer`. The `gold_tier` and `confidence_tier` fields are present on all 4,220 rows.

---

## (d) Label schema

20 V-layer process codes across 8 families. Each code takes one of three decision states per episode.

| Family | Codes | Process dimension |
|---|---|---|
| V1 | V1A, V1B | Iteration quality |
| V2 | V2A, V2B | Cognitive load and usability strain |
| V3 | V3A, V3B | Engagement and persistence |
| V4 | V4A, V4B | Error recovery and resilience |
| V5 | V5A, V5B | Social dependence and help-seeking |
| V6 | V6A, V6B, V6C | Misconception traces |
| V7 | V7A, V7B, V7C | Video-only negative evidence |
| V8 | V8A, V8B, V8C, V8D | CODAP-specific strategic organization |

See `framework/VIDEO_PROCESS_CODEBOOK_v1.md` for full definitions, detection rules, and the V7 negative-evidence pre-check protocol.

---

## (e) Splits

Student-level splits (no episode-level mixing). Stratified by episode count.
See `training_datasets/2025/split_assignment.json` — frozen; do not re-randomize after modeling.

| Split | Students (n) | Episodes | Decision cells |
|---|---|---|---|
| train | 11 | 117 | 2,340 |
| dev | 3 | 47 | 940 |
| test | 3 | 47 | 940 |

**Train students:** Bob, Calvin, Daisy, David, Edgar, Eliot, Felicity, Henry, Mike, Ozzy, Sabrina

**Dev students:** Ally, Boris, Daryl

**Test students:** Barbara, Frank, Zabby

---

## (f) Class distribution per code per split

Overall observed rate: **6.0%** (252 / 4,220 cells) after full V7 precheck automation. Severe class imbalance; see § Imbalance treatment.

Per-code loss weights: `training_datasets/2025/cohort_imbalance_weights.json`.

| Code | Label | Total obs (rate) | Train obs/117ep (rate) | Dev obs/47ep | Test obs/47ep | Train status |
|---|---|---|---|---|---|---|
| V1A | systematic_iteration | 68/211 (32.2%) | 35 (29.9%) | 17 | 16 | active |
| V1B | chaotic_iteration | 0/211 (0.0%) | 0 | 0 | 0 | **zero-train** |
| V2A | hesitation_disorientation | 6/211 (2.8%) | 3 (2.6%) | 1 | 2 | active |
| V2B | interface_cycling | 0/211 (0.0%) | 0 | 0 | 0 | **zero-train** |
| V3A | sustained_engagement | 0/211 (0.0%) | 0 | 0 | 0 | **zero-train** |
| V3B | disengagement_passivity | 8/211 (3.8%) | 8 (6.8%) | 0 | 0 | active |
| V4A | productive_recovery | 8/211 (3.8%) | 5 (4.3%) | 1 | 2 | active |
| V4B | dead_end_loop | 2/211 (0.9%) | 1 (0.9%) | 1 | 0 | active (sparse) |
| V5A | productive_help_seeking | 0/211 (0.0%) | 0 | 0 | 0 | **zero-train** |
| V5B | dependent_execution | 46/211 (21.8%) | 19 (16.2%) | 5 | 22 | active |
| V6A | mcr_zero_targeting | 2/211 (0.9%) | 0 (0.0%) | 1 | 1 | **zero-train** (dev/test only) |
| V6B | label_inversion | 0/211 (0.0%) | 0 | 0 | 0 | **zero-train** |
| V6C | metric_scope_awareness | 3/211 (1.4%) | 2 (1.7%) | 1 | 0 | active (sparse) |
| V7A | no_metric_inspection | 63/211 (29.9%) | 34 (29.1%) | 16 | 13 | active |
| V7B | no_graph_reading | 15/211 (7.1%) | 5 (4.3%) | 3 | 7 | active |
| V7C | no_comparison_despite_opportunity | 11/211 (5.2%) | 5 (4.3%) | 4 | 2 | active |
| V8A | multi_instance_benchmarking | 0/211 (0.0%) | 0 | 0 | 0 | **retired** |
| V8B | table_sort_threshold | 1/211 (0.5%) | 1 (0.9%) | 0 | 0 | active (sparse) |
| V8C | ctr_in_place_edit | 13/211 (6.2%) | 5 (4.3%) | 2 | 6 | active |
| V8D | import_failure_recovery | 6/211 (2.8%) | 6 (5.1%) | 0 | 0 | active |

**Zero-in-train codes:** V1B, V2B, V3A, V5A, V6A, V6B, V8A — 7 codes have zero positive examples in the training split. Exclude from training loss. See § Coverage gap table for recruitment plan.

**V6A structural note:** 2 cohort positives exist but both fall in dev/test splits. Exclude from training loss; include in eval as unseen-code probe.

**Note on V8A (retired):** zero fires across 211 episodes; retired for 2025 task context. See codebook retired_codes section.

**not_measurable cells: 17 total.** Breakdown: V7A=7, V7B=7, V7C=2, V2A=1. Sources: (a) V7 precheck automation — 8 cells (Ally 2, Calvin 1, David 1, Henry 1, Ozzy 3) where the episode contained an unanchored observation step; (b) prior application — 9 cells (Edgar 3 V7A from span=0 rule, 6 from Pass 1 calibration adjudication). Audit log: `training_datasets/2025/v7_precheck_auto_log.json`.

---

## (g) Known limitations

1. **No event log (2025 cohort).** CODAP Arbor event CSVs are not available for this cohort. All task-4 process variables (time-to-first-emit, feature change counts, etc.) are null. Planned for 2026.

2. **Single-observer heuristic labels.** All 243 observed cells come from one expert observer. No cell has been adjudicated by a second analyst yet. Labels reflect one observer's interpretation of the video, not a consensus construct determination.

3. **Single task context.** All sessions use the same CODAP Arbor classification task. Codes that require different task affordances (V5A, V8A) may not be observable in this context.

4. **Small cohort.** n=17 students limits generalizability. Rare-event codes with <5 positives across the cohort are not reliably trainable on this dataset alone.

5. **Linkage tier.** Three sessions have partial or no silver timestamp coverage: Daisy (65%), David (70%), Felicity (0%). Felicity has 1 episode and 1 step; L3 is correct for minimal engagement. Edgar originally had 0% span (all steps degenerated to frame_0001/ts=0 by the visual alignment algorithm); an ordinal-proportional heuristic alignment was applied — all 50 steps are now mapped proportionally across 74 frames. Edgar's `alignment_method = ordinal_proportional_heuristic` and `linkage_tier = L1` but timestamps are **approximate, not frame-matched**. The 3 Edgar V7A `not_measurable` cells are preserved. Edgar's EPC labels are valid for training; temporal bounds should not be used for fine-grained temporal analysis.

6. **not_measurable now active: 17 cells.** All three decision states are reachable. The V7 precheck automation covered the full cohort; no remaining cohort V7* `observed` cells require manual review.

7. **Adjudication is self-adjudication, not dual-rater.** The 600 expert_adjudicated cells come from a single researcher conducting Pass 1 and Pass 2 with ≥7-day washout, not two independent raters. This is documented as a scope decision (single-researcher lab context), not an oversight. Claims about inter-rater reliability must not be made from this process.

---

## (h) Intended uses

- Exploratory sequence analysis of CODAP Arbor learning processes.
- Pilot training of sparse multi-label process classifiers on the 14 active codes.
- Codebook coverage demonstration for the V1–V8 process layer.
- Multimodal linkage research (video + narrative; log pending).
- Methods section evidence for the Q1 paper on process-data pipeline design.

### Recommended evaluation metrics

**Primary:** per-code and per-family instance-averaged F1 (micro-F1 on the positive class). Report separately for each V-code family (V1 through V8), not as a single aggregate.

**Secondary:** precision@k where k = expected observed codes per episode (empirically ~1.15 in this cohort; ~2.5 when restricted to active codes only).

**Tertiary:** coverage — fraction of episodes where at least one code is correctly predicted as `observed`.

**Do not report** macro-F1 across all 20 codes as the headline metric; it is inflated by the many `not_observed` true negatives. Do not report accuracy; a model predicting `not_observed` for all cells achieves 94.2%.

### Imbalance treatment

Per-code treatment is required. Apply label-frequency-based loss weighting (weight = 1/positive_frequency) for codes with observed ratio < 1:10. Consider binary focal loss (γ=2) for codes with ratio < 1:30. Exclude zero-fire codes from the training loss and document the exclusion. Do not use SMOTE or synthetic oversampling — it breaks temporal episode structure.

---

## (i) Non-intended uses

See also `framework/SCOPE_PROCESS_PIPELINE_ONLY.md` § NON-GOALS.

1. **Not for proficiency scoring.** This dataset does not provide B0–B13 proficiency scores or AI-CFT construct levels. Results from classifiers trained here cannot be interpreted as proficiency measures.

2. **Not validated as a scorer training set.** The dataset has not undergone validity assessment for automated scoring. Single-observer heuristic labels are not equivalent to adjudicated construct ratings.

3. **No IRR for proficiency constructs.** Inter-rater reliability for B0–B13 constructs has not been established.

4. **Not for high-stakes automated assessment.** Not appropriate for deployment in summative or high-stakes assessment contexts without additional validity evidence, adversarial testing, and ethical review.

5. **Not a complete training set for all 20 codes.** Six codes (V1B, V2B, V5A, V7B, V7C, V8A) have zero positive examples. Training on this dataset cannot produce a model that predicts these codes.

---

## Coverage gap table (Step 11: expansion plan)

Codes that require additional sessions before they are trainable. Minimum threshold: ≥10 positive episodes per code for binary classification, ≥20 for reliable representation learning.

| Code | Current positives | Minimum needed | Most likely recruitment path |
|---|---|---|---|
| V1B chaotic_iteration | 0 | 10 | Sessions with less scaffolding, earlier task stages, or open-ended exploration tasks |
| V2B interface_cycling | 0 | 10 | Longer sessions or students with interface confusion; may co-occur with V2A |
| V5A productive_help_seeking | 0 | 10 | Collaborative or lab-based sessions where instructor/peer help is visibly accepted |
| V7B no_graph_reading | 0 | 10 | Sessions where students skip the graph panel entirely; review multi-emit sessions |
| V7C no_comparison_despite_opportunity | 0 | 10 | Multi-emit sessions with visible alternatives and no comparison behavior |
| V8A multi_instance_benchmarking | 0 | — | Retired for 2025 task context; restore condition: explicit multi-window scaffolding |
| V3A sustained_engagement | 1 | 10 | More sessions needed; currently only Ozzy |
| V8B table_sort_threshold | 1 | 10 | Sessions with explicit data-inspection prompts |

The 2026 data collection plan should reference this table and prioritize task designs that recruit V1B, V5A, and V7B/V7C.

---

## File manifest

**Layout version:** v2 (migrated 2026-07-21). Each student directory is layered into five functional subdirectories.

```
training_datasets/2025/
  split_assignment.json                        ← frozen student-level split
  adjudication/
    pass1_coding_form.json
    pass2_coding_form.json
    resolve_log.json                           ← 9 disagreements, all resolved
    pipeline_hints_SEALED.json
  hf_export/                                   ← cohort-level merge (Parquet + JSONL)
    episode_process_codes.{parquet,jsonl}
    episodes.{parquet,jsonl}
    session_ml_features.{parquet,jsonl}
  <student>/
    raw/
      frames/
        frame_0001.jpg … frame_NNNN.jpg        ← extracted video frames
      docx_screenshots/
        docx_shot_0000.png … docx_shot_NNN.png ← Analysis.docx page images
    annotations/                               ← expert-authored; version-tagged
      <student>_expert_process_narrative.v1.jsonl
      <student>_gold_behavior_alignment.v1.jsonl
      <student>_process_codes.v1.json
    intermediate/                              ← derived; reproducible from raw + annotations
      <student>_frame_behavior_coverage.jsonl
      <student>_observation_steps.json
      <student>_silver_cost_matrix.npy          ← float32, shape (n_steps × n_frames)
      <student>_silver_cost_matrix_meta.json    ← dimensions, frame_ids, load note
    metadata/
      <student>_video_extraction_manifest.json  ← FPS, resolution, source_timestamp_ms per frame
      <student>_video_analysis_bundle.json      ← process manifest + linkage_tier + coverage_audit
      <student>_log_process_metadata.json       ← log_available flag + task4_process_variables (null 2025)
      <student>_tables_manifest.json
      session_manifest.json                     ← data_availability flags + SHA-256 for annotation files
    exports/
      tabular/
        <student>_episodes.parquet              ← 1 row/episode
        <student>_episode_process_codes.parquet ← 1 row/episode×code; gold_tier, confidence_tier
        <student>_session_ml_features.parquet   ← 1 row/session (wide ML flags)

training_datasets/2025/
  v7_precheck_auto_log.json               ← audit log for V7 precheck automation
  cohort_imbalance_weights.json           ← per-code loss_weight, use_focal_loss, exclude_from_train

framework/
  VIDEO_PROCESS_CODEBOOK_v1.md            ← triage table, V7 pre-check protocol
  EPISODE_SEGMENTATION_PROTOCOL_v1.md     ← boundary rule, categories, anchor events, 2026 extensions
  SCOPE_PROCESS_PIPELINE_ONLY.md          ← NON-GOALS
  Q1_CLAIM_LANGUAGE.md

DATASET_CARD.md                           ← this file
```

**Format notes:**
- `annotations/` files are the Single Source of Truth for expert labels. Load these; do not modify.
- `intermediate/` files are reproducible. The `.npy` matrix is loaded with `np.load()`. It encodes the step→frame alignment cost used by the gold behavior alignment pipeline.
- `exports/tabular/*.parquet` are build artifacts. Regenerate with `python scripts/export_process_codes_tables.py --all-2025 --merge-cohort` after any annotation edit.
- `session_manifest.json` contains SHA-256 hashes for all annotation files. Use these to detect untracked annotation changes before a model run.
- v1 layout (pre-2026-07-21) used a flat per-student directory with `.jsonl/.csv` tabular pairs and JSON matrices. The v1 layout is not supported.

---

## Resolved critical issues

| Issue | Resolved | Resolution |
|---|---|---|
| `gold_tier` / `confidence_tier` missing from all 4,220 cells | 2026-07-20 | Re-applied: 600 `expert_adjudicated`, 3,620 `single_observer`; T3=90, T1=163, T2=7 |
| Pass2 blanket `not_observed` destroyed adjudicated cells | 2026-07-20 | Reverted: cal_26 V2A reinstated to `not_measurable`; 9 disagreements resolved by evidence |
| `not_measurable` never used | 2026-07-20 | Now 9 cells: 3 Edgar V7 (span=0 precheck fail) + 6 calibration |
| V7B and V7C disappeared from distribution | 2026-07-20 | Restored: blanket Pass2 had zeroed calibration observed decisions; adjudication now correctly reflected |
| Zero-in-train codes undocumented | 2026-07-20 | Documented in § (f): 7 zero-train codes listed with train status column |
| L3 linkage risk silent | 2026-07-20 | Documented in § (g) limitation 5; Edgar/Felicity V7 corrected in data |
| Flat per-student directory; redundant formats; no traceability | 2026-07-21 | Migrated to v2 layered layout: `raw/`, `annotations/`, `intermediate/`, `metadata/`, `exports/tabular/`; silver_cost_matrix → `.npy`; tabular exports → `.parquet`; SHA-256 hashes in `session_manifest.json`; `source_timestamp_ms` added to every frame entry in extraction manifest |
| V7 precheck not yet cohort-wide | 2026-07-21 | Automation applied to all 17 students; 8 cells changed; `v7_precheck_auto_log.json` records all changes |
| No per-code loss weight table | 2026-07-21 | `cohort_imbalance_weights.json` computed: loss_weight and use_focal_loss per code |
| Edgar visual alignment degenerate (all steps → frame_0001/ts=0) | 2026-07-21 | Ordinal-proportional heuristic alignment applied; `alignment_method` flag set; temporal bounds are approximate |
| No segmentation protocol documented | 2026-07-21 | `framework/EPISODE_SEGMENTATION_PROTOCOL_v1.md` written (boundary rule, 4 categories, 18 anchor events, 2026 extensions) |

## Remaining human-action items

All 2025 preparation items are resolved. No outstanding human-action items.

| Step | Status | Resolution |
|---|---|---|
| V7 precheck (cohort-wide) | DONE | Automation applied; 8 cells updated; audit log saved |
| Per-code imbalance weight table | DONE | `training_datasets/2025/cohort_imbalance_weights.json` |
| Episode segmentation protocol | DONE | `framework/EPISODE_SEGMENTATION_PROTOCOL_v1.md` |
| Edgar/Felicity timestamp recovery | DONE | Edgar: ordinal-proportional heuristic alignment. Felicity: single-step L3, closed. |

**Pending (2026 pipeline, not 2025):** log-video sync test, Colab segmentation anchor event definition, `split_assignment.json` freeze.

Calibration pack: `training_datasets/2025/adjudication/` — Pass 1 locked, Pass 2 complete, 9/9 disagreements resolved.

---

# 2026 Cohort Extension

**Status:** directory skeleton created; video analysis pipeline not yet run. All fields below reflect planned structure, not completed data.

---

## 2026 (a) Key differences from 2025

| Dimension | 2025 | 2026 |
|---|---|---|
| Students | 17 | 15 |
| Sessions per student | 1 | 1–3 |
| Total sessions | 17 | 33 |
| Task types | CODAP Arbor only | CODAP Arbor (21 Apr, 28 Apr) + Colab Python (5 May) |
| Event log | Not available | Available (CODAP Arbor event CSV planned) |
| task4_process_variables | All null | Expected to be populated |
| linkage_tier target | L1–L3 (achieved L2 majority) | L1 target via log-video sync |
| Directory layout | v2 (migrated) | v2 (built from scratch) |
| Per-student structure | `<student>/` | `<student>/<session_id>/` |

---

## 2026 (b) Source data

| Property | Value |
|---|---|
| Cohort | 2026, n=15 students |
| Total sessions | 33 (across 3 task dates) |
| Recording type | Screen recordings (.webm) |
| Task dates | 21 April (CODAP Arbor), 28 April (CODAP Arbor), 5 May (Colab Python) |
| Event log | CODAP Arbor event CSV available (planned sync) |
| Language of narratives | Turkish (uzman_nitel_gözlemi field, same as 2025) |

### Session coverage per student

| Student | codap_21apr | codap_28apr | colab_05may | Total sessions |
|---|---|---|---|---|
| Amy | yes | — | yes | 2 |
| Bruno | yes | yes | yes | 3 |
| Helena | yes | — | yes | 2 |
| Iris | yes | — | — | 1 |
| Irma | yes | yes | yes | 3 |
| Isabel | yes | yes | — | 2 |
| Marco | yes | yes | yes | 3 |
| Marcus | yes | — | — | 1 |
| Melinda | — | yes | — | 1 |
| Nadia | yes | yes | yes | 3 |
| Serena | — | yes | yes | 2 |
| Shana | yes | — | yes | 2 |
| Sheila | yes | — | yes | 2 |
| Ulysses | yes | yes | yes | 3 |
| Zara | yes | yes | yes | 3 |
| **Total** | 13 | 9 | 11 | **33** |

---

## 2026 (c) Directory layout

```
training_datasets/2026/
  split_assignment.json                      ← pending; assign after pipeline completes
  hf_export/                                 ← cohort-level merge (populated by pipeline)
  <student>/
    metadata/
      student_manifest.json                  ← session list, task_type, log_available per session
    <session_id>/                            ← codap_21apr | codap_28apr | colab_05may
      raw/frames/                            ← extracted video frames
      raw/docx_screenshots/                  ← Analysis.docx page images
      annotations/                           ← expert_process_narrative.v1.jsonl
                                                gold_behavior_alignment.v1.jsonl
                                                process_codes.v1.json
      intermediate/                          ← frame_behavior_coverage.jsonl
                                                silver_cost_matrix.npy
                                                log_event_sequence.parquet  ← NEW (CODAP sessions)
      metadata/                              ← video_extraction_manifest.json
                                                video_analysis_bundle.json
                                                log_process_metadata.json   ← task4 vars populated
                                                session_manifest.json
      exports/tabular/                       ← episodes.parquet
                                                episode_process_codes.parquet
                                                session_ml_features.parquet
```

**New in 2026 vs 2025:**
- `intermediate/log_event_sequence.parquet` — CODAP event CSV parsed to tidy format; one row per event with timestamp, action, attribute, value.
- `metadata/log_process_metadata.json` — `log_available: true`; `task4_process_variables` populated (time_to_first_emit_ms, feature_change_count, etc.).
- `metadata/video_analysis_bundle.json` — `log_video_sync_status: synced | partial | unavailable` per session.

---

## 2026 (d) V-code schema

Same V1A–V8D schema as 2025. Codebook: `framework/VIDEO_PROCESS_CODEBOOK_v1.md`.

**Expected differences in code firing rates for colab_05may sessions:**
- V8A–V8D (CODAP-specific codes) are **not applicable** to Colab Python sessions. These cells should be coded `not_measurable` by default.
- V5A (productive help-seeking) may fire more in Colab sessions if collaborative work is visible.
- V1B (chaotic iteration) may fire if students lack notebook familiarity.

---

## 2026 (e) Splits

Not yet assigned. The split will be student-level (same policy as 2025) to prevent session-level leakage across the train/dev/test boundary.

**Constraint:** Students who appear in the 2025 test set (Barbara, Frank, Zabby) are not in the 2026 cohort. Cross-cohort eval is structurally clean.

**When to freeze:** After all 33 sessions are processed and episode counts are known. See `training_datasets/2026/split_assignment.json` (status: pending).

---

## 2026 (f) Known limitations and open issues

1. **Colab Python sessions use a different tool.** V8 codes (CODAP-specific strategies) cannot fire in `colab_05may` sessions. This creates within-student code-availability heterogeneity that must be handled in the feature schema before cross-session modeling.

2. **Multi-session students complicate the unit of analysis.** A student with 3 sessions contributes 3 independent episode sets. Cross-session learning trajectories are not modeled in v1 of the codebook. Treat each session as an independent observation unit for now.

3. **log_video_sync not yet validated.** The CODAP event CSV sync has not been tested against actual 2026 video. Linkage tier outcomes (L1/L2/L3) are unknown until the pipeline runs.

4. **Episode segmentation for Colab sessions is undefined.** The current segmentation protocol is anchored to CODAP Arbor emit events. Colab Python requires a separate anchor event definition (cell execution? output appearance?) before coding can begin.

5. **2026 split not frozen.** Do not begin modeling until `split_assignment.json` is written and committed.

---

## 2026 (g) Pipeline entry point

```bash
# After extracting frames for a student session:
python scripts/build_video_analysis_bundle.py --student Amy --session codap_21apr --year 2026

# Tabular export (after all sessions processed):
python scripts/export_process_codes_tables.py --all-2026 --merge-cohort
```

The `--year 2026` flag routes output to `training_datasets/2026/<student>/<session_id>/`.
