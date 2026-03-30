# RECEIPT: Graph Evidence as Primary Agent Context

**Date:** 2026-03-29
**Scope:** EoHD graph data → first-class, primary agent context with individual citations
**Status:** Complete — awaiting live run verification

---

## Problem Statement

Graph data from `PatientTimelineVision` (4668 events, 57672 edges) was loaded and available during EoHD runs, but was treated as an afterthought:

1. **Appended last** — graph context was a single blob injected at position 9 (behind case analogs, guidelines, EoH framework docs) in the fused context list
2. **Single generic citation** — all graph evidence cited as one entry `"graph_evidence"` instead of typed per-node citations
3. **Legacy timeline still loaded** — despite having a structured graph, each inner step re-loaded the raw 4223-event timeline from Postgres and emitted `timeline_events_loaded`, `timeline_signals_summary`, `timeline_flare_features` SSE walls
4. **LLM saw `kind=INTERNAL_MKG`** — graph docs were indistinguishable from guidelines in the LLM prompt

Evidence from the run output:
- `fused` matches showed `graph_evidence` as a single item at position 14 of 14
- Evidence map cited `"graph_evidence"` generically (not by event type)
- Each step emitted ~316 flare features and ~3413 signals from the legacy timeline

---

## Changes Made

### 1. `server/eoh/patient_timeline_chart.py` — New `build_graph_context_docs()`

**Added** a structured alternative to `build_graph_context()` that returns individual per-type context documents.

| Parameter | Old | New |
|---|---|---|
| `sem_k` | 10 | 15 |
| `ts_k` | 10 | 15 |
| Traversal seeds | top-3 merged | top-5 merged |
| Edge types | 5 | 7 (added `causal`, `symptom_cluster`) |
| Output | Single `(str, List[str])` | `List[Dict[str, Any]]` — one doc per event type |

Each returned doc contains:
- `id`: `graph:{event_type}` (e.g., `graph:diagnosis`, `graph:medication`)
- `source`: `patient_graph`
- `title`: `Patient Graph — Diagnoses`, etc.
- `text`: Timestamped event lines with drug annotations
- `meta.event_ids`: List of individual event IDs for enrichment
- `meta.event_count` / `meta.edge_count`: Structural metadata

Old function `build_graph_context()` preserved as fallback.

### 2. `server/api/rag_stream_detective.py` — Detective uses structured docs

- Replaced `build_graph_context` call with `build_graph_context_docs`
- Passes `graph_context_docs` to inner EoH stream as new parameter
- **`use_timeline=not graph_available`** — when graph is loaded, inner stream skips legacy timeline entirely

Before:
```
use_timeline=True,
graph_context=step_graph_context,
```

After:
```
use_timeline=not graph_available,
graph_context=step_graph_context,
graph_context_docs=step_graph_context_docs,
```

### 3. `server/api/rag_stream_eoh.py` — Graph docs injected at position 0

- New parameter: `graph_context_docs: Optional[List[Dict[str, Any]]]`
- Graph docs inserted at **position 0** of `final_ctx` (highest precedence in LLM prompt)
- Legacy blob fallback retained at position 0 if structured docs unavailable
- **System prompt (`EOH_ROUTED_ANSWER_SYSTEM_PROMPT`)** updated with explicit instructions:
  > "Patient Graph evidence (source: "patient_graph") is the PRIMARY clinical evidence source."

Context ordering (new):
```
[0..N] Patient Graph docs (graph:diagnosis, graph:medication, ...)
[N+1]  Patient state / diagnostic landscape
[N+2]  EoH router plan
[N+3]  Ethos module docs
[N+4]  Guidelines (ACR, EULAR, etc.)
[N+5]  Case analogs
```

### 4. `server/api/rag_stream_routes.py` — Citations & LLM formatting

**`_classify_citation_kind()`:**
- New kind: `"patient_graph"` for `src == "patient_graph"` or `method == "graph_probe"`

**`build_citations()`:**
- New case for `patient_graph` source: generates keys like `patient_graph:diagnosis`
- Citation sort order: `patient_graph` (0) → `valyu` (1) → `ethos` (2) → `timeline` (3) → `router` (4) → `guideline` (5)

**`format_context_for_llm()`:**
- New `PATIENT_GRAPH` kind label (was lumped into `INTERNAL_MKG`)
- LLM now sees `[1] kind=PATIENT_GRAPH patient_graph (patient_graph:diagnosis) | Patient Graph — Diagnoses | ...`

### 5. `server/api/stream_config.py` — Evidence mapping prompt

**`EVIDENCE_MAPPING_SYSTEM_PROMPT`** updated:
> "Patient Graph docs are FIRST-CLASS evidence. ALWAYS cite them by their specific type ID (e.g., 'graph:diagnosis', 'graph:medication') — never use a generic 'graph_evidence' ID."

---

## Expected Behavioral Differences (Next Run)

| Metric | Before | After |
|---|---|---|
| Graph docs in fused context | 1 blob at position 14 | 5-9 typed docs at positions 0-8 |
| Graph citation count | 1 (`graph_evidence`) | Up to 9 (`patient_graph:diagnosis`, `patient_graph:medication`, ...) |
| Citation sort position | Last | First |
| LLM context label | `kind=INTERNAL_MKG` | `kind=PATIENT_GRAPH` |
| Legacy timeline load per step | Yes (4223 events → signals/flare SSE) | **Skipped** when graph available |
| `timeline_flare_features` SSE per step | 316 items (truncated to 15) | **Not emitted** |
| `timeline_signals_summary` SSE per step | 3413 signals (truncated to 5) | **Not emitted** |
| Evidence map `supporting_evidence_ids` | Generic `graph_evidence` | Typed: `graph:diagnosis`, `graph:lab`, etc. |

---

## Files Modified

| File | Lines Changed | Nature |
|---|---|---|
| `server/eoh/patient_timeline_chart.py` | +100 | New `build_graph_context_docs()` |
| `server/api/rag_stream_detective.py` | ~25 | Use structured docs, skip legacy timeline |
| `server/api/rag_stream_eoh.py` | ~20 | New param, position-0 injection, system prompt |
| `server/api/rag_stream_routes.py` | ~25 | Citation kind, key gen, sort order, LLM label |
| `server/api/stream_config.py` | ~5 | Evidence mapping prompt for graph docs |

All files pass `py_compile` syntax check.

---

## Verification Command

```bash
curl -N -X POST http://localhost:8000/api/rag/eoh_detective_stream \
  -H "Content-Type: application/json" \
  -d '{
    "patient_id": "NORMAN_ROBERTS",
    "question": "What are the most significant unresolved clinical issues and how have treatments evolved over time?",
    "max_steps": 6,
    "use_valyu": false
  }'
```

**What to look for:**
1. `fused` matches should show `graph:diagnosis`, `graph:medication`, etc. at the **top** of the list
2. `citations` should have `kind: "patient_graph"` entries appearing **first**
3. `evidence_map` claims should reference `graph:diagnosis`, `graph:medication` in `supporting_evidence_ids`
4. No `timeline_events_loaded`, `timeline_signals_summary`, or `timeline_flare_features` per step
5. LLM answer text should reference "graph evidence" and specific event types
