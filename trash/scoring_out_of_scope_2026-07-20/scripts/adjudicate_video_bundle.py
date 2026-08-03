#!/usr/bin/env python3
"""Assemble expert adjudication prompts for a student's video analysis bundle.

Does not call an LLM by default — writes a ready-to-send prompt package:
  training_datasets/<cohort>/<id>/<id>_adjudication_prompt.json

Optional: --invoke-anthropic runs Claude with the system prompt and saves
  <id>_adjudication_report.json

Usage:
  python scripts/adjudicate_video_bundle.py Ally
  python scripts/adjudicate_video_bundle.py --all-2025
  python scripts/adjudicate_video_bundle.py Ally --invoke-anthropic
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
SYSTEM_PROMPT_PATH = REPO / "framework" / "prompts" / "video_bundle_adjudication_system.md"
USER_TEMPLATE_PATH = REPO / "framework" / "prompts" / "video_bundle_adjudication_user.template.md"
OUT_2025 = REPO / "training_datasets" / "2025"

REQUIRED_ARTIFACTS = (
    "construct_scores",
    "expert_process_narrative",
    "video_analysis_bundle",
)
OPTIONAL_ARTIFACTS = (
    "process_codes",
    "log_process_metadata",
)

FILENAME_MAP = {
    "construct_scores": "{id}_construct_scores.json",
    "expert_process_narrative": "{id}_expert_process_narrative.json",
    "video_analysis_bundle": "{id}_video_analysis_bundle.json",
    "process_codes": "{id}_process_codes.json",
    "log_process_metadata": "{id}_log_process_metadata.json",
}


def load_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".md" and text.startswith("#"):
        parts = text.split("---\n", 1)
        return parts[1].strip() if len(parts) > 1 else text
    return text


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def compact_narrative(doc: dict[str, Any], *, max_steps: int | None = None) -> dict[str, Any]:
    """Optional trim for very long timelines when sending to LLM."""
    if max_steps is None:
        return doc
    out = dict(doc)
    timeline = list(doc.get("timeline") or [])
    if len(timeline) > max_steps:
        out["timeline"] = timeline[:max_steps]
        out["_truncated"] = {
            "timeline_total": len(timeline),
            "timeline_included": max_steps,
            "note": "Uzun timeline kısaltıldı; tam dosya diskte mevcut.",
        }
    return out


def artifact_paths(student_dir: Path, student_id: str) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for key, pattern in FILENAME_MAP.items():
        p = student_dir / pattern.format(id=student_id)
        if p.is_file():
            paths[key] = p
    return paths


def build_user_message(
    student_id: str,
    cohort_year: int,
    paths: dict[str, Path],
    *,
    max_narrative_steps: int | None = None,
) -> str:
    template = load_text(USER_TEMPLATE_PATH)
    payloads: dict[str, str] = {}

    for key in REQUIRED_ARTIFACTS + OPTIONAL_ARTIFACTS:
        if key not in paths:
            payloads[key] = "null"
            continue
        doc = load_json(paths[key])
        if key == "expert_process_narrative":
            doc = compact_narrative(doc, max_steps=max_narrative_steps)
        payloads[key] = json.dumps(doc, ensure_ascii=False, indent=2)

    replacements = {
        "STUDENT_ID": student_id,
        "COHORT_YEAR": str(cohort_year),
        "CONSTRUCT_SCORES_JSON": payloads["construct_scores"],
        "EXPERT_PROCESS_NARRATIVE_JSON": payloads["expert_process_narrative"],
        "VIDEO_ANALYSIS_BUNDLE_JSON": payloads["video_analysis_bundle"],
        "PROCESS_CODES_JSON": payloads.get("process_codes", "null"),
        "LOG_PROCESS_METADATA_JSON": payloads.get("log_process_metadata", "null"),
    }
    out = template
    for k, v in replacements.items():
        out = out.replace("{{" + k + "}}", v)
    return out


def build_prompt_package(
    student_id: str,
    cohort_year: int,
    student_dir: Path,
    *,
    max_narrative_steps: int | None = None,
) -> dict[str, Any]:
    paths = artifact_paths(student_dir, student_id)
    missing = [k for k in REQUIRED_ARTIFACTS if k not in paths]
    if missing:
        raise FileNotFoundError(
            f"[{student_id}] missing required artifacts: {', '.join(missing)}"
        )

    system_prompt = load_text(SYSTEM_PROMPT_PATH)
    user_message = build_user_message(
        student_id,
        cohort_year,
        paths,
        max_narrative_steps=max_narrative_steps,
    )

    return {
        "$schema": "schema/video_bundle_adjudication.schema.json",
        "prompt_package_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "student_id": student_id,
        "cohort_year": cohort_year,
        "system_prompt": system_prompt,
        "user_message": user_message,
        "output_schema": "schema/video_bundle_adjudication.schema.json",
        "source_artifacts": {k: str(paths[k].name) for k in sorted(paths)},
        "instructions": (
            "Send system_prompt as system message and user_message as user message. "
            "Model response must be a single JSON object matching video_bundle_adjudication.schema.json."
        ),
    }


def parse_json_response(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    return json.loads(text)


def invoke_anthropic(system_prompt: str, user_message: str) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError("pip install anthropic required for --invoke-anthropic") from exc

    client = anthropic.Anthropic(api_key=api_key)
    model = os.environ.get("ADJUDICATION_MODEL", "claude-sonnet-4-20250514")
    msg = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    parts = [b.text for b in msg.content if hasattr(b, "text")]
    return "\n".join(parts)


def process_student(
    student_id: str,
    cohort_year: int,
    student_dir: Path,
    *,
    invoke: bool = False,
    max_narrative_steps: int | None = None,
) -> dict[str, Any]:
    package = build_prompt_package(
        student_id,
        cohort_year,
        student_dir,
        max_narrative_steps=max_narrative_steps,
    )
    prompt_path = student_dir / f"{student_id}_adjudication_prompt.json"
    write_json(prompt_path, package)

    result: dict[str, Any] = {
        "student_id": student_id,
        "status": "prompt_ready",
        "prompt_path": str(prompt_path),
    }

    if invoke:
        raw = invoke_anthropic(package["system_prompt"], package["user_message"])
        report = parse_json_response(raw)
        report_path = student_dir / f"{student_id}_adjudication_report.json"
        write_json(report_path, report)
        result["status"] = "adjudicated"
        result["report_path"] = str(report_path)

    return result


def list_2025_students() -> list[str]:
    if not OUT_2025.is_dir():
        return []
    return sorted(
        p.name
        for p in OUT_2025.iterdir()
        if p.is_dir() and (p / f"{p.name}_video_analysis_bundle.json").is_file()
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Build expert adjudication prompt packages")
    ap.add_argument("students", nargs="*", help="Student IDs")
    ap.add_argument("--all-2025", action="store_true")
    ap.add_argument("--invoke-anthropic", action="store_true", help="Call Claude API")
    ap.add_argument(
        "--max-narrative-steps",
        type=int,
        default=None,
        help="Truncate timeline for LLM context (default: full)",
    )
    args = ap.parse_args()

    students = list_2025_students() if args.all_2025 else args.students
    if not students:
        ap.error("Provide student IDs or --all-2025")

    ok = 0
    for sid in students:
        student_dir = OUT_2025 / sid
        try:
            result = process_student(
                sid,
                2025,
                student_dir,
                invoke=args.invoke_anthropic,
                max_narrative_steps=args.max_narrative_steps,
            )
            print(f"[{sid}] {result['status']} -> {result['prompt_path']}")
            if result.get("report_path"):
                print(f"         report -> {result['report_path']}")
            ok += 1
        except Exception as exc:
            print(f"[{sid}] ERROR: {exc}", file=sys.stderr)

    print(f"Done {ok}/{len(students)}")


if __name__ == "__main__":
    main()
