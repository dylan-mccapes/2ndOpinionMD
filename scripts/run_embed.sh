#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT"
while true; do
  TS=$(date +%Y%m%d_%H%M%S)
  echo "[${TS}] starting worker..."
  server/venv312/bin/python server/scripts/embed_mimic4_note_worker.py \
    2>&1 | tee -a "logs/embed_${TS}.log" || true
  # backoff w/ jitter if it exits
  S=$(( 20 + RANDOM % 40 ))
  echo "restarting in ${S}s..."
  sleep "$S"
done
