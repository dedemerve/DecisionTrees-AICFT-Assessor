# Milestone 4 Summary

## Domain Understanding Ontology

| Field | Value |
|-------|-------|
| Artifacts | `Domain_Understanding.json`, `LO_to_Domain_Understanding.json` |
| Version | **1.0** |
| Validation status | **PASS** |
| Domains | 8 emergent assessment constructs |
| ILO→Domain pairs | 37 |
| Domain stress tests | 5/5 passed |

## Methodological contribution

> You are not assessing AI-CFT directly. You are assessing Decision Tree understanding through an Evidence-Centered, multimodal, explainable assessment framework, and only then deriving provisional AI-CFT interpretations through a constrained, human-governed inferential process.

## Construct validation gate

Each domain includes `construct_validation` with:

- what_construct_represents
- supporting_evidence / non_supporting_evidence
- not_formed_when
- confusable_with

## Domain Independence Matrix

- Pairs analyzed: 28
- High/moderate overlap risk: 5

### Top overlap pairs

| Domain A | Domain B | Shared ILO | Risk |
|----------|----------|------------|------|
| Classification Reasoning | Decision Structure Reasoning | 4 | moderate |
| Classification Reasoning | Supervised Data Representation Understanding | 2 | moderate |
| Evidence-Based Parameter Tuning | Threshold Reasoning | 2 | high |
| Threshold Reasoning | Decision Structure Reasoning | 2 | moderate |
| Classification Reasoning | Threshold Reasoning | 1 | low |

## Domain Stress Test

| Test | Scenario | Status |
|------|----------|--------|
| DST-01 | Conceptual high, procedural low | PASS |
| DST-02 | Procedural high, reflection low | PASS |
| DST-03 | Video strong, worksheet weak | PASS |
| DST-04 | Reflection strong, CODAP weak | PASS |
| DST-05 | Single evidence source | PASS |

## Automated validation

- `reports/milestone4_validation.json` — single validation artifact (includes stress test when run)

## Remaining risks

1. Human expert domain boundary agreement pending.
2. `DU_GENERALISATION` partial ILO proxy coverage (accepted limitation).
3. Domain synthesis engine is provisional until `Aggregation_Policy.json` is authored.

## Milestone 5 design constraint

Domain_to_AI_CFT must follow the design constraint in `Domain_Understanding.json`:

> Domain_to_AI_CFT must not be implemented as a deterministic lookup table. AI-CFT claims are interpretive, provisional, and evidence-weighted. Each mapping must specify the theoretical rationale, minimum evidence requirements, convergence criteria, contradiction conditions, confidence ceiling, and explicit situations where escalation to the AI-CFT level is prohibited. No Domain may map directly to an AI-CFT competency solely because it is present. Domain evidence must satisfy sufficiency and coherence requirements before an AI-CFT interpretation becomes available.

## Expert review status

| Review | Status |
|--------|--------|
| Automated validation | complete |
| Domain stress test | complete |
| Independence matrix | complete |
| Human expert review | **pending** |

## Validation summary

| Check | Status |
|-------|--------|
| `milestone4_validation.json` | pass |
| Domain stress test | pass |

