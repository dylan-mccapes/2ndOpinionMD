#!/usr/bin/env bash
# RTX-4090 / PortalNode: MKG dual-lane retrieval + optional Ollama analysis.
#
# Default flow on the 4090:
#   1) eoh-llama3.2-source-router  -> expanded ts_terms + rewritten semantic_query
#   2) BGE local embedding (CUDA)  -> ANN against rag_corpus.embedding_local
#   3) Postgres FTS per-term       -> ts via websearch_to_tsquery('public.simple_unaccent', term)
#   4) Synthesis model (default eoh-llama 8B q8_0; set MKG_SYNTH_MODEL=eoh-llama:70b for the 70B)
#
# Prereqs:
#   - WSL Ubuntu venv with sentence-transformers + psycopg + requests
#   - Ollama on host with both models loaded:
#       ollama create eoh-llama -f server/ollama/eoh-llama3.1-8b.Modelfile
#       ollama create eoh-llama3.2-source-router -f server/ollama/eoh-llama3.2-source-router.Modelfile
#       (optional) ollama pull llama3.1:70b && build eoh-llama:70b for synthesis
#
# Env knobs:
#   SYNC_DATABASE_URL or DATABASE_URL    Postgres DSN (must include user + password)
#   OLLAMA_URL                           default http://127.0.0.1:11434 (set to host IP from WSL)
#   OLLAMA_MODEL                         default eoh-llama  (planning / fallback synth)
#   MKG_SYNTH_MODEL / OLLAMA_SYNTH_MODEL final synthesis model (e.g. eoh-llama:70b)
#   OLLAMA_NUM_CTX                       synthesis context (default 32768; drop for 70B if VRAM tight)
#   EOH_SOURCE_ROUTER_MODEL              default eoh-llama3.2-source-router
#   OLLAMA_ROUTER_NUM_CTX                router context (default 8192)
#   MKG_USE_ROUTER=0                     opt out of the router stage
#   MKG_RESTRICT_SOURCES=1               restrict retrieval to router-selected sources

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT"

export OLLAMA_NUM_CTX="${OLLAMA_NUM_CTX:-32768}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-eoh-llama}"
export EOH_SOURCE_ROUTER_MODEL="${EOH_SOURCE_ROUTER_MODEL:-eoh-llama3.2-source-router}"
export OLLAMA_ROUTER_NUM_CTX="${OLLAMA_ROUTER_NUM_CTX:-8192}"

SYNTH_MODEL="${MKG_SYNTH_MODEL:-${OLLAMA_SYNTH_MODEL:-}}"
USE_ROUTER="${MKG_USE_ROUTER:-1}"
RESTRICT_SOURCES="${MKG_RESTRICT_SOURCES:-0}"

if [[ -f "$ROOT/.venv_embed/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/.venv_embed/bin/activate"
elif [[ -f "$ROOT/.BeatingHeart/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/.BeatingHeart/bin/activate"
fi

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

EXTRA_ARGS=()
if [[ "$USE_ROUTER" != "0" ]]; then
  EXTRA_ARGS+=("--use-router")
fi
if [[ "$RESTRICT_SOURCES" != "0" ]]; then
  EXTRA_ARGS+=("--router-restrict-sources")
fi
if [[ -n "$SYNTH_MODEL" ]]; then
  EXTRA_ARGS+=("--synth-model" "$SYNTH_MODEL")
fi

exec python server/scripts/mkg_retrieval_harness.py "${EXTRA_ARGS[@]}" "$@"
