#!/bin/bash
# Run 2OPMD server using .BeatingHeart venv. Run from 2ndOpinionMD-MVP directory.
# If .BeatingHeart is missing, run ./SETUP_BEATING_HEART.sh first.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [[ ! -d ".BeatingHeart" ]]; then
  echo "❌ .BeatingHeart venv not found."
  echo "Run first: ./SETUP_BEATING_HEART.sh"
  exit 1
fi

source .BeatingHeart/bin/activate
exec python server/scripts/run_postgres_app.py "$@"
