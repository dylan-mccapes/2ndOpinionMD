#!/usr/bin/env bash
# After portalnode4090_restore_mkg.sh: fill public.rag_corpus.embedding_local (768-d)
# with sentence-transformers — default model matches STRATEGY_FORWARD_PILOT_4090_DEPLOYMENT §3.6 / §4.
#
# WSL2 on 4090 (from repo root on ext4 or /mnt/c clone):
#   export SYNC_DATABASE_URL='postgresql://portalnode:PASSWORD@127.0.0.1:5432/portalnode'
#   ./scripts/portalnode4090_embed_rag_slice.sh
# If you already use psql restore env, this script also picks up DATABASE_URL or
# PGUSER + PGDATABASE + PGPASSWORD + PGHOST (defaults host 127.0.0.1, port 5432).
#
# Ubuntu 24.04+ blocks system pip (PEP 668). Use .BeatingHeart, or run once:
#   ./scripts/portalnode4090_bootstrap_venv_embed.sh && source .venv_embed/bin/activate
#
# Optional: LOCAL_EMBED_MODEL (default BAAI/bge-base-en-v1.5), LOCAL_EMBED_DEVICE=cuda,
# EMBED_BATCH_SIZE (default 128), extra args pass through to the Python script.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -z "${SYNC_DATABASE_URL:-}" ]]; then
  if [[ -n "${DATABASE_URL:-}" ]]; then
    export SYNC_DATABASE_URL="$DATABASE_URL"
  elif [[ -n "${PGUSER:-}" && -n "${PGDATABASE:-}" ]]; then
    _h="${PGHOST:-127.0.0.1}"
    _p="${PGPORT:-5432}"
    if [[ -n "${PGPASSWORD:-}" ]]; then
      export SYNC_DATABASE_URL="postgresql://${PGUSER}:${PGPASSWORD}@${_h}:${_p}/${PGDATABASE}"
    else
      export SYNC_DATABASE_URL="postgresql://${PGUSER}@${_h}:${_p}/${PGDATABASE}"
    fi
  fi
fi
if [[ -z "${SYNC_DATABASE_URL:-}" ]]; then
  echo "Set SYNC_DATABASE_URL, or DATABASE_URL, or PGUSER+PGDATABASE (+ PGPASSWORD for TCP)." >&2
  exit 1
fi

_activate_embed_venv() {
  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    return 0
  fi
  if [[ -f "$ROOT/.BeatingHeart/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$ROOT/.BeatingHeart/bin/activate"
    return 0
  fi
  if [[ -f "$ROOT/.venv_embed/bin/activate" ]]; then
    # shellcheck source=/dev/null
    source "$ROOT/.venv_embed/bin/activate"
    return 0
  fi
  echo "No active venv and none found at .BeatingHeart/ or .venv_embed/ (PEP 668: do not pip install system-wide)." >&2
  echo "Run once:  ./scripts/portalnode4090_bootstrap_venv_embed.sh" >&2
  echo "Then:      source $ROOT/.venv_embed/bin/activate" >&2
  echo "Re-run:     $0" >&2
  exit 1
}

_activate_embed_venv

MODEL="${LOCAL_EMBED_MODEL:-BAAI/bge-base-en-v1.5}"
BS="${EMBED_BATCH_SIZE:-128}"

exec python "$ROOT/server/scripts/embed_rag_corpus_local_slice.py" \
  --model "$MODEL" \
  --batch-size "$BS" \
  "$@"
