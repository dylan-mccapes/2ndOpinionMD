#!/bin/bash
# Run Alembic migrations using .BeatingHeart venv.

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/server"

if [[ ! -x "../.BeatingHeart/bin/alembic" ]]; then
  echo "❌ .BeatingHeart alembic not found."
  echo "Run first: ./SETUP_BEATING_HEART.sh"
  exit 1
fi

exec ../.BeatingHeart/bin/alembic "$@"
