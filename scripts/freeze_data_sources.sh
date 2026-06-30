#!/usr/bin/env bash
# Freeze protected research data folders (macOS user-immutable flag).
# Prevents accidental deletion or overwrite until unfrozen.
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROTECTED_DIRS=(data_sources_2025 data_sources_2026 answer_key_worksheets)
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

for dir in "${PROTECTED_DIRS[@]}"; do
  target="${REPO_ROOT}/${dir}"
  if [[ ! -d "$target" ]]; then
    echo "SKIP missing: $target" >&2
    continue
  fi
  echo "Freezing ${target} ..."
  cat > "${target}/.FROZEN" <<EOF
frozen_at: ${TS}
platform: macOS chflags uchg
note: Do not delete. Unfreeze with scripts/unfreeze_data_sources.sh before adding files.
EOF
  chflags -R uchg "$target"
done

total=0
for dir in "${PROTECTED_DIRS[@]}"; do
  [[ -d "${REPO_ROOT}/${dir}" ]] || continue
  n=$(find "${REPO_ROOT}/${dir}" -type f 2>/dev/null | wc -l | tr -d ' ')
  total=$((total + n))
done
echo "Done. ${total} files are user-immutable across ${#PROTECTED_DIRS[@]} protected folders."
