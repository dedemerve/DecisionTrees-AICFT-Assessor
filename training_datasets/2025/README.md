# 2025 MMLA frame + Word training pipeline

Outputs live under `training_datasets/2025/` (never mutates frozen `data_sources_2025/`).

## Same extractor as 2026

```bash
.venv-hybrid/bin/python scripts/dynamic_video_analytics.py \
  Ally Barbara Bob Boris Calvin Daisy Daryl David Edgar Eliot Felicity Frank Henry Mike Ozzy Sabrina Zabby \
  --audio-root training_datasets/2025 \
  --video-root data_sources_2025 \
  --task-activity codap \
  --skip-existing
```

Silent 2025 recordings → `motion_only_fallback` keyframes + CODAP task guard (same as silent 2026 sessions).

## Training samples (Word GT + video frames)

```bash
.venv-hybrid/bin/python scripts/build_2025_mmla_training_dataset.py --all-with-video
```

## Behavior coding + frame↔docx alignment (primary learning set)

```bash
.venv-hybrid/bin/python scripts/align_2025_frames_to_analysis.py
# or: … Ally Boris Henry
```

For each observation step:
1. **Multi-label behavior codes** from expert Turkish text  
   (`CREATE_GRAPH`, `ADD_MOVABLE_VALUE`, `UPDATE_MOVABLE_VALUE`, `UPDATE_THRESHOLD`, `EMIT_TREE`, …)
2. **Screen-change gloss** — how the CODAP UI should look after that act
3. **Visual align** — Word embedded screenshot → nearest motion frame via  
   aspect-band dHash + **monotonic DP** (steps never go backwards in time)

Per-student outputs:
- `{id}_behavior_coded_alignments.json` (+ `.jsonl`)
- `{id}_screen_change_timeline.json`

Cohort: `cohort_behavior_alignment_summary.json`
