# Explainable AI Competency Assessment Architecture

## Purpose

This repository should be redesigned as a reusable Evidence-Centered Design (ECD) assessment framework for pre-service teachers learning Decision Trees. It should not be treated as a worksheet scorer with appended competency labels.

The defensible interpretive chain is:

`Raw Evidence -> Evidence Units -> Observable Behaviours -> Learning Objects -> Domain Understanding -> AI-CFT Competency Claims -> Researcher Validation`

This ordering is not cosmetic. It is necessary for:

- construct validity
- traceability
- explainability
- multimodal evidence integration
- reusability across tasks and cohorts

## Architectural Position

AI-CFT is the final interpretive framework, not the primary assessment model.

The primary assessment model is domain-specific Decision Tree understanding, inferred from observable behaviours grounded in evidence. UNESCO AI-CFT should only be used after domain understanding has been assembled and reviewed.

The target construct itself is defined separately in `Construct_Definition.md` so that the framework can distinguish decision-tree understanding from non-target constructs such as general writing quality or digital fluency.

## Why A Redesign Is Necessary

The legacy repository pattern remains too close to:

`worksheet item -> score -> AI-CFT interpretation`

That pattern is methodologically weak because it:

- collapses evidence and interpretation into the same artifact
- over-privileges worksheets relative to other sources
- obscures the reasoning chain required by ECD
- encourages direct mapping from task performance to competency labels
- makes later multimodal expansion harder

## Terminology

### Learning Object

An instructional concept or skill intentionally targeted by an item or task.

Examples:

- object
- feature
- label
- threshold
- rule
- decision tree
- overfitting
- sensitivity
- misclassification rate

Learning Objects are not competencies.

### Observable Behaviour

An observable learner action, explanation, reasoning process, decision, revision, or reflection extracted from evidence.

Examples:

- defines object
- distinguishes feature from label
- applies threshold
- compares thresholds
- justifies threshold selection
- explains overfitting
- revises decision tree
- evaluates model performance

Observable Behaviours are not worksheet-specific whenever a more reusable formulation is possible.

### Domain Understanding

A broader interpretation of Decision Tree understanding inferred from accumulated Learning Object evidence and behavioural patterns.

Examples:

- basic AI techniques and applications (LO3.1 — Acquire)
- application skills (LO3.2 — Deepen)
- threshold reasoning
- classification reasoning
- tree construction
- model evaluation
- generalisation
- evidence-based decision making

### AI-CFT Competency Claim

A higher-level interpretation derived from accumulated domain understanding and reviewed by a researcher.

## ECD Assessment Argument

All interpretive logic should follow:

`Claim -> Evidence -> Reasoning -> Interpretation`

### Claim

The learner demonstrates a particular level of Decision Tree understanding or an AI-CFT-relevant capability.

### Evidence

Observable evidence is extracted from multiple sources:

- worksheets
- CODAP logs
- screen recordings
- reflections
- observations
- interviews

### Reasoning

Evidence units support observable behaviours.
Observable behaviours support Learning Objects.
Learning Objects support Domain Understanding.
Domain Understanding supports provisional AI-CFT claims.

### Interpretation

Researchers review the assembled case and make the final judgement.

## Layered Architecture

### Layer 1. Raw Evidence

Responsibility:

- store source-native assessment artifacts only

Examples:

- worksheet scan or OCR text
- CODAP interaction log
- screen recording file or transcript
- reflection text
- observation note
- interview transcript

Must not include:

- behavioural coding
- Learning Object inference
- competency interpretations

### Layer 2. Evidence Units

Responsibility:

- transform source-native evidence into atomic, traceable units

Each evidence unit must include:

- source
- timestamp or item reference
- location
- content
- confidence
- provenance
- uncertainty
- alternative interpretations

Examples:

- a response span for `WS4_Q3`
- a CODAP threshold-change event
- a video segment showing revision after hesitation
- a reflection paragraph explaining why a tree is imperfect

Must not include:

- AI-CFT labels
- final understanding claims

### Layer 3. Observable Behaviour Ontology

Responsibility:

- define reusable learner behaviours independent of any single worksheet

Each behaviour should include:

- id
- title
- description
- cognitive_process
- knowledge_type
- possible_sources
- difficulty
- expected_evidence
- possible_misconceptions
- related_behaviours
- evidence_strength_ceiling
- confidence_requirements

Design principle:

- behaviours describe what the learner did, not where they did it

### Layer 4. Learning Objects

Responsibility:

- represent the instructional concepts intentionally targeted in tasks

Learning Objects serve as a bridge between observed behaviour and disciplinary meaning.

Examples:

- object
- feature
- label
- dataset
- threshold
- rule
- decision tree
- overfitting
- sensitivity
- misclassification rate

Design principle:

- a behaviour may support zero, one, or several Learning Objects

### Layer 5. Domain Understanding

Responsibility:

- synthesize Learning Object evidence into broader Decision Tree understanding

Domain Understanding dimensions should capture disciplinary coherence, not isolated item correctness.

Examples:

- foundational terminology
- classification reasoning
- threshold optimisation
- tree construction
- model evaluation
- generalisation
- critical interpretation
- evidence-based decision making

Design principle:

- domain understanding is the primary assessment interpretation layer

### Layer 6. AI-CFT Interpretation

Responsibility:

- interpret accumulated domain understanding through UNESCO AI-CFT

Design principle:

- no worksheet or single behaviour directly determines AI-CFT level
- AI-CFT remains provisional until researcher confirmation

### Layer 7. Researcher Validation

Responsibility:

- support final human judgement with full traceability

Researchers should review:

- supporting evidence
- contradictory evidence
- confidence
- uncertainty
- provenance
- rationale

Design principle:

- the system proposes; the researcher decides

## Separation Of Responsibilities

Every artifact must have one responsibility only.

### Framework artifacts

- ontology definitions
- mappings
- aggregation rules
- confidence rules
- validation rules
- assessment argument
- researcher review protocol
- versioning policy
- dependency graph
- architecture change log

### Worksheet artifacts

- rubric
- behaviour opportunities
- local Learning Object targets
- extraction schema
- validity notes

### Evidence artifacts

- extracted evidence units from one source instance
- no final interpretations

### Portfolio artifacts

- cumulative learner evidence
- traceability
- provisional interpretations
- review queue

### Validation artifacts

- researcher decisions and justifications

## Inference artifact responsibilities

| Artifact | Role | Reviewer question |
|----------|------|-------------------|
| `Construct_Definition.md` | Ontological definition of Decision Tree Understanding | What is measured? |
| `Inference_Rules.md` | Normative laws (admissible vs prohibited moves) | What must never happen? |
| `Inference_Patterns.md` | Operational templates (`pattern_id`, inputs, logic, review triggers) | How is each move executed? |

Mappings and policies must cite patterns; patterns must comply with rules; rules protect the construct defined above.

## Required Repository Structure

```text
framework/
  ARCHITECTURE.md
  Observable_Behaviours.json
  Learning_Objects.json
  Behaviour_to_ILO.json
  Domain_Understanding.json
  LO_to_Domain_Understanding.json
  Domain_to_AI_CFT.json
  AICFT_Aspect3_Reference.json
  Misconception_Ontology.json
  Evidence_Types.json
  Evidence_Strength.json
  Confidence_Model.json
  Aggregation_Policy.json
  Validation_Policy.json
  Assessment_Argument.md
  Construct_Definition.md
  Inference_Rules.md
  Inference_Patterns.md
  Researcher_Review_Protocol.md
  Versioning_Policy.md
  Artifact_Dependency_Graph.md
  CHANGELOG.md

worksheets/
  WS1/
    rubric.json
    behaviour_opportunities.json
    learning_objects.json
    extraction_schema.json
    validity_notes.json
  ...

evidence/
  worksheet/
  codap/
  screen_recording/
  reflection/
  observation/

portfolio/
  portfolio_builder.py
  research_dashboard.py
```

## Claim Structure And Information Flow

### A. Source processing

1. ingest source artifact
2. create source manifest
3. extract evidence units
4. attach provenance and confidence

### B. Behavioural interpretation

1. identify candidate observable behaviours
2. code evidence strength
3. record alternative interpretations
4. preserve source trace links

### C. Instructional interpretation

1. map behaviours to Learning Objects
2. determine whether LO evidence is weak, partial, consistent, or conflicting

### D. Domain interpretation

1. aggregate Learning Object patterns into Domain Understanding
2. identify coherence, transfer, and limitations

### E. Competency interpretation

1. interpret Domain Understanding through AI-CFT
2. generate a provisional competency claim
3. attach rationale, uncertainty, and gaps

### F. Human validation

1. researcher reviews the full evidence trail
2. researcher confirms, revises, or rejects the recommendation
3. researcher records final justification

## Evidence Strength

Evidence strength should express support for an interpretive claim, not task difficulty.

Recommended levels:

- `weak`
- `moderate`
- `strong`
- `very_strong`

Strength should depend on:

- directness
- clarity
- completeness
- consistency
- source appropriateness

Important warning:

- a hard task is not necessarily strong evidence
- a correct answer without reasoning may be weaker than a justified explanation

## Confidence

Confidence should be modeled across layers rather than overwritten.

Recommended confidence inputs:

- extraction confidence
- interpretation confidence
- corroboration across sources
- contradiction penalty
- source sufficiency
- ambiguity level

Design principle:

- keep numeric confidence internally
- present categorized confidence to researchers
- never collapse confidence into achievement status

## Traceability Requirements

Every provisional recommendation must be traceable to source evidence.

Minimum traceability targets:

- worksheet item
- OCR span or region
- CODAP event and timestamp
- screen recording timestamp interval
- reflection paragraph
- observation note
- interview turn

## Validity And Reliability Safeguards

### Construct validity

- no direct worksheet-to-competency mapping
- behaviours and Learning Objects are distinct constructs
- Domain Understanding is the primary interpretation layer
- evidence never directly supports competencies; it supports behaviours first

### Content validity

- multiple evidence sources sample the construct more broadly than worksheets alone
- worksheets are treated as opportunity structures, not the whole construct
- converging evidence is required for broader interpretive claims where appropriate

### Reliability

- source-specific extraction schemas
- explicit coding rules
- calibration examples
- reviewer flags for ambiguous evidence
- versioned artifacts and recorded decision rationales

### Explainability

- every mapping layer is explicit
- every recommendation includes rationale and traceability

### Reusability

- behaviours are source-agnostic where possible
- Learning Objects are instructional targets reusable across tasks

## Major Validity Threats To Guard Against

- OCR error mistaken for conceptual misunderstanding
- fluent explanation mistaken for procedural competence
- repeated CODAP actions mistaken for strategic reasoning
- activity completion mistaken for understanding
- reflection sophistication mistaken for model evaluation skill
- sparse evidence over-interpreted as AI-CFT competency

## Governance Requirements

To be scientifically reusable, the framework must also maintain:

- a formal researcher review protocol
- a versioning policy for ontologies, mappings, rubrics, and policies
- a dependency graph showing which artifacts depend on which others
- a change log documenting architectural decisions and their rationale

## Final Architectural Decision

The scientifically stronger architecture is:

`Raw Evidence -> Evidence Units -> Observable Behaviours -> Learning Objects -> Domain Understanding -> AI-CFT Competency Claims -> Researcher Validation`

This design is superior to direct worksheet scoring because it is more defensible, more traceable, more scalable, and better aligned with both ECD and UNESCO AI-CFT.
