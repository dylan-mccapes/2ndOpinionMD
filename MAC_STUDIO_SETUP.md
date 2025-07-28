# Mac Studio Setup Instructions

## Prerequisites

1. **Install PostgreSQL and pgvector:**
```bash
brew install postgresql@14 pgvector
brew services start postgresql@14
```

2. **Add PostgreSQL to PATH (if needed):**
```bash
echo 'export PATH="/opt/homebrew/opt/postgresql@14/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

3. **Create database and user:**
```bash
createdb 2ndopinionmd
psql -c "CREATE USER devin WITH PASSWORD 'devin123';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE 2ndopinionmd TO devin;"
psql 2ndopinionmd -c "CREATE EXTENSION vector;"
```

4. **Fix database permissions (run after migrations):**
```bash
# Grant proper permissions to devin user for all tables
psql 2ndopinionmd -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO devin;"
psql 2ndopinionmd -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO devin;"
psql 2ndopinionmd -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO devin;"
```

## Configuration

1. **Update .env file:**
Ensure your `.env` file in the project root contains:
```
DATABASE_URL=postgresql+asyncpg://devin:devin123@2ndopinionmd.ai:5432/2ndopinionmd
ICD10_MAIN_CODES_FILE=~/Documents/2ndOpinionMD-data/icd10cm-codes-2026.txt
ICD10_ADDENDA_FILE=~/Documents/2ndOpinionMD-data/icd10cm-codes-addenda-2026.txt
```

2. **Create ICD-10 data directory:**
```bash
mkdir -p ~/Documents/2ndOpinionMD-data
```

3. **Download ICD-10 data files:**
You need to obtain these files and place them in `~/Documents/2ndOpinionMD-data/`:
- `icd10cm-codes-2026.txt`
- `icd10cm-codes-addenda-2026.txt`

Alternatively, the application will also check for these files in the project's `server/data/icd10/` directory.

## Running the Application

1. **Install Python dependencies:**
```bash
cd server
pip install -r requirements.txt
```

2. **Run database migrations:**
```bash
alembic upgrade head
```

3. **Fix database permissions (IMPORTANT):**
```bash
# Grant proper permissions to devin user
psql 2ndopinionmd -c "GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO devin;"
psql 2ndopinionmd -c "GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO devin;"
psql 2ndopinionmd -c "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO devin;"
```

4. **Load ICD-10 data:**
```bash
python scripts/load_icd10_data.py
```

5. **Start the application:**
```bash
python scripts/run_postgres_app.py
```

The application will be available at http://localhost:3000

## Frontend Setup

1. **Install frontend dependencies:**
```bash
cd ~/Sites/2ndOpinionMD-MVP  # or wherever you cloned the repo
npm install
```

2. **Start the React development server:**
```bash
npm start
```

The React frontend will start on port 3001 (or another available port if 3001 is busy). It's configured to connect to the PostgreSQL backend running on port 3000.

3. **Access the application:**
- Backend API: http://localhost:3000
- API Documentation: http://localhost:3000/docs  
- Frontend Application: http://localhost:3001

## Complete Application Stack

With both servers running, you have:
- **PostgreSQL Database**: Running locally with 75,206 ICD-10 entries
- **FastAPI Backend**: Port 3000 with full API endpoints
- **React Frontend**: Port 3001 with user interface
- **Vector Search**: pgvector-powered medical knowledge search

## Troubleshooting

### PostgreSQL Issues
- If `psql` command is not found, ensure PostgreSQL is properly installed and added to PATH
- Try using the full path: `/opt/homebrew/opt/postgresql@14/bin/psql`
- Restart PostgreSQL service: `brew services restart postgresql@14`

### Database Connection Issues
- Verify PostgreSQL is running: `brew services list | grep postgresql`
- Check database exists: `psql -l | grep 2ndopinionmd`
- Verify user permissions: `psql 2ndopinionmd -c "\du"`

### ICD-10 Data File Issues
- Ensure files exist in one of the supported locations
- Check file permissions: `ls -la ~/Documents/2ndOpinionMD-data/`
- Verify file format (should be plain text files with ICD-10 codes)

## File Locations

The application checks for ICD-10 data files in this order:
1. Environment variables (`ICD10_MAIN_CODES_FILE`, `ICD10_ADDENDA_FILE`)
2. User Documents directory (`~/Documents/2ndOpinionMD-data/`)
3. Project data directory (`server/data/icd10/`)

This provides flexibility for different deployment scenarios while maintaining ease of setup.
