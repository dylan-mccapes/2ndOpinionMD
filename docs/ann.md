# ANN (Approximate Nearest Neighbor) Engine Documentation

**Version:** v100 (Cipher + Devin Method)  
**Location:** `server/ann/`

## Overview

The ANN Engine provides flare prediction and diagnostic landscape estimation using pgvector HNSW indexes. It analyzes patient timeline embeddings to detect flare precursors and estimate probabilistic diagnostic patterns.

## Directory Structure

```
server/ann/
├── __init__.py
├── flare.py           # Flare precursor detection
├── diagnostic.py      # Diagnostic landscape estimation
├── index_builder.py   # HNSW index management
└── utils.py           # ANN utilities
```

## Configuration (MANDATORY - DO NOT CHANGE)

| Parameter | Value |
|-----------|-------|
| Embedding Model | `text-embedding-3-small` |
| Vector Dimension | `1536` |
| ANN Engine | pgvector HNSW |
| Distance Metric | cosine |
| ef_search | `40` |
| ef_construction | `200` |
| M | `16` |

---

## Flare Prediction Engine

**Location:** `server/ann/flare.py`

### Function Signature

```python
def find_flare_precursors(patient_id: str, window_days: int = 90) -> Dict[str, Any]:
    """
    Find flare precursors in patient timeline.
    
    Args:
        patient_id: Patient identifier
        window_days: Lookback window (default 90 days)
        
    Returns:
        {
            "precursors": [...],
            "scores": [...],
            "explanations": [...],
            "flare_likelihood": {"level": "low|medium|high", "explanation": "..."}
        }
    """
```

### Precursor Patterns

The engine detects these precursor patterns:

| Pattern | Description | Indicators |
|---------|-------------|------------|
| `inflammatory_marker_rise` | Rising CRP/ESR | CRP > 10, ESR > 30, trending up |
| `symptom_cluster` | Joint/organ symptom clustering | Multiple related symptoms |
| `medication_lapse` | Medication gaps | Stopped, missed doses |
| `fatigue_sleep_pattern` | Fatigue/sleep disturbance | Fatigue, insomnia, exhaustion |

### Output Schema

```json
{
  "patient_id": "TEST001",
  "window_days": 90,
  "events_analyzed": 45,
  "precursors": [
    {
      "type": "inflammatory_marker_rise",
      "description": "Rising inflammatory markers detected",
      "events": [...]
    }
  ],
  "scores": [0.85, 0.72],
  "explanations": [
    "CRP trending upward from 5 to 25 mg/L over 3 weeks"
  ],
  "flare_likelihood": {
    "level": "high",
    "explanation": "Multiple precursor patterns detected..."
  }
}
```

---

## Diagnostic Landscape Engine

**Location:** `server/ann/diagnostic.py`

### Output Schema (MANDATORY)

```json
{
  "diagnostic_probabilities": {
    "ra_like": 0.41,
    "sle_like": 0.22,
    "psa_like": 0.15,
    "sjogren_like": 0.07,
    "mctd_like": 0.10,
    "other": 0.05
  },
  "drivers": [
    "Lab: RF positive",
    "Lab: elevated CRP",
    "Symptom: symmetric joint pain"
  ]
}
```

### Rules

1. **Values MUST sum to ~1.0** (within 5% tolerance)
2. **Disease names MUST be `*_like`** (except "other")
3. **NO diagnostic statements allowed**

### Pattern Signatures

| Pattern | Lab Indicators | Symptom Indicators |
|---------|---------------|-------------------|
| `ra_like` | RF+, anti-CCP+, CRP↑, ESR↑ | Symmetric joint pain, morning stiffness |
| `sle_like` | ANA+, anti-dsDNA, low C3/C4 | Malar rash, photosensitivity, fatigue |
| `psa_like` | RF-, CRP↑, ESR↑ | Asymmetric joint pain, dactylitis, enthesitis |
| `sjogren_like` | anti-SSA, anti-SSB, ANA+ | Dry eyes, dry mouth, fatigue |
| `mctd_like` | anti-U1 RNP, ANA+ | Raynaud, swollen hands, myositis |

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

### 1. Test Flare Prediction Engine

```bash
# Run flare tests
python -m pytest tests/ann/test_flare.py -v

# Test specific function
python -m pytest tests/ann/test_flare.py::TestFindFlarePrecursors -v

# Test with coverage
python -m pytest tests/ann/test_flare.py -v --cov=server.ann.flare
```

**Expected Output:**
- All tests pass
- Function signature matches spec
- Output schema includes precursors, scores, explanations

### 2. Test Diagnostic Landscape Engine

```bash
# Run diagnostic tests
python -m pytest tests/ann/test_diagnostic.py -v

# Test probability validation
python -m pytest tests/ann/test_diagnostic.py::TestEstimateDiagnosticLandscape::test_probabilities_sum_to_one -v

# Test disease name validation
python -m pytest tests/ann/test_diagnostic.py::TestEstimateDiagnosticLandscape::test_disease_names_use_like_suffix -v
```

**Expected Output:**
- All tests pass
- Probabilities sum to ~1.0
- All disease names use `_like` suffix

### 3. Interactive Flare Analysis

```bash
# Test flare precursor detection
python -c "
from datetime import datetime, timedelta, timezone
from server.ann.flare import find_flare_precursors

# Create test events
events = [
    {
        'event_type': 'lab',
        'ts': datetime.now(timezone.utc) - timedelta(days=30),
        'structured': {'test_name': 'CRP', 'value': 5.0, 'flag': 'normal'},
        'text': 'CRP 5.0 mg/L normal',
    },
    {
        'event_type': 'lab',
        'ts': datetime.now(timezone.utc) - timedelta(days=7),
        'structured': {'test_name': 'CRP', 'value': 25.0, 'flag': 'high'},
        'text': 'CRP 25.0 mg/L elevated',
    },
]

result = find_flare_precursors('TEST001', events=events)

print('Flare Likelihood:', result['flare_likelihood']['level'])
print('Precursors Found:', len(result['precursors']))
for p in result['precursors']:
    print(f'  - {p[\"type\"]}: {p[\"description\"]}')
"
```

**Expected Output:**
```
Flare Likelihood: medium or high
Precursors Found: 1+
  - inflammatory_marker_rise: Rising inflammatory markers detected
```

### 4. Interactive Diagnostic Landscape

```bash
# Test diagnostic landscape estimation
python -c "
from server.ann.diagnostic import estimate_diagnostic_landscape

# Create test events with RA-like pattern
events = [
    {
        'event_type': 'lab',
        'ts': '2024-01-15',
        'structured': {'test_name': 'RF', 'flag': 'high'},
        'text': 'RF positive, anti-CCP positive, elevated CRP',
    },
    {
        'event_type': 'symptom',
        'ts': '2024-01-15',
        'structured': {'primary_symptom': 'joint pain', 'body_regions': ['hands']},
        'text': 'Symmetric joint pain, morning stiffness, small joint involvement',
    },
]

result = estimate_diagnostic_landscape('TEST001', events=events)

print('Diagnostic Probabilities:')
for condition, prob in sorted(result['diagnostic_probabilities'].items(), key=lambda x: -x[1]):
    print(f'  {condition}: {prob:.1%}')

print('\\nDrivers:')
for driver in result['drivers'][:5]:
    print(f'  - {driver}')

# Verify sum
total = sum(result['diagnostic_probabilities'].values())
print(f'\\nProbability Sum: {total:.4f} (should be ~1.0)')
"
```

**Expected Output:**
```
Diagnostic Probabilities:
  ra_like: 41.0%
  sle_like: 22.0%
  ...

Drivers:
  - Lab: RF positive
  - Lab: elevated CRP
  ...

Probability Sum: 1.0000 (should be ~1.0)
```

### 5. Test Embedding Dimension

```bash
# Verify embedding dimension is 1536
python -c "
from server.ann.utils import VECTOR_DIMENSION, validate_embedding

print(f'Vector Dimension: {VECTOR_DIMENSION}')
assert VECTOR_DIMENSION == 1536, 'Dimension must be 1536!'

# Test validation
test_embedding = [0.1] * 1536
is_valid, error = validate_embedding(test_embedding)
print(f'Valid 1536-dim embedding: {is_valid}')

wrong_embedding = [0.1] * 512
is_valid, error = validate_embedding(wrong_embedding)
print(f'Invalid 512-dim embedding: {is_valid} ({error})')
"
```

**Expected Output:**
```
Vector Dimension: 1536
Valid 1536-dim embedding: True
Invalid 512-dim embedding: False (Embedding dimension must be 1536, got 512)
```

### 6. Test Index Builder

```bash
# Generate index creation SQL
python -m server.ann.index_builder
```

**Expected Output:**
```sql
-- ANN Index Creation SQL
-- HNSW Config: ef_search=40, ef_construction=200, M=16

CREATE INDEX IF NOT EXISTS patient_timeline_embedding_idx
ON ehr.patient_timeline
USING hnsw (embedding vector_cosine_ops)
WITH (
    m = 16,
    ef_construction = 200
);

SET hnsw.ef_search = 40;
```

### 7. Run All ANN Tests

```bash
# Run complete ANN test suite
python -m pytest tests/ann/ -v

# Run with verbose output
python -m pytest tests/ann/ -v --tb=short

# Run and stop on first failure
python -m pytest tests/ann/ -v -x
```

**Expected Output:**
- All tests pass
- No diagnostic statements in outputs
- Probabilities sum to ~1.0
- Disease names use `_like` suffix

---

## Regulatory Compliance

### Forbidden Language

The ANN engine MUST NOT output:
- "has [disease]"
- "diagnosis is"
- "confirmed"
- "definitely"
- "certainly"

### Allowed Language

The ANN engine SHOULD use:
- "pattern consistent with..."
- "...like" (e.g., ra_like)
- "probabilistic estimate"
- "observed signal includes..."

### Validation

```bash
# Test forbidden language detection
python -c "
from server.eoh.validators import check_forbidden_language

# Should detect forbidden language
text1 = 'The patient has rheumatoid arthritis'
violations = check_forbidden_language(text1)
print(f'Forbidden text violations: {len(violations)}')

# Should allow safe language
text2 = 'Pattern consistent with ra_like presentation'
violations = check_forbidden_language(text2)
print(f'Safe text violations: {len(violations)}')
"
```

**Expected Output:**
```
Forbidden text violations: 1+
Safe text violations: 0
```

---

## Troubleshooting

### Common Issues

1. **Embedding Dimension Mismatch**
   ```bash
   # Verify dimension
   python -c "from server.ann.utils import VECTOR_DIMENSION; print(VECTOR_DIMENSION)"
   ```

2. **Index Not Found**
   ```bash
   # Check index exists
   psql -c "SELECT indexname FROM pg_indexes WHERE indexname LIKE '%embedding%';"
   ```

3. **Import Errors**
   ```bash
   # Verify module structure
   python -c "from server.ann import flare, diagnostic, utils; print('Imports OK')"
   ```
