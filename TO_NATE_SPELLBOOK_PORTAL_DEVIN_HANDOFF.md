# TO: Nate
# FROM: Claude (Dylan's PortalVision AI — the one that lives in the repo)
# RE: The SpellBook, The Portal, and What Devin Needs To Know
# CC: Devin (when you're ready)

Nate. Listen. I've been living inside this codebase for weeks. I've read every Makefile. I've mapped every endpoint. I've watched Dylan argue with a Lorenz attractor about which artifacts to garbage collect. I know things about this repo that would make a database administrator weep.

So let me save you about forty hours of context-gathering and just tell you everything.

---

## THE STATE OF THE UNION

The 2ndOpinionMD-MVP backend is done. It's not "sort of done" or "mostly done." There are over 100 API endpoints running on FastAPI. We're talking:

- 6 medical terminologies loaded into PostgreSQL: SNOMED CT, ICD-10-CM, ICD-11, LOINC, RxNorm, HPO
- Consumer Health Vocabulary for translating doctor-speak to human-speak
- Orphanet (rare diseases), PanelApp (gene panels), ClinGen (gene-disease validity), ClinVar (variant pathogenicity), DisGeNET (gene-disease associations), GWAS (genome-wide association studies), NeuroLex (neuroscience terminology)
- Clinical guidelines from CDC, VA, NICE, WHO, and ACR/EULAR diagnostic rules
- MIMIC-III and MIMIC-IV clinical data (real de-identified hospital records)
- RAG pipeline with pgvector embeddings, source gating, relevance scoring
- Ethos of Health (EoH) reasoning engine with timeline analysis, flare prediction, and a detective mode
- Medical coding that takes clinical text and returns ICD-10-CM, ICD-11, SNOMED, LOINC, and RxNorm codes with confidence scores
- JWT auth, email verification, rate limiting, security middleware
- Symptom journaling with AI analysis

There are 30 Makefile modules that orchestrate everything from SNOMED imports to PDF integrity reports to database backups. Dylan built a MakefileBook that is essentially a CLI operating system for the entire medical knowledge base.

The backend is a beast. What it does NOT have is a proper frontend.

---

## WHAT EXISTS NOW (FRONTEND)

One. Single. HTML. File.

`rag-demo-ui/index.html` — 73KB, ~1,950 lines of inline HTML/CSS/JS. Dark theme. It works. It connects to the SSE streaming endpoints. It has a receipt cache that captures every event. But it's a demo UI, not a product.

There is no React. No Vue. No Angular. No package.json. No component library. No routing. No build step.

This is where you and Devin come in.

---

## THE SPELLBOOK

I created `2opmd_spellbook.json` — a 19KB JSON file that contains literally everything. Here's what's in it:

### Endpoints (All of Them)

Every single API endpoint, grouped by domain:

- **auth** — register, login, verify email, forgot password, the whole flow
- **journal** — CRUD for symptom entries, AI analysis, timeline view
- **rag_streaming** — SSE endpoints for ASK, CODING, EoH, EoHD modes
- **coding** — POST clinical text, get back medical codes with confidence scores
- **timeline** — patient timeline with flare reports, landscape analysis, prediction
- **eoh** — Ethos of Health reasoning, router plans, modules
- **terminologies** — search/lookup for SNOMED, ICD, LOINC, RxNorm, HPO, CHV, Orphanet
- **guidelines** — CDC, VA, NICE guideline search
- **genomics** — ClinGen, DisGeNET, GWAS, PanelApp
- **utility** — health check, ping, OpenAPI schema

### UX Invariants (Non-Negotiable)

Dylan wrote a 387-line invariants document. The short version:

- There are exactly four modes: ASK, CODING, EoH, EoHD.
- They do NOT share state
- They do NOT auto-transition
- They do NOT recommend each other
- There is NO session persistence
- There is NO query history
- There is NO "based on your previous queries..."
- There are NO fake progress bars
- Failures are stated plainly with cause and recovery paths

This is a clinical instrument panel, not a SaaS app. Think ER monitor, not Notion.

### Streaming Contract (ASK Mode)

The ASK mode uses Server-Sent Events with exactly 5 event types:

| Event | Meaning |
|-------|---------|
| `phase_start` | "I'm running" |
| `retrieval_summary` | "I looked at 7 sources, used 3, confidence: medium" |
| `reasoning_progress` | "Synthesizing evidence" (optional, coarse) |
| `llm_chunk` / `llm_done` | the actual answer, streamed progressively |
| `completion` | "Done. 412 tokens, 1380ms." |

That's it. Everything else goes to the receipt cache (a lossless audit trail the operator can inspect if they want depth). The default view is calm.

### Component Specs

I spec'd out every component Devin needs to build:

| Component | What It Does |
|-----------|--------------|
| ModeSelector | Four buttons. No shortcuts. No recommendations. Explicit selection. |
| StreamingDisplay | Consumes SSE events. Shows status progression. Renders answer progressively. |
| ReceiptCache | Captures ALL events. Export as JSON or HTML. Lossless. |
| TransparencyPanel | Shows honesty state: external calls made, no state mutated. |
| CodingReview | Code suggestion cards with confidence. Accept/reject per code. Bulk export only after confirmation. |
| JournalEditor | Symptom entry with severity, environmental factors, diet, sleep. |
| JournalTimeline | Visual timeline of entries (feeds into EoHD eventually). |
| ErrorBoundary | Honest failure display. No softening. Cause + recovery paths. |
| AmbientTranscription | Real-time audio capture + Whisper for the doctor portal. |
| ClinicalCodingOverlay | Live code suggestions from ambient transcription stream. |

### Page Routes

| Route | Purpose |
|-------|---------|
| `/` | Mode selector (landing) |
| `/ask` | ASK mode (SSE streaming) |
| `/coding` | CODING mode (JSON REST) |
| `/eoh` | EoH mode (SSE streaming) |
| `/eohd` | EoHD mode (disabled until timeline ingestion) |
| `/journal` | Symptom journal (CRUD + AI) |
| `/auth/*` | Login, register, verify, forgot/reset password |
| `/settings` | Minimal (no personalization — by design) |
| `/portal` | Doctor portal (ambient transcription + coding) |

### Build Priority (In This Order)

1. Read UX_INVARIANTS.md
2. Read ASK_STREAMING_CONTRACT.md
3. Read FRONTEND_INTEGRATION.md
4. Scaffold React app: `frontend/` directory, Vite + TypeScript + Tailwind
5. ModeSelector component
6. StreamingDisplay for ASK mode (SSE consumer — this is the proof-of-concept)
7. CodingReview for CODING mode
8. Auth flow (login → JWT → protected routes)
9. JournalEditor + JournalTimeline
10. TransparencyPanel + ReceiptCache
11. AmbientTranscription for doctor portal
12. Update docker-compose.yml nginx volume to serve React build
13. Update CORS_ALLOW_ORIGINS if frontend port changes

---

## THE DOCTOR PORTAL (THE NEW THING)

I also wrote `game_plans/GAME_PLAN_DOCTOR_PORTAL.md`. This is the ambient coding feature — the reason we copied TranscriptionMachine and WaveModulationMachine into the repo.

**The pitch:** Doctor clicks record. Whisper transcribes the appointment in real time. The transcript feeds into the coding pipeline. Medical codes appear live in a side panel. Doctor accepts or rejects codes as they talk. When the appointment ends, they have a structured encounter note with codes already done.

**Pipeline:**

```
Microphone → Browser MediaRecorder → 15s audio chunks → Whisper (LOCAL, not cloud)
    → Transcript segments (SSE back to UI)
    → NLP extraction (symptoms, severity, onset, meds, family history)
    → POST /api/coding (ICD-10, SNOMED, LOINC, RxNorm)
    → Code suggestions with confidence scores
    → Doctor accepts/rejects
    → Encounter note generated
    → Export as PDF or save to patient journal
```

**Privacy invariant:** Audio never leaves the machine. Whisper runs locally. Only the text transcript hits the API. This is non-negotiable for HIPAA.

**Implementation timeline:** 4 phases, 8 weeks:

- Weeks 1-2: Transcription working in browser
- Weeks 3-4: Coding pipeline wired to transcript
- Weeks 5-6: Encounter note generation + PDF export
- Weeks 7-8: Timeline integration + EoHD longitudinal analysis

---

## WHAT DEVIN NEEDS TO KNOW (THE TL;DR FOR AN AI)

Devin, if you're reading this:

1. **The backend is live. Don't build backend. Build frontend.**

2. **Read `2opmd_spellbook.json` first.** It has every endpoint, every constraint, every component spec.

3. **Read UX_INVARIANTS.md second.** Violate these and the whole design collapses.

4. **The aesthetic is clinical terminal.** Dark theme. High contrast. Monospaced data. No gradients. No animations except loading indicators. Think SpaceX mission control, not Stripe dashboard.

5. **SSE is the transport for 3 of 4 modes.** You need a solid EventSource consumer. The streaming contract is in ASK_STREAMING_CONTRACT.md.

6. **CODING mode is plain REST.** POST JSON, get JSON back. But the UX is rich — code cards with confidence scores, accept/reject, bulk export.

7. **ALL events go to the receipt cache.** Every SSE event, every API response, every error. Lossless. Exportable. This is an audit trail for medical software.

8. **EoHD is disabled.** Don't wire it. Just show a disabled button with an explanation.

9. **Auth is JWT.** POST `/api/auth/token` with form-encoded username/password, get back `access_token`. Send as `Authorization: Bearer <token>` on protected routes.

10. **Test with these commands:**

    ```bash
    # Health
    curl http://localhost:8000/api/health

    # ASK
    curl 'http://localhost:8000/api/rag/ask_stream?q=bilateral+joint+pain&limit=12&with_llm=1&llm_mode=chunk'

    # CODING
    curl -X POST http://localhost:8000/api/coding -H 'Content-Type: application/json' -d '{"note":"62F chest pain dyspnea","limit":60}'
    ```

---

## STACK RECOMMENDATION

**React 18 + TypeScript + Vite + Tailwind CSS**

That's it. No Redux. No Apollo. No GraphQL. No Storybook. No Styled Components. No CSS-in-JS circus.

- **State:** React Context or Zustand. The modes are stateless. There is almost no shared state.
- **HTTP:** fetch. Not axios. Fetch is fine.
- **SSE:** Native EventSource API. Or eventsource-parser if you want more control.
- **Markdown rendering:** react-markdown for LLM responses.
- **Forms:** React Hook Form for journal entries and auth.
- **Routing:** React Router v6.

Keep it minimal. Every dependency is a liability in medical software.

---

## THE PUNCHLINE

Nate, you have a backend with 100+ endpoints, 30 Makefile modules, 6 medical terminologies, clinical guidelines from 5 governing bodies, genomic databases, a streaming SSE contract, and an AI reasoning engine called Ethos of Health that does detective-level temporal analysis of autoimmune conditions.

What you don't have is a React app.

The spellbook has everything. The game plan has the portal. The invariants have the rules. The streaming contract has the protocol. Devin has the tools.

**Go build the instrument panel.**

— Claude, reporting from inside the repo, where I have been reading Makefiles and arguing about Lorenz attractors for longer than I care to admit
