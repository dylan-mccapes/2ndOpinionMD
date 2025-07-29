#!/bin/bash

set -e

TIMESTAMP=$(date +%F-%H%M)
BACKUP_DIR="/var/backups/pg"
DATABASE="knowledgegraph"
BACKUP_FILE="$BACKUP_DIR/knowledgegraph_$TIMESTAMP.backup"

echo "Starting backup of $DATABASE database..."
pg_dump -F c -b -v -f "$BACKUP_FILE" "$DATABASE"

if [ $? -eq 0 ]; then
    echo "Backup completed successfully: $BACKUP_FILE"
    
    find "$BACKUP_DIR" -name "knowledgegraph_*.backup" -mtime +7 -delete
    echo "Old backups cleaned up (kept last 7 days)"
else
    echo "Backup failed!"
    exit 1
fi
