#!/usr/bin/env bash
# Install PostgreSQL + pgvector on the RTX-4090 / PortalNode-0 box.
#
# Target: Ubuntu — native Linux OR WSL2 (recommended on a Windows 4090 host).
# If SSH lands in PowerShell, run this script *inside* WSL, not in Windows:
#   wsl -d Ubuntu -- bash -lc "sudo bash ~/portalnode4090_install_postgres.sh"
# Or use scripts/portalnode4090_wsl.ps1 -Install from PowerShell.
#
# Pure Linux SSH:
#   scp scripts/portalnode4090_install_postgres.sh dylan@HOST:~/
#   ssh dylan@HOST 'bash -lc "sudo bash ~/portalnode4090_install_postgres.sh"'
#
# Windows OpenSSH: scp to user@host:~/ lands in C:\Users\<user>\, not WSL. Copy into WSL first:
#   wsl -d Ubuntu -- cp /mnt/c/Users/dylan/portalnode4090_install_postgres.sh ~/
#   wsl -d Ubuntu -- chmod +x ~/portalnode4090_install_postgres.sh
# Or: scripts/portalnode4090_wsl.ps1 -StageInstallFromWindowsProfile -Install
#
# Env (optional):
#   PORTALNODE_DB_NAME=portalnode
#   PORTALNODE_DB_USER=portalnode
#   PORTALNODE_DB_PASSWORD=...   if unset, a random password is printed once

set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

DB_NAME="${PORTALNODE_DB_NAME:-portalnode}"
DB_USER="${PORTALNODE_DB_USER:-portalnode}"

if ! command -v lsb_release >/dev/null 2>&1; then
  echo "lsb_release not found; install lsb-release or run on Ubuntu." >&2
  exit 1
fi

CODENAME="$(lsb_release -cs)"
VERSION_ID="$(lsb_release -rs)"
echo "Detected Ubuntu ${VERSION_ID} (${CODENAME})"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y

# Pick PostgreSQL major + pgvector package available on this release.
PG_MAJOR=""
if apt-cache show postgresql-16-pgvector &>/dev/null; then
  PG_MAJOR=16
elif apt-cache show postgresql-15-pgvector &>/dev/null; then
  PG_MAJOR=15
elif apt-cache show postgresql-14-pgvector &>/dev/null; then
  PG_MAJOR=14
else
  echo "No postgresql-*-pgvector package found in apt. Enable universe and retry:" >&2
  echo "  sudo add-apt-repository universe && sudo apt-get update" >&2
  exit 1
fi

echo "Installing PostgreSQL ${PG_MAJOR} + pgvector…"
apt-get install -y \
  "postgresql-${PG_MAJOR}" \
  "postgresql-client-${PG_MAJOR}" \
  "postgresql-contrib-${PG_MAJOR}" \
  "postgresql-${PG_MAJOR}-pgvector"

systemctl enable "postgresql@${PG_MAJOR}-main.service" 2>/dev/null || true
systemctl restart "postgresql@${PG_MAJOR}-main.service" 2>/dev/null || systemctl restart postgresql

# --- Role + database ---------------------------------------------------------
if [[ -z "${PORTALNODE_DB_PASSWORD:-}" ]]; then
  PORTALNODE_DB_PASSWORD="$(openssl rand -base64 24 | tr -d '/+=' | head -c 24)"
  GENERATED_PW=1
else
  GENERATED_PW=0
fi

sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${PORTALNODE_DB_PASSWORD}';
  ELSE
    ALTER ROLE ${DB_USER} WITH PASSWORD '${PORTALNODE_DB_PASSWORD}';
  END IF;
END
\$\$;

ALTER ROLE ${DB_USER} CREATEDB;
SQL

if sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  echo "Database ${DB_NAME} already exists."
else
  sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}"
fi

sudo -u postgres psql -v ON_ERROR_STOP=1 -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};"

sudo -u postgres psql -v ON_ERROR_STOP=1 -d "${DB_NAME}" <<SQL
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
SQL

echo ""
echo "PostgreSQL ${PG_MAJOR} + pgvector installed."
echo "  Database: ${DB_NAME}"
echo "  Role:     ${DB_USER}"
if [[ "${GENERATED_PW}" -eq 1 ]]; then
  echo "  Password: ${PORTALNODE_DB_PASSWORD}"
  echo "  (save this in .env on the 4090 — it was randomly generated)"
else
  echo "  Password: (from PORTALNODE_DB_PASSWORD env)"
fi
echo ""
echo "DSN (socket, same host as app):"
echo "  postgresql://${DB_USER}:${PORTALNODE_DB_PASSWORD}@/${DB_NAME}?host=/var/run/postgresql"
echo ""
echo "Optional: restrict TCP to localhost (default on Ubuntu). Peer auth for local user is typical; for password auth from Docker, edit pg_hba.conf."
