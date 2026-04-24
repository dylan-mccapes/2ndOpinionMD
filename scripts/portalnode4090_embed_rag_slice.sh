#!/usr/bin/env bash
# After portalnode4090_restore_mkg.sh: fill public.rag_corpus.embedding_local (768-d)
# with sentence-transformers — default model matches STRATEGY_FORWARD_PILOT_4090_DEPLOYMENT §3.6 / §4.
#
# WSL2 on 4090 (from repo root on ext4 or /mnt/c clone):
#   export SYNC_DATABASE_URL='postgresql://portalnode:PASSWORD@127.0.0.1:5432/portalnode'
#   ./scripts/portalnode4090_embed_rag_slice.sh
#
# Optional: LOCAL_EMBED_MODEL (default BAAI/bge-base-en-v1.5), LOCAL_EMBED_DEVICE=cuda,
# EMBED_BATCH_SIZE (default 128), extra args pass through to the Python script.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${SYNC_DATABASE_URL:?set SYNC_DATABASE_URL=postgresql://portalnode:PASS@127.0.0.1:5432/portalnode}"

if [[ -f "$ROOT/.BeatingHeart/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/.BeatingHeart/bin/activate"
fi

MODEL="${LOCAL_EMBED_MODEL:-BAAI/bge-base-en-v1.5}"
BS="${EMBED_BATCH_SIZE:-128}"

exec python "$ROOT/server/scripts/embed_rag_corpus_local_slice.py" \
  --model "$MODEL" \
  --batch-size "$BS" \
  "$@"
