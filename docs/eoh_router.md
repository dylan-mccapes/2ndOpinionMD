# EoH Router Documentation

**Version:** v100 (Cipher + Devin Method)  
**Location:** `server/eoh/`

## Overview

The EoH (Ethos of Health) Router integrates timeline context with the RAG system for clinical reasoning. It provides SSE (Server-Sent Events) streaming for real-time updates and enforces regulatory safety guardrails.

## Directory Structure

```
server/eoh/
├── __init__.py
├── router.py          # Main router with timeline integration
├── router_llm.py      # LLM-based routing logic
├── fusion.py          # Context fusion (timeline + RAG)
├── validators.py      # Safety validation
└── module_index.py    # EoH module definitions
```

## SSE Event Order (MANDATORY)

When `?use_timeline=1` is enabled, SSE events MUST be emitted in this exact order:

| Order | Event | Description |
|-------|-------|-------------|
| 1 | `timeline_loaded` | Timeline data loaded for patient |
| 2 | `timeline_signals` | Signals extracted from events |
| 3 | `timeline_flare_features` | Flare-related features |
| 4 | `timeline_probabilistic_differential` | Probabilistic differential |

## API Endpoints

### GET /api/timeline/{patient_id}

Returns chronologically ordered, normalized timeline.

**Request:**
```bash
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
      "structured": {
        "test_name": "CRP",
        "value": 15.5,
        "unit": "mg/L",
        "flag": "high"
      },
      "text": "CRP elevated at 15.5 mg/L"
    }
  ],
  "total_events": 50
}
```

### GET /api/eoh/flarereport/{patient_id}

Returns complete flare prediction report.

**Request:**
```bash
curl -X GET "http://localhost:8000/api/eoh/flarereport/TEST_RA"
```

**Response:**
```json
{
  "flare_forecast": "Pattern analysis suggests elevated flare risk...",
  "probabilistic_differential": {
    "ra_like": 0.41,
    "sle_like": 0.22,
    "psa_like": 0.15,
    "sjogren_like": 0.07,
    "mctd_like": 0.10,
    "other": 0.05
  },
  "precursor_signals": [
    {
      "type": "inflammatory_marker_rise",
      "description": "CRP trending upward"
    }
  ],
  "contradictions": [],
  "risk_drivers": [
    "Lab: elevated CRP",
    "Symptom: joint pain"
  ],
  "timeline_summary": "45 events analyzed over 90 days",
  "guidance_for_clinician": [
    "Consider monitoring inflammatory markers",
    "Review medication adherence"
  ]
}
```

### GET /api/rag/eoh_stream?use_timeline=1

Streams EoH response with timeline context.

**Request:**
```bash
curl -N "http://localhost:8000/api/rag/eoh_stream?patient_id=TEST_RA&use_timeline=1&question=What%20is%20the%20flare%20risk"
```

**Response (SSE):**
```
event: timeline_loaded
data: {"patient_id": "TEST_RA", "event_count": 45}

event: timeline_signals
data: {"signals": [...]}

event: timeline_flare_features
data: {"precursors": [...], "scores": [...]}

event: timeline_probabilistic_differential
data: {"probabilities": {...}, "drivers": [...]}

event: eoh_result
data: {"plan": {...}, "fused_context": {...}}
```

---

## Regulatory Guardrails (MANDATORY)

### Forbidden Language Patterns

The system MUST NOT output:

| Pattern | Example |
|---------|---------|
| `has [disease]` | "The patient has rheumatoid arthritis" |
| `diagnosis is` | "The diagnosis is lupus" |
| `should start` | "You should start taking methotrexate" |
| `should take` | "You should take this medication" |
| `will progress` | "The disease will progress" |
| `confirmed` | "This is a confirmed diagnosis" |
| `you have` | "You have an autoimmune condition" |

### Allowed Language Patterns

The system SHOULD use:

| Pattern | Example |
|---------|---------|
| `pattern consistent with...` | "Pattern consistent with inflammatory process" |
| `*_like` | "ra_like", "sle_like" |
| `probabilistic estimate` | "This is a probabilistic estimate" |
| `observed signal includes...` | "Observed signal includes elevated CRP" |
| `may suggest` | "This may suggest increased activity" |

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

### 1. Test Safety Validators

```bash
# Run all validator tests
python -m pytest tests/eoh/test_validators.py -v

# Test forbidden language detection
python -m pytest tests/eoh/test_validators.py::TestForbiddenLanguageDetection -v

# Test probability validation
python -m pytest tests/eoh/test_validators.py::TestProbabilityValidation -v

# Test SSE event ordering
python -m pytest tests/eoh/test_validators.py::TestSSEEventOrdering -v
```

**Expected Output:**
- All tests pass
- Forbidden language detected correctly
- Probabilities validated to sum to ~1.0
- SSE events validated in correct order

### 2. Test Forbidden Language Detection

```bash
# Interactive test
python -c "
from server.eoh.validators import check_forbidden_language

# Test forbidden patterns
test_cases = [
    'The patient has rheumatoid arthritis',
    'The diagnosis is lupus',
    'You should start taking methotrexate',
    'The disease will progress rapidly',
    'This is a confirmed diagnosis',
]

print('Testing forbidden language detection:')
for text in test_cases:
    violations = check_forbidden_language(text)
    status = 'DETECTED' if violations else 'MISSED'
    print(f'  [{status}] \"{text[:50]}...\"')
"
```

**Expected Output:**
```
Testing forbidden language detection:
  [DETECTED] "The patient has rheumatoid arthritis..."
  [DETECTED] "The diagnosis is lupus..."
  [DETECTED] "You should start taking methotrexate..."
  [DETECTED] "The disease will progress rapidly..."
  [DETECTED] "This is a confirmed diagnosis..."
```

### 3. Test Allowed Language

```bash
# Interactive test
python -c "
from server.eoh.validators import check_forbidden_language

# Test allowed patterns
test_cases = [
    'Pattern consistent with inflammatory process',
    'The pattern shows ra_like characteristics',
    'This is a probabilistic estimate based on pattern analysis',
    'Observed signal includes elevated inflammatory markers',
]

print('Testing allowed language (should have 0 violations):')
for text in test_cases:
    violations = check_forbidden_language(text)
    status = 'PASS' if not violations else f'FAIL ({len(violations)} violations)'
    print(f'  [{status}] \"{text[:50]}...\"')
"
```

**Expected Output:**
```
Testing allowed language (should have 0 violations):
  [PASS] "Pattern consistent with inflammatory process..."
  [PASS] "The pattern shows ra_like characteristics..."
  [PASS] "This is a probabilistic estimate based on patter..."
  [PASS] "Observed signal includes elevated inflammatory m..."
```

### 4. Test SSE Event Order Validation

```bash
# Interactive test
python -c "
from server.eoh.validators import validate_sse_event_order, SSE_EVENT_ORDER

print('Mandatory SSE Event Order:')
for i, event in enumerate(SSE_EVENT_ORDER, 1):
    print(f'  {i}. {event}')

# Test correct order
correct_order = [
    'timeline_loaded',
    'timeline_signals',
    'timeline_flare_features',
    'timeline_probabilistic_differential',
]
is_valid, msg = validate_sse_event_order(correct_order)
print(f'\\nCorrect order: {is_valid} - {msg}')

# Test incorrect order
wrong_order = [
    'timeline_signals',  # Should be second
    'timeline_loaded',   # Should be first
]
is_valid, msg = validate_sse_event_order(wrong_order)
print(f'Wrong order: {is_valid} - {msg}')
"
```

**Expected Output:**
```
Mandatory SSE Event Order:
  1. timeline_loaded
  2. timeline_signals
  3. timeline_flare_features
  4. timeline_probabilistic_differential

Correct order: True - SSE events in correct order
Wrong order: False - SSE events out of order...
```

### 5. Test Response Safety Validation

```bash
# Interactive test
python -c "
from server.eoh.validators import validate_response_safety

# Test safe response
safe_response = {
    'diagnostic_probabilities': {
        'ra_like': 0.4,
        'sle_like': 0.2,
        'psa_like': 0.15,
        'sjogren_like': 0.1,
        'mctd_like': 0.1,
        'other': 0.05,
    },
    'drivers': ['Lab: elevated CRP', 'Symptom: joint pain'],
    'narrative': 'Pattern consistent with inflammatory process',
}

result = validate_response_safety(safe_response)
print(f'Safe response: is_safe={result[\"is_safe\"]}')
print(f'  Violations: {len(result[\"violations\"])}')
print(f'  Warnings: {len(result[\"warnings\"])}')

# Test unsafe response
unsafe_response = {
    'narrative': 'The patient has rheumatoid arthritis',
}

result = validate_response_safety(unsafe_response)
print(f'\\nUnsafe response: is_safe={result[\"is_safe\"]}')
print(f'  Violations: {len(result[\"violations\"])}')
for v in result['violations']:
    print(f'    - {v.get(\"matched_text\", v.get(\"type\", \"unknown\"))}')
"
```

**Expected Output:**
```
Safe response: is_safe=True
  Violations: 0
  Warnings: 0

Unsafe response: is_safe=False
  Violations: 1+
    - has rheumatoid arthritis
```

### 6. Test Response Sanitization

```bash
# Interactive test
python -c "
from server.eoh.validators import sanitize_response

# Test sanitization
unsafe_response = {
    'text': 'The patient has rheumatoid arthritis and the disease will progress.',
}

sanitized = sanitize_response(unsafe_response)
print('Original:', unsafe_response['text'])
print('Sanitized:', sanitized['text'])
"
```

**Expected Output:**
```
Original: The patient has rheumatoid arthritis and the disease will progress.
Sanitized: The patient shows patterns consistent with rheumatoid arthritis-like presentation and the disease may progress.
```

### 7. Test Flare Report Schema Validation

```bash
# Interactive test
python -c "
from server.eoh.validators import validate_flare_report_schema

# Test valid report
valid_report = {
    'flare_forecast': 'Pattern suggests elevated risk',
    'probabilistic_differential': {'ra_like': 0.5},
    'precursor_signals': ['elevated CRP'],
    'contradictions': [],
    'timeline_summary': '30 events analyzed',
}

is_valid, missing = validate_flare_report_schema(valid_report)
print(f'Valid report: is_valid={is_valid}, missing={missing}')

# Test invalid report
invalid_report = {
    'flare_forecast': 'Pattern suggests elevated risk',
    # Missing other required fields
}

is_valid, missing = validate_flare_report_schema(invalid_report)
print(f'Invalid report: is_valid={is_valid}, missing={missing}')
"
```

**Expected Output:**
```
Valid report: is_valid=True, missing=[]
Invalid report: is_valid=False, missing=['differential', 'precursors', 'contradictions', 'timeline_summary']
```

### 8. Test Context Fusion

```bash
# Interactive test
python -c "
from datetime import datetime, timezone
from server.eoh.fusion import fuse_timeline_context, create_timeline_context_doc

# Create test events
events = [
    {
        'event_type': 'lab',
        'ts': datetime.now(timezone.utc),
        'structured': {'test_name': 'CRP', 'value': 15.5, 'flag': 'high'},
        'text': 'CRP elevated at 15.5 mg/L',
    },
    {
        'event_type': 'symptom',
        'ts': datetime.now(timezone.utc),
        'structured': {'primary_symptom': 'joint pain', 'severity': 'moderate'},
        'text': 'Joint pain in hands',
    },
]

# Test context document creation
doc = create_timeline_context_doc(events)
print('Timeline Context Document:')
print(doc[:500])
print('...')

# Test fusion
fused = fuse_timeline_context(events)
print(f'\\nFused Context Summary:')
print(f'  Event count: {fused[\"event_count\"]}')
print(f'  Has flare analysis: {fused[\"has_flare_analysis\"]}')
print(f'  Has diagnostic analysis: {fused[\"has_diagnostic_analysis\"]}')
"
```

### 9. Run All EoH Tests

```bash
# Run complete EoH test suite
python -m pytest tests/eoh/ -v

# Run with verbose output
python -m pytest tests/eoh/ -v --tb=short

# Run and stop on first failure
python -m pytest tests/eoh/ -v -x

# Run with coverage
python -m pytest tests/eoh/ -v --cov=server.eoh
```

**Expected Output:**
- All tests pass
- No forbidden language in outputs
- SSE events in correct order
- Response schemas validated

### 10. Test Full Integration

```bash
# Test full pipeline with seed data
python -c "
from datetime import datetime, timedelta, timezone
from server.timeline.seed_data import generate_ra_like_patient
from server.ann.flare import find_flare_precursors
from server.ann.diagnostic import estimate_diagnostic_landscape
from server.eoh.fusion import fuse_timeline_context
from server.eoh.validators import validate_response_safety

# Generate test patient
events = generate_ra_like_patient('TEST_INTEGRATION')
print(f'Generated {len(events)} events')

# Convert to dict format for analysis
event_dicts = [
    {
        'event_type': e.event_type.value if hasattr(e.event_type, 'value') else e.event_type,
        'ts': e.timestamp,
        'structured': e.structured.model_dump() if hasattr(e.structured, 'model_dump') else {},
        'text': e.text,
    }
    for e in events
]

# Run flare analysis
flare_result = find_flare_precursors('TEST_INTEGRATION', events=event_dicts)
print(f'Flare likelihood: {flare_result[\"flare_likelihood\"][\"level\"]}')

# Run diagnostic analysis
diagnostic_result = estimate_diagnostic_landscape('TEST_INTEGRATION', events=event_dicts)
print(f'Top pattern: {max(diagnostic_result[\"diagnostic_probabilities\"].items(), key=lambda x: x[1])}')

# Fuse context
fused = fuse_timeline_context(
    events=event_dicts,
    flare_result=flare_result,
    diagnostic_result=diagnostic_result,
)
print(f'Fused context created: {fused[\"event_count\"]} events')

# Validate safety
result = validate_response_safety({
    'diagnostic_probabilities': diagnostic_result['diagnostic_probabilities'],
    'drivers': diagnostic_result['drivers'],
})
print(f'Safety validation: is_safe={result[\"is_safe\"]}')
"
```

---

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```bash
   # Verify module structure
   python -c "from server.eoh import router, fusion, validators; print('Imports OK')"
   ```

2. **Circular Import**
   ```bash
   # Check for circular imports
   python -c "
   import sys
   sys.setrecursionlimit(100)
   try:
       from server.eoh.router import route_with_timeline
       print('No circular imports')
   except RecursionError:
       print('Circular import detected!')
   "
   ```

3. **Missing Dependencies**
   ```bash
   # Check required packages
   python -c "
   import openai
   import pydantic
   print('Dependencies OK')
   "
   ```

### Logs

Error logs are written to `logs/timeline/YYYYMMDD.log`:

```bash
# View today's logs
cat logs/timeline/$(date +%Y%m%d).log

# Search for safety violations
grep -i "forbidden\|violation\|unsafe" logs/timeline/$(date +%Y%m%d).log
```
