#!/usr/bin/env bash
set -euo pipefail

BASE="${DISGENET_API_BASE:-https://api.disgenet.com/api/v1}"
TOKEN="${DISGENET_TOKEN:?Set DISGENET_TOKEN}"
LIST="${GENE_ID_LIST:-data/autoimmune_gene_ids.txt}"
OUT="${DISGENET_TSV:-data/disgenet_curated.tsv}"
SRC_PARAM="${DISGENET_SRC_PARAM:-source}"
SRC_VAL="${DISGENET_SRC_VAL:-CURATED}"
ENDPOINT="${DISGENET_ENDPOINT:-gda/summary}"
BATCH_DIR="${BATCH_DIR:-data/disgenet_batches}"
SLEEP="${DISGENET_SLEEP:-2}"

mkdir -p "$BATCH_DIR"
touch "$OUT"
DONE="$BATCH_DIR/done.ids"; touch "$DONE"

# Create batches if absent
if ! ls "$BATCH_DIR"/genes_* >/dev/null 2>&1; then
  split -l 10 -a 3 -d "$LIST" "$BATCH_DIR/genes_"
fi

for f in "$BATCH_DIR"/genes_*; do
  GENES=$(paste -sd, "$f")

  # skip batch if all IDs already done
  SKIP=1
  while read -r id; do
    [[ -z "$id" ]] && continue
    if ! grep -qx "$id" "$DONE"; then SKIP=0; break; fi
  done < "$f"
  [[ $SKIP -eq 1 ]] && { echo "== skip $f (already done)"; continue; }

  echo "== fetch $f -> $GENES"
  TMP="$f.partial"
  set +e
  code=$(curl -sS -w '%{http_code}' -o "$TMP" \
    -H "Authorization: $TOKEN" -H 'accept: application/csv' \
    "$BASE/$ENDPOINT?gene_ncbi_id=$GENES&page_number=0&$SRC_PARAM=$SRC_VAL")
  rc=$?
  set -e

  if [[ $rc -ne 0 || "$code" -ge 400 ]]; then
    echo "!! HTTP $code for $f (kept partial? no) — skipping" >&2
    rm -f "$TMP"
    continue
  fi

  if [[ ! -s "$OUT" ]]; then
    mv "$TMP" "$OUT"
  else
    tail -n +2 "$TMP" >> "$OUT" && rm -f "$TMP"
  fi

  # de-dupe by assocID (3rd column)
  awk -F'\t' 'NR==1{print; next} !seen[$3]++' "$OUT" > "$OUT.dedup" && mv "$OUT.dedup" "$OUT"

  tr ',' '\n' <<< "$GENES" >> "$DONE"
  sleep "$SLEEP"
done

echo "== Done. Rows: $(wc -l < "$OUT")  -> $OUT"
