# PostgreSQL Migration Guide for 2ndOpinionMD

This document outlines the migration from MongoDB and ChromaDB to PostgreSQL with pgvector for the 2ndOpinionMD application.

## Overview

The migration includes:

1. Replacing MongoDB with PostgreSQL for relational data storage
2. Replacing ChromaDB with pgvector for vector embeddings and similarity search
3. Integrating ICD-10 medical data with standardized codes
4. Maintaining all existing features (user authentication, journaling, symptom intake)

## Setup Instructions

### 1. Install PostgreSQL and pgvector

```bash
# Install PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Install pgvector extension
sudo apt install postgresql-server-dev-14  # Use your PostgreSQL version
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

### 2. Update Environment Variables

Update your `.env` file with PostgreSQL connection details:

```
DATABASE_URL=postgresql+asyncpg://username:password@localhost:5432/2ndopinionmd
```

### 3. Run Database Setup Script

```bash
cd ~/repos/2ndOpinionMD-MVP/server
python scripts/setup_postgres.py
```

### 4. Run Database Migrations

```bash
cd ~/repos/2ndOpinionMD-MVP/server
alembic upgrade head
```

### 5. Migrate Existing Data

```bash
cd ~/repos/2ndOpinionMD-MVP/server
python scripts/migrate_mongodb_to_postgresql.py
```

### 6. Load ICD-10 Data

```bash
cd ~/repos/2ndOpinionMD-MVP/server
python scripts/load_icd10_data.py
```

### 7. Start the PostgreSQL-based Application

```bash
cd ~/repos/2ndOpinionMD-MVP/server
python scripts/run_postgres_app.py
```

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR UNIQUE NOT NULL,
    full_name VARCHAR NOT NULL,
    hashed_password VARCHAR NOT NULL,
    birthdate TIMESTAMP,
    subscription_tier VARCHAR DEFAULT 'basic',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE,
    verification_token VARCHAR,
    verification_token_expires TIMESTAMP,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP,
    password_reset_token VARCHAR,
    password_reset_token_expires TIMESTAMP
);
```

### Journal Entries Table

```sql
CREATE TABLE journal_entries (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    symptoms JSONB,
    environmental_factors JSONB,
    stress_level INTEGER,
    diet_notes TEXT,
    sleep_quality INTEGER,
    notes TEXT,
    analysis TEXT,
    pattern_observations TEXT,
    ai_analysis JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP
);
```

### Medical Knowledge Table

```sql
CREATE TABLE medical_knowledge (
    id UUID PRIMARY KEY,
    content_type VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    content TEXT NOT NULL,
    icd10_code VARCHAR,
    metadata JSONB,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Vector Search Implementation

The pgvector extension enables efficient vector similarity search in PostgreSQL:

```sql
-- Example query for finding similar medical knowledge
SELECT id, title, content, icd10_code, 
       embedding <-> :query_embedding as distance
FROM medical_knowledge
ORDER BY embedding <-> :query_embedding
LIMIT 5;
```

## ICD-10 Data Integration

The ICD-10 data is processed from XML files and loaded into the `medical_knowledge` table with the following structure:

- `content_type`: Type of medical data (e.g., "icd10_condition", "icd10_drug")
- `title`: Name of the condition or drug
- `content`: Detailed description
- `icd10_code`: The standardized ICD-10 code
- `metadata`: Additional information
- `embedding`: Vector representation for similarity search

## API Changes

The API endpoints remain the same, but the implementation has been updated to use PostgreSQL:

- `/api/journal` - Create and retrieve journal entries
- `/api/journal/{entry_id}` - Get or delete a specific journal entry
- `/api/journal/timeline/{user_id}` - Get timeline data for journal entries

## Troubleshooting

### Connection Issues

If you encounter connection issues with PostgreSQL:

1. Check that PostgreSQL is running: `sudo systemctl status postgresql`
2. Verify connection parameters in `.env` file
3. Ensure pgvector extension is installed: `SELECT * FROM pg_extension WHERE extname = 'vector';`

### Migration Issues

If data migration fails:

1. Check MongoDB connection parameters
2. Ensure PostgreSQL tables are created correctly
3. Run the migration script with verbose logging: `python -m scripts.migrate_mongodb_to_postgresql --verbose`

### Vector Search Issues

If vector search is not working correctly:

1. Verify embeddings are being generated and stored correctly
2. Check that pgvector extension is enabled in the database
3. Test vector similarity search directly in PostgreSQL
