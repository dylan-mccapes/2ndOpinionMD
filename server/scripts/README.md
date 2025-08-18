# LOINC Data Ingestion

This directory contains scripts for ingesting LOINC (Logical Observation Identifiers Names and Codes) data into the PostgreSQL database.

## Setup

1. Ensure your `.env` file contains the `DATABASE_URL`:
   ```
   DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@localhost:5432/2ndopinionmd
   ```

2. Install dependencies:
   ```bash
   pip install -r server/requirements.txt
   ```

## Usage

### Ingest LOINC Data

Using hosted ZIP URL (recommended):
```bash
source server/venv312/bin/activate
python server/scripts/ingest_loinc.py --zip-url https://2ndopinionmd.ai/private/loinc-34efcd3d8beb/loinc.zip
```

Using local ZIP file:
```bash
source server/venv312/bin/activate
python server/scripts/ingest_loinc.py --zip /path/to/loinc.zip
```

### Makefile Target

```bash
make loinc-import ZIP_URL=https://2ndopinionmd.ai/private/loinc-34efcd3d8beb/loinc.zip
```

### Options

- `--zip PATH`: Path to local LOINC ZIP file
- `--zip-url URL`: URL to download LOINC ZIP file
- `--schema SCHEMA`: Database schema (default: ontology)
- `--dry-run`: Run without committing changes

## API Usage

After ingesting data, you can search LOINC terms via the API:

```bash
# Search for glucose-related terms
curl -s "http://localhost:8000/api/loinc/search?q=glucose&limit=5" | jq

# Search with filters
curl -s "http://localhost:8000/api/loinc/search?q=glucose&system=Ser/Plas&limit=5" | jq

# Get specific LOINC term
curl -s "http://localhost:8000/api/loinc/term/2345-7" | jq

# Get panel members
curl -s "http://localhost:8000/api/loinc/panel/24357-6" | jq
```

## Database Schema

The script creates the following tables in the `ontology` schema:

- `loinc_terms`: Core LOINC terms (~104k rows)
- `loinc_panels`: Panel-to-member relationships (~90k rows)
- `loinc_answer_list`: Answer lists (~30k rows)
- `loinc_answer_link`: Links between terms and answer lists
- `loinc_parts`: LOINC parts (~70k rows)
- `loinc_part_link`: Links between terms and parts (~640k rows)

## Verification

Check data was loaded correctly:

```bash
# Verify table counts
psql -d 2ndopinionmd -c "SELECT count(*) FROM ontology.loinc_terms;"

# Verify glucose code exists (smoke test)
psql -d 2ndopinionmd -c "SELECT loinc_num,long_common_name,system,scale_typ FROM ontology.loinc_terms WHERE loinc_num='2345-7';"
```

## Features

- **Idempotent**: Safe to run multiple times without duplicates
- **Bulk Loading**: Uses PostgreSQL COPY for fast data loading
- **Upserts**: Uses `ON CONFLICT DO UPDATE` for data updates
- **Smoke Tests**: Verifies critical data like glucose code 2345-7
- **Progress Logging**: Shows timing and row counts for each table
- **Error Handling**: Comprehensive error messages and cleanup
