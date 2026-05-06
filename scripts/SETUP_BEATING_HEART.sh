#!/bin/bash
# Create .BeatingHeart venv for 2OPMD (local server). Run once from repo root (script lives in scripts/).
# Uses Python 3.12 or 3.11 if available (Python 3.14 is too new for many wheels, e.g. scikit-learn).
# After: source .BeatingHeart/bin/activate && python server/scripts/run_postgres_app.py
# Config: .pulse or .env (and optionally server/.pulse or server/.env) — see ENV_STRATEGY in PortalVision/game_plans.

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT"

echo "========================================"
echo ".BeatingHeart venv setup (2OPMD)"
echo "========================================"

# Require Python 3.12 (3.14+ breaks scikit-learn/numpy build)
PYTHON=""
if command -v python3.12 &>/dev/null; then
  PYTHON=python3.12
fi
if [[ -z "$PYTHON" ]]; then
  echo "ERROR: python3.12 is required but not found."
  echo "Install it (e.g. brew install python@3.12), ensure it's on PATH, then re-run this script."
  exit 1
fi
echo "Using: $PYTHON ($($PYTHON --version 2>&1))"

# Remove any prior path: directory, broken symlink, or stray file (git sometimes
# leaves a file or submodule pointer — `python -m venv` fails with "File exists").
if [[ -e ".BeatingHeart" ]] || [[ -L ".BeatingHeart" ]]; then
  echo "Removing existing .BeatingHeart (file, symlink, or directory)..."
  rm -rf .BeatingHeart
fi

echo "Creating .BeatingHeart venv..."
"$PYTHON" -m venv .BeatingHeart
source .BeatingHeart/bin/activate

echo "Upgrading pip..."
pip install --quiet --upgrade pip

echo "Installing server requirements (uvicorn, fastapi, etc.)..."
pip install -r server/requirements.txt

echo "Verifying critical migration deps..."
python - <<'PY'
import importlib
import importlib.util
missing = [name for name in ("alembic", "greenlet") if importlib.util.find_spec(name) is None]
if missing:
    raise SystemExit(f"Missing required packages in .BeatingHeart: {', '.join(missing)}")
print("Migration deps ok: alembic, greenlet")
PY

echo ""
echo "✅ .BeatingHeart ready."
echo ""
echo "Activate and run server:"
echo "  source .BeatingHeart/bin/activate"
echo "  python server/scripts/run_postgres_app.py"
echo ""
echo "Run DB migrations with .BeatingHeart (recommended):"
echo "  cd server && ../.BeatingHeart/bin/alembic upgrade head"
echo ""
echo "Config: copy .env.example to .pulse or .env."
echo "  SYNC_DATABASE_URL (postgresql://...) is used for rag_corpus and is the most important."
echo "  DATABASE_URL can be the same URL; the app will use +asyncpg for the async server."
echo "  (Optional: server/.pulse or server/.env for overrides; .pulse is loaded before .env)"
echo ""
