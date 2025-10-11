#!/usr/bin/env bash
set -euo pipefail

DB_URL="${1:-${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}}"

# cores → parallel jobs
if command -v sysctl >/dev/null 2>&1; then
  NCPU=$(sysctl -n hw.ncpu 2>/dev/null || echo 4)
elif command -v nproc >/dev/null 2>&1; then
  NCPU=$(nproc)
else
  NCPU=4
fi
JOBS=${JOBS:-$(( NCPU/2 ))}; [[ "$JOBS" -lt 2 ]] && JOBS=2

TS=$(date +%Y%m%d_%H%M%S)
ROOT="backups"
DIR="$ROOT/2ndopinionmd_$TS"
mkdir -p "$ROOT"

echo "[backup] starting → $DIR  (jobs=$JOBS)"
if command -v caffeinate >/dev/null 2>&1; then
  CAFF="caffeinate -dims"
else
  CAFF=""
fi

$CAFF pg_dump -Fd -j "$JOBS" -Z 3 -v -f "$DIR" "$DB_URL" 2>&1 | tee "$DIR/dump.log"
pg_dumpall --globals-only "$DB_URL" > "$DIR/globals.sql"

ln -sfn "$DIR" "$ROOT/latest"
echo "[backup] done. latest -> $DIR"

