# Milestone 2 Summary

## Instructional Learning Object (ILO) Ontology

| Field | Value |
|-------|-------|
| Artifact | `framework/Learning_Objects.json` |
| Terminology | **ILO** — Instructional Learning Object |
| Version | **1.0** |
| Validation status | **PASS** |
| ILO count | 21 |
| Upstream ontology | Observable_Behaviours.json v1.0 |

## Contribution (publication)

> The framework distinguishes reusable Observable Behaviours from Instructional Learning Objects, allowing behavioural evidence to be interpreted independently of competency frameworks.

## Behaviour → ILO Coverage Matrix

- Behaviours mapped: 28/28

## Concept Families

| Family | ILO count |
|--------|-----------|
| classification | 6 |
| data_representation | 5 |
| evaluation | 5 |
| reasoning | 2 |
| reflection | 3 |

## Instructional Sequence

Canonical order documented in `ILO_Dependency_Graph.json` → `instructional_sequence`.

```
ILO_PRIOR_BELIEF → ILO_INSTANCE → ILO_FEATURE → ILO_LABEL → ILO_DATASET → ILO_TRAINING_ROLE → ILO_THRESHOLD → ILO_RULE → ...
```

## ILO Dependency Graph

- Artifact: `framework/ILO_Dependency_Graph.json`
- Edges: 36
- Validation errors: 0

## Automated validation

- `reports/milestone2_validation.json` — single validation artifact

## Remaining Risks

1. Human expert ILO coding agreement pending.
2. No dedicated `generalisation` ILO (v1.0 accepted limitation).
3. TP/TN/FP/FN not separate ILOs — embedded in ILO_CONFUSION_MATRIX.

## Accepted Limitations

- `generalisation` concept family has no standalone ILO; partial coverage via `reasoning` ILOs.
- AI-CFT competency codes (LO3.x) remain separate from ILO layer.
- `ILO_PRIOR_BELIEF` is diagnostic (sequence position 0) and excluded from mastery aggregation.

## Expert Review Status

| Review | Status |
|--------|--------|
| Automated validation | complete |
| Behaviour→ILO matrix complete | complete |
| Human expert review | **pending** |

## Validation summary

| Check | Status |
|-------|--------|
| Automated validation (`milestone2_validation.json`) | pass |
| ILO dependency graph | pass |
| Behaviour→ILO coverage | 28/28 |

