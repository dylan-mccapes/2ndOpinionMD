#!/usr/bin/env bash
# Run on the Mac (origin MKG). Produces gzipped dumps for PortalNode-0 / 4090.
# Does NOT dump full rag_corpus (MIMIC); ships ontology, guidelines, schema, auth seed, slice.
# Total folder size is still ~0.9–1.1 GB mostly from 03_ontology.sql.gz; the rag slice (05b) is ~80–120 MB typical.
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
# shellcheck source=portalnode_rag_slice_sources_lib.sh
. "$ROOT/scripts/portalnode_rag_slice_sources_lib.sh"

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

# E — rag_corpus + chunks DDL only (--if-not-exists: slightly safer if someone re-pipes 05a on PG 9.5+)
echo "==> 05a_rag_corpus_schema.sql.gz…"
pg_dump --no-owner --no-acl --schema-only --if-not-exists -t public.rag_corpus -t public.rag_corpus_chunks \
  | gzip > "$DUMP_ROOT/05a_rag_corpus_schema.sql.gz"

# F — slice: text + tsvector + jsonb (no embedding columns → smaller, re-embed on 4090)
echo "==> 05b_rag_corpus_slice.copy.gz (binary COPY — all sources in scripts/portalnode_rag_slice_sources.txt)…"
SLICE_IN="$(portalnode_rag_slice_in_clause_from_file "$LIST_FILE")"
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

echo "==> MANIFEST_slice_by_source.txt (every listed source, count 0 if absent on origin)…"
psql -v ON_ERROR_STOP=1 -tA -F'|' -c "$(portalnode_rag_slice_manifest_sql "$LIST_FILE")" \
  >"$DUMP_ROOT/MANIFEST_slice_by_source.txt"

echo "Per-artifact (most bytes are 03_ontology; 05b is only the rag_corpus slice from portalnode_rag_slice_sources.txt):"
du -sh "$DUMP_ROOT"/* 2>/dev/null | sort -h
echo -n "Total "; du -sh "$DUMP_ROOT"
echo "Done. Copy to 4090:"
echo "  # rsync needs rsync ON THE REMOTE HOST — Windows OpenSSH does not; use scp or tar:"
echo "  scp -r \"$DUMP_ROOT\" \"dylan@192.168.0.245:C:/Users/dylan/forward_pilot_dump/\""
echo "  # Optional single tarball (ephemeral; gitignored: artifacts/forward_pilot_dump_*.tgz):"
echo "  ( cd \"$(dirname "$DUMP_ROOT")\" && tar czf \"$(basename "$DUMP_ROOT").tgz\" \"$(basename "$DUMP_ROOT")\" )"
echo "  scp \"$(dirname "$DUMP_ROOT")/$(basename "$DUMP_ROOT").tgz\" \"dylan@192.168.0.245:C:/Users/dylan/Downloads/\""
echo "Windows/WSL: copy the dump folder (or extract .tgz) to ext4 before restore; rm artifacts/forward_pilot_dump_*.tgz when done."
