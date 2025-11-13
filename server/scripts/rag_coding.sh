# server/scripts/rag_coding.sh
#!/usr/bin/env bash
set -euo pipefail

API_URL="${API_URL:-http://127.0.0.1:8000}"
NOTE="${NOTE:-${1:-}}"
LIMIT="${LIMIT:-60}"
SOURCES="${SOURCES:-icd10cm,icd11,rxnorm,loinc,snomed,chv,orphanet}"

if [[ -z "${NOTE}" ]]; then
  echo "Usage: NOTE='62F with ...' $0"
  exit 1
fi

# JSON preview to stdout
jq -n --arg note "$NOTE" --arg sources "$SOURCES" --argjson limit "$LIMIT" \
  '{note:$note, sources:$sources, limit:$limit}' \
| curl -fsS -H 'Content-Type: application/json' -d @- \
  "${API_URL}/api/rag/coding?format=json&pretty=1" \
| jq -C .

# CSV and PDF artifacts
jq -n --arg note "$NOTE" --arg sources "$SOURCES" --argjson limit "$LIMIT" \
  '{note:$note, sources:$sources, limit:$limit}' \
| curl -fsS -H 'Content-Type: application/json' -d @- \
  -o coding.csv "${API_URL}/api/rag/coding?format=csv"

jq -n --arg note "$NOTE" --arg sources "$SOURCES" --argjson limit "$LIMIT" \
  '{note:$note, sources:$sources, limit:$limit}' \
| curl -fsS -H 'Content-Type: application/json' -d @- \
  -o coding.pdf "${API_URL}/api/rag/coding?format=pdf"

echo "Wrote coding.csv"
echo "Wrote coding.pdf"

