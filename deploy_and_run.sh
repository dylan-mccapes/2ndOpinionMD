#!/bin/bash
# Deploy index.html to nginx webroot, reload nginx, then start the app server.
# Run from the 2ndOpinionMD-MVP project root.
#
# Usage:
#   ./deploy_and_run.sh            # deploy + reload + start app
#   ./deploy_and_run.sh --no-app   # deploy + reload only (skip app server)

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

NGINX_WEBROOT="/opt/homebrew/var/www/2ndopinionmd"
INDEX_SRC="$SCRIPT_DIR/index.html"
INDEX_DEST="$NGINX_WEBROOT/index.html"

# -----------------------------------------------------------------------
# 0. Pull latest code
# -----------------------------------------------------------------------
echo "⬇️  Pulling latest code..."
git pull origin "$(git rev-parse --abbrev-ref HEAD)"
echo "   ✅ Up to date"

# -----------------------------------------------------------------------
# 1. Deploy index.html
# -----------------------------------------------------------------------
echo "📄 Deploying index.html → $INDEX_DEST"
sudo cp "$INDEX_SRC" "$INDEX_DEST"
echo "   ✅ Copied"

# -----------------------------------------------------------------------
# 2. Test and reload nginx
# -----------------------------------------------------------------------
echo "🔧 Testing nginx config..."
sudo nginx -t
echo "🔄 Reloading nginx..."
sudo nginx -s reload
echo "   ✅ nginx reloaded"

# -----------------------------------------------------------------------
# 3. Start app server (unless --no-app passed)
# -----------------------------------------------------------------------
if [[ "$1" == "--no-app" ]]; then
    echo "⏭️  Skipping app server (--no-app)"
    exit 0
fi

if [[ ! -d ".BeatingHeart" ]]; then
    echo "❌ .BeatingHeart venv not found. Run ./SETUP_BEATING_HEART.sh first."
    exit 1
fi

echo "🚀 Starting 2OPMD app server..."
source .BeatingHeart/bin/activate
exec python server/scripts/run_postgres_app.py "$@"
