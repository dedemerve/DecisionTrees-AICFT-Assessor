# Milestone 2 Freeze Report

## Instructional Learning Object (ILO) Ontology

| Field | Value |
|-------|-------|
| Artifact | `framework/Learning_Objects.json` |
| Terminology | **ILO** — Instructional Learning Object |
| Version | **1.0** |
| Freeze status | **PENDING_APPLY** |
| Generated | 2026-06-28T10:53:46.209524+00:00 |
| ILO count | 21 |
| Frozen behaviour input | Observable_Behaviours.json v1.0 |

## Contribution (publication)

> The framework distinguishes reusable Observable Behaviours from Instructional Learning Objects, allowing behavioural evidence to be interpreted independently of competency frameworks.

## Behaviour → ILO Coverage Matrix

- Behaviours mapped: 28/28
- Full matrix: `behaviour_ilo_coverage_matrix.json`

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

## Remaining Risks

1. Human expert ILO coding agreement pending.
2. No dedicated `generalisation` ILO (v1.0 accepted limitation).
3. TP/TN/FP/FN not separate ILOs — embedded in ILO_CONFUSION_MATRIX.
4. Milestone 3 mapping (`Behaviour_to_ILO.json`) not yet authored.

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

## Freeze Decision

**READY:** Run with `--apply-freeze` to write freeze metadata.
