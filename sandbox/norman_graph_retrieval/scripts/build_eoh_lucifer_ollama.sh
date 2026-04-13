#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
MODEFILE="${ROOT}/server/ollama/eoh-llama3.1-8b-lucifer.Modelfile"
echo "Using Modelfile: ${MODEFILE}"
if ! command -v ollama >/dev/null 2>&1; then
  echo "ollama not found in PATH" >&2
  exit 1
fi
ollama create eoh-llama-lucifer -f "${MODEFILE}"
echo "Created model: eoh-llama-lucifer"
ollama list | grep -E "eoh-llama-lucifer|llama3.1" || true
