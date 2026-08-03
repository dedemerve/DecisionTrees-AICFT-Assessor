# Q1 Claim Language — Process / Pipeline / Methods Scope

Version: 2.0 | Date: 2026-07-20 | Status: Binding

**Active scope:** video analysis **pipeline**, **process data**, and **methods**.  
**Out of scope:** construct scoring (B0–B13 levels), IRR for proficiency scores, automated scorer validation.

Scoring artifacts were quarantined (not deleted) under:
`trash/scoring_out_of_scope_2026-07-20/`

---

## SAFE CLAIMS (use these)

| Context | Approved phrasing |
|---|---|
| Paper type | "This paper reports a multimodal process-data pipeline for CODAP Arbor screen recordings, producing structured expert narratives, episode-level process codes, and log/process metadata." |
| Dataset | "We release analysis-ready process tables (episodes, process codes, session process features) derived from observer narratives and video alignment. A 30-episode subset is expert self-adjudicated (two passes with washout); remaining labels are single-observer with confidence tiers." |
| Process codes | "V-layer process codes capture iteration, help-seeking, and related process traces; they are not proficiency scores. The 2025 release is pilot-model-ready for active codes only — not dual-rated and not training-ready for all 20 codes." |
| Pipeline | "The pipeline links screen recordings, expert observation steps, and (when available) event logs without assigning Acquire/Deepen construct levels." |
| Limitations | "This work does not validate an automated proficiency scorer or report inter-rater reliability for B0–B13 construct scores." |

---

## PROHIBITED PHRASES

| Prohibited | Why |
|---|---|
| "students were scored on B0–B13" | Scoring out of scope |
| "gold-standard construct labels / IRR established" | Quarantined; not claimed |
| "dual-rated / dual-adjudicated gold" | Single researcher — self-adjudication only |
| "training-ready for all 20 V-codes" | Zero-fire codes remain; 2026 recruit required |
| "human-level automated scoring reliability" | Out of scope |
| "AI-CFT proficiency results" | Would require scoring + validity evidence |
| "validated scorer" / "macro-F1 / κ demonstrates…" | Scoring validation quarantined |

---

## Active artifact stack (keep)

- `*_expert_process_narrative.json` (+ jsonl)
- `*_process_codes.json` + `tabular/` + `hf_export/`
- `*_log_process_metadata.json`
- `*_video_analysis_bundle.json` (process-only manifest)
- `framework/VIDEO_PROCESS_CODEBOOK_v1.md`

---

## Quarantined (recoverable)

See `trash/scoring_out_of_scope_2026-07-20/MANIFEST.json`.
