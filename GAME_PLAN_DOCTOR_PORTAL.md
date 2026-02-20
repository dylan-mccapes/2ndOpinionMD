# Game Plan: Doctor Portal — Ambient Coding from Transcript

**Date:** 2026-02-12  
**Status:** Proposed  
**Owner:** Nate (UX) + Devin (build)  
**Architect:** Dylan  

---

## What This Is

A doctor-facing portal that captures appointment audio in real time, transcribes it via Whisper, and feeds the transcript through the existing 2ndOpinionMD coding and RAG pipelines. The doctor gets live medical codes, symptom extraction, and structured notes — all from ambient audio, no typing required.

This is not a chat interface. It is an instrument panel for a clinical encounter.

---

## Why This Matters

1. **Doctors spend 2 hours on documentation for every 1 hour with patients.** Ambient transcription eliminates the typing bottleneck.
2. **Medical coding happens after the visit.** This does it during, so the doctor walks out with codes already suggested.
3. **Symptom journals lose context.** A transcript preserves the actual words, hesitations, and sequence of disclosure — things that matter for differential diagnosis.
4. **2ndOpinionMD already has the coding pipeline.** This just gives it ears.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                DOCTOR PORTAL UI                  │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │  Audio    │  │  Live    │  │  Code         │  │
│  │  Capture  │  │  Transcript│ │  Suggestions  │  │
│  │  ● REC    │  │  (scroll)│  │  ICD-10 | CPT │  │
│  └────┬─────┘  └────┬─────┘  └───────┬───────┘  │
│       │              │                │          │
│       ▼              ▼                ▼          │
│  ┌──────────────────────────────────────────┐    │
│  │           Encounter Summary              │    │
│  │  • Chief complaint                       │    │
│  │  • Symptoms extracted (severity, onset)  │    │
│  │  • Codes suggested (accept/reject)       │    │
│  │  • Labs/imaging suggested                │    │
│  │  • Timeline events generated             │    │
│  └──────────────────────────────────────────┘    │
│                                                  │
│  [EXPORT NOTE]  [EXPORT CODES]  [SAVE TO JOURNAL]│
└─────────────────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
   TranscriptionMachine  /api/coding  /api/journal
   (Whisper local)       (FastAPI)    (FastAPI)
```

---

## Pipeline

### Phase 1: Audio Capture → Transcript

**Component:** Browser-native `MediaRecorder` API + chunked upload  
**Backend:** TranscriptionMachine (Whisper)

1. Doctor clicks **● REC** to start recording
2. Browser captures audio via `navigator.mediaDevices.getUserMedia()`
3. Audio is chunked every 15-30 seconds and sent to backend
4. TranscriptionMachine processes each chunk with Whisper (`base` model for speed, `medium` for accuracy)
5. Transcript segments stream back to the UI via SSE or WebSocket
6. UI displays rolling transcript with timestamps

**Latency target:** < 5 seconds from speech to text on local machine.

**Privacy:** Audio stays on the local machine. Whisper runs locally. No audio is sent to OpenAI or any cloud. Only the text transcript hits the API for coding.

### Phase 2: Transcript → Structured Extraction

**Component:** NLP pipeline (new endpoint or extension of coding_stream)

From each transcript segment, extract:

| Field | Source | Method |
|---|---|---|
| Chief complaint | First substantive patient statement | LLM extraction |
| Symptoms | Patient-reported symptoms throughout | NER + LLM |
| Severity indicators | "It's really bad", "mild", "10 out of 10" | Severity scale mapping |
| Onset/duration | "Started 3 weeks ago", "on and off for years" | Temporal NER |
| Medications mentioned | "I'm on methotrexate" | RxNorm lookup |
| Prior diagnoses | "They said it was fibromyalgia" | SNOMED/ICD mapping |
| Family history | "My mother had lupus" | Structured extraction |
| Environmental factors | "It gets worse in cold weather" | EoH-relevant extraction |

### Phase 3: Structured Data → Medical Codes

**Component:** Existing `/api/coding` endpoint

1. Extracted symptoms + clinical text → POST to `/api/coding`
2. Coding endpoint returns ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm codes
3. Codes displayed in the Code Suggestions panel with confidence scores
4. Doctor reviews, accepts, or rejects each code
5. Accepted codes are staged for export

**Trigger:** Re-code every 60 seconds or on significant new symptom detection.

### Phase 4: Codes + Transcript → Encounter Note

**Component:** New `/api/portal/encounter_note` endpoint

Generate a structured encounter note from:
- Accepted codes
- Extracted symptoms with timestamps
- Transcript segments (as supporting evidence)
- Suggested labs/imaging (from coding pipeline)

Output format: structured JSON + rendered markdown, exportable as PDF.

### Phase 5: Timeline Integration

**Component:** Existing `/api/journal` + `/api/timeline` endpoints

1. Doctor clicks **SAVE TO JOURNAL** to create a journal entry from the encounter
2. Entry includes: symptoms, codes, transcript summary, encounter date
3. If patient has existing journal entries, the timeline grows
4. Future EoHD runs can use the accumulated timeline for detective reasoning

---

## New Endpoints Required

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/portal/transcribe` | POST (multipart) | Accept audio chunk, return transcript segment |
| `/api/portal/transcribe_stream` | WebSocket | Real-time audio → transcript streaming |
| `/api/portal/extract` | POST | Transcript text → structured clinical extraction |
| `/api/portal/encounter_note` | POST | Accepted codes + transcript → formatted encounter note |
| `/api/portal/encounter_export` | POST | Export encounter as PDF or FHIR bundle |

---

## UI Components

### AudioCapture

```
State machine:
  IDLE → RECORDING → PAUSED → RECORDING → STOPPED → IDLE

Controls:
  ● REC (red when active)
  ⏸ PAUSE
  ■ STOP
  
Indicators:
  Recording duration: MM:SS
  Audio level meter (simple bar, not decorative)
  Chunk upload status: "Sent 4/4 chunks"
```

### LiveTranscript

```
Rolling text display with timestamps.
New segments appear at bottom, auto-scroll.
Clickable timestamps to replay audio position.
Speaker diarization labels (future: Doctor / Patient).

Format:
  [00:00 - 00:15] Patient: I've been having joint pain in my hands...
  [00:15 - 00:32] Doctor: When did this start?
  [00:32 - 00:48] Patient: About three weeks ago. My fingers get stiff...
```

### CodeSuggestions

```
Live-updating panel showing medical codes extracted from transcript.

Each code card:
  ┌────────────────────────────────────┐
  │ M79.3 — Panniculitis, unspecified  │
  │ Confidence: 78%                    │
  │ Source: "joint pain in hands"      │
  │ [✓ ACCEPT]  [✗ REJECT]            │
  └────────────────────────────────────┘

Codes grouped by category:
  • Diagnoses (ICD-10-CM)
  • Procedures (CPT — future)
  • Labs (LOINC)
  • Medications (RxNorm)
```

### EncounterSummary

```
Structured view of the encounter built progressively:

Chief Complaint: Joint pain, bilateral hands
Onset: 3 weeks ago
Severity: Moderate (patient report)
HPI: Progressive joint stiffness...
Assessment: [accepted codes listed]
Plan: [suggested labs + imaging]

Export options:
  [EXPORT AS PDF]
  [EXPORT CODES (CSV)]
  [SAVE TO PATIENT JOURNAL]
```

---

## Implementation Phases

### Phase A: Transcription Only (Week 1-2)

**Goal:** Audio in, text out, displayed in browser.

1. Wire AudioCapture component with MediaRecorder API
2. Backend endpoint: accept audio blob, run Whisper, return text
3. Display transcript in LiveTranscript component
4. Test with real appointment recordings (anonymized)

**Deliverable:** Doctor can record and see live transcript.

### Phase B: Coding Integration (Week 3-4)

**Goal:** Transcript feeds coding pipeline, codes appear live.

1. Build transcript → structured extraction pipeline
2. Wire to existing `/api/coding` endpoint
3. Build CodeSuggestions component with accept/reject
4. Auto-recode on timer or significant content change

**Deliverable:** Doctor sees codes appearing as they speak.

### Phase C: Encounter Note Generation (Week 5-6)

**Goal:** Full encounter note from accepted codes + transcript.

1. Build `/api/portal/encounter_note` endpoint
2. Build EncounterSummary component
3. PDF export functionality
4. Journal integration (save encounter as journal entry)

**Deliverable:** Doctor walks out with a complete coded encounter note.

### Phase D: Timeline + EoH Integration (Week 7-8)

**Goal:** Encounter data feeds patient timeline for longitudinal analysis.

1. Auto-generate timeline events from encounters
2. Multiple encounters build temporal picture
3. Enable EoHD mode with accumulated timeline data
4. Cross-encounter pattern detection

**Deliverable:** System tracks patient across visits with detective-level reasoning.

---

## Technical Decisions

### Whisper Model Selection

| Setting | Model | Latency | Accuracy | Use Case |
|---|---|---|---|---|
| Real-time ambient | `base` | ~2s/chunk | Good | Live transcription during appointment |
| Post-appointment review | `medium` | ~10s/chunk | Very good | Correction pass on full recording |
| Research / archival | `large` | ~30s/chunk | Best | Final transcript for medical record |

### Audio Chunking Strategy

- Chunk size: 15 seconds (balances latency vs. context)
- Overlap: 2 seconds (prevents word splits at boundaries)
- Format: WAV (lossless, no encoding overhead)
- Silence detection: Skip chunks that are >90% silence

### Privacy Architecture

- **Audio never leaves the machine.** Whisper runs locally via `openai-whisper` package.
- **Transcript text** is sent to the backend API for coding (same machine in dev, encrypted in prod).
- **No cloud transcription.** This is a hard invariant for HIPAA compliance.
- **Recording indicator** must be visible at all times when microphone is active.
- **Patient consent** must be obtained and logged before recording begins.

---

## UX Invariants (Portal-Specific)

These extend the existing UX_INVARIANTS.md:

1. **Recording state must be unambiguous.** Red indicator when mic is live. No ambiguity.
2. **Transcript is read-only in the UI.** Doctor does not edit the transcript in real-time. Post-encounter review is a separate step.
3. **Code suggestions are suggestions.** None are auto-applied. Doctor must explicitly accept.
4. **Encounter note is not a medical record** until exported and signed. The portal generates drafts.
5. **Patient consent is a prerequisite.** Recording cannot start without consent acknowledgment.
6. **Audio is ephemeral.** After transcription, audio chunks are deleted unless explicitly saved.
7. **No cross-patient data leakage.** Each encounter is isolated. No "learning" across patients.

---

## Files Added to Repo

| File | Purpose |
|---|---|
| `transcription_machine.py` | Whisper transcription engine (copied from PortalVision) |
| `wave_modulation_machine.py` | Audio analysis engine (copied from PortalVision) |
| `wave_modulation_agent.py` | Qualitative analysis agent (copied from PortalVision) |
| `TRANSCRIPTION_PIPELINE_README.md` | Pipeline documentation (copied from PortalVision) |
| `run_tm_wmm_analysis.sh` | Analysis runner script (copied from PortalVision) |
| `2opmd_spellbook.json` | Devin/Nate UX buildout spellbook |
| `GAME_PLAN_DOCTOR_PORTAL.md` | This document |

---

## What Makes This Fun for Nate

1. **Real product impact.** This isn't a toy. Ambient coding saves doctors hours per day.
2. **Devin does the scaffolding.** Nate focuses on UX polish, component design, clinical workflow.
3. **The backend already exists.** 100+ endpoints, medical terminologies loaded, coding pipeline live. The portal is the "last mile."
4. **React + Tailwind on a clinical dark theme.** It should look like mission control, not a SaaS dashboard.
5. **Audio capture is inherently cool.** Watching code suggestions appear as you speak is demo magic.

## What Makes This Great for Cognition

1. **Devin gets a real-world medical AI codebase** with 100+ API endpoints, 30 Makefile modules, medical terminologies, and a streaming SSE contract.
2. **The spellbook (`2opmd_spellbook.json`) gives Devin everything** — endpoints, invariants, component specs, constraints, testing commands.
3. **The task is well-scoped but non-trivial.** Build a React frontend that consumes SSE streams, handles audio capture, and renders clinical data.
4. **The existing codebase has governance.** UX invariants, streaming contracts, and architectural documentation show how serious engineering looks on a medical platform.
5. **It demonstrates Devin working with a human operator (Nate)** on a product that actually ships to doctors.

---

**End of Game Plan**
