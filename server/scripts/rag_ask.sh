# server/scripts/rag_ask.sh
#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://127.0.0.1:8000}"
NOTE="${NOTE:-${1:-}}"
LIMIT="${LIMIT:-60}"
SOURCES="${SOURCES:-icd10cm,icd11,snomed,loinc,rxnorm,hpo,orphanet,guidelines}"
EOH="${EOH:-true}"

if [[ -z "${NOTE}" ]]; then
  echo "Usage: NOTE='62F with ...' $0"
  exit 1
fi

jq -n --arg q "$NOTE" --arg sources "$SOURCES" --argjson limit "$LIMIT" --argjson eoh_enabled "$EOH" \
  '{q:$q, sources:$sources, limit:$limit, eoh_enabled:($eoh_enabled|tostring|test("true")) }' \
| curl -fsS -H 'Content-Type: application/json' -d @- \
  "${API_URL}/api/rag/ask?format=json&pretty=1" \
| jq -C .

