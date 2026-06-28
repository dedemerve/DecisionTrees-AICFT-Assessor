# Milestone reports (lightweight policy)

Each framework milestone (M1–M5) produces **at most two artifacts**:

| File | Purpose |
|------|---------|
| `milestone{N}_summary.md` | Human-readable: what was defined, key decisions, known gaps (~1 page). Suitable for supplementary material. |
| `milestone{N}_validation.json` | Machine-readable: validator status, errors, nested analytics (single file). |

## What we do not maintain

- No `generated_at` / audit timestamps on report JSON.
- No parallel shard JSON under `reports/milestone3/`, `milestone4/`, or `milestone5/` (removed).
- No `reports/milestone*_freeze/` regeneration — those folders are **legacy** from an earlier multi-file freeze design.

Script names still use `generate_milestone*_freeze_package.py` for backward compatibility; they only write `milestone{N}_summary.md`.

Freeze metadata (`freeze.status`, `freeze.version`) lives on framework artifacts under `framework/` when `--apply-freeze` is run.

## Commands

```bash
python scripts/validate_observable_behaviours.py    # → milestone1_validation.json
python scripts/validate_learning_objects.py         # → milestone2_validation.json
python scripts/validate_behaviour_to_ilo.py       # → milestone3_validation.json
python scripts/validate_domain_understanding.py     # → milestone4_validation.json
python scripts/validate_domain_to_ai_cft.py         # → milestone5_validation.json

python scripts/generate_milestone1_freeze_package.py  # → milestone1_summary.md (+ optional --apply-freeze)
# … same pattern for milestones 2–5
```

## Scale note

This project targets a small research corpus (~20–40 teacher candidates). The ECD ontology is academically useful; the reporting layer stays minimal so effort stays on data collection and manuscript writing.
