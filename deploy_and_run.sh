#!/bin/bash
# Deploy Epistemic Vault index.html to nginx web root and (re)start the backend.
#
# Steps:
#   1. sudo cp index.html -> /opt/homebrew/var/www/2ndopinionmd/
#   2. nginx -t, then sudo nginx -s reload (fallback to `brew services restart nginx`)
#   3. Free port 8000 (lsof + kill), waiting briefly for graceful exit
#   4. exec ./RUN_POSTGRES_APP.sh
#
# Run from 2ndOpinionMD-MVP directory (or anywhere; script cd's to its own dir).
# Prompts once for sudo password at the top so nginx ops do not block later.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

SRC_INDEX="$SCRIPT_DIR/index.html"
DEST_DIR="/opt/homebrew/var/www/2ndopinionmd"
DEST_INDEX="$DEST_DIR/index.html"
APP_PORT="${APP_PORT:-8000}"

log() { printf '\033[1;36m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[deploy]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31m[deploy ERROR]\033[0m %s\n' "$*" >&2; exit 1; }

# ── Preflight ────────────────────────────────────────────────────────────────
[[ -f "$SRC_INDEX" ]] || die "index.html not found at $SRC_INDEX"
[[ -d "$DEST_DIR"  ]] || die "web root $DEST_DIR missing (install nginx config first)"
[[ -x "$SCRIPT_DIR/RUN_POSTGRES_APP.sh" ]] || die "RUN_POSTGRES_APP.sh missing or not executable"

# Warm the sudo cache so the rest runs without prompting mid-flight.
log "Requesting sudo (one prompt for nginx ops)…"
sudo -v

# ── 1. Deploy index.html ─────────────────────────────────────────────────────
log "Copying index.html → $DEST_INDEX"
sudo cp -p "$SRC_INDEX" "$DEST_INDEX"
sudo chmod 644 "$DEST_INDEX"
SRC_SIZE=$(wc -c < "$SRC_INDEX" | tr -d ' ')
DST_SIZE=$(sudo wc -c < "$DEST_INDEX" | tr -d ' ')
if [[ "$SRC_SIZE" != "$DST_SIZE" ]]; then
  die "Size mismatch after copy (src=$SRC_SIZE dst=$DST_SIZE)"
fi
log "Deployed ($SRC_SIZE bytes)."

# ── 2. Reload nginx ──────────────────────────────────────────────────────────
if command -v nginx >/dev/null 2>&1; then
  log "nginx -t"
  if sudo nginx -t; then
    if sudo nginx -s reload 2>/dev/null; then
      log "nginx reloaded."
    else
      warn "nginx -s reload failed; trying brew services restart nginx"
      if command -v brew >/dev/null 2>&1; then
        brew services restart nginx || warn "brew services restart nginx failed"
      else
        warn "brew not found; skipping service restart"
      fi
    fi
  else
    die "nginx config test failed; not reloading"
  fi
else
  warn "nginx binary not found on PATH; skipping reload"
fi

# ── 3. Free port $APP_PORT ──────────────────────────────────────────────────
log "Checking port $APP_PORT"
PIDS=$(lsof -ti tcp:"$APP_PORT" -sTCP:LISTEN 2>/dev/null || true)
if [[ -n "${PIDS}" ]]; then
  log "Killing listeners on :$APP_PORT → PIDs: $(echo "$PIDS" | tr '\n' ' ')"
  kill $PIDS 2>/dev/null || true
  # Give them up to 5 seconds to exit gracefully
  for _ in 1 2 3 4 5; do
    sleep 1
    REMAIN=$(lsof -ti tcp:"$APP_PORT" -sTCP:LISTEN 2>/dev/null || true)
    [[ -z "$REMAIN" ]] && break
  done
  REMAIN=$(lsof -ti tcp:"$APP_PORT" -sTCP:LISTEN 2>/dev/null || true)
  if [[ -n "$REMAIN" ]]; then
    warn "Force-killing stubborn PIDs: $(echo "$REMAIN" | tr '\n' ' ')"
    kill -9 $REMAIN 2>/dev/null || true
    sleep 1
  fi
else
  log "Port $APP_PORT is free."
fi

# ── 4. Start backend ─────────────────────────────────────────────────────────
log "Starting backend via ./RUN_POSTGRES_APP.sh"
exec "$SCRIPT_DIR/RUN_POSTGRES_APP.sh" "$@"
