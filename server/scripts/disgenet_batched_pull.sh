#!/usr/bin/env bash
set -euo pipefail

BASE="${DISGENET_API_BASE:-https://api.disgenet.com/api/v1}"
: "${DISGENET_TOKEN:?Set DISGENET_TOKEN in env}"
TSV="${DISGENET_TSV:-data/disgenet_curated.tsv}"
ACC='application/csv'

# Initial gentle spacing (seconds) between successful calls
SPACING="${DISGENET_SPACING:-75}"

# Max retry attempts per batch on 429
MAX_RETRY="${DISGENET_MAX_RETRY:-5}"

# Build list of batch files from args or default directory
BATCH_DIR="${1:-data/disgenet_batches}"
mapfile -t FILES < <(ls "$BATCH_DIR"/genes_* 2>/dev/null | sort -V || true)

if [ "${#FILES[@]}" -eq 0 ]; then
  echo "No batch files found under $BATCH_DIR (genes_*)"
  exit 0
fi

echo "Batches: ${#FILES[@]} (≈10 genes per batch)"
for f in "${FILES[@]}"; do
  # collapse IDs to comma list; guard empty files
  if ! GENES="$(paste -sd, "$f" 2>/dev/null)"; then
    echo "!! Could not read $f, skipping"
    continue
  fi
  if [ -z "$GENES" ]; then
    continue
  fi

  echo ">>> $(date +%T) fetch: $GENES"
  attempt=0
  while :; do
    attempt=$((attempt + 1))

    # Perform request and capture code/body
    r=$(curl -sS -w '\n%{http_code}\n' \
      -H "Authorization: $DISGENET_TOKEN" \
      -H "accept: $ACC" \
      "$BASE/gda/summary?gene_ncbi_id=$GENES&page_number=0&source=CURATED" )
    body="$(printf '%s' "$r" | sed '$d')"
    code="$(printf '%s' "$r" | tail -n1)"

    if [ "$code" = "200" ] && [ -n "$body" ]; then
      # write header if master is empty, else append without header
      if [ ! -s "$TSV" ]; then
        printf '%s\n' "$body" > "$TSV"
      else
        printf '%s\n' "$body" | tail -n +2 >> "$TSV"
      fi
      # dedupe on assocID (col 3)
      awk -F'\t' 'NR==1{print;next}!seen[$3]++' "$TSV" > "$TSV.tmp" && mv "$TSV.tmp" "$TSV"

      # success spacing before next batch
      sleep "$SPACING"
      break
    fi

    if [ "$code" = "429" ]; then
      # Quota hit: back off with linear + jitter; keep attempts few
      backoff=$(( 120 * attempt + (RANDOM % 60) ))  # 2–7 minutes, grows per attempt
      echo "429 rate-limited; sleeping ${backoff}s (attempt ${attempt}/${MAX_RETRY})"
      sleep "$backoff"
      if [ "$attempt" -lt "$MAX_RETRY" ]; then
        continue
      fi
    fi

    echo "!! HTTP $code for $GENES — giving up this batch"
    printf '%s\n' "$GENES" >> "${BATCH_DIR}/failed_ids.txt"
    # brief pause so we don’t hammer in failure storms
    sleep 30
    break
  done
done

echo "All batches processed."
if [ -s "${BATCH_DIR}/failed_ids.txt" ]; then
  sort -u "${BATCH_DIR}/failed_ids.txt" -o "${BATCH_DIR}/failed_ids.txt"
  echo "Failed batch IDs recorded in ${BATCH_DIR}/failed_ids.txt"
fi

