# PatientTimelineVision: Architecture, Semantic Queryability, and Ollama Strategy

**Date:** 2026-03-01  
**Audience:** Claude Opus (and any engineer picking this up)  
**Scope:** How the graph is loaded and enriched; downstream EoHD consumers; how to make it semantically queryable via local embeddings (mirroring `RepoChart`); agent query strategies; Ollama cost reduction path.

---

## 1. The Two-Layer Architecture

There are two separate Python implementations that both use the name "PatientTimelineVision." They serve different purposes and must not be confused.

### Layer A — In-memory session graph (`server/eoh/patient_timeline_vision.py`)

This is the workhorse used during PDF import and EoHD execution. It is a lightweight pure-Python dataclass graph that lives in RAM for the duration of a session. Session-only runs never write to the database.

**`TimelineEventVision`** — one node per clinical event:

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | `str` | Stable key: `dx_001`, `pdf_p0042_e002`, etc. |
| `event_type` | `str` | `diagnosis`, `lab`, `medication`, `procedure`, `symptom`, `visit`, `imaging`, `note`, `flare`, `page` |
| `timestamp` | `str` | ISO date string or `"unknown"` |
| `preview` | `str` | 1–2 sentence human summary (max ~200 chars from extractor) |
| `discovered_by` | `List[str]` | Provenance chain: `pdf_page_42`, `snapshot`, `llm_connascence`, etc. |
| `status` | `str` | `included` \| `excluded` \| `uncertain` |
| `connascence` | `Dict[str, List[str]]` | Edge map: `{"temporal": ["lab_001"], "diagnostic": ["dx_003"]}` |
| `annotations` | `Dict[str, Any]` | Freeform bag: `{"pdf_page": 42, "batch": 1}` |

**`PatientTimelineVision`** — the graph container:

| Field | Type | Description |
|-------|------|-------------|
| `patient_id` | `str` | Stable patient identifier |
| `built_at` | `str` | ISO timestamp of graph construction |
| `session_only` | `bool` | `True` = no DB writes |
| `events` | `Dict[str, TimelineEventVision]` | All nodes keyed by `event_id` |
| `metadata` | `Dict[str, Any]` | PDF provenance, page counts, etc. |

Key methods: `add_event()`, `add_connascence_link(from, to, kind)`, `add_edge()` (bidirectional + provenance), `count_edges()`, `get_events_by_type(type)`, `get_connascent_events(event_id, kind=None)`, `iter_connascence_edges(limit)`, `save(path, force=True)`, `load(path)`.

Persistence is **JSON** (not JSONL despite the default path ending in `.jsonl`). Default path: `ai_coder_output/patient_timeline/{patient_id}_timeline_vision.jsonl`.

### Layer B — DB-backed typed schema (`server/ptv/models.py`)

A richer schema with enums for DB persistence. Not currently wired into the PDF pipeline but represents the target for production.

**`NodeType`:** `EVENT`, `MEASUREMENT`, `MEDICATION_CHANGE`, `RISK_SIGNAL`, `NOTE`, `DECISION`, `DERIVED_INSIGHT`

**`RelationshipType`:** `TEMPORAL_SEQUENCE`, `TEMPORAL_WINDOW`, `CAUSAL_LIKELY`, `CAUSAL_POSSIBLE`, `CAUSAL_PREVENTS`, `REFERENCES`, `MODIFIES`, `SUPERSEDES`, `DERIVED_FROM`, `COMPOSITE`, `CORRELATES_WITH`, `SIMILARITY`, `CONTRADICTS`, `CARE_PLAN_LINK`

**`PatientEventNode`** adds fields absent from Layer A: `version`, `node_type`, `source_type`, `source_system`, `structured` (typed values), `text` (full text), **`embedding_id`** (foreign key to vector store), `parent_event_id`, `superseded_by_event_id`, `strength`, `confidence`.

**Gap:** Layer A has no `embedding_id` field. The semantic queryability work below bridges this.

---

## 2. Loading and Enrichment Pipeline

### 2a. PDF ingestion (`summarize_timeline_from_pdf`)

```
PDF file
  │
  ├─ PdfReader: extract text from all N pages → (page_num, text) list
  │                                                       ↓
  ├─ seed_from_structured_probe_snapshot() → empty PatientTimelineVision
  │
  ├─ _select_pages_lite() or all pages               [extraction_mode]
  │     head=200, tail=200, mc_middle=400 → ~800 pages
  │
  ├─ _iter_pdf_event_extraction_batches() → batches of ~183 pages
  │     fill_ratio=0.10 of 1M-token context → ~179 output tokens/page
  │
  ├─ _extract_events_from_pages_batch() [LLM call per batch, ~4–5 lite / ~23 full]
  │     system: per-page JSON extraction with typed event_type
  │     response: {pages: [{page_num, events: [{event_type, timestamp, preview}]}]}
  │
  ├─ add_events_from_pdf_page() → ingest into vision
  │     + _infer_temporal_connascence(window_days=7) after each page [seed helper]
  │
  ├─ _reclassify_event_types()  ← keyword pass: upgrades "page"/"note"/"unknown"
  │     patterns: lab, diagnosis, medication, procedure, symptom, visit, imaging
  │
  ├─ vision.save(vision_path, force=True)  → JSON snapshot
  │
  └─ _run_timeline_enrichment_gap_synthesis_connascence()
        │
        ├─ [pool=None: skip gap+synthesis entirely, go straight to connascence]
        │
        ├─ analyze_timeline_enrichment_gaps()   [LLM — DB mode only]
        │     compact vision → gap JSON → ts_terms, event_id queries
        │
        ├─ _search_timeline_ts_for_terms()     [DB full-text — DB mode only]
        │
        ├─ synthesize_timeline_enrichment()    [LLM — DB mode only]
        │     gap_results → new edges + metadata_updates → applied to vision
        │
        └─ _enrich_timeline_vision_connascence()   [ALWAYS runs]
              ├─ RULE 1 – Temporal (mechanical)
              │     short window ≤30 days all types, bidirectional
              │     episode window 31–90 days cross-type only
              ├─ RULE 4 – Treatment (mechanical)
              │     med_types → lab/symptom/note/imaging within 60 days
              ├─ LLM diagnostic batch
              │     events with type in {diagnosis, procedure, symptom, flare}
              │     batches of 300, type-stratified, chronological
              └─ LLM lab_trend batch
                    events with type = "lab"
                    batches of 300, chronological
```

After enrichment the vision is resaved. Then `summarize_timeline_for_eoh()` runs the 9-chunk hierarchical summarization with `_compact_graph_for_reduce()` injecting the graph into the final reduce call.

### 2b. DB-backed detective run (`rag_stream_detective.py`)

In production (pool available), the vision is loaded from disk or constructed from the DB snapshot, then passed through the same gap/synthesis/connascence pipeline after each RAG probe round. The graph accumulates edges incrementally across the entire EoHD session.

---

## 3. EoHD Downstream Consumers

| File | Role |
|------|------|
| `server/eoh/timeline_summarizer.py` | Owns the full pipeline: PDF import, enrichment, hierarchical summarization, graph-guided reduce |
| `server/eoh/graph_enrichment.py` | `enrich_graph_from_batch()`, `enrich_graph_opportunistic()` — LLM merges structured events/edges into vision during probe steps |
| `server/eoh/timeline_enrichment_gap_agent.py` | `analyze_timeline_enrichment_gaps()` — LLM identifies missing connections, returns ts_terms + event_id queries |
| `server/eoh/timeline_enrichment_synthesis_agent.py` | `synthesize_timeline_enrichment()` — takes gap retrieval results, proposes new edges and metadata updates |
| `server/api/rag_stream_detective.py` | Loads/creates vision for detective runs; calls enrichment after each RAG round |
| `server/api/rag_stream_shared.py` | Shared type imports and vision handling helpers |
| `server/timeline/ingest.py` | Can construct/persist vision during DB ingest |
| `server/ptv/builder.py` | DB-oriented vision builder (Layer B) |
| EoHD modules (`modules/*.py`) | Currently **no direct vision consumption** — gap for future phase-stratified graph queries |

---

## 4. PatientTimelineVision vs RepoVision

| Dimension | `PatientTimelineVision` (eoh layer) | `RepoVision` (ai_coder layer) |
|-----------|--------------------------------------|-------------------------------|
| Node key | `event_id` (clinical event) | file path |
| Node payload | `event_type`, `timestamp`, `preview` | `summary`, `topics`, `relevance`, `key_functions`, `interacts_with`, `importance` |
| Edge model | Named connascence types on source node: `{"temporal": ["lab_001"]}` | Implicit: `annotations.imports`, `annotations.references` |
| Edge richness | Type-tagged but no `strength`/`confidence` in Layer A | No typed strength either; traversal via `neighbors()` |
| Temporal axis | First-class (`timestamp`) | None (git `last_commit` is a proxy) |
| Embedding | **Not present in Layer A** | `embed_node_payload()` produces text payload; no stored vector yet |
| Vector index | Not built | `RepoChart` (JSONL, `all-MiniLM-L6-v2`, cosine via numpy) |
| Persistence | JSON (one big dict) | JSON (`repo_vision.json`) |
| Session vs DB | Session-only flag | Always on-disk; no DB |
| LLM enrichment | Gap agent + synthesis agent + connascence rules | `enrich_files_semantically()` via chat |

**Key structural insight:** `RepoChart` (`portal_vision/graph/repo_chart.py`) is the exact pattern to mirror. It already implements everything needed:
- `sentence-transformers/all-MiniLM-L6-v2` (384 dims, free, local, no API key)
- `build_index()` → batch encode → JSONL with `_meta` header
- `search(query)` → encode + numpy cosine → top-k
- `get_near(file_path)` → nearest neighbors to existing node
- `_text_to_embed(path, summary, topics)` → text construction

The only work needed is a `TimelineChart` equivalent that adapts the text construction for clinical events.

---

## 5. Making PatientTimelineVision Semantically Queryable

### 5a. TimelineChart design (`server/eoh/timeline_chart.py`)

Mirror `RepoChart` exactly. The critical adaptation is the embedding text construction:

```python
def _text_to_embed_event(event: TimelineEventVision) -> str:
    """Build embedding input for a clinical event node."""
    conn_types = ", ".join(event.connascence.keys()) if event.connascence else "none"
    return (
        f"[{event.event_type}] {event.timestamp}\n"
        f"{event.preview}\n"
        f"Connascence: {conn_types}"
    )
```

This encodes type, time, clinical text, and graph neighbourhood signal into a single embedding. A richer variant can include neighbour previews (graph-aware embedding, like `embed_node_payload`).

**`TimelineChartPoint`** fields:
- `point_id` — sha256 of `event_id`
- `event_id` — back-reference to the graph node
- `patient_id` — for multi-patient indexes
- `event_type` — for post-filter
- `timestamp` — for temporal range filter
- `embedding` — `List[float]` (384 dims)
- `preview` — for display
- `connascence_types` — `List[str]` for graph-guided re-ranking
- `created_at` — index build time
- `is_navigation_only` — always `True`

**`TimelineChart`** methods:
- `build_index(vision, output_path)` — encode all events, write JSONL
- `load_index(path)` — deserialize, build numpy matrix
- `search(query, top_k, filter_type=None)` — semantic search with optional event_type filter
- `get_near(event_id, top_k)` — nearest neighbours to an existing node
- `get_connascent_cluster(event_id, kind)` — resolve graph edges to points for a given connascence type

**Storage:** One JSONL file per patient per session: `timeline_chart_{patient_id}_{timestamp}.jsonl`, alongside the vision JSON in the artifact directory.

### 5b. Incremental update

When new events are added (via EoHD probe enrichment), call `update_events(vision, changed_event_ids)`:
- Re-encode only the changed nodes
- Patch the JSONL (rewrite affected lines) and rebuild the numpy matrix
- No full rebuild needed for small deltas

### 5c. Model choice

| Model | Dims | Size | Speed | Notes |
|-------|------|------|-------|-------|
| `all-MiniLM-L6-v2` | 384 | 80MB | Very fast | Already used in `RepoChart`; good for short medical text |
| `all-mpnet-base-v2` | 768 | 420MB | Moderate | Better quality for longer previews |
| `nomic-embed-text` via Ollama | 768 | pull once | Fast via HTTP | No Python dep; same Ollama infra as LLM calls |
| `mxbai-embed-large` via Ollama | 1024 | pull once | Moderate | State of the art local, good medical text |

**Recommendation:** Start with `all-MiniLM-L6-v2` (same as `RepoChart`) to keep zero new dependencies. Upgrade to `nomic-embed-text` via Ollama once Ollama is wired in.

---

## 6. Agent Query Strategies

Three orthogonal traversal modes. Agents should compose them.

### Mode 1: Connascence traversal (graph walk)

Best for: "What events are causally related to this diagnosis?" "What lab trends followed this medication?"

```python
# Get all events diagnostically connected to dx_lupus_001
connected = vision.get_connascent_events("dx_lupus_001", kind="diagnostic")
# Then walk one hop further
for ev_id in connected:
    second_hop = vision.get_connascent_events(ev_id, kind="lab_trend")
```

Agent patterns:
- **Focal expansion:** start from a seed event (e.g. a diagnosis), walk connascence edges 1–2 hops
- **Connascence type filter:** restrict to `temporal` for chronology, `diagnostic` for clinical arc, `treatment` for response tracking, `lab_trend` for biomarker progression
- **Subgraph extraction:** collect all nodes reachable from a seed within N hops + a connascence type mask → pass as compact JSON to the LLM

### Mode 2: Node type filter

Best for: "Show me all medications" "Give me the lab arc" "What flares occurred?"

```python
labs = vision.get_events_by_type("lab")
meds = vision.get_events_by_type("medication")
diagnoses = vision.get_events_by_type("diagnosis")
```

Agent patterns:
- **Type-stratified summarization** (Phase 2 from `STRATEGY_GRAPH_GUIDED_SUMMARIZATION`): run one focused LLM call per node type, then synthesize
- **Cross-type join:** medications × labs within 60 days = treatment response candidates (already implemented as RULE 4)
- **Temporal slice:** filter by `timestamp` range, then by type → "all diagnoses in 2019"

### Mode 3: Vector semantic search (TimelineChart)

Best for: "What events are similar to this complaint?" "Find events related to kidney function" "What happened around the time of this hospitalization?"

```python
chart = TimelineChart(vision_path)
chart.load_index()

# Free-text query
results = chart.search("renal function creatinine worsening", top_k=10)

# Find events semantically similar to a known event
similar = chart.get_near("lab_creatinine_2021_03", top_k=5)

# Type-filtered semantic search
results = chart.search("infection fever", top_k=10, filter_type="diagnosis")
```

Agent patterns:
- **Query-driven retrieval:** patient asks "what was happening when my kidneys got worse?" → embed query → top-k events → pass to LLM with connascence context
- **Similarity clustering:** identify events with cosine sim > 0.85 → propose `symptom_cluster` connascence edges (Phase 2 rubric)
- **Hybrid re-ranking:** vector top-20 → filter by connascence relevance to a seed node → return top-5

### Mode 4: Composed multi-modal (recommended for EoHD agents)

```
Patient question: "Why did my doctor start methotrexate in 2019?"
  │
  ├─ 1. Type filter: get all "medication" events with "methotrexate" in preview
  ├─ 2. Vector search: embed question → top-10 semantically related events
  ├─ 3. Connascence walk: for each candidate med event → get "diagnostic" + "temporal" neighbours
  └─ 4. Assemble subgraph → pass to LLM with "answer using graph provenance" instruction
```

This is the Phase 3 "connascence-guided diagnostic chains" from the strategy report, now fully specified.

---

## 7. Patient Self-Query Interface

Future path for letting patients query their own timeline ("when was my last kidney function test?" "what happened after my lupus diagnosis?").

**Storage:** After PDF import, persist `TimelineChart` JSONL alongside the vision JSON in the artifact directory. Patient session loads both.

**Query handler sketch:**

```python
async def patient_timeline_query(
    question: str,
    vision: PatientTimelineVision,
    chart: TimelineChart,
    client: AsyncOpenAI,
) -> str:
    # 1. Vector retrieval
    hits = chart.search(question, top_k=15)
    
    # 2. Connascence expansion on top hits
    event_ids = [h[0].event_id for h in hits[:5]]
    expanded = set(event_ids)
    for eid in event_ids:
        for kind in ("diagnostic", "temporal", "treatment"):
            expanded.update(vision.get_connascent_events(eid, kind=kind))
    
    # 3. Build context
    context_events = [
        vision.events[eid] for eid in expanded if eid in vision.events
    ]
    context_events.sort(key=lambda e: e.timestamp)
    
    # 4. LLM answer
    return await _llm_answer_from_events(question, context_events, client)
```

This can be exposed as a lightweight HTTP endpoint or a CLI flag (`--query "..."` on `run_eohd_timeline_pdf.py`).

---

## 8. Ollama Strategy — Cost Reduction

### Where the money goes today

| Step | Model | Calls (lite mode) | Approx cost |
|------|-------|-------------------|-------------|
| PDF event extraction | `gpt-4.1` | ~4–5 | High (2M+ input chars) |
| Connascence LLM (diagnostic + lab) | `gpt-4.1` | 1–5 | Medium |
| Gap agent | `gpt-4.1` | 1 (DB mode) | Medium |
| Synthesis agent | `gpt-4.1` | 1 (DB mode) | Medium |
| Hierarchical summarization (map) | `gpt-4.1` | 9 | High |
| Reduce | `gpt-4.1` | 1 | Medium |
| Embeddings | `text-embedding-3-small` | N queries | Low |

### Ollama replacement targets

The Ollama API is OpenAI-compatible. `AsyncOpenAI(base_url="http://localhost:11434/v1", api_key="ollama")` is a drop-in for most calls. No code restructuring needed beyond passing a different client.

**Tier A — Use Ollama for ingestion/enrichment, keep OpenAI for final summary:**

| Step | Replace with | Rationale |
|------|-------------|-----------|
| PDF event extraction | `llama3.1:8b` or `mistral-nemo` | Structured JSON extraction; no reasoning needed; local speed is fine |
| Connascence LLM | `llama3.1:8b` | Pattern matching against rubric; small context |
| Gap agent | `llama3.1:8b` | Generates query terms; doesn't need frontier reasoning |
| Synthesis agent | `llama3.3:70b` or keep gpt-4.1 | Needs stronger reasoning; 70b local is viable |
| Hierarchical map chunks | `llama3.1:8b` or `mistral-nemo` | Per-chunk summarization; parallelizable |
| Final reduce | `gpt-4.1` (keep) | This is the money shot; quality matters |
| Embeddings | `nomic-embed-text` via Ollama | Free, 768 dims, pulls once, HTTP-compatible |

**Tier B — Full local (development / offline):**
All steps → Ollama. Use `llama3.3:70b` for synthesis and reduce if quality is acceptable, `llama3.1:8b` for extraction and connascence.

### Implementation path

1. **Add `ollama_client()` factory to `llm_client.py`:**
   ```python
   def get_ollama_client(base_url: str = "http://localhost:11434/v1") -> AsyncOpenAI:
       return AsyncOpenAI(base_url=base_url, api_key="ollama")
   ```

2. **Add `--llm-backend {openai,ollama}` flag to `run_eohd_timeline_pdf.py`** (or env var `LLM_BACKEND`). Pass the appropriate client to the pipeline.

3. **Add `--embed-backend {openai,local,ollama}` flag.** `local` = sentence-transformers; `ollama` = `nomic-embed-text` via HTTP.

4. **Decouple ingestion client from summarization client** in `summarize_timeline_from_pdf`:
   ```python
   async def summarize_timeline_from_pdf(
       ...,
       ingestion_client: AsyncOpenAI = None,   # Ollama for extraction
       summary_client: AsyncOpenAI = None,     # OpenAI for final reduce
   )
   ```
   Defaults to the same client (current behaviour). When both are passed, uses `ingestion_client` for event extraction + connascence, `summary_client` for summarization.

5. **Model config via env vars** (already partially done via `EOH_TIMELINE_SUMMARIZER_MODEL`):
   - `INGESTION_MODEL` (default: `gpt-4.1`)
   - `CONNASCENCE_MODEL` (default: same as ingestion)
   - `SUMMARY_MAP_MODEL` (default: same)
   - `SUMMARY_REDUCE_MODEL` (default: `gpt-4.1` always)
   - `EMBED_MODEL_LOCAL` (default: `sentence-transformers/all-MiniLM-L6-v2`)

### Estimated savings

For a 4,223-page record in lite mode with Ollama ingestion:
- Event extraction (4–5 calls, ~2M input chars) → **$0** (local)
- Connascence LLM (1–5 calls) → **$0** (local)
- Map summarization (9 calls, ~700K chars each) → **$0** if using local model
- Final reduce (1 call, ~50K chars) → keep gpt-4.1 → minimal cost
- Embeddings → **$0** (nomic-embed-text local)

**Net: >90% cost reduction for ingestion-heavy workloads.**

---

## 9. Files to Read for Opus (Full Dependency Map)

### Core graph
- `server/eoh/patient_timeline_vision.py` — Layer A dataclasses, all graph methods
- `server/ptv/models.py` — Layer B typed schema with `embedding_id` and `RelationshipType` enum
- `server/ptv/builder.py` — DB-oriented builder
- `server/eoh/PATIENT_TIMELINE_CONNASCENCE_RUBRIC.md` — v0.2 rules

### Ingestion + enrichment
- `server/eoh/timeline_summarizer.py` — Entire pipeline (4,307 lines; key sections: `_extract_events_from_pages_batch`, `_reclassify_event_types`, `_select_pages_lite`, `_enrich_timeline_vision_connascence`, `_infer_llm_connascence_batched`, `_compact_graph_for_reduce`, `summarize_timeline_from_pdf`)
- `server/eoh/graph_enrichment.py` — `enrich_graph_from_batch`, `enrich_graph_opportunistic`
- `server/eoh/timeline_enrichment_gap_agent.py` — gap analysis LLM agent
- `server/eoh/timeline_enrichment_synthesis_agent.py` — synthesis LLM agent
- `server/scripts/run_eohd_timeline_pdf.py` — CLI entry point

### EoHD runtime
- `server/eoh/router.py` — EoHD HTTP routing
- `server/eoh/module_index.py` — module registry
- `server/eoh/modules/m17_diagnostic_landscape.py` — example module (no PTV yet)
- `server/api/rag_stream_detective.py` — detective run with incremental vision enrichment
- `server/api/rag_stream_shared.py` — shared vision helpers

### Embedding infrastructure (pattern to copy)
- `portal_vision/graph/repo_chart.py` — **THE template**: `RepoChart`, `RepoChartPoint`, `build_index`, `search`, `get_near`, `all-MiniLM-L6-v2`, JSONL persistence
- `server/api/embeddings.py` — existing OpenAI embedding helpers
- `server/timeline/embedding_cache.py` — pgvector query embedding cache

### Strategy docs
- `2ndOpinionMD-MVP/STRATEGY_GRAPH_GUIDED_SUMMARIZATION_20260327.md` — graph-guided summarization roadmap
- `2ndOpinionMD-MVP/REPORT_PATIENT_TIMELINE_VISION_INGESTION_ENRICHMENT_20260327.md` — enrichment pipeline notes

---

## 10. Immediate Next Steps (Priority Order)

1. **`server/eoh/timeline_chart.py`** — Create `TimelineChartPoint` and `TimelineChart` mirroring `repo_chart.py`. Text construction: `f"[{event_type}] {timestamp}\n{preview}\nConnascence: {conn_types}"`. Build index after vision save in `summarize_timeline_from_pdf`.

2. **Add `embedding_id` to `TimelineEventVision`** (Layer A) — optional field pointing to the chart point. Bridges Layer A and Layer B schemas.

3. **Add `search` + `query` route to EoHD** — thin HTTP endpoint calling the composed Mode 4 query (vector → connascence expansion → LLM answer).

4. **`get_ollama_client()` in `llm_client.py`** + `--llm-backend` CLI flag — unlock Ollama for extraction when card arrives; switch `INGESTION_MODEL` to `llama3.1:8b` first.

5. **Pull `nomic-embed-text` via Ollama** once Ollama is wired — replace `text-embedding-3-small` for `TimelineChart` index building.

6. **EoHD module integration** — pass vision to modules (e.g. `m17_diagnostic_landscape.py`) as a queryable substrate: `vision.get_events_by_type("diagnosis")` instead of raw text parsing.

---

*This report generated from live codebase inspection of `portal_vision/graph/repo_chart.py`, `server/eoh/patient_timeline_vision.py`, `server/ptv/models.py`, `server/eoh/timeline_summarizer.py`, `FullMetalPacket/ai_coder/repo_vision.py`, `FullMetalPacket/ai_probe/embed_incremental.py`, and supporting EoHD files.*
