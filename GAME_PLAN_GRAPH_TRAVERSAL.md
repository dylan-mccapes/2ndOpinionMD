# GAME_PLAN: Graph Traversal Experiments — Norman PTV × eoh-llama-lucifer

**Source graph**: `artifacts/timeline_ollama_20260329_1805/patient_timeline_vision_norman_eric_roberts_20260329_195915.json`  
**Model**: `eoh-llama-lucifer` @ `http://localhost:11434`  
**Hardware**: RTX 4050 6GB (Lucifer), q4_K_M, 16K ctx  
**Objective**: Find the best traversal strategy for feeding Norman's PTV graph to eoh-llama for EoH-frame clinical reasoning

---

## Graph anatomy (observed)

```
event_id          string   "pdf_p0010_e0000"
event_type        string   "page" | "lab" | "medication" | "diagnosis" | "visit" | "procedure" | ...
timestamp         string   "12/28/2023" or "unknown"
preview           string   raw text excerpt from the PDF page
discovered_by     list     ["pdf_page_10"]
status            string   "included" | ...
connascence       object   {
                             "temporal":  [event_id, ...],   # same-time cluster
                             "treatment": [event_id, ...],   # drug→outcome, dx→rx
                             "causal":    [event_id, ...],   # event → event cause
                             "diagnostic":[event_id, ...]    # lab → impression
                           }
annotations       object   { "pdf_page": 10 }
```

**Key observations**:
- Pages 1–9 are header/cover noise: `event_type: "page"`, empty connascence — must be filtered
- Real clinical graph starts at p10 (first lab: Hgb A1c 6.2%)
- Connascence edges are typed and bidirectional (multiple relationship layers)
- ~4,200 source pages → estimated thousands of real clinical events

---

## Phase 0 — Build the index layer (prerequisite for all experiments)

Before any traversal, build reusable in-memory indices from the JSON.
Script: `server/scripts/graph/build_index.py`

```
graph_index = {
  "by_type":        { "lab": [...], "medication": [...], ... }
  "by_timestamp":   sorted list of (parsed_date, event_id) — unknowns bucketed separately
  "by_page":        { 10: [event_id, ...], ... }
  "adjacency":      { event_id: { "temporal": [...], "treatment": [...], ... } }
  "degree":         { event_id: total_edge_count }
  "token_estimate": { event_id: len(preview) // 4 }
}
```

This index is the substrate. Every experiment imports it. Build once, reuse everywhere.

---

## Reduction strategies (thin the graph before traversal)

### R1 — Type filter
**Idea**: Drop `event_type: "page"` entirely. Pages are PDF dump noise with no connascence.
**Expected**: Removes ~2,000–3,000 events, keeps only lab/medication/diagnosis/visit/procedure.
**Code**: `[e for e in events if e["event_type"] != "page"]`

### R2 — Timestamp validity filter
**Idea**: Drop events with `timestamp: "unknown"`. These can't be placed on a timeline.
**Variant A**: Drop them entirely.
**Variant B**: Keep them in a separate "undated" bucket for context injection at the end.
**Note**: Many page-type events have unknown timestamps — R1+R2 together may remove >80% of noise.

### R3 — Connascence density filter
**Idea**: Keep only events with at least one connascence edge. Events with empty `connascence: {}` are isolated nodes — no graph signal.
**Expected**: Very aggressive reduction. Isolated nodes contribute nothing to multi-hop traversal.

### R4 — Status filter
**Idea**: Only process events with `status: "included"`. Any other status values are pipeline artifacts.

### R5 — Regex sweep — structured extraction
**Idea**: Run regex over `preview` text to extract machine-readable signals without LLM:
- Lab values: `r'([A-Za-z][A-Za-z0-9 ]+)\s+(\d+\.?\d*)\s*(\([HL]\))?'` → `{name, value, flag}`
- ICD-10 codes: `r'\b[A-Z]\d{2}\.?\d*\b'`
- Drug names + dosages: `r'(\w+)\s+(\d+\.?\d*\s*mg)'`
- Dates: `r'\d{1,2}/\d{1,2}/\d{4}'`
- A1c, CRP, ESR, ANA patterns: disease-specific panel regexes

**Output**: Structured event metadata that can be filtered/sorted without any embedding or LLM.
**Use case**: Pre-filter to "all abnormal labs" → pass only those events to traversal.

### R6 — Keyword whitelist filter
**Idea**: Maintain a clinical keyword list (autoimmune-specific):
```python
KEYWORDS = ["lupus", "SLE", "ANA", "anti-dsDNA", "rheumatoid", "flare",
            "methotrexate", "hydroxychloroquine", "prednisone", "CRP", "ESR",
            "fatigue", "joint", "inflammation", ...]
```
Score each event by keyword hit count. Filter to top N or threshold.
**Advantage**: Zero latency, zero dependencies. Instant domain-aware reduction.

### R7 — Token budget pruning
**Idea**: Each event costs `len(preview) // 4` tokens (rough estimate). Sort by relevance signal (keyword score, degree, recency), keep events until budget fills (e.g., 12,000 tokens of 16,384 ctx).
**This is the core budget management layer used by all traversal strategies.**

### R8 — Temporal binning
**Idea**: Parse all timestamps, bin events into N-month buckets. Discard buckets with fewer than K events (sparse periods with no clinical activity).
**Output**: A ranked list of "active periods" — months where the most happened. Focus traversal there.

---

## Traversal strategies

### T1 — Linear chronological sweep (baseline)
**Idea**: Sort all events by timestamp, walk forward in time, batch into LLM context windows.
**This is what the existing pipeline does.** Benchmark for all others to beat.
**Weakness**: No graph signal — treats events as a flat list. Context windows are arbitrary, not clinically meaningful.

### T2 — Type-partitioned temporal
**Idea**: Apply R1 first (drop page events), then partition by type: all labs sorted chronologically → LLM call; all medications chronologically → LLM call; all diagnoses → LLM call. Final LLM call gets summaries from each partition.
**Strengths**: Natural clinical question alignment. Lab trends, medication history, and diagnosis timeline each get dedicated reasoning.
**Model call budget**: 4–5 calls + 1 synthesis call.

### T3 — Temporal windowing with overlap
**Idea**: Slide a 90-day window across the timeline. Each window = one LLM call. Windows overlap by 30 days to preserve continuity across boundaries.
**Output per window**: structured EoH state snapshot `{stack, band, flare_risk, drivers}`.
**Final call**: Feed all snapshots → reduce to longitudinal trajectory.
**Handles**: The 38-year Norman timeline. Windowing prevents context overflow.

### T4 — Hierarchical map-reduce
**Idea**: Classic LLM document reduction, applied to the graph.
```
Level 0: ~50 event chunks → each gets an EoH micro-summary
Level 1: ~10 micro-summaries → grouped into period summaries
Level 2: All period summaries → single final narrative
```
**Strength**: Scales to any graph size. Each call is within token budget.
**Weakness**: Summaries lose raw signal (compression artifacts compound upward).

### T5 — Anchor-and-expand (BFS from seed node)
**Idea**: Pick a seed event — e.g., the event with the highest connascence degree, or a known key diagnosis. BFS outward along connascence edges, collecting events until token budget fills.
**Seed selection options**:
- Highest total edge count (most structurally important)
- Most recent diagnosis event
- First ANA+ result
- User-specified event_id
**Strength**: Context is topically coherent — everything in the window is graph-connected to the seed.
**Code**: Standard BFS with a token budget deque.

### T6 — DFS along connascence chains
**Idea**: From a seed, DFS along one edge type at a time (e.g., only `treatment` edges). Follow chains to depth N, collect the chain as a narrative path.
**Use case**: "Trace this medication forward — what outcomes follow it?"
**Output**: A causal chain from intervention to downstream state.

### T7 — Connascence-type partitioned traversal
**Idea**: Treat each connascence edge type as a separate graph layer:
- `temporal` layer → temporal proximity reasoning
- `treatment` layer → intervention→outcome reasoning
- `causal` layer → cause→effect reasoning
- `diagnostic` layer → lab→impression reasoning
Run one LLM call per layer, then synthesize across layers.
**Strength**: Each LLM call has a single well-defined reasoning task.

### T8 — Centrality-first traversal
**Idea**: Rank all events by graph centrality metrics, traverse highest-centrality first.
- **Degree centrality**: events with most edges (hubs)
- **Betweenness centrality**: events that bridge clusters (no library needed — approximate via sampling)
- **Temporal centrality**: events that appear in many connascence lists from other events
**Tool**: `networkx` on the adjacency list, or manual degree counting from the JSON.
**Strength**: Surface the most clinically significant events without any LLM or embedding. Pure structural signal.

### T9 — Sentence-transformer semantic retrieval (FAISS)
**Idea**: Embed all event `preview` texts using a sentence-transformer model. At query time, embed the clinical question and retrieve top-K most semantically similar events.
**Model**: `sentence-transformers/all-MiniLM-L6-v2` (90 MB, CPU-friendly) or `pritamdeka/S-PubMedBert-MS-MARCO` (medical domain)
**Index**: FAISS `IndexFlatIP` (cosine) or `IndexIVFFlat` (faster for large N)
**Pipeline**:
```
query = "What is Norman's inflammatory burden over 2023?"
query_vec = model.encode(query)
top_k = faiss_index.search(query_vec, k=30)
events = [event_map[id] for id in top_k.ids]
# → LLM call with top_k events as context
```
**Strength**: Handles semantic synonymy. "Joint pain" matches "arthralgia". No keyword list maintenance.
**Cost**: One-time embedding pass (~minutes on CPU for thousands of events). Sub-millisecond retrieval.

### T10 — BM25 sparse retrieval
**Idea**: Classic BM25 over event previews. Better than TF-IDF for short clinical text.
**Library**: `rank_bm25` (pip install, zero dependencies)
**Use case**: Keyword-style queries where exact term match matters more than semantics.
**Fast, no GPU, no embeddings.** Complementary to T9.

### T11 — Hybrid retrieval (BM25 + FAISS RRF fusion)
**Idea**: Run both BM25 and FAISS retrieval, fuse results with Reciprocal Rank Fusion (RRF). Each method contributes its top-K, RRF reranks.
**Formula**: `score(event) = Σ 1/(k + rank_in_method_i)` where k=60
**Strength**: BM25 catches exact clinical terms; FAISS catches semantic variants. Together they miss less.

### T12 — Regex + temporal hybrid
**Idea**: Use R5 regex extraction to parse structured lab values. Build a time series per biomarker (A1c, CRP, ESR, ANA, etc.). Feed biomarker time series as structured data to LLM instead of raw preview text.
```
A1c timeline: [2022-05: 6.0, 2023-12: 6.2, ...]
CRP timeline: [2023-03: 14.2 (H), ...]
```
**Advantage**: Dramatically denser signal per token. No prose filler.
**Use case**: "Is Norman's metabolic control deteriorating?" — pure time series reasoning.

### T13 — Hypothesis-guided beam search
**Idea**: Start with a clinical hypothesis (e.g., "Lupus nephritis onset precipitated the 2019 flare cluster"). Score candidate next events for relevance to the hypothesis. Expand only the top-B branches (beam width B=3).
**Scoring**: Keyword overlap or sentence-transformer cosine similarity against the hypothesis string.
**Output**: A path through the graph that confirms or contradicts the hypothesis, with evidence trail.
**Strength**: Directed, hypothesis-driven. No wasted context on irrelevant events.

### T14 — Flare-cluster detection → inward traversal
**Idea**: First pass identifies temporal clusters of abnormal events (labs flagged H/L, new diagnoses, medication changes all within a 60-day window). These are candidate flare periods.
Mark them as cluster seeds. Second pass: for each cluster, collect all events within ±90 days, run LLM call.
**Strength**: Finds the most clinically dramatic periods automatically.

### T15 — Multi-hop connascence chain context
**Idea**: For each seed event, follow connascence edges N hops deep, collecting the chain. Present the chain as ordered context to the LLM with hop depth annotated.
```
[Seed: lab/A1c 6.2 → hop1: treatment/metformin_increase → hop2: temporal/visit_endocrinology → ...]
```
**Strength**: The LLM sees causally-linked events in traversal order, not arbitrary batches.
**Token efficiency**: Chains of 5–10 hops are typically within budget.

### T16 — Reverse chronological with recency weighting
**Idea**: Walk backward from the most recent event. Weight recent events more heavily in token allocation — they reflect current state. Older events get progressively less budget.
**Use case**: "What is Norman's state right now and how did we get here?"

### T17 — Named Entity Recognition (NER) pre-pass
**Idea**: Run a lightweight medical NER model over all previews to extract entities: conditions, drugs, labs, procedures, body parts. Use entity co-occurrence to build an entity graph overlaid on the event graph.
**Model**: `en_core_sci_sm` (scispaCy, 12 MB) or `d4data/biomedical-ner-all` (HuggingFace)
**Output**: Entity-annotated events. Filter/group by entity type before LLM traversal.

### T18 — Temporal + connascence hybrid window
**Idea**: For each temporal window (T3), instead of taking ALL events in that window, expand only via connascence edges from the period's highest-degree node. Intersect temporal window with connascence neighborhood.
**Result**: A context window that is both temporally coherent AND graph-connected — not just an arbitrary time slice.

### T19 — Type-reduction → temporal sort → semantic rerank
**Idea**: Three-stage pipeline:
1. R1+R2+R3 (type, timestamp, connascence density filters) — drops noise
2. T3 temporal sort — imposes timeline structure
3. T9 FAISS semantic rerank within each window — reorders events by relevance to the window's summary query
**The most sophisticated pre-LLM pipeline. Addresses all three failure modes of the baseline.**

### T20 — Graph community detection → per-community LLM calls
**Idea**: Run a simple community detection algorithm (Louvain or label propagation) on the connascence adjacency list. Each community = a clinically coherent cluster of co-occurring events. Run one LLM call per community, synthesize.
**Library**: `networkx` + `community` (python-louvain)
**Strength**: Communities emerge from the graph structure itself — no human-defined taxonomy needed.

---

## Experiment execution plan

Each experiment = one Python script in `server/scripts/graph/`:

```
server/scripts/graph/
  build_index.py          # Phase 0 — build and cache graph_index
  run_linear.py           # T1 baseline
  run_type_partition.py   # T2
  run_windowed.py         # T3
  run_map_reduce.py       # T4
  run_bfs_anchor.py       # T5
  run_dfs_chain.py        # T6
  run_centrality.py       # T8
  run_faiss.py            # T9 — requires sentence-transformers + faiss-cpu
  run_bm25.py             # T10 — requires rank_bm25
  run_hybrid_rrf.py       # T11
  run_regex_timeseries.py # T12
  run_hypothesis.py       # T13
  run_flare_clusters.py   # T14
  run_community.py        # T20 — requires python-louvain
```

Each script:
1. Imports `build_index.py` output
2. Applies its reduction strategy
3. Calls `eoh-llama-lucifer` at `http://localhost:11434/api/chat` (native endpoint — NOT /v1)
4. Writes output to `artifacts/graph_traversal/<strategy>/<timestamp>.json`
5. Prints: events considered, events sent, token estimate, call count, latency, output quality notes

---

## Evaluation rubric

For each strategy, score manually:

| Metric | Description |
|--------|-------------|
| **Precision** | Did the context contain what the LLM actually used? |
| **Recall** | Did the LLM miss clinically important events that were in the graph? |
| **Coherence** | Did the LLM response apply EoH modules correctly? |
| **Token efficiency** | Signal tokens / total tokens sent |
| **Latency** | Seconds per LLM call × number of calls |
| **Scalability** | Would this work on a 10x larger graph? |

---

## Dependencies

```bash
pip install rank_bm25 networkx python-louvain faiss-cpu sentence-transformers scispacy
python -m spacy download en_core_sci_sm   # optional NER
```

All CPU-compatible. FAISS and sentence-transformers use CPU on Lucifer (GPU reserved for Ollama).

---

## Recommended execution order

1. `build_index.py` — required first
2. `run_linear.py` — establish baseline quality and latency
3. `run_type_partition.py` — quick win, no new dependencies
4. `run_regex_timeseries.py` — zero-dependency, high signal density test
5. `run_bm25.py` — add keyword retrieval
6. `run_bfs_anchor.py` — first graph-native traversal
7. `run_faiss.py` — semantic retrieval (requires install)
8. `run_hybrid_rrf.py` — best-of-both retrieval
9. `run_flare_clusters.py` — clinically motivated, should produce best EoH alignment
10. `run_community.py` — pure graph structure, interesting to compare vs semantic
