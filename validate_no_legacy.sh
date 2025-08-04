#!/bin/bash
echo "🔍 Scanning for remaining legacy dependencies..."

echo "Searching for MongoDB/ChromaDB/Express imports..."
grep -r -E "mongo|motor|chroma|mongoose" . --exclude-dir={.git,venv,node_modules,build} --include="*.py" --include="*.js" --include="*.json" || echo "✅ No legacy imports found"

echo ""
echo "Checking requirements.txt for legacy packages..."
if grep -E "pymongo|motor|chromadb" server/requirements.txt; then
    echo "❌ Legacy packages found in requirements.txt"
    exit 1
else
    echo "✅ No legacy packages in requirements.txt"
fi

echo ""
echo "Checking package.json for legacy packages..."
if grep -E "mongodb|mongoose" package.json; then
    echo "❌ Legacy packages found in package.json"
    exit 1
else
    echo "✅ No legacy packages in package.json"
fi

echo ""
echo "✅ Legacy cleanup validation complete!"
