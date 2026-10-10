#!/usr/bin/env python3
"""Renumber WS15 rubric items DTI_34–80 → DTI_01–47 (single pass)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "worksheets" / "WS15" / "rubric.json"
TARGET = REPO_ROOT / "rubrics" / "WS15_rubric.json"

OLD_MIN, OLD_MAX = 34, 80


def old_to_new_num(n: int) -> int | None:
    if OLD_MIN <= n <= OLD_MAX:
        return n - 33
    return None


def old_to_new_id(old_id: str) -> str:
    m = re.fullmatch(r"DTI_(\d+)", old_id)
    if not m:
        return old_id
    new_n = old_to_new_num(int(m.group(1)))
    return f"DTI_{new_n:02d}" if new_n is not None else old_id


def rekey_text(s: str) -> str:
    def repl_range(m: re.Match[str]) -> str:
        start, end = int(m.group(1)), int(m.group(2))
        ns, ne = old_to_new_num(start), old_to_new_num(end)
        if ns is not None and ne is not None:
            sep = m.group(0)[len(f"DTI_{m.group(1)}") : len(f"DTI_{m.group(1)}") + 1]
            if m.group(0).lstrip().startswith("DTI_") and "DTI_" in m.group(0)[m.group(0).find(sep) :]:
                return f"DTI_{ns:02d}{sep}DTI_{ne:02d}"
            return f"DTI_{ns:02d}{sep}{ne:02d}"
        return m.group(0)

    s = re.sub(r"DTI_(\d+)\s*[–-]\s*DTI_(\d+)", repl_range, s)
    s = re.sub(r"DTI_(\d+)\s*[–-]\s*(\d+)", repl_range, s)

    def repl_id(m: re.Match[str]) -> str:
        new_n = old_to_new_num(int(m.group(1)))
        return f"DTI_{new_n:02d}" if new_n is not None else m.group(0)

    return re.sub(r"DTI_(\d+)", repl_id, s)


def rekey_dict_keys(d: dict[str, Any]) -> dict[str, Any]:
    return {old_to_new_id(k) if re.fullmatch(r"DTI_\d+", k) else k: v for k, v in d.items()}


def rekey_value(val: Any) -> Any:
    if isinstance(val, dict):
        return {k: rekey_value(v) for k, v in val.items()}
    if isinstance(val, list):
        if val and all(isinstance(x, str) and re.fullmatch(r"DTI_\d+", x) for x in val):
            return [old_to_new_id(x) for x in val]
        return [rekey_value(x) for x in val]
    if isinstance(val, str):
        return rekey_text(val)
    return val


def renumber_rubric(rubric: dict[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(rubric))
    out["items"] = {
        old_to_new_id(old_id): rekey_value(item)
        for old_id, item in rubric["items"].items()
    }
    out["metadata"] = rekey_value(rubric["metadata"])
    out["metadata"]["item_range"] = "DTI_01 – DTI_47"
    out["scoring_policy"] = rekey_value(rubric["scoring_policy"])
    if "validation_schema" in out:
        out["validation_schema"] = rekey_value(rubric["validation_schema"])
    if "gold_standard" in out:
        gs = dict(rubric["gold_standard"])
        gs["ws_snapshot"] = rekey_text(gs.get("ws_snapshot", ""))
        gs["page_notes"] = rekey_text(gs.get("page_notes", ""))
        if "extraction" in gs:
            gs["extraction"] = rekey_dict_keys(gs["extraction"])
        if "validation" in gs and "item_checks" in gs["validation"]:
            gs["validation"]["item_checks"] = rekey_dict_keys(gs["validation"]["item_checks"])
        if "validation" in gs and "system_analytical_summary" in gs["validation"]:
            gs["validation"]["system_analytical_summary"] = rekey_text(
                gs["validation"]["system_analytical_summary"]
            )
        out["gold_standard"] = gs
    return out


def main() -> int:
    rubric = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert len(rubric["items"]) == 47
    renumbered = renumber_rubric(rubric)
    assert len(renumbered["items"]) == 47
    assert set(renumbered["items"]) == {f"DTI_{i:02d}" for i in range(1, 48)}
    traps = renumbered["scoring_policy"]["regimes"]["interpretive"]["trap_questions"]
    assert set(traps) == {"DTI_43", "DTI_44"}, traps
    assert "DTI_32-DTI_40" in renumbered["metadata"]["structure"][4]
    TARGET.write_text(
        json.dumps(renumbered, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {TARGET} with {len(renumbered['items'])} items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
