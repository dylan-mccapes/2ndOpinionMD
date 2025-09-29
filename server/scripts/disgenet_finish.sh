#!/usr/bin/env bash
set -euo pipefail

: "${DISGENET_TOKEN:?Set DISGENET_TOKEN in env}"
: "${SYNC_DATABASE_URL:?Set SYNC_DATABASE_URL=postgresql://user@host:5432/db}"

INPUT="${1:-data/autoimmune_gene_ids.clean}"
TSV="data/disgenet_curated.tsv"
BASE="${DISGENET_API_BASE:-https://api.disgenet.com/api/v1}"

# 1) Compute TODO (IDs in INPUT not yet in DB)
psql -d "${SYNC_DATABASE_URL##*/}" -Atc \
  "select gene_ncbi_id::text from molecular.disgenet_associations where gene_ncbi_id is not null group by 1 order by 1" \
  | tr -d '\r' | LC_ALL=C sort -u > data/disgenet_done.ids

LC_ALL=C tr -d '\r' < "$INPUT" | awk 'NF && $0 ~ /^[0-9]+$/' | sort -u > data/autoimmune_gene_ids.clean
comm -23 data/autoimmune_gene_ids.clean data/disgenet_done.ids > data/autoimmune_gene_ids.todo || true

TODO_N=$(wc -l < data/autoimmune_gene_ids.todo || echo 0)
echo "TODO gene IDs: $TODO_N"
if [ "$TODO_N" -eq 0 ]; then
  echo "All set: nothing to fetch."
  exit 0
fi

# 2) Fetch (trial-safe in batches of 10, with backoff inside the Python)
DISGENET_ENDPOINT=gda/summary \
DISGENET_FILTER_KEY=source DISGENET_FILTER_VALUE=CURATED \
DISGENET_AUTH_MODE=bare \
DISGENET_TSV="$TSV" \
server/venv312/bin/python server/scripts/download_disgenet_by_genes.py GENES_FILE="data/autoimmune_gene_ids.todo"

# 3) Dedupe TSV on assocID (col 3)
cp -v "$TSV"{,.bak.$(date +%F-%H%M)}
awk -F'\t' 'NR==1{print; next} !seen[$3]++' "$TSV" > "$TSV.tmp" && mv "$TSV.tmp" "$TSV"

# 4) Import
make disgenet-import TSV="$TSV"

# 5) Verify coverage again
psql -d "${SYNC_DATABASE_URL##*/}" -Atc \
  "select count(distinct gene_ncbi_id) from molecular.disgenet_associations where gene_ncbi_id is not null" \
  | awk '{print "Distinct genes now in DB: " $0}'

comm -23 data/autoimmune_gene_ids.clean \
  <(psql -d "${SYNC_DATABASE_URL##*/}" -Atc "select gene_ncbi_id::text from molecular.disgenet_associations where gene_ncbi_id is not null group by 1 order by 1") \
  || true

