#!/usr/bin/env bash
#
# Create the .OcrForge venv and install dependencies.
#
# Run from repo root (or anywhere — the script figures out its own location):
#     bash server/ocr_service/setup.sh
#
# Produces: server/ocr_service/.OcrForge/
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/.OcrForge"
REQS="${SCRIPT_DIR}/requirements.txt"

PY_BIN="${PYTHON_BIN:-python3}"
TORCH_INDEX="${TORCH_INDEX_URL:-https://download.pytorch.org/whl/cu121}"

echo "[OcrForge] Using Python: $(${PY_BIN} --version 2>&1)"
echo "[OcrForge] Venv path:    ${VENV_DIR}"
echo "[OcrForge] Torch index:  ${TORCH_INDEX}"

if [ ! -d "${VENV_DIR}" ]; then
    echo "[OcrForge] Creating venv..."
    "${PY_BIN}" -m venv "${VENV_DIR}"
else
    echo "[OcrForge] Venv already exists, reusing."
fi

# shellcheck disable=SC1091
source "${VENV_DIR}/bin/activate"

python -m pip install --upgrade pip wheel setuptools

echo "[OcrForge] Installing PyTorch (CUDA) from ${TORCH_INDEX}..."
pip install --index-url "${TORCH_INDEX}" torch torchvision

echo "[OcrForge] Installing service requirements..."
pip install -r "${REQS}"

echo "[OcrForge] Verifying CUDA visibility..."
python - <<'PY'
import torch
print(f"  torch:          {torch.__version__}")
print(f"  cuda available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"  device:         {torch.cuda.get_device_name(0)}")
    print(f"  capability:     {torch.cuda.get_device_capability(0)}")
PY

echo ""
echo "[OcrForge] Setup complete."
echo "[OcrForge] Activate with: source ${VENV_DIR}/bin/activate"
echo "[OcrForge] Launch with:   bash ${SCRIPT_DIR}/run.sh"
