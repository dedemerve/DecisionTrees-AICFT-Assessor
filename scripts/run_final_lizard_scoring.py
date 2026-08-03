"""
Batch scoring script for FINAL_LIZARD extracted JSONs.

Usage:
    python scripts/run_final_lizard_scoring.py [STUDENT ...]

If no student names given, runs for all students who have an extraction JSON
but no scoring output yet.

Output: worksheets/FINAL_LIZARD/scoring_output_{student}.json

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

ROOT         = Path(__file__).parent.parent
WS_DIR       = ROOT / "worksheets" / "FINAL_LIZARD"
SCORING_SCHEMA_PATH = WS_DIR / "scoring_schema.json"
SCORING_PROMPT_PATH = WS_DIR / "scoring_prompt.md"
ISABEL_EXAMPLE_PATH = WS_DIR / "scoring_output_Isabel.json"

MODEL      = "claude-sonnet-5"
MAX_TOKENS = 16000


def score_student(client: anthropic.Anthropic, student_id: str,
                  extraction: dict, prompt: str,
                  scoring_schema: dict, isabel_example: dict) -> dict:

    extraction_str    = json.dumps(extraction, ensure_ascii=False, indent=2)
    schema_str        = json.dumps(scoring_schema, ensure_ascii=False, indent=2)
    isabel_str        = json.dumps(isabel_example, ensure_ascii=False, indent=2)

    system_msg = (
        prompt
        + "\n\n---\n\n## Scoring Schema\n\n```json\n" + schema_str + "\n```"
        + "\n\n---\n\n## Reference Example (Isabel's scoring output)\n\n```json\n" + isabel_str + "\n```"
    )

    user_msg = (
        f"Score the following student extraction.\n\n"
        f"student_id: {student_id}\n\n"
        f"```json\n{extraction_str}\n```"
    )

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        thinking={"type": "disabled"},
        system=system_msg,
        messages=[{"role": "user", "content": user_msg}],
    )

    text_block = next((b for b in response.content if hasattr(b, "text")), None)
    if text_block is None:
        types = [type(b).__name__ for b in response.content]
        raise ValueError(f"No text block in response. Types: {types}. stop_reason={response.stop_reason}")

    text = text_block.text.strip()
    # Strip markdown fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    # If model returned prose before the JSON object, find the first {
    if not text.startswith("{"):
        idx = text.find("{")
        if idx != -1:
            text = text[idx:]
    if not text:
        raise ValueError(f"API returned empty text. stop_reason={response.stop_reason}")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}\nRaw (first 300): {text[:300]!r}") from e


def validate(data: dict, schema: dict) -> list[str]:
    validator = jsonschema.Draft7Validator(schema)
    return [e.message + f" @ {list(e.absolute_path)}" for e in validator.iter_errors(data)]


def extracted_students() -> list[str]:
    return sorted(p.stem.replace("example_extracted_", "")
                  for p in WS_DIR.glob("example_extracted_*.json"))


def scored_students() -> set[str]:
    return {p.stem.replace("scoring_output_", "")
            for p in WS_DIR.glob("scoring_output_*.json")}


def main():
    parser = argparse.ArgumentParser(description="Score FINAL_LIZARD extractions via Claude API")
    parser.add_argument("students", nargs="*", help="Student pseudonyms (default: all pending)")
    parser.add_argument("--force", action="store_true", help="Re-score even if output exists")
    args = parser.parse_args()

    prompt         = SCORING_PROMPT_PATH.read_text(encoding="utf-8")
    with open(SCORING_SCHEMA_PATH) as f:
        scoring_schema = json.load(f)
    with open(ISABEL_EXAMPLE_PATH) as f:
        isabel_example = json.load(f)

    all_extracted = extracted_students()
    already_done  = scored_students() if not args.force else set()
    candidates    = args.students or all_extracted
    pending       = [s for s in candidates if s not in already_done]

    if not pending:
        print("All students already scored. Use --force to re-run.")
        return

    print(f"Pending: {pending}")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set.", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    for student_id in pending:
        extraction_path = WS_DIR / f"example_extracted_{student_id}.json"
        out_path        = WS_DIR / f"scoring_output_{student_id}.json"

        if not extraction_path.exists():
            print(f"[SKIP] {student_id}: no extraction file found")
            continue

        with open(extraction_path, encoding="utf-8") as f:
            extraction = json.load(f)

        print(f"\n[{student_id}] Calling API ...", flush=True)

        try:
            data = score_student(client, student_id, extraction,
                                 prompt, scoring_schema, isabel_example)
        except Exception as e:
            print(f"[{student_id}] ERROR: {e}", file=sys.stderr)
            continue

        errors = validate(data, scoring_schema)
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
