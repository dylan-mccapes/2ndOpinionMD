#!/usr/bin/env zsh
set -euo pipefail

BASE="${DISGENET_API_BASE:-https://api.disgenet.com/api/v1}"
: "${DISGENET_TOKEN:?Set DISGENET_TOKEN in env}"
TSV="${DISGENET_TSV:-data/disgenet_curated.tsv}"
ACC='application/csv'
SPACING="${DISGENET_SPACING:-75}"       # seconds between successful batches
MAX_RETRY="${DISGENET_MAX_RETRY:-5}"    # max attempts per batch on 429
BATCH_DIR="${1:-data/disgenet_batches}"

# gather batch files (genes_000, genes_001, ...)
typeset -a FILES
FILES=("${BATCH_DIR}"/genes_*(N))        # (N) = nullglobe; no error if none
if (( ${#FILES} == 0 )); then
  echo "No batch files found under ${BATCH_DIR} (genes_*)"
  exit 0
fi
# sort naturally
IFS=$'\n' FILES=($(printf '%s\n' "${FILES[@]}" | sort -V)); unset IFS

echo "Batches: ${#FILES} (≈10 genes per batch)"
for f in "${FILES[@]}"; do
  GENES=$(paste -sd, "$f" 2>/dev/null || true)
  [[ -z "${GENES:-}" ]] && continue
  echo ">>> $(date +%T) fetch: $GENES"

  integer attempt=0
  while true; do
    attempt=$(( attempt + 1 ))
    r=$(curl -sS -w '\n%{http_code}\n' \
      -H "Authorization: $DISGENET_TOKEN" \
      -H "accept: $ACC" \
      "$BASE/gda/summary?gene_ncbi_id=$GENES&page_number=0&source=CURATED")
    body="$(print -r -- "$r" | sed '$d')"
    code="$(print -r -- "$r" | tail -n1)"

    if [[ "$code" == "200" && -n "$body" ]]; then
      if [[ ! -s "$TSV" ]]; then
        print -r -- "$body" > "$TSV"
      else
        print -r -- "$body" | tail -n +2 >> "$TSV"
      fi
      # dedupe on assocID (col 3)
      awk -F'\t' 'NR==1{print;next}!seen[$3]++' "$TSV" > "$TSV.tmp" && mv "$TSV.tmp" "$TSV"
      sleep "$SPACING"
      break
    fi

    if [[ "$code" == "429" ]]; then
      # linear backoff + jitter: ~2–7 min growing each attempt
      backoff=$(( 120 * attempt + (RANDOM % 60) ))
      echo "429 rate-limited; sleeping ${backoff}s (attempt ${attempt}/${MAX_RETRY})"
      sleep "$backoff"
      (( attempt < MAX_RETRY )) && continue
    fi

    echo "!! HTTP $code for $GENES — giving up this batch"
    print -r -- "$GENES" >> "${BATCH_DIR}/failed_ids.txt"
    sleep 30
    break
  done
done

echo "All batches processed."
if [[ -s "${BATCH_DIR}/failed_ids.txt" ]]; then
  sort -u "${BATCH_DIR}/failed_ids.txt" -o "${BATCH_DIR}/failed_ids.txt"
  echo "Failed batch IDs recorded in ${BATCH_DIR}/failed_ids.txt"
fi

