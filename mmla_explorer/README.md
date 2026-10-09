# MMLA Data Explorer

A static website that shows the 2026 cohort data (worksheets, screen recordings,
CODAP Arbor logs, Python notebooks) and explains how each was processed.
Every value is read from the project files. Nothing is estimated.

## Build, test, open

```bash
python3 mmla_explorer/build_site_data.py   # reads project files, writes site/data, site/thumbs
python3 mmla_explorer/test_site_data.py    # re-reads the sources and checks the site data
open mmla_explorer/site/index.html         # works offline; fonts load from Google Fonts when online
```

`build_report.json` lists missing files, notes and the privacy check result.
`video_durations_cache.json` stores measured video lengths so the videos are read only once.

## Privacy

- Only pseudonyms appear. Log IDs typed as real names are mapped with the official
  `PSEUDONYM_MAP` in `scripts/anonymize_student_data.py`. Instructor IDs are dropped.
- The build stops if a real name from that map or from the logs appears in the output.
- Thumbnails are cropped (browser tab and taskbar removed) and softened so no text is readable.
- Speech transcripts are not included.

The site folder contains pseudonymised student answers. Check your data-sharing rules
before publishing it.
