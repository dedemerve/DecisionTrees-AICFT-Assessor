#!/usr/bin/env python3
"""
aicft_mcp.py — MCP server for the DecisionTrees AI-CFT Assessor pipeline.

Exposes the 2026 cohort research pipeline to LLM agents via the Model Context
Protocol (stdio transport).  All data is read from the local repository; no
external network calls are made.

Usage (stdio, e.g. in claude_desktop_config.json):
    {
      "command": "python",
      "args": ["/path/to/aicft_mcp.py"],
      "env": {"AICFT_REPO": "/path/to/DecisionTrees-AICFT-Assessor"}
    }

Or run directly:
    python aicft_mcp.py
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS & PATHS
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(
    os.environ.get(
        "AICFT_REPO",
        Path(__file__).parent,
    )
)

STUDENTS_DIR = REPO_ROOT / "students"
DATA_2026 = REPO_ROOT / "data_sources_2026"
HOMEWORK_DIR = DATA_2026 / "homework_scores"
COLAB_DIR = DATA_2026 / "Final Ödevi Dokümanları"
LOGS_21APR = DATA_2026 / "21 Nisan CODAP Arbor Dosyası"
LOGS_28APR = DATA_2026 / "28 Nisan CODAP Arbor Dosyası"
RECORDINGS_21APR = DATA_2026 / "21 April CODAP Arbor Screen Recordings"
RECORDINGS_28APR = DATA_2026 / "28 April CODAP Arbor Screen Recordings"
RECORDINGS_MAY = DATA_2026 / "05 May Colab Python Screen Recordings"
RUBRIC_GAPS = DATA_2026 / "rubric_gaps_2026.json"
FRAMEWORK = REPO_ROOT / "mappings" / "AICFT_assessment_framework.json"
BEHAVIOR_GUIDE = REPO_ROOT / "screen_recording_analysis_guide.md"

KNOWN_WORKSHEETS = [
    "WS1", "WS3", "WS4", "WS5", "WS6", "WS7", "WS10", "WS11",
    "WS_DT", "WS_DT_INTRO", "WS_DT_TITANIC", "WS_DT_XENO",
]
WORKSHEET_ARTIFACTS = ["extraction", "scoring", "evidence", "validation"]
SESSIONS = ["21april", "28april", "colab_may"]

logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

# ─────────────────────────────────────────────────────────────────────────────
# MCP SERVER
# ─────────────────────────────────────────────────────────────────────────────

mcp = FastMCP("aicft_mcp")

# ─────────────────────────────────────────────────────────────────────────────
# SHARED UTILITIES
# ─────────────────────────────────────────────────────────────────────────────


def _load_json(path: Path) -> Any:
    """Load JSON from path; raises FileNotFoundError if missing."""
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _student_dir(student_id: str) -> Path:
    return STUDENTS_DIR / student_id


def _all_students() -> List[str]:
    if not STUDENTS_DIR.exists():
        return []
    return sorted(
        p.name
        for p in STUDENTS_DIR.iterdir()
        if p.is_dir() and not p.name.startswith(".")
    )


def _pipeline_status(student_id: str) -> Dict[str, Any]:
    """Return completion flags for each pipeline stage for a student."""
    sdir = _student_dir(student_id)
    status: Dict[str, Any] = {
        "portfolio": (sdir / "portfolio.json").exists(),
        "evidence_units": (sdir / "evidence_units.json").exists(),
        "worksheets": {},
        "homework_score": (HOMEWORK_DIR / f"{student_id}_homework_score.json").exists(),
        "colab_notebook": (COLAB_DIR / f"{student_id}.ipynb").exists(),
        "log_21april": any(
            LOGS_21APR.glob(f"{student_id}*.codap") if LOGS_21APR.exists() else []
        ),
        "log_28april": any(
            LOGS_28APR.glob(f"{student_id}*.codap") if LOGS_28APR.exists() else []
        ),
    }
    for ws in KNOWN_WORKSHEETS:
        ws_dir = sdir / ws
        if ws_dir.exists():
            status["worksheets"][ws] = {
                a: (ws_dir / f"{a}.json").exists() for a in WORKSHEET_ARTIFACTS
            }
    return status


def _fmt_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _err(msg: str) -> str:
    return f"Error: {msg}"


# ─────────────────────────────────────────────────────────────────────────────
# INPUT MODELS
# ─────────────────────────────────────────────────────────────────────────────


class StudentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    student_id: str = Field(
        ...,
        description=(
            "Pseudonymised student ID as it appears in the students/ folder "
            "(e.g. 'Amy', 'Bruno', 'Helena'). Case-sensitive."
        ),
        min_length=1,
        max_length=64,
    )


class WorksheetArtifactInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    student_id: str = Field(
        ...,
        description="Student pseudonym (e.g. 'Amy').",
        min_length=1,
        max_length=64,
    )
    worksheet: str = Field(
        ...,
        description=(
            "Worksheet ID, one of: WS1, WS3, WS4, WS5, WS6, WS7, WS10, WS11, "
            "WS_DT, WS_DT_INTRO, WS_DT_TITANIC, WS_DT_XENO."
        ),
    )
    artifact: str = Field(
        default="scoring",
        description=(
            "Artifact type: 'extraction' (OCR output), 'scoring' (item scores), "
            "'evidence' (LO evidence), 'validation' (Group B deterministic checks)."
        ),
    )

    @field_validator("worksheet")
    @classmethod
    def validate_worksheet(cls, v: str) -> str:
        if v not in KNOWN_WORKSHEETS:
            raise ValueError(
                f"Unknown worksheet '{v}'. Valid values: {', '.join(KNOWN_WORKSHEETS)}"
            )
        return v

    @field_validator("artifact")
    @classmethod
    def validate_artifact(cls, v: str) -> str:
        if v not in WORKSHEET_ARTIFACTS:
            raise ValueError(
                f"Unknown artifact '{v}'. Valid values: {', '.join(WORKSHEET_ARTIFACTS)}"
            )
        return v


class EvidenceSearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    lo_id: Optional[str] = Field(
        default=None,
        description=(
            "Filter by Learning Outcome ID, e.g. 'LO3.2.2'. "
            "If omitted, all LOs are returned."
        ),
    )
    student_id: Optional[str] = Field(
        default=None,
        description="Filter by student pseudonym. If omitted, all students are included.",
    )
    keyword: Optional[str] = Field(
        default=None,
        description="Case-insensitive keyword to match inside evidence text.",
        max_length=200,
    )


class LogFeaturesInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    student_id: str = Field(
        ...,
        description="Student pseudonym (e.g. 'Amy').",
        min_length=1,
        max_length=64,
    )
    session: str = Field(
        default="21april",
        description=(
            "Which CODAP session log to extract: '21april' or '28april'. "
            "CODAP logs only — Colab sessions have no structured log."
        ),
    )

    @field_validator("session")
    @classmethod
    def validate_session(cls, v: str) -> str:
        valid = {"21april", "28april"}
        if v not in valid:
            raise ValueError(f"session must be one of: {', '.join(sorted(valid))}")
        return v


# ─────────────────────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────────────────────


@mcp.tool(
    name="aicft_list_students",
    annotations={
        "title": "List 2026 Cohort Students",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_list_students() -> str:
    """List all pseudonymised students in the 2026 cohort with their pipeline completion status.

    Returns a JSON object keyed by student_id. Each value reports which pipeline
    stages (portfolio, worksheets, homework_score, colab_notebook, CODAP logs) have
    been completed and which are still pending.

    Returns:
        str: JSON object:
        {
          "<student_id>": {
            "portfolio": bool,
            "evidence_units": bool,
            "homework_score": bool,
            "colab_notebook": bool,
            "log_21april": bool,
            "log_28april": bool,
            "worksheets": {
              "<WS>": {
                "extraction": bool,
                "scoring": bool,
                "evidence": bool,
                "validation": bool
              }
            }
          }
        }
    """
    students = _all_students()
    if not students:
        return _err(
            f"No student directories found under {STUDENTS_DIR}. "
            "Run the pipeline first or check AICFT_REPO environment variable."
        )
    result = {s: _pipeline_status(s) for s in students}
    return _fmt_json(result)


@mcp.tool(
    name="aicft_get_student_portfolio",
    annotations={
        "title": "Get Student AI-CFT Portfolio",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_get_student_portfolio(params: StudentInput) -> str:
    """Retrieve the AI-CFT portfolio rollup for a single student.

    The portfolio aggregates LO evidence across all worksheets and proposes
    an AI-CFT competency level (Acquire / Deepen / Create) per Learning Outcome.
    It also records data gaps (items that could not be assessed).

    Args:
        params (StudentInput): student_id — pseudonym exactly as in students/ folder.

    Returns:
        str: JSON content of students/<student_id>/portfolio.json.

        Key fields:
        - "framework": UNESCO AI-CFT 2024
        - "lo_review_packets": per-LO evidence excerpts for researcher review
        - "evidence_by_lo": collected evidence keyed by LO ID
        - "data_gaps": list of worksheet/item pairs with missing data
        - "researcher_rubric_decisions": manually recorded decisions

        Error:
        "Error: Portfolio not found for <student_id>. Run run_portfolio_builder.py first."
    """
    path = _student_dir(params.student_id) / "portfolio.json"
    if not path.exists():
        return _err(
            f"Portfolio not found for '{params.student_id}'. "
            "Run: python run_portfolio_builder.py " + params.student_id
        )
    try:
        return _fmt_json(_load_json(path))
    except Exception as e:
        return _err(f"Failed to read portfolio: {e}")


@mcp.tool(
    name="aicft_get_worksheet_artifact",
    annotations={
        "title": "Get Student Worksheet Artifact",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_get_worksheet_artifact(params: WorksheetArtifactInput) -> str:
    """Retrieve one stage artifact for a student+worksheet combination.

    Artifact types:
    - extraction: raw OCR / HTR output from the worksheet scan
    - scoring:    item-level scores, confidence, review flags, totals
    - evidence:   per-item Learning Outcome evidence (feeds portfolio)
    - validation: deterministic pipeline health checks (Group B: WS5/WS6/WS7 only)

    Args:
        params (WorksheetArtifactInput):
            - student_id (str): e.g. 'Amy'
            - worksheet (str): e.g. 'WS5'
            - artifact (str): one of extraction | scoring | evidence | validation

    Returns:
        str: JSON content of students/<student_id>/<worksheet>/<artifact>.json.

        Error: "Error: <artifact>.json not found for <student_id>/<worksheet>."
    """
    path = _student_dir(params.student_id) / params.worksheet / f"{params.artifact}.json"
    if not path.exists():
        return _err(
            f"'{params.artifact}.json' not found for "
            f"'{params.student_id}/{params.worksheet}'. "
            f"Available worksheets: {', '.join(KNOWN_WORKSHEETS)}. "
            f"Check aicft_list_students for completion status."
        )
    try:
        return _fmt_json(_load_json(path))
    except Exception as e:
        return _err(f"Failed to read artifact: {e}")


@mcp.tool(
    name="aicft_get_homework_scores",
    annotations={
        "title": "Get Student Colab Homework Score",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_get_homework_scores(params: StudentInput) -> str:
    """Retrieve the automated Colab notebook homework score for a student.

    The score captures notebook health (cells, executions, errors, plots) and
    behavioural indicators B1–B12 derived from static analysis of the .ipynb:
    B1 = required imports, B2 = data load, B3 = EDA, B4 = cleaning,
    B5 = train/test split, B6 = model fit, B7 = accuracy, B8 = confusion matrix,
    B9 = visualisation, B10 = cross-validation, B11 = feature importance,
    B12 = reflection / markdown commentary.

    Args:
        params (StudentInput): student_id — student pseudonym.

    Returns:
        str: JSON content of data_sources_2026/homework_scores/<student_id>_homework_score.json.

        Error: "Error: Homework score not found for <student_id>."
    """
    path = HOMEWORK_DIR / f"{params.student_id}_homework_score.json"
    if not path.exists():
        return _err(
            f"Homework score not found for '{params.student_id}'. "
            "Expected: data_sources_2026/homework_scores/"
            f"{params.student_id}_homework_score.json"
        )
    try:
        return _fmt_json(_load_json(path))
    except Exception as e:
        return _err(f"Failed to read homework score: {e}")


@mcp.tool(
    name="aicft_get_colab_notebook_summary",
    annotations={
        "title": "Get Student Colab Notebook Summary",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_get_colab_notebook_summary(params: StudentInput) -> str:
    """Summarise a student's Final Ödev (Colab Python) notebook.

    Extracts cell types, source text (truncated per cell), output types, and
    execution counts without running the notebook.  Use aicft_get_homework_scores
    for the scored behavioural indicators; use this tool to inspect the raw
    notebook content directly.

    Args:
        params (StudentInput): student_id — student pseudonym.

    Returns:
        str: JSON summary:
        {
          "student_id": str,
          "cell_count": int,
          "cells": [
            {
              "index": int,
              "cell_type": "code" | "markdown",
              "execution_count": int | null,
              "source_preview": str,   # first 400 chars of source
              "output_types": [str],   # e.g. ["stream", "display_data"]
              "has_error": bool
            }
          ]
        }
    """
    path = COLAB_DIR / f"{params.student_id}.ipynb"
    if not path.exists():
        return _err(
            f"Colab notebook not found for '{params.student_id}'. "
            f"Expected: {COLAB_DIR}/{params.student_id}.ipynb"
        )
    try:
        nb = _load_json(path)
    except Exception as e:
        return _err(f"Failed to parse notebook: {e}")

    cells_raw = nb.get("cells", [])
    cells_summary = []
    for i, cell in enumerate(cells_raw):
        source = "".join(cell.get("source", []))
        outputs = cell.get("outputs", [])
        has_error = any(o.get("output_type") == "error" for o in outputs)
        cells_summary.append(
            {
                "index": i,
                "cell_type": cell.get("cell_type", "unknown"),
                "execution_count": cell.get("execution_count"),
                "source_preview": source[:400] + ("…" if len(source) > 400 else ""),
                "output_types": [o.get("output_type", "") for o in outputs],
                "has_error": has_error,
            }
        )

    return _fmt_json(
        {
            "student_id": params.student_id,
            "notebook_format": nb.get("nbformat"),
            "cell_count": len(cells_raw),
            "cells": cells_summary,
        }
    )


@mcp.tool(
    name="aicft_get_log_features",
    annotations={
        "title": "Extract CODAP Log Behavioral Features",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_get_log_features(params: LogFeaturesInput) -> str:
    """List and summarise CODAP Arbor log files available for a student.

    The CODAP log files (.codap) record all in-tool actions: feature selections,
    threshold changes, tree emits, accuracy snapshots, dataset switches.  This
    tool reports which log files exist and their basic metadata (file size,
    modification time).  To run the full LogDerivedFeatures extraction pipeline
    (exploration_index, emit_count, accuracy trajectory, etc.) execute:

        python log_extractor.py <path_to_codap_file>

    from the repository root.

    Args:
        params (LogFeaturesInput):
            - student_id (str): student pseudonym
            - session (str): '21april' or '28april'

    Returns:
        str: JSON:
        {
          "student_id": str,
          "session": str,
          "log_files": [
            {
              "filename": str,
              "path": str,
              "size_bytes": int,
              "modified_at": str
            }
          ],
          "note": str   # guidance on running log_extractor
        }

        Error: "Error: No CODAP log files found for <student_id> in <session>."
    """
    log_dir = LOGS_21APR if params.session == "21april" else LOGS_28APR
    if not log_dir.exists():
        return _err(
            f"Log directory does not exist: {log_dir}. "
            "Check AICFT_REPO environment variable."
        )

    # Match case-insensitively (student pseudonym vs. filename)
    name_lower = params.student_id.lower()
    matches = [
        p for p in log_dir.iterdir()
        if p.suffix == ".codap" and name_lower in p.name.lower()
    ]
    if not matches:
        return _err(
            f"No CODAP log files found for '{params.student_id}' in session "
            f"'{params.session}'. "
            f"Available files: {[p.name for p in log_dir.glob('*.codap')]}"
        )

    import datetime

    files_info = []
    for p in sorted(matches):
        stat = p.stat()
        files_info.append(
            {
                "filename": p.name,
                "path": str(p),
                "size_bytes": stat.st_size,
                "modified_at": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )

    return _fmt_json(
        {
            "student_id": params.student_id,
            "session": params.session,
            "log_files": files_info,
            "note": (
                "To extract full LogDerivedFeatures (exploration_index, emit_count, "
                "accuracy_trajectory, feature_selection_counts, etc.) run: "
                f"python log_extractor.py <path> from {REPO_ROOT}"
            ),
        }
    )


@mcp.tool(
    name="aicft_get_behavior_signals",
    annotations={
        "title": "Get Screen Recording Behavior Signal Guide",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_get_behavior_signals(params: StudentInput) -> str:
    """Return screen-recording inventory and behavior-signal coding guide for a student.

    Reports which screen recordings exist for the student across all three
    sessions (21 April CODAP, 28 April CODAP, 5 May Colab), and returns the
    full behavior signal guide (17 signal types) that must be applied during
    manual or AI-assisted frame coding.

    Args:
        params (StudentInput): student_id — student pseudonym.

    Returns:
        str: JSON:
        {
          "student_id": str,
          "recordings": {
            "21april_codap": { "found": bool, "filename": str | null, "size_mb": float | null },
            "28april_codap": { "found": bool, "filename": str | null, "size_mb": float | null },
            "colab_may":     { "found": bool, "filename": str | null, "size_mb": float | null }
          },
          "behavior_guide_excerpt": str   # first 3000 chars of the coding guide
        }
    """
    def _rec_info(directory: Path) -> Dict[str, Any]:
        if not directory.exists():
            return {"found": False, "filename": None, "size_mb": None}
        name_lower = params.student_id.lower()
        matches = [
            p for p in directory.iterdir()
            if p.suffix == ".webm" and name_lower in p.stem.lower()
        ]
        if not matches:
            return {"found": False, "filename": None, "size_mb": None}
        p = matches[0]
        return {
            "found": True,
            "filename": p.name,
            "size_mb": round(p.stat().st_size / 1_048_576, 2),
        }

    guide_excerpt = ""
    if BEHAVIOR_GUIDE.exists():
        raw = BEHAVIOR_GUIDE.read_text(encoding="utf-8")
        guide_excerpt = raw[:3000] + ("…" if len(raw) > 3000 else "")

    return _fmt_json(
        {
            "student_id": params.student_id,
            "recordings": {
                "21april_codap": _rec_info(RECORDINGS_21APR),
                "28april_codap": _rec_info(RECORDINGS_28APR),
                "colab_may": _rec_info(RECORDINGS_MAY),
            },
            "behavior_guide_excerpt": guide_excerpt,
        }
    )


@mcp.tool(
    name="aicft_get_cohort_summary",
    annotations={
        "title": "Get 2026 Cohort AI-CFT Summary",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_get_cohort_summary() -> str:
    """Summarise AI-CFT competency evidence across all 2026 cohort students.

    Aggregates portfolio data for every student who has a portfolio.json, and
    reports per-student, per-LO evidence counts and data gaps.  Students with
    no portfolio are listed as pending.

    Returns:
        str: JSON:
        {
          "cohort_year": 2026,
          "total_students": int,
          "students_with_portfolio": int,
          "students_pending": [str],
          "per_student": {
            "<student_id>": {
              "worksheets_scored": [str],
              "lo_evidence_counts": { "<LO>": int },
              "data_gap_count": int
            }
          }
        }
    """
    students = _all_students()
    summary: Dict[str, Any] = {
        "cohort_year": 2026,
        "total_students": len(students),
        "students_with_portfolio": 0,
        "students_pending": [],
        "per_student": {},
    }

    for sid in students:
        path = _student_dir(sid) / "portfolio.json"
        if not path.exists():
            summary["students_pending"].append(sid)
            continue
        try:
            pf = _load_json(path)
        except Exception:
            summary["students_pending"].append(sid)
            continue

        summary["students_with_portfolio"] += 1
        ev_by_lo = pf.get("evidence_by_lo", {})
        summary["per_student"][sid] = {
            "worksheets_scored": pf.get("worksheets_scored", []),
            "lo_evidence_counts": {lo: len(ev) for lo, ev in ev_by_lo.items()},
            "data_gap_count": len(pf.get("data_gaps", [])),
        }

    return _fmt_json(summary)


@mcp.tool(
    name="aicft_search_evidence",
    annotations={
        "title": "Search AI-CFT Evidence",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_search_evidence(params: EvidenceSearchInput) -> str:
    """Search AI-CFT evidence packets across students and Learning Outcomes.

    Scans portfolio.json files for evidence matching the given filters.
    All filters are optional — omitting all returns a cross-cohort index.

    Args:
        params (EvidenceSearchInput):
            - lo_id (Optional[str]): e.g. 'LO3.2.2' — filter by LO
            - student_id (Optional[str]): filter to one student
            - keyword (Optional[str]): case-insensitive text match in evidence

    Returns:
        str: JSON list of matches:
        [
          {
            "student_id": str,
            "lo_id": str,
            "evidence_items": [str]   # matched evidence excerpts
          }
        ]

        Error: "Error: No evidence found matching the given filters."
    """
    students = (
        [params.student_id]
        if params.student_id
        else _all_students()
    )

    matches = []
    keyword_lower = params.keyword.lower() if params.keyword else None

    for sid in students:
        path = _student_dir(sid) / "portfolio.json"
        if not path.exists():
            continue
        try:
            pf = _load_json(path)
        except Exception:
            continue

        ev_by_lo: Dict[str, Any] = pf.get("evidence_by_lo", {})

        for lo, ev_items in ev_by_lo.items():
            if params.lo_id and lo != params.lo_id:
                continue

            # ev_items may be a list of strings or dicts
            texts: List[str] = []
            for item in (ev_items if isinstance(ev_items, list) else []):
                texts.append(item if isinstance(item, str) else json.dumps(item))

            if keyword_lower:
                texts = [t for t in texts if keyword_lower in t.lower()]

            if texts:
                matches.append(
                    {"student_id": sid, "lo_id": lo, "evidence_items": texts}
                )

    if not matches:
        return _err(
            "No evidence found matching the given filters. "
            "Try relaxing lo_id, student_id, or keyword filters."
        )
    return _fmt_json(matches)


@mcp.tool(
    name="aicft_get_rubric_gaps",
    annotations={
        "title": "Get 2026 Cohort Rubric Gaps",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_get_rubric_gaps() -> str:
    """Return the rubric gap analysis for the 2026 cohort.

    The rubric_gaps_2026.json file records items where the current rubric
    or extraction pipeline cannot reliably assign AI-CFT evidence — e.g.
    items that are ambiguous, require human review, or have no LO mapping.

    Returns:
        str: JSON content of data_sources_2026/rubric_gaps_2026.json.

        Error: "Error: rubric_gaps_2026.json not found."
    """
    if not RUBRIC_GAPS.exists():
        return _err(
            "rubric_gaps_2026.json not found at "
            f"{RUBRIC_GAPS}. Check AICFT_REPO environment variable."
        )
    try:
        return _fmt_json(_load_json(RUBRIC_GAPS))
    except Exception as e:
        return _err(f"Failed to read rubric gaps: {e}")


@mcp.tool(
    name="aicft_get_framework",
    annotations={
        "title": "Get AI-CFT Assessment Framework",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_get_framework() -> str:
    """Return the canonical AI-CFT (UNESCO AI Competency Framework for Teachers) mapping.

    Contains: competency definitions, LO→worksheet profiles, item→competency
    priors with rationale, and scoring mode metadata.  This is the authoritative
    source used by all pipeline scoring modules.

    Returns:
        str: JSON content of mappings/AICFT_assessment_framework.json.

        Error: "Error: Framework file not found."
    """
    if not FRAMEWORK.exists():
        return _err(
            f"Framework not found at {FRAMEWORK}. "
            "Run: python scripts/build_aicft_framework.py"
        )
    try:
        return _fmt_json(_load_json(FRAMEWORK))
    except Exception as e:
        return _err(f"Failed to read framework: {e}")


@mcp.tool(
    name="aicft_get_evidence_units",
    annotations={
        "title": "Get Student Evidence Units",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def aicft_get_evidence_units(params: StudentInput) -> str:
    """Retrieve the consolidated evidence_units.json for a student.

    Evidence units are the normalised, cross-worksheet evidence records that
    feed the portfolio builder.  Each unit links a scored item to its LO,
    competency level indicator, and source worksheet.

    Args:
        params (StudentInput): student_id — student pseudonym.

    Returns:
        str: JSON content of students/<student_id>/evidence_units.json.

        Error: "Error: evidence_units.json not found for <student_id>."
    """
    path = _student_dir(params.student_id) / "evidence_units.json"
    if not path.exists():
        return _err(
            f"evidence_units.json not found for '{params.student_id}'. "
            "Run: python scripts/build_evidence_units.py " + params.student_id
        )
    try:
        return _fmt_json(_load_json(path))
    except Exception as e:
        return _err(f"Failed to read evidence units: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
