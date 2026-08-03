#!/usr/bin/env bash
# Canlı extraction ilerleme paneli
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
exec "$ROOT/.venv-hybrid/bin/python" -u scripts/watch_extraction_progress.py "$@"
