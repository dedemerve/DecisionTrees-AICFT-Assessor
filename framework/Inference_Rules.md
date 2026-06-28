# Inference Rules

## Artifact role (normative)

This document is the **law book** of the inference system.

It answers:

> Which inferential moves are **admissible** or **prohibited**?

It does **not** answer:

> How should a specific case be scored step-by-step?

Operational recipes live in `Inference_Patterns.md`.

| Artifact | Responsibility | Analogy |
|----------|----------------|---------|
| `Construct_Definition.md` | What is measured | Constitution preamble |
| `Inference_Rules.md` | What moves are allowed | Statute law |
| `Inference_Patterns.md` | How to apply the law | Case procedures / templates |
| Mapping & policy JSON | Case records | Court filings |

A reviewer should be able to read **only this file** and know what the system must never do.

---

## Scope

These rules govern all transitions in the inferential chain:

```
Evidence Unit → Observable Behaviour → Learning Object → Domain Understanding
  → AI-CFT Competency Claim → Researcher Validation → Scientific Claim
```

---

## Statutory rules

### Layer integrity

**R1.** No layer may be bypassed.

- Prohibited: worksheet item → AI-CFT; evidence unit → Learning Object without behaviour; behaviour → AI-CFT without LO and Domain synthesis.

**R2.** Evidence cannot directly support AI-CFT competency claims.

**R3.** Upper-layer confidence cannot exceed lower-layer confidence without documented justification.

### Traceability

**R4.** Every higher-layer claim must be recoverable from lower-layer units, reasoning, and uncertainty.

**R5.** Convenience is not admissibility. Prefer narrower defensible claims over broader weak ones.

### Contradiction & competition

**R6.** Contradictions must be preserved, not averaged away.

**R7.** Contradiction may reduce confidence, block escalation, or trigger mandatory review. It must not be silently discarded.

**R8.** Competing hypotheses must be represented when multiple higher-layer interpretations remain plausible.

**R9.** Premature resolution of competition for interface simplicity is prohibited.

### Negative & null evidence

**R10.** Missing evidence is not negative evidence.

- Absence of data ≠ evidence of absence.
- Missing evidence may still block escalation when required by the target claim.

**R11.** Negative inference requires **affirmative counter-evidence**, not mere lack of support.

**R12.** Null inference means no admissible claim; it implies neither support nor penalty.

### Non-compensation & leakage

**R13.** Weak lower-layer evidence cannot be compensated by eloquent higher-layer wording.

- Reflection cannot override absent procedural evidence when procedure is central.
- Interaction volume cannot override absent interpretable reasoning when reasoning is central.

**R14.** Source affordances cap admissible claims.

- Logs: strong for action sequence, limited for reasoning.
- Reflections: strong for articulated belief, limited for execution.
- Worksheets: strong for explicit explanation, limited for unseen tool behaviour.

**R15.** Alternative explanations must be inspected before escalation.

Plausible alternatives include: guessing, copying, superficial fluency, procedural imitation, OCR error, exploratory interaction without understanding.

### Sufficiency (normative grammar)

All operational artifacts must express sufficiency using these fields:

| Field | Meaning |
|-------|---------|
| `minimum_evidence_sources` | Source families minimally required |
| `minimum_independent_observations` | Non-duplicate observations required |
| `required_diversity` | Cross-task / cross-modality requirement |
| `allowed_contradictions` | Tolerable contradiction level |
| `confidence_threshold` | Minimum lower-layer confidence pattern |
| `review_trigger` | Condition forcing human review |

**R16.** Higher layers require narrower ambiguity and stronger coordination than lower layers.

- One evidence unit may support one behaviour (tentatively).
- One behaviour may support one LO (tentatively).
- One LO is rarely sufficient for broad Domain Understanding.
- One domain indicator is rarely sufficient for AI-CFT interpretation.

### Inference types (classification only)

Rules classify *kinds* of moves; patterns instantiate them.

| Transition | Primary inference type |
|------------|------------------------|
| Evidence → Behaviour | Deductive |
| Behaviour → LO | Inductive |
| LO → Domain | Abductive |
| Domain → AI-CFT | Interpretive |
| AI-CFT → Researcher | Validation handoff (not autonomous inference) |

**R17.** Deductive moves require minimal interpretive expansion. Abductive and interpretive moves require broader coordination and lower default confidence.

### AI-CFT & researcher boundary

**R18.** AI-CFT outputs are provisional until researcher validation.

**R19.** Auto-confirmation, hidden ranking, and suppression of contradictory evidence for UI simplicity are prohibited.

**R20.** Population-level scientific claims require researcher-validated case evidence and must not exceed sample scope.

---

## Prohibited shortcuts (explicit)

| Shortcut | Status |
|----------|--------|
| Worksheet → AI-CFT | **Forbidden** |
| Item score → competency claim | **Forbidden** |
| Evidence unit → Domain Understanding | **Forbidden** |
| Behaviour frequency → deep understanding | **Forbidden** |
| Fluent writing → DT understanding | **Forbidden** (construct leakage) |
| CODAP click count → strategic reasoning | **Forbidden** |
| Terminology recall → procedural mastery | **Forbidden** |
| Reflection quality → execution competence (without corroboration) | **Forbidden** |
| Procedural success → conceptual mastery (when explanation is required) | **Forbidden** |
| LO → AI-CFT without Domain synthesis | **Forbidden** |
| Create-level AI-CFT from sparse adaptation evidence | **Forbidden** |

---

## Confidence propagation laws

**C1.** Confidence is propagated, not reinvented at each layer.

**C2.** Unresolved lower-layer ambiguity caps higher-layer confidence.

**C3.** Contradiction reduces confidence and may block escalation.

**C4.** Source limitations cap confidence regardless of wording quality.

---

## Relationship to other artifacts

- `Construct_Definition.md` — defines the target construct these rules protect.
- `Inference_Patterns.md` — operational templates that must comply with every rule above.
- `Framework_Verification_Plan.md` Test 11 — construct leakage cases test compliance with R13–R15.
- Ontology / mapping JSON — must cite applicable patterns and must not violate prohibited shortcuts.

---

## Reviewer gate

Before accepting any mapping or policy change, ask:

1. Which rule(s) does this instantiate?
2. Which pattern template is used?
3. What alternative explanation remains plausible?
4. What counter-evidence blocks escalation?
5. Does this violate any prohibited shortcut?
6. Is confidence bounded by lower layers?

---

## Status

**Normative core — stable subject to adversarial verification.**

Operational transition detail belongs in `Inference_Patterns.md`, not here. If a proposed change adds step-by-step procedure to this file, it belongs in Patterns instead.
