"""
Batch extraction script for FINAL_LIZARD notebooks.

Usage:
    python scripts/run_final_lizard_extraction.py [STUDENT ...]

If no student names are given, runs for all students who do not yet have
an extracted JSON.

Output: worksheets/FINAL_LIZARD/example_extracted_{student}.json

Requires:
    pip install anthropic jsonschema
    ANTHROPIC_API_KEY env var set
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import anthropic
import jsonschema

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
NOTEBOOKS_DIR = ROOT / "data_sources_2026" / "Final Ödevi Dokümanları"
SCHEMA_PATH   = ROOT / "worksheets" / "FINAL_LIZARD" / "extraction_schema.json"
PROMPT_PATH   = ROOT / "worksheets" / "FINAL_LIZARD" / "extraction_prompt.md"
OUT_DIR       = ROOT / "worksheets" / "FINAL_LIZARD"

MODEL = "claude-sonnet-5"   # structured extraction
MAX_TOKENS = 20000


# ---------------------------------------------------------------------------
# Notebook → text
# ---------------------------------------------------------------------------

def _output_text(output: dict) -> str:
    if output.get("output_type") == "stream":
        return "".join(output.get("text", []))
    if output.get("output_type") in ("execute_result", "display_data"):
        data = output.get("data", {})
        if "text/plain" in data:
            return "".join(data["text/plain"])
    if output.get("output_type") == "error":
        return f"ERROR: {output.get('ename','')}: {output.get('evalue','')}"
    return ""


def notebook_to_text(nb_path: Path, student_id: str) -> str:
    with open(nb_path, encoding="utf-8") as f:
        nb = json.load(f)

    lines = [f"FILENAME: {student_id}.ipynb\n"]

    for i, cell in enumerate(nb["cells"], 1):
        src = "".join(cell["source"]).strip()
        ctype = cell["cell_type"]

        if ctype == "markdown":
            if src:
                lines.append(f"[MARKDOWN cell {i}]\n{src}")

        elif ctype == "code":
            if src:
                lines.append(f"[CODE cell {i}]\n{src}")
            outputs = cell.get("outputs", [])
            out_parts = [_output_text(o) for o in outputs]
            combined = "\n".join(p for p in out_parts if p).strip()
            if combined:
                lines.append(f"[OUTPUT cell {i}]\n{combined}")

    return "\n\n".join(lines)


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def extract_student(client: anthropic.Anthropic, student_id: str,
                    notebook_text: str, prompt: str, schema: dict) -> dict:
    schema_str = json.dumps(schema, ensure_ascii=False, indent=2)

    system_msg = (
        prompt
        + "\n\n---\n\n## Schema\n\n```json\n"
        + schema_str
        + "\n```"
    )

    user_msg = (
        f"Extract structured data from the following notebook.\n\n"
        f"student_id: {student_id}\n\n"
        + notebook_text
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "disabled"},
        system=system_msg,
        messages=[{"role": "user", "content": user_msg}],
    )

    # Sonnet 5 may return thinking blocks before the text block
    text_block = next((b for b in response.content if hasattr(b, "text")), None)
    if text_block is None:
        types = [type(b).__name__ for b in response.content]
        raise ValueError(f"No text block in API response. Block types: {types}. stop_reason={response.stop_reason}")
    text = text_block.text.strip()

    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()

    return json.loads(text)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(data: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema)
    errors = [e.message + f" @ {list(e.absolute_path)}" for e in validator.iter_errors(data)]
    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def all_students() -> list[str]:
    return sorted(p.stem for p in NOTEBOOKS_DIR.glob("*.ipynb"))


def already_done() -> set[str]:
    done = set()
    for p in OUT_DIR.glob("example_extracted_*.json"):
        done.add(p.stem.replace("example_extracted_", ""))
    return done


def main():
    parser = argparse.ArgumentParser(description="Extract FINAL_LIZARD notebooks via Claude API")
    parser.add_argument("students", nargs="*", help="Student pseudonyms (default: all pending)")
    parser.add_argument("--force", action="store_true", help="Re-extract even if output exists")
    parser.add_argument("--dry-run", action="store_true", help="Print notebook text only, no API call")
    args = parser.parse_args()

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    with open(SCHEMA_PATH) as f:
        schema = json.load(f)

    students = args.students or all_students()
    done = already_done() if not args.force else set()
    pending = [s for s in students if s not in done]

    if not pending:
        print("All students already extracted. Use --force to re-run.")
        return

    print(f"Pending: {pending}")

    if args.dry_run:
        for student_id in pending[:1]:
            nb_path = NOTEBOOKS_DIR / f"{student_id}.ipynb"
            if not nb_path.exists():
                print(f"  SKIP {student_id}: notebook not found")
                continue
            text = notebook_to_text(nb_path, student_id)
            print(f"\n--- {student_id} notebook text ({len(text)} chars) ---")
            print(text[:3000])
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    for student_id in pending:
        nb_path = NOTEBOOKS_DIR / f"{student_id}.ipynb"
        out_path = OUT_DIR / f"example_extracted_{student_id}.json"

        if not nb_path.exists():
            print(f"[SKIP] {student_id}: {nb_path} not found")
            continue

        print(f"\n[{student_id}] Reading notebook ...", flush=True)
        notebook_text = notebook_to_text(nb_path, student_id)
        print(f"[{student_id}] {len(notebook_text)} chars → calling API ...", flush=True)

        try:
            data = extract_student(client, student_id, notebook_text, prompt, schema)
        except json.JSONDecodeError as e:
            print(f"[{student_id}] ERROR: API returned invalid JSON: {e}", file=sys.stderr)
            continue
        except Exception as e:
            print(f"[{student_id}] ERROR: {e}", file=sys.stderr)
            continue

        errors = validate(data, schema)
        if errors:
            print(f"[{student_id}] WARNING: {len(errors)} validation error(s):")
            for err in errors[:5]:
                print(f"  - {err}")
        else:
            print(f"[{student_id}] VALID")

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[{student_id}] Saved → {out_path.relative_to(ROOT)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
