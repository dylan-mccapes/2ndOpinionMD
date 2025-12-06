#!/usr/bin/env bash
set -euo pipefail

# Adjust these if needed
PROJECT_ROOT="$(pwd)"
DB_NAME="2ndopinionmd"

OUT_DIR="${PROJECT_ROOT}/docker_env_report"
mkdir -p "$OUT_DIR"

log() {
  echo "[$(date +'%F %T')] $*" | tee -a "$OUT_DIR/inspect.log"
}

log "=== 2ndOpinionMD Docker Environment Inspection ==="
log "Project root: $PROJECT_ROOT"
log "Output dir:   $OUT_DIR"

############################
# 0. OS & hardware profile #
############################
log "--- OS & hardware ---"
{
  echo "# OS"
  uname -a || true
  command -v sw_vers >/dev/null 2>&1 && sw_vers || true

  echo
  echo "# CPU"
  sysctl -n machdep.cpu.brand_string 2>/dev/null || true
  sysctl -n hw.ncpu 2>/dev/null || true

  echo
  echo "# Memory"
  vm_stat 2>/dev/null || true

  echo
  echo "# Disk usage (top-level)"
  df -h /
} > "$OUT_DIR/os_hardware.txt"

###################################
# 1. Python / venv / dependencies #
###################################
log "--- Python / venv / deps ---"
{
  echo "# Python executables"
  which python || true
  which python3 || true
  python3 -V 2>/dev/null || true

  echo
  echo "# Virtualenv info"
  echo "VIRTUAL_ENV=${VIRTUAL_ENV:-<not set>}"
  echo "PWD=$(pwd)"
  echo
  echo "# Pip packages (may be big)"
  pip freeze 2>/dev/null || true

  echo
  echo "# Poetry / uv / pipenv (if any)"
  which poetry 2>/dev/null || true
  which uv 2>/dev/null || true
  which pipenv 2>/dev/null || true
} > "$OUT_DIR/python_env.txt"

###################################
# 2. Node / frontend environment  #
###################################
log "--- Node / frontend ---"
{
  echo "# Node / npm / pnpm / yarn"
  node -v 2>/dev/null || true
  npm -v 2>/dev/null || true
  pnpm -v 2>/dev/null || true
  yarn -v 2>/dev/null || true

  echo
  echo "# package.json (if present)"
  if [ -f package.json ]; then
    cat package.json
  else
    echo "No package.json in $PROJECT_ROOT"
  fi
} > "$OUT_DIR/node_frontend.txt"

############################
# 3. Python app structure  #
############################
log "--- Python app structure ---"
{
  echo "# Top-level server/ layout"
  find server -maxdepth 3 -type f \( -name "main.py" -o -name "app.py" -o -name "rag_stream*.py" -o -name "*.py" \) 2>/dev/null | sort

  echo
  echo "# FastAPI entrypoints (grep for FastAPI / APIRouter)"
  rg "FastAPI\(" server 2>/dev/null || true
  rg "APIRouter\(" server 2>/dev/null || true

  echo
  echo "# Makefiles for ingestion / maintenance"
  if [ -d mk ]; then
    ls mk
  fi
} > "$OUT_DIR/python_app_structure.txt"

##########################
# 4. Environment variables
##########################
log "--- Environment variables ---"
{
  echo "# Full env snapshot (caution: check for secrets before sharing)"
  env | sort

  echo
  echo "# Common sensitive / config keys (redacted here manually if needed)"
  env | egrep -i 'OPENAI|API_KEY|POSTGRES|PGHOST|PGPORT|PGUSER|PGPASSWORD|DATABASE_URL|VALYU|REDIS|2NDOPINION|EMBED_MODEL|CHAT_MODEL' || true
} > "$OUT_DIR/env_vars.txt"

##################################
# 5. Postgres: version & settings
##################################
log "--- Postgres: version & settings ---"
{
  echo "# psql version"
  psql --version 2>/dev/null || true

  echo
  echo "# DB version / basic info"
  psql -d "$DB_NAME" -c "SELECT version();" 2>/dev/null || true

  echo
  echo "# Installed extensions"
  psql -d "$DB_NAME" -c "\dx" 2>/dev/null || true

  echo
  echo "# Databases"
  psql -d "$DB_NAME" -c "\l" 2>/dev/null || true
} > "$OUT_DIR/postgres_basic.txt"

log "--- Postgres: schema & indexes ---"
{
  echo "# rag_corpus schema"
  psql -d "$DB_NAME" -c "\d+ rag_corpus" 2>/dev/null || true

  echo
  echo "# Other key tables (ontology, EoH, etc.)"
  psql -d "$DB_NAME" -c "\dn" 2>/dev/null || true
  echo
  echo "# Example EoH views (if present)"
  psql -d "$DB_NAME" -c "\dv eoh_*" 2>/dev/null || true

  echo
  echo "# Indexes on rag_corpus"
  psql -d "$DB_NAME" -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename='rag_corpus';" 2>/dev/null || true
} > "$OUT_DIR/postgres_schema.txt"

log "--- Postgres: performance / memory settings ---"
{
  echo "# Core memory-related settings"
  psql -d "$DB_NAME" -c "SHOW shared_buffers;" 2>/dev/null || true
  psql -d "$DB_NAME" -c "SHOW work_mem;" 2>/dev/null || true
  psql -d "$DB_NAME" -c "SHOW maintenance_work_mem;" 2>/dev/null || true
  psql -d "$DB_NAME" -c "SHOW effective_cache_size;" 2>/dev/null || true
  psql -d "$DB_NAME" -c "SHOW max_connections;" 2>/dev/null || true

  echo
  echo "# pgvector-related settings (if any custom)"
  psql -d "$DB_NAME" -c "SELECT name, setting FROM pg_settings WHERE name LIKE '%hnsw%' OR name LIKE '%ivfflat%';" 2>/dev/null || true

  echo
  echo "# Size of DB and key tables"
  psql -d "$DB_NAME" -c "SELECT pg_size_pretty(pg_database_size(current_database())) AS db_size;" 2>/dev/null || true
  psql -d "$DB_NAME" -c "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) FROM pg_catalog.pg_statio_user_tables ORDER BY pg_total_relation_size(relid) DESC LIMIT 20;" 2>/dev/null || true
} > "$OUT_DIR/postgres_perf.txt"

#######################################
# 6. Running services / ports in use  #
#######################################
log "--- Services / ports ---"
{
  echo "# Brew services"
  brew services list 2>/dev/null || true

  echo
  echo "# Listening ports for core services"
  lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | egrep '(:80|:443|:8000|:5432|:3000)' || true

  echo
  echo "# Processes with 'uvicorn', 'gunicorn', 'nginx', 'postgres'"
  ps aux | egrep 'uvicorn|gunicorn|nginx|postgres' | egrep -v 'egrep' || true
} > "$OUT_DIR/services_ports.txt"

#######################
# 7. Nginx / web tier #
#######################
log "--- Nginx / web tier ---"
{
  echo "# nginx binary and version"
  which nginx 2>/dev/null || true
  nginx -v 2>&1 || true

  echo
  echo "# nginx main config"
  if [ -f /opt/homebrew/etc/nginx/nginx.conf ]; then
    echo "=== /opt/homebrew/etc/nginx/nginx.conf ==="
    cat /opt/homebrew/etc/nginx/nginx.conf
  fi

  echo
  echo "# 2ndOpinionMD-specific vhost (if any)"
  rg "2ndopinionmd" /opt/homebrew/etc/nginx 2>/dev/null || true

  echo
  echo "# SSL cert paths (if you want to inspect for dockerizing TLS termination)"
  find /opt/homebrew/etc/nginx -maxdepth 3 -type f \( -name "*.crt" -o -name "*.pem" -o -name "*.key" \) 2>/dev/null || true
} > "$OUT_DIR/nginx_web.txt"

###################################
# 8. App runtime commands / Make  #
###################################
log "--- App runtime helpers ---"
{
  echo "# Make targets (if using make)"
  if [ -f Makefile ]; then
    cat Makefile
  fi

  echo
  echo "# mk/* files (ingestion, embedding, etc.)"
  if [ -d mk ]; then
    for f in mk/*.mk; do
      echo "=== \$f ==="
      cat "$f"
      echo
    done
  fi

  echo
  echo "# Common startup commands (grep for uvicorn / gunicorn / main)"
  rg "uvicorn" . 2>/dev/null || true
  rg "gunicorn" . 2>/dev/null || true
} > "$OUT_DIR/app_runtime.txt"

##########################
# 9. Cache / temp paths  #
##########################
log "--- Cache / temp / data paths ---"
{
  echo "# Project-level data directories"
  find . -maxdepth 3 -type d \( -name "data" -o -name "db_integrity_reports" -o -name "logs" -o -name "server" \) 2>/dev/null || true

  echo
  echo "# System temp"
  echo "TMPDIR=${TMPDIR:-/tmp}"
  ls -ld "${TMPDIR:-/tmp}" 2>/dev/null || true
} > "$OUT_DIR/cache_paths.txt"

log "=== Inspection complete ==="
log "Artifacts written to: $OUT_DIR"
