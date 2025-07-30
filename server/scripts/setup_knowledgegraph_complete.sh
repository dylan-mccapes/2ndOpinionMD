#!/bin/bash

set -e

echo "🚀 Setting up PostgreSQL Knowledge Graph database..."

if [[ "$OSTYPE" == "darwin"* ]] && [[ $EUID -eq 0 ]]; then
    echo "❌ ERROR: Do not run this script with 'sudo' on macOS!"
    echo "   macOS PostgreSQL (Homebrew) uses your regular user account, not root."
    echo "   Please run: ./scripts/setup_knowledgegraph_complete.sh"
    echo "   (without sudo)"
    exit 1
fi

if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    POSTGRES_USER=$(whoami)
    WAL_ARCHIVE_DIR="/usr/local/var/postgresql/wal_archive"
    BACKUP_DIR="/usr/local/var/backups/pg"
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    BACKUP_SCRIPT="$SCRIPT_DIR/pg_backup_knowledgegraph.sh"
    
    if ! psql --version &>/dev/null; then
        echo "❌ ERROR: PostgreSQL not found or not accessible."
        echo ""
        echo "📦 Please install PostgreSQL and required extensions first:"
        echo "   brew install postgresql@14 pgvector"
        echo "   brew services start postgresql@14"
        echo ""
        echo "📋 Then create the initial database:"
        echo "   createdb postgres"
        echo "   psql postgres -c \"CREATE EXTENSION IF NOT EXISTS pg_trgm;\""
        echo ""
        echo "🔄 After installation, run this script again."
        exit 1
    fi
    
    if ! brew services list | grep -q "postgresql.*started"; then
        echo "⚠️  PostgreSQL service not running. Starting it now..."
        if ! brew services start postgresql@14 2>/dev/null && ! brew services start postgresql@15 2>/dev/null && ! brew services start postgresql 2>/dev/null; then
            echo "❌ ERROR: Failed to start PostgreSQL service."
            echo "   Please install PostgreSQL first: brew install postgresql@14 pgvector"
            exit 1
        fi
        sleep 2
    fi
    
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
        echo "⏳ Waiting for PostgreSQL to fully start..."
        sleep 3
        
        for i in {1..10}; do
            if psql postgres -c "SELECT 1;" &>/dev/null; then
                echo "✅ PostgreSQL is ready"
                break
            fi
            echo "⏳ Waiting for PostgreSQL... (attempt $i/10)"
            sleep 2
        done
        
        if ! psql postgres -c "SELECT 1;" &>/dev/null; then
            echo "❌ ERROR: PostgreSQL failed to start properly after restart"
            echo "   Please check service status: brew services list | grep postgresql"
            echo "   Try manual restart: brew services restart postgresql@14"
            exit 1
        fi
    else
        echo "⚠️ Please restart PostgreSQL manually (e.g., brew services restart postgresql@14)"
    fi
else
    sudo systemctl restart postgresql
    sleep 2
fi

echo "Connecting to PostgreSQL as user: $(whoami)"

if ! psql postgres -c "SELECT 1 FROM pg_available_extensions WHERE name = 'vector';" &>/dev/null; then
    echo "❌ ERROR: pgvector extension not available."
    echo "   Please install pgvector: brew install pgvector"
    echo "   Then restart PostgreSQL: brew services restart postgresql@14"
    exit 1
fi

if ! psql postgres -c "SELECT 1 FROM pg_available_extensions WHERE name = 'pg_trgm';" &>/dev/null; then
    echo "❌ ERROR: pg_trgm extension not available."
    echo "   This should be included with PostgreSQL. Try reinstalling:"
    echo "   brew reinstall postgresql@14"
    exit 1
fi

echo "🗄️ Creating knowledge graph database and schemas..."

if [[ "$OS" == "macos" ]]; then
    TEMP_SQL_FILE="$HOME/.setup_knowledgegraph_temp.sql"
    cp "$SCRIPT_DIR/setup_knowledgegraph.sql" "$TEMP_SQL_FILE"
    
    if psql -h localhost postgres -f "$TEMP_SQL_FILE" 2>/dev/null; then
        echo "Connected via localhost"
    elif psql -h /usr/local/var/postgresql postgres -f "$TEMP_SQL_FILE" 2>/dev/null; then
        echo "Connected via /usr/local/var/postgresql socket"
    elif psql -h /opt/homebrew/var/postgresql postgres -f "$TEMP_SQL_FILE" 2>/dev/null; then
        echo "Connected via /opt/homebrew/var/postgresql socket (Apple Silicon)"
    elif psql postgres -f "$TEMP_SQL_FILE" 2>/dev/null; then
        echo "Connected via default method"
    else
        echo "❌ ERROR: Could not connect to PostgreSQL after installation verification."
        echo "   PostgreSQL is installed but not accessible. Please check:"
        echo "   1. Service status: brew services list | grep postgresql"
        echo "   2. Manual connection: psql postgres"
        echo "   3. Service logs: brew services info postgresql@14"
        echo "   4. Try restarting: brew services restart postgresql@14"
        rm -f "$TEMP_SQL_FILE"
        exit 1
    fi
    
    rm -f "$TEMP_SQL_FILE"
else
    cp "$SCRIPT_DIR/setup_knowledgegraph.sql" /tmp/setup_knowledgegraph.sql
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
    echo ""
    echo "⚠️  IMPORTANT: On macOS, always run this script WITHOUT 'sudo'"
    echo "   PostgreSQL uses your regular user account, not root."
else
    echo "1. sudo -u postgres psql -d knowledgegraph -c '\dn'"
    echo "2. sudo -u postgres psql -c 'SHOW wal_level; SHOW archive_mode;'"
    echo "3. sudo crontab -u postgres -l"
fi
