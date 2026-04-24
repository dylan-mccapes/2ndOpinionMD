# PatientTimelineVision: Architecture Appension — Opinion on Best Steps Forward

**Date:** 2026-03-27  
**Appends:** `REPORT_PATIENT_TIMELINE_VISION_ARCHITECTURE_20260301.md`  
**Audience:** Dylan, and any engineer picking this up  
**Scope:** Honest assessment of current state, critical path for a 4,223-page record at clinical stakes

---

## 0. What This Appension Is — And What Changed

The original report was written from codebase inspection. This appension is written from codebase inspection *plus* tracing every call path end-to-end. The opinion is not diplomatic. The stakes are people's health.

**Critical context:** The previous graph work was a **proof of concept** — the graph was built opportunistically during EoHD detective runs, accumulated as a side artifact without influencing agent reasoning, for the purpose of having a graph at the end without breaking anything. The 16 edges / 4,226 events figure comes from this POC on a truncated run (API credits exhausted before completion).

**What's changed:** We are now doing a **full graph-based implementation**. The graph is no longer a passive artifact. It is the reasoning substrate. EoHD agents query through it, enrich it, and reason over its structure. This changes everything downstream.

The architecture inverts:

| | POC (previous) | Full implementation (now) |
|---|---|---|
| **Graph role** | Side artifact accumulated during EoHD | Primary reasoning substrate |
| **When built** | During detective run, opportunistically from step outputs | Before detective run, from PDF ingestion + multi-pass enrichment |
| **Agent query** | Agents ignore graph; use Postgres RAG (TS + ANN) only | Agents query graph alongside RAG; graph provides chain context |
| **Enrichment** | Opportunistic only (lightweight, from step answers) | Full pre-run enrichment + opportunistic during run |
| **Output** | Graph JSON persisted after run for future use | Graph drives summarization, visualization, simulation |

We are starting with EoHD.

---

## 1. Honest Assessment of Current State

### What works and carries forward

- **Event extraction from PDF** is functional on the Norman Roberts 4,223-page record. Lite mode (~800 pages) ran successfully before credits exhausted. The extraction logic, batching, and event schema are sound.
- **Mechanical connascence rules** (temporal ±30/90 days, treatment ±60 days) are correctly implemented. They have not been tested at full scale (truncated run), but the logic is right.
- **Opportunistic enrichment** (`enrich_graph_opportunistic`) — correct design for the *during-run* enrichment layer. Still needed in full implementation, but now enriching an already-substantial graph rather than building from scratch.
- **Phase 1 graph injection into reduce** (`_compact_graph_for_reduce`) — this carries forward as one of several graph-to-agent interfaces, no longer the only one.
- **Provenance on every node** (`discovered_by`) — load-bearing for trust. Correct.

### What the POC was never designed to handle (and what we now need)

**1. The graph must exist before the detective run starts.**

In the POC, the graph accumulated during the run. In the full implementation, the detective needs a rich graph *before step 1*. This means:

- PDF → full extraction → full multi-pass connascence → indexed graph → *then* detective run starts.
- The graph is the detective's primary knowledge structure. It tells the planner where the diagnostic arcs are, where the gaps are, where the chains break. The planner can't do this if the graph doesn't exist yet.

This is the fundamental architectural change. The ingestion + enrichment pipeline is no longer a background task. It is the prerequisite for EoHD.

**2. Agents must query the graph during reasoning.**

In the POC, agents retrieved evidence via Postgres RAG (TS + ANN against `ehr.patient_timeline`). The graph was invisible to step-by-step reasoning. In the full implementation, every agent step should:

1. Query the graph (semantic search + connascence traversal) to find relevant events and diagnostic chains
2. Query Postgres RAG for source evidence (TS + ANN — this still has value as a raw-text fallback)
3. Merge graph-structured results with RAG results
4. Reason over the combined evidence, with graph chains providing the structural context that RAG alone cannot

This is not "add a parallel call." This is "the graph is the primary retrieval path; RAG is the evidence backing."

**3. Edge density is untested at full scale.**

The 16-edge figure is from the POC's truncated run — not diagnostic. The first full run with complete extraction and all connascence passes is the milestone that tells us whether the pipeline produces a useful graph. This run hasn't happened because API credits ran out. Ollama for extraction unblocks it regardless of payment status.

**4. Timeline TS search is ILIKE — the only data source without proper FTS.**

Every other data source in the system gets real text search. The MakefileBook (`mk/`) shows the pattern: `to_tsvector('english', ...)` + GIN index on `rag_corpus.ts` for guidelines, NICE, CHV, PanelApp, MIMIC, GWAS. Ontology tables get `gin_trgm_ops` trigram indexes (SNOMED, HPO, Orphanet, NeuroLex, LOINC, RxNorm, ClinVar). CHV even has `ts_rank()` BM25 sanity checks (`chv-bm25-sanity`).

The timeline is the outlier. `_search_timeline_ts_for_terms` uses `text ILIKE '%term%'` OR chains — no tsvector, no ranking, no trigram index. This was acceptable in the POC where RAG was primary. In the full implementation, the timeline needs the same treatment as every other source: `tsvector` column, GIN index, `ts_rank()` for BM25 scoring. The infrastructure and patterns already exist in the codebase. This is a matter of applying the established pattern to `ehr.patient_timeline`, not inventing anything new.

**5. The `augmented_rows` bug in `_run_eoh_gap_retrieval_for_timeline`.**

`augmented_rows` referenced but never defined — should be `current_context`. Live bug. Fix immediately.

**6. Schema duplication (Layer A vs Layer B) now matters.**

In the POC, only Layer A ran. Layer B (`ptv/models.py`) existed as a target schema. In the full implementation, the graph needs fields from both: Layer A's runtime simplicity *plus* Layer B's `embedding_id`, `confidence`, `strength`, and typed `RelationshipType`. Unify now, before the full implementation locks in one schema.

---

## 2. The Pipeline — EoHD First

The full implementation has two phases: **build the graph** (before EoHD), then **reason through it** (during EoHD). The POC conflated these into a single runtime. The full implementation separates them.

### Phase A: Ingest (extract + classify + timestamp)

```
PDF (4,223 pages)
  │
  ├─ Full extraction, not lite. Sampling 800 of 4,223 pages was
  │  acceptable for the POC. For the full implementation, missing
  │  pages = missing events = missing edges = missing diagnostic arcs.
  │  Use Ollama (llama3.1:8b or mistral-nemo) for extraction — this
  │  is parsing, not reasoning. Run all pages. Zero API cost.
  │
  ├─ Per-page event extraction → TimelineEventVision nodes
  │
  ├─ Aggressive reclassification pass:
  │    - Current keyword pass (_reclassify_event_types) is a good start
  │    - Add: NLP-based medical entity recognition pass (scispaCy or
  │      a small clinical NER model) to catch events the keyword pass
  │      misses. This is the single highest-leverage improvement for
  │      edge density downstream.
  │    - Ensure every event has: parseable timestamp (or explicit
  │      "unknown" with relative ordering preserved), correct event_type,
  │      and a preview that contains the clinical substance.
  │
  └─ Persist vision snapshot (checkpoint 1)
```

**Why full extraction is non-negotiable now:** In the POC, lite mode was a cost optimization for a side artifact. In the full implementation, the graph is the reasoning substrate. A rheumatology patient's 20-year record has critical inflection points scattered across the middle — the first positive ANA, the switch from methotrexate to biologics, the hospitalization that changed the diagnostic trajectory. Monte Carlo sampling is not guaranteed to catch these. The cost argument dissolves with local inference.

### Phase B: Connascence (mechanical + LLM, multi-pass)

```
Vision (all events, checkpointed)
  │
  ├─ Pass 1: Mechanical connascence (current Rules 1 + 4)
  │    - MUST produce thousands of edges for a multi-year record.
  │    - If it doesn't, the upstream extraction/classification failed.
  │    - Instrument: log edge count after each rule. Assert minimums.
  │
  ├─ Pass 2: LLM diagnostic connascence (current Rule 2)
  │    - Batched, 300 events/batch, precision > recall.
  │    - This is correct as designed. The issue is that it fires on
  │      a graph that's already sparse because mechanical edges are
  │      sparse — fix Phase A and this pass gets richer context.
  │
  ├─ Pass 3: LLM lab trend connascence (current Rule 3)
  │    - Same batch structure. Correct as designed.
  │
  ├─ Pass 4 (NEW): Symptom cluster connascence
  │    - Group symptom events by semantic similarity (requires
  │      TimelineChart / embedding index — see Phase C).
  │    - Events with cosine sim > 0.85 get candidate "symptom_cluster"
  │      edges. LLM validates in a confirmation pass.
  │
  ├─ Pass 5 (NEW): Cross-type causal inference
  │    - For each diagnostic chain (connected component from Pass 2),
  │      look for medication events within 60 days of diagnosis events
  │      and lab events within 90 days of medication starts.
  │    - This is the Phase 3 chain-building pass from the Strategy doc,
  │      but done at enrichment time, not summarization time.
  │
  └─ Persist vision snapshot (checkpoint 2)
```

**Why multi-pass:** Each pass builds on the previous one's edges. Mechanical edges give the LLM context for diagnostic inference. Diagnostic edges give the causal inference pass chains to extend. The graph compounds. A single pass cannot achieve this.

**Expected edge density after 5 passes:** 5–15% for a well-structured multi-year record. That's 200–600 edges for 4,226 events. Still sparse by graph standards, but rich enough for chain extraction and graph-guided summarization.

### Phase C: Index (make the graph queryable)

```
Vision (enriched, checkpointed)
  │
  ├─ Build TimelineChart (RepoChart pattern):
  │    - Embed every event using all-MiniLM-L6-v2 (local, free, 384d)
  │    - Text construction: "[{event_type}] {timestamp}\n{preview}\n
  │      Connascence: {conn_types}\nNeighbors: {top-3 neighbor previews}"
  │    - The neighbor previews in the embedding text are the key
  │      innovation over naive embedding — they make the vector space
  │      graph-aware. An event's embedding reflects its neighborhood,
  │      not just its content.
  │    - Persist as JSONL alongside vision JSON.
  │
  ├─ Build in-memory numpy matrix for cosine k-NN
  │
  └─ Register query methods:
       - search(query, top_k, filter_type) → semantic retrieval
       - get_near(event_id, top_k) → neighborhood expansion
       - get_chain(event_id) → walk connascence to connected component
       - get_subgraph(event_ids) → extract typed subgraph for LLM context
```

**Why local embeddings, not OpenAI:** Cost scales linearly with re-indexing. Every connascence pass that changes neighbor previews should trigger re-embedding of affected nodes. At OpenAI embedding prices, this makes iterative enrichment expensive. Local embeddings make it free. The quality difference for short clinical text is negligible.

**Why graph-aware embedding text:** Standard embedding of just `preview` makes the vector space blind to graph structure. Including neighbor previews means that two events that are semantically different but graph-connected (e.g., "started methotrexate" and "liver function elevated") will have *closer* embeddings because each includes the other's preview. This is the bridge between vector search and graph traversal.

### Phase D: EoHD agent query interface

This is the architectural centerpiece. The POC had no agent-facing graph query. The full implementation makes the graph the primary retrieval path for EoHD.

**How EoHD agents currently retrieve evidence** (POC / existing code):

In `eoh_stream_event_generator` (`rag_stream_eoh.py`), per selected source:
1. TS phase: `search_source_ts_for_terms(pool, source, terms)` — ILIKE on Postgres
2. ANN phase: `search_source_ann(pool, source, q_vec_literal)` — pgvector cosine
3. Merge: `dedupe_matches(ts_rows + ann_rows)`

The graph is invisible. Agents reason over flat text hits with no structural context.

**How EoHD agents should retrieve evidence** (full implementation):

```python
async def query_vision(
    question: str,
    vision: PatientTimelineVision,
    chart: TimelineChart,
) -> VisionQueryResult:
    """
    Primary graph query for EoHD agents.
    Composed: vector → graph expansion → chain extraction → subgraph.
    """
    # 1. Semantic retrieval against the graph's embedding index
    hits = chart.search(question, top_k=20)

    # 2. Graph expansion: for top-5 hits, walk connascence 2 hops
    seed_ids = [h.event_id for h in hits[:5]]
    expanded = set(seed_ids)
    for eid in seed_ids:
        for kind in vision.events[eid].connascence:
            neighbors = vision.get_connascent_events(eid, kind=kind)
            expanded.update(neighbors)
            if kind == "diagnostic":
                for nid in neighbors:
                    expanded.update(
                        vision.get_connascent_events(nid, kind="diagnostic")
                    )

    # 3. Assemble subgraph (chronological)
    subgraph_events = sorted(
        [vision.events[eid] for eid in expanded if eid in vision.events],
        key=lambda e: e.timestamp,
    )

    # 4. Extract diagnostic chains (connected components in subgraph)
    chains = _extract_diagnostic_chains(vision, expanded)

    return VisionQueryResult(
        events=subgraph_events,
        chains=chains,
        provenance=[h.event_id for h in hits[:5]],
    )
```

**Where this plugs in — the EoHD retrieval loop changes:**

```
CURRENT (POC):
  per step → TS + ANN against Postgres → flat text hits → LLM reasons

FULL IMPLEMENTATION:
  per step → query_vision (graph semantic + chain expansion)
           + TS + ANN against Postgres (raw evidence backing)
           → merge: graph-structured results carry chain context,
             RAG results carry source text for citation
           → LLM reasons over combined evidence with graph provenance
```

The graph query is not an optional parallel call. It is the primary retrieval path. Postgres RAG remains as the evidence-backing layer — when the graph says "this diagnosis connects to this lab trend via this treatment chain," the RAG source text provides the citable page and paragraph. Graph gives structure. RAG gives citation. Together they give the agent what neither alone can: *reasoned evidence with provenance*.

**For the planner:** Before step 1, the planner receives the graph's global topology — number of diagnostic chains, largest chains, gap regions (temporal periods with few events), high-degree nodes (events with many connections). This replaces the current `timeline_snapshot` with a graph-derived planning substrate that tells the planner *where to investigate*, not just *what happened*.

### Phase E: Opportunistic enrichment (already exists, needs wiring to query)

The current `enrich_graph_opportunistic` is correct in design. What it needs:

1. **After enrichment, re-embed affected nodes** in the TimelineChart. This keeps the vector index fresh as the graph compounds.
2. **Discrepancy detection:** When an agent's step answer contradicts an existing event's preview or timestamp, flag it. Add an `annotations.discrepancy` field. Surface discrepancies in the next query result.
3. **Missing-edge inference:** When an agent retrieves 3+ events from the same diagnostic chain but no edges exist between them, propose edges and run a lightweight LLM confirmation.

### Phase F: Visualization and simulation

```
Vision (queryable, enriched)
  │
  ├─ Graph visualization:
  │    - D3.js force-directed graph of events + edges
  │    - Color by event_type, edge thickness by connascence type
  │    - Time axis (x) with vertical lanes per event type
  │    - Click node → show preview, provenance, neighbors
  │    - This is the "patient story at a glance" view.
  │
  ├─ Diagnostic chain visualization:
  │    - Extract all connected components > 3 nodes
  │    - Render as horizontal Gantt-style chains
  │    - Each chain is a diagnostic arc: onset → workup → diagnosis → treatment → response
  │    - This is what clinicians actually want to see.
  │
  ├─ Simulation:
  │    - "What if" over the graph: remove a treatment node, re-run
  │      causal inference — what chains break?
  │    - Counterfactual exploration: "if methotrexate had been started
  │      6 months earlier, which downstream events would shift?"
  │    - This requires causal edge strength (not yet in Layer A).
  │      Add `confidence` field to edges as a prerequisite.
  │
  └─ Timeline analytics (partially exists in timeline/analytics.py):
       - Extend current charts with graph-derived metrics:
         edge density over time, diagnostic chain lengths,
         treatment response latencies, gap periods.
```

---

## 3. Priority Order (My Opinion) — EoHD First

The priorities are reordered around the constraint: EoHD must reason through the graph. Everything that blocks that is P0. Everything that improves it is P1. Everything else waits.

| Priority | Task | Why | Effort |
|----------|------|-----|--------|
| **P0** | Fix the `augmented_rows` bug | Live bug. Replace `augmented_rows` with `current_context`. | 5 min |
| **P0** | Wire Ollama client (`get_ollama_client()` + `--llm-backend`) | Unblocks full extraction without API credits. This is the gate. | Half day |
| **P0** | Run first full extraction + connascence on Norman Roberts record | The diagnostic run. Instrument everything. This tells us the actual state of the graph. | 1 day (wall clock — mostly model inference time) |
| **P0** | Unify Layer A + Layer B schema | The full implementation needs `embedding_id`, `confidence`, `strength` on every edge and node. Do this before building on Layer A's current schema — migrations get harder every day. | 1 day |
| **P1** | Build `TimelineChart` (`timeline_chart.py`) | RepoChart mirror with graph-aware embedding text. Unlocks `query_vision`, similarity clustering, symptom grouping. Without this, agents can't semantically search the graph. | 1-2 days |
| **P1** | Build `query_vision` and wire into `eoh_stream_event_generator` | **This is the feature.** Agents query the graph. Graph results merge with Postgres RAG. EoHD now reasons through structure. | 1-2 days |
| **P1** | Graph-derived planner input | Replace current `timeline_snapshot` with graph topology: chain count, largest chains, gap regions, high-degree nodes. Planner knows *where* to investigate. | 1 day |
| **P2** | Multi-pass connascence (Passes 4-5) | Symptom clustering + cross-type causal inference. Requires TimelineChart. Richer graph = better agent reasoning. | 2 days |
| **P2** | Discrepancy detection in opportunistic enrichment | When agent step output contradicts graph, flag it. Surface in next query. | 1 day |
| **P3** | Graph visualization (D3.js timeline + chain view) | Clinician-facing "story at a glance." Not needed for EoHD agent reasoning but high value for product. | 2-3 days |
| **P3** | Simulation / counterfactual exploration | Requires edge confidence. Design carefully. | 1-2 weeks |

---

## 4. The Connascence Density Problem Will Be The Whole Problem

Everything downstream — summarization quality, agent reasoning, chain extraction, visualization utility, simulation fidelity — depends on edge density. The first legit full run will reveal whether the pipeline produces a graph or a spreadsheet. If edge density comes back low after a complete run, the fix is not more LLM passes. The fix is upstream:

1. **Better timestamps.** If `_parse_ts` can't parse the timestamp, the event is invisible to all mechanical connascence rules. Medical records have notoriously inconsistent date formats. The parser needs to handle: `"03/2019"`, `"March 2019"`, `"3/15/19"`, `"2019-03-15T00:00:00Z"`, `"approximately 2018"`, `"several years ago"`. For the last two, assign a `timestamp_confidence` and use the best estimate.
2. **Better event types.** The `_reclassify_event_types` keyword pass catches obvious cases. But medical records are full of events that don't match simple keywords — "patient reports increasing joint stiffness" should be `symptom`, not `note`. A small clinical NER model (or even a focused LLM reclassification pass on events currently typed as `note` or `page`) would dramatically increase the coverage of Rules 1-4.
3. **Better previews.** The `preview` field is capped at ~200 chars from the extractor. For LLM connascence passes, the model needs enough clinical content to judge whether two events describe the same condition. If the preview truncates the diagnosis name, the LLM can't link them. Consider a `full_text` field (or `annotations.full_text`) for events where the source text is longer.

Fix these three *if they turn out to be weak after the first full run* and the mechanical rules alone should produce 500+ edges. Add LLM passes on top of a properly classified, properly timestamped graph and you'll hit the 5–15% density range that makes chain extraction meaningful. But the first full run may surprise — the pipeline might already handle these correctly. We don't know yet because credits ran out before the legit run completed.

---

## 5. On the Ollama Strategy

The original report's Tier A strategy is correct: use local models for extraction/enrichment, keep `gpt-4.1` for the final reduce and high-stakes reasoning. One adjustment:

**Don't use Ollama for embeddings.** Use `sentence-transformers` directly via Python. `all-MiniLM-L6-v2` is already a dependency for `RepoChart`. Adding an HTTP hop to Ollama for embeddings adds latency, a dependency on Ollama being running, and no quality benefit. Keep embeddings in-process. Reserve Ollama for LLM inference where the model size justifies an inference server.

The `get_ollama_client()` factory in `llm_client.py` is the right abstraction. The dual-client pattern for `summarize_timeline_from_pdf` (ingestion_client vs summary_client) is the right separation. Implement both. The cost savings are real and the quality tradeoff for extraction is negligible.

---

## 6. On Visualization and Simulation

Visualization is not cosmetic for this product. A clinician looking at a 4,223-page record needs to see the diagnostic story *before* reading any text. The graph visualization is the answer to "what happened to this patient?" in 5 seconds.

Two views matter:

**View 1: The Timeline Graph.** Events on a time axis, colored by type, edges drawn between connected events. This is the "at a glance" view. A clinician can immediately see: cluster of lab events in 2019 → diagnosis → medication start → lab response. The shape of the graph *is* the diagnostic story.

**View 2: The Chain View.** Extract the top-N diagnostic chains (connected components sorted by size or clinical significance). Render each as a horizontal arc: onset event → workup events → diagnosis → treatment → response → outcome. This is the "here are the N most important stories in this patient's record" view.

For simulation: proceed carefully. "What if we had started treatment earlier" is a counterfactual that requires causal inference, not just graph traversal. Edge confidence scores are a prerequisite. And the output must be clearly labeled as hypothetical, not predictive. For a V1, I'd limit simulation to: "remove this node — which chains break?" and "add a hypothetical treatment node at this timestamp — which existing events fall within its treatment response window?" These are graph operations, not causal claims.

---

## 7. Files to Create or Modify

| File | Action | Description |
|------|--------|-------------|
| `server/eoh/timeline_chart.py` | **CREATE** | RepoChart mirror for clinical events. Graph-aware embedding text. |
| `server/eoh/timeline_summarizer.py` ~line 2018 | **FIX** | Replace `augmented_rows` with `current_context` |
| `server/eoh/timeline_summarizer.py` connascence function | **INSTRUMENT** | Add logging for `len(dated)`, `len(med_dated)`, `len(resp_dated)` |
| `server/eoh/patient_timeline_vision.py` | **EXTEND** | Add `timestamp_confidence`, `full_text` to `TimelineEventVision`. Add `confidence` to edge model. Add `events_by_type()` method. |
| `server/llm/llm_client.py` | **EXTEND** | Add `get_ollama_client()` factory |
| `server/scripts/run_eohd_timeline_pdf.py` | **EXTEND** | Add `--llm-backend`, `--embed-backend` flags |
| `server/api/rag_stream_eoh.py` | **EXTEND** | Add `query_vision` call parallel to TS + ANN |
| `server/api/timeline_vision_routes.py` | **CREATE** | Vision graph visualization endpoints |

---

## 8. What I Would Do Tomorrow Morning

1. **Fix the `augmented_rows` bug.** Five minutes. Ship it.
2. **Unify schema.** Add `embedding_id`, `confidence`, `strength` to `TimelineEventVision` and edge model in `patient_timeline_vision.py`. Align with `ptv/models.py` `RelationshipType` enum. This is 30 minutes of dataclass editing that prevents weeks of migration pain later.
3. **Wire `get_ollama_client()`** into `llm_client.py`. Add `--llm-backend ollama` to the CLI. This unblocks full extraction regardless of API credit status.
4. **Run first full extraction + connascence** on the Norman Roberts record. All 4,223 pages via Ollama for extraction, `gpt-4.1` for connascence LLM passes only (or Ollama for those too if credits are still blocked). Instrument: `len(dated)`, `len(med_dated)`, `len(resp_dated)`, edge counts after each rule. This is the diagnostic milestone.
5. **Build `timeline_chart.py`.** Mirror `repo_chart.py`. Graph-aware embedding text. Index the Norman Roberts vision from step 4.
6. **Build `query_vision` and wire into `eoh_stream_event_generator`.** This is where the architecture inverts — agents now reason through the graph. Merge graph results with existing Postgres RAG. The graph provides chain structure. RAG provides citation text.
7. **Run EoHD detective on Norman Roberts with graph-based retrieval.** Compare output quality against the POC run (same record, same questions, graph-based vs graph-ignorant). This is the validation that the full implementation produces better clinical reasoning.

Steps 1-3 unblock. Step 4 tells you the state of the graph. Steps 5-6 are the feature. Step 7 is the proof.

---

*Appension filed 2026-03-27. Updated with POC→full implementation context. The graph was a side artifact. Now it's the substrate. EoHD first.*
