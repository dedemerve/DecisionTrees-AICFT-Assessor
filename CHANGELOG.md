# Changelog

All notable changes to this project are recorded here.
Format: `## YYYY-MM-DD` → bullet points.

---

## 2026-11-13

### Site infrastructure
- Added `mmla_explorer/package.json` with `npm test`, `npm run validate`, `npm run build` scripts
- Added `mmla_explorer/run_tests.js` to run all `test_*.js` as child processes
- Added `mmla_explorer/validate_build.py` — 39 schema checks on built data files
- Expanded `mmla_explorer/README.md` with full command reference, data file table, CI notes
- Added site-tests job to `.github/workflows/validate.yml` (runs JS tests in CI)

### Data
- WS15 scores added to cohort
- WS14 scoring fixed: added `credit_levels` to bundle rubric and Xeno supplement
- WS13 all 15 students rescored with relaxed B1/B2/B3 rubric
- v6 report scope expanded to WS1-WS15 with unified methodology

---

## 2026-11-12

### Scoring
- WS14 site data rebuilt with updated scores
- WS13 B1/B2/B3 rubric relaxed; all 25 items shown in findings answer grid
- WS13 CODAP log notes added to `score_extra` for per-student item context
- Worksheet findings breadcrumbs matched to collected data section

---

## 2026-11-10

### Site
- Structural stopping analysis added
- WS12 compact renderer added (130 cells, 13 student disclosures, 10 groups)
- Fix: `max_score=0` items no longer cause test failures
- Fix: WS5/WS6/WS7 scoring corrections applied

---

## Earlier

See `git log --oneline` for full history.
