# EoH Demo Endpoints

This document describes the EoH (Ethos-of-Health) demo endpoints for the multi-patient RA flare-risk playground.

## Overview

The EoH demo provides in-memory synthetic patient data for demonstrating the EoH router and flare-risk analysis capabilities. Four synthetic RA (Rheumatoid Arthritis) patients are available, each with different disease trajectories and risk profiles.

## Demo Patients

| ID | Label | Description |
|----|-------|-------------|
| P1 | Recurrent flares on MTX + ADA | 38F, seropositive RA, 2 moderate flares in 12 months, currently controlled |
| P2 | Deep remission | 42F, seropositive RA, no flares in 18-24 months, DAS28 <2.6 |
| P3 | Smoldering / high risk | 35F, seropositive RA, multiple flares, incomplete control on csDMARD |
| P4 | Subjective heavy / psychosomatic noise | 30F, RA with moderate objective activity but frequent subjective symptoms |

## Endpoints

### GET /api/eoh_demo/patients

Returns a list of all demo patients with their ID, label, and summary.

**Response:**
```json
[
  {
    "id": "P1",
    "label": "Recurrent flares on MTX + ADA",
    "summary": "38F with seropositive RA on MTX + adalimumab..."
  },
  ...
]
```

**Example:**
```bash
curl -s https://2ndopinionmd.ai/api/eoh_demo/patients | jq
```

### GET /api/eoh_demo/patient_state/{patient_id}

Returns a patient_state JSON suitable for EoH questions. This includes demographics, current medications, recent flare history, DAS28 scores, labs, and journal entries.

**Parameters:**
- `patient_id` (path): Patient ID (P1, P2, P3, or P4)

**Response:**
```json
{
  "patient_id": "P1",
  "age": 38,
  "sex": "F",
  "diagnosis": "seropositive RA",
  "terrain": "chronic autoimmune inflammatory arthritis",
  "serostatus": "seropositive",
  "current_meds": [...],
  "recent_flare_history": [...],
  "recent_das28": {...},
  "das28_trend": [...],
  "recent_labs": [...],
  "recent_journal": [...],
  "journal_highlights": [...],
  "summary": "..."
}
```

**Example:**
```bash
curl -s https://2ndopinionmd.ai/api/eoh_demo/patient_state/P1 | jq
```

### GET /api/eoh_demo/timeline/{patient_id}

Returns the full chronological list of events for a patient, including visits, flares, labs, medication changes, and journal entries.

**Parameters:**
- `patient_id` (path): Patient ID (P1, P2, P3, or P4)
- `max_events` (query, optional): Maximum number of events to return (default: 200, max: 500)

**Response:**
```json
[
  {
    "ts": "2024-01-15T09:00:00",
    "kind": "visit",
    "summary": "Routine rheumatology visit",
    "details": {...}
  },
  ...
]
```

**Example:**
```bash
curl -s "https://2ndopinionmd.ai/api/eoh_demo/timeline/P1?max_events=50" | jq
```

### POST /api/eoh_demo/hypothetical

Creates a hypothetical patient_state by applying changes (e.g., a new flare) to a base patient. Useful for "what if" scenarios.

**Request Body:**
```json
{
  "base_patient_id": "P1",
  "changes": [
    {
      "ts": "2025-09-01T08:00:00Z",
      "kind": "flare",
      "severity": "moderate",
      "summary": "New flare knees/wrists"
    }
  ]
}
```

**Response:**
Returns a modified patient_state with the hypothetical changes applied, including adjusted labs and DAS28 scores.

**Example:**
```bash
curl -s -X POST https://2ndopinionmd.ai/api/eoh_demo/hypothetical \
  -H "Content-Type: application/json" \
  -d '{
    "base_patient_id": "P1",
    "changes": [{
      "ts": "2025-09-01T08:00:00Z",
      "kind": "flare",
      "severity": "moderate",
      "summary": "New flare knees/wrists"
    }]
  }' | jq
```

## Using the Demo Page

The RAG demo page at `/srv/collector/edge_17` includes an EoH mode with patient selection and helper buttons.

### Steps to Use:

1. Click the "EoH Mode" pill to switch to EoH mode
2. Select a patient from the dropdown (P1-P4)
3. Click "Load Patient" to fetch patient data and timeline
4. Use the helper buttons to auto-populate EoH questions:
   - **Flare risk (6-12 months)**: Asks for qualitative flare risk assessment
   - **Trajectory / drift summary**: Asks for baseline terrain and drift analysis
   - **What if: new flare 2 weeks ago**: Creates a hypothetical scenario with a recent flare
5. Click "Run query" to stream the EoH analysis

### Example EoH Stream Request

```bash
STATE=$(curl -s https://2ndopinionmd.ai/api/eoh_demo/patient_state/P1)

curl -N "https://2ndopinionmd.ai/api/rag/eoh_stream" \
  --get \
  --data-urlencode "q=Using the following patient_state JSON, conceptually estimate qualitative 6- and 12-month flare risk and explain the main EoH drivers:

${STATE}" \
  --data-urlencode "limit=8" \
  --data-urlencode "ctx_k=24" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=0"
```

## Data Model

### DemoPatient

```python
class DemoPatient(TypedDict):
    id: str                          # Patient ID (P1, P2, P3, P4)
    label: str                       # Short label for UI
    summary: str                     # Brief clinical summary
    diagnosis: str                   # Primary diagnosis
    age: int                         # Age in years
    sex: str                         # Sex (M/F)
    serostatus: str                  # Serostatus (seropositive/seronegative)
    meds: List[Dict[str, Any]]       # Current medications
    recent_labs: List[Dict[str, Any]] # Recent lab results
    das28_history: List[Dict[str, Any]] # DAS28 score history
    recent_flares: List[Dict[str, Any]] # Recent flare events
    journal_highlights: List[str]    # Notable journal entries
```

### DemoEvent

```python
class DemoEvent(TypedDict):
    ts: str          # ISO 8601 timestamp
    kind: str        # Event type: "visit", "flare", "lab", "med_change", "journal"
    summary: str     # Brief summary of the event
    details: Dict[str, Any]  # Event-specific details
```

## Notes

- All data is in-memory and not persisted to a database
- Data is reset when the server restarts
- The demo is designed for demonstration purposes only and does not represent real patient data
- The hypothetical endpoint modifies labs and DAS28 scores based on flare severity to simulate realistic disease progression
