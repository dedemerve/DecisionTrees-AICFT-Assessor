#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

chmod +x "$ROOT/.githooks/prepare-commit-msg"
git -C "$ROOT" config core.hooksPath .githooks
git -C "$ROOT" config commit.template .gitmessage

echo "Co-author hooks enabled for DecisionTrees-AICFT-Assessor."
echo "  hooks:  .githooks/prepare-commit-msg"
echo "  authors: kokluoguz-hub, msahal-hub"
