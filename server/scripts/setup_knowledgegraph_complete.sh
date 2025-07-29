#!/bin/bash

set -e

echo "🚀 Setting up PostgreSQL Knowledge Graph database..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    POSTGRES_USER=$(whoami)
    WAL_ARCHIVE_DIR="/usr/local/var/postgresql/wal_archive"
    BACKUP_DIR="/usr/local/var/backups/pg"
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    BACKUP_SCRIPT="$SCRIPT_DIR/pg_backup_knowledgegraph.sh"
else
    OS="linux"
    POSTGRES_USER="postgres"
    WAL_ARCHIVE_DIR="/var/lib/postgresql/wal_archive"
    BACKUP_DIR="/var/backups/pg"
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    BACKUP_SCRIPT="$SCRIPT_DIR/pg_backup_knowledgegraph.sh"
fi

echo "📁 Creating WAL archive directory..."
if [[ "$OS" == "macos" ]]; then
    mkdir -p "$WAL_ARCHIVE_DIR"
    chmod 750 "$WAL_ARCHIVE_DIR"
else
    sudo mkdir -p "$WAL_ARCHIVE_DIR"
    sudo chown postgres:postgres "$WAL_ARCHIVE_DIR"
    sudo chmod 750 "$WAL_ARCHIVE_DIR"
fi

echo "📁 Creating backup directory..."
if [[ "$OS" == "macos" ]]; then
    mkdir -p "$BACKUP_DIR"
    chmod 750 "$BACKUP_DIR"
else
    sudo mkdir -p "$BACKUP_DIR"
    sudo chown postgres:postgres "$BACKUP_DIR"
    sudo chmod 750 "$BACKUP_DIR"
fi

echo "🔄 Restarting PostgreSQL to apply WAL configuration..."
if [[ "$OS" == "macos" ]]; then
    if brew services list | grep -q postgresql; then
        brew services restart postgresql@14 2>/dev/null || brew services restart postgresql@15 2>/dev/null || brew services restart postgresql
    else
        echo "⚠️ Please restart PostgreSQL manually (e.g., brew services restart postgresql@14)"
    fi
else
    sudo systemctl restart postgresql
fi

echo "🗄️ Creating knowledge graph database and schemas..."
cp "$SCRIPT_DIR/setup_knowledgegraph.sql" /tmp/setup_knowledgegraph.sql

if [[ "$OS" == "macos" ]]; then
    psql postgres -f /tmp/setup_knowledgegraph.sql
else
    sudo -u postgres psql -f /tmp/setup_knowledgegraph.sql
fi

echo "📝 Setting up backup script permissions..."
chmod +x "$BACKUP_SCRIPT"

echo "⏰ Setting up daily backup cron job..."
if [[ "$OS" == "macos" ]]; then
    sed -i.bak "s|/var/backups/pg|$BACKUP_DIR|g" "$BACKUP_SCRIPT"
    (crontab -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT") | crontab -
else
    (sudo crontab -u postgres -l 2>/dev/null; echo "0 2 * * * $BACKUP_SCRIPT") | sudo crontab -u postgres -
fi

echo "✅ Knowledge graph database setup complete!"
echo ""
echo "Database: knowledgegraph"
echo "Schemas: ontology, ehr, text, molecular, guidelines"
echo "WAL: Enabled with logical level and archiving"
echo "Backups: Daily at 2 AM, stored in $BACKUP_DIR"
echo ""
echo "Verification commands:"
if [[ "$OS" == "macos" ]]; then
    echo "1. psql -d knowledgegraph -c '\dn'"
    echo "2. psql -c 'SHOW wal_level; SHOW archive_mode;'"
    echo "3. crontab -l"
else
    echo "1. sudo -u postgres psql -d knowledgegraph -c '\dn'"
    echo "2. sudo -u postgres psql -c 'SHOW wal_level; SHOW archive_mode;'"
    echo "3. sudo crontab -u postgres -l"
fi
