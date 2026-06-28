# WS10 scoring context

This file is injected alongside `stage3_scoring.md` when scoring WS10.

## Files to load

- Rubric: `rubrics/WS10_rubric.json`
- Mapping: `mappings/WS10_AICFT_mapping.json`
- Responses: `students/<student>/WS10.json → extraction`

## Worksheet description

WS10 is a numeric table worksheet. Students work through a systematic threshold search on 7 energy values [28, 69, 219, 346, 359, 408, 489]. All items are numeric and checked deterministically in Stage 2.

## Scoring notes

- All items are validated deterministically. If the validation file marks this worksheet blocked:true, set blocked:true and items:[] in the scoring output. Do not attempt to score a blocked worksheet.
- If the numeric table was partially captured, score only the items present in the extraction file. Mark the rest review:true.
