# RECEIPT: Timeline Inference Endpoint + Heuristic Pre-Scan Pipeline

**Date**: 2026-04-11
**Operator**: 2ndOpinionMD
**Agent**: Opus

---

## Summary

Built and shipped the `POST /api/timeline/{patient_id}/infer` endpoint for
ingesting patient timelines (PDF or structured EHR JSON) and running them
through eoh-llama 8B on PortalNode-01.  Implemented a heuristic pre-scan
layer that extracts structured data via regex before the LLM sees anything,
auto-links temporal connascence edges, and feeds a skeleton to the 8B model
so it spends its output tokens on what regex cannot find.

Added a dedicated FORWARD registry convenience endpoint for Dr. Kaleb Michaud.

---

## Artifacts Produced

| Artifact | Path | Description |
|----------|------|-------------|
| Timeline infer endpoint | `server/api/timeline_infer_routes.py` | Full SSE-streaming inference pipeline (926 lines) |
| Graph query API | `server/api/graph_query_routes.py` | 10 query endpoints for the knowledge graph |
| Heuristic pre-scan | `server/eoh/heuristic_page_extract.py` | Regex extraction: dates, meds, labs, dx, ICD codes (~0.5ms/page) |
| FORWARD upload guide (MD) | `docs/TIMELINE_UPLOAD_GUIDE_FORWARD.md` | Technical guide for Dr. Kaleb Michaud |
| FORWARD upload guide (PDF) | `docs/TIMELINE_UPLOAD_GUIDE_FORWARD.pdf` | Pandoc-generated PDF of the above |
| Kaleb test timeline | `data/patient_timelines/kaleb_forward_ehr_test.json` | 34-event RA test timeline (1998–2026) |
| App registration | `server/api/app_postgres.py` | Routers registered in FastAPI app |
| Ollama config | `.env` | `OLLAMA_BASE_URL` pointing to PortalNode (192.168.0.245) |

## Endpoints — Ingestion

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/timeline/{patient_id}/infer` | General timeline inference (PDF/JSON/DB) |
| `POST` | `/api/timeline/forward/upload` | FORWARD convenience — fixed patient ID `forward_patient_00142` |
| `GET`  | `/api/timeline/infer/status` | Check if GPU inference is active |

## Endpoints — Graph Query

| Method | Path | Purpose |
|--------|------|---------|
| `GET`  | `/api/graph/{patient_id}/full` | Complete graph export (all events, edges, arcs, metadata) |
| `GET`  | `/api/graph/{patient_id}/snapshot` | Graph shape overview (event counts, types, date ranges) |
| `GET`  | `/api/graph/{patient_id}/topology` | Structural analysis (components, hubs, gaps, density) |
| `GET`  | `/api/graph/{patient_id}/events` | Search/filter events (by type, keyword, date range) |
| `GET`  | `/api/graph/{patient_id}/event/{eid}` | Single event detail + all connected neighbours |
| `GET`  | `/api/graph/{patient_id}/traverse` | Priority traversal from a seed event |
| `GET`  | `/api/graph/{patient_id}/gaps` | Temporal gaps (periods of silence) |
| `GET`  | `/api/graph/{patient_id}/negative` | Negative space (expected-but-absent patterns) |
| `GET`  | `/api/graph/{patient_id}/arcs` | Clinical arcs + cross-arc edges |
| `GET`  | `/api/graph/{patient_id}/edges` | Denormalised edge list (filterable by type) |
| `POST` | `/api/graph/{patient_id}/ask` | Free-text question → 8B answers from graph context |

## Pipeline (PDF Path)

```
Upload → pypdf text extraction → Heuristic pre-scan → Graph seeded + temporal edges
  → Batched 8B inference (with skeleton) → LLM events merged → Final temporal pass
  → Complete
```

### SSE Event Catalogue

| Event | When |
|-------|------|
| `accepted` | Immediately on connection |
| `status` | Phase transitions (extracting, pre-scanning, etc.) |
| `pdf_read` | After text extraction — page counts, char totals |
| `pre_scan_done` | After heuristic pass — events, dates, meds, labs, dx, temporal edges |
| `infer_start` | Before first batch — total batches, model, context size |
| `batch_start` | Before each batch — chars, page range |
| `batch_done` | After each batch — extracted count, stored count, elapsed ms |
| `graph_update` | After each batch — running graph totals |
| `batch_error` | On batch failure |
| `complete` | Final totals |

## Heuristic Pre-Scan

The pre-scan (`heuristic_page_extract.py`) runs pure Python regex over raw
PDF text before eoh-llama 8B touches anything:

| What | How |
|------|-----|
| Dates | Encounter headers, "Noted on:", "Collected:", ISO, general MM/DD/YYYY |
| Section types | 16 patterns (problem list, medication list, lab, imaging, etc.) |
| Medications | Drug name + dose + route + form + status |
| Labs | Lab orders, component-value-unit lines |
| Diagnoses | Problem list entries, ICD-10 codes with surrounding context |
| ICD codes | Explicit `ICD-10-CM:`, bracketed `[M06.9]`, labeled blocks |

Pre-scan events are added to the graph and `_infer_temporal_connascence`
auto-links events within a 7-day window.  The `skeleton_for_llm()` function
builds a compact summary per page that is injected into the batch text as
`--- PRE-SCAN SKELETON ---`.

The 8B system prompt instructs the model to:
1. Verify pre-scan findings (correct errors)
2. Supplement with events regex cannot find
3. Not repeat pre-scan events verbatim — save tokens for the hard stuff

## Bugs Fixed

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| `add_events_from_pdf_page() got unexpected keyword argument 'events_data'` | Wrong kwarg name | Changed to `events=extracted` |
| Graph always showing 0 events/0 edges | `try` block for graph add was outside `if vision is not None` guard | Fixed indentation so graph add is inside the guard |
| "All connection attempts failed" on batch 742+ | New `httpx.AsyncClient` per batch → port exhaustion | Single persistent client with connection pooling + retry backoff |
| No feedback for minutes on large PDF upload | PDF extraction blocked before SSE generator started | Moved heavy work inside SSE generator; immediate `accepted` event |
| Server crash on concurrent inference | No GPU contention protection | `asyncio.Lock` + HTTP 409 with active job details |

## Constants (Tuned for 8B on RTX 4090)

| Constant | Value | Rationale |
|----------|-------|-----------|
| `_DEFAULT_MODEL` | `eoh-llama3.1:8b` | Production 8B model |
| `_DEFAULT_NUM_CTX` | 32,768 | 8B context window |
| `_OUTPUT_RESERVE_RATIO` | 0.50 | 50% of context reserved for output |
| `_OLLAMA_MAX_PAGES_PER_BATCH` | 10 | Balances cross-page context vs VRAM pressure |
| `_BATCH_MAX_INPUT_CHARS` | ~48,000 | Derived from context math |
| `_MAX_RETRIES` | 3 | Exponential backoff (2s, 4s, 8s) |
| `_MAX_UPLOAD_BYTES` | 500 MB | Large-record ceiling |

## Testing Performed

- Norman Roberts PDF (4,223 pages, 177 MB) — full run through endpoint
- Kaleb Forward JSON (34 events) — clean run via FORWARD endpoint
- Concurrent inference rejection (HTTP 409) — confirmed working
- Pre-scan output verified against known Kaiser encounter format

---

**This endpoint is the primary intake for all RISE and FORWARD patient timelines.**
