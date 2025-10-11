#!/usr/bin/env bash
set -euo pipefail

DUMP_DIR="${1:-backups/latest}"
DB_URL="${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}"
JOBS=${JOBS:-2}

if [[ ! -d "$DUMP_DIR" ]]; then
  echo "[verify] dump dir not found: $DUMP_DIR" >&2
  exit 1
fi

echo "[verify] listing archive:"
pg_restore -l "$DUMP_DIR" | head -n 20

TMPDB="restore_smoke_$(date +%s)"
echo "[verify] smoke restore → $TMPDB"
createdb "$TMPDB"
trap 'dropdb --if-exists "$TMPDB"' EXIT

pg_restore -j "$JOBS" -d "$TMPDB" "$DUMP_DIR" > /dev/null
echo "[verify] smoke restore OK. dropping $TMPDB..."

