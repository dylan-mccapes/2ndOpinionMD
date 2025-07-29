#!/bin/bash

set -e

echo "🚀 Setting up PostgreSQL Knowledge Graph database..."

echo "📁 Creating WAL archive directory..."
sudo mkdir -p /var/lib/postgresql/wal_archive
sudo chown postgres:postgres /var/lib/postgresql/wal_archive
sudo chmod 750 /var/lib/postgresql/wal_archive

echo "📁 Creating backup directory..."
sudo mkdir -p /var/backups/pg
sudo chown postgres:postgres /var/backups/pg
sudo chmod 750 /var/backups/pg

echo "🔄 Restarting PostgreSQL to apply WAL configuration..."
sudo systemctl restart postgresql

echo "🗄️ Creating knowledge graph database and schemas..."
sudo -u postgres psql -f /home/ubuntu/repos/2ndOpinionMD-MVP/server/scripts/setup_knowledgegraph.sql

echo "📝 Setting up backup script permissions..."
chmod +x /home/ubuntu/repos/2ndOpinionMD-MVP/server/scripts/pg_backup_knowledgegraph.sh

echo "⏰ Setting up daily backup cron job..."
(sudo crontab -u postgres -l 2>/dev/null; echo "0 2 * * * /home/ubuntu/repos/2ndOpinionMD-MVP/server/scripts/pg_backup_knowledgegraph.sh") | sudo crontab -u postgres -

echo "✅ Knowledge graph database setup complete!"
echo ""
echo "Database: knowledgegraph"
echo "Schemas: ontology, ehr, text, molecular, guidelines"
echo "WAL: Enabled with logical level and archiving"
echo "Backups: Daily at 2 AM, stored in /var/backups/pg/"
echo ""
echo "Verification commands:"
echo "1. sudo -u postgres psql -d knowledgegraph -c '\dn'"
echo "2. sudo -u postgres psql -c 'SHOW wal_level; SHOW archive_mode;'"
echo "3. sudo crontab -u postgres -l"
