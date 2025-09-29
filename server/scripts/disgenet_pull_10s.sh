#!/usr/bin/env bash
set -euo pipefail

BATCH_DIR="${1:-data/disgenet_batches}"
BASE="${DISGENET_API_BASE:-https://api.disgenet.com/api/v1}"
: "${DISGENET_TOKEN:?Set DISGENET_TOKEN}"
TSV="${DISGENET_TSV:-data/disgenet_curated.tsv}"

mkdir -p "$BATCH_DIR"
: > "$BATCH_DIR/failed_ids.txt" || true

for f in "$BATCH_DIR"/genes_*; do
  [ -s "$f" ] || continue
  GENES="$(paste -sd, "$f")"
  echo ">>> $(date +%T) fetch: $GENES"

  tries=0
  while :; do
    tries=$((tries+1))
    r="$(curl -sS -w '\n%{http_code}\n' \
      -H "Authorization: $DISGENET_TOKEN" -H 'accept: application/csv' \
      "$BASE/gda/summary?gene_ncbi_id=$GENES&page_number=0&source=CURATED")"
    body="$(printf '%s' "$r" | sed '$d')"
    code="$(printf '%s' "$r" | tail -n1)"

    if [ "$code" = "200" ] && [ -n "$body" ]; then
      if [ ! -s "$TSV" ]; then
        printf '%s\n' "$body" > "$TSV"
      else
        printf '%s\n' "$body" | tail -n +2 >> "$TSV"
      fi
      # dedupe on assocID (col 3)
      awk -F'\t' 'NR==1{print;next}!seen[$3]++' "$TSV" > "$TSV.tmp" && mv "$TSV.tmp" "$TSV"
      break
    fi

    if [ "$code" = "429" ]; then
      # linear backoff + jitter; keep tries modest to protect the daily quota
      sleep $(( 90 * tries + (RANDOM % 45) ))
      [ $tries -lt 4 ] && continue
    fi

    echo "!! HTTP $code for $GENES — recording & skipping"
    tr ',' '\n' <<< "$GENES" >> "$BATCH_DIR/failed_ids.txt"
    break
  done

  # spacing between successful batches to reduce chance of 429s
  sleep $(( 75 + (RANDOM % 45) ))
done

if [ -s "$BATCH_DIR/failed_ids.txt" ]; then
  sort -u "$BATCH_DIR/failed_ids.txt" -o "$BATCH_DIR/failed_ids.txt"
  echo "Failed batch IDs recorded in $BATCH_DIR/failed_ids.txt"
else
  echo "All batches succeeded."
fi

