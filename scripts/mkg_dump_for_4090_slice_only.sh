#!/usr/bin/env bash
# Regenerate only 05b_rag_corpus_slice.copy.gz + MANIFEST (fast) after editing
# scripts/portalnode_rag_slice_sources.txt — avoids re-dumping ontology.
#
# Usage:
#   export PGUSER=2ndopinionmd PGDATABASE=2ndopinionmd
#   DUMP_ROOT=/path/to/existing/forward_pilot_dump_20260424T195608Z ./scripts/mkg_dump_for_4090_slice_only.sh
#
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LIST_FILE="$ROOT/scripts/portalnode_rag_slice_sources.txt"
: "${DUMP_ROOT:?set DUMP_ROOT to an existing forward_pilot_dump_* directory}"
: "${PGUSER:?set PGUSER}"
: "${PGDATABASE:?set PGDATABASE}"

rag_slice_in_clause() {
  grep -v '^#' "$LIST_FILE" | grep -v '^[[:space:]]*$' | while IFS= read -r line || [[ -n "$line" ]]; do
    printf "'%s'," "$line"
  done | sed 's/,$//'
}

SLICE_IN=$(rag_slice_in_clause)
echo "==> 05b_rag_corpus_slice.copy.gz -> $DUMP_ROOT"
SQL_SLICE=$(cat <<EOSQL
COPY (
  SELECT id, source, source_id, title, text, ts, meta, metadata
  FROM public.rag_corpus
  WHERE source IN ($SLICE_IN)
  AND source NOT LIKE 'mimic%'
) TO STDOUT WITH (FORMAT binary)
EOSQL
)
psql -v ON_ERROR_STOP=1 -c "$SQL_SLICE" | gzip > "$DUMP_ROOT/05b_rag_corpus_slice.copy.gz"

echo "==> MANIFEST_slice_by_source.txt"
psql -v ON_ERROR_STOP=1 -tAc "
  SELECT source, count(*)
  FROM public.rag_corpus
  WHERE source IN ($SLICE_IN)
  GROUP BY source ORDER BY source;
" > "$DUMP_ROOT/MANIFEST_slice_by_source.txt"

ls -lh "$DUMP_ROOT/05b_rag_corpus_slice.copy.gz" "$DUMP_ROOT/MANIFEST_slice_by_source.txt"
echo "scp \"$DUMP_ROOT/05b_rag_corpus_slice.copy.gz\" \"$DUMP_ROOT/MANIFEST_slice_by_source.txt\" dylan@192.168.0.245:C:/Users/dylan/forward_pilot_dump/forward_pilot_dump_20260424T195608Z/"
