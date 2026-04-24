#!/usr/bin/env bash
# Shared by mkg_dump_for_4090.sh, mkg_dump_for_4090_slice_only.sh, portalnode4090_restore_mkg.sh
# Parses scripts/portalnode_rag_slice_sources.txt → SQL fragments (CRLF-safe, trim, # comments).

portalnode_rag_slice_trim() {
  local s="$1"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

# One line per source, in file order (no comments / blanks).
portalnode_rag_slice_sources_lines() {
  local list_file="$1"
  [[ -f "$list_file" ]] || {
    echo "portalnode_rag_slice_sources_lib: missing $list_file" >&2
    return 1
  }
  local raw line
  while IFS= read -r raw || [[ -n "$raw" ]]; do
    raw="${raw//$'\r'/}"
    [[ "$raw" =~ ^[[:space:]]*# ]] && continue
    line="${raw%%#*}"
    line="$(portalnode_rag_slice_trim "$line")"
    [[ -n "$line" ]] && printf '%s\n' "$line"
  done <"$list_file"
}

# SQL: 'a','b',... for IN (...)
portalnode_rag_slice_in_clause_from_file() {
  local list_file="$1"
  local out="" sep="" esc line
  while IFS= read -r line || [[ -n "$line" ]]; do
    esc="${line//\'/\'\'}"
    out+="${sep}'${esc}'"
    sep=","
  done < <(portalnode_rag_slice_sources_lines "$list_file")
  if [[ -z "$out" ]]; then
    echo "portalnode_rag_slice_sources_lib: no sources in $list_file" >&2
    return 1
  fi
  printf '%s' "$out"
}

# PostgreSQL ARRAY['a','b']::text[] matching file order (for manifest / verification).
portalnode_rag_slice_pg_array_from_file() {
  local list_file="$1"
  local inner="" sep="" esc line
  while IFS= read -r line || [[ -n "$line" ]]; do
    esc="${line//\'/\'\'}"
    inner+="${sep}'${esc}'::text"
    sep=","
  done < <(portalnode_rag_slice_sources_lines "$list_file")
  if [[ -z "$inner" ]]; then
    echo "portalnode_rag_slice_sources_lib: no sources in $list_file" >&2
    return 1
  fi
  printf 'ARRAY[%s]' "$inner"
}

# Full SELECT: one row per configured source, count (0 if none). Tab-separated with psql -F $'\t'.
portalnode_rag_slice_manifest_sql() {
  local list_file="$1"
  local arr slice_in
  arr="$(portalnode_rag_slice_pg_array_from_file "$list_file")" || return 1
  slice_in="$(portalnode_rag_slice_in_clause_from_file "$list_file")" || return 1
  cat <<EOSQL
SELECT w.s::text, COALESCE(t.n, 0::bigint)
FROM unnest(${arr}) AS w(s)
LEFT JOIN (
  SELECT source, count(*)::bigint AS n
  FROM public.rag_corpus
  WHERE source IN (${slice_in})
    AND source NOT LIKE 'mimic%'
  GROUP BY source
) t ON t.source = w.s
ORDER BY 1;
EOSQL
}
