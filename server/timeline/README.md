# EoH Timeline Engine

The EoH Timeline Engine is the backbone of 2ndOpinionMD's Patient Timeline system, powering autoimmune flare prediction, probabilistic diagnostic landscape mapping, trajectory analysis, symptom/lab clustering, and clinician-auditable EoH reasoning.

## Overview

The Timeline Engine converts raw patient documents (journals, labs, messages, imaging summaries, clinician notes, medication logs, etc.) into a unified normalized timeline, stores them in PostgreSQL with pgvector embeddings, and enables ANN (Approximate Nearest Neighbor) search for pattern matching and flare prediction.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Timeline Engine                               │
├─────────────────────────────────────────────────────────────────────┤
│  Ingestion Layer (ingest.py)                                        │
│  ├── Document Parser (PDF, OCR, plaintext, JSON)                    │
│  ├── Timestamp Extraction                                           │
│  ├── Event Type Classification                                      │
│  └── Structured Data Extraction (labs, symptoms, meds, imaging)     │
├─────────────────────────────────────────────────────────────────────┤
│  Core Engine (engine.py)                                            │
│  ├── Embedding Generation (text-embedding-3-small)                  │
│  ├── Timeline Storage & Retrieval                                   │
│  ├── ANN Search (pgvector HNSW)                                     │
│  ├── Flare Precursor Detection                                      │
│  ├── Flare Prediction                                               │
│  └── Diagnostic Landscape Estimation                                │
├─────────────────────────────────────────────────────────────────────┤
│  Data Models (models.py)                                            │
│  ├── TimelineEvent, TimelineEventCreate                             │
│  ├── LabResult, SymptomData, MedicationData                         │
│  ├── FlareData, VisitData, ImagingData                              │
│  ├── FlarePrecursor, FlareSignature, FlarePrediction                │
│  └── DiagnosticLandscape, FlareReport, TimelineContext              │
├─────────────────────────────────────────────────────────────────────┤
│  API Routes (timeline_routes.py)                                    │
│  ├── GET /api/timeline/{patient_id}                                 │
│  ├── POST /api/timeline/{patient_id}/events                         │
│  ├── POST /api/timeline/{patient_id}/search                         │
│  ├── GET /api/eoh/flarereport/{patient_id}                          │
│  ├── GET /api/eoh/landscape/{patient_id}                            │
│  └── GET /api/eoh/flareprediction/{patient_id}                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Database Schema

The timeline data is stored in the `ehr.patient_timeline` table:

```sql
CREATE TABLE ehr.patient_timeline (
    id BIGSERIAL PRIMARY KEY,
    patient_id TEXT NOT NULL,
    ts TIMESTAMP WITH TIME ZONE NOT NULL,
    event_type TEXT NOT NULL,
    source TEXT NOT NULL,
    structured JSONB,
    text TEXT,
    embedding VECTOR(1536),
    meta JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

Key indexes:
- `(patient_id, ts DESC)` - Fast chronological queries
- `HNSW (embedding vector_cosine_ops)` - Fast ANN search
- `GIN (structured)` - JSONB queries
- `GIN (to_tsvector(text))` - Full-text search

## Event Types

The system supports the following event types:

| Event Type | Description | Structured Fields |
|------------|-------------|-------------------|
| `lab` | Laboratory results | test_name, value, unit, reference_range, flag |
| `symptom` | Patient-reported symptoms | symptom_name, severity, location, duration |
| `medication` | Medication records | medication_name, dose, frequency, route, status |
| `imaging` | Imaging studies | modality, body_part, findings, impression |
| `flare` | Disease flare events | severity, duration_days, joints_involved, triggers |
| `note` | Clinical notes | note_type, author, content |
| `self_report` | Patient self-reports | report_type, content |
| `visit` | Clinical visits | visit_type, provider, location, chief_complaint |
| `med_change` | Medication changes | medication_name, change_type, old_dose, new_dose |
| `journal` | Patient journal entries | mood, energy_level, content |

## CLI Usage

### Ingest Documents

Process a directory of patient documents:

```bash
python -m server.timeline.ingest --patient-id PATIENT123 --path /path/to/documents
```

Options:
- `--patient-id` (required): Patient identifier
- `--path` (required): Path to directory containing documents
- `--source`: Source identifier (default: "patient_upload")
- `--recursive`: Process subdirectories recursively
- `--dry-run`: Parse documents without storing to database

### Supported File Formats

- `.txt` - Plain text files
- `.json` - JSON documents (structured or unstructured)
- `.pdf` - PDF documents (text extraction)
- `.md` - Markdown files

## API Endpoints

### Timeline Reconstruction

```http
GET /api/timeline/{patient_id}
```

Query parameters:
- `start_date`: Filter events after this date (ISO 8601)
- `end_date`: Filter events before this date (ISO 8601)
- `event_types`: Comma-separated list of event types to include
- `limit`: Maximum number of events (default: 100)
- `offset`: Pagination offset

Response:
```json
{
  "patient_id": "PATIENT123",
  "events": [
    {
      "id": 1,
      "ts": "2024-01-15T10:30:00Z",
      "event_type": "lab",
      "source": "EHR",
      "structured": {
        "test_name": "CRP",
        "value": 2.5,
        "unit": "mg/L",
        "flag": "high"
      },
      "text": "CRP elevated at 2.5 mg/L (reference: <1.0 mg/L)"
    }
  ],
  "total_count": 150,
  "span_days": 365
}
```

### Semantic Search

```http
POST /api/timeline/{patient_id}/search
```

Request body:
```json
{
  "query": "joint pain and swelling",
  "limit": 10,
  "threshold": 0.7
}
```

Response:
```json
{
  "results": [
    {
      "event": { ... },
      "similarity": 0.85
    }
  ]
}
```

### Flare Report

```http
GET /api/eoh/flarereport/{patient_id}
```

Response:
```json
{
  "patient_id": "PATIENT123",
  "generated_at": "2024-01-20T15:00:00Z",
  "flare_forecast": "Based on recent inflammatory marker trends and symptom patterns, there is a moderate probability of flare activity in the next 2-4 weeks.",
  "differential_landscape": {
    "ra_like": 0.41,
    "sle_like": 0.22,
    "psa_like": 0.15,
    "sjogren_like": 0.07,
    "mixed_ctd_like": 0.10,
    "other": 0.05
  },
  "key_precursors": [
    {
      "event_id": 145,
      "description": "CRP rising trend over 3 weeks",
      "similarity": 0.82
    }
  ],
  "risk_drivers": [
    "Rising inflammatory markers (CRP, ESR)",
    "Increasing morning stiffness duration",
    "Recent medication gap"
  ],
  "guidance_for_clinician": [
    "Consider closer monitoring of inflammatory markers",
    "Review medication adherence",
    "Assess for early intervention opportunities"
  ]
}
```

### Diagnostic Landscape

```http
GET /api/eoh/landscape/{patient_id}
```

Response:
```json
{
  "patient_id": "PATIENT123",
  "diagnostic_probabilities": {
    "ra_like": 0.41,
    "sle_like": 0.22,
    "psa_like": 0.15,
    "sjogren_like": 0.07,
    "mixed_ctd_like": 0.10,
    "vasculitis_like": 0.0,
    "other": 0.05
  },
  "drivers": [
    "Joint-centric flare clustering",
    "Symmetric small joint involvement",
    "RF positivity pattern",
    "CRP oscillation with flares"
  ],
  "confidence": 0.75,
  "event_count": 150
}
```

## EoH Router Integration

The Timeline Engine integrates with the EoH Router to provide timeline context for conceptual reasoning.

### Enable Timeline Context

Add `use_timeline=1` and `timeline_patient_id=PATIENT123` to the `/api/rag/eoh_stream` endpoint:

```http
GET /api/rag/eoh_stream?q=...&use_timeline=1&timeline_patient_id=PATIENT123
```

### SSE Events

When timeline is enabled, the following SSE events are emitted:

| Event | Description |
|-------|-------------|
| `timeline_loaded` | Timeline successfully loaded with event count and span |
| `timeline_signals` | Key signals extracted from timeline |
| `timeline_flare_features` | Flare-related features detected |
| `timeline_probabilistic_differential` | Diagnostic landscape probabilities |
| `patient_timeline_ctx` | Timeline context injected into fused context |

## Flare Prediction

The flare prediction system uses ANN search to compare patient trajectories against known flare signatures.

### Flare Signatures

The system includes synthetic flare signatures for common autoimmune patterns:

1. **RA Flare Pattern**: Rising CRP/ESR, morning stiffness >60min, symmetric joint involvement
2. **Lupus Flare Pattern**: Rising anti-dsDNA, complement consumption, fatigue + rash
3. **PsA Flare Pattern**: Enthesitis, dactylitis, skin flare preceding joint symptoms
4. **General Inflammatory**: Non-specific inflammatory marker elevation

### Precursor Detection

The `find_flare_precursors()` function identifies events that historically precede flares:

- Rising inflammatory markers (CRP, ESR)
- Symptom clusters (fatigue + joint pain + morning stiffness)
- Medication gaps or changes
- Sleep disturbance patterns

## Regulatory Compliance

All outputs from the Timeline Engine are designed to be:

- **Probabilistic**: All predictions are expressed as probabilities, not certainties
- **Transparent**: All reasoning is auditable with clear evidence trails
- **Non-diagnostic**: The system provides pattern analysis, not medical diagnoses

The `_like` suffix on diagnostic categories (e.g., `ra_like`, `sle_like`) emphasizes that these are pattern similarities, not diagnoses.

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

### Quick Start: Test Seed Data Generation

```bash
# Test all patient types (dry run - no database writes)
python -m server.timeline.seed_data --patient-id TEST_ALL --type all --dry-run

# Test specific patient types
python -m server.timeline.seed_data --patient-id TEST_RA --type ra --dry-run
python -m server.timeline.seed_data --patient-id TEST_SLE --type sle --dry-run
python -m server.timeline.seed_data --patient-id TEST_PSA --type psa --dry-run
```

**Expected Output:** No errors, JSON output showing generated events.

### Run Timeline Tests

```bash
# Run all timeline tests
python -m pytest tests/timeline/ -v

# Run specific test modules
python -m pytest tests/timeline/test_normalizer.py -v
python -m pytest tests/timeline/test_parser.py -v

# Run with coverage
python -m pytest tests/timeline/ -v --cov=server.timeline
```

### Test Normalization Contracts

```bash
# Verify normalization contracts
python -c "
from server.timeline.normalizer import NormalizedLab, NormalizedSymptom

# Test LAB normalization
lab = NormalizedLab(test_name='CRP', value=15.5, unit='mg/L', flag='high')
print('LAB:', lab.model_dump())

# Test SYMPTOM normalization (numeric severity mapping)
symptom = NormalizedSymptom(severity='7')
print('Severity 7 maps to:', symptom.severity)  # Should be 'severe'
"
```

### Test Error Taxonomy

```bash
# Verify error classification
python -c "
from server.timeline.utils import ErrorType, classify_error

try:
    raise FileNotFoundError('test.txt')
except Exception as e:
    print(f'FileNotFoundError -> {classify_error(e)}')

try:
    raise UnicodeDecodeError('utf-8', b'', 0, 1, 'test')
except Exception as e:
    print(f'UnicodeDecodeError -> {classify_error(e)}')
"
```

### Run ANN Tests

```bash
# Run flare prediction tests
python -m pytest tests/ann/test_flare.py -v

# Run diagnostic landscape tests
python -m pytest tests/ann/test_diagnostic.py -v

# Run all ANN tests
python -m pytest tests/ann/ -v
```

### Run Safety Tests

```bash
# Run EoH validator tests
python -m pytest tests/eoh/test_validators.py -v

# Test forbidden language detection
python -c "
from server.eoh.validators import check_forbidden_language

text = 'The patient has rheumatoid arthritis'
violations = check_forbidden_language(text)
print(f'Violations found: {len(violations)}')
"
```

### Full Test Suite

```bash
# Run all tests
python -m pytest tests/ -v

# Run with verbose output and stop on first failure
python -m pytest tests/ -v -x --tb=short
```

## Development

### Running Tests

```bash
pytest tests/timeline/ -v
```

### Adding New Event Types

1. Add the event type to `EventType` enum in `models.py`
2. Create structured data model if needed
3. Add extraction patterns to `ingest.py`
4. Update documentation

### Adding New Flare Signatures

1. Define the signature in `engine.py` `_init_flare_signatures()`
2. Include characteristic events, markers, and patterns
3. Generate embedding for the signature
4. Test against known patient trajectories

## Files

- `server/timeline/__init__.py` - Module exports
- `server/timeline/models.py` - Pydantic data models
- `server/timeline/engine.py` - Core timeline engine
- `server/timeline/ingest.py` - Document ingestion and parsing
- `server/api/timeline_routes.py` - FastAPI routes
- `database/schemas/ehr_timeline.sql` - Database schema

## Dependencies

- `openai` - Embedding generation (text-embedding-3-small)
- `pgvector` - Vector similarity search
- `sqlalchemy` - Database ORM
- `pydantic` - Data validation
- `fastapi` - API framework
