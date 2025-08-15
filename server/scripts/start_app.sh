#!/bin/bash

set -e

echo "🚀 Starting 2ndOpinionMD-MVP with PostgreSQL..."

cd /home/ubuntu/repos/2ndOpinionMD-MVP/server

if ! sudo systemctl is-active --quiet postgresql; then
    echo "🔧 Starting PostgreSQL service..."
    sudo systemctl start postgresql
fi

if [ ! -f ".deps_installed" ]; then
    echo "📦 Installing Python dependencies..."
    pip install -r requirements.txt
    touch .deps_installed
fi

echo "🗄️ Running database migrations..."
alembic upgrade head

echo "📊 Checking ICD-10 data..."
python -c "
import asyncio
import sys
sys.path.append('.')
from server.db.session import SessionLocal
from sqlalchemy import text

async def check_data():
    async with SessionLocal() as session:
        result = await session.execute(text('SELECT COUNT(*) FROM medical_knowledge'))
        count = result.scalar()
        if count == 0:
            print('⚠️ No ICD-10 data found. Loading...')
            return False
        else:
            print(f'✅ Found {count} medical knowledge entries')
            return True

if not asyncio.run(check_data()):
    exit(1)
" || {
    echo "📥 Loading ICD-10 data..."
    python scripts/load_icd10_data.py
}

echo "🌟 Starting FastAPI application..."
echo "App will be available at: http://localhost:8000"
python scripts/run_postgres_app.py
