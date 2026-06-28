# Artifact Dependency Graph

## Purpose

This graph records which artifacts depend on which others so that redesign remains internally consistent.

## Core Dependency Chain

1. `ARCHITECTURE.md`
2. `Assessment_Argument.md`
3. `Construct_Definition.md`
4. `Inference_Rules.md`
5. `Inference_Patterns.md`
6. `Evidence_Types.json`
7. `Evidence_Strength.json`
8. `Confidence_Model.json`
9. `Observable_Behaviours.json`
10. `Misconception_Ontology.json`
11. `Learning_Objects.json`
12. `Behaviour_to_ILO.json`
13. `Domain_Understanding.json`
14. `LO_to_Domain_Understanding.json`
15. `Domain_to_AI_CFT.json`
16. `Aggregation_Policy.json`
17. `Validation_Policy.json`
18. `Researcher_Review_Protocol.md`
19. worksheet-level artifacts
20. portfolio and dashboard artifacts

## Dependency Notes

### Architecture dependencies

- all framework artifacts depend on `ARCHITECTURE.md`

### Assessment argument dependencies

- all interpretive mappings and policies must remain consistent with `Assessment_Argument.md`

### Construct definition dependencies

- all ontology and mapping artifacts must remain consistent with `Construct_Definition.md`
- construct leakage verification should be grounded in `Construct_Definition.md`

### Behaviour ontology dependencies

- `Observable_Behaviours.json` v1.0 is **frozen** (see `reports/milestone1_freeze/milestone1_freeze_report.md`)
- `Behaviour_Dependency_Graph.json` documents requires/supports/related edges among frozen behaviours
- `Learning_Objects.json` v1.0 (ILO) is **frozen** (see `reports/milestone2_freeze/milestone2_freeze_report.md`)
- `ILO_Dependency_Graph.json` documents instructional sequence and prerequisite edges
- `Behaviour_to_ILO.json` (Milestone 3) maps frozen `OB_*` → `ILO_*` with traceable rationale

### Inference rule dependencies (normative)

- `Inference_Rules.md` is the statute: admissible moves, prohibitions, confidence laws
- all ontology and mapping artifacts must comply; they must not restate operational recipes here
- `Aggregation_Policy.json` depends on escalation and contradiction rules (R6–R7, C1–C4)
- `Validation_Policy.json` depends on sufficiency grammar and prohibited shortcuts

### Inference pattern dependencies (operational)

- `Inference_Patterns.md` depends on `Inference_Rules.md` and must cite `governing_rules` per pattern
- ontology and mapping artifacts should declare `pattern_id` (e.g. PAT-POS-001) for each inferential move
- future `Artifact_Contracts` should validate pattern template completeness

### Behaviour ontology dependencies

- `Behaviour_to_ILO.json` depends on `Observable_Behaviours.json` and `Learning_Objects.json`
- `Misconception_Ontology.json` should align with `Observable_Behaviours.json`

### Learning Object dependencies

- `Behaviour_to_ILO.json` depends on `Learning_Objects.json`
- `Domain_Understanding.json` depends on the Learning Object ontology

### Domain interpretation dependencies

- `LO_to_Domain_Understanding.json` depends on `Learning_Objects.json` and `Domain_Understanding.json`
- `Domain_to_AI_CFT.json` depends on `Domain_Understanding.json`

### Policy dependencies

- `Aggregation_Policy.json` depends on evidence, behaviour, LO, and Domain Understanding structures
- `Validation_Policy.json` depends on aggregation outputs and review requirements
- `Researcher_Review_Protocol.md` depends on validation policy and confidence model

### Worksheet dependencies

- each worksheet rubric depends on the architecture, behaviour ontology, LO ontology, and validity rules
- each worksheet extraction schema depends on the evidence model
- each worksheet behaviour opportunity file depends on the behaviour ontology

### Portfolio dependencies

- portfolio artifacts depend on aggregation and validation policies
- dashboard artifacts depend on traceability, confidence, and review protocol definitions

## Change Impact Rule

If any upstream artifact changes, all downstream artifacts listed here must be checked for consistency before proceeding.
