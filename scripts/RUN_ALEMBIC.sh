#!/bin/bash
# Run Alembic migrations using .BeatingHeart venv.

set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT/server"

if [[ ! -x "../.BeatingHeart/bin/alembic" ]]; then
  echo "❌ .BeatingHeart alembic not found."
  echo "Run first: ./scripts/SETUP_BEATING_HEART.sh"
  exit 1
fi

exec ../.BeatingHeart/bin/alembic "$@"
