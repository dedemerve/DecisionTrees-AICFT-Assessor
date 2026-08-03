# CODAP Arbor AI-CFT Behavior Coding Manual (B0–B13)

**Document type:** Official coding manual and methodological specification
**Intended use:** Supplementary Material for a Q1 educational technology journal, plus operational codebook for human coders and LLM-based scoring
**Behavior set:** B0–B13, fixed; no behaviors added or removed
**Operational source of record:** `calibration/codap_rubric_v4_candidate.json` (`rubric_id: codap_arbor_v4_candidate`, `schema_version: 4.0`)
**Companion analysis:** `framework/CODAP_AI_CFT_RUBRIC_V4_FINAL_REFINEMENT.md`
**Status:** Candidate codebook for expert content validation and independent double coding. Not yet an empirically validated instrument.
**Version:** 4.1-candidate
**Date:** 2026-07-19
**Change note (4.1):** Added Section 3.3 (researcher observation notes as second-order evidence); added B2 exclusion for CODAP fixed statistical lines; added B3 decision rule for wrong-target correction; added Section 4.2 rows for multiple recordings and no-task-engagement; added Section 6 rule for scaffolded speech; added B1 clarification for non-scatter-plot representations; updated Sections 15 and 16 accordingly.

---

## How to read this manual

This document is a coding manual, not a research paper. It is written so that two independent coders, or a coder and an LLM, reach the same decision on the same evidence. Every behavior is operationalized. Every ambiguity has a deterministic resolution. Where an empirical claim cannot yet be made, the manual says so rather than implying validation that does not exist.

Three terms are used throughout with fixed meanings:

- **Behavior**: the cognitive learning process that is scored (for example, threshold reasoning).
- **Evidence**: the observable worksheet, video, transcript, or log trace that supports or refutes a behavior.
- **Metadata**: counts, timings, sequences, coverage, and recording quality that describe a session but never determine a level by themselves.

A behavior receives one **decision state** (`observed`, `not_observed`, `not_measurable`) and, when observed, one **level** (`Acquire`, `Deepen`, or `null`). Confidence (`High`, `Medium`, `Low`) is recorded separately and never changes the level. `Create` is Not Applicable for every CODAP behavior; the reasoning is given in Section 1 and Section 14.

Global scoring rules that apply to every behavior:

1. Never score a behavior from interface state, a click, a drag, a count, a duration, or a change in model accuracy alone.
2. All criteria stated for a level must be met. Higher levels inherit lower-level criteria unless stated otherwise.
3. Use `not_measurable`, not a zero, when required evidence is unavailable because a modality is missing or capture is incomplete. Use `not_observed` only when the behavior was assessable and the qualifying evidence was absent.
4. Do not infer intention from a final screen state. Require a learner-produced artifact, a temporal action sequence, an explanation, or convergent evidence.
5. Outcome improvement may corroborate a strategy but cannot establish reasoning by itself.

---

# SECTION 1. Conceptual Foundations

## 1.1 Why behaviors are scored instead of interface actions

The instructional context is a sequence of representations. Students learn classification decision trees through: physical data cards, threshold exploration, manual decision-tree construction, CODAP Arbor construction, model comparison, performance evaluation, and reflection. Across that sequence the learner produces thousands of interface events. A naive analytics approach would score those events directly. This manual does not, for a specific measurement reason.

The target construct is **Decision Tree Understanding**: the learner's demonstrated capacity to know decision-tree concepts, execute decision-tree procedures, choose and justify among alternatives, and reflect on limits and trade-offs, in ways that are evidentially grounded and distinguishable from unrelated abilities. This construct is domain-specific and multi-dimensional. An interface event is not a member of this construct. It is at most a trace from which a member of the construct may be inferred.

Scoring interface actions directly commits a construct-validity error. Construct validity, in Kane's argument-based sense, requires that the interpretation of a score be defensible as a claim about the target construct rather than about a proxy. A mouse click, a drag, a keystroke, a delete, or an emit is an operation on software. It is compatible with understanding, with imitation, with accident, and with off-task behavior. It therefore cannot, on its own, warrant a claim about cognition. The same trace supports several incompatible interpretations, which is the defining property of a construct-irrelevant indicator.

The distinction is not merely cautious. It protects the score from three well-documented threats:

- **Activity mistaken for understanding.** A learner who drags many attributes is active, not necessarily strategic.
- **Frequency mistaken for strategy.** A high threshold-change count can reflect systematic search or random flailing.
- **Fluency mistaken for reasoning.** Fast, confident operation can reflect competence or rote imitation of a demonstrated sequence.

Learning analytics and multimodal learning analytics research repeatedly report that low-level interaction counts are weak, unstable predictors of learning unless anchored to a semantic model of what the learner is trying to do. This manual therefore treats the interface event as evidence to be interpreted inside a meaningful episode, never as the unit of scoring.

## 1.2 Why clicks, drags, typing, and deletions are not behaviors

A behavior in this framework is a cognitive learning process with propositional content: an observation about the data, a claim about a boundary, an interpretation of a metric, a comparison between models. An interface action has no propositional content of its own.

| Interface action | Why it is not a behavior | What would make it evidence for a behavior |
|---|---|---|
| Mouse click | Selects or activates a control; compatible with any intention | A click that is part of a reconstructable inspect-then-decide sequence, corroborated by a statement or a connected model change |
| Dragging an attribute | Moves an object; does not encode a rationale | A drag preceded by data or graph consultation and connected to a stated or applied reason (B4) |
| Typing a value | Enters a parameter; the value alone carries no reasoning | A typed threshold accurately related to the cases it partitions (B6) |
| Deleting a row or tree | Removes an object; deletion is housekeeping | A deletion tied to an explicit diagnosis or comparison criterion (B12) |
| Moving a graph line | Operates a control; the line is a default until acted upon | A deliberate reposition followed by inspection of the resulting partition (B2) |

The rule is uniform: an action becomes evidence only when it is embedded in a meaningful episode that connects it to construct-relevant content. Isolated, the action is metadata.

## 1.3 The unit of analysis: the episode, not the frame

The unit of analysis is a **meaningful episode**, defined as a temporally bounded sequence that begins with task-relevant inspection or intention evidence and ends after the resulting model action, output review, or abandonment. An isolated video frame or a single log event can detect the presence of evidence, but it cannot establish reasoning, iteration, transfer, or comparison, all of which are inherently temporal. When an automatic window is required, the default is at least 30 seconds before and 20 seconds after the anchor event, extended to the next meaningful action.

This choice follows directly from qualitative content analysis practice, where the coding unit must be large enough to carry meaning and where reliability is defined over meaning-bearing units rather than surface tokens. It also follows from the observation that decision-tree reasoning is enacted over time: a threshold is proposed, its partition is inspected, and it is retained or revised. A frame samples that process; it does not contain it.

## 1.4 How AI-CFT learning outcomes map onto cognitive behaviors

The instrument reports against the UNESCO AI Competency Framework for Teachers. The framework's relevant progression is:

- **3.1 Acquire**: Basic AI techniques and applications.
- **3.2 Deepen**: Application skills.
- **3.3 Create**: Creating with AI.

Each behavior is aligned to specific learning-outcome identifiers rather than to coarse level labels (the full crosswalk is Section 14.6). Two alignment rules are load-bearing:

1. **Create ceiling.** Constructing and evaluating a decision tree in CODAP Arbor provides Acquire and Deepen evidence. It does not, by itself, satisfy the official Create block, which requires customization or assembly of an AI tool or model into a locally relevant solution. Treating routine Arbor operation as Create is a framework error. Create is therefore Not Applicable for B0–B13. Later customization tasks that carry genuine Create evidence must be scored under a separate, namespaced rubric.
2. **Evidence before competency.** An AI-CFT claim is a high-order interpretive layer. It is grounded in accumulated domain evidence, never in a single worksheet, a single behavior, or a direct behavior-to-competency shortcut. This follows the evidence-centered design (ECD) chain: raw evidence, evidence units, observable behaviors, learning objects, domain understanding, provisional competency, human-validated judgment.

## 1.5 Reference basis for Section 1

- UNESCO (2024). *AI competency framework for teachers.*
- Kane, M. T. (2013). Validating the interpretations and uses of test scores. *Journal of Educational Measurement, 50*(1).
- Mislevy, R. J., Steinberg, L. S., & Almond, R. G. Evidence-centered assessment design: layers, structures, and terminology.
- O'Connor, C., & Joffe, H. (2020). Intercoder reliability in qualitative research. *International Journal of Qualitative Methods, 19.*
- Cohn, C., et al. (2024). Multimodal methods for analyzing learning and training environments: a systematic literature review.
- Engel, J., & Erickson, T. (2023). What goes before the CART? Introducing classification trees with Arbor and CODAP. *Teaching Statistics, 45*(S1).

---

# SECTION 2. Behavior Specification

This section specifies every behavior B0–B13 with identical structure. The operational source of record is `calibration/codap_rubric_v4_candidate.json`; where this manual and the JSON differ in wording, the JSON governs machine scoring and this manual governs human interpretation, and any discrepancy is a defect to be reconciled before use.

**Criterion identifiers.** Each Acquire criterion is labeled `Bn-A1`, `Bn-A2`; each Deepen criterion is labeled `Bn-D1`, `Bn-D2`. Coders and LLMs report the specific criterion identifiers met, so that disagreements can be localized to a criterion rather than to a behavior.

**Level rule.** Acquire requires every listed Acquire criterion. Deepen requires every listed Deepen criterion and inherits Acquire. If Acquire criteria are not met, Deepen cannot be assigned even when a Deepen-flavored trace is present.

---

## B0: Data Familiarization and Variable Appraisal

**Behavior ID:** B0
**Learning Outcome alignment:** Acquire LO3.1.1; Deepen LO3.2.3 (supporting). Create: Not Applicable.
**Purpose:** Identify task-relevant properties of the dataset before or during model construction.
**Cognitive Construct:** Data sensemaking and variable awareness (concept formation about data).

**Theoretical Foundation.** Variable appraisal is the entry move of model-based reasoning: a learner cannot reason about a classifier's inputs without first apprehending the structure of the data those inputs describe. Statistical-reasoning research treats attention to variable type, distribution, and data quality as a disposition of statistical thinking rather than a byproduct of viewing a table. Constructivist accounts add that knowledge of the data is built through active engagement, not through exposure. B0 represents this construct because it requires the learner to produce or use a correct observation about a variable, which is an externalization of sensemaking, and it explicitly excludes the mere availability of a table, which is only software state.

**Operational Definition.** Code B0 when the learner actively inspects the dataset and produces or uses at least one correct observation about a variable's role, type, values, range, distribution, missingness, or class balance.

**Acquire Criteria.**
- **B0-A1:** Active inspection of at least one variable or case is observable.
- **B0-A2:** A correct data-relevant observation is expressed in a worksheet or transcript, or is used in the immediately connected modeling decision.

**Deepen Criteria.**
- **B0-D1:** Two or more variables, distributions, or data-quality properties are compared.
- **B0-D2:** The comparison is explicitly connected to a target, predictor, threshold, or evaluation strategy.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** correct description of variable type, range, distribution, class balance, or data quality; a written comparison used to motivate a later model decision.
- **Video:** purposeful table scrolling, sorting, column selection, or case inspection followed by a connected statement or action.
- **Transcript:** a specific, accurate statement about dataset content or variable properties.
- **Log:** data-context or case-selection events may locate the episode but cannot establish B0 alone.

**Video Evidence Indicators (never scored):** table revisited before a model choice; cursor tracks values within a named column; graph or table consulted before target or predictor selection.

**Exclusion Rules (do not score).**
- Table merely open or already visible.
- Scrolling without an identifiable task connection.
- A generic statement such as "I looked at the data" without a data observation.

**Decision Rules (ambiguity).** If inspection is visible but no observation is expressed, and no connected decision follows, code `not_observed`, not Acquire. If the data view is preloaded and provenance of inspection is unknown, lower confidence and do not infer B0 from the later correct model (global rule 4). If the worksheet carries the observation but the video does not show inspection, worksheet evidence is sufficient for Acquire.

**Common Coding Errors.** Scoring software readiness as familiarization; treating dwell time as attention; inferring a data observation backward from a later correct model.

**LLM Coding Notes.** Locate an explicit data observation or an inspection-to-decision link. If only the table state is visible, return `not_observed`. Dwell duration is metadata and never a level criterion. Precedence: worksheet or transcript observation outranks video inference.

**Behavior Dependencies.** Prerequisite: none. Optional predecessor: none. Possible successors: B1, B3, B4. B0 can support these but is not a mandatory prerequisite when equivalent worksheet evidence exists.

**Confidence Rating.** High: specific correct observation plus a connected action in another modality. Medium: specific correct observation in one complete modality. Low: inspection is visible but cognitive purpose is only indirectly supported.

---

## B1: Graph-Based Data Exploration

**Behavior ID:** B1
**Learning Outcome alignment:** Acquire LO3.1.1; Deepen LO3.2.2. Create: Not Applicable.
**Purpose:** Use a graph as an epistemic representation to examine patterns relevant to classification.
**Cognitive Construct:** Visual and representational reasoning.

**Theoretical Foundation.** A graph is not decoration; it is an external representation that offloads and restructures cognition. Dual Coding Theory explains why a visual encoding of the data supports reasoning that a table does not, and Representational Fluency research treats the ability to extract meaning from a chosen representation as a competence in its own right. B1 represents this construct because it requires the learner to extract or apply a pattern, separation, cluster, or relation, which is interpretation of a representation, and it excludes graph creation without examination, which is only tool use.

**Operational Definition.** Code B1 when the learner intentionally constructs, changes, or revisits a graph and extracts or applies a pattern from it to the classification task.

**Acquire Criteria.**
- **B1-A1:** A task-relevant graph is intentionally configured or examined.
- **B1-A2:** At least one visible pattern, separation, cluster, or relation is stated or used in a connected decision.

**Deepen Criteria.**
- **B1-D1:** Graphs or axis-variable configurations are compared.
- **B1-D2:** The comparison justifies predictor or threshold selection, rejection, or refinement.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** graph interpretation linked to a variable or split.
- **Video:** axis change, graph comparison, or graph revisit followed by a model decision.
- **Transcript:** specific interpretation of a plotted pattern or separation.
- **Log:** component creation or change identifies candidate episodes only.

**Video Evidence Indicators (never scored):** graph revisited before a split; cursor traces clusters or a boundary; axis variable changed; two graph panels compared.

**Exclusion Rules (do not score).**
- Graph merely visible.
- Default graph accepted without evidence of examination.
- Graph creation followed by unrelated activity.

**Decision Rules (ambiguity).** Two visible panels do not establish comparison; require evidence that the panels were contrasted. A movable value on a scatter plot belongs to B2, not B1; do not confuse a graph line with a tree threshold. If a pattern is named but never used, code Acquire only if B1-A2 is met through the statement itself.

B1 covers any intentional graphical representation used to examine classification-relevant patterns: scatter plots, mosaic charts, network graphs, bar charts, dot plots, and similar CODAP-supported visualizations. The representation type is not restricted to scatter plots. Apply the same criteria regardless of chart type: B1-A1 requires intentional configuration or examination, and B1-A2 requires that a pattern, separation, or relation is stated or used in a connected decision. A mosaic chart that shows class proportions by category meets these criteria when the learner reads it and uses the pattern. A network or graph representation that is opened, glanced at, and closed without an observable reading does not meet B1-A2. The presence of a non-scatter-plot representation does not change the exclusion rules.

**Common Coding Errors.** Equating graph creation with interpretation; confusing a scatter-plot movable value with a tree threshold; using graph count as a score.

**LLM Coding Notes.** Require a graph-to-meaning or graph-to-decision link. Multiple panels alone do not establish comparison. A plotted panel without a link is evidence metadata only.

**Behavior Dependencies.** Prerequisite: none. Optional predecessor: B0. Possible successors: B2, B4, B11. B1 does not imply B11 without cross-representational transfer evidence.

**Confidence Rating.** High: pattern is named and immediately used. Medium: purposeful comparison is visible without explanation. Low: only a revisit or cursor trace suggests examination.

---

## B2: Candidate Threshold Exploration

**Behavior ID:** B2
**Learning Outcome alignment:** Acquire LO3.1.1 (supporting); Deepen LO3.2.3. Create: Not Applicable.
**Purpose:** Generate and examine plausible decision boundaries before committing a tree split.
**Cognitive Construct:** Hypothesis generation and threshold reasoning.

**Theoretical Foundation.** Placing and moving a candidate boundary is hypothesis generation in the sense of dual-space search: the learner searches a hypothesis space of possible separations and tests each against the data it partitions. Variational reasoning frames this as attending to how outcomes change as a boundary changes. B2 represents this construct because it requires that the resulting partition be inspected or used, which is the test half of generate-and-test, and it excludes a default movable value and accidental drags, which carry no hypothesis.

**Operational Definition.** Code B2 when the learner deliberately places or changes a graph movable value and examines how the candidate boundary partitions cases.

**Acquire Criteria.**
- **B2-A1:** A movable value is deliberately placed or changed on a relevant graph.
- **B2-A2:** The resulting partition is inspected, described, or used as a candidate split.

**Deepen Criteria.**
- **B2-D1:** At least two candidate values are compared using separation, errors, or model consequences.
- **B2-D2:** The retained or rejected candidate is justified by that comparison.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** alternative candidate thresholds and their partitions or errors.
- **Video:** movable value repositioned with subsequent inspection or comparison.
- **Transcript:** reason for trying, retaining, or rejecting a candidate threshold.
- **Log:** graph events may delimit the episode; committed tree threshold changes belong primarily to B6.

**Video Evidence Indicators (never scored):** pause before moving the boundary; boundary moved and graph reread; cases near the boundary inspected.

**Exclusion Rules (do not score).**
- Movable value already present with no learner interaction.
- A single accidental drag.
- Repeated movement without evidence that partitions are being examined.
- CODAP fixed statistical lines (Mean value, Median, Percentile) placed on a graph: these are computed lines that show a dataset property, not a learner-adjusted candidate boundary. They do not constitute a "movable value" under B2-A1, even when the learner adds them deliberately. They may be evidence for B0 (data familiarization) or B1 (graph-based pattern reading) if examination follows.

**Decision Rules (ambiguity).** Two logged values are not a comparison; Deepen requires an evaluative contrast (B2-D1). If a movement is captured but purpose is ambiguous, code Acquire only if B2-A2 is met, else `not_observed`. Distinguish graph (B2) from tree (B6) throughout.

**Common Coding Errors.** Scoring the visual line itself; treating movement count as Deepen; confusing candidate exploration (B2) with committed-split reasoning (B6).

**LLM Coding Notes.** Deepen requires an evaluative comparison, not merely two logged values. Distinguish graph and tree controls explicitly.

**Behavior Dependencies.** Prerequisite: none. Optional predecessor: B1. Possible successors: B6, B11. B11 requires coordinated evidence from B2 and B6.

**Confidence Rating.** High: alternative values and partition consequences are explicit. Medium: deliberate movement and inspection are visible. Low: one movement is captured and purpose is ambiguous.

---

## B3: Prediction-Target Framing

**Behavior ID:** B3
**Learning Outcome alignment:** Acquire LO3.1.1. Deepen: not separately aligned. Create: Not Applicable.
**Purpose:** Formulate what the decision tree is intended to predict.
**Cognitive Construct:** Problem framing and the target-versus-predictor distinction.

**Theoretical Foundation.** Choosing what to predict is the framing move that defines a supervised-learning task. Problem-framing theory and model-based reasoning treat the identification of the dependent variable, and its separation from predictors, as a conceptual act that structures every later decision. B3 represents this construct because it requires intentional selection or an accurate target-versus-predictor distinction, not a populated drop zone, which can be a default or an automatic event.

**Operational Definition.** Code B3 when the learner intentionally identifies or selects the dependent variable and treats it as the prediction outcome rather than as a predictor.

**Acquire Criteria.**
- **B3-A1:** The selected target is consistent with the task.
- **B3-A2:** Evidence shows intentional selection or an accurate target-versus-predictor distinction.

**Deepen Criteria.**
- **B3-D1:** An alternative target is evaluated, or a target is changed or reaffirmed.
- **B3-D2:** The final choice is justified by the prediction question or its consequences for interpretation.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** prediction question and target variable stated consistently.
- **Video:** target deliberately dragged or changed after task or data inspection.
- **Transcript:** a statement of what is being predicted and why.
- **Log:** `set_dependent_variable` is supporting evidence only because it may fire automatically.

**Video Evidence Indicators (never scored):** task prompt revisited before target choice; target corrected after recognizing a mismatch; predictor list inspected before selection.

**Exclusion Rules (do not score).**
- Target preloaded or present at recording start.
- Automatic `set_dependent_variable` event.
- Correct target inferred only from the final model.

**Decision Rules (ambiguity).** A populated target field with unknown provenance is `not_observed`, not Acquire. A target change without a stated reason is not Deepen. Do not confuse target selection with positive-class definition, which is B5.

When a learner drags an incorrect variable as the target (for example, an administrative tag such as "Training/Test" or a predictor such as "Fat") and then corrects it to the task-appropriate target: the correction sequence is evidence for B3-D1 (an alternative target was evaluated). Code B3 as Deepen if B3-D2 is also met (the final choice is explicitly justified). If the learner corrects without explanation, cap at Acquire. Do not score the initial wrong drag as B3 evidence; score only from the correction onward. If the learner drags a non-target variable onto the prediction field and the interface rejects it without the learner taking a subsequent action, treat as a single interface event and do not code B3.

**Common Coding Errors.** Treating a populated field as intentional framing; scoring a target change as Deepen without a rationale; confusing target with positive-class definition.

**LLM Coding Notes.** Prefer worksheet or transcript evidence, or a visible selection sequence. State-only evidence is insufficient when provenance is unknown.

**Behavior Dependencies.** Prerequisite: none. Optional predecessor: B0. Possible successors: B7 (B3 precedes coherent construction); B5 specifies the class semantics of the B3 target.

**Confidence Rating.** High: intentional selection plus accurate prediction framing. Medium: intentional selection without explanation. Low: only indirect provenance suggests learner selection.

---

## B4: Strategic Predictor Selection

**Behavior ID:** B4
**Learning Outcome alignment:** Deepen LO3.2.3. Acquire: not separately aligned. Create: Not Applicable.
**Purpose:** Choose predictors on the basis of data, domain, or model evidence.
**Cognitive Construct:** Strategic variable selection.

**Theoretical Foundation.** Selecting predictors on evidence-based grounds indexes adaptive expertise rather than routine execution: the learner adapts the model to what the data and prior performance suggest, rather than dragging attributes at random or because they are domain-familiar. B4 represents this construct because it requires an observable basis for the choice, connecting the selection to a plausible relationship with the target, an observed pattern, or prior performance, and it excludes plausible-feature dragging with no ownership evidence.

**Operational Definition.** Code B4 when the learner selects a predictor and evidence connects the choice to a plausible relationship with the target, an observed data pattern, or prior model performance.

**Acquire Criteria.**
- **B4-A1:** A predictor is intentionally selected for a split.
- **B4-A2:** A plausible data-, domain-, or task-based basis for the choice is observable.

**Deepen Criteria.**
- **B4-D1:** At least two predictors are compared, or a predictor is replaced.
- **B4-D2:** The choice or replacement is justified using separation, errors, or performance evidence.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** predictor choice with a data- or domain-grounded rationale.
- **Video:** table, graph, or model output consulted before selection or replacement.
- **Transcript:** specific rationale linking predictor to target or model outcome.
- **Log:** `drop_attribute` and feature sequence locate choices but do not prove strategy.

**Video Evidence Indicators (never scored):** data consulted before drag; feature replaced after output review; alternative features compared.

**Exclusion Rules (do not score).**
- Random or teacher-directed drag with no ownership evidence.
- A domain-relevant feature treated as automatically strategic.
- Feature count used as level evidence.

**Decision Rules (ambiguity).** If only a feature name appears in a split, do not infer strategic selection; that is B7 state evidence, not B4. Do not infer rationale from an accuracy improvement (global rule 5). A single replacement is Deepen only if B4-D2 is met.

**Common Coding Errors.** Rewarding any plausible feature; inferring rationale from accuracy improvement; conflating predictor with target selection.

**LLM Coding Notes.** Extract alternatives, evidence, and criterion. A feature name in a split is not, by itself, strategic selection.

**Behavior Dependencies.** Prerequisite: none. Optional predecessors: B0, B1 (B4 can use their evidence but does not require B1). Possible successors: B7, B10.

**Confidence Rating.** High: explicit rationale plus a connected selection. Medium: clear inspection-to-selection sequence. Low: choice appears purposeful but rationale is unavailable.

---

## B5: Class Semantics and Positive-Class Framing

**Behavior ID:** B5
**Learning Outcome alignment:** Acquire LO3.1.1; Deepen LO3.2.3 (supporting). Create: Not Applicable.
**Purpose:** Define the meaning of model outcomes and the positive class in context.
**Cognitive Construct:** Classification concept formation and semantic framing.

**Theoretical Foundation.** Understanding what the two outcome classes mean, and which is the positive class, is concept formation in Vygotsky's sense of a scientific concept: a deliberately defined category that structures interpretation. It is also the semantic precondition for every downstream metric, because true positive, false positive, and sensitivity are meaningless until the positive class is fixed. B5 represents this construct because it requires correct application of class meaning and separation of the positive class from desirability, and it excludes default visible labels that may never have been interpreted.

**Operational Definition.** Code B5 when the learner defines or correctly applies the two outcome classes and the positive class in a way consistent with the task context.

**Acquire Criteria.**
- **B5-A1:** Both class meanings are correctly identified or applied.
- **B5-A2:** The positive class is distinguishable from desirability or moral value.

**Deepen Criteria.**
- **B5-D1:** The learner explains how class framing changes TP/TN/FP/FN interpretation or decision consequences.
- **B5-D2:** Alternative positive-class choices are evaluated when relevant.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** correct class labels, positive-class definition, and confusion-matrix semantics.
- **Video:** prediction labels deliberately assigned or corrected.
- **Transcript:** explicit statement of class meaning or positive outcome.
- **Log:** prediction-assignment events show action; semantics require another source.

**Video Evidence Indicators (never scored):** leaf labels checked after assignment; prediction reversed after noticing class meaning; matrix consulted after class assignment.

**Exclusion Rules (do not score).**
- Default class labels merely visible.
- Two labels present with no evidence they were learner-defined or interpreted.
- Treating "positive" as necessarily beneficial.

**Decision Rules (ambiguity).** Context-appropriate label text without provenance is supporting evidence at low confidence, not automatic Acquire. Resolve the positive class before interpreting any metric. Do not infer confusion-matrix understanding from valid labels.

**Common Coding Errors.** Scoring context-appropriate text without provenance; conflating class definition with target selection; inferring matrix understanding from valid labels.

**LLM Coding Notes.** Resolve positive class first. Visible labels are evidence availability, not behavior. Require semantic evidence, not text detection.

**Behavior Dependencies.** Prerequisite: none. Related: B3 (B5 specifies the class semantics of the B3 target). Possible successors: B8 and B13 both depend on defensible B5.

**Confidence Rating.** High: class and positive-class meaning explicit and correctly used. Medium: deliberate assignment or correction visible. Low: only contextual label consistency is available.

---

## B6: Decision-Boundary Reasoning

**Behavior ID:** B6
**Learning Outcome alignment:** Acquire LO3.1.1 (supporting); Deepen LO3.2.3. Create: Not Applicable.
**Purpose:** Select and refine a split boundary according to its partition and classification consequences.
**Cognitive Construct:** Quantitative threshold reasoning and iterative optimization.

**Theoretical Foundation.** Relating a committed split to the cases it assigns, and refining it on evidence, is the core inductive reasoning of recursive partitioning. It draws on quantitative and covariational reasoning (how membership and error change with the boundary) and on iterative refinement (proposing, testing, and revising a candidate against a goal). B6 represents this construct because it requires accurate partition interpretation or evidence-based revision, and it excludes a merely visible threshold and random numeric changes, which carry no reasoning.

**Operational Definition.** Code B6 when the learner applies a numeric or categorical split and accurately relates it to the cases assigned to each branch or to the resulting classification errors.

**Acquire Criteria.**
- **B6-A1:** A committed split is learner-produced.
- **B6-A2:** The learner accurately identifies or uses how the split partitions cases.

**Deepen Criteria.**
- **B6-D1:** Alternative splits are compared using partition quality, errors, or model evaluation.
- **B6-D2:** The selected split is retained, rejected, or revised with an evidence-based rationale.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** correct split rule and case partition; threshold comparison or optimization reasoning.
- **Video:** split changed after graph, data, or output review, and resulting branches inspected.
- **Transcript:** explanation of why a value separates cases or changes errors.
- **Log:** `change_split_values` supplies values and sequence but not reasoning.

**Video Evidence Indicators (never scored):** branch memberships inspected; threshold revised after error review; near-boundary cases checked; graph consulted before split.

**Exclusion Rules (do not score).**
- Threshold merely visible.
- Random numeric changes.
- A different value alone treated as iteration.
- A movable value without a committed tree split.

**Decision Rules (ambiguity).** If feature, target, class polarity, dataset, or depth also changed, do not attribute an outcome change to the threshold alone. A change count is not Deepen. Conflate neither B2 (graph candidate) nor B6 (committed split). Improved accuracy is corroboration, not proof.

**Common Coding Errors.** Using change count as Deepen; conflating B2 with B6; using improved accuracy as proof.

**LLM Coding Notes.** Require partition interpretation or evidence-based evaluation. A logged value change is supporting evidence only. If multiple elements change at once, do not attribute the effect to the threshold.

**Behavior Dependencies.** Prerequisite: none. Optional predecessor: B2. Possible successors: B7, B10; B11 requires coordinated B2 and B6.

**Confidence Rating.** High: split consequences and rationale explicit. Medium: inspection-to-revision sequence complete. Low: purposeful split visible but interpretation incomplete.

---

## B7: Coherent Model Construction and Execution

**Behavior ID:** B7
**Learning Outcome alignment:** Acquire LO3.1.3; Deepen LO3.2.1 and LO3.2.3. Create: Not Applicable.
**Purpose:** Integrate target, predictors, splits, and predictions into an executable classification model.
**Cognitive Construct:** Procedural integration and model construction.

**Theoretical Foundation.** Assembling target, predictors, splits, and leaf predictions into a coherent, executable tree is the synthesis act of model-based reasoning and of computational thinking: separate components are integrated into an algorithm that runs and produces output. Knowledge-integration theory frames coherence as the mark of understanding, distinct from possessing the parts. B7 represents this construct because it requires learner authorship or meaningful modification plus structural validity, and it excludes a preloaded tree, a copied tree run without modification, and an emit click alone.

**Operational Definition.** Code B7 when the learner assembles and executes a valid decision tree whose target, split structure, and leaf predictions form a coherent response to the task.

**Acquire Criteria.**
- **B7-A1:** Learner authorship or meaningful modification is observable.
- **B7-A2:** The executed tree is structurally valid and task-consistent.

**Deepen Criteria.**
- **B7-D1:** The learner reviews an output and deliberately rebuilds or reruns a changed configuration.
- **B7-D2:** The revision is connected to a diagnosed issue or an explicit goal.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** coherent tree or rule set constructed for the task.
- **Video:** target, split, predictions, and emit assembled by the learner; output-driven rebuild.
- **Transcript:** model plan or reason for rerunning or rebuilding.
- **Log:** ordered target/drop/split/emit events corroborate authorship and revision.

**Video Evidence Indicators (never scored):** tree assembled incrementally; leaf predictions checked; output read before rebuild; reset followed by targeted reconstruction.

**Exclusion Rules (do not score).**
- Tree already present at recording start.
- Copied tree run without meaningful modification or explanation.
- Emit click alone.
- Depth 2 alone treated as Deepen.

**Decision Rules (ambiguity).** Do not infer authorship or intention from a single final frame; reconstruct the ordered sequence configuration-1, output-1, evidence consulted, configuration-2, output-2. Repeated emits are not refinement. A structurally invalid but complex tree is not rewarded.

**Common Coding Errors.** Equating visibility with construction; counting repeated emits as refinement; rewarding structurally invalid but complex trees.

**LLM Coding Notes.** Reconstruct the ordered build-and-revise sequence. Do not code from a final-state frame when authorship is unknown.

**Behavior Dependencies.** Prerequisites (evidential): B3–B6 integrate into B7. Possible successors: B8 evaluates B7 output; B10 is a local refinement of B7; B9 is a generalization branch after B7.

**Confidence Rating.** High: complete construction sequence and valid output. Medium: meaningful modification and execution visible. Low: only partial provenance.

---

## B8: Model-Performance Interpretation

**Behavior ID:** B8
**Learning Outcome alignment:** Deepen LO3.2.1 and LO3.2.3. Acquire: not separately aligned. Create: Not Applicable.
**Purpose:** Draw an accurate claim about model quality from valid evaluation output.
**Cognitive Construct:** Reflective evaluation and statistical interpretation.

**Theoretical Foundation.** Reading a metric and connecting it to model quality is interpretation, not perception, and it enacts an evaluativist epistemology in which a claim is judged against evidence. Reflective evaluation requires the learner to move from a displayed number to a proposition about the model. B8 represents this construct because it requires an accurate interpretation tied to the learner's own model, and it excludes a merely visible metric, a number read without meaning, and an invalid all-zero matrix.

**Operational Definition.** Code B8 when the learner accurately interprets at least one valid performance measure and connects it to model quality, an error pattern, or a next decision.

**Acquire Criteria.**
- **B8-A1:** A valid metric or confusion-matrix quantity is accurately interpreted.
- **B8-A2:** The interpretation refers to the learner's current model rather than merely reading a label or number.

**Deepen Criteria.**
- **B8-D1:** At least two complementary measures or error types are integrated, or two models are compared.
- **B8-D2:** The interpretation motivates a justified model decision or limitation claim.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** accurate interpretation of accuracy, confusion matrix, sensitivity, or MCR.
- **Video:** metric panel actively inspected before a connected decision.
- **Transcript:** specific metric or error interpretation tied to the model.
- **Log:** `emit_tree_data` supplies valid values but cannot show interpretation.

**Video Evidence Indicators (never scored):** scroll to the confusion matrix; cursor compares FP and FN; post-emit active reading followed by a targeted change.

**Exclusion Rules (do not score).**
- Metric merely visible.
- Number read aloud without interpretation.
- Invalid all-zero confusion matrix or a no-prediction output.
- Accuracy improvement treated as interpretation.

**Decision Rules (ambiguity).** Verify class polarity and displayed denominators before accepting a TP/FP/FN or sensitivity claim. A post-emit delay is not evidence of reading. General evaluation is B8; contextual error-cost reasoning is B13 and must not be assumed from B8.

**Common Coding Errors.** Scoring output visibility; treating post-emit delay as reading; equating general evaluation with B13 trade-off reasoning.

**LLM Coding Notes.** Extract the chain metric/value, meaning, judgment or action. Verify class polarity and displayed values. If only values are visible or logged, return `not_observed`.

**Behavior Dependencies.** Prerequisite: valid B7 output. Possible successors: B12 (comparison); B8 never automatically implies B13.

**Confidence Rating.** High: specific accurate interpretation plus a connected decision. Medium: accurate interpretation in one semantic source. Low: inspection suggests interpretation but semantics are absent.

---

## B9: Training–Test Generalization Reasoning

**Behavior ID:** B9
**Learning Outcome alignment:** Acquire LO3.1.1 (supporting); Deepen LO3.2.2 and LO3.2.3. Create: Not Applicable.
**Purpose:** Use training data for construction and held-out data for estimating generalization.
**Cognitive Construct:** Generalization reasoning and validation awareness.

**Theoretical Foundation.** Using held-out data to estimate generalization is the defining scientific practice that separates description of a sample from prediction about new cases. It rests on inductive-generalization reasoning and on overfitting as a threshold concept: once grasped, it reorganizes how a learner evaluates any model. B9 represents this construct because it requires correct role assignment and evaluation on held-out data without tuning on it, and it excludes two visible dataset names and accidental switches, which carry no conceptual distinction.

**Operational Definition.** Code B9 when the learner correctly distinguishes training and test roles and uses held-out performance to evaluate a model without treating test data as additional training evidence.

**Acquire Criteria.**
- **B9-A1:** Training and test roles are correctly identified.
- **B9-A2:** The model is constructed on training data and evaluated on held-out test data.

**Deepen Criteria.**
- **B9-D1:** Training and test outcomes are compared.
- **B9-D2:** The learner makes an accurate claim about generalization, overfitting, or model selection without tuning on the test set.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** correct distinction and comparison of training and test results.
- **Video:** purposeful dataset switch in the correct sequence with output comparison.
- **Transcript:** explanation of held-out evaluation or a generalization gap.
- **Log:** dataset-change and emit sequences establish order but not conceptual distinction.

**Video Evidence Indicators (never scored):** training output recorded before the test switch; test result inspected without rebuilding on test; return to training after diagnosing generalization.

**Exclusion Rules (do not score).**
- Two dataset names merely visible.
- Accidental dataset switch.
- Test data used repeatedly to tune, then reported as unbiased performance.
- No train/test opportunity: code `not_measurable`, not zero.

**Decision Rules (ambiguity).** If dataset identity is ambiguous, code `not_measurable`, not a guess. Not every performance gap is overfitting; require an accurate claim for B9-D2. Verify chronology and that the initial model was preserved when applied to test.

**Common Coding Errors.** Scoring the Choosy interface; assuming roles from ambiguous names; calling any gap "overfitting."

**LLM Coding Notes.** Verify dataset identity, chronology, preservation of the initial model, and interpretation. If identity is ambiguous, code `not_measurable`.

**Behavior Dependencies.** Prerequisite: executable B7 model. Possible successor: strengthens B8; contributes to B12. B9 is a branch, not a prerequisite for all B8.

**Confidence Rating.** High: correct sequence and explicit generalization claim. Medium: correct sequence without explanation. Low: dataset labels or coverage ambiguous.

---

## B10: Conditional Model Refinement

**Behavior ID:** B10
**Learning Outcome alignment:** Deepen LO3.2.2 and LO3.2.3. Acquire: not separately aligned. Create: Not Applicable.
**Purpose:** Refine a heterogeneous subgroup with an additional split while managing complexity.
**Cognitive Construct:** Conditional reasoning and model-complexity management.

**Theoretical Foundation.** Adding a child split to address a specific subgroup is nested conditional reasoning: the learner reasons "within this branch, a further condition applies." Managing when to add or withhold complexity engages the bias-variance trade-off in an age-appropriate form. B10 represents this construct because it requires a subgroup-targeted diagnosis, and it excludes a merely visible depth-2 tree and complexity added everywhere without local rationale, because depth is structural metadata, not reasoning.

**Operational Definition.** Code B10 when the learner adds or revises a child split to address a specific subgroup, residual error pattern, or conditional relationship.

**Acquire Criteria.**
- **B10-A1:** A child-node split is learner-produced.
- **B10-A2:** Evidence identifies the subgroup or local classification problem the split is intended to address.

**Deepen Criteria.**
- **B10-D1:** Alternative child splits or depths are compared.
- **B10-D2:** The refinement is justified using local errors, performance gain, interpretability, or overfitting risk.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** valid multi-level tree with conditional rationale.
- **Video:** child node inspected and split after subgroup or output review.
- **Transcript:** explanation of why a branch requires further division.
- **Log:** node-specific drop/focus events and depth values support chronology only.

**Video Evidence Indicators (never scored):** focus on one impure leaf; child split revised; tree pruned or simplified after comparison.

**Exclusion Rules (do not score).**
- Depth-2 tree merely visible.
- Extra split added everywhere without subgroup rationale.
- Complexity treated as automatically superior.

**Decision Rules (ambiguity).** Depth metadata never triggers B10; require a local diagnosis. Do not duplicate B7 for every multi-level tree. Accuracy gain alone is not a rationale.

**Common Coding Errors.** Equating depth with level; duplicating B7; using accuracy gain alone as rationale.

**LLM Coding Notes.** Require subgroup-targeted diagnosis. Parse root-to-leaf conditions; depth metadata never triggers B10.

**Behavior Dependencies.** Prerequisite: B7 (B10 is a local elaboration of B7). Possible successors: evaluated through B8 or B12.

**Confidence Rating.** High: subgroup diagnosis, child split, and evaluation observed. Medium: targeted child-split sequence clear. Low: only local focus and split visible.

---

## B11: Cross-Representational Threshold Coordination

**Behavior ID:** B11
**Learning Outcome alignment:** Deepen LO3.2.2 and LO3.2.3. Acquire: not separately aligned. Create: Not Applicable.
**Purpose:** Coordinate a graphical boundary with a decision-tree split and evaluate their correspondence.
**Cognitive Construct:** Representational fluency and transfer.

**Theoretical Foundation.** Reconciling the same threshold across a graph and a tree is translation among representations, which representational-fluency research treats as a high mark of representational competence, and which transfer research treats as productive use of a construct across contexts. B11 represents this construct because it requires an intentional transfer of a threshold for the same variable, with matching values within display precision and temporal or semantic support, and it excludes coincidental numeric matches and the mere co-occurrence of B2 and B6.

**Operational Definition.** Code B11 when the learner intentionally transfers or reconciles a threshold for the same variable between a graph and the tree.

**Acquire Criteria.**
- **B11-A1:** Graph and tree use the same variable.
- **B11-A2:** Values match within display precision (Section 8) and temporal or semantic evidence supports intentional transfer.

**Deepen Criteria.**
- **B11-D1:** Transfer is repeated for another variable or revised after checking model consequences.
- **B11-D2:** The learner explains agreement, rounding, or a deliberate discrepancy between representations.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** graph-derived threshold explicitly applied to a tree rule.
- **Video:** graph read immediately before a matching tree entry; representations revisited for verification.
- **Transcript:** explicit graph-to-tree transfer statement.
- **Log:** temporal proximity of graph and threshold events supports but never proves transfer.

**Video Evidence Indicators (never scored):** alternation between graph and tree; value read then entered; rounding checked; tree result used to revisit the graph.

**Exclusion Rules (do not score).**
- B2 and B6 co-occur without transfer evidence.
- Values happen to match by coincidence.
- Different variables or incompatible scales.
- Approximate match outside display precision without explanation.

**Decision Rules (ambiguity).** Verify variable identity, units, value tolerance (Section 8), and temporal or semantic linkage. If any element is missing, do not score B11. Numerical equality is not intent.

**Common Coding Errors.** Treating equality as intent; ignoring variable identity or units; double-counting B2 and B6 as B11 automatically.

**LLM Coding Notes.** Confirm variable, units, tolerance, and temporal/semantic linkage. Missing any element means no B11.

**Behavior Dependencies.** Prerequisites (evidential): B2 and B6. B11 is a distinct coordination construct; neither B2 nor B6 implies it.

**Confidence Rating.** High: explicit statement or a read-enter-verify sequence. Medium: matching sequence and value. Low: approximate co-occurrence only.

---

## B12: Comparative Model Evaluation and Record Use

**Behavior ID:** B12
**Learning Outcome alignment:** Deepen LO3.2.1 and LO3.2.3. Acquire: not separately aligned. Create: Not Applicable.
**Purpose:** Use retained model records to compare alternatives and make an evidence-based selection.
**Cognitive Construct:** Comparative evaluation and metacognitive monitoring.

**Theoretical Foundation.** Using retained records to compare alternatives and select one on a criterion is metacognitive monitoring and control applied to one's own modeling, and it is the compare-select-apply cycle of evidence-based decision making. Self-regulated-learning theory frames this as evaluating and regulating a produced artifact against a standard. B12 represents this construct because it requires at least two records treated as alternatives and a comparison on an explicit criterion, and it excludes accumulated rows and deletion without evaluation, which are record management.

**Operational Definition.** Code B12 when the learner uses at least two retained model records to compare configurations or outcomes according to an explicit criterion.

**Acquire Criteria.**
- **B12-A1:** At least two valid model records are identified as alternatives.
- **B12-A2:** A comparison on at least one relevant criterion is observable.

**Deepen Criteria.**
- **B12-D1:** Multiple criteria, error costs, generalization, or complexity are integrated.
- **B12-D2:** A model is selected, rejected, or retained with an explicit evidence-based justification.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** comparison of multiple models with a selection rationale.
- **Video:** CTR rows deliberately selected, revisited, or compared with outputs.
- **Transcript:** specific comparison and model-selection claim.
- **Log:** multiple valid emits and row interactions establish opportunity, not comparison.

**Video Evidence Indicators (never scored):** alternating row selection; parameters and metrics compared; inferior record deleted after an articulated criterion.

**Exclusion Rules (do not score).**
- Multiple rows merely accumulated.
- Row deletion without evidence of evaluation.
- Latest model assumed to be preferred.
- Emit count used as a score.

**Decision Rules (ambiguity).** All three of alternatives, a common criterion, and a comparison are required; row count is metadata. Deletion is metadata unless tied to an explicit diagnosis or comparison. Do not conflate single-model interpretation (B8) with comparison (B12).

**Common Coding Errors.** Scoring CTR housekeeping; inferring comparison from visibility; conflating B8 interpretation with B12 selection.

**LLM Coding Notes.** Require alternatives, a common criterion, and a comparison. Row count is metadata only.

**Behavior Dependencies.** Prerequisites: multiple B7 outputs and at least basic B8 interpretation. Related: B13 may supply the comparison criterion.

**Confidence Rating.** High: alternatives, criterion, and justified selection explicit. Medium: direct comparison visible without a final selection. Low: navigation suggests comparison but semantics are incomplete.

---

## B13: Cost-Sensitive Metric Trade-Off Reasoning

**Behavior ID:** B13
**Learning Outcome alignment:** Deepen LO3.2.1 and LO3.2.3. Acquire: not separately aligned. Create: Not Applicable.
**Purpose:** Evaluate model errors according to context-dependent consequences rather than accuracy alone.
**Cognitive Construct:** Cost-sensitive evaluation and contextual judgment.

**Theoretical Foundation.** Weighing false positives against false negatives by their context-specific consequences is decision-theoretic reasoning under asymmetric costs, and it enacts a consequential, ethically aware view of model error that accuracy alone cannot express. B13 represents this construct because it requires an accurate metric interpretation combined with a contextual trade-off, and it excludes reciting a metric name or a formula, because vocabulary is not reasoning.

**Operational Definition.** Code B13 when the learner accurately interprets sensitivity, MCR, FP, or FN and uses contextual error consequences to compare or prioritize model outcomes.

**Acquire Criteria.**
- **B13-A1:** At least one relevant metric or error type is accurately interpreted.
- **B13-A2:** The interpretation identifies which cases or errors the quantity represents.

**Deepen Criteria.**
- **B13-D1:** A trade-off between sensitivity and MCR, or between FP and FN consequences, is explicitly evaluated.
- **B13-D2:** A priority or model choice is justified by the application context.

**Create Criteria.** Not Applicable.

**Observable Evidence.**
- **Worksheet:** correct calculation or interpretation and a contextual trade-off explanation.
- **Video:** relevant outputs inspected before a contextual decision; video alone rarely establishes the trade-off.
- **Transcript:** explicit interpretation and contextual prioritization.
- **Log:** metric values support checking but cannot establish reasoning.

**Video Evidence Indicators (never scored):** sensitivity/MCR fields compared; FP/FN cells revisited; two records inspected before a contextual choice.

**Exclusion Rules (do not score).**
- Metric term merely mentioned.
- Formula recited without interpretation.
- Accuracy-only comparison.
- Missing semantic source coded as zero instead of `not_measurable`.

**Decision Rules (ambiguity).** Require the chain metric meaning, contextual consequence, priority or choice. If neither transcript nor worksheet supplies semantic evidence, return `not_measurable`, not zero. Do not infer cost sensitivity from a low FN alone. Do not map evaluation to Create.

**Common Coding Errors.** Treating vocabulary as reasoning; inferring cost sensitivity from low FN; mapping evaluation to UNESCO Create.

**LLM Coding Notes.** Require metric meaning, contextual consequence, and priority or choice. If transcript and worksheet semantic evidence are unavailable, return `not_measurable`.

**Behavior Dependencies.** Prerequisites: B5 (class semantics) and B8 (metric interpretation). B8 never implies B13.

**Confidence Rating.** High: accurate meaning plus an explicit contextual trade-off. Medium: accurate contextual interpretation in one semantic source. Low: inspection only, without a complete trade-off.

---

# SECTION 3. Evidence Taxonomy

The framework separates three layers. Confusing them is the primary source of construct-invalid scoring. This section makes the separation explicit and gives the rule that only behaviors receive levels.

## 3.1 The three layers

| Layer | Definition | Role in scoring | Examples |
|---|---|---|---|
| **Behavior** | A cognitive learning process with propositional content | The only layer that receives a level | "The salt column separates the two classes near 11.6"; "Sensitivity matters more here because a missed positive is costly" |
| **Evidence** | An observable trace that supports or refutes a behavior | Interpreted inside an episode to decide a behavior | A worksheet sentence; a transcript utterance; a video sequence of inspect-then-select; a validated log event |
| **Metadata** | Counts, timings, sequences, coverage, and technical quality | Locates episodes and qualifies confidence; never sets a level | `threshold_change_count`; `time_to_first_emit_ms`; `frame_coverage_ratio`; `audio_available` |

## 3.2 Why evidence never receives a score

Evidence is a trace, not a claim. The same trace is compatible with several intentions. A confusion matrix that is visible on screen is evidence that output was available; it is not evidence that the learner interpreted it. Scoring the trace rather than the interpreted behavior would inflate the score with construct-irrelevant variance (Section 1.1). Evidence therefore enters scoring only after it is interpreted inside a meaningful episode and connected to a behavior's criteria.

## 3.3 Behavioral observation transcripts (Analysis documents)

Some datasets include observer-authored behavioral transcripts (for example, an `Analysis.docx`) in which a researcher recorded every observable learner action on the screen in real time or from video review. These documents are **primary behavioral evidence** of the same epistemic type as a validated event log combined with a behavioral transcript. They describe the actual sequence of interface actions (drags, value changes, emit events, graph operations) and include verbatim learner and teacher utterances in quotation marks where speech was audible.

Evidence status by content type:

| Content in the Analysis document | Evidence status | Equivalent to |
|---|---|---|
| Action description (e.g., "Fat sürüklenir", "threshold 15 yerine 11 olarak güncellenir") | Primary action evidence | Validated log event; authoritative for what occurred and its order |
| Verbatim learner utterance in quotation marks with speaker identified | Transcript evidence — High confidence when the session had audio, Medium when reconstructed from video only | Diarized transcript segment |
| Verbatim teacher or peer utterance in quotation marks | Other-speaker transcript evidence; not usable as learner evidence except to establish context or opportunity | Background conversation entry |
| Observer paraphrase of learner intent (no quotation marks) | Supporting context; not scored as a learner-produced semantic claim | Researcher fieldnote |

Coding rule: Treat action descriptions in an Analysis document as you would a validated log: use them to reconstruct the temporal sequence, locate episodes, and establish the doing element of a criterion. Apply the same criteria for Acquire and Deepen as you would when coding directly from video or log. Do not treat observer paraphrases of intent as a stated learner rationale; require a quoted utterance or a worksheet response for any criterion that demands learner-produced semantic content.

## 3.4 Worked separation

Consider a learner who moves a scatter-plot line to 11.6, pauses, then sets a tree split at 11.6 and says "so anything above 11.6 is class A."

- **Metadata:** one graph movement; one split change; a two-second pause; a timestamp.
- **Evidence:** the ordered video sequence; the transcript utterance; the two logged values within display precision.
- **Behavior:** B2 (candidate exploration, from the graph move plus inspection), B6 (decision-boundary reasoning, from the accurate partition statement), and potentially B11 (transfer, only if the read-then-enter linkage is supported and the values match within Section 8 tolerance).

The counts and pause never score. They locate the episode and raise or lower confidence. The behaviors score.

---

# SECTION 4. Video Coding Manual

Screen recordings are the richest and the noisiest source. This section gives deterministic handling for each recurring capture problem. The governing principle is that video establishes what occurred and the order in which it occurred; it does not by itself establish stated reasoning, which comes from worksheet or transcript.

## 4.1 Frame aggregation

Detect evidence at the frame level, then code the episode. A frame that shows a threshold value is a detection; the behavior is coded over the surrounding episode (at least 30 seconds before and 20 seconds after the anchor, extended to the next meaningful action). Never assign a level from a single frame. Merge adjacent detections that belong to the same action into one episode before coding.

## 4.2 Recurring capture problems

| Case | Deterministic handling |
|---|---|
| **Multiple windows or monitors** | Mark capture incompleteness, lower confidence, and never infer actions on an unseen surface. If a required action is off-screen, the dependent behavior is `not_measurable`, not `not_observed`. |
| **Hidden interface elements** (collapsed matrix, off-screen tree) | Logged values show availability, not inspection. Score only what is visible. Do not reconstruct hidden elements. |
| **Screen freezes** | Treat the frozen interval as missing capture. Use logs to locate events but do not infer visual transitions across the freeze. Lower confidence or mark `not_measurable`. |
| **Cursor disappearance** | The cursor is a confidence indicator only. Its absence never removes an otherwise supported behavior and its presence never adds one. |
| **Fast actions** | Speed neither proves fluency nor guessing. Slow the review, use logs to confirm the sequence, and code the reconstructed episode. |
| **Video compression artifacts** | If a value is unreadable, treat it as missing for that behavior and seek the value in logs or worksheet. Do not guess a digit. |
| **Frame skipping / low frame rate** | Use logs to locate events; do not infer the missing visual transition. If the transition is load-bearing for the behavior (for example an iteration), lower confidence or code `not_measurable`. |
| **Multiple separate recording files for one student** (session split across two or more files) | Treat the ordered file set as a single session. Each inter-file gap is handled as a recording-ends-early / recording-starts-late pair under the two rules below. Behaviors whose qualifying evidence spans two files are assessable when both files are available and the gap interval is not load-bearing for the criterion (for example a comparison that must be continuous). When the gap is load-bearing, lower confidence or code `not_measurable` for the affected criterion only. Always document the gap duration and the file count in metadata. |
| **No task engagement** (tool opened but dataset not loaded, or task not started before recording ends) | Code all behaviors as `not_measurable` and record `session_status: no_task_engagement` in metadata. This is a session-level condition, not a per-behavior zero. The learner had no opportunity to produce task-relevant evidence. Do not infer ability from what was not done. If the recording shows only application launch or interface inspection with no data and no task action, do not apply any exclusion rule from Section 2; the opportunity condition in step 1 of Section 11.1 is not met. |
| **Recording starts late** (capture begins after the session start) | Any behavior whose qualifying evidence would fall in the uncaptured interval is `not_measurable`, not `not_observed`, for that interval only. Use logs, if available and validated, to determine whether a load-bearing action occurred before capture began; if logs are absent or unvalidated, do not infer the missing opening state. A tree, graph, or label already present when capture begins is preloaded state under the standard exclusion rules (Section 2) unless prior construction is independently established. |
| **Recording ends early** (capture stops before the session end) | Any behavior whose qualifying evidence would fall after the cutoff is `not_measurable` for that interval, not a zero. Do not extrapolate a final decision, a final threshold, or a comparison outcome from the last captured frame. If a Deepen criterion depends on an action after the cutoff (for example a revision or a final selection), cap the coded level at what was directly observed before the cutoff. |

## 4.3 Standard video reading order

1. Confirm recording quality and whether the behavior had an opportunity to occur.
2. Identify learner-attributable artifacts and actions (exclude preloaded state).
3. Reconstruct the temporal sequence of actions and outputs.
4. Only then decide the behavior, applying exclusions before positive criteria.

---

# SECTION 5. Worksheet Coding Manual

Worksheets carry the clearest semantic evidence and are often the deciding source when audio is missing. The unit is the response to a prompt, read together with any linked table or figure the prompt requires.

| Case | Deterministic handling |
|---|---|
| **Missing response** | The behavior is `not_observed` if the item was assessable, or `not_measurable` if the worksheet region is absent, illegible from capture loss, or the task was not administered. A blank is never Acquire. |
| **Partially completed response** | Score only the completed, legible portion against the criteria. A partial answer can meet Acquire without meeting Deepen; do not extrapolate the missing part. |
| **Multiple answers to one prompt** | If answers are mutually consistent, code the behavior they jointly support. If they conflict and none is marked final, code the lower defensible level and flag an evidence conflict. If one is clearly marked as the final answer, code that one. |
| **Erasures** | An erased-then-replaced answer is scored on the replacement. The erasure itself is metadata (possible revision) and never a level. |
| **Marginal annotations** | Annotations count as evidence when they carry construct-relevant content (a threshold, a comparison, a rationale). Decorative marks are metadata. |
| **Unclear handwriting** | If a value or word cannot be read with confidence, treat it as missing for that behavior. Do not infer the intended value from context to reach a higher level. Lower confidence when a legible-but-uncertain reading is used. |
| **Crossed-out answers** | A crossed-out answer is treated as withdrawn. Score the retained answer. If only a crossed-out answer exists, code `not_observed` for the intended behavior and record the crossed-out content as metadata about revision. |

Handwriting and completeness are recording-quality issues. They lower confidence and can force `not_measurable`, but they never, by themselves, lower a learner's level.

---

# SECTION 6. Transcript Coding Manual

Transcripts supply stated reasoning. They are structurally unequal across this dataset: several sessions have confirmed silent audio (microphone inactive at capture; RMS zero across all formats), so a substantial share of learner sessions carry no recoverable speech (see `calibration/audio_limitations.json`). Missing transcript is therefore treated as a modality-availability condition, not as evidence of absence.

| Case | Deterministic handling |
|---|---|
| **Missing audio** (confirmed silent or absent) | Set transcript context to null. Behaviors that can be met through worksheet or complete temporal video evidence are still assessable. Behaviors that require a semantic source (notably B13, and Deepen for B5) are `not_measurable` when neither transcript nor worksheet supplies the semantics. Missing transcript never lowers a level that other direct evidence can establish. |
| **Background conversation / other speakers** | Attribute utterances to the focal learner only when speaker identity is established (diarization plus gold speaker labels). Unattributable speech is metadata, not learner evidence. |
| **Partial speech** (dropouts, low intelligibility) | Code only clearly transcribed, attributable content. Treat unintelligible spans as missing; do not complete them. |
| **Off-task discussion** | Off-task speech is metadata (`off_task_duration_ms`) and is not scored, positively or negatively. |
| **Thinking aloud** | Concurrent think-aloud is valid reasoning evidence when attributable and specific. It supports Acquire and Deepen like any other transcript evidence. |
| **Retrospective explanation** | A retrospective account (after the action) supports stated reasoning but does not by itself establish that the reasoning drove the original action. Use it for the reasoning criterion; require action or artifact evidence for the doing criterion. Flag when action and speech conflict. |
| **Scaffolded or teacher-initiated speech** | When an instructor explains a concept, states a metric value, or names a strategy aloud, that speech is the teacher's evidence, not the learner's, regardless of whether the learner is present. Do not use teacher utterances to meet any learner behavior criterion. When the learner subsequently restates the teacher's explanation, the learner's own restatement is valid transcript evidence **only if** it adds specificity, correct application, or contextual adaptation beyond the scaffolded prompt. A verbatim repeat of the teacher's words, without a learner-generated extension or application, is echo behavior and is not scored. When the learner performs an action immediately after a teacher demonstration or directive (for example, drags the suggested predictor), treat the action as teacher-directed under the B4 exclusion unless the learner adds an observable rationale. The `assistance_status` metadata field records the episode context; it never penalizes independent behavior and never inflates teacher-directed behavior. |

**Confidence adjustment.** For confirmed-silent sessions, downgrade confidence from High to Medium where speech would normally triangulate an inference, and disclose the modality limitation in any publication (this is a preregistered handling rule, not a per-case judgment).

---

# SECTION 7. Evidence Hierarchy

When sources disagree, the coder needs a deterministic precedence rule. The hierarchy is not a fixed source ranking; it is a role-based rule, because different sources are authoritative for different questions.

## 7.1 Role-based precedence

1. **What occurred and in what order:** validated video and validated logs are authoritative. Between them, validated logs outrank uncertain visual timing, but logs never establish cognition.
2. **What the learner reasoned:** worksheet and transcript are authoritative. Direct learner-produced semantic evidence outranks interface-state inference.
3. **Numerical values:** logs and legible on-screen readings are authoritative for the value itself, subject to the tolerance rules in Section 8.

A behavior generally needs both a doing element (from sources of type 1) and, where the criterion demands reasoning, a reasoning element (from sources of type 2). Metadata is never authoritative for any of the three questions.

## 7.2 Conflict resolution

| Conflict | Resolution |
|---|---|
| Video shows the action; worksheet denies the reasoning | The action is evidence of doing; the absent reasoning caps the level. If a criterion requires reasoning and none exists, do not assign that level. This is not a contradiction; the two sources answer different questions. |
| Transcript claims a reasoning; video shows no corresponding action | Stated reasoning without the doing element cannot satisfy a criterion that requires the action. Code the lower defensible level and emit an `evidence_conflict`. |
| Two irreconcilable sources on the same question | Assign the lower defensible level and record an `evidence_conflict`. Never average. |
| Log value and on-screen value differ within tolerance | Treat as the same value (Section 8). |
| Log value and on-screen value differ beyond tolerance | Record `sync_error` metadata, prefer the legible learner-facing value for semantic claims, and lower confidence. |

## 7.3 The "Video says YES, Worksheet says NO" case

The example in the specification is resolved by roles, not by outranking. If the video shows a learner set a split at 11.6 (a YES on the doing element for B6-A1) but the worksheet gives no partition interpretation and none is spoken (a NO on B6-A2), then B6 is `not_observed`, because Acquire requires both criteria. The video does not "win"; it establishes only the element it is authoritative for. Conversely, if the worksheet supplies an accurate partition interpretation but the video did not capture the split action (off-screen), and the tree is otherwise learner-attributable, the behavior can still be Acquire, with confidence lowered for the missing action capture.

---

# SECTION 8. Tolerance Rules

Numeric agreement must be deterministic so that two coders, or a coder and an LLM, treat the same two values identically. All tolerances below are preregistered and must be documented in the methods section; they are not adjusted per case.

## 8.1 Display precision and the display step

CODAP Arbor renders movable-line values and tree split values to a fixed number of decimals as shown in the interface. Define, per field:

- `d` = the number of decimal places the interface displays for that field.
- `display_step = 10^(-d)` (the smallest difference the display can distinguish). For a field shown to one decimal, `display_step = 0.1`.

Two values `a` and `b` are the **same value** for coding when both of the following hold:

1. They render to the identical displayed string at precision `d` (round half up), and
2. `|a - b| <= 0.5 * display_step`.

Rounding uses round-half-up applied to the last displayed digit, fixed for reproducibility.

## 8.2 Worked examples at one-decimal display (`d = 1`, `display_step = 0.1`)

| Comparison | Rounded strings | \|a - b\| | Same value? | Reason |
|---|---|---|---|---|
| 11.6 vs 11.7 | 11.6 vs 11.7 | 0.10 | No | Different displayed values; difference equals a full display step |
| 11.64 vs 11.6 | 11.6 vs 11.6 | 0.04 | Yes | 11.64 rounds to 11.6; within half a step |
| 11.65 vs 11.7 | 11.7 vs 11.7 | 0.05 | Yes | 11.65 rounds half-up to 11.7; within half a step |
| 11.65 vs 11.6 | 11.7 vs 11.6 | 0.05 | No | Round-half-up sends 11.65 to 11.7, not 11.6 |
| 11.649 vs 11.65 | 11.6 vs 11.7 | 0.001 | No | The two round to different displayed strings even though numerically close; the display-string rule governs |

The display-string rule (condition 1) is decisive when a value sits on a rounding boundary. This removes coder discretion at the boundary.

## 8.3 Cross-representational tolerance (B11)

A graph-derived value and a tree split value for the **same variable** are a match for B11 when they are the same value under Section 8.1 at the coarser of the two fields' display precisions. Variable identity and unit identity are prerequisites and are checked first; a value match across different variables or units is never B11.

## 8.4 Slider and movable-line precision

If the movable line snaps to a grid, the grid step replaces `display_step` in Section 8.1. If the line is continuous, use the displayed precision `d`. A single logged value equal to the grid default with no learner movement is excluded (interface state).

## 8.5 Timing windows

- **Adjacent frames / same event:** two detections are the same event when they are within 1 second and no intervening meaningful action separates them.
- **"Immediately before" / read-then-enter linkage:** a read and a subsequent entry are linked when they occur within 10 seconds with no intervening unrelated action. Beyond 10 seconds, temporal linkage alone is insufficient and semantic evidence is required.
- **Episode window:** the default automatic window is 30 seconds before and 20 seconds after the anchor, extended to the next meaningful action.

## 8.6 Metric tolerance

Confusion-matrix counts are integers and are compared exactly. Derived metrics (accuracy, sensitivity, MCR) are compared at the precision the interface displays. A learner-stated metric is "accurate" when it matches the displayed value under Section 8.1 or is a correct exact fraction of the displayed integer counts.

---

# SECTION 9. Video Evidence Appendix

The indicators below improve evidential confidence. They never produce a score. Pauses, cursor movement, click counts, and time on screen are never behavior scores; they qualify confidence and episode interpretation only.

| Behavior | Non-scored video indicators |
|---|---|
| B0 | table scrolling or resizing; column tracing; return to data before a decision |
| B1 | axis inspection or change; cluster tracing; graph comparison or revisit |
| B2 | pause at candidate values; boundary adjustment followed by rereading; near-boundary inspection |
| B3 | task prompt reread; deliberate target drag; correction of a target/predictor reversal |
| B4 | data or graph consultation before a drag; targeted predictor replacement after output |
| B5 | leaf composition checked; labels corrected; matrix inspected after polarity assignment |
| B6 | branch memberships checked; threshold revised after error review; graph consulted before split |
| B7 | incremental construction; predictions checked; output read before rebuild |
| B8 | scroll to matrix; cursor compares FP and FN; targeted post-emit correction |
| B9 | dataset identity checked; training output retained; unchanged model applied to test |
| B10 | impure leaf selected; child split changed; complexity added or reverted after review |
| B11 | graph-tree alternation; value read then entered; rounding verified |
| B12 | alternating rows; common fields compared; dominated model removed after evaluation |
| B13 | metric or error cells compared; a context-specific decision follows output inspection |

---

# SECTION 10. Metadata Appendix

Every variable below is useful for locating episodes, describing process, or auditing evidence quality. None sets a level. The last column states why.

| Variable | Operational definition | Why useful | Why never scored |
|---|---|---|---|
| `time_to_first_target_ms` | session start to first attributable target selection | workflow onset and usability | latency is not problem framing |
| `time_to_first_split_ms` | session start to first committed split | workflow comparison | speed is not threshold reasoning |
| `time_to_first_emit_ms` | session start to first valid emit | process description | speed is not competence |
| `feature_change_count` | number of predictor replacements | locates exploration or instability | frequency cannot show strategy |
| `unique_features_tried` | distinct predictors used | describes search breadth | breadth may be systematic or random |
| `threshold_change_count` | number of threshold changes | locates candidate episodes | changes do not show evaluation |
| `unique_thresholds_tried` | distinct values within precision | search-space description | count does not show reasoning |
| `graph_creation_count` | graph panels created | tool-use profile | creation is not interpretation |
| `graph_revisit_count` | returns to an existing graph | potential cross-representation episodes | revisiting does not prove use |
| `emit_count` | all emit events | candidate model opportunities | repetition is not refinement |
| `valid_emit_count` | emits with valid predictions | output opportunity | valid output is not interpretation |
| `depth2_attempts` | valid depth >= 2 model attempts | locates B10 episodes | depth is structural metadata |
| `max_tree_depth` | maximum observed depth | complexity description | complexity is not quality |
| `tree_rebuild_count` | reset followed by construction | locates revision episodes | rebuild can reproduce the same model |
| `comparison_cycles` | transitions among distinct records | locates B12 opportunities | navigation is not comparison |
| `dataset_switch_count` | train/test or context switches | locates B9 episodes | switch does not show role awareness |
| `late_behavior_onset` | first qualified evidence timestamp per behavior | temporal trajectory | timing is not proficiency |
| `pause_before_model_selection_ms` | dwell before a choice | deliberation hypothesis | pause may be distraction |
| `post_emit_gap_ms` | emit to next meaningful action | output-reading opportunity | gap does not show reading |
| `active_tree_read_ms` | focal tree interaction after output | attention evidence | attention does not prove interpretation |
| `undo_count` | undo or reversal events | error-recovery description | undo may be correction or accident |
| `instruction_revisit_count` | instruction panel reopens | self-regulation context | instruction use is not a target behavior |
| `assistance_status` | independent / peer / instructor / unclear | agency qualifier | assistance is not an automatic penalty |
| `off_task_duration_ms` | verified off-task interval | coverage and context | not an inverse competency score |
| `frame_coverage_ratio` | captured relevant intervals / expected intervals | evidence-quality audit | technical completeness is not performance |
| `audio_available` | usable learner-audio flag | missingness stratification | modality access must not alter ability |
| `log_available` | usable event-log flag | provenance and sequence quality | missing logs are not behavior absence |
| `sync_error_ms` | estimated log-video offset or error | temporal-validity audit | technical error is not learner error |
| `duplicate_frame_ratio` | redundant frames / captured frames | extraction QA | sampling artifact is not behavior |
| `model_configuration_hash` | normalized target/features/thresholds/classes/depth | detects substantive model changes | a hash difference does not prove rationale |

---

# SECTION 11. Coder Manual (Human)

## 11.1 Master decision procedure

Apply this procedure to every behavior in every episode, in order.

1. **Opportunity check.** Did the behavior have a chance to occur, and is the required modality present? If not, code `not_measurable` and stop.
2. **Provenance check.** Exclude preloaded, copied, or teacher-directed state as authorship (global rule 4; Section 2 exclusions).
3. **Exclusions before criteria.** Apply the behavior's exclusion rules. If an exclusion fires, code `not_observed` and stop.
4. **Acquire test.** Are all Acquire criteria met with direct evidence? If not, code `not_observed`.
5. **Deepen test.** Are all Deepen criteria met, with Acquire inherited? If not, cap at Acquire.
6. **Confidence.** Assign High, Medium, or Low from the behavior's confidence rubric, independent of the level.
7. **Record.** Log criterion identifiers met, evidence references (source and timestamp or worksheet locus), exclusions checked, and any `evidence_conflict`.

## 11.2 Decision tree (text form)

```
Opportunity + required modality?
  No  -> not_measurable
  Yes -> Preloaded/copied/teacher-directed authorship?
           Yes -> not_observed (state, not behavior)
           No  -> Any exclusion rule fired?
                    Yes -> not_observed
                    No  -> All Acquire criteria met by direct evidence?
                             No  -> not_observed
                             Yes -> All Deepen criteria met?
                                      No  -> observed / Acquire
                                      Yes -> observed / Deepen
Then assign confidence independently; never let confidence change the level.
```

## 11.3 Worked examples

- **Positive (Deepen).** Learner compares split at 11.6 versus 12.0 on the graph, states 11.6 "misclassifies fewer heavy items," sets 11.6 in the tree, and checks the branches. B6-A1, B6-A2, B6-D1, B6-D2 met. Code B6 = Deepen, High confidence.
- **Acquire, not Deepen.** Learner sets 11.6, correctly says "above 11.6 goes right," but never compares alternatives. B6-A1, B6-A2 met; B6-D1 not met. Code B6 = Acquire.
- **Exclusion.** A depth-2 tree is visible at recording start with no build sequence. B7 authorship exclusion fires. Code B7 = `not_observed` for construction; note preloaded state.
- **Not measurable.** Silent session, no worksheet trade-off item, learner inspects sensitivity but says nothing. B13 has no semantic source. Code B13 = `not_measurable`, not zero.

## 11.4 Calibration workflow

1. Train coders on the behavior/evidence/metadata separation and the episode unit.
2. Provide, per behavior, exemplars of each type: positive, negative, borderline, missing-modality, and conflicting-evidence.
3. Require independent qualification on a held-out calibration set before production coding.
4. Freeze a versioned codebook after calibration. Any later change triggers an impact review and recoding of affected cases.

## 11.5 Adjudication workflow

1. Preserve the original independent codes; never overwrite them.
2. Compute reliability first (Section 13), then adjudicate disagreements with a third coder or a panel.
3. Log the disputed evidence, each original decision, the final decision, the rationale, and any rule change.
4. When a rule changes, recode all potentially affected cases.

---

# SECTION 12. LLM Coding Manual

This section instructs an LLM coder (for example Claude, GPT-class, or Gemini-class models). It is deterministic by construction.

## 12.1 Prompt layering (higher layers cannot be overridden by lower layers)

1. Immutable system rules: behavior/evidence/metadata separation, missingness handling, no inference from state.
2. The versioned B0–B13 codebook and its exclusions (`codap_arbor_v4_candidate`).
3. Episode definition and source-provenance rules.
4. Input evidence: frames or video, worksheet excerpt, transcript, validated log window.
5. Non-scored metadata.
6. The JSON output schema.

## 12.2 Reasoning order

1. Verify recording quality and whether the behavior had an opportunity.
2. Identify learner-attributable artifacts and actions.
3. Reconstruct the temporal sequence.
4. Extract semantic claims from worksheet and transcript.
5. Check logs for chronology and numeric values (apply Section 8 tolerance).
6. Apply exclusions before positive criteria.
7. Decide `not_measurable`, `not_observed`, or `observed`.
8. If observed, test Acquire, then Deepen.
9. Assign confidence independently.
10. Return evidence references, not hidden chain-of-thought.

## 12.3 Conflict, missing evidence, and uncertainty

- Direct learner-produced semantic evidence outranks interface-state inference.
- Validated logs outrank uncertain visual timing but never establish cognition.
- Two irreconcilable sources: assign the lower level and emit an `evidence_conflict`.
- Missing required modality or opportunity: `not_measurable`. Assessable but unqualified: `not_observed`.
- Never fabricate hidden content or bridge dropped frames.
- Counts and durations never promote a level.

## 12.4 Determinism and reproducibility controls

- Temperature 0, JSON-schema validation on every output.
- Freeze and record: provider, exact model version, prompt SHA-256, schema version, image or video hashes, preprocessing version, and evidence ordering.
- Run repeated stability tests on a fixed fixture set; store raw output and normalized decision separately.
- Route Low confidence, any `evidence_conflict`, and any behavior below validation thresholds to human review.

## 12.5 Output schema

```json
{
  "rubric_id": "codap_arbor_v4_candidate",
  "schema_version": "4.0",
  "student_id": "canonical_id",
  "session_id": "session_id",
  "episode": {
    "start_ms": 0,
    "end_ms": 0,
    "anchor_event": "emit_tree_data",
    "opportunity": true,
    "modalities_available": ["video", "worksheet", "transcript", "log"]
  },
  "behaviors": {
    "B6": {
      "decision": "observed",
      "level": "Deepen",
      "confidence": "high",
      "criteria_met": ["B6-A1", "B6-A2", "B6-D1", "B6-D2"],
      "evidence": [
        {
          "source": "transcript",
          "ref": "utt_0142",
          "start_ms": 61000,
          "end_ms": 67000,
          "observation": "Compared 11.6 and 12.0; 11.6 misclassifies fewer heavy items."
        }
      ],
      "exclusions_checked": ["threshold_visible_only", "random_change"],
      "uncertainty_reason": null
    }
  },
  "evidence_conflicts": [],
  "process_metadata_ref": "session_metadata.json",
  "model_provenance": {
    "provider": "provider",
    "model": "exact-version",
    "prompt_sha256": "hash",
    "temperature": 0
  }
}
```

---

# SECTION 13. Inter-rater Reliability Protocol

This protocol is publication-ready in design. The coefficients themselves do not yet exist for B0–B13, which is why the instrument is a candidate (Section 16).

## 13.1 Expert content validation

1. Recruit 8–12 experts spanning decision-tree and statistics education, learning sciences, AI education, educational measurement, MMLA and HCI, and qualitative coding.
2. Rate each behavior for relevance, clarity, observability, and AI-CFT alignment on a four-point scale.
3. Preregister I-CVI >= 0.78 for every behavior and S-CVI/Ave >= 0.90. With 6–8 experts, use the more conservative 0.83 item threshold.
4. Record every revision and dissent. Do not report internal team consensus as CVI.

## 13.2 Coder training and qualification

Follow Section 11.4. Freeze a versioned codebook before production coding.

## 13.3 Pilot and sampling

- Double-code a stratified pilot covering every behavior, each of 0 / Acquire / Deepen, cohorts, transcript conditions (including confirmed-silent sessions), and recording quality.
- Use at least 100 episodes, or enough enriched episodes to secure positive examples for rare behaviors (B11, B13).
- Then double-code at least 20 percent of production sessions, stratified by cohort and modality.
- Keep an untouched validation sample; never tune coder or LLM rules on it.

## 13.4 Agreement measures

- Two coders, ordinal level: weighted Cohen's kappa per behavior.
- Three or more coders, or missing values: ordinal Krippendorff's alpha.
- Also report exact agreement, positive and negative agreement, prevalence, confusion matrices, and bootstrap 95 percent confidence intervals.
- Strict acceptance: per-behavior kappa and alpha >= 0.80. Values below trigger recalibration and repeat testing.
- Do not hide low-prevalence instability inside pooled coefficients.

## 13.5 Human–LLM agreement

- Adjudicated human codes are the reference standard.
- Report per-behavior and per-level precision, recall, F1, exact agreement, the severe 0-to-Deepen error rate, and macro averages.
- Strict acceptance: macro-F1 >= 0.80, with each behavior inspected separately.
- Any below-target behavior remains human-reviewed. Human–LLM agreement never substitutes for human–human reliability.

## 13.6 Adjudication

Follow Section 11.5. Preserve original codes, adjudicate after computing reliability, log every dispute, and recode affected cases when a rule changes.

---

# SECTION 14. Construct Validation

This section states the validation argument and its current evidential status honestly. It uses the standard validity facets.

## 14.1 Construct validity

Each behavior is defined as a cognitive process with propositional content and is separated from the interface trace that evidences it (Sections 1 and 3). The v4 revision removed interface-state triggers, adopted the episode as the unit, and separated `not_measurable` from absence. This substantially improves the construct boundary. Discriminant evidence (that behaviors are empirically separable) is not yet collected.

## 14.2 Content validity

The behavior set covers the full CODAP Arbor decision-tree workflow: data appraisal, exploration, boundary setting, target and predictor framing, class semantics, construction, evaluation, generalization, refinement, cross-representation, comparison, and cost-sensitive judgment. This is strong content coverage. A formal expert CVI study is not yet run (Section 13.1).

## 14.3 Face validity

Behavior names, criteria, exclusions, and evidence sources are intelligible to domain reviewers and map onto recognizable statistics-education and ML-education constructs. This is the strongest facet at present.

## 14.4 Criterion validity

No relation has yet been established between B0–B13 codes and an independent holistic or transfer measure of decision-tree understanding. Criterion validity is currently untested.

## 14.5 Discriminant validity and construct leakage

The framework explicitly guards against construct leakage, where variance in writing quality, brevity, digital fluency, terminology recall, or reflection quality is mistaken for decision-tree understanding. Adversarial leakage cases are specified (strong writing with weak reasoning; weak writing with strong procedure; terminology without transfer; reflection without correct execution). These are design controls; the empirical discriminant study remains to be run.

## 14.6 Why every behavior measures learning rather than software interaction

The uniform mechanism is the exclusion of interface state and the requirement of learner-attributable, construct-relevant evidence inside an episode. The crosswalk below shows each behavior's UNESCO AI-CFT alignment and the fact that no behavior reaches Create from Arbor operation alone.

| Behavior | Acquire | Deepen | Create | Basis |
|---|---|---|---|---|
| B0 | LO3.1.1 | LO3.2.3 (supporting) | N/A | data-grounded application |
| B1 | LO3.1.1 | LO3.2.2 | N/A | visual representation of patterns |
| B2 | LO3.1.1 (supporting) | LO3.2.3 | N/A | candidate boundary exploration |
| B3 | LO3.1.1 | not aligned | N/A | problem scoping and prediction target |
| B4 | not aligned | LO3.2.3 | N/A | evidence-based predictor application |
| B5 | LO3.1.1 | LO3.2.3 (supporting) | N/A | class and error semantics |
| B6 | LO3.1.1 (supporting) | LO3.2.3 | N/A | parameter reasoning |
| B7 | LO3.1.3 | LO3.2.1, LO3.2.3 | N/A | tool operation integrated with construction |
| B8 | not aligned | LO3.2.1, LO3.2.3 | N/A | evidence-based evaluation |
| B9 | LO3.1.1 (supporting) | LO3.2.2, LO3.2.3 | N/A | training/testing and generalization |
| B10 | not aligned | LO3.2.2, LO3.2.3 | N/A | hierarchical conditional problem solving |
| B11 | not aligned | LO3.2.2, LO3.2.3 | N/A | coordination of representations |
| B12 | not aligned | LO3.2.1, LO3.2.3 | N/A | compare-select-apply cycle |
| B13 | not aligned | LO3.2.1, LO3.2.3 | N/A | contextual evaluation of model errors |

**Create ceiling.** None of B0–B13 independently supports LO3.3.1–LO3.3.4. Create requires customization or assembly of an AI tool into a locally relevant solution, systematic testing of a self-created tool, or contribution to a tailored-tool repository. Such evidence, when it exists in later tasks, must be scored under a separate namespaced rubric.

## 14.7 Reference basis for Section 14

- Kane, M. T. (2013). *Journal of Educational Measurement, 50*(1).
- Mislevy, Steinberg, & Almond. Evidence-centered assessment design.
- Yusoff, M. S. B. (2019). ABC of content validation and content validity index calculation. *Education in Medicine Journal, 11*(2).
- Krippendorff, K. Methodological notes on Krippendorff's alpha.
- Frischemeier, Biehler, Podworny, & Budde (2025). Students' constructions of data-based decision trees after an introductory ML unit. *ZDM Mathematics Education.*

---

# SECTION 15. Reviewer #2 Simulation

This section takes the adversarial stance: assume the manuscript is rejected, enumerate every plausible criticism, and state the repair or the honest concession.

## 15.1 Criticisms repaired by the v4 specification

| # | Criticism | Repair in this manual |
|---|---|---|
| 1 | Interface state is scored as cognition | Interface-state triggers removed; behavior/evidence/metadata separation (Sections 1, 3) |
| 2 | The unit of analysis (a frame) cannot show reasoning | Episode is the unit (Sections 1.3, 4.1) |
| 3 | AI-CFT LO3.3 mislabeled as Deepen | Create ceiling stated; exact LO crosswalk (Sections 1.4, 14.6) |
| 4 | Missing modality becomes a zero | `not_measurable` separated from `not_observed` (Sections 6, 11) |
| 5 | Level inflation from any positive trace | All criteria required; Deepen inherits Acquire (Section 2) |
| 6 | Double counting of B2/B6/B11, B7/B10/B12, B8/B13 | Explicit dependency and non-implication rules (Section 2 dependencies; 15.3) |
| 7 | Improved accuracy mistaken for reasoning | Outcome corroborates but never proves (global rule 5) |
| 8 | Preloaded, copied, and teacher-directed states conflated with authorship | Provenance and assistance rules (Sections 2, 11.1) |
| 9 | Ambiguous numeric agreement | Deterministic tolerance rules with worked boundary cases (Section 8) |
| 10 | Transcript inequity across sessions | Modality-availability handling; confirmed-silent sessions documented (Section 6) |
| 11 | Non-deterministic LLM coding | Temperature 0, schema validation, frozen provenance (Section 12) |
| 12 | Namespace collision between CODAP and other tasks | Create-bearing tasks scored under a separate namespaced rubric (Sections 1.4, 14.6) |
| 13 | Ambiguous evidence status of behavioral observation transcripts | Evidence-type table added (Section 3.3): action descriptions treated as validated log evidence; verbatim quoted learner utterances treated as transcript; observer paraphrases of intent are not scored as learner-produced semantic claims |
| 14 | Teacher scaffold counted as learner reasoning | Scaffolded speech rule: teacher utterances never satisfy learner criteria; learner restatements count only when they add specificity beyond the prompt (Section 6) |
| 15 | Fixed CODAP statistical lines (Mean, Median) scored as B2 | Explicit exclusion added to B2: computed lines are not movable values (Section 2, B2 exclusions) |
| 16 | Sessions with no task engagement scored as zero | No-task-engagement rule: all behaviors coded `not_measurable`; opportunity condition governs (Section 4.2, 11.1) |

## 15.2 Criticisms that cannot be repaired by wording (honest concessions)

These require new empirical work and are not claimed as done:

- Expert content validity (I-CVI, S-CVI).
- Human–human inter-rater reliability (kappa, alpha) on independent double coding.
- Human–LLM accuracy on a held-out sample.
- Event-alignment and modality-coverage validation.
- Convergent, discriminant, and criterion validity.
- Transfer across datasets, tasks, interfaces, and cultural contexts.
- Quantified analysis of missing-modality bias.

## 15.3 Anticipated finer objections and answers

- **"B7 and B10 overlap."** B7 is whole-model coherence; B10 is a local, subgroup-targeted child refinement with its own diagnosis criterion. Depth alone never triggers B10.
- **"B8 implies B13."** Explicitly denied. B13 requires class semantics (B5) plus a contextual cost trade-off beyond metric interpretation.
- **"B11 is just B2 plus B6."** Denied. B11 requires intentional transfer with variable and unit identity and Section 8 tolerance, not co-occurrence.
- **"Video is treated as ground truth for reasoning."** Denied. Video is authoritative only for what occurred and its order; reasoning comes from worksheet or transcript (Section 7).

---

# SECTION 16. Publication Readiness Audit

Each criterion is scored 0–10 for the v4 candidate after this documentary refinement. Scores describe the specification, not empirical performance, which does not yet exist.

| Criterion | Score / 10 | Justification |
|---|---:|---|
| Construct validity | 8 | Construct boundaries substantially improved; empirical discriminant evidence absent |
| Content validity | 8 | CODAP decision-tree workflow well covered; 2025-cohort validation added rules for researcher notes, scaffold speech, multiple recordings, no-task sessions, and non-scatter-plot representations; expert CVI not yet collected |
| Face validity | 9 | Names, criteria, exclusions, and evidence sources are intelligible to domain reviewers |
| Coding reliability | 4 | A rigorous protocol exists; no coefficients exist yet |
| LLM readiness | 8 | Deterministic rules, tolerance, and schema are strong; held-out human–LLM validation absent |
| Replicability | 7 | Codebook and provenance are versioned; runtime prompt and schema drift must be repaired and regression-tested |
| AI-CFT alignment | 8 | Exact LO crosswalk with a defensible Create ceiling |
| Learning-sciences grounding | 8 | Coherent grounding in statistics education, representational fluency, ECD, and self-regulated learning |
| Educational-measurement quality | 6 | Strong argument-based design; criterion and discriminant evidence not yet gathered |
| Publication quality (as a coding manual) | 8 | Operationally usable after exemplars and training; episode coding raises effort |

## 16.1 Overall verdict

**Moderate Revision.**

The manual is suitable for expert content review and pilot double coding. It is not yet suitable for a top-tier paper that claims a validated instrument, because the reliability and criterion facets depend on data that do not yet exist. No further behavior proliferation is recommended; the remaining work is empirical, not another redesign of the behavior set.

## 16.2 Path to "Ready"

1. Repair runtime scorer, schema, and prompt drift; add regression tests.
2. Establish event-alignment and modality-coverage thresholds.
3. Run the expert CVI study (Section 13.1).
4. Conduct stratified independent double coding and compute per-behavior kappa and alpha (Section 13.4).
5. Validate LLM coding on the untouched sample and report macro-F1 with per-behavior breakdown (Section 13.5).
6. Test convergent, discriminant, and transfer validity, and quantify missing-modality bias.

When facets 3 through 6 meet their preregistered thresholds, the audit is re-run and the verdict is revisited.

---

## Appendix A. Document control

| Field | Value |
|---|---|
| Operational source of record | `calibration/codap_rubric_v4_candidate.json` |
| Companion analysis | `framework/CODAP_AI_CFT_RUBRIC_V4_FINAL_REFINEMENT.md` |
| Construct definition | `framework/Construct_Definition.md` |
| Assessment argument | `framework/Assessment_Argument.md` |
| Audio-availability record | `calibration/audio_limitations.json` |
| Version | 4.0-candidate |
| Change control | Any change to a criterion, exclusion, or tolerance triggers an impact review and recoding of affected cases (Section 11.4). |

