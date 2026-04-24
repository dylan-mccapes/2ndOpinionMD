#!/usr/bin/env bash
# Export ehr.patient_graph_vision.graph_json as a single-line JSON document.
# This avoids multiline/jsonb_pretty pipelines that sometimes produce invalid JSON
# when copied through certain tools or shells.
#
# Usage:
#   export POSTGRES_DSN='postgresql://user:pass@host:5432/dbname'
#   # Patient id from filename ptv_<UUID>.json (path or basename):
#   export PTV_ARTIFACT_DIR=/artifacts   # optional; default ./artifacts
#   ./scripts/export_ptv_graph.sh ptv_428b017a-3840-490c-8a95-65c4d6cfe10d.json
#   ./scripts/export_ptv_graph.sh /full/path/ptv_428b017a-3840-490c-8a95-65c4d6cfe10d.json
#   # Or pass the UUID directly:
#   ./scripts/export_ptv_graph.sh 428b017a-3840-490c-8a95-65c4d6cfe10d
#   # Optional explicit output path (second arg overrides default dir + name):
#   ./scripts/export_ptv_graph.sh ptv_<uuid>.json /tmp/other.json
#
# Default output name is NOT ptv_<uuid>.json (so you never overwrite a reference
# file and scp targets are obvious): ptv_<uuid>_pg_export_<UTCstamp>.json
#
# Equivalent SQL file (versioned): database/sql/export_ptv_graph.sql
#
# Then from your laptop: copy the exact path printed by this script (scp does
# not expand globs on the remote). Or use rsync, which expands on the server:
#   rsync -avz -e ssh 'USER@HOST:REMOTE_DIR/ptv_<uuid>_pg_export_*.json' ./artifacts/
set -euo pipefail

usage() {
  echo "usage: $0 <patient_uuid | ptv_<uuid>.json [path]> [output.json]" >&2
  echo "  Default output: \${PTV_ARTIFACT_DIR:-./artifacts}/ptv_<uuid>_pg_export_<UTCstamp>.json" >&2
  exit 1
}

# UUID v4-ish (also accepts other versions); safe for SQL single-quoted literal.
_uuid_re='^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'

_resolve_patient_id() {
  local raw="$1"
  local base
  base="$(basename "$raw")"
  if [[ "$base" == ptv_*.json ]]; then
    local id="${base#ptv_}"
    id="${id%.json}"
    if [[ "$id" =~ $_uuid_re ]]; then
      printf '%s' "$id"
      return 0
    fi
    echo "ERROR: ptv_*.json must contain a UUID, got: $base" >&2
    return 1
  fi
  if [[ "$raw" =~ $_uuid_re ]]; then
    printf '%s' "$raw"
    return 0
  fi
  echo "ERROR: expected UUID or ptv_<uuid>.json, got: $raw" >&2
  return 1
}

[[ -n "${1:-}" ]] || usage
PATIENT_ID="$(_resolve_patient_id "$1")" || exit 1

ART_DIR="${PTV_ARTIFACT_DIR:-./artifacts}"
if [[ -n "${2:-}" ]]; then
  OUT="$2"
else
  _stamp="$(date -u +"%Y%m%dT%H%M%S")Z"
  OUT="${ART_DIR%/}/ptv_${PATIENT_ID}_pg_export_${_stamp}.json"
fi

if [[ -z "${POSTGRES_DSN:-${DATABASE_URL:-}}" ]]; then
  echo "ERROR: set POSTGRES_DSN or DATABASE_URL" >&2
  exit 1
fi
DSN="${POSTGRES_DSN:-${DATABASE_URL}}"

mkdir -p "$(dirname "$OUT")"

# -t : tuples only (no column headers)
# -A : unaligned (no padding; one field = one line of output)
# graph_json::text : compact JSON, one line — safe for jq / python -m json.tool
psql "$DSN" -v ON_ERROR_STOP=1 -t -A -c \
  "SELECT graph_json::text FROM ehr.patient_graph_vision WHERE patient_id = '$PATIENT_ID';" \
  >"$OUT"

if [[ ! -s "$OUT" ]]; then
  echo "ERROR: empty output — check patient_id or row exists" >&2
  exit 1
fi

echo "wrote $OUT ($(wc -c <"$OUT") bytes)"
