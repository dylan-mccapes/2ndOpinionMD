#!/bin/bash

set -e  # Exit on any error

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
cd "$ROOT"

echo "🚀 Starting ICD-10-CM Setup..."

if ! pg_isready -q; then
    echo "❌ PostgreSQL is not running. Please start it with: brew services start postgresql"
    exit 1
fi

KG_SQL="database/sql/setup_knowledgegraph.sql"
if [ ! -f "$KG_SQL" ]; then
    echo "❌ $KG_SQL not found (expected under database/sql/)"
    exit 1
fi

if [ ! -f "ontology_loaders/icd/load_icd10cm.py" ]; then
    echo "❌ ontology_loaders/icd/load_icd10cm.py not found"
    exit 1
fi

ICD_FILE="$1"
if [ -z "$ICD_FILE" ]; then
    echo "📁 Please provide the path to your ICD-10-CM file:"
    echo "Usage: ./scripts/setup_icd10cm.sh /path/to/icd10cm-order-April-2025.txt"
    exit 1
fi

if [ ! -f "$ICD_FILE" ]; then
    echo "❌ ICD-10-CM file not found: $ICD_FILE"
    exit 1
fi

echo "✅ All required files found"

echo "📊 Creating knowledgegraph database..."
psql postgres -c "DROP DATABASE IF EXISTS knowledgegraph;" 2>/dev/null || true
psql postgres -c "CREATE DATABASE knowledgegraph;"

echo "🏗️  Setting up database schema..."
psql -d knowledgegraph -f "$KG_SQL"

echo "📥 Importing ICD-10-CM data..."
python3 ontology_loaders/icd/load_icd10cm.py "$ICD_FILE"

echo "🔍 Verifying import..."
python3 scripts/verify_icd_import.py

echo ""
echo "🎉 ICD-10-CM setup completed successfully!"
echo "📊 Database: knowledgegraph.ontology.icd"
echo "🔗 You can now query the data using PostgreSQL"
