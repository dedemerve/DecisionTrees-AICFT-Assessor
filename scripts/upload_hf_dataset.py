#!/usr/bin/env python3
"""
Build and upload the MMLA frame dataset to Hugging Face.

Includes:
  - All 5,825 behaviour-coded frames from the two CODAP Arbor sessions
  - metadata.csv  (one row per frame, manifest-verified)
  - CODAP platform log CSV (anonymized)
  - Dataset card (README.md)

Run after:  hf auth login
Usage:      python3 scripts/upload_hf_dataset.py [--stage-only]
"""
from __future__ import annotations

import csv
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "hf_dataset_stage"

HF_REPO = "dedemerve/DecisionTrees-AICFT-Frames"

SESS_DIR = {
    "codap_21apr": "codap_arbor_21april_audio",
    "codap_28apr": "codap_arbor_28april_audio",
}
SESS_LABEL = {
    "codap_21apr": "CODAP Arbor - 21 April 2026",
    "codap_28apr": "CODAP Arbor - 28 April 2026",
}
TRIGGER_DESC = {
    "motion_threshold_exceeded": "Screen changed noticeably while speech was available",
    "motion_only_fallback": "Screen changed noticeably in a recording without usable speech",
    "speech_anchor_midpoint": "Someone was speaking at that moment",
    "codap_static_gap_fill": "Gap fill: nothing captured for a while on the CODAP screen",
    "silent_screen_gap_fill": "Gap fill: nothing captured for a while in a silent recording",
}
STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel", "Marco", "Marcus",
    "Melinda", "Nadia", "Serena", "Shana", "Sheila", "Ulysses", "Zara",
]


def load_frames() -> list[dict]:
    txt = (ROOT / "mmla_explorer" / "site" / "data" / "frames.js").read_text("utf-8")
    return json.loads(txt[len("window.FRAMES="):-2])


def build_manifest_index() -> dict[tuple[str, str, str], dict]:
    index = {}
    for ss, proc in SESS_DIR.items():
        for s in STUDENTS:
            p = ROOT / "data_sources_2026" / proc / s / f"{s}_video_extraction_manifest.json"
            if not p.exists():
                continue
            for entry in json.load(open(p))["frames"]:
                index[(s, ss, entry["frame_id"])] = entry
    return index


def build_dataset() -> int:
    STAGE.mkdir(parents=True, exist_ok=True)
    img_dir = STAGE / "images"
    img_dir.mkdir(exist_ok=True)

    F = load_frames()
    manifest = build_manifest_index()
    coded = [f for f in F if f["ss"] in SESS_DIR]

    rows = []
    missing_img = 0
    missing_manifest = 0

    for f in coded:
        key = (f["s"], f["ss"], f["id"])
        man_entry = manifest.get(key)
        if not man_entry:
            missing_manifest += 1
            continue

        proc = SESS_DIR[f["ss"]]
        src = ROOT / "data_sources_2026" / proc / f["s"] / f"{f['s']}_frames" / f"{f['id']}.jpg"
        if not src.exists():
            missing_img += 1
            continue

        dest_name = f"{f['s']}_{f['ss']}_{f['id']}.jpg"
        dest = img_dir / dest_name
        if not dest.exists():
            shutil.copy2(src, dest)

        rows.append({
            "file_name": f"images/{dest_name}",
            "student": f["s"],
            "session": f["ss"],
            "session_label": SESS_LABEL[f["ss"]],
            "frame_id": f["id"],
            "timestamp_s": round(f["t"], 2),
            "selection_trigger": f["tr"],
            "selection_trigger_desc": TRIGGER_DESC.get(f["tr"], f["tr"]),
            "screen_change_pct": round(f["px"], 2) if f.get("px") is not None else "",
            "speaker": f.get("sp") or "",
            "behavior": f.get("b") or "",
            "behavior_secondary": f.get("b2") or "",
            "screen_context": f.get("sc") or "",
            "phase": f.get("ph") or "",
            "coder_confidence": f.get("cf") or "",
            "evidence_flags": ",".join(f["ev"]) if f.get("ev") else "",
            "has_thumbnail": str(bool(f.get("th"))).lower(),
            "source_timestamp_s": round(man_entry.get("source_timestamp_seconds", f["t"]), 2),
            "extraction_trigger_raw": man_entry.get("extraction_trigger_reason", ""),
        })

    print(f"Frames staged    : {len(rows)}")
    print(f"Missing image    : {missing_img}")
    print(f"Missing manifest : {missing_manifest}")

    csv_path = STAGE / "metadata.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print("metadata.csv written")

    log_src = (ROOT / "data_sources_2026" / "All Documents" /
               "28 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv")
    if log_src.exists():
        shutil.copy2(log_src, STAGE / "codap_log_anonymized.csv")
        print("Log CSV copied")
    else:
        print(f"Log CSV not found at: {log_src}")

    write_card(len(rows))
    print(f"Dataset staged at: {STAGE}")
    return len(rows)


def write_card(n: int) -> None:
    card = f"""\
---
license: cc-by-4.0
task_categories:
  - other
tags:
  - education
  - multimodal-learning-analytics
  - decision-trees
  - screen-recording
  - behavior-coding
  - MMLA
  - AICFT
  - UNESCO
language:
  - tr
  - en
size_categories:
  - 1K<n<10K
---

# DecisionTrees-AICFT-Frames

Behaviour-coded screen-recording frames from a 2026 Turkish pre-service teacher cohort (n=15) learning decision trees with CODAP Arbor. Part of the AI Competency Framework for Teachers (AI-CFT) assessment research.

## Dataset summary

| | |
|---|---|
| **Frames** | {n:,} |
| **Students** | 15 pseudonymised pre-service teachers |
| **Sessions** | 2 x CODAP Arbor sessions (21 April and 28 April 2026) |
| **Frame selection** | Motion threshold + speech anchor triggers |
| **Behaviour labels** | 9 categories (see below) |
| **Coder** | Single researcher; confidence recorded per frame |
| **Language** | Turkish instruction, English labels |

## Behaviour categories

| Code | Label |
|---|---|
| `EXPLORE_DATA` | Explore data |
| `SELECT_TARGET` | Select target variable |
| `BUILD_TREE` | Build decision tree |
| `TUNE_THRESHOLD` | Adjust split threshold |
| `EVALUATE_MODEL` | Check model performance |
| `COMPARE_MODELS` | Compare models |
| `INTERPRET_RESULTS` | Interpret results |
| `IDLE_THINKING` | Idle / thinking |
| `OFF_TASK` | Off task |

## Files

| File | Description |
|---|---|
| `images/` | JPG frames, named `<student>_<session>_<frame_id>.jpg` |
| `metadata.csv` | One row per frame with all labels and metadata |
| `codap_log_anonymized.csv` | Raw CODAP Arbor event log (anonymized) |

## Columns in metadata.csv

| Column | Description |
|---|---|
| `file_name` | Path to the image in this repository |
| `student` | Pseudonym (Amy, Bruno, Helena, ...) |
| `session` | `codap_21apr` or `codap_28apr` |
| `session_label` | Human-readable session name |
| `frame_id` | Frame identifier within the session |
| `timestamp_s` | Time in the recording (seconds) |
| `selection_trigger` | Machine trigger code that selected this frame |
| `selection_trigger_desc` | Plain-English description of the trigger |
| `screen_change_pct` | Pixel-level screen change at extraction (%) |
| `speaker` | Who was speaking: `teacher`, `student`, or empty |
| `behavior` | Primary coded behaviour (see categories above) |
| `behavior_secondary` | Secondary behaviour if two were observed |
| `screen_context` | What was on screen: `TREE`, `TABLE`, `GRAPH`, `MIXED`, `MENU` |
| `phase` | Task phase: `SETUP`, `BUILDING`, `TUNING`, `EVALUATING`, `IDLE` |
| `coder_confidence` | Researcher confidence: `LOW`, `MEDIUM`, or `HIGH` |
| `evidence_flags` | Comma-separated on-screen observation flags |
| `has_thumbnail` | Whether a downsampled thumbnail appears on the companion website |

## Companion website

Full archive with worksheets, notebooks and platform logs:
[Decision Tree Learning Archive](https://dedemerve.github.io/DecisionTrees-AICFT-Assessor/)

Source code: [github.com/dedemerve/DecisionTrees-AICFT-Assessor](https://github.com/dedemerve/DecisionTrees-AICFT-Assessor)

## Citation

```bibtex
@dataset{{dede2026decisiontrees,
  author    = {{Dede, Merve}},
  title     = {{DecisionTrees-AICFT-Frames}},
  year      = {{2026}},
  publisher = {{Hugging Face}},
  url       = {{https://huggingface.co/datasets/{HF_REPO}}}
}}
```

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) -- You may share and adapt with attribution.
"""
    (STAGE / "README.md").write_text(card, encoding="utf-8")


def upload() -> None:
    try:
        from huggingface_hub import HfApi
    except ImportError:
        sys.exit("huggingface_hub not installed. Run: pip install huggingface_hub")

    api = HfApi()
    print(f"Creating repo {HF_REPO} ...")
    api.create_repo(repo_id=HF_REPO, repo_type="dataset", exist_ok=True)

    print("Uploading -- this will take several minutes ...")
    api.upload_folder(
        folder_path=str(STAGE),
        repo_id=HF_REPO,
        repo_type="dataset",
        commit_message="Initial dataset upload: coded frames + metadata",
    )
    print(f"\nDone: https://huggingface.co/datasets/{HF_REPO}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--stage-only", action="store_true",
                   help="Build local staging folder without uploading")
    args = p.parse_args()

    n = build_dataset()
    if not args.stage_only:
        upload()
    else:
        print(f"\nStage-only mode. Run without --stage-only to upload.")
        print(f"Total frames ready: {n}")
