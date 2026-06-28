#!/usr/bin/env python3
"""Remove schema_version from all JSON data files in the repository."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKIP_PARTS = {".git", "node_modules", "__pycache__", ".cursor"}


def _strip(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in obj.items() if k != "schema_version"}
    if isinstance(obj, list):
        return [_strip(v) for v in obj]
    return obj


def _strip_schema_file(path: Path) -> bool:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "schema_version" not in data.get("required", []):
        props = data.get("properties", {})
        if "schema_version" not in props:
            return False
    req = [k for k in data.get("required", []) if k != "schema_version"]
    if req:
        data["required"] = req
    elif "required" in data:
        del data["required"]
    props = dict(data.get("properties", {}))
    props.pop("schema_version", None)
    if props:
        data["properties"] = props
    elif "properties" in data:
        del data["properties"]
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    for path in sorted(REPO_ROOT.rglob("*.json")):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if path.parts[-2:-1] == ("schema",) or path.parent.name == "schema":
            if _strip_schema_file(path):
                changed += 1
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        cleaned = _strip(data)
        if cleaned != data:
            path.write_text(json.dumps(cleaned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            changed += 1
    print(f"Stripped schema_version from {changed} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
