#!/usr/bin/env bash
# Run after mkg_dump_for_4090.sh output is on the same machine as Postgres.
#
# Windows 4090 + WSL2: run inside Ubuntu (ext4), not PowerShell — paths like /home/dylan/...
#   wsl -d Ubuntu -- bash -lc 'export DUMP_DIR=... PGHOST=...; bash ~/.../portalnode4090_restore_mkg.sh'
# Or: scripts/portalnode4090_wsl.ps1 -Restore ...
#
# Requires: PostgreSQL + pgvector (portalnode4090_install_postgres.sh).
#
# Usage:
#   export DUMP_DIR=/opt/portalnode/forward_pilot_dump
#   export PGHOST=/var/run/postgresql PGUSER=portalnode PGDATABASE=portalnode
#   ./scripts/portalnode4090_restore_mkg.sh
#
# If you use a password for portalnode over TCP, set PGPASSWORD.

set -euo pipefail

: "${DUMP_DIR:?set DUMP_DIR to the directory containing 01_*.sql.gz … 05b_*.copy.gz}"
: "${PGUSER:?set PGUSER}"
: "${PGDATABASE:?set PGDATABASE}"

if [[ ! -f "$DUMP_DIR/05b_rag_corpus_slice.copy.gz" ]]; then
  echo "Missing $DUMP_DIR/05b_rag_corpus_slice.copy.gz" >&2
  exit 1
fi

run_sql_gz() {
  local f="$1"
  echo "==> $f"
  zcat "$f" | psql -v ON_ERROR_STOP=1
}

run_sql_gz "$DUMP_DIR/02_patient_substrate_schema.sql.gz"
run_sql_gz "$DUMP_DIR/03_ontology.sql.gz"
run_sql_gz "$DUMP_DIR/04_guidelines.sql.gz"
run_sql_gz "$DUMP_DIR/05a_rag_corpus_schema.sql.gz"
# Auth seed after rag_corpus DDL (matches STRATEGY_FORWARD_PILOT_4090_DEPLOYMENT load order).
run_sql_gz "$DUMP_DIR/01_auth_seed.sql.gz"

echo "==> 05b_rag_corpus_slice.copy.gz (binary COPY)"
# Re-loading 05b only on a DB that already has rag rows will duplicate ids — truncate first, e.g.:
#   psql -c 'TRUNCATE public.rag_corpus, public.rag_corpus_chunks CASCADE;'
zcat "$DUMP_DIR/05b_rag_corpus_slice.copy.gz" | psql -v ON_ERROR_STOP=1 -c \
  "COPY public.rag_corpus (id, source, source_id, title, text, ts, meta, metadata) FROM STDIN WITH (FORMAT binary)"

echo "==> verify counts vs MANIFEST"
if [[ -f "$DUMP_DIR/MANIFEST_slice_by_source.txt" ]]; then
  diff -u "$DUMP_DIR/MANIFEST_slice_by_source.txt" \
    <(psql -tAc "SELECT source, count(*) FROM public.rag_corpus GROUP BY source ORDER BY source;") \
    || echo "(warn) manifest mismatch — inspect above"
fi

psql -tAc "SELECT count(*) AS rag_corpus_rows FROM public.rag_corpus;"
echo "Restore complete. Next: add embedding_local + run server/scripts/embed_rag_corpus_local_slice.py"
