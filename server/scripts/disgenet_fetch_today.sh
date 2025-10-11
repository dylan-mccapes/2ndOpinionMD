#!/usr/bin/env bash
set -euo pipefail

BATCH_DIR="${1:-data/disgenet_batches}"
: "${DISGENET_TOKEN:?Set DISGENET_TOKEN}"
: "${DISGENET_TSV:?Set DISGENET_TSV}"

BASE="https://api.disgenet.com/api/v1"
MAX_CALLS="${MAX_CALLS:-10}"        # trial hard-cap (10/day)
SLEEP_BETWEEN="${SLEEP_BETWEEN:-8}" # keeps <10/min
calls=0; ok=0; skipped=0

append_csv_body() {
  local body="$1"
  if [ ! -s "$DISGENET_TSV" ]; then
    printf '%s\n' "$body" > "$DISGENET_TSV"
  else
    printf '%s\n' "$body" | tail -n +2 >> "$DISGENET_TSV"
  fi
}

dedupe_associd() {
  awk -F'\t' 'NR==1{print;next}!seen[$3]++' "$DISGENET_TSV" > "$DISGENET_TSV.tmp" \
    && mv "$DISGENET_TSV.tmp" "$DISGENET_TSV"
}

for f in $(ls "$BATCH_DIR"/genes_* 2>/dev/null | head -n "$MAX_CALLS"); do
  GENES="$(paste -sd, "$f")"
  echo ">>> $(date +%T) fetch: $GENES"

  # 1) Try CSV
  r=$(curl -sS -w '\n%{http_code}\n' \
       -H "Authorization: $DISGENET_TOKEN" \
       -H "accept: text/csv" \
       "$BASE/gda/summary?gene_ncbi_id=$GENES&page_number=0&source=CURATED")
  body="$(printf '%s' "$r" | sed '$d')"
  code="$(printf '%s' "$r" | tail -n1)"
  echo "    http(csv): $code"

  if [ "$code" = "200" ] && [ -n "$body" ]; then
    append_csv_body "$body"
    ok=$((ok+1))
  else
    # --- JSON fallback (use a temp file; no unbound vars) ---
    json_tmp="data/tmp/disgenet.$(date +%s%N).json"
    mkdir -p "$(dirname "$json_tmp")"

    json_code=$(
      curl -sS \
        -H "Authorization: $DISGENET_TOKEN" \
        -H 'accept: application/json' \
        -w '%{http_code}' -o "$json_tmp" \
        "$BASE/gda/summary?gene_ncbi_id=$GENES&page_number=0&source=CURATED"
    )

    printf '    http(json): %s\n' "$json_code"

    if [ "$json_code" = "200" ] && [ -s "$json_tmp" ]; then
      # Import JSON directly to DB (safer than TSV alignment)
      SYNC_DATABASE_URL="${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}" \
        server/venv312/bin/python server/scripts/ingest_disgenet_json_direct.py "$json_tmp"
      ok=$(( ok + 1 ))
    else
      # If we got rate limited, stop early to preserve quota
      if [ "$json_code" = "429" ]; then
        echo "!! Quota hit (429). Stopping today to preserve calls."
        break
      fi
      # Record failed batch for tomorrow’s resume
      echo "$GENES" >> "$BATCH_DIR/failed_batches.txt"
      skipped=$(( skipped + 1 ))
    fi
  fi

  # Dedupe by associd
  [ -s "$DISGENET_TSV" ] && dedupe_associd || true

  calls=$((calls+1))
  [ "$calls" -ge "$MAX_CALLS" ] && break
  sleep "$SLEEP_BETWEEN"
done

echo "All batches processed."
echo "  total calls       : $calls"
echo "  ok (200 any fmt)  : $ok"
echo "  skipped (non-200) : $skipped"
[ -s "$BATCH_DIR/failed_batches.txt" ] && echo "Failed batches recorded in $BATCH_DIR/failed_batches.txt"
