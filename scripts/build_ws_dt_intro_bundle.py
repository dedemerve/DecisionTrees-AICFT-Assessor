#!/usr/bin/env python3
"""Deprecated — use scripts/build_ws_dt_codap_bundles.py (WS13 + WS14)."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main() -> int:
    log.warning(
        "WS_DT_INTRO bundle is deprecated. Building WS13 + WS14 instead."
    )
    from build_ws_dt_codap_bundles import main as build_codap  # noqa: E402

    return build_codap()


if __name__ == "__main__":
    raise SystemExit(main())
