#!/bin/bash
# Run 2OPMD server using .BeatingHeart venv. Run from 2ndOpinionMD-MVP directory.
# If .BeatingHeart is missing, run ./SETUP_BEATING_HEART.sh first.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Require a real venv (directory with python), not an empty folder or stray file.
if [[ ! -x ".BeatingHeart/bin/python" ]]; then
  echo "❌ .BeatingHeart venv missing or incomplete (need .BeatingHeart/bin/python)."
  echo "If setup failed with \"File exists\", a file may be blocking the venv path."
  echo "Run: ./SETUP_BEATING_HEART.sh"
  exit 1
fi

source .BeatingHeart/bin/activate
exec python server/scripts/run_postgres_app.py "$@"
