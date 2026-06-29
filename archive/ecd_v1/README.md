# ECD v1 — Archived Evidence-Centered Design Assessment Chain

## What this folder is

This directory preserves the **first-generation** assessment architecture for the
DecisionTrees-AICFT-Assessor project: a multi-layer Evidence-Centered Design (ECD)
chain from raw evidence through Observable Behaviours (OB), Instructional Learning
Objects (ILO), Domain Understanding (DU), and `Domain_to_AI_CFT` interpretive
policies to provisional UNESCO AI-CFT recommendations.

Artifacts include frozen ontologies, inference mappings, validators, builders, JSON
Schemas, milestone reports (M1–M5), and unit tests that enforced that chain.

## Why it was archived (not deleted)

The research workflow for the current pilot is **researcher-led portfolio review**:
each pre-service teacher portfolio is read holistically by a researcher
(`researcher_review_required` was already true at every interpretive step). At this
scale, automated evidence-threshold machinery (`minimum_evidence_sources`,
`confidence_ceiling`, `contradiction_conditions`, multi-layer `may_contribute_to`
policies) did not reduce reviewer workload — it duplicated judgement in JSON rule
language without calibration data.

The active pipeline was simplified to three steps:

1. Collect raw evidence (worksheets, CODAP logs, screen recordings — unchanged)
2. Present UNESCO LO3.x indicator text beside relevant evidence excerpts
   (`lo_rubric_check.py`)
3. Record researcher decisions (`met` / `partial` / `not_met` / `insufficient_data`)
   with evidence quotes and a one-sentence rationale

## When to restore or consult this archive

Revisit ECD v1 if any of the following become true:

- Portfolio sample grows beyond roughly **100** cases and manual review becomes a bottleneck
- **Multiple coders** require inter-rater reliability (e.g. Cohen's κ) with explicit convergence rules
- Funders or reviewers require full ECD traceability from behaviour codes to domain constructs
- Automated escalation rules are calibrated against researcher override data

## Active pipeline status

**The running application does not import or read files under `archive/ecd_v1/`.**
Validators, portfolio builders, and worksheet bundle checks must not reference
these paths at runtime. Historical reference and `git log` / `git blame` remain
available because files were moved with `git mv`.

## Layout

| Path | Contents |
|------|----------|
| `framework/` | OB, ILO, DU, Domain→AI-CFT JSON ontologies and dependency graphs |
| `scripts/` | Builders, validators, stress tests, milestone summary generators |
| `tests/` | Milestone 1–5 unit tests for the ECD chain |
| `schema/` | JSON Schemas for archived framework artifacts |
| `reports/` | Milestone validation JSON and human summaries (M1–M5) |

## Git reference

Archived on branch `main` when migrating to the simple LO rubric workflow.
See commit history for the exact migration commit message.
