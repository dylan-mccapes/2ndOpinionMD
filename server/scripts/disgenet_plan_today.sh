#!/usr/bin/env bash
set -euo pipefail

# Inputs you already keep up to date
UNIVERSE="data/autoimmune_gene_ids.clean"     # full candidate list (Entrez IDs)
DONE_IDS="data/disgenet_done.ids"             # what’s already in DB
TODOS="data/disgenet_batches/todo.ids"        # computed below
BATCH_DIR="data/disgenet_batches"
PRIOR_IDS="data/priority.ids"                 # union of “medically relevant” sources

# (A) Normalize universe
LC_ALL=C tr -d '\r' < "$UNIVERSE" | awk 'NF && $0 ~ /^[0-9]+$/' | sort -u > data/all_ids.sorted

# (B) What’s already in your DB
psql -d 2ndopinionmd -Atc \
  "SELECT gene_ncbi_id::text
   FROM molecular.disgenet_associations
   WHERE gene_ncbi_id IS NOT NULL
   GROUP BY 1 ORDER BY 1" > "$DONE_IDS"

# (C) Build “medical relevance” priority list (IDs only)
#    – You can extend this block anytime with new sources.
> "$PRIOR_IDS"

# 1) Core immune & druggable axes you’ve been using
#    (already in repo) – if present, append their IDs:
for f in \
  data/seed_modern_gene_ids.tsv \
  data/seed_autoimmune_gene_ids.tsv \
  data/seed_extra_gene_ids.tsv \
  data/seed_additions_gene_ids.tsv \
  data/immune_plus.ids.tsv; do
  [ -s "$f" ] && awk -F'\t' 'NR>1 && $2 ~ /^[0-9]+$/ {print $2}' "$f" >> "$PRIOR_IDS" || true
done

# 2) HLA cluster (if not fully covered yet)
grep -E '^(3105|3106|3107|3122|3123|3125|3126|3127|3128|3133|3134|3135|3136)$' data/all_ids.sorted >> "$PRIOR_IDS" || true

# 3) Hand-picked “therapeutic & pathway” spillover (just in case)
#    (Add any extra IDs you care about here)
# echo -e "355\n3569\n..." >> "$PRIOR_IDS"

# De-dup and keep only IDs that exist in the universe
LC_ALL=C tr -d '\r' < "$PRIOR_IDS" | awk 'NF && $0 ~ /^[0-9]+$/' \
  | sort -u | grep -xF -f data/all_ids.sorted > "${PRIOR_IDS}.clean"
mv "${PRIOR_IDS}.clean" "$PRIOR_IDS"

# (D) Build TODO = universe \ already-in-DB (sorted ascending)
comm -23 data/all_ids.sorted "$DONE_IDS" > "$TODOS"

# (E) Split TODO into priority-first then the rest
#     We’ll take exactly 100 for today (10 calls × 10 genes).
PRIO_TODO="data/disgenet_batches/todo.priority"
REST_TODO="data/disgenet_batches/todo.rest"
> "$PRIO_TODO"; > "$REST_TODO"

# priority slice (preserve ascending order of universe)
grep -xF -f "$PRIOR_IDS" "$TODOS" | sort -n > "$PRIO_TODO" || true
# rest slice
grep -vxF -f "$PRIOR_IDS" "$TODOS" | sort -n > "$REST_TODO" || true

# final selection: first take priority, then rest, to reach 100 rows max
SELECTED="data/disgenet_batches/todo.selected"
( cat "$PRIO_TODO"; cat "$REST_TODO" ) | awk 'NF' | head -n 100 > "$SELECTED"

# Prepare batches of 10 (exactly 10 files if ≥100 selected; fewer otherwise)
mkdir -p "$BATCH_DIR"
rm -f "$BATCH_DIR"/genes_*
split -l 10 -a 3 -d "$SELECTED" "$BATCH_DIR/genes_"

# Sanitize each batch file (CRLF, non-numeric guards)
for f in "$BATCH_DIR"/genes_*; do
  [ -f "$f" ] || continue
  LC_ALL=C tr -d '\r' < "$f" | awk 'NF && $0 ~ /^[0-9]+$/' > "$f.clean" && mv "$f.clean" "$f"
done

# Show plan summary
echo "=== PLAN (today) ==="
echo "Universe IDs   : $(wc -l < data/all_ids.sorted)"
echo "In DB already  : $(wc -l < $DONE_IDS)"
echo "Still missing  : $(wc -l < $TODOS)"
echo "Priority pool  : $(wc -l < $PRIOR_IDS)"
echo "Selected today : $(wc -l < $SELECTED)"
echo "Batch files    : $(ls $BATCH_DIR/genes_* | wc -l)"
echo
echo "First 2 batches:"
for f in $(ls "$BATCH_DIR"/genes_* | head -n 2); do
  echo "  $(basename "$f"): $(paste -sd, "$f")"
done

