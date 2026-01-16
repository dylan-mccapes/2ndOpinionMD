# Frontend Integration Documentation

## Overview

The 2OPMD UI (`index.html`) is now wired to backend RAG endpoints.

**Last Updated:** 2025-01-02

---

## Architecture

### Serving

**Development:**
- Static HTML served via: `python3 -m http.server 8080`
- Access: http://localhost:8080/
- API calls: http://localhost:8000/api/* (CORS required)

**Production (Docker/nginx):**
- nginx serves `index.html` at `/`
- nginx proxies `/api/*` to backend container
- Access: http://localhost/
- Single origin, no CORS issues

### API Configuration

```javascript
const API_BASE = window.location.hostname === 'localhost' && window.location.port === '8080'
    ? 'http://localhost:8000'  // Dev: different port
    : '';  // Production: same origin
```

---

## Mode → Endpoint Mapping

### ASK Mode
- **UI ID:** `submit-ask`
- **Endpoint:** `GET /api/rag/ask_stream` (SSE)
- **Query Params:**
  - `q`: Clinical question text
  - `limit`: 12 (evidence retrieval limit)
  - `with_llm`: 1 (enable LLM synthesis)
  - `llm_mode`: chunk (coalesced streaming)
- **Response:** Server-Sent Events stream
- **Streaming Contract (Honest):**
  1. `phase_start`: Execution began
  2. `retrieval_summary`: Sources considered/used, confidence
  3. `reasoning_progress`: Optional coarse progress updates
  4. `llm_chunk` / `llm_delta`: Answer content (streamed)
  5. `llm_done` / `final_answer`: Complete answer with confidence and limitations
  6. `completion` / `done`: Closure with tokens and duration
- **UI Behavior:**
  - Status updates: "Connecting" → "RUNNING" → "Evidence: X/Y sources" → "Complete"
  - Answer streams progressively (no blank screen)
  - Limitations displayed if present
  - Metrics shown on completion
- **Receipt Events:** `query_submitted`, all SSE events captured, `completion`

### CODING Mode
- **UI ID:** `submit-coding`
- **Endpoint:** `POST /api/coding`
- **Request:**
  ```json
  {
    "note": "clinical text to code",
    "context": "optional context",
    "limit": 60
  }
  ```
- **Response:** JSON with `probable_dx`, `differential_dx`, `procedures`, `labs`, `medications`
- **Receipt Events:** `coding_requested`, `response_received`, `completion`

### EoH Mode
- **UI ID:** `submit-eoh`
- **Endpoint:** `GET /api/rag/eoh_stream` (SSE)
- **Query Params:**
  - `q`: Combined query text (symptoms, age, sex, history, context)
  - `limit`: 10
  - `with_llm`: 1
  - `llm_mode`: chunk
- **Response:** Server-Sent Events stream
- **Receipt Events:** `eoh_requested`, `sse_event` (multiple), `stream_complete`

### EoHD Mode
- **UI ID:** `submit-eohd`
- **Status:** Disabled (timeline data ingestion not implemented)
- **Planned Endpoint:** `GET /api/rag/eoh_stream` with `use_timeline=1`

---

## Receipt Cache Integration

### Event Types Captured

1. **event**: Normal execution step
2. **error**: Failure or exception
3. **completion**: Successful completion

### Example ASK Receipt (Streaming)

```json
{
  "session_id": "ephemeral",
  "started_at": "2025-01-02T12:34:56.789Z",
  "mode": "ask",
  "events": [
    {
      "seq": 1,
      "timestamp": "2025-01-02T12:34:56.789Z",
      "type": "event",
      "source": "ask",
      "payload": {
        "action": "query_submitted",
        "query": "What are symptoms of lupus?"
      }
    },
    {
      "seq": 2,
      "timestamp": "2025-01-02T12:34:57.123Z",
      "type": "event",
      "source": "ask",
      "payload": {
        "sse_event": {
          "event": "phase_start",
          "mode": "ask"
        }
      }
    },
    {
      "seq": 3,
      "timestamp": "2025-01-02T12:34:57.456Z",
      "type": "event",
      "source": "ask",
      "payload": {
        "sse_event": {
          "event": "retrieval_summary",
          "sources_considered": 7,
          "sources_used": 3,
          "confidence": "medium"
        }
      }
    },
    {
      "seq": 4,
      "timestamp": "2025-01-02T12:34:58.123Z",
      "type": "event",
      "source": "ask",
      "payload": {
        "sse_event": {
          "event": "llm_chunk",
          "content": "Systemic lupus erythematosus (SLE) presents with..."
        }
      }
    },
    {
      "seq": 5,
      "timestamp": "2025-01-02T12:34:58.789Z",
      "type": "event",
      "source": "ask",
      "payload": {
        "sse_event": {
          "event": "llm_done",
          "text": "...[full answer]...",
          "confidence": 0.87,
          "limitations": ["Guideline-only", "No patient timeline"]
        }
      }
    },
    {
      "seq": 6,
      "timestamp": "2025-01-02T12:34:58.990Z",
      "type": "completion",
      "source": "ask",
      "payload": {
        "tokens_used": 412,
        "duration_ms": 2201
      }
    }
  ],
  "completed_at": "2025-01-02T12:34:58.990Z"
}
```

**Note:** ALL SSE events are captured in the receipt cache, but only contract-specified events (`phase_start`, `retrieval_summary`, `reasoning_progress`, `final_answer`, `completion`) affect the UI. Raw retrieval chunks, embeddings metadata, and internal router decisions remain available in the receipt but are not surfaced in the default display.

---

## Transparency Panel Behavior

### Default State
- ✓ No state mutated
- ✓ No data persisted
- ✓ No external calls made
- ✓ No session tracking
- ✓ No implicit behavior

### After API Call
- ⚠ External API call made (status changes, warning color)
- Panel updates with timestamp
- Honest reflection of system behavior

### After Mode Switch
- External calls status resets to ✓
- New session begins
- Previous call state does not carry over

---

## Error Handling

### Network Errors
- Caught in try/catch
- Displayed in red error box
- Recorded in receipt cache as `error` event
- Button re-enabled after error

### API Errors (4xx, 5xx)
- Status code captured in receipt
- Error response text captured
- Displayed to operator
- No retry logic (operator must explicitly retry)

### SSE Connection Errors
- EventSource `onerror` handler
- Connection closed
- Recorded as error event
- Button re-enabled

---

## UI State Management

### Button States
- **Default:** Enabled, "SUBMIT QUERY" etc.
- **Loading:** Disabled, opacity 0.6, cursor: wait
- **After completion:** Re-enabled
- **EoHD:** Permanently disabled (timeline required)

### Results Display
- Hidden by default (`display: none`)
- Visible class added on submit
- Persists until mode switch or page reload
- No auto-clear behavior

### Mode Switching
- Resets transparency panel
- Does NOT clear results (operator may want to compare)
- Resets external calls indicator
- Adds mode change receipt

---

## Development Notes

### Testing Without Backend

Comment out API calls and use demo data:

```javascript
// In handleAskSubmit():
// const response = await fetch(...);  // Comment out
const data = { matches: [{ title: "Demo", snippet: "Test" }] };  // Mock
```

### CORS Issues

If running dev server on :8080 and API on :8000, backend must include CORS headers:

```python
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### SSE Debugging

Browser DevTools → Network → Filter: EventStream
- Watch for connection open/close
- View individual SSE messages
- Check for connection errors

---

## Future Enhancements

### EoHD Timeline Upload
- File upload component
- CSV/JSON parser
- Timeline validation
- Enable `submit-eohd` button when valid timeline loaded

### Result Formatting
- Structured display instead of raw JSON
- Syntax highlighting
- Collapsible sections
- Evidence cards

### Streaming Display (EoH)
- Live update results during SSE stream
- Progressive rendering
- Chunk-by-chunk display

---

## Constraints (Non-Negotiable)

✓ No automatic retries  
✓ No optimistic updates  
✓ No result caching  
✓ No session persistence  
✓ No analytics or tracking  
✓ Failures surfaced honestly  
✓ External calls acknowledged in transparency panel  
✓ ALL SSE events captured in receipt cache (honest audit trail)  
✓ Only contract-specified events affect UI (no noise)  
✓ Streaming is for trust calibration, not completeness  

---

## Files Modified

- `index.html` (main UI + wiring)
- `docker-compose.yml` (nginx volume mount)
- `docker/nginx/conf.d/app.conf` (static + proxy config)

## Files Created

- `FRONTEND_INTEGRATION.md` (this file)

---

**Status:** Operational for ASK, CODING, EoH modes. EoHD blocked on timeline ingestion.

