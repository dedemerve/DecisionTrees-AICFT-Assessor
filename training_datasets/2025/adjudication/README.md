# Expert adjudication pack (2025) — single researcher + AI assist

**Claim lock (binding):**
> Expert-coded, self-adjudicated 2025 process training subset; pilot-model-ready for active V-codes. Not dual-rated; not all-20-codes training-ready.

## Roles (binding)

| Role | Who | Artifact |
|------|-----|----------|
| **AI-A** | First AI coding | `pass1_coding_form.json` (locked) |
| **Expert B** | Second independent AI expert (conservative) | `expert_b_coding_form.json` |
| **You (human)** | Pass 2 coder after ≥7 days | `pass2_coding_form.json` + resolve queue |

AI agreement ≠ gold. You own finals.

## Files

| File | Role |
|------|------|
| `calibration_set_30.json` | Frozen 30-episode list (L3 excluded) |
| `pass1_coding_form.json` | AI-A Pass 1 (locked) |
| `expert_b_coding_form.json` | Independent Expert B |
| `disagreement_queue.json` / `.md` | AI-A vs B diffs — **your review worklist** |
| `pass2_coding_form.json` | Your blind re-code after washout |
| `pipeline_hints_SEALED.json` | Pipeline heuristics — not gold |
| `EPISODE_SEGMENTATION_PROTOCOL.md` | As-is boundaries |
| `SELF_ADJUDICATION_PROTOCOL.md` | Coding rules + claim |
| `resolve_log.template.json` | Final resolve after Pass 2 |

## Your next actions

1. Open `disagreement_queue.md` — **9 HIGH** items (observed ↔ not_observed flips).
2. For each item: watch/read evidence → fill `human_final` + `human_rationale` in `disagreement_queue.json`.
3. Wait ≥7 days from Pass 1 lock (`pass1_locked_at`).
4. Fill `pass2_coding_form.json` **blind** (do not open Pass 1 / Expert B / queue while coding).
5. Reconcile Pass 2 vs your queue finals → `resolve_log.json`.
6. Tag `gold_tier: expert_adjudicated` on resolved cells; then V7 cohort back-fill + pilot train.

## Note on “other AI”

Repo’da ayrı bir AI-B dosyası yoktu. Karşılaştırma: **Pass1 (AI-A) vs Expert B (bu oturum)**.  
Başka AI’nın JSON’unu eklersen yeniden diff alınır.
