# REPORT_READINESS

**Date:** 2026-02-20
**From:** Devin (Cognition)
**To:** Dylan, Nate
**Status:** Ready for tasking

---

## SOURCES INGESTED

| Document | Location | Summary |
|---|---|---|
| HANDOFF | `TO_NATE_SPELLBOOK_PORTAL_DEVIN_HANDOFF.md` | Full context transfer: backend status (100+ endpoints, done), frontend status (single HTML file, needs React), spellbook overview, doctor portal vision, stack recommendation, build priority |
| SpellBook | `2opmd_spellbook.json` | 404-line manifest: every endpoint, UX invariants, aesthetic spec, component specs, page routes, build priority, environment config, Docker setup, Make targets, security model, Devin constraints |
| ASK Streaming Contract | `ASK_STREAMING_CONTRACT.md` | 5-event SSE contract (phase_start, retrieval_summary, reasoning_progress, llm_chunk/llm_done, completion), receipt cache integration, UI behavior spec, transparency panel behavior |
| Frontend Integration | `FRONTEND_INTEGRATION.md` | Current wiring: mode-endpoint mapping, receipt cache event schema, transparency panel states, error handling, UI state management, CORS notes |
| Doctor Portal Game Plan | `GAME_PLAN_DOCTOR_PORTAL.md` | Ambient coding pipeline: audio capture -> Whisper (local) -> transcript -> NLP extraction -> /api/coding -> code suggestions -> encounter note -> timeline. 4 phases, 8 weeks. 5 new endpoints required. |
| Patient & Doctor Portals | `GAME_PLAN_PATIENT_DOCTOR_PORTALS.md` | Role selection at registration (doctor/patient). Splash page = modes + login. Patient portal: journal, timeline, EoHD. Doctor portal: patient list, read-only patient data. Data model: user_type, doctor_id. |
| Deploy Better UX | `DEPLOY_BETTER_UX.md` | One-line docker-compose volume swap from `./index.html` to `./rag-demo-ui/index.html` for nginx |

---

## TASK LIST (Execution Order)

### Phase 1: React Frontend Scaffold

| # | Task | Routing (Where to Find Everything) |
|---|---|---|
| 1.1 | **Read UX invariants** | `2opmd_spellbook.json` → `ux_invariants.hard_rules[]` (9 rules). Also referenced throughout the HANDOFF. No standalone `UX_INVARIANTS.md` exists in repo — invariants are in the spellbook. |
| 1.2 | **Read ASK streaming contract** | `ASK_STREAMING_CONTRACT.md` (354 lines). Defines the 5-event SSE protocol, receipt cache integration, status progression, and non-negotiable constraints. |
| 1.3 | **Read frontend integration doc** | `FRONTEND_INTEGRATION.md` (339 lines). Mode-endpoint mapping, receipt cache event schema, error handling patterns, CORS setup. |
| 1.4 | **Scaffold React app** | Create `frontend/` directory. Stack: Vite + React 18 + TypeScript + Tailwind CSS. Source: `2opmd_spellbook.json` → `frontend_buildout.recommended_tools`. No Redux, no axios, no GraphQL, no CSS-in-JS. |
| 1.5 | **Configure environment** | `2opmd_spellbook.json` → `environment`. VITE_API_BASE=`http://localhost:8000` (dev) or `''` (prod, same-origin via nginx). CORS origins already include `localhost:3000` and `localhost:8080` — see `architecture.cors_origins[]`. |

### Phase 2: Core Components (Modes)

| # | Task | Routing |
|---|---|---|
| 2.1 | **Build ModeSelector** | `2opmd_spellbook.json` → `frontend_buildout.components.ModeSelector`. Four buttons: ASK, CODING, EoH, EoHD. EoHD disabled (tooltip: "Blocked — timeline data ingestion not implemented"). No shortcuts, no recommendations, no auto-transitions. Routes: `/ask`, `/coding`, `/eoh`, `/eohd`. |
| 2.2 | **Build StreamingDisplay (ASK mode)** | Endpoint: `GET /api/rag/ask_stream` (SSE). Params: `q`, `limit=12`, `with_llm=1`, `llm_mode=chunk`. Contract: `ASK_STREAMING_CONTRACT.md`. Status progression: Connecting → RUNNING → Evidence: X/Y sources → [answer streams] → Complete. Use native `EventSource` API or `eventsource-parser`. Render LLM responses with `react-markdown`. |
| 2.3 | **Build StreamingDisplay (EoH mode)** | Endpoint: `GET /api/rag/eoh_stream` (SSE). Params: `q`, `limit=10`, `with_llm=1`, `llm_mode=chunk`. Same SSE consumer as ASK, different endpoint. See `2opmd_spellbook.json` → `ux_invariants.modes.eoh`. |
| 2.4 | **Build CodingReview (CODING mode)** | Endpoint: `POST /api/coding`. Body: `{"note": "clinical text", "context": "optional", "limit": 60}`. Response: JSON with `probable_dx`, `differential_dx`, `procedures`, `labs`, `medications`. Code cards with confidence scores, accept/reject per code, bulk export only after explicit confirmation. Export formats: JSON, CSV, PDF. See `2opmd_spellbook.json` → `ux_invariants.modes.coding`. |
| 2.5 | **Build EoHD disabled state** | Route `/eohd`: disabled button + explanation ("Blocked — timeline data ingestion not implemented"). No wiring. See `2opmd_spellbook.json` → `ux_invariants.modes.eohd`. |

### Phase 3: Infrastructure Components

| # | Task | Routing |
|---|---|---|
| 3.1 | **Build ReceiptCache** | Captures ALL SSE events + API responses + errors. Lossless audit trail. Export as JSON or HTML. See `ASK_STREAMING_CONTRACT.md` → "Receipt Cache Integration" and `FRONTEND_INTEGRATION.md` → "Receipt Cache Integration". Event schema: `{seq, timestamp, type, source, payload}`. |
| 3.2 | **Build TransparencyPanel** | Default state: no state mutated, no data persisted, no external calls, no session tracking. After API call: yellow warning "External API call made" + timestamp. Resets on mode switch. See `FRONTEND_INTEGRATION.md` → "Transparency Panel Behavior" and `ASK_STREAMING_CONTRACT.md` → "Transparency Panel Integration". |
| 3.3 | **Build ErrorBoundary** | Honest failure display. No softening. State cause + recovery paths. Network errors, API errors (4xx/5xx), SSE connection errors all handled. See `FRONTEND_INTEGRATION.md` → "Error Handling". |

### Phase 4: Auth Flow

| # | Task | Routing |
|---|---|---|
| 4.1 | **Build login** | `POST /api/auth/token` (form-encoded `username` + `password`). Returns `access_token`. Store as `Authorization: Bearer <token>`. Route: `/auth/login`. See `2opmd_spellbook.json` → `api_endpoints.auth`. |
| 4.2 | **Build registration** | `POST /api/auth/register`. Email verification required (tokens expire 30 min). Route: `/auth/register`. Resend: `POST /api/auth/resend-verification`. |
| 4.3 | **Build email verification** | `GET /api/auth/verify-email`. Route: `/auth/verify`. |
| 4.4 | **Build password reset** | `POST /api/auth/forgot-password` → `POST /api/auth/reset-password/{token}`. Routes: `/auth/forgot-password`, `/auth/reset-password/:token`. |
| 4.5 | **Build protected routes** | `GET /api/auth/users/me` to verify token. Guard journal and portal routes behind auth. Rate limits: auth endpoints 5 req/min/IP, general API 60 req/min/IP. See `2opmd_spellbook.json` → `security`. |

### Phase 5: Journal

| # | Task | Routing |
|---|---|---|
| 5.1 | **Build JournalEditor** | CRUD: `POST /GET /DELETE /api/journal`. AI analysis: `POST /api/journal/query-ai`. Fields: severity, environmental factors, diet, sleep, stressors. Use React Hook Form. Route: `/journal`. See `2opmd_spellbook.json` → `api_endpoints.journal`. |
| 5.2 | **Build JournalTimeline** | `GET /api/journal/timeline/{report_id}`. Visual timeline of entries. Feeds into future EoHD integration. |

### Phase 5a: Patient Enablement — Timeline Ingestion + EoHD Gate

| # | Task | Routing |
|---|---|---|
| 5a.1 | **Build TimelineUploadPage** | Route: `/timeline/upload`. File picker (PDF only, max 10MB), optional password field for encrypted PDFs, progress states (Idle → Uploading → Extracting → Ingesting → Done). Calls `POST /api/timeline/import-pdf` (multipart/form-data: `file` + optional `password`). Response: `{ timeline_id, patient_id, event_count, status }`. Auth required (Bearer JWT). Errors: 401, 403 (not system user), 400 (invalid PDF/wrong password), 413 (too large). See `GAME_PLAN_TIMELINE_UPLOAD_EOHD.md` → "Frontend Components → Timeline Upload Page". |
| 5a.2 | **Build TimelineStatusIndicator** | Calls `GET /api/timeline/status`. Response: `{ has_timeline, timeline_id, event_count, last_updated }`. Renders "Timeline ready" or "Upload timeline" link. Shown in header or mode selector. See `GAME_PLAN_TIMELINE_UPLOAD_EOHD.md` → "Frontend Components → Timeline Status Indicator". |
| 5a.3 | **Build EoHD gate logic** | If user has no timeline + is system user: show "Upload timeline to unlock EoHD" with link to `/timeline/upload`. If user has timeline: enable EoHD, pass `timeline_patient_id` to `/api/rag/eoh_stream` (or `/api/eoh/router_plan`). Free users: EoHD remains disabled with current message. See `GAME_PLAN_TIMELINE_UPLOAD_EOHD.md` → "Frontend Components → EoHD Gate". |
| 5a.4 | **Build EohdPage (enabled state)** | When timeline exists: show query input, call EoHD endpoints (`POST /api/eoh/router_plan`, `GET /api/eoh/flarereport/{patient_id}`, `GET /api/eoh/landscape/{patient_id}`). Display: question type classification, module execution plan, flare forecast, diagnostic landscape, precursor signals, risk drivers. See `server/api/eoh_router_routes.py` and `server/api/timeline_routes.py`. |
| 5a.5 | **Add /timeline/upload route** | Protected route (auth required). Add to App.tsx router. Redirect system users without timeline here after first login. See `GAME_PLAN_TIMELINE_UPLOAD_EOHD.md` → "User Flow". |
| 5a.6 | **Update ModeSelector EoHD card** | Replace static "Blocked" message with dynamic state: disabled (free user), "Upload timeline" (system user, no timeline), enabled (system user, has timeline). See `GAME_PLAN_TIMELINE_UPLOAD_EOHD.md` → "Frontend Components → EoHD Gate". |

### Phase 5c: Patient & Doctor Portals

| # | Task | Routing |
|---|---|---|
| 5c.1 | **Add user_type to users** | Migration: add `user_type VARCHAR(20) NOT NULL DEFAULT 'patient'`. Values: `patient` \| `doctor`. Add `doctor_id UUID REFERENCES users(id)` to users or create doctor_patients table. See `GAME_PLAN_PATIENT_DOCTOR_PORTALS.md` → "Data Model Changes". |
| 5c.2 | **Update registration API** | `POST /api/auth/register`: require `user_type` in body. Validate `user_type in ("patient", "doctor")`. Store in users. Update `GET /api/auth/me` to return `user_type`. |
| 5c.3 | **Add role selector to RegisterPage** | UI: radio or card select "I am a patient" \| "I am a doctor". Submit `user_type` in registration payload. See `GAME_PLAN_PATIENT_DOCTOR_PORTALS.md` → "Registration (New Requirement)". |
| 5c.4 | **Splash page (modes + login)** | HomePage `/`: unauthenticated → mode cards (ASK, CODING, EoH, EoHD) + LOGIN and REGISTER buttons. Authenticated → redirect to `/patient` or `/doctor` by user_type. See `GAME_PLAN_PATIENT_DOCTOR_PORTALS.md` → "Splash Page". |
| 5c.5 | **Patient portal shell** | Route `/patient`. Layout: nav (Journal, Timeline, EoHD, Settings). Guard: `user_type === "patient"`. Nest existing JournalPage, TimelineUploadPage, EohdPage. See `GAME_PLAN_PATIENT_DOCTOR_PORTALS.md` → "Patient Portal". |
| 5c.6 | **Doctor portal + patient list** | Route `/doctor`. `GET /api/doctor/patients`: list patients for current doctor (`doctor_id = current_user.id`). Patient list UI. DoctorPatientDetailPage `/doctor/patients/:id`: read-only journal, timeline status. Guard: `user_type === "doctor"`. See `GAME_PLAN_PATIENT_DOCTOR_PORTALS.md` → "Doctor Portal". |
| 5c.7 | **Patient–doctor linking (MVP)** | Seed/script to link test patients to doctors, or `POST /api/doctor/link-patient` (patient_email). See `GAME_PLAN_PATIENT_DOCTOR_PORTALS.md` → "Patient–Doctor Linking". |

### Phase 6: Doctor Portal — Patient Connection + Ambient Coding

#### 6.0 Patient–Doctor Connection (Invite Flow)

| # | Task | Routing |
|---|---|---|
| 6.0a | **Doctor invites patient (doctor portal)** | Doctor portal: "Connect patient" — enter patient email. System sends email to patient: register or log in and accept the connection. Backend: `POST /api/doctor/invite-patient` (body: `{ email }`). Creates pending link; sends email with magic link or token to `/auth/accept-doctor-invite?token=...`. See `GAME_PLAN_PATIENT_DOCTOR_PORTALS.md`. |
| 6.0b | **Patient invites doctor (patient portal)** | Patient portal: "Connect doctor" — enter doctor email. System sends email to doctor: register or log in and accept the connection. Backend: `POST /api/patient/invite-doctor` (body: `{ email }`). Creates pending link; sends email with magic link to `/auth/accept-patient-invite?token=...`. See `GAME_PLAN_PATIENT_DOCTOR_PORTALS.md`. |
| 6.0c | **Accept-invite flow** | New routes: `/auth/accept-doctor-invite`, `/auth/accept-patient-invite`. Token in query. If unauthenticated: redirect to login/register, then return to accept. If authenticated: confirm link, create `doctor_patients` (or set `doctor_id`), redirect to portal. Email templates: "Dr. X invites you to connect" / "Patient Y invites you as their doctor". |

#### 6.1+ Ambient Coding (Audio → Transcript → Codes)

| # | Task | Routing |
|---|---|---|
| 6.1 | **Build AudioCapture** | Browser `MediaRecorder` API. States: IDLE → RECORDING → PAUSED → STOPPED. 15s chunks, WAV format, 2s overlap. Red indicator when mic live. Patient consent required before recording. Route: `/portal`. See `GAME_PLAN_DOCTOR_PORTAL.md` → "Phase 1" and "UI Components → AudioCapture". |
| 6.2 | **Build LiveTranscript** | Chunks sent to `POST /api/portal/transcribe` (new endpoint, multipart). Whisper runs locally (privacy invariant — audio never leaves machine). Rolling text with timestamps. See `GAME_PLAN_DOCTOR_PORTAL.md` → "UI Components → LiveTranscript". |
| 6.3 | **Build ClinicalCodingOverlay / CodeSuggestions** | Transcript text → `POST /api/coding`. Live code cards with confidence. Accept/reject per code. Re-code every 60s or on significant new symptom. See `GAME_PLAN_DOCTOR_PORTAL.md` → "Phase 2" and "UI Components → CodeSuggestions". |
| 6.4 | **Build EncounterSummary** | New endpoint: `POST /api/portal/encounter_note`. Generates structured note from accepted codes + transcript. Export as PDF. Save to journal via `POST /api/journal`. See `GAME_PLAN_DOCTOR_PORTAL.md` → "Phase 3". |
| 6.5 | **Build Timeline Integration** | Auto-generate timeline events from encounters. Feed into `/api/timeline` endpoints. Enable EoHD when timeline data exists. See `GAME_PLAN_DOCTOR_PORTAL.md` → "Phase 4". |

### Phase 7: Deployment Wiring

| # | Task | Routing |
|---|---|---|
| 7.1 | **Update docker-compose.yml** | Swap nginx volume from `./rag-demo-ui/index.html` to React build output (e.g., `./frontend/dist`). See `DEPLOY_BETTER_UX.md` and `2opmd_spellbook.json` → `docker`. |
| 7.2 | **Update CORS_ALLOW_ORIGINS** | If frontend dev port changes from 3000/8080, update `architecture.cors_origins` in backend. See `2opmd_spellbook.json` → `architecture.cors_origins`. |

---

## ROUTING INDEX (Quick Reference)

| What You Need | Where It Lives |
|---|---|
| All API endpoints | `2opmd_spellbook.json` → `api_endpoints` |
| UX hard rules (9 invariants) | `2opmd_spellbook.json` → `ux_invariants.hard_rules[]` |
| Mode definitions + constraints | `2opmd_spellbook.json` → `ux_invariants.modes` |
| Component specs | `2opmd_spellbook.json` → `frontend_buildout.components` |
| Page routes | `2opmd_spellbook.json` → `frontend_buildout.pages` |
| Recommended stack / tools | `2opmd_spellbook.json` → `frontend_buildout.recommended_tools` |
| SSE streaming protocol | `ASK_STREAMING_CONTRACT.md` |
| Current frontend wiring | `FRONTEND_INTEGRATION.md` |
| Receipt cache event schema | `FRONTEND_INTEGRATION.md` → "Receipt Cache Integration" |
| Timeline upload + EoHD game plan | `GAME_PLAN_TIMELINE_UPLOAD_EOHD.md` |
| Patient & doctor portals game plan | `GAME_PLAN_PATIENT_DOCTOR_PORTALS.md` |
| Doctor portal pipeline | `GAME_PLAN_DOCTOR_PORTAL.md` |
| New portal endpoints needed | `GAME_PLAN_DOCTOR_PORTAL.md` → "New Endpoints Required" |
| Ambient transcription tools | `transcription_machine.py`, `wave_modulation_machine.py`, `wave_modulation_agent.py` (repo root) |
| Transcription pipeline docs | `TRANSCRIPTION_PIPELINE_README.md` |
| Docker deployment | `DEPLOY_BETTER_UX.md`, `docker-compose.yml`, `docker/` |
| Backend entry point | `server/api/app_postgres.py` |
| Backend runner | `server/scripts/run_postgres_app.py` |
| Auth routes (backend) | `server/api/auth_routes_postgres.py` |
| Coding routes (backend) | `server/api/coding_routes.py`, `server/api/coding_routes_v2.py` |
| RAG streaming routes (backend) | `server/api/rag_stream_routes.py` |
| Journal routes (backend) | `server/api/journal.py` |
| Timeline routes (backend) | `server/api/timeline_routes.py` |
| EoH routes (backend) | `server/api/eoh_router_routes.py`, `server/eoh/` |
| Terminology routes (backend) | `server/api/snomed_routes.py`, `server/api/loinc_routes.py`, `server/api/rxnorm_routes.py`, `server/api/hpo_routes.py`, `server/api/chv_routes.py`, `server/api/orphanet_routes.py` |
| Guidelines routes (backend) | `server/api/guidelines_routes.py`, `server/api/guidelines_cdc_routes.py`, `server/api/guidelines_va_routes.py`, `server/api/nice_routes.py` |
| Genomics routes (backend) | `server/api/clingen_actionability_routes.py`, `server/api/disgenet_routes.py`, `server/api/gwas_routes.py`, `server/api/panelapp_routes.py` |
| Environment variables | `.env.example` |
| Makefile targets | `2opmd_spellbook.json` → `make_targets` |
| Database migrations | `server/alembic/` |
| Security / rate limits | `2opmd_spellbook.json` → `security` |
| Email allowlist | `server/allowed_emails.txt` |
| PortalVision module | `PortalVision/` (audio routes, receipts, vault, printer, consent) |
| Aesthetic spec | `2opmd_spellbook.json` → `aesthetic` |
| Test commands | `2opmd_spellbook.json` → `devin_instructions.testing` |

---

## CONSTRAINTS (Non-Negotiable, from SpellBook)

1. Modes do not share state
2. Modes do not auto-transition
3. No session persistence across queries
4. No "remembering your preferences"
5. No optimistic UI / fake progress bars / partial results
6. Failures surfaced honestly — stop, state cause, state recovery paths
7. Export is one-way transmission with no feedback loop
8. ALL SSE events captured in receipt cache (lossless audit trail)
9. Only contract-specified events affect UI display
10. Do NOT use axios — fetch is sufficient
11. Do NOT add analytics, telemetry, or tracking
12. Do NOT add gradients, animations (except loading), or decorative elements
13. CODING mode exports require explicit operator confirmation before sending
14. EoHD button must be disabled until timeline upload is implemented
15. Audio never leaves the machine (Whisper runs locally, HIPAA invariant)

---

## READINESS STATUS

| Item | Status |
|---|---|
| HANDOFF ingested | YES |
| SpellBook ingested | YES |
| Streaming contract understood | YES |
| Frontend integration doc read | YES |
| Doctor portal game plan read | YES |
| Deployment wiring understood | YES |
| All endpoint routes mapped | YES |
| All component specs located | YES |
| All backend source files identified | YES |
| Constraints cataloged | YES |

**Ready to execute. Awaiting tasking.**
