# Patient Timeline Vision: Ingestion, Summarization, and Graph Enrichment

**Document type:** Technical product brief (draft for investor and strategic partner review)  
**Status:** Draft — subject to revision before external distribution  
**Codebase:** `2ndOpinionMD-MVP` (EoH / detective stack)  
**Last updated:** 2026-03-27  

*Internal context: This draft is intended to support upcoming conversations with life-science incubators and medical venture investors (including discussions aligned with Portal Innovations and medical VC audiences). Tone and claims should be tightened before any formal VC deck or data room use.*

---

## Executive summary

**PatientTimelineVision** is the system’s structured, incrementally maintained view of a patient’s clinical timeline: discrete **events** (diagnoses, labs, notes, medications, procedures, visits, flares, etc.), **provenance** for how each event was discovered, and **connascence** (typed relationships between events—temporal, causal, diagnostic, treatment, lab trends, symptom clusters).  

The platform separates three concerns that matter for regulated, high-stakes clinical AI:

1. **Ingestion** — how raw timeline text (EHR-backed events or PDF) becomes structured events and context.  
2. **Summarization for reasoning** — how `summarize_timeline_for_eoh` produces compact, investigation-ready narrative and snapshots for planners and UI (single-pass, probe+RAG, or hierarchical fallback).  
3. **Graph enrichment** — how the event graph grows and links over time: **lightweight opportunistic enrichment** after each detective step, versus **deeper two-phase enrichment** on PDF import when a DB pool is available.

Together, this yields an **auditable, compounding clinical memory** rather than a one-off LLM summary—an important differentiator for enterprise and compliance-minded buyers.

---

## What PatientTimelineVision is

Implementation follows a deliberate pattern (analogous to repository “vision” objects elsewhere in the stack): each patient has a **PatientTimelineVision** holding **TimelineEventVision** records with:

- Identity and type (`event_id`, `event_type`, `timestamp`, human-readable `preview`)  
- **Provenance:** `discovered_by` (e.g. structured snapshot, `pdf_page_N`, `detective_step_*`, manual)  
- **Connascence:** edges to other events, grouped by relationship type  
- **Session vs persisted mode:** `session_only` suppresses default persistence when appropriate  

Default on-disk location (when not session-only): `ai_coder_output/patient_timeline/{patient_id}_timeline_vision.jsonl`, via `get_default_vision_path`, `load_timeline_vision`, and `save_timeline_vision` in `server/eoh/patient_timeline_vision.py`.

---

## Path A — EoH Detective stream (production-shaped flow)

The **`eoh_detective`** path in `server/api/rag_stream_detective.py` orchestrates investigation steps and owns the relationship between **timeline summarization** and **vision graph** state.

### A1. Timeline load and summarizer (planner-facing)

1. **Load events** from the patient timeline (`load_patient_timeline`).  
2. **Build timeline context** (`build_timeline_context_from_events`) including diagnostic landscape payloads and landscape history where available.  
3. **One-shot call to `summarize_timeline_for_eoh`** — the detective run is the **owner** of this summarizer invocation for that session. It feeds the planner and downstream UX with a structured `TimelineSummaries` result (subject to timeout and graceful degradation).  
4. A **timeline snapshot** object is assembled for the planner (patient id, span, key signals, flare features, diagnostic landscape, history, canonical timeline text / summary fields as implemented).

This summarizer pass is **not** the same subsystem as incremental graph construction; it is the **reasoning-facing condensation** of the timeline for planning and display.

### A2. Load or create PatientTimelineVision

After the snapshot phase, the stream **loads** existing `PatientTimelineVision` for the patient, or **creates** a new instance with metadata such as `source: "detective_run"` when none exists. This graph is what gets **enriched** during the run.

### A3. Per-step opportunistic enrichment

After each detective step completes (question, streamed answer, citations), the pipeline calls **`enrich_graph_opportunistic`** in `server/eoh/graph_enrichment.py`. That function:

- Takes the step id, question, answer (trimmed), optional citations, patient id, and the current vision.  
- Samples existing events to give the model **local graph context** without unbounded context growth.  
- Invokes a **JSON-shaped** model response proposing **new events** and **new edges**, which are merged into the vision with provenance like `detective_step_{step_id}` and annotations marking opportunistic enrichment.

This is intentionally **lighter** than batch or full-corpus enrichment: it keeps latency compatible with interactive detective runs while still **compounding** structured memory across steps.

### A4. Persistence

After all steps, **`save_timeline_vision(detective_vision)`** persists the enriched graph (unless session-only semantics apply). The stream emits status events for load/save and enrichment metrics (events and edges added, totals, timing).

---

## Path B — PDF import (`summarize_timeline_from_pdf`)

For **session-oriented PDF import**, `summarize_timeline_from_pdf` in `server/eoh/timeline_summarizer.py` implements a distinct ingestion story:

1. **Open/decrypt** PDF as needed; avoid retaining secrets longer than necessary.  
2. **Extract text** per page and concatenate for downstream summarization.  
3. **Seed** a `PatientTimelineVision` (often `session_only=True` for strict session semantics) and **incrementally** process each page: LLM-assisted **event extraction** per page, then **`add_events_from_pdf_page`** (which can infer lightweight temporal connascence for new vs existing events).  
4. **Persist a temporary vision artifact** to `/tmp/...` for debugging or downstream tooling (forced save even when session-only).  
5. Call **`summarize_timeline_for_eoh`** on the full timeline text with RAG when a **pool** is available (`use_timeline_rag=True` when `pool` is set).  
6. When events exist **and** a pool is present, an optional **two-phase enrichment** runs: gap analysis (`analyze_timeline_enrichment_gaps`) and synthesis (`synthesize_timeline_enrichment`), applying opportunistic edges and follow-on logic as implemented.

Path B emphasizes **portable document ingestion** and **session privacy** (no writes to core RAG/EHR tables in the documented session-only design) while still producing the same **summarization contract** (`TimelineSummaries`) for EoH.

---

## `summarize_timeline_for_eoh` — behavior (single entrypoint, multiple strategies)

`summarize_timeline_for_eoh` is the **main summarization entrypoint** for the EoH stack. Documented behavior:

- **Small timelines:** single-pass JSON summary.  
- **Large timelines:** prefer **probe + RAG** over the patient timeline (when enabled and `pool` + `patient_id` support it), then return RAG-grounded text (with optional meds/labs snapshot from DB when available).  
- If RAG fails or is disabled: **hierarchical map/reduce** over chronological chunks.  
- On catastrophic failure: fall back to **truncated raw timeline** text rather than empty output.

This layered behavior is what allows the product to scale from **short extracts** to **longitudinal multi-year** records without a single brittle prompt.

---

## Why this matters for investors and partners

| Theme | Connection to this architecture |
|--------|----------------------------------|
| **Trust and auditability** | Events carry **discovered_by** provenance; graph edits are attributable to ingestion paths or explicit enrichment phases. |
| **Compounding product value** | Each detective run and (where enabled) PDF pipeline can **add** nodes and edges instead of replacing state—supporting longitudinal differentiation. |
| **Operational cost control** | Summarization **tiers** (single-pass vs RAG vs hierarchical) bound cost and latency; opportunistic enrichment avoids full-graph rewrites per step. |
| **Enterprise fit** | Separation of **session PDF** flows from **persisted** vision files maps cleanly to privacy reviews and deployment modes. |

---

## Source map (implementation references)

| Concern | Primary modules |
|--------|------------------|
| Detective orchestration, vision load/save, per-step enrichment | `server/api/rag_stream_detective.py` |
| Timeline summarization (`summarize_timeline_for_eoh`, PDF import) | `server/eoh/timeline_summarizer.py` |
| Opportunistic step enrichment | `server/eoh/graph_enrichment.py` (`enrich_graph_opportunistic`) |
| Vision model, default path, load/save helpers | `server/eoh/patient_timeline_vision.py` |
| Shared imports / re-exports | `server/api/rag_stream_shared.py` |

---

## Disclaimer

This document describes **current implementation intent** as reflected in the codebase at the time of writing. Behavior flags, timeouts, and deployment configuration may change; for binding representations, refer to the repository revision in use and your regulatory review process.
