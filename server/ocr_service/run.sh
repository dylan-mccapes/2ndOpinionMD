#!/usr/bin/env bash
#
# Launch the OCR Forge FastAPI service using the .OcrForge venv.
#
# Environment overrides:
#     OCR_FORGE_HOST   Default: 0.0.0.0    (0.0.0.0 exposes on LAN like Ollama)
#     OCR_FORGE_PORT   Default: 8765
#     OCR_FORGE_LANGS  Default: en         (comma-separated EasyOCR language codes)
#     OCR_FORGE_GPU    Default: 1          (set 0 to force CPU)
#     OCR_FORGE_MODEL_DIR  Default: (unset — EasyOCR's ~/.EasyOCR/)
#     OCR_FORGE_WORKERS  Default: 1        (must be 1 — single GPU-resident engine)
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
VENV_DIR="${SCRIPT_DIR}/.OcrForge"

if [ ! -d "${VENV_DIR}" ]; then
    echo "[OcrForge] Venv not found at ${VENV_DIR}"
    echo "[OcrForge] Run: bash ${SCRIPT_DIR}/setup.sh"
    exit 1
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

HOST="${OCR_FORGE_HOST:-0.0.0.0}"
PORT="${OCR_FORGE_PORT:-8765}"
WORKERS="${OCR_FORGE_WORKERS:-1}"

export OCR_FORGE_LANGS="${OCR_FORGE_LANGS:-en}"
export OCR_FORGE_GPU="${OCR_FORGE_GPU:-1}"
if [ -n "${OCR_FORGE_MODEL_DIR:-}" ]; then
    export OCR_FORGE_MODEL_DIR
fi

cd "${REPO_ROOT}"

echo "[OcrForge] Launching on http://${HOST}:${PORT}"
echo "[OcrForge]   langs=${OCR_FORGE_LANGS} gpu=${OCR_FORGE_GPU} workers=${WORKERS}"

exec uvicorn server.ocr_service.app:app \
    --host "${HOST}" \
    --port "${PORT}" \
    --workers "${WORKERS}" \
    --log-level info
