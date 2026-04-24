#!/usr/bin/env bash
# Run on the Mac (origin MKG). Produces gzipped dumps for PortalNode-0 / 4090.
# Does NOT dump full rag_corpus (MIMIC); ships ontology, guidelines, schema, auth seed, slice.
#
# Usage:
#   cd 2ndOpinionMD-MVP
#   export PGUSER=2ndopinionmd PGDATABASE=2ndopinionmd PGHOST=localhost PGPORT=5432
#   ./scripts/mkg_dump_for_4090.sh
#
# Output: ./artifacts/forward_pilot_dump_<UTC>/  (override with DUMP_ROOT=path)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DUMP_ROOT="${DUMP_ROOT:-$ROOT/artifacts/forward_pilot_dump_${STAMP}}"
mkdir -p "$DUMP_ROOT"

: "${PGUSER:?set PGUSER}"
: "${PGDATABASE:?set PGDATABASE}"

LIST_FILE="$ROOT/scripts/portalnode_rag_slice_sources.txt"
rag_slice_in_clause() {
  grep -v '^#' "$LIST_FILE" | grep -v '^[[:space:]]*$' | while IFS= read -r line || [[ -n "$line" ]]; do
    printf "'%s'," "$line"
  done | sed 's/,$//'
}

echo "Writing dumps to $DUMP_ROOT"
echo "(Steps can run several minutes with little output; 03_ontology is usually the longest.)"

# A — small auth / public tables (data)
# --disable-triggers: emit ALTER TABLE … DISABLE/ENABLE TRIGGER so restore tolerates circular FKs (e.g. users).
echo "==> 01_auth_seed.sql.gz (public auth tables, data-only)…"
pg_dump --no-owner --no-acl --data-only --disable-triggers --schema=public \
  -t public.users -t public.operators -t public.sessions \
  -t public.patient_timelines -t public.timeline_access \
  -t public.doctor_patient_invites -t public.journal_entries \
  | gzip > "$DUMP_ROOT/01_auth_seed.sql.gz"

# B — patient substrate (empty). Includes ehr.v_timeline_note_events → text.mimiciv_notes_resolved
# (MIMIC not dumped). Restore on 4090 runs database/sql/portalnode_stub_text_mimic_for_4090.sql before 02.
echo "==> 02_patient_substrate_schema.sql.gz…"
pg_dump --no-owner --no-acl --schema-only --schema=ehr --schema=eoh --schema=b2b \
  | gzip > "$DUMP_ROOT/02_patient_substrate_schema.sql.gz"

# C + D — ontology + guidelines
echo "==> 03_ontology.sql.gz (large — may take 10–30+ min, CPU + disk bound)…"
pg_dump --no-owner --no-acl --schema=ontology | gzip > "$DUMP_ROOT/03_ontology.sql.gz"
echo "==> 04_guidelines.sql.gz (full guidelines schema: DDL + table data, not schema-only)…"
pg_dump --no-owner --no-acl --schema=guidelines | gzip > "$DUMP_ROOT/04_guidelines.sql.gz"

# E — rag_corpus + chunks DDL only
echo "==> 05a_rag_corpus_schema.sql.gz…"
pg_dump --no-owner --no-acl --schema-only -t public.rag_corpus -t public.rag_corpus_chunks \
  | gzip > "$DUMP_ROOT/05a_rag_corpus_schema.sql.gz"

# F — slice: text + tsvector + jsonb (no embedding columns → smaller, re-embed on 4090)
echo "==> 05b_rag_corpus_slice.copy.gz (binary COPY — sources from scripts/portalnode_rag_slice_sources.txt)…"
SLICE_IN=$(rag_slice_in_clause)
#    ts is tsvector (FTS), not timestamptz.
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

echo "==> MANIFEST_slice_by_source.txt…"
psql -v ON_ERROR_STOP=1 -tAc "
  SELECT source, count(*)
  FROM public.rag_corpus
  WHERE source IN ($SLICE_IN)
  GROUP BY source ORDER BY source;
" > "$DUMP_ROOT/MANIFEST_slice_by_source.txt"

du -sh "$DUMP_ROOT"
echo "Done. Copy to 4090:"
echo "  # rsync needs rsync ON THE REMOTE HOST — Windows OpenSSH does not; use scp or tar:"
echo "  scp -r \"$DUMP_ROOT\" \"dylan@192.168.0.245:C:/Users/dylan/forward_pilot_dump/\""
echo "  # Or one file:"
echo "  ( cd \"$(dirname "$DUMP_ROOT")\" && tar czf \"$(basename "$DUMP_ROOT").tgz\" \"$(basename "$DUMP_ROOT")\" )"
echo "  scp \"$(dirname "$DUMP_ROOT")/$(basename "$DUMP_ROOT").tgz\" \"dylan@192.168.0.245:C:/Users/dylan/Downloads/\""
echo "Windows/WSL: then copy from /mnt/c/Users/dylan/... into ~/forward_pilot_dump on ext4 before restore."
