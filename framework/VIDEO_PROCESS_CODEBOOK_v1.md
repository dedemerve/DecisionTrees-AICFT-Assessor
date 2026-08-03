# Video Process Codebook v1

**Status:** active process layer for Q1 pipeline / process-data / methods work  
**Purpose:** capture video-visible learning-process patterns (iteration, help-seeking, recovery, CODAP strategies, etc.)  
**Methodological stance:** process codes support interpretation, modeling, and instructional diagnosis; they are **not** proficiency scores

## Why this layer exists

The B0-B13 rubric is a **construct rubric**. It measures AI-CFT-aligned cognitive behaviors. It does **not** fully capture everything that screen recordings reveal. Video also exposes:

- iteration quality;
- cognitive-load and usability strain;
- engagement/disengagement;
- help-seeking and dependence;
- misconception traces;
- error-recovery style;
- negative evidence such as "the learner did not inspect the metric panel."

These traces are valuable for mixed-method interpretation and machine learning. This codebook defines a **process layer**, consistent with ILSA process-data practice where clickstream/video indicators are analyzed as process evidence rather than as proficiency scores.

## Coding architecture

### Unit of analysis

The default unit is a **meaningful episode**, aligned to the main rubric:

- at least 30 seconds before the anchor event,
- at least 20 seconds after the anchor event,
- extended to the next meaningful action when required.

### Decision states

Each process code uses:

- `observed`
- `not_observed`
- `not_measurable`

### Allowed evidence

- **Video:** primary source for all codes in this layer
- **Analysis.docx behavioral transcript:** acceptable proxy for ordered visible actions
- **Transcript:** used only when the process code depends on ownership, challenge, or help-seeking meaning
- **Log:** may corroborate order and counts but cannot independently establish most process codes

## Code families

### V1. Iteration quality

#### V1A Systematic iteration

**Definition:** the learner changes one meaningful control at a time and inspects the consequence before the next change.

**Typical indicators**
- threshold updated, then branch/metric/graph inspected;
- predictor replaced, then output inspected before another modification;
- child split added after diagnosing a local subgroup problem.

**Exclusions**
- multiple controls change in the same episode with no stable inspection cycle;
- repeated emit clicks with no evidence of review.

**Detection source**
- video: strong
- log: partial chronology only

#### V1B Chaotic iteration

**Definition:** the learner changes several controls or representations in quick succession without an interpretable inspection-evaluation cycle.

**Typical indicators**
- predictor, threshold, and labels all changed before any output review;
- repeated graph/tree switching with no stable criterion;
- random-seeming numeric trials.

**Measurement note**
- this code is diagnostic, not punitive; it is a process descriptor only.

### V2. Cognitive load and usability strain

#### V2A Hesitation / disorientation

**Definition:** visible delay, search, or interface wandering suggests uncertainty about what to do next.

**Typical indicators**
- long cursor dwell before action;
- repeated opening/closing of panels;
- scanning multiple controls without selection;
- revisiting the same place with no progress.

**Exclusions**
- purposeful pause immediately before a correct transfer or evaluation;
- off-task interruption confirmed from another source.

#### V2B Interface cycling

**Definition:** repeated panel toggling or repeated navigation among the same windows without clear task progress.

**Use**
- useful for UX diagnosis and model feature engineering.

### V3. Engagement and persistence

#### V3A Sustained engagement

**Definition:** the learner maintains coherent task focus across an episode and continues working after difficulty.

#### V3B Disengagement / observational passivity

**Definition:** the learner is present on task but does not meaningfully act on available information.

**Typical indicators**
- long idle periods after output appears;
- visible opportunity to inspect metrics or graph but no inspection follows;
- passive watching without testing a next step.

**Important distinction**
- disengagement is not the same as silence;
- missing opportunity due to off-screen capture is `not_measurable`, not disengagement.

### V4. Error recovery and resilience

#### V4A Productive recovery

**Definition:** after an error, failed model, or unexpected output, the learner diagnoses and repairs the problem in a targeted way.

**Typical indicators**
- corrected label inversion after noticing impossible metrics;
- rebuild after reset with a clearly improved configuration;
- import failure followed by deliberate restart.

#### V4B Dead-end looping

**Definition:** the learner repeats the same unsuccessful move without diagnosis or adaptation.

**Typical indicators**
- repeated emit with unchanged flawed configuration;
- same threshold re-entered after failure with no new evidence consulted;
- repeated reset/rebuild to the same state.

### V5. Social dependence and help-seeking

#### V5A Productive help-seeking

**Definition:** the learner seeks help or responds to a challenge in a way that shows active ownership of the solution.

**Typical indicators**
- asks a question, then applies and adapts the answer;
- defends a model choice against peer challenge with own rationale;
- requests clarification and resumes independent work.

#### V5B Dependent execution

**Definition:** the learner performs the next move directly from peer/teacher direction without adding own rationale.

**Important rule**
- this code documents process context only; it does not automatically invalidate a scored construct unless the main rubric explicitly requires independent authorship.

### V6. Misconception traces

#### V6A MCR-zero targeting

**Definition:** the learner treats perfect training performance or zero error as the sole goal without generalization reasoning.

**Why it matters**
- this is a pedagogically important misconception and should be reported even if B9 remains `not_observed`.

#### V6B Label inversion / same-class collapse

**Definition:** the learner assigns class labels in a way that inverts or collapses the classification problem.

**Examples**
- positive and negative leaves swapped;
- both leaves assigned the same class.

#### V6C Metric scope awareness

**Definition:** the learner explicitly notices that the displayed metrics are incomplete for the decision context.

**Example**
- asking about precision or recall when CTR shows only MCR, sensitivity, or accuracy.

### V7. Video-only negative evidence

#### V7A No metric inspection

**Definition:** a model output is produced, but no active reading of the metric or matrix panel follows.

**Use**
- supports interpretation that B8 is not evidenced.

#### V7B No graph reading

**Definition:** a graph is opened or visible, but the learner does not visibly inspect or use it before the next decision.

#### V7C No comparison despite opportunity

**Definition:** multiple visible alternatives exist, but no comparison behavior is observed.

**Use**
- supports interpretation that B12 is not evidenced.

### V8. CODAP-specific strategic organization

#### V8A Multi-instance benchmarking

**Definition:** the learner opens several CODAP instances/windows to compare variables or thresholds in parallel.

**Coding rule**
- when direct cross-window comparison or transfer is explicit, this may support B4, B10, or B11;
- otherwise code it here as a process strategy.

#### V8B Table sorting for threshold estimation

**Definition:** the learner sorts the data table to visually estimate a candidate split point.

**Coding rule**
- this may support B0 as data appraisal when tied to a later decision;
- it remains a process strategy here when the strategic use of sorting itself is of interest.

#### V8C In-place CTR editing

**Definition:** the learner edits an already emitted record instead of building a fresh record.

**Use**
- distinguishes revision strategy from append-only comparison workflows.

#### V8D Import / session-continuity failure recovery

**Definition:** the learner encounters an import, network, or session-continuity failure (e.g., 404, unreachable server, failed dataset import) and then attempts recovery (retry, reload, alternate path, or restart).

**Typical indicators**
- failed import / “server not found” / IP-address error visible on screen;
- repeated import after failure;
- deliberate restart or alternate load path after continuity break.

**Exclusions**
- ordinary first-time dataset load with no failure;
- productive recovery from model/content errors without an import/session break (prefer V4A).

**Detection source**
- video / expert narrative: strong
- log: partial (analyst flags only)

**Use**
- profiles tool/infra disruption as a process event; does not establish proficiency.

## Code triage: zero-fire and near-zero codes (2025 cohort, n=17, 211 episodes)

**Last reviewed:** 2026-07-20 | **Trigger:** improvement plan Step 2

For each code that never fired or fired ≤1 time across the full 2025 cohort, one of four outcomes is assigned: **Keep-recruit**, **Redefine**, **Merge**, or **Retire**.

| Code | 2025 fires | Outcome | Rationale |
|------|-----------|---------|-----------|
| V1B chaotic_iteration | 0 | Keep-recruit | Theoretically present in CODAP Arbor. The 2025 task may have scaffolded students too heavily to produce chaotic behavior. Recruit from sessions with less instructional support or earlier task stages. Target ≥10 positive episodes before training. |
| V2B interface_cycling | 0 | Keep-recruit | Plausible when students repeatedly open/close panels without productive action. May require longer sessions or students experiencing interface confusion. |
| V3A sustained_engagement | 1 (Ozzy) | Keep-recruit | Fires rarely because most students show mixed engagement. The 1-episode signal is insufficient; recruit ≥10. |
| V5A productive_help_seeking | 0 | Keep-recruit | Requires a session where an instructor or peer is visibly present and provides accepted help. The 2025 individual-task design suppressed this. A collaborative or lab-based session would recruit it. |
| V7B no_graph_reading | 0 | Keep-recruit | Requires a visible graph opportunity followed by no inspection. May fire in sessions where students skip the graph panel entirely. Review sessions where V7A fires — V7B often co-occurs. |
| V7C no_comparison_despite_opportunity | 0 | Keep-recruit | High threshold: multiple visible alternatives AND no comparison. Likely suppressed because most sessions show at least minimal comparison. Review multi-emit episodes. |
| V8A multi_instance_benchmarking | 0 | Retire (task-context) | Opening multiple CODAP instances simultaneously is not typical student behavior in the 2025 task context. Move to `retired_codes` with the note: not observable in single-window CODAP Arbor sessions without explicit multi-tab scaffolding. Re-examine if 2026 tasks involve parallel model comparison. |
| V8B table_sort_threshold | 1 (Daisy) | Keep-recruit | Fires very rarely because most students use the visual tree interface rather than the raw data table. Sessions with explicit data-inspection prompts are more likely to recruit it. |

### Retired codes

The following codes are moved out of active training use for the 2025 cohort. They remain defined in this codebook for future data collection.

| Code | Retirement reason | Restore condition |
|------|------------------|------------------|
| V8A multi_instance_benchmarking | Not observable in single-window CODAP Arbor sessions. Zero fires across 211 episodes, and the task design does not create the multi-window context the code requires. | Restore when 2026 or later sessions involve parallel model comparison across explicit multi-window or multi-tab scaffolding. |

---

## V7 negative-evidence pre-check protocol

**Applies to:** V7A (no metric inspection), V7B (no graph reading), V7C (no comparison despite opportunity)

**Rationale:** Absence-of-behavior codes are uniquely prone to false positives when the opportunity for the behavior was off-screen or simply not present. V7A fired in 34% of 2025 episodes and is the second-most-common code, making its reliability critical for training-set quality.

### Mandatory pre-check (must pass all three before coding `observed`)

1. **Opportunity visible.** Confirm that the behavioral target was present on screen during the episode. For V7A: the emit button or metric panel must have been visible. For V7B: a graph must have been open or actively available. For V7C: at least two distinct model configurations or alternatives must have been visible side by side or in rapid succession.

2. **Recording coverage.** Confirm that the recording covers the full window in which the behavior could have occurred. If the recording starts after a possible inspection, or has a gap during the relevant window, use `not_measurable`, not `not_observed`.

3. **No plausible off-screen activity.** Confirm there is no reason to believe the behavior occurred outside the recording frame (e.g., on a second monitor, after the camera stopped). If in doubt, use `not_measurable`.

### Decision rule

```
opportunity visible AND full coverage AND no off-screen ambiguity → observed
any condition fails → not_measurable  (not not_observed)
behavior actually seen → code is irrelevant (do not apply V7 codes when behavior occurs)
```

### Back-fill note

All existing V7A=`observed` cells where `frames_with_step_inheritance / frames_total < 0.90` for that episode should be reviewed and potentially reclassified to `not_measurable`. Flag these cells with `confidence_tier: T2` until reviewed.

---

## Process-only scope note

Active Q1 scope is **pipeline / process data / methods**. V-codes are not proficiency scores. Construct scoring artifacts are quarantined under `trash/scoring_out_of_scope_2026-07-20/`. Historical mapping notes below are interpretive only and must not be treated as an active scoring claim.

## Interpretive mapping (non-scoring)

| Process code family | Supports process interpretation of | Does not establish |
|---|---|---|
| V1 iteration quality | inspection cycles, control change discipline | proficiency levels |
| V2 load / usability | UX strain and navigation cost | scored competency |
| V3 engagement | persistence / passivity opportunities | reasoning quality |
| V4 recovery | repair vs dead-end loops | Deepen competency |
| V5 help-seeking | assistance context and agency | independent mastery |
| V6 misconceptions | error patterns and instructional need | construct mastery alone |
| V7 negative evidence | missed inspection / comparison opportunities | positive proficiency evidence |
| V8 CODAP-specific strategy | domain workflow profiling (incl. import recovery) | automatic Deepen |

## Machine-learning feature guidance

Consistent with ILSA process-data practice, these codes may be transformed into high-level model features such as:

- `systematic_iteration_present`
- `chaotic_iteration_present`
- `hesitation_episode_count`
- `productive_recovery_present`
- `mcr_zero_targeting_present`
- `metric_inspection_absent_after_emit`
- `multi_instance_strategy_present`
- `import_failure_recovery_present`

Do **not** flatten raw micro-clicks or frame counts into proficiency labels. Keep the process layer explicitly separate from any future scoring work.

## Recommended output shape

For each student/session, prefer **four linked process artifacts** (2025 cohort under `training_datasets/2025/<id>/`):

| File | Role |
|------|------|
| `<id>_expert_process_narrative.json` | Full `uzman_nitel_gözlemi` timeline (Analysis.docx equivalent) |
| `<id>_process_codes.json` | Episode-level V1–V8 process codes (observed / not_observed / not_measurable) |
| `<id>_log_process_metadata.json` | Log chronology + Task-4 variables video cannot supply |
| `<id>_video_analysis_bundle.json` | Process-only manifest + coverage audit |

Build with: `python scripts/build_video_analysis_bundle.py --all-2025`  
(also runs automatically after `finalize_2025_gold_alignment.py --all`).

Tabular export (lossless, Hugging Face–ready):

```bash
python scripts/export_process_codes_tables.py --all-2025 --merge-cohort
```

Per student under `tabular/`:
- `<id>_episodes.jsonl` — 1 row / episode
- `<id>_episode_process_codes.jsonl` — 1 row / episode × V-code (full matrix)
- `<id>_session_ml_features.jsonl` — 1 row / session (wide ML flags)

Cohort merge: `training_datasets/2025/hf_export/{episodes,episode_process_codes,session_ml_features}.jsonl`

Episode-level process JSON example:

```json
{
  "episode_id": "student_session_episode_01",
  "anchor_event": "emit_tree_data",
  "start_ms": 120000,
  "end_ms": 171000,
  "process_codes": {
    "V1A_systematic_iteration": {
      "decision": "observed",
      "evidence": ["threshold changed, metric inspected, next change delayed until review"]
    },
    "V7A_no_metric_inspection": {
      "decision": "not_observed",
      "evidence": []
    }
  },
  "assistance_status": "peer",
  "notes": "Peer suggested threshold, learner then defended own revised choice."
}
```

## Final rule

If a trace is visible in video but does not meet a scored construct criterion, **do not force it into B0-B13**. Preserve it here as process evidence. This is the key revision needed to make the full value of video analytically usable without damaging the validity of the construct rubric.
