#!/usr/bin/env bash
# Drop and recreate the PortalNode MKG target database after a failed or partial
# restore (e.g. ERROR: schema "b2b" already exists when re-running 02_*.sql.gz).
#
# Run inside WSL/Ubuntu on the 4090 host:
#   sudo bash scripts/portalnode4090_reset_mkg_target_db.sh
#
# Env (optional, must match portalnode4090_install_postgres.sh):
#   PORTALNODE_DB_NAME=portalnode
#   PORTALNODE_DB_USER=portalnode
#
# Then re-run:
#   export PGUSER PGDATABASE PGPASSWORD DUMP_DIR  # as for restore
#   ./scripts/portalnode4090_restore_mkg.sh

set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

DB_NAME="${PORTALNODE_DB_NAME:-portalnode}"
DB_USER="${PORTALNODE_DB_USER:-portalnode}"

sudo -u postgres dropdb --if-exists "$DB_NAME"
sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"

sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres \
  -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

sudo -u postgres psql -v ON_ERROR_STOP=1 -d "${DB_NAME}" <<SQL
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
SQL

echo "Database ${DB_NAME} is empty and ready. Re-run: ./scripts/portalnode4090_restore_mkg.sh"
