# User — Process Pipeline Q1 Gate

Run a professional gate on the **process / pipeline / methods** stack. Start with the pilot student, then recommend cohort readiness.

## Inputs (attach or open)

| Role | Path |
|------|------|
| Scope | `framework/SCOPE_PROCESS_PIPELINE_ONLY.md` |
| Claim language | `framework/Q1_CLAIM_LANGUAGE.md` |
| Codebook | `framework/VIDEO_PROCESS_CODEBOOK_v1.md` |
| Pilot narrative | `training_datasets/2025/{{STUDENT_ID}}/{{STUDENT_ID}}_expert_process_narrative.json` |
| Pilot process codes | `training_datasets/2025/{{STUDENT_ID}}/{{STUDENT_ID}}_process_codes.json` |
| Pilot tabular | `training_datasets/2025/{{STUDENT_ID}}/tabular/` |
| Pilot bundle | `training_datasets/2025/{{STUDENT_ID}}/{{STUDENT_ID}}_video_analysis_bundle.json` |
| Optional log meta | `training_datasets/2025/{{STUDENT_ID}}/{{STUDENT_ID}}_log_process_metadata.json` |
| Quarantine note | `trash/scoring_out_of_scope_2026-07-20/README.md` |

Default `{{STUDENT_ID}}` = `Ally`.

---

## Checklist (execute in order)

### A. Pilot quality (~15 min)

1. **Narrative timeline** — Steps ordered; `uzman_nitel_gözlemi` readable; timestamps/`episode_id` coherent; no orphaned steps that break the story.
2. **Process codes + tabular** — Episodes cover the session; each episode has V1–V8 decisions in `{observed|not_observed|not_measurable}`; JSON ↔ `tabular/*_episodes*` ↔ `*_episode_process_codes*` row counts align; codes do not claim proficiency levels.
3. **Bundle hygiene** — `scoring_out_of_scope === true`; `bundle_version` process-only; `artifacts` has **no** `construct_scores` path; measurement layers are narrative / process_codes / log only.

### B. Claim lock (3–5 sentences)

Using **only** SAFE CLAIMS from `Q1_CLAIM_LANGUAGE.md`, draft a paper/abstract claim block.  
Hard fail if any of: score, IRR, κ, F1, “validated scorer”, B0–B13 proficiency results.

### C. Methods evidence choice (pick 1–2)

Recommend which Q1 evidence track(s) to pursue next, with one primary figure/table each:

| Track | What to show |
|-------|----------------|
| `pipeline_reproducibility` | Same inputs → same process tables |
| `codebook_usability` | V-layer clarity / coverage / decision-state distribution |
| `multimodal_linkage` | video ↔ narrative ↔ log (when available) join |

### D. Commit readiness

State whether quarantine + process-only bundles + claim docs are ready to commit. Do **not** commit; only advise.

### E. Hard prohibitions (confirm not recommended)

- Restore scoring from trash  
- IRR / calibration / fewshot work  
- Any delete/move under frozen research trees  

---

## Required JSON output

```json
{
  "gate_id": "process_pipeline_q1_gate_v1",
  "student_id": "{{STUDENT_ID}}",
  "verdict": "PASS | PASS_WITH_NOTES | REFINE | BLOCK",
  "pilot_checks": {
    "narrative_timeline": { "status": "pass|fail|warn", "notes": [] },
    "process_codes_tabular": { "status": "pass|fail|warn", "notes": [] },
    "bundle_hygiene": { "status": "pass|fail|warn", "notes": [] }
  },
  "cohort_trust": "yes|conditional|no",
  "claim_draft_en": "3-5 sentences, SAFE CLAIMS only",
  "claim_violations": [],
  "methods_tracks": [
    {
      "id": "pipeline_reproducibility|codebook_usability|multimodal_linkage",
      "priority": 1,
      "rationale": "",
      "primary_deliverable": "figure or table name"
    }
  ],
  "commit_advice": { "ready": true, "message": "commit only when user asks" },
  "prohibitions_acknowledged": true,
  "blocking_issues": [],
  "next_actions": ["ordered, concrete, owner-ready"]
}
```
