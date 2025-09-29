# server/scripts/disgenet_resume.sh
#!/usr/bin/env bash
set -euo pipefail

BASE="${DISGENET_API_BASE:-https://api.disgenet.com/api/v1}"
: "${DISGENET_TOKEN:?Set DISGENET_TOKEN}"
TSV="${DISGENET_TSV:-data/disgenet_curated.tsv}"
TODO="${1:-data/autoimmune_gene_ids.todo}"

# Guard: make sure TODO has only integers, one per line
grep -E '^[0-9]+$' "$TODO" | sort -u > "$TODO.clean" || true
if [[ ! -s "$TODO.clean" ]]; then
  echo "Nothing to fetch (empty $TODO.clean)"; exit 0
fi

# Tiny batches: 1 gene per request minimizes 429s
mkdir -p data/disgenet_batches
rm -f data/disgenet_batches/genes_*
split -l 1 -a 3 -d "$TODO.clean" data/disgenet_batches/genes_

# helper: append and dedupe by assocID (3rd column)
append_and_dedupe() {
  local body="$1"
  if [[ ! -s "$TSV" ]]; then
    printf '%s\n' "$body" > "$TSV"
  else
    printf '%s\n' "$body" | tail -n +2 >> "$TSV"
  fi
  awk -F'\t' 'NR==1{print;next}!seen[$3]++' "$TSV" > "$TSV.tmp" && mv "$TSV.tmp" "$TSV"
}

# loop with gentle backoff + jitter
for f in data/disgenet_batches/genes_*; do
  GENES="$(paste -sd, "$f")"
  echo ">>> $(date +%T) fetch: $GENES"
  attempt=0
  while :; do
    attempt=$((attempt+1))
    resp="$(curl -sS -w $'\n%{http_code}\n' \
      -H "Authorization: $DISGENET_TOKEN" -H 'accept: application/csv' \
      "$BASE/gda/summary?gene_ncbi_id=$GENES&page_number=0&source=CURATED")"
    body="$(printf '%s' "$resp" | sed '$d')"
    code="$(printf '%s' "$resp" | tail -n1)"

    if [[ "$code" == "200" && -n "$body" ]]; then
      append_and_dedupe "$body"
      # gentle pacing even on success
      sleep $((8 + RANDOM % 7))
      break
    fi

    if [[ "$code" == "429" ]]; then
      # Back off *beyond* the window: linear + jitter
      sleep $(( 12*attempt + (RANDOM % 9) ))
      [[ $attempt -lt 6 ]] && continue
    fi

    echo "!! HTTP $code for $GENES — skipping"
    printf '%s\n' "$GENES" >> data/disgenet_batches/failed_ids.txt
    break
  done
done

echo "Done. TSV at $TSV"

