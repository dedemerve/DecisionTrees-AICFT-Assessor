#!/usr/bin/env python3
"""
validate_schemas.py — Run JSON Schema validation across bundles, framework, and mappings.

  python validate_schemas.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from schema_json_validate import (  # noqa: E402
    validate_all_mappings_jsonschema,
    validate_all_schemas_wellformed,
    validate_all_worksheet_bundles_jsonschema,
    validate_framework_jsonschema,
)
from worksheet_bundle_data import BUNDLE_WORKSHEETS  # noqa: E402


def main() -> int:
    errors: list[str] = []
    errors.extend(validate_all_schemas_wellformed())
    errors.extend(validate_all_worksheet_bundles_jsonschema(BUNDLE_WORKSHEETS))
    errors.extend(validate_all_mappings_jsonschema())
    errors.extend(validate_framework_jsonschema())

    if errors:
        print(f"JSON Schema validation failed ({len(errors)} issues):\n", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(
        f"JSON Schema validation passed "
        f"({len(BUNDLE_WORKSHEETS)} bundles, mappings)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
