# Game Plan: Timeline Upload & EoHD for System Users

**Date:** 2026-02-20  
**Status:** Proposed  
**Owner:** Product + Devin  

---

## What This Is

EoHD (Ethos-of-Health Detective) is moving behind a paywall for **system users** (paid subscribers). Free workflow users retain ASK, CODING, and EoH modes but cannot run EoHD.

System users need a simple path to upload their patient timeline PDF (decrypted or encrypted with password), ingest it into the database, and run EoHD investigations. This flow occurs **right after onboarding** — the first time a paid user logs in, they are guided to upload their timeline before EoHD is unlocked.

---

## Context Shift

| Before | After |
|--------|-------|
| Session-only EoHD (free) | EoHD behind paywall |
| Timeline in memory, no persistence | Timeline in DB, owned by user |
| No upload UX | Browser upload → DB ingestion |

---

## User Flow

```
Onboarding (register → verify → login)
    ↓
First login as system user
    ↓
Timeline Upload Step (new)
    • "Upload your patient timeline PDF"
    • File picker (PDF only)
    • Optional: password field if encrypted
    • Progress: "Extracting...", "Ingesting...", "Building timeline..."
    ↓
Ingestion complete
    • "Timeline ready ✓"
    • EoHD button enabled
    ↓
User can run EoHD investigations
```

---

## Architecture

### Data Flow

```
Browser (PDF file)
    │
    ▼  POST /api/timeline/import-pdf (multipart + optional password)
    │
Backend (auth required)
    │
    ├─► Decrypt PDF if encrypted (password in form, deleted after use)
    ├─► Extract text (pypdf)
    ├─► Parse → structured events (timeline parser / LLM extraction)
    ├─► INSERT into ehr.patient_timeline (patient_id = user's timeline_id)
    ├─► Embed events (text-embedding-3-small → pgvector)
    ├─► Build PatientTimelineVision (optional enrichment)
    │
    ▼
Response: { timeline_id, event_count, status: "ready" }
```

### User → Timeline Mapping

Existing schema supports this:

- **users** (auth) → **operators** (user_id → operator_id)
- **patient_timelines** (timeline_id, patient_operator_id) — one per user
- **ehr.patient_timeline** (patient_id, ts, event_type, source, structured, text, embedding)

**Mapping:** `patient_id` in ehr.patient_timeline = `str(timeline_id)` from patient_timelines for that user's operator.

**Flow:**
1. User authenticated (JWT)
2. Get or create operator for user_id (`get_or_create_operator`)
3. Get or create patient_timelines row for operator (`timeline_initialize` or equivalent)
4. Use `timeline_id` as `patient_id` when inserting events

---

## Backend Components

### 1. New Endpoint: `POST /api/timeline/import-pdf`

**Auth:** Required (Bearer JWT)

**Request:** `multipart/form-data`
- `file`: PDF file (required)
- `password`: string (optional, for encrypted PDFs)

**Response:**
```json
{
  "timeline_id": "uuid",
  "patient_id": "uuid",
  "event_count": 42,
  "status": "ready",
  "message": "Timeline ingested successfully"
}
```

**Errors:**
- 401: Unauthorized
- 403: Forbidden (not a system user / subscription check)
- 400: Invalid PDF, wrong password, parse failure
- 413: File too large (recommend max 10MB)

**Implementation steps:**
1. Validate auth, get user_id
2. Get or create operator → timeline_id for user
3. Save uploaded file to temp path (or process in-memory)
4. Decrypt if encrypted (`pypdf`, password from form)
5. Extract text via pypdf
6. Run timeline ingest:
   - Option A: Reuse `server/timeline/ingest.py` flow (DocumentParser, TimelineEngine) — may need PDF text adapter
   - Option B: Extend `summarize_timeline_from_pdf` path to write to ehr.patient_timeline instead of session-only
   - Option C: New `ingest_timeline_from_pdf_text()` that calls existing timeline parser + engine
7. Call `embed_patient_timeline(patient_id)` for ANN search
8. Optionally build PatientTimelineVision for enrichment (can be async/secondary)
9. Delete temp file, clear password from memory
10. Return success

### 2. Subscription / Paywall Check

Before allowing upload or EoHD:
- Check `user.subscription_tier` or equivalent
- System users: `subscription_tier in ("pro", "clinical", "enterprise")` or similar
- Free users: Redirect or show upgrade prompt

*Define exact tier names in product spec.*

### 3. Timeline Status Endpoint

**GET /api/timeline/status**

Returns whether the current user has a timeline and event count. Used by frontend to show "Upload timeline" vs "Timeline ready ✓".

```json
{
  "has_timeline": true,
  "timeline_id": "uuid",
  "event_count": 42,
  "last_updated": "2026-02-20T12:00:00Z"
}
```

---

## Frontend Components

### 1. Timeline Upload Page (or Step)

**Route:** `/timeline/upload` or embedded in onboarding wizard

**UI:**
- Headline: "Upload your patient timeline"
- File input (PDF only, max 10MB)
- Optional password field: "PDF is encrypted" (checkbox to reveal)
- Submit button: "UPLOAD & INGEST"
- Progress states: Idle → Uploading → Extracting → Ingesting → Done
- Error display: wrong password, invalid file, server error

**Placement:** Shown after first login for system users who don't yet have a timeline. Can also be reachable from Settings or a "Timeline" nav item.

### 2. EoHD Gate

**Current:** EoHD button disabled with tooltip "Blocked — timeline data ingestion not implemented"

**New:** 
- If user has no timeline and is system user: "Upload timeline to unlock EoHD"
- If user has timeline: EoHD enabled, `timeline_patient_id` = user's timeline_id when calling `/eoh_detective_stream`

### 3. Timeline Status Indicator

Small indicator in header or mode selector:
- "Timeline ready ✓" when `has_timeline`
- "Upload timeline" link when not

---

## Security & Privacy

1. **Password handling:** Received in multipart form, used only for decryption, `del` immediately after. Never logged or persisted.
2. **File storage:** Temp file deleted after processing. No long-term PDF storage unless explicitly added later.
3. **Auth:** All endpoints require valid JWT. Timeline is scoped to user via operator/timeline_id.
4. **PHI:** Timeline data in ehr.patient_timeline is user-owned. Access control via patient_id = user's timeline_id.

---

## Implementation Phases

### Phase 1: Backend — Upload & Ingest (1–2 weeks)

- [ ] `POST /api/timeline/import-pdf` endpoint
- [ ] Auth + operator/timeline resolution
- [ ] PDF decrypt + extract (reuse import_timeline_pdf logic)
- [ ] Pipeline: text → structured events → ehr.patient_timeline
- [ ] Embedding step
- [ ] `GET /api/timeline/status`

### Phase 2: Frontend — Upload UI (1 week)

- [ ] Timeline upload page/step
- [ ] File picker, password field, progress states
- [ ] Error handling
- [ ] Post-upload redirect or status update

### Phase 3: EoHD Integration (3–5 days)

- [ ] Subscription check middleware or helper
- [ ] EoHD button: conditional enable based on timeline + subscription
- [ ] Pass `timeline_patient_id` from user's timeline when calling eoh_detective_stream

### Phase 4: Onboarding Flow (2–3 days)

- [ ] Post-login check: system user without timeline → redirect to /timeline/upload
- [ ] Skip for free users
- [ ] Optional: "Upload later" so user can explore other modes first

---

## Existing Code to Reuse

| Component | Location | Use |
|-----------|----------|-----|
| PDF decrypt + extract | `server/scripts/import_timeline_pdf.py` | decrypt_pdf_if_needed, extract_timeline_text |
| Timeline summarizer (LLM extraction) | `server/eoh/timeline_summarizer.py` | _extract_events_from_page_text, add_events_from_pdf_page |
| Timeline engine | `server/timeline/engine.py` | Insert events, build context |
| Timeline ingest | `server/timeline/ingest.py` | DocumentParser, patterns for labs/meds/symptoms |
| Embed | `server/timeline/embed_patient_timeline.py` | embed_patient_timeline(patient_id) |
| Operator/session | `server/api/session_routes.py` | get_or_create_operator, get_timeline_id_for_operator, timeline_initialize |

---

## Open Questions

1. **PDF storage:** Do we ever persist the original PDF, or only the extracted timeline? (Recommend: extract only, no PDF storage.)
2. **Replace vs append:** If user uploads a second PDF, do we replace the timeline or append? (Recommend: replace for MVP — clear existing events, re-ingest.)
3. **PatientTimelineVision:** Required for EoHD or optional enrichment? (Current EoHD loads from ehr.patient_timeline; PatientTimelineVision is used for graph enrichment. Can defer full enrichment.)
4. **Subscription tier field:** Confirm field name and values in User model.

---

## Success Criteria

- System user can upload a PDF (encrypted or not) from the browser
- Timeline is ingested into ehr.patient_timeline under their account
- EoHD is unlocked and uses their timeline
- Free users do not see upload prompt; EoHD remains disabled
- Password never persists; temp files cleaned up

---

**End of Game Plan**
