#!/usr/bin/env bash
# Sync the splash + lab UI into the Homebrew nginx tree for 2ndopinionmd.
# Default docroot: /opt/homebrew/var/www/2ndopinionmd
#   - index.html         &larr; root splash (this repo's 2ndOpinionMD-MVP/index.html)
#   - assets/            &larr; PTV conceptual images referenced by the splash
#   - rag-demo/index.html &larr; lab / vault SPA (not linked from the splash)
#
# Usage:
#   ./scripts/deploy_rag_demo_mac.sh
#   RAG_DEMO_WWW=/custom/www ./scripts/deploy_rag_demo_mac.sh

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_MVP="$(cd "${SCRIPT_DIR}/.." && pwd)"
DST="${RAG_DEMO_WWW:-/opt/homebrew/var/www/2ndopinionmd}"

mkdir -p "${DST}/rag-demo" "${DST}/assets"

install -m 0644 "${REPO_MVP}/index.html"           "${DST}/index.html"
install -m 0644 "${REPO_MVP}/rag-demo/index.html"  "${DST}/rag-demo/index.html"

# Splash assets (PTV conceptual images, etc.)
shopt -s nullglob
for asset in "${REPO_MVP}/assets/"*; do
  install -m 0644 "${asset}" "${DST}/assets/$(basename "${asset}")"
done
shopt -u nullglob

echo "Deployed:"
echo "  ${DST}/index.html (splash)"
echo "  ${DST}/assets/*"
echo "  ${DST}/rag-demo/index.html"
