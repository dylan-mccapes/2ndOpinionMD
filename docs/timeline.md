# Timeline Engine Documentation

**Version:** v100 (Cipher + Devin Method)  
**Location:** `server/timeline/`

## Overview

The Timeline Engine handles ingestion, normalization, and storage of patient timeline events. It converts raw documents (journals, labs, messages, imaging summaries, clinician notes, medication logs) into a unified normalized timeline stored in PostgreSQL with pgvector embeddings for ANN search.

## Directory Structure

```
server/timeline/
├── __init__.py
├── ingest.py          # Main ingestion pipeline (10 stages)
├── parser.py          # Document parsing and field extraction
├── normalizer.py      # Normalization contracts (v100)
├── schema.sql         # Database schema
├── utils.py           # Error taxonomy and utilities
├── engine.py          # Timeline engine class
├── models.py          # Pydantic models
├── seed_data.py       # Synthetic patient data generator
└── README.md          # Module documentation
```

## Normalization Contracts

Every parsed document MUST be transformed into this structure:

```json
{
  "ts": "<timestamp>",
  "event_type": "<string>",
  "source": "<string>",
  "structured": {...},
  "text": "<normalized_narrative>",
  "meta": {...}
}
```

### Event Types

| Type | Description |
|------|-------------|
| `lab` | Laboratory test results |
| `symptom` | Patient-reported symptoms |
| `medication` | Medication events |
| `imaging` | Imaging study results |
| `flare` | Disease flare events |
| `note` | Clinical notes |
| `self_report` | Patient self-reports |

### Source Types

| Source | Description |
|--------|-------------|
| `patient_upload` | Patient-uploaded documents |
| `EHR` | Electronic Health Record |
| `synced_device` | Synced device data |
| `clinician_note` | Clinician notes |

### Structured Field Requirements

#### LAB Events
```json
{
  "test_name": "CRP",
  "value": 15.5,
  "unit": "mg/L",
  "reference_range": "<5",
  "flag": "high"  // high | low | normal | unknown
}
```

#### SYMPTOM Events
```json
{
  "primary_symptom": "joint pain",
  "severity": "moderate",  // mild | moderate | severe
  "duration": "2 weeks",
  "body_regions": ["hands", "wrists"],
  "modifiers": ["bilateral", "morning stiffness"]
}
```

#### MEDICATION Events
```json
{
  "drug": "methotrexate",
  "dose": "15mg",
  "frequency": "weekly",
  "changes": "started",
  "adherence_gaps": null
}
```

#### IMAGING Events
```json
{
  "modality": "x-ray",
  "impression": "Joint space narrowing",
  "key_findings": ["erosions", "soft tissue swelling"]
}
```

#### FLARE Events
```json
{
  "severity": "moderate",  // mild | moderate | severe
  "duration": "2 weeks",
  "affected_regions": ["hands", "knees"],
  "trigger_pattern": "medication gap"
}
```

## Error Taxonomy

All errors are classified into exactly 10 types:

| Error Type | Description | Fix Workflow |
|------------|-------------|--------------|
| `IO_ERROR` | File read/write errors | Verify path, skip if missing |
| `ENCODING_ERROR` | Character encoding issues | Try utf-8 → latin-1 → chardet |
| `PARSE_ERROR` | Document parsing failures | Fallback to raw text |
| `SCHEMA_MISMATCH` | Schema validation errors | Update mapping, not schema |
| `CONSTRAINT_VIOLATION` | DB constraint errors | Deduplicate, normalize PK |
| `TYPE_CAST_ERROR` | Type conversion errors | Coerce or set null |
| `DATA_INTEGRITY_ERROR` | Corrupt data | Skip file, log |
| `EMBEDDING_ERROR` | Embedding generation errors | Retry 3x, store with null |
| `ANN_INDEX_ERROR` | Index errors | Rebuild index once |
| `API_MODEL_ERROR` | API call errors | Exponential backoff 3x |

---

## Terminal Testing Instructions

### Prerequisites

```bash
# Navigate to the repository
cd /path/to/2ndOpinionMD-MVP

# Activate virtual environment
source server/venv312/bin/activate

# Ensure dependencies are installed
pip install -r server/requirements.txt
```

### 1. Test Seed Data Generation (Dry Run)

Generate synthetic patient data without database writes:

```bash
# Test all patient types
python -m server.timeline.seed_data --patient-id TEST_ALL --type all --dry-run

# Test RA-like patient
python -m server.timeline.seed_data --patient-id TEST_RA --type ra --dry-run

# Test SLE-like patient
python -m server.timeline.seed_data --patient-id TEST_SLE --type sle --dry-run

# Test PsA-like patient
python -m server.timeline.seed_data --patient-id TEST_PSA --type psa --dry-run
```

**Expected Output:**
- No errors
- JSON output showing generated events
- Event counts for each type

### 2. Test Normalizer Module

```bash
# Run normalizer tests
python -m pytest tests/timeline/test_normalizer.py -v

# Run specific test class
python -m pytest tests/timeline/test_normalizer.py::TestNormalizedLab -v

# Run with coverage
python -m pytest tests/timeline/test_normalizer.py -v --cov=server.timeline.normalizer
```

**Expected Output:**
- All tests pass
- Coverage report showing normalization contract coverage

### 3. Test Parser Module

```bash
# Run parser tests
python -m pytest tests/timeline/test_parser.py -v

# Test timestamp extraction
python -m pytest tests/timeline/test_parser.py::TestExtractTimestamp -v

# Test event type identification
python -m pytest tests/timeline/test_parser.py::TestIdentifyEventType -v
```

**Expected Output:**
- All tests pass
- Timestamp extraction works for ISO, date-only, meta, and filename formats
- Event type identification correctly classifies lab, symptom, medication, imaging, flare

### 4. Test Error Handling

```bash
# Test error taxonomy
python -c "
from server.timeline.utils import ErrorType, classify_error

# Test error classification
try:
    raise FileNotFoundError('test.txt')
except Exception as e:
    error_type = classify_error(e)
    print(f'FileNotFoundError -> {error_type}')

try:
    raise UnicodeDecodeError('utf-8', b'', 0, 1, 'test')
except Exception as e:
    error_type = classify_error(e)
    print(f'UnicodeDecodeError -> {error_type}')
"
```

**Expected Output:**
```
FileNotFoundError -> ErrorType.IO_ERROR
UnicodeDecodeError -> ErrorType.ENCODING_ERROR
```

### 5. Test Full Timeline Test Suite

```bash
# Run all timeline tests
python -m pytest tests/timeline/ -v

# Run with verbose output
python -m pytest tests/timeline/ -v --tb=short

# Run and stop on first failure
python -m pytest tests/timeline/ -v -x
```

**Expected Output:**
- All tests pass
- No forbidden language in outputs
- Normalization contracts enforced

### 6. Verify Normalization Contracts

```bash
# Interactive verification
python -c "
from server.timeline.normalizer import (
    NormalizedLab, NormalizedSymptom, NormalizedMedication,
    NormalizedImaging, NormalizedFlare
)

# Test LAB normalization
lab = NormalizedLab(
    test_name='CRP',
    value=15.5,
    unit='mg/L',
    reference_range='<5',
    flag='high'
)
print('LAB:', lab.model_dump())

# Test SYMPTOM normalization
symptom = NormalizedSymptom(
    primary_symptom='joint pain',
    severity='moderate',
    duration='2 weeks',
    body_regions=['hands', 'wrists'],
    modifiers=['bilateral']
)
print('SYMPTOM:', symptom.model_dump())

# Test severity mapping (numeric to category)
symptom_numeric = NormalizedSymptom(severity='7')
print('Severity 7 maps to:', symptom_numeric.severity)
"
```

**Expected Output:**
- LAB shows all required fields
- SYMPTOM shows all required fields
- Numeric severity 7 maps to "severe"

### 7. Test Idempotency

```bash
# Generate events twice and verify no duplicates
python -c "
from server.timeline.seed_data import generate_ra_like_patient

# Generate twice
events1 = generate_ra_like_patient('TEST_IDEM')
events2 = generate_ra_like_patient('TEST_IDEM')

print(f'First run: {len(events1)} events')
print(f'Second run: {len(events2)} events')
print('Idempotency check: Events are deterministic')
"
```

---

## Database Setup

### Create Schema

```bash
# Connect to PostgreSQL
psql -U postgres -d your_database

# Run schema creation
\i server/timeline/schema.sql

# Verify table exists
\dt ehr.patient_timeline

# Verify indexes
\di ehr.*
```

### Schema Definition

```sql
CREATE TABLE ehr.patient_timeline (
    id BIGSERIAL PRIMARY KEY,
    patient_id TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    structured JSONB,
    text TEXT,
    embedding VECTOR(1536),
    meta JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX ON ehr.patient_timeline (patient_id, ts DESC);
CREATE INDEX ON ehr.patient_timeline USING hnsw (embedding vector_cosine_ops);
```

---

## API Endpoints

### GET /api/timeline/{patient_id}

Returns chronologically ordered, normalized timeline.

```bash
# Test endpoint
curl -X GET "http://localhost:8000/api/timeline/TEST_RA"
```

**Response:**
```json
{
  "patient_id": "TEST_RA",
  "events": [
    {
      "ts": "2024-01-15T10:30:00Z",
      "event_type": "lab",
      "source": "EHR",
      "structured": {...},
      "text": "CRP elevated at 15.5 mg/L"
    }
  ],
  "total_events": 50
}
```

---

## Troubleshooting

### Common Issues

1. **Pydantic Validation Errors**
   ```bash
   # Check model definitions
   python -c "from server.timeline.models import *; print('Models OK')"
   ```

2. **Import Errors**
   ```bash
   # Verify module structure
   python -c "from server.timeline import normalizer, parser, utils; print('Imports OK')"
   ```

3. **Database Connection**
   ```bash
   # Test connection
   python -c "
   import os
   print('DATABASE_URL:', os.environ.get('DATABASE_URL', 'Not set'))
   "
   ```

### Logs

Error logs are written to `logs/timeline/YYYYMMDD.log`:

```bash
# View today's logs
cat logs/timeline/$(date +%Y%m%d).log

# Tail logs in real-time
tail -f logs/timeline/$(date +%Y%m%d).log
```
