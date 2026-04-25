#!/usr/bin/env bash
# EoH source-router harness wrapper (4090 pilot).
#
# Usage:
#   bash scripts/portalnode4090_source_router_harness.sh "query text"
#   bash scripts/portalnode4090_source_router_harness.sh --query-file q.txt --out receipts/router.json
#
# Build model first:
#   ollama create eoh-llama3.2-source-router -f server/ollama/eoh-llama3.2-source-router.Modelfile

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.venv_embed/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/.venv_embed/bin/activate"
elif [[ -f "$ROOT/.BeatingHeart/bin/activate" ]]; then
  # shellcheck source=/dev/null
  source "$ROOT/.BeatingHeart/bin/activate"
fi

export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-eoh-llama3.2-source-router}"
export OLLAMA_NUM_CTX="${OLLAMA_NUM_CTX:-8192}"

exec python server/scripts/eoh_source_router_harness.py "$@"
