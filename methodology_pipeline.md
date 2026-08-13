# Data Processing Pipeline — Methods Section Draft (Q1 Paper)

**Scope:** This section describes the multimodal data processing pipeline developed to transform four heterogeneous data source types — paper-based worksheets, screen recordings, CODAP Arbor event logs, and Google Colab notebooks — into structured, analysis-ready artifacts for process-code annotation and model-readiness assessment. No proficiency scores (B0–B13 construct levels) are assigned in this pipeline. All outputs described here are process-layer artifacts only.

---

## 3.1 Overview

Data were collected from two cohorts of pre-service teachers (2025: n=17; 2026: n=15, 33 sessions) completing a decision tree modeling task. Participants used CODAP Arbor for visual modeling and Google Colab for Python-based replication. Paper worksheets accompanied both phases. Four data source types were processed through distinct sub-pipelines, each producing typed JSON or Parquet artifacts that converge at a per-student portfolio layer.

The pipeline was implemented in Python 3.11. Schema contracts were enforced with Pydantic v2 and JSON Schema Draft-07. All numerical scoring logic was implemented in Python/Pandas; no large language model (LLM) call was permitted to compute or assign numerical values. LLMs were used exclusively for extracting and transcribing handwritten or typed free-text responses from scanned worksheets, and for generating expert process narratives from structured observation protocols.

The pipeline produces four artifact types per student per session:

| Artifact | Format | Description |
|---|---|---|
| `extraction.json` | JSON | OCR/HTR transcript of worksheet responses |
| `validation.json` | JSON | Deterministic parse and field-integrity checks |
| `scoring.json` | JSON | Item-level scores, confidence flags, review triggers |
| `evidence.json` | JSON | Per-item learning-objective evidence trace |

For screen recording sessions, a parallel set of process-layer artifacts is produced:

| Artifact | Format | Description |
|---|---|---|
| `*_expert_process_narrative.v1.jsonl` | JSONL | Expert observer free-text narratives per step |
| `*_gold_behavior_alignment.v1.jsonl` | JSONL | Step-to-frame alignments with confidence tier |
| `*_process_codes.v1.json` | JSON | Episode-level V-code binary decisions |
| `*_episodes.parquet` | Parquet | One row per episode, temporal bounds |
| `*_episode_process_codes.parquet` | Parquet | One row per episode × V-code |
| `*_session_ml_features.parquet` | Parquet | Session-level feature vector |

---

## 3.2 Source 1 — Paper-Based Worksheets

### 3.2.1 Data characteristics

Participants completed 8–11 paper worksheets across the instructional sequence. Worksheets varied in response format: multiple-choice, short-answer numerical fields, handwritten decision tree diagrams, operator expressions (e.g., `Fat ≤ 4.0`), and Likert-scale surveys. Worksheets were collected as physical documents and digitized by scanning.

Two processing groups were defined based on the nature of the correct response:

**Group A (LLM-scored):** Worksheets where the correct response is interpretive or equivalence-based (WS1, WS3, WS4, WS10, WS11, WS_DT series). Responses were extracted by OCR and evaluated by a prompted LLM against rubric criteria. Deterministic Python scoring was applied for specific fields where the answer space is finite and exact (see §3.2.4).

**Group B (deterministic-scored):** Worksheets where the correct response is fully computable from a reference dataset (WS5, WS6, WS7). LLMs extracted the text; Python rules scored it.

### 3.2.2 Step 1 — Scan ingestion and page layout isolation

Scanned worksheets were ingested as multi-page PDF or image bundles. A layout isolation stage (`layout_isolator.py`) applied OpenCV-based region-of-interest (ROI) detection to segment each page into individual response regions. ROI coordinates were defined per worksheet in `layout_rois/<worksheet>/` manifest files. Cropped images were saved to `ocr_output/<student>/` for downstream OCR.

For worksheets containing tabular responses (WS5, WS6, WS10), table region detection used line-detection heuristics to identify row and column boundaries before cropping. This step was critical for WS10, which contained a fixed energy table where cell position encodes semantic identity (blank 1–8 map to specific misclassification counts).

### 3.2.3 Step 2 — Optical character recognition and handwriting transcription

Each cropped response region was processed by a vision-capable LLM (`ocr_pipeline.py`) using a structured extraction prompt. The prompt specified the expected field identifier, the response format type (e.g., `operator_expression`, `numeric`, `free_text`, `multiple_choice`), and any known constraints (e.g., "operator must be one of ≤, <, ≥, >").

For printed text regions, standard OCR was applied. For handwritten regions, handwriting transcription (HTR) was used. WS10's table required a dedicated extractor (`ws10_table_extractor.py`) that mapped table column position to blank identifiers B1–B7 using a column-order heuristic, then applied exact integer matching against the reference answer key (`data/ws10_energy_reference.json`).

Raw transcription output was stored verbatim in `extraction.json` under the field identifier (e.g., `WS5_B3_operator`). The raw extraction was never modified in place; all downstream normalization operated on a derived copy.

### 3.2.4 Step 3 — Mechanical normalization

A normalization stage (`ws_extraction_normalize.py`) applied a fixed set of rule-based corrections to common OCR transcription artifacts before validation. These corrections were mechanical and did not require semantic judgment:

- Operator character substitutions: `=<` → `≤`, `=>` → `≥`, `< =` → `≤`, `> =` → `≥`
- Whitespace stripping around operator tokens
- Decimal separator normalization (comma → period for numeric fields)
- Case normalization for multiple-choice fields where the key is case-insensitive

Normalization rules were worksheet-specific and defined in `worksheet_blank_registry.py`. The raw `extraction.json` was preserved unchanged; the normalized output was used exclusively by the validation and scoring stages.

### 3.2.5 Step 4 — Deterministic validation (Group B only)

For Group B worksheets (WS5, WS6, WS7), a Python validation module checked each extracted field against a rule set derived from the reference dataset (`data/prodabi_food_cards.csv`, N=11 food items).

**WS5 validation** checked: (a) that operator expressions used a member of the allowed operator set {≤, <, ≥, >}; (b) that threshold values were within the observable range for the named feature; (c) that split counts (items satisfying the condition / not satisfying) summed to 11; (d) that operator pairs on complementary branches were logically complementary (e.g., `≤` paired with `>`); and (e) that the misclassification count (MCR) was consistent with the stated split.

**WS6 validation** extended WS5 checks to a two-level tree. MCR=0 with two levels was accepted as a valid response. Fields B1–B13 extracted by OCR were sufficient for complete validation; an optional vision crop of the tree diagram (`dt_vision_pipeline.py`) was used as supplementary evidence only and did not override the text-based validation result.

**WS7 validation** operated in two parts. Part 1 checked three fixed path letter responses (B, A, C) against the reference sample tree (`data/ws7_sample_tree.json`). Part 2 cross-referenced the student's WS7 if-then rule expressions against their own WS6 tree output, verifying that operator symbols and threshold values matched exactly. This cross-worksheet reference required that WS6 extraction be complete before WS7 validation could run.

Validation output was written to `validation.json`, recording parse success, detected issues, and any fields requiring manual review.

### 3.2.6 Step 5 — Scoring

Scoring was applied after validation. Two scoring pathways were used:

**Deterministic scoring (Group B + selected Group A fields):** Python functions computed point allocations from validation outcomes. No LLM call was made in this pathway. For WS4, fields B2 (four-food unordered set) and B5 (energy numeric range 160–2223) were scored deterministically; remaining WS4 fields used the LLM pathway. For WS10, all eight blank fields were scored by exact integer match.

**LLM scoring (Group A interpretive fields):** A rubric-prompted LLM received the normalized extraction, the rubric criteria from `rubrics/<WS>_rubric.json`, and a few-shot exemplar set. The model returned a structured response specifying the score, the rubric criterion satisfied, and a brief evidence quote (minimum 10 characters). The prompt explicitly prohibited the model from assigning numerical totals; total score computation was performed by a Python accumulator after all item scores were returned.

Scoring output was written to `scoring.json`, including item scores, confidence flags, and `review_required` boolean fields for items where the LLM reported low confidence or where the response was ambiguous.

### 3.2.7 Step 6 — Evidence unit construction

The final worksheet stage built learning-objective evidence units (`evidence.json`). Each item score was mapped to one or more UNESCO AI-CFT learning objectives (LO3.1.x through LO3.3.x) using the per-worksheet mapping files in `mappings/`. Evidence units recorded the field identifier, the score, the LO code, the evidence quote from scoring, and a confidence tier. These units served as input to the cross-worksheet portfolio builder.

---

## 3.3 Source 2 — Screen Recordings

### 3.3.1 Data characteristics

Each student session was captured as a full-session screen recording (2025 cohort: format varies; 2026 cohort: `.webm`). Session durations ranged approximately 10–25 minutes. Recordings captured the CODAP Arbor interface, any browser tabs opened during the session, and in some cases partial audio. No face or physical environment was recorded. The 2025 cohort comprised 17 sessions; the 2026 cohort comprised 33 sessions across three task dates.

### 3.3.2 Step 1 — Frame extraction

Video frames were extracted at a fixed sampling rate using FFmpeg. Extracted frames were stored as JPEG files under `training_datasets/<year>/<student>/raw/frames/`. A video extraction manifest (`*_video_extraction_manifest.json`) recorded the source timestamp in milliseconds for each frame, the resolution, and the frames-per-second rate of the source recording. This manifest enabled subsequent step-to-frame alignment to operate on absolute timestamps rather than frame indices alone.

### 3.3.3 Step 2 — Expert observation protocol

A single expert observer reviewed each recording and produced a free-text narrative in JSONL format (`*_expert_process_narrative.v1.jsonl`). Each line in the narrative corresponded to one observation step and recorded: the approximate timestamp, a Turkish-language qualitative description of the observed behavior (`uzman_nitel_gözlemi`), and the behavioral signal type from the 17-category observation protocol defined in `screen_recording_analysis_guide.md`.

The observation protocol distinguished behaviors that are detectable from screen content alone from those requiring inference. Behaviors were classified into 17 signal types organized by priority. Priority 1 signals (data table inspection, error recognition, peer interaction, train/test understanding) were required for any process-code assignment. Priority 2 signals (tree reading time, confusion matrix inspection, Python error reading, depth intentionality) were required for assignment of higher-tier process codes. Priority 3 and 4 signals enriched interpretation but were not gatekeeping.

### 3.3.4 Step 3 — Step-to-frame alignment

Each observation step was aligned to one or more video frames using a cost-matrix alignment procedure (`*_silver_cost_matrix.npy`, shape: n_steps × n_frames). The cost matrix encoded the alignment cost between each step and each frame based on timestamp proximity and visual-behavioral consistency. Gold alignment (`*_gold_behavior_alignment.v1.jsonl`) stored the resolved frame assignment for each step, together with a linkage tier:

- **L1 (silver-timestamp):** Step timestamp matched a frame timestamp within a 2-second tolerance. The majority of 2025 sessions achieved L1.
- **L2 (interpolated):** Step fell between two anchored frames; timestamp was interpolated from neighboring L1 anchors.
- **L3 (heuristic):** No reliable timestamp anchor; ordinal-proportional heuristic applied. One 2025 student (Edgar) required L3 due to degenerate visual alignment where all steps mapped to frame 0001. An ordinal-proportional heuristic was applied, distributing steps evenly across the session frame range. Edgar's temporal bounds are flagged as approximate and must not be used for fine-grained temporal analysis.

Three 2025 students had partial linkage coverage: Daisy (65% L1), David (70% L1), Felicity (single-step, L3). These coverage gaps are documented in the dataset card limitation section and the `*_video_analysis_bundle.json` manifest.

### 3.3.5 Step 4 — Episode segmentation

Aligned observation steps were grouped into episodes using a boundary rule defined in `framework/EPISODE_SEGMENTATION_PROTOCOL_v1.md`. An episode was defined as a meaningful behavioral segment anchored by a transition event. Anchor event types included: emit (model submission), feature change, threshold change, dataset switch, tree type change, and session start/end. Episodes had a target duration of 30–90 seconds; episodes falling outside this range were flagged for review.

The 2025 cohort produced 211 episodes across 17 sessions (mean 12.4 episodes/session). Episode boundaries were stored in `*_episodes.parquet` (one row per episode), recording episode identifier, start and end timestamps, anchor event type, and a flag for V7 pre-check eligibility (see §3.3.6).

### 3.3.6 Step 5 — V7 pre-check protocol

Process codes V7A (`no_metric_inspection`), V7B (`no_graph_reading`), and V7C (`no_comparison_despite_opportunity`) are negative-evidence codes: they are observed when a student fails to perform an expected behavior in an episode where that behavior was structurally possible. This pre-check was mandatory before any V7 code could be assigned.

The pre-check determined, for each episode, whether the structural precondition was met: did the episode contain an emit event (V7A precondition), a visible graph panel (V7B precondition), or a moment where multiple model versions were available for comparison (V7C precondition)? Episodes failing the precondition received a `not_measurable` decision for the relevant V7 code rather than `not_observed`.

A cohort-wide automated pre-check (`v7_precheck_auto_log.json`) was applied to all 17 students. This produced 8 cell changes from `not_observed` to `not_measurable`. The audit log records the student, episode, V-code, and reason for each change. Total `not_measurable` cells in the 2025 dataset: 17 (V7A=7, V7B=7, V7C=2, V2A=1).

### 3.3.7 Step 6 — Process code assignment

For each episode, each of the 20 V-layer process codes (V1A–V8D) received one of three decisions: `observed`, `not_observed`, or `not_measurable`. Decisions were assigned by the expert observer based on the behavioral narrative and the frame evidence. The codebook (`framework/VIDEO_PROCESS_CODEBOOK_v1.md`) defined the detection rule for each code, including the minimum behavioral evidence required for an `observed` decision.

A 30-episode calibration subset was expert-coded twice by the same researcher with a washout period of at least 7 days between passes (self-adjudication protocol). Nine disagreements between Pass 1 and Pass 2 were identified and resolved with written rationales stored in `training_datasets/2025/adjudication/resolve_log.json`. This self-adjudication process does not constitute dual-rater inter-rater reliability; the dataset documentation makes this limitation explicit.

Each decision cell carries two metadata fields: `confidence_tier` (T1 = video-behavioral evidence with frame anchor; T2 = narrative-inferred without anchor; T3 = expert self-adjudicated) and `gold_tier` (`expert_adjudicated` for the 600 calibration cells; `single_observer` for the remaining 3,620 cells).

### 3.3.8 Step 7 — Tabular export

Episode and process-code data were exported to Parquet format for downstream analysis. Three export files were produced per student: `*_episodes.parquet`, `*_episode_process_codes.parquet` (one row per episode × V-code, containing all decision fields and metadata tiers), and `*_session_ml_features.parquet` (one row per session, wide-format binary feature vector). A cohort-level merge (`hf_export/episode_process_codes.parquet`) combined all students into a single analysis-ready file.

---

## 3.4 Source 3 — CODAP Arbor Event Logs

### 3.4.1 Data characteristics

**2025 cohort:** CODAP Arbor event CSV logs were not available. All task-process variables (time to first emit, feature change count, emit count, accuracy trajectory) are null for 2025. This limitation is documented in `*_log_process_metadata.json` (field: `log_available: false`) and in the dataset card.

**2026 cohort:** Event CSV logs were planned for collection across all 33 sessions. Log files record timestamped user actions within the CODAP Arbor interface. The raw action space contains 16 action types, of which approximately 61.8% are noise actions (UI state changes, drag events, session metadata) that require filtering before analysis.

### 3.4.2 Step 1 — Log ingestion and noise filtering

Raw event CSVs were ingested and filtered to retain only analytically meaningful actions: `emit` (model submission), `drop_attribute` (feature selection), `change_split_values` (threshold adjustment), `change_tree_type`, `change_dataset`, and `data_context_change`. Noise action types (drag events, component resize, session start/end markers, UI state) were discarded.

A deduplicated student identifier map resolved raw student ID variants to canonical identifiers. The 2025 log analysis identified 32 unique raw student IDs for 17 active students, indicating that multiple raw IDs per student required manual resolution.

### 3.4.3 Step 2 — Emit sequence construction

For each student, the filtered event stream was sorted by timestamp and the emit sequence was extracted: the ordered list of model submissions with accuracy at each emit. This sequence was the basis for computing behavioral summary features: total emit count, accuracy at final emit, accuracy trajectory volatility (standard deviation across emit sequence), time to first emit, and feature change count between consecutive emits.

These features were stored in `*_log_process_metadata.json` under `task4_process_variables`. For 2025 students, all fields in this object are null. For 2026 students, these fields are expected to be populated after log-video sync validation.

### 3.4.4 Step 3 — Log-video synchronization (2026 only)

For 2026 sessions where both an event log and a screen recording were available, a synchronization step aligned log timestamps to video frame timestamps. Synchronization quality was recorded as `log_video_sync_status` in `*_video_analysis_bundle.json`: `synced` (alignment within 2 seconds for anchor events), `partial` (some anchor events aligned, others not), or `unavailable` (no reliable anchor found).

Synchronized log data enables direct linkage between observed video behaviors (e.g., a student pausing before an emit) and the log-recorded event sequence, supporting multimodal behavioral analysis. This step was not completed for 2025 due to the absence of event logs.

### 3.4.5 Step 4 — Tidy event sequence export (2026 only)

Filtered and synchronized log events were exported to `intermediate/log_event_sequence.parquet` (one row per event, columns: timestamp, action, attribute, value, aligned_frame_id). This file enables time-series analysis of behavioral sequences alongside process-code episode data.

---

## 3.5 Source 4 — Google Colab Notebooks (2026 Cohort)

### 3.5.1 Data characteristics

Eleven of 15 students in the 2026 cohort completed a Python-based decision tree session in Google Colab on 5 May. Each student produced a Colab notebook (`.ipynb`) as the primary artifact. Notebooks contained code cells implementing scikit-learn decision tree models, markdown cells with explanations, and cell execution outputs.

### 3.5.2 Step 1 — Notebook ingestion and structure parsing

Notebooks were ingested as JSON (`.ipynb` format). A parsing stage extracted the ordered cell sequence, cell type (code / markdown / raw), source code or text content, execution count, and output objects (stdout, stderr, error tracebacks, display outputs).

### 3.5.3 Step 2 — Execution pattern analysis

The cell execution sequence was reconstructed from execution counts. Out-of-order execution counts (e.g., a later cell executed before an earlier one) were flagged as non-sequential execution. The pattern was classified as: `incremental` (cells executed in order, one at a time), `batch` (all cells executed in sequence after all were written), or `mixed`.

Error cells (cells producing a red traceback output) were identified and the corrective action was characterized from the subsequent cell state: `targeted_fix` (specific line edited), `full_rewrite` (cell deleted and rewritten), `copy_paste` (new content appeared without incremental typing evidence), or `no_action` (cell re-run without modification).

### 3.5.4 Step 3 — Code content extraction for worksheet cross-reference

For students who completed both the Colab session and the decision tree worksheet series (WS5, WS6, WS7), the Python implementation in the notebook was cross-referenced against the tree structure the student had hand-designed on paper. This cross-reference checked whether the feature selection and threshold values in the Python `DecisionTreeClassifier` call were consistent with the student's own WS6 tree. Consistency was recorded as a binary flag in `*_log_process_metadata.json` (field: `notebook_ws_consistency`).

### 3.5.5 Step 4 — Screen recording integration

Colab sessions were also captured by screen recording. The observation protocol for Python-phase signals (Signals 9–12 in the observation guide) was applied: error message reading behavior, typing versus copy-paste detection, incremental versus batch cell execution, and variable inspection behavior. Screen recording analysis for Colab sessions followed the same pipeline as §3.3 with one exception: V8-family process codes (CODAP-specific strategic organization codes V8A–V8D) were coded as `not_measurable` by default for all `colab_05may` sessions, as these codes require CODAP Arbor interface affordances that are absent in a Python notebook environment.

---

## 3.6 Convergence — Portfolio Construction

After all source-specific pipelines completed, per-student portfolios were constructed by the portfolio builder (`run_portfolio_builder.py`). The portfolio aggregated evidence units across all worksheets, process-code summaries from the video pipeline, and (where available) log-derived behavioral features into a single `portfolio.json` artifact.

The portfolio recorded peak evidence per learning objective across all worksheet items, behavioral process-code patterns from the video layer, and data availability flags indicating which source types were present for each student. Data availability flags were used to suppress claims in the portfolio narrative for sources that were absent (e.g., log-derived variables were flagged as unavailable for all 2025 students).

Portfolio construction was explicitly scoped to process-layer evidence. Construct-level proficiency assignments (B0–B13 AI-CFT levels) were outside the scope of the current pipeline and were not computed.

---

## 3.7 Schema validation and reproducibility

All pipeline artifacts were validated against JSON Schema Draft-07 contracts before being accepted as pipeline outputs (`validate_schemas.py`, `validate_pipeline_outputs.py`). Schema violations triggered pipeline failure rather than silent data corruption.

Pipeline reproducibility was ensured through: (a) SHA-256 hashes in `session_manifest.json` for all annotation files, enabling detection of untracked changes before a model run; (b) frozen split assignments in `split_assignment.json` that were not re-randomized after initial assignment; (c) version-tagged annotation files (`*.v1.jsonl`, `*.v1.json`) that preserved the annotation state at each pipeline step; and (d) an immutable raw layer (`training_datasets/<year>/<student>/raw/`) that was never written to by pipeline stages downstream of frame extraction.

The full pipeline, codebook, dataset card, and schema files are released alongside this paper to support replication and extension to other CODAP-based or Colab-based assessment contexts.
