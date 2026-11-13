# MMLA Data Explorer

A static website that shows the 2026 cohort data (worksheets, screen recordings,
CODAP Arbor logs, Python notebooks) and explains how each was processed.
Every value is read from the project files. Nothing is estimated.

## Quick start

```bash
# Build the site data from project files
python3 mmla_explorer/build_site_data.py

# Validate the build outputs
python3 mmla_explorer/validate_build.py

# Run all JS tests
npm test --prefix mmla_explorer

# Run Python tests
python3 mmla_explorer/test_site_data.py
python3 mmla_explorer/test_stage_credit_colors.py

# Open locally (works offline; fonts load from Google Fonts when online)
open mmla_explorer/site/index.html
```

All commands run from the **repository root**.

## npm scripts (run from `mmla_explorer/`)

| Command | What it does |
|---|---|
| `npm test` | Runs all `test_*.js` files |
| `npm run test:py` | Runs Python test scripts |
| `npm run test:all` | Runs both JS and Python tests |
| `npm run build` | Runs `build_site_data.py` |
| `npm run validate` | Runs `validate_build.py` |

## Repository layout

```
mmla_explorer/
  build_site_data.py      Reads project files, writes site/data/ and site/thumbs/
  validate_build.py       Checks required keys and counts in built data files
  run_tests.js            Runs all test_*.js as child processes
  test_*.js               JS unit tests for site rendering logic
  test_site_data.py       Cross-checks site data against original sources
  test_stage_credit_colors.py  Tests credit color logic
  build_report.json       Build log: missing files, privacy checks, counts
  video_durations_cache.json   Measured video lengths (avoid re-reading)
  site/
    index.html            Single-page app entry point
    assets/               app.js, style.css and per-section JS modules
    data/                 JS data files written by build_site_data.py (see below)
    downloads/            Downloadable CSVs and worksheet PDFs
    thumbs/               Cropped recording thumbnails
```

## Data files in `site/data/`

| File | Global var | Contents |
|---|---|---|
| `core.js` | `window.CORE` | Students, worksheets, sessions, logs, notebooks |
| `frames.js` | `window.FRAMES` | Per-frame screen recording data |
| `score_extra.js` | `window.SCORE_EXTRA` | Item notes and blocked flags |
| `worksheet_docs.js` | `window.WORKSHEET_DOCS` | Worksheet text overrides |
| `evaluation.js` | `window.EVAL_DATA` | Human-system agreement results |
| `structural_stopping.js` | `window.STRUCTURAL_STOPPING` | Structural stopping analysis |
| `quality_audit.js` | `window.QUALITY_AUDIT` | Data quality audit results |
| `ws12_review.js` | `window.WS12_REVIEW` | WS12 detailed review data |
| `notebook_evidence.js` | `window.NOTEBOOK_EVIDENCE` | Notebook inspection evidence |

All files are written by `build_site_data.py`. Do not edit them by hand.

## CI

GitHub Actions runs on every push to `main` and on pull requests:

- **validate** job: pipeline tests, `test_site_data.py`, `validate_build.py`
- **site-tests** job: `node run_tests.js` (all JS tests)

See `.github/workflows/validate.yml`.

## Privacy

- Only pseudonyms appear. Log IDs typed as real names are mapped with the official
  `PSEUDONYM_MAP` in `scripts/anonymize_student_data.py`. Instructor IDs are dropped.
- The build stops if a real name from that map or from the logs appears in the output.
- Thumbnails are cropped (browser tab and taskbar removed) and softened so no text is readable.
- Speech transcripts are not included.

The `site/` folder contains pseudonymised student answers. Check your data-sharing
rules before publishing it.
