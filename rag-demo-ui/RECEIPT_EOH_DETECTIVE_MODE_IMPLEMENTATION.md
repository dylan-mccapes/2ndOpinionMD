# Receipt: EoH Detective Mode Implementation

**Date:** 2026-01-19  
**Session:** Afternoon Session 4  
**System:** 2ndOpinionMD-MVP / rag-demo-ui

---

## What Was Implemented

### Frontend (index.html)

**New Mode: EoH Detective**
- Added mode pill: "EoH Detective" → `/eoh_detective_stream + PDF`
- PDF upload control with password input (for encrypted PDFs)
- Explanatory text documenting the workflow
- Session-only processing with explicit receipt note

**UI Flow:**
1. User selects "EoH Detective" mode
2. User uploads patient timeline PDF (optional password if encrypted)
3. System uploads PDF to `/api/rag/upload_timeline_pdf`
4. Backend processes PDF:
   - Decrypts if password provided
   - Extracts events using LLM agents
   - Builds PatientTimelineVision graph
   - Runs two-phase enrichment (gap + synthesis)
   - Returns session key + metadata
5. Frontend displays timeline vision summary
6. Frontend streams EoH Detective report from `/api/rag/eoh_detective_stream`

**Event Handlers Added:**
- `timeline_vision_built`: Displays PatientTimelineVision metadata, gap analysis, synthesis report

**Panel Titles (Detective Mode):**
- Left: "Timeline Vision Graph & Investigation Trace"
- Right: "EoH Detective Clinical Report"

---

## What Needs to Be Implemented (Backend)

### 1. POST `/api/rag/upload_timeline_pdf`

**Input:**
- `file`: PDF file (multipart/form-data)
- `password`: Optional password string (if PDF is encrypted)

**Processing:**
```python
async def upload_timeline_pdf(file: UploadFile, password: Optional[str] = None):
    # 1. Save uploaded file to temp directory
    # 2. Call summarize_timeline_from_pdf(pdf_path, password=password)
    #    - This runs LLM event extraction
    #    - Builds PatientTimelineVision graph
    #    - Runs two-phase enrichment (gap + synthesis)
    # 3. Store PatientTimelineVision in session cache (Redis or in-memory dict)
    # 4. Return session metadata
```

**Output (JSON):**
```json
{
  "session_key": "timeline_abc123xyz",
  "patient_id": "session-only",
  "event_count": 4488,
  "edge_count": 350,
  "gap_analysis_summary": "...",
  "synthesis_summary": "..."
}
```

**Session Storage:**
- Store `PatientTimelineVision` instance keyed by `session_key`
- TTL: 1 hour (session-only, auto-cleanup)
- Cache: Redis (preferred) or in-memory dict with expiry

---

### 2. GET `/api/rag/eoh_detective_stream` (SSE)

**Input (Query Params):**
- `q`: Clinical question
- `timeline_session_key`: Session key from upload_timeline_pdf
- `limit`: Max results (default 10)
- `ctx_k`: Context window (default 48)
- `with_llm`: Enable LLM (default 1)
- `llm_mode`: LLM mode (default "chunk")

**Processing:**
```python
async def eoh_detective_stream(
    q: str,
    timeline_session_key: str,
    limit: int = 10,
    ctx_k: int = 48,
    with_llm: bool = True,
    llm_mode: str = "chunk"
):
    # 1. Retrieve PatientTimelineVision from session cache
    # 2. Emit "timeline_vision_built" event with metadata
    # 3. Run EoH Detective workflow:
    #    - Extract query terms
    #    - Route to EoH modules
    #    - Retrieve guideline context
    #    - Fuse with PatientTimelineVision context
    #    - Generate clinical report with LLM
    # 4. Stream events: start, router, matches, llm_chunk, citations, end
```

**SSE Events:**
- `timeline_vision_built`: Emitted after loading PatientTimelineVision
  ```json
  {
    "patient_id": "session-only",
    "event_count": 4488,
    "edge_count": 350,
    "gap_analysis_summary": "Identified 15 missing connascence edges...",
    "synthesis_summary": "Added 22 new edges, corrected 3 metadata entries..."
  }
  ```
- Standard events: `start`, `router`, `eoh_router_plan`, `matches`, `llm_chunk`, `citations`, `end`

---

## Integration with Existing Timeline Summarizer

**Reuse:**
- `summarize_timeline_from_pdf()` from `server/eoh/timeline_summarizer.py`
- Already implements:
  - LLM-based event extraction
  - PatientTimelineVision graph building
  - Two-phase enrichment (gap + synthesis)
  - Session-only save with `force=True`

**Wire-up:**
```python
from server.eoh.timeline_summarizer import summarize_timeline_from_pdf
from server.eoh.patient_timeline_vision import PatientTimelineVision

# In upload_timeline_pdf handler:
vision, summaries = await summarize_timeline_from_pdf(
    pdf_path=temp_pdf_path,
    password=password,
    question="Extract all clinical events",  # Generic for full extraction
    patient_id="session-only",
    temp_dir=temp_dir,
    connascence_rubric=PATIENT_TIMELINE_CONNASCENCE_RUBRIC,  # Optional
)

# Store in session cache:
session_key = f"timeline_{uuid.uuid4().hex}"
session_cache[session_key] = vision
session_cache.set_ttl(session_key, 3600)  # 1 hour

# Return metadata:
return {
    "session_key": session_key,
    "patient_id": vision.patient_id,
    "event_count": len(vision.events),
    "edge_count": vision.count_edges(),
    "gap_analysis_summary": "...",  # Extract from artifacts
    "synthesis_summary": "...",  # Extract from artifacts
}
```

---

## Docker Path Cleanup (Noted in Receipt)

**Current State:**
- `rag-demo-ui/index.html` is served from `2ndOpinionMD-MVP/rag-demo-ui/`
- `index.html` exists at both `2ndOpinionMD-MVP/` root and `rag-demo-ui/` subdirectory

**To Do:**
- Consolidate to single `index.html` location
- Update Docker nginx config to point to canonical path
- Document location in deployment docs

**Receipt Note Added to UI:**
> 📝 Receipt: Docker path cleanup pending (will consolidate rag-demo-ui → single index.html location).

---

## Testing Plan

**Manual Test (from 3Pi$73MiC87MLV4UL7):**
1. Rebuild Docker: `docker-compose build`
2. Restart: `docker-compose up`
3. Open UI: `https://2ndopinionmd.ai` (or localhost)
4. Select "EoH Detective" mode
5. Upload `/data/patient_timelines/NormanEricRoberts_decrypted.pdf`
6. Enter question: "What are the key events in Norman's MG journey and risk factors for exacerbation?"
7. Click "Run query"
8. Verify:
   - PDF uploads successfully
   - Timeline vision displays (events + edges)
   - EoH Detective stream runs
   - Clinical report generates with citations

**Expected Output:**
- Left panel: Timeline vision summary (4488 events, ~350 edges after enrichment)
- Right panel: Clinical report synthesizing MG journey, risk factors, flare risk assessment
- Raw events panel: Full SSE event log

---

## Artifacts

**Modified:**
- `/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/rag-demo-ui/index.html`

**Created:**
- `/Users/2ndopinionmd/dev/provenance-engines/PortalVision/2ndOpinionMD-MVP/rag-demo-ui/RECEIPT_EOH_DETECTIVE_MODE_IMPLEMENTATION.md` (this file)

**Updated:**
- `/Users/2ndopinionmd/dev/provenance-engines/PortalVision/game_plans/AEN_DUMP` (implementation notes)

---

## Design Adherence

✅ **Session-only processing** (no persistence beyond 1-hour TTL)  
✅ **Explicit provenance** (receipt in UI, all events logged)  
✅ **Two-phase enrichment** (gap + synthesis) wired in  
✅ **LLM-based event extraction** (no brittle heuristics)  
✅ **Opportunistic graph enrichment** (mousetrap model)  
✅ **Full transparency** (raw SSE events panel)  

---

## Status

**Frontend:** ✅ Complete  
**Backend:** ⚠️  Pending implementation  
**Testing:** ⏳ Awaiting backend + Docker rebuild  

---

**Next:** Implement backend endpoints, then test with Norman's PDF.

🫡

