#!/usr/bin/env bash
# Remove user-immutable flag from protected research folders (macOS only).
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROTECTED_DIRS=(data_sources_2025 data_sources_2026 answer_key_worksheets)

for dir in "${PROTECTED_DIRS[@]}"; do
  target="${REPO_ROOT}/${dir}"
  [[ -d "$target" ]] || continue
  echo "Unfreezing ${target} ..."
  if [[ -f "${target}/.FROZEN" ]]; then
    chflags nouchg "${target}/.FROZEN" 2>/dev/null || true
    chflags nouchg "${target}" 2>/dev/null || true
    rm -f "${target}/.FROZEN" 2>/dev/null || true
  fi
  chflags -R nouchg "$target" 2>/dev/null || true
done

echo "Done. You can now add or replace files; re-run freeze_data_sources.sh when finished."
