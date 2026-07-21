# Episode Segmentation Protocol — CODAP Arbor Process Analysis
**Version:** 1.0  
**Date:** 2026-07-21  
**Scope:** 2025 cohort (n=17 students, 211 episodes); extends to 2026 with additions noted.

---

## 1. What Is an Episode?

An **episode** is the smallest unit of analysis in this pipeline. It is a consecutive sequence of observation steps in which the student's cognitive behavior category remains constant.

Each episode has:
- A single **dominant category** (EXPLORE, TUNE, EVALUATE, or MISCONCEPTION)
- One or more **observation steps** describing discrete CODAP actions
- A **primary anchor event** — the most consequential CODAP interaction within the episode
- **Temporal bounds** (start_ms, end_ms) derived from video-frame alignment
- An **assistance status** (independent or instructor-present)

---

## 2. Cognitive Behavior Categories

The four categories are mutually exclusive and exhaustive at the step level.

| Category | Operational Definition | Typical CODAP Actions |
|---|---|---|
| **EXPLORE** | Student examines data structure, loads datasets, or sets up the workspace without yet committing to a model configuration | LOAD_DATASET, OPEN_ARBOR, SET_AXIS, DRAG_SPLIT_ATTRIBUTE |
| **TUNE** | Student actively modifies decision tree parameters to improve performance | EMIT_TREE, SET_TARGET_ATTRIBUTE, UPDATE_MOVABLE_VALUE, UPDATE_THRESHOLD, ASSIGN_LEAF_LABEL |
| **EVALUATE** | Student reads and interprets performance metrics, graphs, or comparison tables | INTERPRET_METRICS, COMPARE_MODELS, SELECT_CTR_ROW |
| **MISCONCEPTION** | Student takes an action that reveals a documented conceptual error (e.g., optimizing training accuracy when CTR is the target, applying label inversion) | Any action accompanied by explicit misconception evidence in the expert narrative |

**Disambiguation rules:**
- If a step involves both tuning and evaluation (e.g., reading metrics then immediately adjusting a threshold), assign TUNE. Evaluation is the trigger; the adjustment is the intent.
- MISCONCEPTION overrides EXPLORE/TUNE/EVALUATE when the expert narrative explicitly flags a conceptual error. Do not assign MISCONCEPTION based on poor performance alone.
- A step that consists of help-seeking (dialogue with instructor, reading documentation) without producing a CODAP state change is assigned EXPLORE.

---

## 3. Episode Boundary Rule

**A new episode begins at step i when the category label of step i differs from the category label of step i−1.**

This is the sole boundary criterion. No minimum episode length is imposed. An episode may contain a single step (this occurs when a student briefly evaluates before resuming tuning, for example).

The algorithm is implemented in `scripts/build_video_analysis_bundle.py → episode_groups()` (line 88). It reads the `bilişsel_davranış_kategorisi` sub-field within each step's `labels` block and flushes the current episode buffer on every category transition.

**Edge case — unlabeled step:** If a step has no category label, it inherits EXPLORE by default (the algorithm default is line 111: `cat = ... or "EXPLORE"`). Reviewers should flag steps where this fallback activates; they should be rare (<2% in the 2025 cohort).

---

## 4. Anchor Event Assignment

After boundary detection, each episode receives one **anchor event** tag. The anchor event is the single CODAP interaction that best characterizes the episode's primary action.

**Assignment is performed by the expert coder** during the narrative step. The coder selects from a controlled vocabulary:

| Tag | Description |
|---|---|
| EMIT_TREE | Tree generated or re-generated in Arbor |
| SET_AXIS | Attribute dragged onto a graph axis |
| SET_TARGET_ATTRIBUTE | Classification target attribute selected |
| LOAD_DATASET | Dataset imported or switched |
| UPDATE_MOVABLE_VALUE | Threshold (movable value) adjusted on a graph |
| DRAG_SPLIT_ATTRIBUTE | Split attribute dragged into decision tree node |
| INTERPRET_METRICS | Student reads CTR, accuracy, or other metric values |
| COMPARE_MODELS | Student compares two or more tree configurations |
| SEEK_HELP_OR_DIALOGUE | Student asks instructor or peer for help |
| TRAIN_TEST_SPLIT | Choosy split applied or modified |
| SELECT_CTR_ROW | Student selects a row in the CTR (confusion matrix) table |
| ASSIGN_LEAF_LABEL | Student manually assigns a class label to a leaf node |
| CREATE_GRAPH | New graph panel created |
| DELETE_TREE_OR_CTR_ROW | Tree or CTR row deleted |
| ERROR_SCREEN | CODAP or Arbor error message visible |
| UPDATE_THRESHOLD | Threshold value typed directly (not via movable value) |
| IMPORT_TREE | Previously saved tree imported |
| OPEN_ARBOR | Arbor plugin launched for the first time in this session |

If an episode contains multiple action types, assign the anchor event that is most consequential for model behavior (preference order: EMIT_TREE > SET_TARGET_ATTRIBUTE > DRAG_SPLIT_ATTRIBUTE > others).

---

## 5. Temporal Bounds

Episode `start_ms` and `end_ms` are derived from the video-frame alignment (silver_video layer):

- `start_ms` = timestamp of the video frame aligned to the first step in the episode
- `end_ms` = timestamp of the video frame aligned to the last step in the episode

Single-step episodes have `start_ms == end_ms`; this is expected and not an error.

If a student's alignment quality is L3 (silver_timestamp_span_ms < 70% of recording duration), temporal bounds should be interpreted with caution. The `alignment_method` field in `session_manifest.json` documents whether bounds are from true visual matching or from a fallback (e.g., `ordinal_proportional_heuristic`).

---

## 6. Distribution in 2025 Cohort (Informational)

| Metric | Value |
|---|---|
| Total episodes (n=17 students) | 211 |
| Episodes per student: range | 1 – 23 |
| Episodes per student: median | 11 |
| EXPLORE episodes | 74 (35.1%) |
| TUNE episodes | 88 (41.7%) |
| EVALUATE episodes | 39 (18.5%) |
| MISCONCEPTION episodes | 10 (4.7%) |
| Most common anchor event | EMIT_TREE (79, 37.4%) |
| Episodes with valid temporal bounds | 201 / 211 (95.3%) |

---

## 7. 2026 Extensions

Two changes apply to 2026 Colab Python sessions (`colab_05may`):
- Categories remain the same. TUNE now includes cell execution as a CODAP-equivalent action.
- Anchor event `EMIT_TREE` is replaced by `RUN_CELL` for sessions where students run Python code to fit a tree.
- V8* codes (import/session management) are `not_measurable` in all Colab episodes (no CODAP Arbor interface present).

CODAP multi-session students (codap_21apr, codap_28apr) use the same protocol as 2025 with no changes.
