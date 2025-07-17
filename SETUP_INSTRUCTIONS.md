# PostgreSQL Setup Instructions for 2ndOpinionMD-MVP

## Quick Start (Automated)

### For Linux/Ubuntu:
```bash
# 1. Run the complete setup script
cd ~/repos/2ndOpinionMD-MVP/server
chmod +x scripts/setup_complete_postgres.sh
bash scripts/setup_complete_postgres.sh

# 2. Start the application
chmod +x scripts/start_app.sh
bash scripts/start_app.sh
```

### For macOS:
```bash
# 1. Install PostgreSQL and pgvector
brew install postgresql@15 pgvector
brew services start postgresql@15

# 2. Create database and user
createdb 2ndopinionmd
psql 2ndopinionmd -c "CREATE EXTENSION vector;"
psql -c "CREATE USER devin WITH PASSWORD 'devin123';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE 2ndopinionmd TO devin;"

# 3. Update .env file (if needed)
cd ~/repos/2ndOpinionMD-MVP
# Ensure DATABASE_URL=postgresql+asyncpg://devin:devin123@localhost:5432/2ndopinionmd

# 4. Start the application
cd server
bash scripts/start_app.sh
```

## Manual Setup (Step-by-Step)

### 1. Install PostgreSQL and pgvector

**Linux/Ubuntu:**
```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib postgresql-server-dev-all build-essential git

# Install pgvector
cd /tmp
git clone --branch v0.5.1 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install

# Start PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

**macOS:**
```bash
brew install postgresql@15 pgvector
brew services start postgresql@15
```

### 2. Create Database and User

```bash
# Create database
sudo -u postgres createdb 2ndopinionmd  # Linux
createdb 2ndopinionmd                   # macOS

# Create user and grant permissions
sudo -u postgres psql -c "CREATE USER devin WITH PASSWORD 'devin123';"  # Linux
psql -c "CREATE USER devin WITH PASSWORD 'devin123';"                   # macOS

sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE 2ndopinionmd TO devin;"  # Linux
psql -c "GRANT ALL PRIVILEGES ON DATABASE 2ndopinionmd TO devin;"                   # macOS

# Enable pgvector extension
sudo -u postgres psql -d 2ndopinionmd -c "CREATE EXTENSION IF NOT EXISTS vector;"  # Linux
psql 2ndopinionmd -c "CREATE EXTENSION vector;"                                     # macOS
```

### 3. Install Python Dependencies

```bash
cd ~/repos/2ndOpinionMD-MVP/server
pip install -r requirements.txt
```

### 4. Run Database Migrations

```bash
# Run Alembic migrations to create tables
alembic upgrade head
```

### 5. Load ICD-10 Data

```bash
# Load the 52,060 ICD-10 medical knowledge entries
python scripts/load_icd10_data.py
```

### 6. Start the Application

```bash
# Start the FastAPI server
python scripts/run_postgres_app.py
```

The application will be available at: **http://localhost:8000**

## Verification

To verify everything is working:

1. **Check database connection:**
   ```bash
   python scripts/test_full_migration.py
   ```

2. **Check API endpoints:**
   - Visit http://localhost:8000/docs for API documentation
   - Test user registration/login
   - Create journal entries with symptoms

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running: `sudo systemctl status postgresql` (Linux) or `brew services list | grep postgresql` (macOS)
- Check DATABASE_URL in `.env` file matches your setup
- Verify user permissions: `psql -U devin -d 2ndopinionmd -c "SELECT 1;"`

### pgvector Extension Issues
- Verify extension is installed: `psql 2ndopinionmd -c "SELECT * FROM pg_extension WHERE extname = 'vector';"`
- If missing, reinstall pgvector following the installation steps above

### ICD-10 Data Loading Issues
- Ensure XML files are present in `~/attachments/` directory
- Check OpenAI API key in `.env` file (currently uses dummy embeddings if invalid)
- Verify database has write permissions

## Configuration

The `.env` file contains the database configuration:
```
DATABASE_URL=postgresql+asyncpg://devin:devin123@localhost:5432/2ndopinionmd
```

Update this if you use different credentials or database names.
