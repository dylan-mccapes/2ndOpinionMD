#!/usr/bin/env bash
# One-time on WSL/Ubuntu (PEP 668): create .venv_embed and install embed deps for the 4090 pilot.
# System pip install is blocked — use this venv, then ./scripts/portalnode4090_embed_rag_slice.sh
#
#   ./scripts/portalnode4090_bootstrap_venv_embed.sh
#   source .venv_embed/bin/activate
#   export SYNC_DATABASE_URL='postgresql://portalnode:PASS@127.0.0.1:5432/portalnode'
#   ./scripts/portalnode4090_embed_rag_slice.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 not found. On Ubuntu: sudo apt-get install -y python3 python3-venv python3-full" >&2
  exit 1
fi

python3 -m venv "$ROOT/.venv_embed"
# shellcheck source=/dev/null
source "$ROOT/.venv_embed/bin/activate"
pip install -U pip wheel
pip install 'sentence-transformers>=2.2' 'psycopg[binary]' torch

echo "Done. Activate with:  source $ROOT/.venv_embed/bin/activate"
echo "Then run:            ./scripts/portalnode4090_embed_rag_slice.sh"
