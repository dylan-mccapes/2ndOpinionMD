#!/usr/bin/env bash
# Export ehr.patient_graph_vision.graph_json as a single-line JSON document.
# This avoids multiline/jsonb_pretty pipelines that sometimes produce invalid JSON
# when copied through certain tools or shells.
#
# Usage:
#   export POSTGRES_DSN='postgresql://user:pass@host:5432/dbname'
#   ./scripts/export_ptv_graph.sh 428b017a-3840-490c-8a95-65c4d6cfe10d
#   ./scripts/export_ptv_graph.sh 428b017a-3840-490c-8a95-65c4d6cfe10d /tmp/ptv.json
#
# Equivalent SQL file (versioned): database/sql/export_ptv_graph.sql
#
# Then from your laptop (WSL example):
#   scp 'USER@HOST:REMOTE_PATH/ptv_428b017a-3840-490c-8a95-65c4d6cfe10d.json' ./artifacts/
set -euo pipefail

PATIENT_ID="${1:?usage: $0 <patient_uuid> [output.json]}"
OUT="${2:-ptv_${PATIENT_ID}.json}"

if [[ -z "${POSTGRES_DSN:-${DATABASE_URL:-}}" ]]; then
  echo "ERROR: set POSTGRES_DSN or DATABASE_URL" >&2
  exit 1
fi
DSN="${POSTGRES_DSN:-${DATABASE_URL}}"

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
