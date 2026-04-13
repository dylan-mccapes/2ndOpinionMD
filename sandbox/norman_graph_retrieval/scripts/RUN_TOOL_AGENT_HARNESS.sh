#!/usr/bin/env bash
# Run the per-tool graph harness (flagship: structural + temporal reduce → hybrid → BFS → … + optional eoh-llama per step).
#
# Plain command (from repo root, venv active, deps installed):
#   export PYTHONPATH=.
#   python sandbox/norman_graph_retrieval/tool_agent_harness.py --no-agent -q "your query"
#
# With LLM (needs Ollama + eoh-llama-lucifer): omit --no-agent
#
# This script: resolves repo root, picks .BeatingHeart or .venv_graph_sandbox, pip-syncs
# requirements-dev.txt, sets PYTHONPATH, runs the harness. Pass-through: all args go to Python.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "${ROOT}"

REQ="${ROOT}/requirements-dev.txt"
HARNESS="${ROOT}/sandbox/norman_graph_retrieval/tool_agent_harness.py"

if [[ ! -f "${REQ}" ]]; then
  echo "Missing ${REQ} (are you in the repo?)" >&2
  exit 1
fi
if [[ ! -f "${HARNESS}" ]]; then
  echo "Missing ${HARNESS}" >&2
  exit 1
fi

PYTHON=""
for candidate in \
  "${ROOT}/.BeatingHeart/bin/python" \
  "${ROOT}/.venv_graph_sandbox/bin/python"; do
  if [[ -x "${candidate}" ]]; then
    PYTHON="${candidate}"
    break
  fi
done

if [[ -z "${PYTHON}" ]]; then
  cat >&2 <<'EOF'
No project venv found. Create one at the repo root, then re-run:

  python3 -m venv .BeatingHeart
  . .BeatingHeart/bin/activate
  pip install -U pip
  pip install -r requirements-dev.txt

(Or use .venv_graph_sandbox as the directory name — this script checks both.)
EOF
  exit 1
fi

echo "ROOT=${ROOT}"
echo "PYTHON=${PYTHON}"
echo "Installing / verifying dependencies (requirements-dev.txt) ..."
"${PYTHON}" -m pip install -q -r "${REQ}"
# Semantic hybrid needs sentence-transformers (not in requirements-dev). Optional but recommended:
#   "${PYTHON}" -m pip install -q 'sentence-transformers>=3'

export PYTHONPATH="${ROOT}"

echo "Running tool_agent_harness.py $*"
exec "${PYTHON}" "${HARNESS}" "$@"
