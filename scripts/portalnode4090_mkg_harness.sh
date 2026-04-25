#!/usr/bin/env bash
# RTX-4090 / PortalNode: MKG dual-lane retrieval + optional eoh-llama-lucifer analysis.
#
# Prereqs: WSL Ubuntu, venv with sentence-transformers + psycopg + requests,
# Ollama on host with eoh-llama-lucifer rebuilt after Modelfile changes:
#   ollama create eoh-llama-lucifer -f server/ollama/eoh-llama3.1-8b-lucifer.Modelfile
#
# Env:
#   SYNC_DATABASE_URL or DATABASE_URL
#   OLLAMA_URL (default http://127.0.0.1:11434) — from WSL, Windows Ollama is often:
#     export OLLAMA_URL="http://$(grep nameserver /etc/resolv.conf | awk '{print $2}'):11434"
#   OLLAMA_NUM_CTX — default 32768 (match Modelfile); use 16384 on 6 GB GPUs.

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT"

# Main q8_0 model (eoh-llama) on 4090 uses 32K; override for Lucifer on 4050.
export OLLAMA_NUM_CTX="${OLLAMA_NUM_CTX:-32768}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-eoh-llama}"

if [[ -f "$ROOT/.venv_embed/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/.venv_embed/bin/activate"
elif [[ -f "$ROOT/.BeatingHeart/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/.BeatingHeart/bin/activate"
fi

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

exec python server/scripts/mkg_retrieval_harness.py "$@"
