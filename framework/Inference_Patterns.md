# Inference Patterns

## Artifact role (operational)

This document is the **recipe library** of the inference system.

It answers:

> Given admissible evidence, **how** should inference be executed?

Normative constraints live in `Inference_Rules.md`. This file must not invent new laws — only instantiate them.

| Artifact | Role |
|----------|------|
| `Inference_Rules.md` | Kanun — what is allowed |
| `Inference_Patterns.md` | Uygulama reçetesi — how to apply |

Every ontology entry, mapping record, aggregation policy, and portfolio rule should reference at least one `pattern_id` from this document.

---

## Standard pattern template

All patterns use this structure:

```yaml
pattern_id: string          # e.g. PAT-POS-001
purpose: string             # what inferential job this performs
applicable_transition: list # e.g. [Evidence → Behaviour]
required_inputs: list
preconditions: list         # must hold before pattern runs
inference_logic: string     # step-by-step application
alternative_explanations: list
counter_evidence: list
confidence_adjustment: string
outputs: list               # what the pattern produces
escalation_rule: string     # when promotion to next layer is allowed
review_trigger: list
prohibited_uses: list
governing_rules: list       # Inference_Rules IDs (R1, R2, …)
example: object             # Decision Tree domain instance
```

---

## Core patterns

### PAT-POS-001 — Positive Inference

```yaml
pattern_id: PAT-POS-001
purpose: Affirmatively support a higher-layer claim from interpretable lower-layer evidence
applicable_transition:
  - Evidence → Behaviour
  - Behaviour → LO
  - LO → Domain
  - Domain → AI-CFT (provisional)
required_inputs:
  - interpretable lower-layer unit(s)
  - explicit theoretical link in mapping artifact
  - no unresolved blocking contradiction
preconditions:
  - source legibility above review threshold
  - behaviour/LO wording matches construct dimensions (Construct_Definition.md)
inference_logic: |
  1. Verify input maps to a single primary interpretation.
  2. Check alternative explanations; none must be equally likely.
  3. Apply strength ceiling from mapping prior.
  4. Emit support record with rationale referencing learner text/action.
  5. Escalate only if sufficiency fields met for target transition.
alternative_explanations:
  - guessing
  - copied phrase
  - vocabulary without understanding
counter_evidence:
  - contradictory unit at same layer
  - misconception indicator in adjacent LO
confidence_adjustment: min(lower_layer_confidence, mapping_ceiling)
outputs:
  - support record (strength, rationale, evidence_type)
escalation_rule: permitted when minimum_independent_observations met and review_trigger false
review_trigger:
  - competing hypotheses remain
  - borderline sufficiency
  - construct leakage risk (Test 11 Pattern A)
prohibited_uses:
  - treating positive support as proof of mastery
governing_rules: [R1, R2, R3, R4, R16]
example:
  worksheet: WS4
  item: WS4_B5
  evidence: "Pia doğru çünkü en düşük MCR'yi veriyor"
  behaviour: Justifies threshold selection with performance evidence
  lo: LO3.2.2
  strength: strong
  rationale: Student links peer answer to MCR criterion — strategic threshold evaluation
```

---

### PAT-NEG-001 — Negative Inference

```yaml
pattern_id: PAT-NEG-001
purpose: Affirmatively weigh against a candidate claim
applicable_transition: all
required_inputs:
  - explicit counter-evidence (not absence)
  - interpretable basis for negative conclusion
preconditions:
  - counter-evidence is construct-relevant
inference_logic: |
  1. Confirm counter-evidence is affirmative (misconception stated, wrong execution documented).
  2. Link counter-evidence to specific behaviour/LO/domain claim.
  3. Reduce strength or block escalation; do not infer unrelated deficits.
alternative_explanations:
  - OCR misread mistaken for misconception
counter_evidence: []  # this pattern IS counter-evidence production
confidence_adjustment: moderate-high when counter-evidence is explicit
outputs:
  - negative weight on target claim OR blocked escalation flag
escalation_rule: blocks escalation to affected dimension
review_trigger:
  - negative inference would flip a portfolio-level proposal
prohibited_uses:
  - treating missing data as negative (violates R10)
governing_rules: [R11, R12]
example:
  item: WS7_P1_box2
  evidence: student assigns wrong class label to tree path despite correct reading
  effect: weighs against Applies decision rules correctly
```

---

### PAT-NULL-001 — Null Inference

```yaml
pattern_id: PAT-NULL-001
purpose: Record that no admissible inference can be drawn
applicable_transition: all
required_inputs:
  - missing, illegible, or non-diagnostic evidence
preconditions:
  - extraction confirms blank or uninterpretable content
inference_logic: |
  1. Set strength = none, evidence_present = false.
  2. Do not apply negative inference.
  3. Keep case open for other units/sources.
confidence_adjustment: 0.0 for target claim
outputs:
  - null record; optional data_gap entry
escalation_rule: blocks escalation that requires this input
review_trigger:
  - null blocks a required construct dimension
prohibited_uses:
  - converting null into failure or negative judgement
governing_rules: [R10, R12]
example:
  item: WS11_Q11_3
  evidence: "(bos)"
  effect: no LO3.1.2 procedural workflow evidence from this item
```

---

### PAT-CONTRA-001 — Contradictory Inference

```yaml
pattern_id: PAT-CONTRA-001
purpose: Preserve tension across sources without averaging
applicable_transition:
  - LO → Domain
  - Domain → AI-CFT
required_inputs:
  - at least one supporting and one contradictory signal, both traceable
preconditions:
  - signals refer to same construct dimension
inference_logic: |
  1. Record both signals with sources.
  2. Lower confidence on affected dimension.
  3. Block strong escalation until resolved or reviewer adjudicates.
alternative_explanations:
  - performance varies by task format
confidence_adjustment: reduce 0.15–0.40 depending on severity
outputs:
  - dual-record with contradiction flag
escalation_rule: strong escalation blocked
review_trigger: mandatory
prohibited_uses:
  - averaging scores across contradictory signals
governing_rules: [R6, R7, C3]
example:
  support: WS1 defines sensitivity correctly (conceptual)
  contradict: WS4 applies wrong threshold with confident justification
  effect: Conceptual strong, Strategic moderate at most; Threshold Reasoning blocked
```

---

### PAT-WEAK-001 — Weak Inference

```yaml
pattern_id: PAT-WEAK-001
purpose: Tentative support under acknowledged limitations
applicable_transition: all
required_inputs:
  - one interpretable signal with narrow or ambiguous scope
preconditions:
  - mapping allows weak/supporting evidence_type
inference_logic: |
  1. Assign weak or moderate strength within ceiling.
  2. Document limitation in rationale.
  3. Do not use as sole basis for broad domain or AI-CFT claims.
confidence_adjustment: cap at 0.72
outputs:
  - supporting competency record
escalation_rule: cannot alone trigger Domain or AI-CFT escalation
review_trigger:
  - downstream artifact treats weak as strong
prohibited_uses:
  - portfolio peak from baseline/diagnostic items
governing_rules: [R16, R19]
example:
  item: DT_A_Q1
  evidence: prior belief naming şeker/yağ
  lo: LO3.1.1
  strength: weak
  portfolio_weight: baseline  # excluded from peak aggregation
```

---

### PAT-MULTI-001 — Multi-Source Inference

```yaml
pattern_id: PAT-MULTI-001
purpose: Convergent support across independent source families
applicable_transition:
  - Behaviour → LO
  - LO → Domain
  - Domain → AI-CFT
required_inputs:
  - ≥2 source families (worksheet, CODAP log, reflection, …)
  - interpretable convergence on same construct dimension
preconditions:
  - sources are independent, not duplicate encodings of same event
inference_logic: |
  1. Align evidence by construct dimension, not worksheet label.
  2. Verify convergence is conceptual/procedural, not lexical repetition.
  3. Raise confidence within lower-layer bound only.
alternative_explanations:
  - same answer copied across sections
counter_evidence:
  - divergence on same dimension across sources
confidence_adjustment: +0.05 to +0.15 vs single-source, never above ceiling
outputs:
  - strengthened domain or LO record with source list
escalation_rule: permitted for Domain → AI-CFT when diversity requirement met
review_trigger:
  - one family dominates numerically but not qualitatively
prohibited_uses:
  - double-counting one event in worksheet + log
governing_rules: [R14, R16, C1]
example:
  sources:
    - WS6 tree_structure (worksheet)
    - DT_D_Q2 two-level tree (WS_DT)
  dimension: Procedural + Strategic
  effect: supports Tree Construction domain dimension
```

---

### PAT-TRANSFER-001 — Transfer Inference

```yaml
pattern_id: PAT-TRANSFER-001
purpose: Related reasoning across tasks or contexts
applicable_transition:
  - LO → Domain
  - Domain → AI-CFT
required_inputs:
  - evidence from ≥2 contexts showing related reasoning pattern
preconditions:
  - construct dimension explicitly requires transfer (Strategic, Generalisation)
inference_logic: |
  1. Identify shared reasoning pattern (not shared vocabulary).
  2. Confirm tasks differ in format or context.
  3. Assign conservative strength; flag if only one format observed.
alternative_explanations:
  - memorized template applied mechanically
counter_evidence:
  - failure on structurally similar novel item
confidence_adjustment: conservative; max moderate without third context
outputs:
  - transfer-tagged domain support
escalation_rule: required for Generalisation claims
review_trigger: always for AI-CFT Create-level hints
prohibited_uses:
  - transfer from repeated performance in one worksheet type only
governing_rules: [R16, R20]
example:
  contexts: [WS3 threshold apply, WS4 optimize, WS10 table]
  dimension: Threshold Reasoning
  effect: supports Strategic Understanding across tasks
```

---

### PAT-COMPETE-001 — Competing Hypothesis Inference

```yaml
pattern_id: PAT-COMPETE-001
purpose: Preserve multiple plausible higher-layer interpretations
applicable_transition: all
required_inputs:
  - ≥2 defensible candidate interpretations
preconditions:
  - competition is not arbitrary; each has mapping-level plausibility
inference_logic: |
  1. List primary and secondary hypotheses with strengths.
  2. Reduce confidence on all until disambiguated.
  3. Block escalation if outcomes diverge materially.
alternative_explanations: []  # hypotheses ARE the alternatives
confidence_adjustment: multiply by 0.7–0.85
outputs:
  - ordered hypothesis list
escalation_rule: blocked until resolved or reviewer selects
review_trigger: mandatory
prohibited_uses:
  - forcing single LO when mapping allows equally weighted alternatives
governing_rules: [R8, R9]
example:
  behaviour: correct classification, no explanation
  compete:
    - Applies threshold (procedural)
    - Guessed class label (non-DT)
  resolution: prefer procedural only if repeated; else review
```

---

### PAT-BLOCK-001 — Escalation Block

```yaml
pattern_id: PAT-BLOCK-001
purpose: Halt promotion when insufficiency, contradiction, or leakage detected
applicable_transition: all
required_inputs:
  - partial support + documented block reason
preconditions:
  - block reason maps to R6–R15 or Test 11 pattern
inference_logic: |
  1. Record support at current layer.
  2. Set escalation_blocked = true with reason code.
  3. Surface in data_gaps or review queue.
confidence_adjustment: cap at triggering layer
outputs:
  - blocked escalation metadata
escalation_rule: none until block cleared
review_trigger: automatic
prohibited_uses:
  - silent escalation past block
governing_rules: [R6, R10, R13, R18]
example:
  trigger: Test 11 Pattern D — excellent reflection, incorrect thresholds
  block: Threshold Reasoning domain dimension
  allow: Reflective Understanding at weak only
```

---

## Transition application patterns

These bundle core patterns for each architectural transition.

### PAT-TRANS-E2B — Evidence → Observable Behaviour

```yaml
pattern_id: PAT-TRANS-E2B
governing_rules: [R1, R4, R14]
primary_patterns: [PAT-POS-001, PAT-NULL-001, PAT-COMPETE-001]
inference_logic: |
  Map raw unit to behaviour verb phrase describing what learner DID/SAID.
  Reject behaviours that describe task demand, not learner action.
sufficiency_defaults:
  minimum_evidence_sources: 1
  minimum_independent_observations: 1
  review_trigger: ambiguity between ≥2 behaviours
example:
  unit: "CODAP movable line at şeker=10 with comment on group separation"
  behaviour: Compares class separation across threshold values
```

### PAT-TRANS-B2LO — Behaviour → Learning Object

```yaml
pattern_id: PAT-TRANS-B2LO
governing_rules: [R16, R17]
primary_patterns: [PAT-POS-001, PAT-WEAK-001, PAT-NEG-001]
inference_logic: |
  Use mapping prior for admissible LOs only.
  Strength cannot exceed mapping ceiling even at full rubric credit.
example:
  behaviour: Orders DT workflow steps correctly (WS11 Q11)
  lo: LO3.1.2
  strength: moderate
  note: not LO3.1.1 — procedural workflow, not vocabulary
```

### PAT-TRANS-LO2D — Learning Object → Domain Understanding

```yaml
pattern_id: PAT-TRANS-LO2D
governing_rules: [R16, R17]
primary_patterns: [PAT-MULTI-001, PAT-TRANSFER-001, PAT-CONTRA-001]
inference_logic: |
  Synthesize LO profile into construct dimension (Conceptual/Procedural/Strategic/Reflective).
  Require ≥2 LOs or multi-source for broad dimensions.
example:
  los: [LO3.2.2 strong across WS3, WS4, WS10]
  domain: Threshold Reasoning (Strategic)
```

### PAT-TRANS-D2A — Domain → AI-CFT (provisional)

```yaml
pattern_id: PAT-TRANS-D2A
governing_rules: [R2, R18, R20]
primary_patterns: [PAT-MULTI-001, PAT-BLOCK-001]
inference_logic: |
  Map domain profile to Acquire/Deepen/Create proposal.
  Never emit is_final = true.
example:
  domain_profile: Conceptual+Strategic strong, Create none
  proposal: Aspect 3 Deepen (provisional)
```

---

## Pattern selection guide

| Situation | Use pattern |
|-----------|-------------|
| Clear supportive evidence | PAT-POS-001 |
| Explicit misconception / wrong execution | PAT-NEG-001 |
| Blank / illegible | PAT-NULL-001 |
| Worksheet vs log disagree | PAT-CONTRA-001 |
| Prior belief / diagnostic item | PAT-WEAK-001 + baseline weight |
| WS + CODAP + DT agree | PAT-MULTI-001 |
| Same skill, different worksheets | PAT-TRANSFER-001 |
| Two LOs equally plausible | PAT-COMPETE-001 |
| Leakage or insufficiency | PAT-BLOCK-001 |

---

## Status

Template library for ontology and mapping instantiation.

Revise only when `Inference_Rules.md` changes (new statute) or adversarial cases expose a missing pattern type.
