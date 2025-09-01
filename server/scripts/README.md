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

# RxNorm Data Ingestion

This directory also contains scripts for ingesting RxNorm (RxNorm Full Monthly) data into the PostgreSQL database.

## RxNorm Usage

### Ingest RxNorm Data

Using hosted ZIP URL (recommended):
```bash
source server/venv312/bin/activate
python server/scripts/ingest_rxnorm.py --zip-url https://2ndopinionmd.ai/private/rxnorm-token/rxnorm.zip
```

Using local ZIP file:
```bash
source server/venv312/bin/activate
python server/scripts/ingest_rxnorm.py --zip /path/to/RxNorm_full_current.zip
```

### Makefile Targets

```bash
# Import RxNorm data
make rxnorm-import ZIP_URL=https://2ndopinionmd.ai/private/rxnorm-token/rxnorm.zip

# Ensure trigram index for fast search
make rxnorm-trgm-index
```

### RxNorm Options

- `--zip PATH`: Path to local RxNorm ZIP file
- `--zip-url URL`: URL to download RxNorm ZIP file
- `--schema SCHEMA`: Database schema (default: ontology)
- `--dry-run`: Run without committing changes

## RxNorm API Usage

After ingesting data, you can search RxNorm terms via the API:

```bash
# Search for drugs by name
curl -s "http://localhost:8000/api/rxnorm/search?q=ibuprofen&limit=5" | jq
curl -s "http://localhost:8000/api/rxnorm/search?q=acetaminophen&tty=SCD,SBD&limit=10" | jq

# Get drug details by RXCUI
curl -s "http://localhost:8000/api/rxnorm/drug/5640" | jq   # if 5640 exists

# Look up by NDC (11-digit or hyphenated format)
curl -s "http://localhost:8000/api/rxnorm/ndc/00093015001" | jq
curl -s "http://localhost:8000/api/rxnorm/ndc/0009-3015-01" | jq

# Using Makefile helpers
make api-rxnorm-search Q=ibuprofen LIMIT=5
make api-rxnorm-search Q=acetaminophen TTY=SCD,SBD LIMIT=10
make api-rxnorm-drug RXCUI=5640
make api-rxnorm-ndc NDC=00093015001
```

## RxNorm Database Schema

The script creates the following tables in the `ontology` schema:

- `rxnorm_conso`: Core concept names and TTY codes (PK: rxaui)
- `rxnorm_rel`: Relationships between concepts (PK: rui)  
- `rxnorm_sat`: Attributes including NDCs (PK: atui)
- `rxnorm_ndc`: Derived NDC mapping table with normalized 11-digit NDCs

## RxNorm Verification

Check data was loaded correctly:

```bash
# Verify table counts
psql -d 2ndopinionmd -c "SELECT count(*) FROM ontology.rxnorm_conso;"

# Verify ibuprofen exists (smoke test)
psql -d 2ndopinionmd -c "SELECT rxcui,str,tty FROM ontology.rxnorm_conso WHERE LOWER(str) LIKE '%ibuprofen%' LIMIT 5;"

# Verify NDC mappings
psql -d 2ndopinionmd -c "SELECT count(*) FROM ontology.rxnorm_ndc;"
```

## RxNorm Features

- **RRF Format Support**: Handles pipe-delimited RRF files with trailing pipes
- **NDC Normalization**: Converts NDCs to 11-digit format (5-4-2 segments)
- **Fast Text Search**: Uses pg_trgm GIN indexes for drug name search
- **Idempotent Loading**: Safe to run multiple times with upserts
- **Smoke Tests**: Verifies ibuprofen/acetaminophen presence
- **Bulk Loading**: Uses PostgreSQL COPY for fast RRF data loading
