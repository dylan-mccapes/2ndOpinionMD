#!/usr/bin/env bash
set -euo pipefail

# Config
SOURCES="${SOURCES:-CURATED,CLINVAR,LITERATURE}"  # broaden to pull more rows under trial
MAX_CALLS="${MAX_CALLS:-9}"                       # leave 1-call buffer under 10/day
DISGENET_BASE="${DISGENET_BASE:-https://www.disgenet.org}"  # follow -L anyway

mkdir -p data/disgenet_batches
: > data/disgenet_batches/no_curated.ids || true

calls=0
for f in data/disgenet_batches/genes_*; do
  ids=$(cat "$f")
  echo ">>> $(date +%T) fetch (sources=$SOURCES): $ids"

  tmp=$(mktemp)
  code=0
  curl -fsSL -L \
    -H "Authorization: Bearer $DISGENET_TOKEN" \
    -H "Accept: application/json" \
    "$DISGENET_BASE/api/gda/gene/${ids}?source=${SOURCES}" \
    -o "$tmp" || code=$?

  if [[ $code -ne 0 ]]; then
    echo "curl failed (code=$code). Stopping."
    rm -f "$tmp"; break
  fi

  # If we accidentally got HTML (missed JSON), fail loudly
  if file "$tmp" | grep -qi 'html'; then
    echo "Non-JSON body (HTML). Did auth/URL change? Kept at $tmp"
    break
  fi

  # empty array? mark IDs as no_curated so planner stops retrying them
  if jq -e 'type=="array" and length==0' "$tmp" >/dev/null 2>&1; then
    echo "$ids" | tr ',' '\n' >> data/disgenet_batches/no_curated.ids
    sort -u data/disgenet_batches/no_curated.ids -o data/disgenet_batches/no_curated.ids
    echo "… empty array; recorded to no_curated.ids"
    rm -f "$tmp"
  else
    # Direct ingest expects a file path arg
    server/venv312/bin/python server/scripts/ingest_disgenet_json_direct.py "$tmp" || {
      echo "ingester failed; keeping file at $tmp for debugging"
      break
    }
    rm -f "$tmp"
  fi

  calls=$((calls+1))
  [[ $calls -ge $MAX_CALLS ]] && { echo "Daily budget used ($MAX_CALLS calls)."; break; }
  sleep 6
done

