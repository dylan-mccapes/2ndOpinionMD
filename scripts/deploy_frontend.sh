#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REACT_DIR="$APP_DIR/frontend/react"
WWW_ROOT="/opt/homebrew/var/www/2ndopinionmd"
STAMP="$(date -u +'%Y%m%d-%H%M%S')"
STAGE="/tmp/2omd-build-$STAMP"
PREV_BACKUP="/tmp/2omd-prev-$STAMP"

# 0) Pre-checks
command -v node >/dev/null || { echo "node not found"; exit 1; }
command -v npm  >/dev/null || { echo "npm not found"; exit 1; }
command -v nginx >/dev/null || { echo "nginx not found"; exit 1; }

echo "Node: $(node -v)  npm: $(npm -v)"

# 1) Build
cd "$REACT_DIR"
# If you need env vars, export them here; prefer relative /api so nginx proxy works:
export REACT_APP_API_BASE="/api"
npm install
npm run build

# 2) Stage with a version stamp (helpful for debugging real builds in prod)
mkdir -p "$STAGE"
cp -R build/* "$STAGE/"
echo "build_stamp: $STAMP" > "$STAGE/version.txt"
git -C "$APP_DIR" rev-parse HEAD >> "$STAGE/version.txt" || true

# 3) Atomic swap: backup current → rsync new → permissions → nginx reload
if [ -d "$WWW_ROOT" ]; then
  sudo mkdir -p "$PREV_BACKUP"
  sudo rsync -a "$WWW_ROOT"/ "$PREV_BACKUP"/
fi

# Use --delete so old hashed assets don’t linger
sudo rsync -a --delete "$STAGE"/ "$WWW_ROOT"/
# Ensure world-readable
sudo find "$WWW_ROOT" -type f -exec chmod 0644 {} \;
sudo find "$WWW_ROOT" -type d -exec chmod 0755 {} \;

# 4) Nginx sanity + reload (no downtime)
sudo nginx -t
sudo nginx -s reload

# 5) Smoke tests (frontend and backend)
set +e
curl -sI https://2ndopinionmd.ai/ | head -n 1
curl -sf https://2ndopinionmd.ai/api/health >/dev/null && echo "API OK" || echo "API check FAILED"
curl -sf https://2ndopinionmd.ai/meta/whoami >/dev/null && echo "Meta OK" || echo "Meta check FAILED"
set -e

echo "✅ Deploy complete: $STAMP"
echo "Backup at: $PREV_BACKUP"

