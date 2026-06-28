# Milestone 3 Summary

## Behaviour → ILO Inference Mapping

| Field | Value |
|-------|-------|
| Artifact | `framework/Behaviour_to_ILO.json` |
| Schema | **1.1** (qualitative confidence only) |
| Freeze status | **PENDING_APPLY** |
| Accepted pairs | 60 |
| Behaviours covered | 28/28 |
| Rejected alternatives | 18 |
| Cross-construct pairs | 20 |

## Scientific significance

> First inference layer of the framework: assessment theory becomes operational mapping from Observable Behaviours to Instructional Learning Objects with explicit roles, rejected alternatives, and counter-evidence.

## Confidence policy

- Qualitative levels only: `high`, `moderate`, `low`, `baseline`
- Each record requires `confidence_basis[]`
- Numeric quantization deferred to `Confidence_Model.json`
- Ad-hoc numeric confidence **prohibited**

## Mapping roles

| Role | Count |
|------|-------|
| primary | 27 |
| secondary | 31 |
| contextual | 1 |
| diagnostic | 1 |

## Automated validation

- `reports/milestone3_validation.json` — single validation artifact

## Remaining risks

1. Human expert agreement on cross-construct bridges pending.
2. Counter-evidence templates require calibration against pilot portfolios.
3. `Confidence_Model.json` not yet authored — no numeric aggregation.

## Accepted limitations

- Some ILOs supported by only one behaviour (underrepresentation flagged in coverage report).
- `ILO_PRIOR_BELIEF` mapped as diagnostic-only baseline.
- Rejected alternatives documented for high-ambiguity behaviours only (9/28).

## Expert review status

| Review | Status |
|--------|--------|
| Automated validation | complete |
| Human expert review | **pending** |

## Freeze decision

**READY:** Run with `--apply-freeze` to write freeze metadata.
