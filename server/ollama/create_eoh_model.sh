#!/usr/bin/env bash
#
# Create the eoh-llama3.1:8b model on the Ollama server.
#
# Usage:
#   ./create_eoh_model.sh                          # local Ollama
#   ./create_eoh_model.sh http://192.168.0.245:11434   # remote Ollama
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODELFILE="${SCRIPT_DIR}/eoh-llama3.1-8b.Modelfile"
MODEL_NAME="eoh-llama3.1:8b"

OLLAMA_HOST="${1:-}"

if [ -z "$OLLAMA_HOST" ]; then
    echo "[EoH] Creating model ${MODEL_NAME} on local Ollama..."
    ollama create "${MODEL_NAME}" -f "${MODELFILE}"
else
    echo "[EoH] Creating model ${MODEL_NAME} on ${OLLAMA_HOST}..."
    OLLAMA_HOST="${OLLAMA_HOST}" ollama create "${MODEL_NAME}" -f "${MODELFILE}"
fi

echo "[EoH] Model ${MODEL_NAME} created successfully."
echo "[EoH] Test with: ollama run ${MODEL_NAME} 'What is the Inflammatory Capacity Model?'"
