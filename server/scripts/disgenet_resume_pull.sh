#!/usr/bin/env bash
set -euo pipefail

: "${DISGENET_TOKEN:?Set DISGENET_TOKEN in your env}"
BASE="${DISGENET_API_BASE:-https://api.disgenet.com/api/v1}"
MASTER="${MASTER:-data/disgenet_curated.tsv}"
TODO="${TODO:-data/autoimmune_gene_ids.todo}"
DONE="${DONE:-data/disgenet_done.ids}"

mkdir -p "$(dirname "$MASTER")"
touch "$MASTER" "$DONE"

pull_one() {
  local gene="$1"
  local tmp
  tmp="$(mktemp -t disgenet.XXXXXX)"
  local url="$BASE/gda/summary?gene_ncbi_id=$gene&page_number=0&source=CURATED"

  # simple backoff loop
  local tries=0
  while :; do
    code=$(curl -sS -o "$tmp" -w "%{http_code}" \
      -H "Authorization: $DISGENET_TOKEN" \
      -H 'accept: application/csv' "$url" || true)

    if [[ "$code" == "200" && -s "$tmp" ]]; then
      if [[ ! -s "$MASTER" ]]; then
        mv "$tmp" "$MASTER"
      else
        tail -n +2 "$tmp" >> "$MASTER"
        rm -f "$tmp"
      fi
      # dedupe by assocID (col 3)
      awk -F'\t' 'NR==1{print; next} !seen[$3]++' "$MASTER" > "$MASTER.dedup" && mv "$MASTER.dedup" "$MASTER"
      # record success, remove from TODO
      echo "$gene" >> "$DONE"
      grep -v -x "$gene" "$TODO" > "$TODO.tmp" && mv "$TODO.tmp" "$TODO"
      echo "✓ gene $gene appended ($(wc -l < "$MASTER") lines total)"
      return 0
    fi

    ((tries++))
    if [[ "$code" == "429" ]]; then
      # rate-limited: exponential-ish backoff
      sleep $((60 + 30*tries))
    elif (( tries < 3 )); then
      sleep 10
    else
      echo "!! gene $gene failed (HTTP $code), giving up for now"
      rm -f "$tmp"
      return 1
    fi
  done
}

# loop genes one by one with a base delay to avoid 429s
while IFS= read -r gene; do
  [[ -n "$gene" ]] || continue
  pull_one "$gene" || true
  # base throttle between calls (trial is touchy)
  sleep "${SLEEP_BETWEEN:-65}"
done < "$TODO"
