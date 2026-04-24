# STRATEGY: Integrating the Living Graph into EoHD
**Date**: 2026-03-28 (revised)  
**Scope**: `rag_stream_detective.py` + `PatientTimelineChart` + graph analysis tools  
**Prerequisite**: `STRATEGY_PATIENT_GRAPH_LIVING_SYSTEM_20260317.md`  
**Constraint**: Graph must be built and validated BEFORE EoHD runs. EoHD is a consumer of the graph, not a builder.

---

## 0. The Separation Principle

**EoHD is the premier source of immediate value.** It is what the doctor sees. It must never be blocked by graph construction, degraded by incomplete graphs, or slowed by embedding builds. The graph is infrastructure. EoHD is the product.

Therefore:

- **Graph construction** (PDF extraction, event typing, connascence inference, timestamp recovery, RxNorm normalization, PatientTimelineChart embedding) happens **offline, before EoHD is available for a patient**.
- **EoHD** loads a **pre-built, validated** PatientTimelineVision and PatientTimelineChart at startup. If neither exists for a patient, EoHD runs without graph retrieval (existing behavior, unchanged).
- **EoHD never builds a graph.** It reads one. It enriches one opportunistically during the run. It saves the enriched version after the run. But construction is someone else's job.

This is the same separation as code → git → IDE. You don't compile the repository inside the text editor. You compile it, then the editor reads the artifacts.

---

## 0.1 What Exists Today

The EoHD detective stream (`rag_stream_detective.py`) currently:

1. **Loads** `ehr.patient_timeline` events and builds a timeline snapshot with diagnostic landscape, key signals, and a canonical summary via `summarize_timeline_for_eoh` (line ~263).
2. **Loads or creates** a PatientTimelineVision graph (line ~478). If no graph exists, it creates an empty one — **this is the problem**. It should not create. It should either load a pre-built graph or proceed without one.
3. **Plans** a multi-step investigation from the timeline snapshot (line ~526).
4. **Executes** each step via `eoh_stream_event_generator` (TS/ANN retrieval against `rag_corpus`) (line ~577).
5. **Enriches opportunistically** after each step via `enrich_graph_opportunistic` (line ~756).
6. **Saves** the enriched graph after all steps (line ~815).

**What changes**: Step 2 stops creating empty graphs. Step 2 instead checks for a pre-built graph + chart and gates graph features on their existence. The `use_graph` flag is removed — if the graph exists and is healthy, use it; if not, don't.

---

## 1. The Graph Pipeline (Offline, Separate from EoHD)

### 1.1 When It Runs

The graph pipeline runs **before** a patient is available in EoHD. This is triggered by:

- **Patient onboarding**: When a new patient timeline PDF is uploaded, the pipeline runs automatically (or is queued).
- **Overnight batch**: For large PDFs (4,223 pages), the pipeline can run overnight on Ollama (local, free) or on GPT-4.1 (faster, paid). The choice depends on compute and server resources.
- **Manual trigger**: Operator runs `run_eohd_timeline_pdf.py` (already exists) followed by `normalize_medications_rxnorm.py` and chart build.

### 1.2 What It Produces

The pipeline outputs three artifacts per patient:

| Artifact | File | What | Required for EoHD? |
|---|---|---|---|
| **PatientTimelineVision** | `patient_timeline_vision_{patient_id}.json` | Typed events + connascence edges + annotations | Yes — the graph |
| **PatientTimelineChart** | `patient_timeline_chart_{patient_id}.jsonl` | Sentence-transformer embeddings over graph nodes | Yes — semantic search substrate |
| **PatientTimelineSnapshot** | `patient_timeline_snapshot_{patient_id}.json` | Lightweight shape summary (event counts, date ranges, gap analysis) | Yes — planner context |

### 1.3 Readiness Gate

A patient graph is **ready for EoHD** when:

```python
def is_graph_ready(patient_id: str) -> bool:
    vision = load_timeline_vision(patient_id)
    chart_path = get_chart_index_path(patient_id)
    
    if not vision or not vision.events:
        return False
    if not chart_path.exists():
        return False
    
    # Minimum quality thresholds
    ts_rate = sum(1 for e in vision.events.values() 
                  if parse_clinical_date(e.timestamp) is not None) / len(vision.events)
    if ts_rate < 0.80:
        return False
    if vision.count_edges() < len(vision.events):
        return False
    
    return True
```

If `is_graph_ready` returns False, EoHD runs in **legacy mode** (existing behavior, no graph retrieval). The doctor sees no degradation — they just don't get graph-powered evidence. When the graph completes construction, the next EoHD run picks it up automatically.

### 1.4 Pipeline Steps (in order)

```
1. PDF extraction       → PatientTimelineVision (events, basic edges)
   [run_eohd_timeline_pdf.py, Ollama or GPT-4.1]

2. Timestamp recovery   → timestamps filled from previews (44.9% → 99.6%)
   [extract_date_from_text on all 'unknown' events]

3. Connascence pass     → temporal, diagnostic, treatment, lab_trend edges
   [_infer_temporal_connascence + _infer_llm_connascence_batched]

4. RxNorm normalization → drug_name + rxcui annotations on medication nodes
   [normalize_medications_rxnorm.py]

5. Chart build          → PatientTimelineChart (local embeddings)
   [sentence-transformers/all-MiniLM-L6-v2, ~40s for 4,668 nodes]

6. Snapshot             → PatientTimelineSnapshot for planner context
   [vision.snapshot()]

7. Readiness validation → is_graph_ready() must return True
```

Steps 1-3 are the existing pipeline (`run_eohd_timeline_pdf.py`). Steps 4-7 are new post-processing. Total wall time: ~1 hour on Ollama (steps 1-3), ~2 minutes for steps 4-7.

---

## 2. EoHD Changes: Graph as Read-Only Input

### What EoHD Does at Startup (per-request)

```python
# Replace the current "load or create" block (line ~478) with:
detective_vision: Optional[PatientTimelineVision] = None
detective_chart: Optional[PatientTimelineChart] = None
graph_available = False

try:
    vision_path = get_vision_path(timeline_patient_id)
    chart_path = get_chart_index_path(timeline_patient_id)
    
    if vision_path.exists() and chart_path.exists():
        detective_vision = PatientTimelineVision.load(vision_path)
        detective_chart = PatientTimelineChart()
        detective_chart.load(chart_path)
        graph_available = is_graph_ready(timeline_patient_id)
        
        yield sse("status", {
            "status": "graph_loaded",
            "graph_events": len(detective_vision.events),
            "graph_edges": detective_vision.count_edges(),
            "graph_ready": graph_available,
        })
    else:
        yield sse("status", {
            "status": "graph_not_available",
            "detail": "No pre-built graph found. Running in legacy mode.",
        })
except Exception:
    logger.warning("Failed to load graph, running in legacy mode", exc_info=True)
```

**No creation. No building. No embedding. Load or skip.**

### Graph Probe per Step (when `graph_available`)

**Where**: Inside the step loop (~line 577), before `eoh_stream_event_generator` is called.  
**What**: For each step, if `graph_available` (i.e., graph was pre-built and loaded):

1. **Semantic search**: `detective_chart.search(step_q, top_k=10)` — instant, index already in memory.
2. **TS search**: `graph_ts_search(detective_vision, step_q, limit=10)` — text match against node previews.
3. **RRF merge**: Reciprocal rank fusion of semantic + TS results.
4. **Graph traversal**: From top 3 merged hits, BFS along diagnostic/treatment/lab_trend edges (depth=2).
5. **Compact to context string**: Format as `event_type | timestamp | preview`, one per line. Cap at ~2,000 chars (~500 tokens).

This context string is injected into `eoh_stream_event_generator` via a new `graph_context` parameter. It sits alongside the existing TS/ANN retrieval results from `rag_corpus`.

```python
# Per-step graph probe — read-only, never builds
if graph_available and detective_chart and detective_vision:
    sem_ids = [p["event_id"] for p, _ in detective_chart.search(step_q, top_k=10)]
    ts_ids = graph_ts_search(detective_vision, step_q, limit=10)
    merged = rrf(sem_ids, ts_ids)[:10]
    
    traversal_ids = set()
    for eid in merged[:3]:
        traversal_ids.update(graph_traverse(detective_vision, eid, depth=2))
    
    graph_evidence_lines = []
    for eid in merged + list(traversal_ids):
        ev = detective_vision.events.get(eid)
        if ev:
            graph_evidence_lines.append(
                f"{ev.event_type} | {ev.timestamp or '?'} | {ev.preview[:120]}"
            )
    
    graph_context = (
        f"--- GRAPH EVIDENCE ({len(graph_evidence_lines)} nodes) ---\n"
        + "\n".join(graph_evidence_lines[:30])
    )[:GRAPH_CONTEXT_MAX_CHARS]
```

**Zero build cost at query time.** The chart is pre-loaded. The graph is pre-loaded. The probe + traversal is ~5ms of numpy cosine + BFS. All construction happened offline.

**Context budget**: Existing `ctx_k=32` controls rag_corpus chunks. Graph context is additive but capped at ~500 tokens. Total context increase per step: <5%. This is well within limits.

### Graph Analysis Tools in Gap Phase (when `graph_available`)

**Where**: Inside the gap retrieval logic (currently in `timeline_summarizer.py` / `timeline_enrichment_gap_agent.py`).  
**What**: When `graph_available`, the gap agent can call pre-written graph analysis functions as tools:

| Tool | What It Returns | When Useful |
|---|---|---|
| `event_type_distribution` | Count by type | Always — helps agent understand what's in the graph |
| `edge_density_by_type` | Edge counts per event type per connascence type | Understanding which regions are well-connected |
| `temporal_gaps(min_days)` | Gaps > N days between events | Finding periods with missing data |
| `cluster_by_type_and_month(type)` | Monthly event counts for a type | Spotting treatment arcs, lab trends |
| `orphan_nodes` | Nodes with zero edges | Finding unconnected events that need enrichment |
| `medication_timeline` | Chronological medication events | Treatment arc visualization |
| `lab_trend(lab_name)` | Temporal series for a specific lab | Map-reduce search across all lab nodes |

**Implementation**: These are the same functions from `demo_living_graph.py` (already written), exposed as tools the gap agent can call. The gap agent's system prompt includes the tool signatures. The agent decides which tools to call based on the probe results.

**For map-reduce patterns** (e.g., "search all lab_trend edges for potassium"): The function iterates over lab nodes, filters by keyword, and returns a summary. This is a Python function operating on the in-memory graph — not an LLM call. Fast and free.

**For PNG generation**: The gap agent can call a `render_timeline_chart(vision, event_types, date_range)` function that uses matplotlib to generate a timeline visualization. The PNG is saved to the artifact directory and its path is included in the SSE stream. The React app already renders images from the stream. This is analogous to the simulation/math rendering you already do.

### Step Execution (UNCHANGED)

`eoh_stream_event_generator` runs exactly as before. The only difference: it may receive a `graph_context` string as additional context when `graph_available`. The router, module selection, TS/ANN retrieval, Valyu, and LLM generation all work as before. The graph evidence is additive context, not a replacement.

### Enrichment Collection (per-run, write-back at end)

**Existing**: `enrich_graph_opportunistic` runs after each step, extracting events from the step answer. This continues unchanged.

**Additional when `graph_available`**: Collect structured enrichment requests:

1. After each step's LLM answer, check if the answer mentions corrections (dates, drug names, dosages) for graph nodes that appeared in the graph evidence.
2. Accumulate these as `enrichment_queue: List[Dict]` throughout the run.
3. After all steps complete (before final report), apply the accumulated enrichments to the vision in batch.
4. Re-embed changed nodes in PatientTimelineChart.
5. Save the updated graph and chart index.

The graph that was loaded at the start of the run is better at the end. But even if step 3-5 fail, the run is not degraded — the existing enrichment path still operates. This is strictly additive.

### Final Report (MODIFIED when `graph_available`)

**Existing**: `detective_report_llm` generates a narrative report from step summaries.  
**Additional when `graph_available`**: The report payload includes:

- Graph shape (from pre-built snapshot, loaded at startup)
- Enrichment stats (corrections applied during this run)
- Unresolved enrichment targets (nodes still missing data after all steps)

The final report SSE also emits a `graph_enrichment_summary` event that the React app can render as a graph health indicator.

---

## 3. Where Things Live (Production vs. Tooling)

| Component | Tooling (now) | Production (target) | Migration |
|---|---|---|---|
| PatientTimelineChart index | JSONL file + numpy | `ehr.patient_chart` table + pgvector | Same as rag_corpus pattern |
| Graph (vision) | JSON file | `ehr.patient_timeline_vision` table (JSONB) or normalized events+edges tables | Schema migration |
| TS search on graph | In-memory `if term in preview` | `tsvector` index on the events table | One index, one query |
| Graph analysis tools | Python functions on in-memory graph | Same functions, loaded from DB into memory per-request | Load from DB instead of JSON file |
| Enrichment write-back | Mutate JSON + save file | `UPDATE` in Postgres | SQL instead of file I/O |
| **Readiness gate** | `is_graph_ready()` on file artifacts | Same function, checks DB tables | Query instead of file check |

The separation principle makes the tooling → production migration cleaner:

- **Graph pipeline** (offline): Already runs as standalone scripts. In production these become queued jobs (Celery, or a simple cron). The storage backend changes from JSON files to Postgres tables. The pipeline logic does not change.
- **EoHD** (online): Loads graph from file or DB. The `load_timeline_vision` call becomes a DB query. The `chart.load()` call becomes a pgvector fetch. Nothing else changes.

The HIPAA boundary is maintained because:
- Embeddings are computed locally (sentence-transformers on server, not sent to OpenAI)
- Graph construction happens offline — PHI never leaves the server during build
- Graph data stays in the server process / Postgres (same as existing patient data)
- LLM calls receive capped context strings (2,000 chars), not raw graph dumps

---

## 4. Context Budget

Current EoHD context budget per step (approximate):

| Source | Tokens | Notes |
|---|---|---|
| System prompt | ~800 | Router + module prompts |
| Patient state | ~500 | Compact diagnostic landscape |
| Timeline summary | ~2,000 | Canonical summary from summarizer |
| RAG corpus chunks | ~4,000 | `ctx_k=32` chunks, truncated |
| Valyu research | ~1,500 | When enabled |
| **Total** | **~8,800** | Well within 128K context window |

When `graph_available`, add:

| Source | Tokens | Notes |
|---|---|---|
| Graph shape (planner only) | ~200 | Snapshot metadata, not per-step |
| Graph evidence per step | ~500 | 30 nodes, one line each, capped at 2,000 chars |
| Graph analysis (gap only) | ~300 | Tool results, once per run |
| **Added** | **~500/step** | ~6% increase over baseline |

This is negligible. The graph evidence is the highest-signal retrieval in the system (typed, timestamped, connected by clinical edges) at the lowest token cost (one line per node vs. multi-paragraph PDF chunks).

---

## 5. File Changes

### Graph Pipeline (offline — separate from EoHD)

| File | Change | Risk |
|---|---|---|
| `scripts/build_patient_graph.py` | **NEW** — Orchestrator that runs the full pipeline: extract → timestamp recovery → connascence → RxNorm → chart build → snapshot → readiness validation. Single entry point. | Zero — new file |
| `eoh/patient_timeline_chart.py` | **NEW** — PatientTimelineChart class extracted from demo scripts | Zero — new file |
| `eoh/graph_analysis_tools.py` | **NEW** — graph analysis functions extracted from demo scripts | Zero — new file |
| `utils/parse_date.py` | Already done — `extract_date_from_text` used in timestamp recovery | None |
| `scripts/normalize_medications_rxnorm.py` | Already done — called by pipeline orchestrator | None |

### EoHD (online — consumer of pre-built graph)

| File | Change | Risk |
|---|---|---|
| `rag_stream_detective.py` | Replace "load or create" graph block with "load or skip". Add graph probe per step (guarded by `graph_available`). Modify enrichment collection. Modify final report payload. | Medium — but all behind `if graph_available` guard, and `graph_available` is False if artifacts don't exist |
| `rag_stream_eoh.py` | Add `graph_context: Optional[str]` parameter to `eoh_stream_event_generator`, inject into context curation | Low — additive context, behind null check |
| `eoh/graph_enrichment.py` | Add `apply_enrichment_batch` function for end-of-run batch enrichment + re-embed | Low — additive |
| `rag_stream_models.py` | No `use_graph` flag needed. Graph availability is detected automatically from artifacts. | Zero |

**Note**: `use_graph` as an explicit flag is **removed**. The presence of pre-built artifacts is the signal. This eliminates an entire class of bugs where someone sets `use_graph=1` on a patient with no graph. If the graph exists and passes readiness, it's used. If not, legacy mode. No knobs.

---

## 6. Execution Order

### Phase A: Graph Pipeline (offline, does not touch EoHD)

1. Extract `PatientTimelineChart` from `demo_living_graph.py` into `server/eoh/patient_timeline_chart.py`
2. Extract graph analysis tools into `server/eoh/graph_analysis_tools.py`
3. Write `scripts/build_patient_graph.py` — the pipeline orchestrator
4. Run pipeline on Nate's dad: `python scripts/build_patient_graph.py ../artifacts/...vision.json`
5. Verify: `is_graph_ready()` returns True, snapshot.json is populated

**Test**: Pipeline produces three artifacts. Readiness gate passes. EoHD is not touched.

### Phase B: EoHD Graph Loading (replaces creation with load-or-skip)

6. Replace "load or create" block in `rag_stream_detective.py` with load-or-skip
7. Add `graph_available` boolean that gates all graph features
8. Add graph snapshot to planner context (when available)

**Test**: Run EoHD on a patient WITH pre-built graph — status SSE says "graph_loaded". Run on a patient WITHOUT — status SSE says "graph_not_available". Both produce correct reports. No regressions.

### Phase C: Graph Probe per Step (adds graph retrieval)

9. Add graph probe per step (semantic + TS + traversal → compact context string)
10. Inject `graph_context` into `eoh_stream_event_generator` context curation

**Test**: Run EoHD on Nate's dad. Compare step answers with and without graph artifacts present. Graph evidence should improve answer quality for temporal/causal questions.

### Phase D: Graph Analysis Tools (adds tool use)

11. Add graph analysis tool dispatcher (gap agent calls tools by name)
12. Add `render_timeline_chart` for PNG generation
13. Expose tool results in gap agent context

**Test**: Gap agent calls `temporal_gaps` and `medication_timeline` when investigating treatment arcs. PNG appears in SSE stream.

### Phase E: Enrichment Write-Back (closes the loop)

14. Add `enrichment_queue` accumulation during step execution
15. Add batch enrichment application after all steps
16. Re-embed changed nodes in PatientTimelineChart
17. Emit `graph_enrichment_summary` SSE event

**Test**: Run EoHD twice on the same patient. Second run starts with a better graph (more edges, better timestamps, richer medication annotations). Verify by comparing graph snapshots before and after.

---

## 7. The Agent's View

When graph artifacts exist, each detective step's agent sees:

```
[System prompt + module context]

[Patient state: diagnostic landscape, key signals]

[Timeline summary: canonical narrative from summarizer]

[RAG corpus: 32 PDF chunks matching this step's question]

[GRAPH EVIDENCE: 30 typed, timestamped nodes from semantic search + 
 traversal along diagnostic/treatment/lab_trend edges]

[Valyu research: external literature results]
```

The graph evidence is the densest, most structured context in the window. A single graph node like `medication | 2017-07-12 | Neurology follow-up: 69 yo man with MG, not robust response to prednisone, mestinon` tells the agent more in one line than a 500-token PDF chunk that includes headers, footers, and fax cover sheets.

The agent doesn't need to know it's querying a graph. It just sees better evidence. The graph traversal did the work of connecting a diagnosis to a medication to a lab — the agent sees the connection already made, not a pile of unrelated chunks.

When graph artifacts do NOT exist, the agent sees exactly what it sees today. No degradation. No missing data. The graph is additive.

---

## 8. Map-Reduce and Simulation

For patterns like "search all lab_trends for potassium across the full timeline":

1. The gap agent calls `tool_lab_trend("potassium")` — a Python function that filters lab nodes by keyword, sorts chronologically, and returns `[(date, value, event_id), ...]`.
2. This is a map-reduce over the graph: map = filter by type + keyword, reduce = sort + extract values.
3. The result is a compact time series that the agent can reason about ("potassium has been trending down since 2022") without reading hundreds of lab PDF pages.

For simulation and visualization:
1. The gap agent calls `render_timeline_chart(vision, event_types=["medication", "lab"], date_range=["2017-01-01", "2025-01-01"])`.
2. The function generates a matplotlib timeline plot showing medication starts/stops and lab values over time.
3. The PNG is saved and its path emitted as an SSE event.
4. The React app renders it inline — this is already supported for other image types in the stream.

EoH modules that do math and simulation (already in the codebase) can be exposed as additional tools. The gap agent calls them by name, receives structured results, and includes them in the report context. The module system doesn't change — the tools are a thin wrapper that calls existing module functions with graph-derived inputs.

---

## 9. The Timeline Summarizer's Role

`TimelineSummarizer` is the pipeline. It acts separately and before EoHD. The relationship:

```
TimelineSummarizer (offline)          EoHD (online)
─────────────────────────             ──────────────
PDF → events → edges                  Load pre-built graph
→ timestamp recovery                  Load pre-built chart
→ RxNorm normalization                Probe per step
→ chart build                         Traverse per step
→ snapshot                            Enrich opportunistically
→ readiness gate ✓                    Save enriched graph
                                      ↓
                    "Graph available"  Doctor sees answer
```

For large PDFs (4,223 pages), the summarizer may require an overnight Ollama run. This is acceptable — the patient is onboarded once. Every subsequent EoHD query benefits from the pre-built graph indefinitely.

For patients where the pipeline hasn't completed (new upload, compute queue, failed validation): EoHD runs in legacy mode. The doctor still gets a full detective report from PDF chunk retrieval. The graph is a bonus, not a prerequisite for the detective to function. But it IS a prerequisite for graph-powered evidence.

---

## 10. What This Means

When a doctor queries EoHD for a patient with a pre-built graph:

1. The system loads a 4,668-node, 57,672-edge clinical knowledge graph with 99.6% timestamp coverage. **Instant** — no build step.
2. The planner sees the graph shape (event type distribution, temporal gaps, edge density) and plans accordingly.
3. Each investigation step gets graph evidence: the 30 most relevant nodes from semantic search + edge traversal, in addition to the existing PDF chunk retrieval.
4. The gap phase can call graph analysis tools: temporal gap detection, medication timeline, lab trends, orphan identification.
5. Each step's answer enriches the graph (existing behavior, unchanged).
6. At run end, accumulated enrichments are applied in batch, changed nodes are re-embedded, and the graph is saved.
7. The next run on the same patient starts with a better graph.

When a doctor queries EoHD for a patient WITHOUT a pre-built graph:

1. The system detects no graph artifacts. Logs "graph_not_available" to SSE status.
2. Everything else runs exactly as it does today. PDF chunk retrieval, TS/ANN, modules, Valyu — all untouched.
3. The doctor sees no degradation.

The graph is infrastructure that makes EoHD better when present. Its absence never makes EoHD worse. Its construction never blocks or slows a query. This is the separation principle in practice.
