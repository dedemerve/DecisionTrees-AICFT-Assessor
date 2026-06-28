# Milestone reports (lightweight policy)

Each framework milestone (M1–M5) produces **at most two artifacts**:

| File | Purpose |
|------|---------|
| `milestone{N}_summary.md` | Human-readable: what was defined, key decisions, known gaps (~1 page). Suitable for supplementary material. |
| `milestone{N}_validation.json` | Machine-readable: validator status, errors, nested analytics (single file). |

Summaries use **validation status** (pass/fail). Framework artifacts use `framework_version` / `mapping_schema_version` only — no `freeze` blocks.

## What we do not maintain

- No `generated_at` / audit timestamps on report JSON.
- No `reports/milestone*_freeze/` shard folders.
- No `freeze` metadata on framework JSON or dependency graphs.

## Commands

```bash
python scripts/validate_observable_behaviours.py    # → milestone1_validation.json
python scripts/validate_learning_objects.py         # → milestone2_validation.json
python scripts/validate_behaviour_to_ilo.py         # → milestone3_validation.json
python scripts/validate_domain_understanding.py     # → milestone4_validation.json
python scripts/validate_domain_to_ai_cft.py         # → milestone5_validation.json

python scripts/generate_milestone1_summary.py  # → milestone1_summary.md
# … same pattern for milestones 2–5
```

## Scale note

This project targets a small research corpus (~20–40 teacher candidates). The ECD ontology is academically useful; the reporting layer stays minimal so effort stays on data collection and manuscript writing.
