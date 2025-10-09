#!/usr/bin/env bash
set -euo pipefail

BATCH_DIR="${1:?usage: disgenet_pull_10s.sh <batch_dir>}"
: "${DISGENET_TOKEN:?Set DISGENET_TOKEN first}"
: "${DISGENET_TSV:?Set DISGENET_TSV first}"

BASE="https://api.disgenet.com/api/v1"
ACCEPT="application/csv"    # CSV → TSV
OK_BATCH=0
SALVAGED=0
TOTAL=0

timestamp() { date +%T; }

# process one batch file of integer IDs (one per line)
process_batch_file() {
  local f="$1"
  # sanitize
  LC_ALL=C tr -d '\r' < "$f" | awk 'NF && $0 ~ /^[0-9]+$/' > "$f.clean" && mv "$f.clean" "$f"

  # build comma list
  GENES="$(paste -sd, "$f")"
  [ -n "${GENES}" ] || return 0

  # validate
  if ! printf '%s' "$GENES" | grep -Eq '^[0-9]+(,[0-9]+)*$'; then
    echo "!! Skipping malformed batch from $f: <$GENES>"
    printf '%s\n' "$GENES" | tr ',' '\n' | awk '$0 !~ /^[0-9]+$/' >> "$BATCH_DIR/failed_ids.txt"
    return 0
  fi

  TOTAL=$((TOTAL+1))
  echo ">>> $(timestamp) fetch: $GENES"

  # do batch request
  r="$(curl -sS -w '\n%{http_code}\n' \
        -H "Authorization: $DISGENET_TOKEN" \
        -H "accept: $ACCEPT" \
        "$BASE/gda/summary?gene_ncbi_id=$GENES&page_number=0&source=CURATED")"
  body="$(printf '%s' "$r" | sed '$d')"
  code="$(printf '%s' "$r" | tail -n1)"

  if [ "$code" = "200" ] && [ -n "$body" ]; then
    if [ ! -s "$DISGENET_TSV" ]; then printf '%s\n' "$body" > "$DISGENET_TSV"
    else printf '%s\n' "$body" | tail -n +2 >> "$DISGENET_TSV"; fi
    OK_BATCH=$((OK_BATCH+1))
    return 0
  fi

  # salvage per-ID on failure
  echo "!! HTTP $code for $GENES — salvaging per ID"
  while IFS= read -r g; do
    [ -n "$g" ] || continue
    rr="$(curl -sS -w '\n%{http_code}\n' \
          -H "Authorization: $DISGENET_TOKEN" \
          -H "accept: $ACCEPT" \
          "$BASE/gda/summary?gene_ncbi_id=$g&page_number=0&source=CURATED")"
    b="$(printf '%s' "$rr" | sed '$d')"
    c="$(printf '%s' "$rr" | tail -n1)"
    if [ "$c" = "200" ] && [ -n "$b" ]; then
      if [ ! -s "$DISGENET_TSV" ]; then printf '%s\n' "$b" > "$DISGENET_TSV"
      else printf '%s\n' "$b" | tail -n +2 >> "$DISGENET_TSV"; fi
      SALVAGED=$((SALVAGED+1))
    else
      echo "$g" >> "$BATCH_DIR/failed_ids.txt"
    fi
    sleep 6   # be gentle with the 10/min trial API cap
  done < "$f"
}

# run
mkdir -p "$BATCH_DIR"
: > "$BATCH_DIR/failed_ids.txt" || true

for f in "$BATCH_DIR"/genes_*; do
  [ -f "$f" ] || continue
  process_batch_file "$f"
done

# dedupe on assocID (col 3)
if [ -s "$DISGENET_TSV" ]; then
  awk -F'\t' 'NR==1{print;next}!seen[$3]++' "$DISGENET_TSV" > "$DISGENET_TSV.tmp" && mv "$DISGENET_TSV.tmp" "$DISGENET_TSV"
fi

echo "All batches processed."
echo "  total batches:   $TOTAL"
echo "  ok as-batch:     $OK_BATCH"
echo "  salvaged (split):$SALVAGED"
if [ -s "$BATCH_DIR/failed_ids.txt" ]; then
  echo "Failed IDs recorded in $BATCH_DIR/failed_ids.txt"
else
  echo "No failed IDs."
fi
