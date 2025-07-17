#!/bin/bash

set -e

echo "🚀 Setting up PostgreSQL with pgvector for 2ndOpinionMD-MVP..."

echo "📦 Installing PostgreSQL and dependencies..."
sudo apt update
sudo apt install -y postgresql postgresql-contrib postgresql-server-dev-all build-essential git

echo "📦 Installing pgvector extension..."
cd /tmp
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

echo "🔧 Starting PostgreSQL service..."
sudo systemctl start postgresql
sudo systemctl enable postgresql

echo "🗄️ Creating database and user..."
sudo -u postgres psql -c "CREATE DATABASE \"2ndopinionmd\";" || echo "Database already exists"
sudo -u postgres psql -c "CREATE USER devin WITH PASSWORD 'devin123';" || echo "User already exists"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"2ndopinionmd\" TO devin;"
sudo -u postgres psql -d "2ndopinionmd" -c "CREATE EXTENSION IF NOT EXISTS vector;"

echo "⚙️ Updating .env configuration..."
cd /home/ubuntu/repos/2ndOpinionMD-MVP
sed -i 's|DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://devin:devin123@localhost:5432/2ndopinionmd|' .env

echo "✅ PostgreSQL setup complete!"
echo ""
echo "Next steps:"
echo "1. cd ~/repos/2ndOpinionMD-MVP/server"
echo "2. pip install -r requirements.txt"
echo "3. alembic upgrade head"
echo "4. python scripts/load_icd10_data.py"
echo "5. python scripts/run_postgres_app.py"
