# GAME_PLAN: Mock Server for Frontend UX Development

**Goal**: A standalone mock server that covers 100% of frontend API calls, requires zero external services (no Postgres, Redis, Ollama, OpenAI), starts in <2s, and serves the full OpenAPI spec for contract-driven frontend work.

**Tool**: FastAPI (reuses existing Python environment, produces OpenAPI automatically)  
**Location**: `server/mock/`  
**Data source**: Norman dev fixtures + static JSON responses  
**Auth**: Always authenticated — no token validation

---

## Frontend API surface (41 endpoints)

Derived from exhaustive search of `frontend/src/**/*.{ts,tsx}`.

### Auth — 9 endpoints
| Method | Path | Mock behavior |
|--------|------|---------------|
| POST | `/api/auth/register` | Returns mock user + JWT |
| POST | `/api/auth/token` | Returns `{"access_token": "mock-jwt", "token_type": "bearer"}` |
| GET | `/api/auth/me` | Returns Norman dev user |
| GET | `/api/auth/verify-email` | Returns `{"verified": true}` |
| POST | `/api/auth/forgot-password` | Returns `{"sent": true}` |
| POST | `/api/auth/reset-password/{token}` | Returns `{"reset": true}` |
| POST | `/api/auth/resend-verification` | Returns `{"sent": true}` |
| POST | `/api/auth/accept-doctor-invite` | Returns `{"accepted": true}` |
| POST | `/api/auth/accept-patient-invite` | Returns `{"accepted": true}` |

### Timeline — 6 endpoints
| Method | Path | Mock behavior |
|--------|------|---------------|
| GET | `/api/timeline/status` | Returns Norman fixture status (has_timeline=true, event_count from PTV) |
| GET | `/api/timeline/{patient_id}` | Returns Norman fixture events (paginated) |
| POST | `/api/timeline/import-pdf` | Returns `{"status": "complete", "event_count": 247}` |
| GET | `/api/timeline/{patient_id}/analytics/summary` | Returns static analytics JSON |
| GET | `/api/timeline/{patient_id}/analytics/precedence` | Returns static precedence edges |
| POST | `/api/timeline/{patient_id}/analytics/export` | Returns static export blob |

### EoH — 2 endpoints
| Method | Path | Mock behavior |
|--------|------|---------------|
| POST | `/api/eoh/router_plan` | Returns static router plan (Type A, 3-step module plan) |
| GET | `/api/eoh/flarereport/{patient_id}` | Returns static flare report with probabilistic differential |

### RAG / Streaming — 3 endpoints
| Method | Path | Mock behavior |
|--------|------|---------------|
| POST | `/api/rag/ask_stream` | SSE stream: connecting → evidence → reasoning → llm_chunks → done |
| POST | `/api/rag/eoh_stream` | SSE stream: same phases, EoH-flavored answer |
| POST | `/api/coding` | Returns static coding result (ICD-10, SNOMED codes) |

### Journal — 5 endpoints
| Method | Path | Mock behavior |
|--------|------|---------------|
| GET | `/api/journal` | Returns array of 3 mock journal entries |
| POST | `/api/journal` | Accepts body, returns new entry with mock AI analysis |
| DELETE | `/api/journal/{entry_id}` | Returns 204 |
| GET | `/api/journal/timeline/{report_id}` | Returns mock timeline bundle |
| POST | `/api/journal/query-ai` | Returns mock AI response |

### Patient portal — 3 endpoints
| Method | Path | Mock behavior |
|--------|------|---------------|
| GET | `/api/patient/my-doctor` | Returns `{"doctor": {"id": "dr-mock", "email": "dr@mock.dev", "full_name": "Dr. House"}}` |
| GET | `/api/patient/pending-invites` | Returns `[]` |
| POST | `/api/patient/invite-doctor` | Returns `{"id": "inv-1", "to_email": "<body.email>", "status": "pending"}` |

### Doctor portal — 5 endpoints
| Method | Path | Mock behavior |
|--------|------|---------------|
| GET | `/api/doctor/patients` | Returns array with Norman as patient |
| GET | `/api/doctor/pending-invites` | Returns `[]` |
| POST | `/api/doctor/invite-patient` | Returns `{"id": "inv-2", "to_email": "<body.email>", "status": "pending"}` |
| GET | `/api/doctor/patients/{patient_id}/journal` | Returns same as GET `/api/journal` |
| GET | `/api/doctor/patients/{patient_id}/timeline-status` | Returns same as timeline/status |

### Chat — 4 endpoints
| Method | Path | Mock behavior |
|--------|------|---------------|
| GET | `/api/chat/history/{patient_id}` | Returns array of 5 mock chat messages |
| GET | `/api/chat/stats/{patient_id}` | Returns `{"total_messages": 5, "anchors": 1}` |
| POST | `/api/chat/send` | Returns mock assistant response |
| POST | `/api/chat/anchor` | Returns `{"anchored": true}` |

### Portal utilities — 3 endpoints
| Method | Path | Mock behavior |
|--------|------|---------------|
| POST | `/api/portal/transcribe` | Returns `{"text": "Mock transcription of uploaded audio."}` |
| POST | `/api/portal/encounter_note` | Returns static encounter note |
| POST | `/api/portal/save-encounter` | Returns `{"saved": true, "id": "enc-mock-1"}` |

---

## Architecture

```
server/mock/
├── app.py                  # FastAPI app, mounts all routers, CORS, OpenAPI config
├── run.py                  # Entry point: uvicorn server.mock.app:app --port 8100
├── fixtures/
│   ├── norman.py           # Reuses server/dev_fixtures.py for timeline data
│   ├── journal.py          # 3 mock journal entries with AI analysis
│   ├── chat.py             # 5 mock chat messages
│   ├── flare_report.py     # Static flare report matching EohdPage schema
│   ├── router_plan.py      # Static router plan matching EohdPage schema
│   ├── coding.py           # Static coding result (ICD-10 + SNOMED)
│   ├── analytics.py        # Static analytics summary, precedence, export
│   ├── streaming.py        # SSE event generators for ask_stream / eoh_stream
│   └── users.py            # Mock user, doctor, patient objects
├── routers/
│   ├── auth.py             # /api/auth/*
│   ├── timeline.py         # /api/timeline/*
│   ├── eoh.py              # /api/eoh/*
│   ├── rag.py              # /api/rag/* + /api/coding
│   ├── journal.py          # /api/journal/*
│   ├── patient.py          # /api/patient/*
│   ├── doctor.py           # /api/doctor/*
│   ├── chat.py             # /api/chat/*
│   └── portal.py           # /api/portal/*
└── README.md               # How to start, how to switch frontend to mock
```

---

## Block 0 — Scaffold + OpenAPI (creates the foundation)

1. Create `server/mock/app.py`:
   - FastAPI with `title="2ndOpinionMD Mock Server"`, `version="0.1.0-mock"`
   - OpenAPI at `/docs`, `/openapi.json`, and `/api/openapi.json`
   - CORS: allow `http://localhost:3000` (Vite dev server)
   - Mount all 9 routers
2. Create `server/mock/run.py`: starts uvicorn on port **8100** (won't conflict with real backend on 8000)
3. Create `server/mock/fixtures/users.py`: dev user, mock doctor, mock patient
4. Verify: `GET /docs` renders Swagger UI with all 41 routes

---

## Block 1 — Auth routes

- All auth endpoints return success instantly
- `POST /api/auth/token` returns a static JWT that never expires
- `GET /api/auth/me` returns the dev user (email, user_type, full_name)
- No validation, no hashing, no DB — pure static returns
- **Frontend test**: login flow, registration form, password reset forms all render and "succeed"

---

## Block 2 — Timeline + Analytics

- `GET /api/timeline/status` delegates to `server/dev_fixtures.py` (already built)
- `GET /api/timeline/{patient_id}` delegates to `dev_fixtures.get_timeline_events()`
- Analytics endpoints return pre-computed JSON from Norman's PTV data:
  - Summary: event type distribution, recent event counts
  - Precedence: top 20 strongest connascence edges
  - Export: JSON blob of the summary
- `POST /api/timeline/import-pdf` returns immediate success (no actual processing)
- **Frontend test**: TimelinePage renders full vertical timeline, charts load

---

## Block 3 — EoH + RAG Streaming

This is the most interesting block — mock SSE streaming.

### SSE mock for `/api/rag/ask_stream` and `/api/rag/eoh_stream`:
```python
async def mock_sse_stream(question: str, mode: str):
    yield sse("phase_start", {"phase": "retrieval"})
    await asyncio.sleep(0.3)
    yield sse("retrieval_summary", {"sources_considered": 12, "sources_used": 8, "confidence": "high"})
    await asyncio.sleep(0.2)
    yield sse("reasoning_progress", {"step": "Applying EoH M13 flare trajectory..."})
    await asyncio.sleep(0.5)
    # Stream answer in chunks (simulates LLM token generation)
    answer = MOCK_ANSWERS[mode]
    for chunk in chunk_text(answer, size=12):
        yield sse("llm_chunk", {"content": chunk})
        await asyncio.sleep(0.03)
    yield sse("llm_done", {"text": answer, "confidence": 0.82, "limitations": ["Mock response"]})
    yield sse("completion", {"tokens_used": len(answer)//4, "duration_ms": 1200})
```

- Simulates real timing: retrieval → reasoning → streaming tokens → done
- `StreamingDisplay.tsx` will show all status phases, the animated answer, and the blinking cursor
- Two canned answers: one clinical Q&A (ask mode), one EoH-structured (eoh mode)

### `POST /api/eoh/router_plan`:
Returns static plan with question type A, 3-step module plan, doc retrieval plan.

### `GET /api/eoh/flarereport/{patient_id}`:
Returns static flare report with:
- `probabilistic_differential`: 4 diagnoses with probabilities
- `precursor_signals`: 3 signals with weights
- `risk_drivers`, `contradictions`, `guidance_for_clinician`, `safety_warnings`
- All matching the `EohdPage.tsx` response schema exactly

### `POST /api/coding`:
Returns static coding result with ICD-10 and SNOMED codes + confidence.

- **Frontend test**: AskPage streams live, EohdPage shows flare report with colored probability bars, CodingPage renders code suggestions

---

## Block 4 — Journal

- In-memory store (Python list) — entries persist within the mock server session
- `POST /api/journal` appends to the list, generates a UUID, adds mock `analysis` and `pattern_observations`
- `GET /api/journal` returns the list
- `DELETE /api/journal/{entry_id}` removes from list
- `GET /api/journal/timeline/{report_id}` returns a mock timeline bundle
- `POST /api/journal/query-ai` returns a canned AI analysis string
- **Frontend test**: JournalEditor creates entries, JournalEntryList shows them, delete works, AI query returns text

---

## Block 5 — Patient Portal + Doctor Portal

- `GET /api/patient/my-doctor` returns mock Dr. House
- `GET /api/patient/pending-invites` returns `[]`
- `POST /api/patient/invite-doctor` echoes back the email as pending
- Doctor endpoints mirror patient data — `GET /api/doctor/patients` returns Norman
- `GET /api/doctor/patients/{id}/journal` returns same as journal list
- `GET /api/doctor/patients/{id}/timeline-status` returns same as timeline/status
- **Frontend test**: PatientPortalPage and DoctorPortalPage fully render with doctor/patient info, portal cards link correctly

---

## Block 6 — Chat

- In-memory message history (Python list)
- `POST /api/chat/send` appends user message + generates mock assistant reply
- `GET /api/chat/history/{patient_id}` returns the history
- `POST /api/chat/anchor` stores the anchor and returns success
- `GET /api/chat/stats/{patient_id}` returns computed stats from history
- **Frontend test**: Chat graph renders messages, send works, anchoring works

---

## Block 7 — Portal Utilities

- `POST /api/portal/transcribe` returns mock transcription text
- `POST /api/portal/encounter_note` returns a static encounter note object
- `POST /api/portal/save-encounter` returns success with mock ID
- **Frontend test**: DoctorPortalPage transcription and encounter flows complete

---

## Frontend integration

Two ways to point the frontend at the mock server:

### Option A — env variable (recommended)
```bash
# frontend/.env.local
VITE_API_BASE=http://localhost:8100
VITE_DEV_BYPASS_AUTH=true
```

### Option B — Vite proxy rewrite
```typescript
// vite.config.ts — proxy /api to mock
server: {
  proxy: {
    '/api': 'http://localhost:8100'
  }
}
```

---

## Running

```bash
# From project root (WSL or Windows)
python -m server.mock.run
# → Mock server at http://localhost:8100
# → Swagger UI at http://localhost:8100/docs
# → OpenAPI JSON at http://localhost:8100/openapi.json

# Frontend (separate terminal)
cd frontend && npm run dev
# → Vite at http://localhost:3000, proxied to mock
```

---

## Dependencies

**Zero new dependencies.** FastAPI + uvicorn are already in `requirements-dev.txt`. The mock server uses only stdlib + FastAPI.

---

## What this enables

- **Full frontend development** with zero external services
- **OpenAPI contract** — frontend devs can generate TypeScript types from `/openapi.json`
- **Deterministic responses** — same input always produces same output, making visual regression testing trivial
- **SSE streaming simulation** — StreamingDisplay gets real phase transitions to animate
- **Offline-capable** — works on airplane wifi
- **Fast iteration** — mock server starts in <2s, hot-reloads with `--reload`
- **Schema validation** — Pydantic models on every mock endpoint catch frontend/backend contract drift early

---

## Execution order

| Block | Scope | Estimated size |
|-------|-------|----------------|
| 0 | Scaffold + OpenAPI | ~80 lines |
| 1 | Auth (9 endpoints) | ~60 lines |
| 2 | Timeline + Analytics (6 endpoints) | ~90 lines |
| 3 | EoH + RAG streaming (5 endpoints) | ~150 lines |
| 4 | Journal (5 endpoints) | ~80 lines |
| 5 | Patient + Doctor portals (8 endpoints) | ~70 lines |
| 6 | Chat (4 endpoints) | ~60 lines |
| 7 | Portal utilities (3 endpoints) | ~40 lines |
| **Total** | **41 endpoints** | **~630 lines** |
