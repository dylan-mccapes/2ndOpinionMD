#!/usr/bin/env bash
# Re-run 05a_rag_corpus_schema.sql.gz after a failed or partial 05a (or when you see
# ERROR: relation "rag_corpus" already exists from piping 05a alone).
#
# Does: DROP rag_corpus + rag_corpus_chunks, then FTS/trigger stubs used by 05a, then 05a.
# Does NOT: 02–04, 01, 05b — assume schemas 02–04 are already OK on this DB.
#
#   export DUMP_DIR=/path/to/forward_pilot_dump_STAMP
#   export PGUSER=portalnode PGDATABASE=portalnode PGPASSWORD='…'
#   ./scripts/portalnode4090_replay_05a.sh
#
# Then load 05b (and 01 first only if you never completed auth seed).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"

: "${DUMP_DIR:?set DUMP_DIR to the dump folder containing 05a_rag_corpus_schema.sql.gz}"
: "${PGUSER:?set PGUSER}"
: "${PGDATABASE:?set PGDATABASE}"

if [[ -n "${PGPASSWORD:-}" ]] && [[ "$(id -un)" != "${PGUSER}" ]]; then
  if [[ -z "${PGHOST:-}" || "${PGHOST}" == "/var/run/postgresql" ]]; then
    export PGHOST=127.0.0.1
    export PGPORT="${PGPORT:-5432}"
    echo "Using PGHOST=$PGHOST (password auth)." >&2
  fi
fi

if [[ ! -f "$DUMP_DIR/05a_rag_corpus_schema.sql.gz" ]]; then
  echo "Missing: $DUMP_DIR/05a_rag_corpus_schema.sql.gz" >&2
  exit 1
fi

_run() {
  psql -v ON_ERROR_STOP=1 -f "$1"
}

echo "==> $ROOT/database/sql/portalnode4090_redrop_rag_corpus_schema_only.sql"
_run "$ROOT/database/sql/portalnode4090_redrop_rag_corpus_schema_only.sql"
echo "==> stubs for 05a (simple_unaccent, rag_corpus_tsv_update, keep_embedding_on_update)"
_run "$ROOT/database/sql/portalnode_stub_simple_unaccent.sql"
_run "$ROOT/database/sql/portalnode_stub_rag_corpus_tsv_update.sql"
_run "$ROOT/database/sql/portalnode_stub_keep_embedding_on_update.sql"

echo "==> $DUMP_DIR/05a_rag_corpus_schema.sql.gz"
zcat "$DUMP_DIR/05a_rag_corpus_schema.sql.gz" | psql -v ON_ERROR_STOP=1

echo "Done. Next: if 01_auth_seed never ran, apply it; then 05b_rag_corpus_slice.copy.gz COPY (see portalnode4090_restore_mkg.sh tail)."
