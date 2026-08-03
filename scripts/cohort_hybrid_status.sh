#!/usr/bin/env bash
# Cohort hybrid diarization status snapshot.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AUDIO="$ROOT/data_sources_2026/codap_arbor_21april_audio"
echo "=== hybrid_diarization cohort status ==="
echo "time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
if [[ -f "$ROOT/logs/hybrid_run.pid" ]]; then
  PID=$(cat "$ROOT/logs/hybrid_run.pid")
  if ps -p "$PID" >/dev/null 2>&1; then
    echo "batch_pid: $PID (running)"
    ps -p "$PID" -o etime=,%cpu=,rss= 2>/dev/null | awk '{print "  elapsed=" $1 " cpu=" $2 "% rss=" $3}'
  else
    echo "batch_pid: $PID (not running)"
  fi
else
  echo "batch_pid: none"
fi
echo ""
done=0 missing=0
for d in "$AUDIO"/*/; do
  sid=$(basename "$d")
  out="$d/${sid}_hybrid_diarization.json"
  if [[ -f "$out" ]]; then
    status=$(python3 -c "import json;print(json.load(open('$out')).get('status','?'))" 2>/dev/null || echo "?")
    segs=$(python3 -c "import json;print(json.load(open('$out')).get('segment_count','?'))" 2>/dev/null || echo "?")
    echo "  [ok] $sid status=$status segments=$segs"
    done=$((done + 1))
  else
    echo "  [--] $sid"
    missing=$((missing + 1))
  fi
done
echo ""
echo "completed: $done / missing: $missing"
