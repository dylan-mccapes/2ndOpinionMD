#!/usr/bin/env bash
# Run after mkg_dump_for_4090.sh output is on the same machine as Postgres.
#
# Windows 4090 + WSL2: run inside Ubuntu (ext4), not PowerShell — paths like /home/dylan/...
#   wsl -d Ubuntu -- bash -lc 'export DUMP_DIR=... PGHOST=...; bash ~/.../portalnode4090_restore_mkg.sh'
# Or: scripts/portalnode4090_wsl.ps1 -Restore ...
#
# Requires: PostgreSQL + pgvector (portalnode4090_install_postgres.sh).
#
# If restore fails with:  ERROR: role "2ndopinionmd" does not exist
# your dump was built before pg_dump gained --no-owner. Either:
#   (A) One-time stub (cluster-wide):  sudo -u postgres psql -d postgres -v ON_ERROR_STOP=1 -f scripts/portalnode_stub_mac_owner_role.sql
#   (B) Re-run mkg_dump_for_4090.sh on the Mac (now uses --no-owner --no-acl) and re-copy 02–05a,01.
#
# If restore fails with:  ERROR: schema "b2b" already exists (or similar)
# a previous run partially applied 02_*.sql.gz. Nuke the target DB, then restore:
#   sudo bash scripts/portalnode4090_reset_mkg_target_db.sh
#
# If restore fails with:  relation "text.mimiciv_notes_resolved" does not exist
# 02 includes ehr.v_timeline_note_events joining MIMIC tables not in the pilot dump.
# This script applies database/sql/portalnode_stub_text_mimic_for_4090.sql before 02 automatically.
#
# If restore fails with:  text search configuration "public.simple_unaccent" does not exist
# 05a creates GIN indexes using that Mac-defined config. We apply database/sql/portalnode_stub_simple_unaccent.sql before 05a.
#
# If restore fails with:  function public.keep_embedding_on_update() does not exist
# 05a may recreate triggers on rag_corpus that reference this Mac-only function. Stub before 05a.
#
# If replaying 05a alone errors with:  relation "rag_corpus" already exists — 05a is not idempotent.
# Full reset + restore, or pilot-only: database/sql/portalnode4090_redrop_rag_corpus_schema_only.sql then stubs+05a+05b (not 01 if auth already loaded).
#
# Usage:
#   export DUMP_DIR=/opt/portalnode/forward_pilot_dump
#   export PGUSER=portalnode PGDATABASE=portalnode PGPASSWORD='…'
#   ./scripts/portalnode4090_restore_mkg.sh
#
# WSL / Ubuntu: Unix socket + role portalnode uses "peer" — the Linux login must be named
# portalnode. If you are hilarious_marcupial (or anything else), use TCP + password:
#   export PGHOST=127.0.0.1
# This script auto-sets PGHOST=127.0.0.1 when PGPASSWORD is set and whoami != PGUSER.
#
# If you did NOT set DUMP_DIR: we look for 05b under WSL ~/forward_pilot_dump or under
# /mnt/c/Users/*/forward_pilot_dump (where scp from Mac to Windows OpenSSH usually lands).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
LIST_FILE="$ROOT/scripts/portalnode_rag_slice_sources.txt"
# shellcheck source=portalnode_rag_slice_sources_lib.sh
. "$ROOT/scripts/portalnode_rag_slice_sources_lib.sh"

: "${PGUSER:?set PGUSER}"
: "${PGDATABASE:?set PGDATABASE}"

# Peer auth on /var/run/postgresql requires OS username == PGUSER. Use localhost TCP + SCRAM.
if [[ -n "${PGPASSWORD:-}" ]] && [[ "$(id -un)" != "${PGUSER}" ]]; then
  if [[ -z "${PGHOST:-}" || "${PGHOST}" == "/var/run/postgresql" ]]; then
    export PGHOST=127.0.0.1
    export PGPORT="${PGPORT:-5432}"
    echo "Using PGHOST=$PGHOST (password auth); peer would fail for OS user $(id -un) → ${PGUSER}." >&2
  fi
fi

# Return 0 and echo absolute dir if $1 is (or contains one child that is) the dump folder.
_resolve_dump_dir() {
  local d="${1:-}"
  [[ -n "$d" && -d "$d" ]] || return 1
  d="$(cd "$d" && pwd)"
  if [[ -f "$d/05b_rag_corpus_slice.copy.gz" ]]; then
    echo "$d"
    return 0
  fi
  local sub
  for sub in "$d"/*; do
    [[ -d "$sub" && -f "$sub/05b_rag_corpus_slice.copy.gz" ]] || continue
    echo "$(cd "$sub" && pwd)"
    return 0
  done
  return 1
}

_auto_find_05b() {
  # Typical layouts: …/forward_pilot_dump_<stamp>/05b*, …/forward_pilot_dump/<stamp>/05b*, Downloads, Desktop
  find "$HOME/forward_pilot_dump" \
    /mnt/c/Users/*/forward_pilot_dump \
    /mnt/c/Users/*/Downloads \
    /mnt/c/Users/*/Desktop \
    -maxdepth 4 \
    -name '05b_rag_corpus_slice.copy.gz' -type f 2>/dev/null | head -1
}

if [[ -n "${DUMP_DIR:-}" ]]; then
  _resolved="$(_resolve_dump_dir "$DUMP_DIR" || true)"
  if [[ -n "$_resolved" ]]; then
    DUMP_DIR="$_resolved"
  fi
fi

if [[ -z "${DUMP_DIR:-}" || ! -f "$DUMP_DIR/05b_rag_corpus_slice.copy.gz" ]]; then
  _found="$(_auto_find_05b || true)"
  if [[ -n "$_found" ]]; then
    DUMP_DIR="$(cd "$(dirname "$_found")" && pwd)"
    echo "Using DUMP_DIR=$DUMP_DIR (auto-detected)"
  fi
fi

: "${DUMP_DIR:?set DUMP_DIR to the folder that contains 05b_rag_corpus_slice.copy.gz}"

if [[ ! -f "$DUMP_DIR/05b_rag_corpus_slice.copy.gz" ]]; then
  echo "Missing 05b under: $DUMP_DIR" >&2
  echo "Search your Windows profile for the slice (scp may have used a different folder name):" >&2
  echo "  find /mnt/c/Users -maxdepth 8 -name '05b_rag_corpus_slice.copy.gz' 2>/dev/null" >&2
  echo "Then: export DUMP_DIR=\"\$(dirname \"\$(find /mnt/c/Users -maxdepth 8 -name 05b_rag_corpus_slice.copy.gz 2>/dev/null | head -1)\")\"" >&2
  exit 1
fi

run_sql_gz() {
  local f="$1"
  echo "==> $f"
  zcat "$f" | psql -v ON_ERROR_STOP=1
}

echo "==> $ROOT/database/sql/portalnode_stub_text_mimic_for_4090.sql (MIMIC text stub for ehr.v_timeline_note_events)"
psql -v ON_ERROR_STOP=1 -f "$ROOT/database/sql/portalnode_stub_text_mimic_for_4090.sql"

run_sql_gz "$DUMP_DIR/02_patient_substrate_schema.sql.gz"
run_sql_gz "$DUMP_DIR/03_ontology.sql.gz"
run_sql_gz "$DUMP_DIR/04_guidelines.sql.gz"
echo "==> $ROOT/database/sql/portalnode_stub_simple_unaccent.sql (FTS config for rag_corpus GIN in 05a)"
psql -v ON_ERROR_STOP=1 -f "$ROOT/database/sql/portalnode_stub_simple_unaccent.sql"
echo "==> $ROOT/database/sql/portalnode_stub_keep_embedding_on_update.sql (trigger fn referenced in 05a)"
psql -v ON_ERROR_STOP=1 -f "$ROOT/database/sql/portalnode_stub_keep_embedding_on_update.sql"
run_sql_gz "$DUMP_DIR/05a_rag_corpus_schema.sql.gz"
# Auth seed after rag_corpus DDL (matches STRATEGY_FORWARD_PILOT_4090_DEPLOYMENT load order).
run_sql_gz "$DUMP_DIR/01_auth_seed.sql.gz"

echo "==> 05b_rag_corpus_slice.copy.gz (binary COPY)"
# Re-loading 05b only on a DB that already has rag rows will duplicate ids — truncate first, e.g.:
#   psql -c 'TRUNCATE public.rag_corpus, public.rag_corpus_chunks CASCADE;'
zcat "$DUMP_DIR/05b_rag_corpus_slice.copy.gz" | psql -v ON_ERROR_STOP=1 -c \
  "COPY public.rag_corpus (id, source, source_id, title, text, ts, meta, metadata) FROM STDIN WITH (FORMAT binary)"

echo "==> verify counts vs MANIFEST (must list every source in portalnode_rag_slice_sources.txt)"
if [[ -f "$DUMP_DIR/MANIFEST_slice_by_source.txt" ]]; then
  diff -u "$DUMP_DIR/MANIFEST_slice_by_source.txt" \
    <(psql -tA -F'|' -c "$(portalnode_rag_slice_manifest_sql "$LIST_FILE")") \
    || echo "(warn) manifest mismatch — re-copy MANIFEST+05b from the same mkg_dump run, or rm stale MANIFEST"
fi

psql -tAc "SELECT count(*) AS rag_corpus_rows FROM public.rag_corpus;"
echo "Restore complete. Next: add embedding_local + run server/scripts/embed_rag_corpus_local_slice.py"
