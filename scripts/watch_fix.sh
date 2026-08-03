#!/usr/bin/env bash
# Fix job için anlaşılır canlı panel (fix_gate_failures.log yerine bunu kullan)
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec "$ROOT/.venv-hybrid/bin/python" -u scripts/watch_fix_progress.py "$@"
