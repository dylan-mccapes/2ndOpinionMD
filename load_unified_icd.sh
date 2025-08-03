#!/bin/bash

set -e  # Exit on any error

echo "🚀 Starting Unified ICD Loader Pipeline..."
echo "================================================"

if ! pg_isready -q; then
    echo "❌ PostgreSQL is not running. Please start it first."
    exit 1
fi

REQUIRED_FILES=(
    "unified_icd_schema.sql"
    "load_unified_icd10cm.py"
    "load_unified_icd11.py"
    "map_icd_systems.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Required file not found: $file"
        exit 1
    fi
done

ICD10CM_FILE="${1:-~/attachments/70008085-ece6-488f-a112-d08662f67f56/icd10cm-0425.txt}"
ICD11_FILE="${2:-~/attachments/547b9ae0-85d3-437d-ad7b-55a2d4b93598/icd11-2026.txt}"

ICD10CM_FILE=$(eval echo "$ICD10CM_FILE")
ICD11_FILE=$(eval echo "$ICD11_FILE")

echo "📁 Input files:"
echo "   ICD-10-CM: $ICD10CM_FILE"
echo "   ICD-11:    $ICD11_FILE"

if [ ! -f "$ICD10CM_FILE" ]; then
    echo "❌ ICD-10-CM file not found: $ICD10CM_FILE"
    echo "Usage: $0 [icd10cm_file] [icd11_file]"
    exit 1
fi

if [ ! -f "$ICD11_FILE" ]; then
    echo "❌ ICD-11 file not found: $ICD11_FILE"
    echo "Usage: $0 [icd10cm_file] [icd11_file]"
    exit 1
fi

echo "✅ All prerequisites met"
echo ""

echo "🏗️  Step 1: Setting up unified database schema..."
sudo cp unified_icd_schema.sql /tmp/ && sudo chmod 644 /tmp/unified_icd_schema.sql
sudo -u postgres psql -d knowledgegraph -f /tmp/unified_icd_schema.sql
echo "✅ Schema setup completed"
echo ""

echo "📥 Step 2: Loading ICD-10-CM data..."
python3 load_unified_icd10cm.py "$ICD10CM_FILE"
echo "✅ ICD-10-CM loading completed"
echo ""

echo "🌐 Step 3: Loading ICD-11 data..."
python3 load_unified_icd11.py "$ICD11_FILE"
echo "✅ ICD-11 loading completed"
echo ""

echo "🔗 Step 4: Generating cross-system mappings..."
python3 map_icd_systems.py 0.75
echo "✅ Cross-system mapping completed"
echo ""

echo "🔍 Step 5: Final verification..."
sudo -u postgres psql -d knowledgegraph -c "
SELECT 
    system,
    COUNT(*) as total_codes,
    COUNT(*) FILTER (WHERE term_vector IS NOT NULL) as with_vectors,
    COUNT(*) FILTER (WHERE parent_code IS NOT NULL) as with_parents
FROM ontology.icd 
GROUP BY system
ORDER BY system;
"

echo ""
sudo -u postgres psql -d knowledgegraph -c "
SELECT 
    'Cross-references' as table_name,
    COUNT(*) as total_mappings,
    COUNT(*) FILTER (WHERE confidence >= 0.80) as high_confidence,
    COUNT(*) FILTER (WHERE confidence >= 0.90) as very_high_confidence,
    ROUND(AVG(confidence), 3) as avg_confidence
FROM ontology.code_cross_references;
"

echo ""
echo "🎉 Unified ICD Loader Pipeline Completed Successfully!"
echo "================================================"
echo "📊 Database: knowledgegraph.ontology.icd"
echo "🔗 Cross-references: knowledgegraph.ontology.code_cross_references"
echo ""
echo "You can now query the unified ICD data using PostgreSQL."
