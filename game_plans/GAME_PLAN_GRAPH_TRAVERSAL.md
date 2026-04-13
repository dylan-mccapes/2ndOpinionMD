# GAME_PLAN: Graph Traversal Experiments — Norman PTV × eoh-llama-lucifer

> **Location:** All `GAME_PLAN_*.md` and strategy artifacts live under `game_plans/`.  
> **Agent surface (core 12):** `game_plans/STRATEGY_GRAPH_TRAVERSAL.md` + `server/graph_traversal/agent_tools.py`.

**Source graph**: `artifacts/timeline_ollama_20260329_1805/patient_timeline_vision_norman_eric_roberts_20260329_195915.json`  
**Model**: `eoh-llama-lucifer` @ `http://localhost:11434`  
**Hardware**: RTX 4050 6GB (Lucifer), q4_K_M, 16K ctx  
**Objective**: Find the best traversal strategy for feeding Norman's PTV graph to eoh-llama for EoH-frame clinical reasoning

---

## Graph anatomy (observed)

```
patient_id        "norman_eric_roberts"
total_events      7,705
total_edges       ~16,000+ directed (temporal + treatment + diagnostic)
isolated_nodes    ~4,000 (connascence: {})
event_types       medication(2463) lab(1863) diagnosis(1060) visit(779)
                  page(723) note(273) symptom(245) procedure(242)
                  imaging(52) vital_signs(3) office_visit(1) appointment(1)
connascence_types temporal(3675 events) treatment(2610) diagnostic(251)
timeline_span     ~39 years
```

Per-event schema:
```
event_id          string   "pdf_p0010_e0000"
event_type        string   "lab" | "medication" | "diagnosis" | "visit" | ...
timestamp         string   "12/28/2023" or "unknown"
preview           string   raw text excerpt from the PDF page
discovered_by     list     ["pdf_page_10"]
status            string   "included" | ...
connascence       object   {
                             "temporal":   [event_id, ...],
                             "treatment":  [event_id, ...],
                             "diagnostic": [event_id, ...]
                           }
annotations       object   { "pdf_page": 10 }
```

**Key observations**:
- Pages 1–9 are header/cover noise: `event_type: "page"`, empty connascence
- Real clinical graph starts at p10 (first lab: Hgb A1c 6.2%)
- Connascence edges are typed — three layers observed: temporal, treatment, diagnostic
- 4,000 isolated nodes (zero edges) — over half the graph is disconnected noise
- Existing tooling: `demo_living_graph.py` has BFS traversal, semantic search (PatientChart), RRF fusion, timestamp recovery, graph analysis tools, and LLM synthesis with enrichment write-back

---

## Phase 0 — Build the index layer (prerequisite for all experiments)

Before any traversal, build reusable in-memory indices from the JSON.
Script: `server/scripts/graph/build_index.py`

```python
graph_index = {
  "by_type":        { "lab": [...], "medication": [...], ... },
  "by_timestamp":   sorted list of (parsed_date, event_id),
  "unknowns":       [event_id, ...],  # timestamp = "unknown"
  "by_page":        { 10: [event_id, ...], ... },
  "adjacency":      { event_id: { "temporal": [...], "treatment": [...], ... } },
  "reverse_adj":    { event_id: { "temporal": [...], ... } },  # inbound edges
  "degree":         { event_id: { "in": N, "out": N, "total": N } },
  "token_estimate": { event_id: len(preview) // 4 },
  "edge_count":     { "temporal": N, "treatment": N, "diagnostic": N },
  "components":     [[event_id, ...], ...],  # connected components
}
```

Also builds a `networkx.DiGraph` for strategies that need it (centrality, community, spectral, etc.).
This index is the substrate. Every experiment imports it. Build once, reuse everywhere.

---

## PART A: Reduction Strategies (thin the graph before traversal)

### R1 — Type filter
Drop `event_type: "page"`. Pages are PDF dump noise with no connascence.
**Expected**: Removes ~723 events, keeps only lab/medication/diagnosis/visit/procedure/note/symptom/imaging.
```python
[e for e in events if e["event_type"] != "page"]
```

### R2 — Timestamp validity filter
Drop events with `timestamp: "unknown"`. These can't be placed on a timeline.
**Variant A**: Drop entirely.
**Variant B**: Keep in separate "undated" bucket for context injection at end.
**Note**: R1+R2 together may remove >60% of noise.

### R3 — Connascence density filter
Keep only events with at least one connascence edge. Isolated nodes contribute nothing to multi-hop traversal.
**Expected**: Removes ~4,000 isolated nodes — very aggressive. Only ~3,705 connected events survive.

### R4 — Status filter
Only process events with `status: "included"`. Other statuses are pipeline artifacts.

### R5 — Regex sweep — structured extraction
Run regex over `preview` text to extract machine-readable signals without LLM:
```python
PATTERNS = {
    "lab_value":   r'([A-Za-z][A-Za-z0-9 ]+)\s+(\d+\.?\d*)\s*(\([HL]\))?',
    "icd10":       r'\b[A-Z]\d{2}\.?\d*\b',
    "drug_dose":   r'(\w+)\s+(\d+\.?\d*\s*mg)',
    "date":        r'\d{1,2}/\d{1,2}/\d{4}',
    "vitals":      r'(BP|HR|Temp|SpO2|RR)\s*[:\s]+(\d+[/.]?\d*)',
    "a1c":         r'(?:Hgb\s*)?A1c\s*[%:]?\s*(\d+\.?\d*)',
    "crp":         r'CRP\s*[:\s]*(\d+\.?\d*)',
    "esr":         r'ESR\s*[:\s]*(\d+\.?\d*)',
    "ana":         r'ANA\s*[:\s]*(positive|negative|1:\d+)',
    "wbc":         r'WBC\s*[:\s]*(\d+\.?\d*)',
    "creatinine":  r'[Cc]reatinine\s*[:\s]*(\d+\.?\d*)',
}
```
**Output**: Structured event metadata, filterable/sortable without embedding or LLM.
**Use case**: Pre-filter to "all abnormal labs" → pass only those to traversal.

### R6 — Keyword whitelist filter
Clinical keyword list (autoimmune-specific):
```python
KEYWORDS = ["lupus", "SLE", "ANA", "anti-dsDNA", "rheumatoid", "flare",
            "methotrexate", "hydroxychloroquine", "prednisone", "CRP", "ESR",
            "fatigue", "joint", "inflammation", "nephritis", "complement",
            "C3", "C4", "fibromyalgia", "plaquenil", "rituximab", "azathioprine",
            "mycophenolate", "cyclophosphamide", "proteinuria", "hematuria",
            "neuropathy", "vasculitis", "rash", "photosensitivity", ...]
```
Score each event by keyword hit count. Filter to top N or threshold.
**Zero latency, zero dependencies.** Instant domain-aware reduction.

### R7 — Token budget pruning
Each event costs `len(preview) // 4` tokens. Sort by relevance signal (keyword score, degree, recency), keep events until budget fills (e.g., 12,000 of 16,384 ctx).
**This is the core budget management layer used by all traversal strategies.**

### R8 — Temporal binning
Parse all timestamps, bin events into N-month buckets. Discard buckets with fewer than K events (sparse periods with no clinical activity).
**Output**: Ranked list of "active periods" — months where the most happened.

### R9 — Preview deduplication
Many pages produce near-duplicate events (same lab on consecutive pages). Exact or fuzzy deduplicate on `preview` text.
```python
from difflib import SequenceMatcher
def is_near_dup(a, b, threshold=0.92):
    return SequenceMatcher(None, a, b).ratio() > threshold
```
**Expected**: 10–20% reduction in connected events with zero signal loss.

### R10 — Preview length filter
Drop events with `len(preview) < 10`. Trivially short previews ("..." or single words) carry no signal.

### R11 — Abnormal-only lab filter
After R5 regex extraction, keep only labs with `(H)` or `(L)` flags or values outside reference ranges. Normal labs consume tokens without driving clinical reasoning.

### R12 — Medication change filter
Keep only medication events where dosage changed, drug was added/stopped, or route changed vs. prior entry. Refills at same dose are low-signal.
```python
# Group medication events by drug_name, sort by timestamp
# Keep first occurrence, last occurrence, and any where dose differs from predecessor
```

### R13 — Page-rank weighted filter
Run PageRank on the connascence graph. Events with PageRank below the 25th percentile are likely peripheral. Filter to top 75%.

### R14 — Information entropy filter
Compute Shannon entropy of each event's preview tokens. High-entropy previews contain diverse clinical information; low-entropy previews are boilerplate headers.
```python
from collections import Counter
import math
def preview_entropy(text):
    tokens = text.lower().split()
    c = Counter(tokens)
    n = len(tokens)
    return -sum((v/n) * math.log2(v/n) for v in c.values()) if n > 0 else 0
```

---

## PART B: Traversal Strategies — Chronological / Sequential

### T1 — Linear chronological sweep (baseline)
Sort all events by timestamp, walk forward in time, batch into LLM context windows.
**This is what the existing pipeline does.** Benchmark for all others to beat.
**Weakness**: No graph signal — treats events as a flat list.

### T2 — Type-partitioned temporal
Apply R1 first, then partition by type: all labs chronologically → LLM call; all medications → LLM call; all diagnoses → LLM call. Final LLM call gets summaries from each partition.
**Model call budget**: 4–5 calls + 1 synthesis call.

### T3 — Temporal windowing with overlap
Slide a 90-day window across the timeline. Each window = one LLM call. Windows overlap by 30 days.
**Output per window**: structured EoH state snapshot `{stack, band, flare_risk, drivers}`.
**Final call**: All snapshots → reduce to longitudinal trajectory.

### T4 — Hierarchical map-reduce
```
Level 0: ~50 event chunks → each gets an EoH micro-summary
Level 1: ~10 micro-summaries → grouped into period summaries
Level 2: All period summaries → single final narrative
```
**Weakness**: Summaries lose raw signal (compression artifacts compound upward).

### T16 — Reverse chronological with recency weighting
Walk backward from most recent event. Weight recent events more heavily in token allocation.
**Use case**: "What is Norman's state right now and how did we get here?"

---

## PART C: Traversal Strategies — Graph-Structural

### T5 — Anchor-and-expand (BFS from seed node)
Pick a seed event — highest degree, most recent diagnosis, first ANA+, user-specified. BFS outward along connascence edges, collecting events until token budget fills.
```python
def bfs_budget(graph, seed, budget_tokens=12000):
    visited, queue, collected = set(), deque([(seed, 0)]), []
    token_total = 0
    while queue:
        eid, depth = queue.popleft()
        if eid in visited: continue
        visited.add(eid)
        cost = graph.token_estimate[eid]
        if token_total + cost > budget_tokens: continue
        token_total += cost
        collected.append((eid, depth))
        for edge_type, targets in graph.adjacency[eid].items():
            for tid in targets:
                if tid not in visited:
                    queue.append((tid, depth + 1))
    return collected
```

### T6 — DFS along connascence chains
From a seed, DFS along one edge type at a time (e.g., only `treatment` edges). Follow chains to depth N.
**Use case**: "Trace this medication forward — what outcomes follow it?"

### T7 — Connascence-type partitioned traversal
Treat each connascence edge type as a separate graph layer:
- `temporal` layer → temporal proximity reasoning
- `treatment` layer → intervention→outcome reasoning
- `diagnostic` layer → lab→impression reasoning
One LLM call per layer, then synthesize.

### T8 — Centrality-first traversal
Rank all events by centrality metrics, traverse highest-centrality first:
- **Degree centrality**: events with most edges (hubs)
- **Betweenness centrality**: events that bridge clusters
- **Eigenvector centrality**: events connected to other important events
- **Closeness centrality**: events with shortest average path to all others
```python
import networkx as nx
G = build_networkx_graph(graph_index)
degree = nx.degree_centrality(G)
betweenness = nx.betweenness_centrality(G, k=min(500, len(G)))  # sampled
eigenvector = nx.eigenvector_centrality_numpy(G)
```

### T15 — Multi-hop connascence chain context
For each seed, follow connascence edges N hops deep, present chain with hop depth annotated:
```
[Seed: lab/A1c 6.2 → hop1: treatment/metformin_increase → hop2: visit_endocrinology → ...]
```

### T20 — Graph community detection → per-community LLM calls
Run community detection (Louvain or label propagation) on adjacency list. Each community = clinically coherent cluster. One LLM call per community, synthesize.
```python
import networkx as nx
from community import community_louvain
partition = community_louvain.best_partition(G.to_undirected())
communities = defaultdict(list)
for node, comm_id in partition.items():
    communities[comm_id].append(node)
```

### T21 — k-core decomposition
Find the k-core of the connascence graph — the maximal subgraph where every node has degree ≥ k. The innermost core contains the densest clinical signal.
```python
import networkx as nx
core_numbers = nx.core_number(G)
max_k = max(core_numbers.values())
inner_core = [n for n, k in core_numbers.items() if k == max_k]
# Traverse outward from inner core
```
**Use case**: Find the absolute densest cluster of interconnected clinical events — likely the primary disease trajectory.

### T22 — Bridge / articulation point detection
Find articulation points (nodes whose removal disconnects the graph) and bridge edges. These are structurally critical — they connect otherwise separate clinical narratives.
```python
articulation_pts = list(nx.articulation_points(G.to_undirected()))
bridges = list(nx.bridges(G.to_undirected()))
```
**Use case**: Identify pivot events — the moment when one clinical arc connects to another (e.g., a diagnosis that links a lab trend to a treatment trajectory).

### T23 — Random walk with restart (personalized PageRank)
Start from a seed node, random walk with probability α of jumping back to seed at each step. Nodes visited most frequently are most relevant to the seed.
```python
ppr = nx.pagerank(G, alpha=0.85, personalization={seed: 1.0})
top_nodes = sorted(ppr, key=ppr.get, reverse=True)[:50]
```
**Advantage over BFS**: Naturally handles multi-path relevance — nodes reachable via many paths rank higher. Robust to noisy edges.

### T24 — Minimum spanning tree of connascence graph
Build MST on the connected component, weighting edges by inverse connascence strength. The MST captures the skeleton of the clinical narrative — the minimum set of relationships that keep the graph connected.
```python
mst = nx.minimum_spanning_tree(G.to_undirected(), weight='inv_strength')
# Walk the MST in DFS order for a narrative-coherent traversal
```

### T25 — Spectral clustering
Compute graph Laplacian eigenvectors, cluster in spectral space. Unlike Louvain, spectral clustering can find clusters at specific granularity controlled by number of eigenvectors.
```python
import numpy as np
from scipy.sparse.linalg import eigsh
L = nx.normalized_laplacian_matrix(G.to_undirected()).astype(float)
eigenvalues, eigenvectors = eigsh(L, k=10, which='SM')
# K-means on first k eigenvectors
from sklearn.cluster import KMeans
labels = KMeans(n_clusters=5).fit_predict(eigenvectors)
```

### T26 — Motif / triangle detection
Count triangles (3-node cycles) in the connascence graph. Events participating in many triangles form tightly coupled clinical micro-narratives.
```python
triangles = nx.triangles(G.to_undirected())
high_triangle = [n for n, count in triangles.items() if count > 3]
```
**Use case**: Find co-occurring lab-medication-diagnosis triplets that form a complete clinical picture.

### T27 — Jaccard similarity clustering
Compute Jaccard similarity between nodes based on shared neighbors. Cluster by similarity to find events that "look alike" structurally even if not directly connected.
```python
from itertools import combinations
def jaccard(G, u, v):
    nu = set(G.neighbors(u))
    nv = set(G.neighbors(v))
    return len(nu & nv) / len(nu | nv) if nu | nv else 0
```

### T28 — Graph diameter path traversal
Find the diameter (longest shortest path) of each connected component. Walk along the diameter path — it represents the full narrative arc from one extreme of the clinical story to the other.

---

## PART D: Traversal Strategies — Retrieval-Based

### T9 — Sentence-transformer semantic retrieval (FAISS)
Embed all event previews using sentence-transformers. Query-time cosine retrieval.
**Model**: `all-MiniLM-L6-v2` (90 MB, CPU) or `pritamdeka/S-PubMedBert-MS-MARCO` (medical domain)
**Index**: FAISS `IndexFlatIP` (cosine)
```python
query_vec = model.encode(query)
top_k = faiss_index.search(query_vec, k=30)
```

### T10 — BM25 sparse retrieval
Classic BM25 over event previews. Better than TF-IDF for short clinical text.
```python
from rank_bm25 import BM25Okapi
corpus = [e.preview.lower().split() for e in events]
bm25 = BM25Okapi(corpus)
scores = bm25.get_scores(query.lower().split())
```

### T11 — Hybrid retrieval (BM25 + FAISS RRF fusion)
Run both BM25 and FAISS retrieval, fuse with Reciprocal Rank Fusion:
```python
score(event) = Σ 1/(k + rank_in_method_i)   where k=60
```
BM25 catches exact clinical terms; FAISS catches semantic variants. Together they miss less.

### T29 — Cross-encoder reranking
After initial retrieval (T9/T10/T11), rerank top-50 candidates with a cross-encoder that scores (query, event_preview) pairs jointly. Much more accurate than bi-encoder similarity.
```python
from sentence_transformers import CrossEncoder
reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
pairs = [(query, e.preview) for e in candidates]
scores = reranker.predict(pairs)
```

### T30 — HyDE (Hypothetical Document Embeddings)
Instead of embedding the query directly, ask the LLM to generate a hypothetical answer, then embed that answer and search. The hypothetical answer is closer in embedding space to the real evidence.
```python
hypothetical = llm("Write a clinical note that would answer: " + query)
hyp_vec = model.encode(hypothetical)
results = faiss_index.search(hyp_vec, k=30)
```

### T31 — Query decomposition + sub-retrieval
Decompose a complex query into atomic sub-queries, retrieve for each, merge:
```python
sub_queries = llm("Break this into 3 simpler clinical questions: " + query)
# e.g., "What is Norman's ANA history?" + "What medications target inflammation?"
#      + "When did kidney involvement begin?"
all_results = [retrieve(sq) for sq in sub_queries]
merged = rrf_merge(all_results)
```

### T32 — ColBERT-style late interaction (lightweight)
Instead of single-vector similarity, compute token-level MaxSim between query tokens and document tokens. More precise matching without full cross-encoder cost.
```python
# Encode query and doc tokens separately, compute MaxSim
q_embs = model.encode(query, output_value='token_embeddings')
d_embs = model.encode(doc, output_value='token_embeddings')
score = sum(max(cos_sim(qt, dt) for dt in d_embs) for qt in q_embs)
```

### T33 — Multi-vector retrieval
Represent each event as multiple vectors (one per sentence in preview). Query matches against all vectors; best-matching sentence determines relevance. Handles long previews with heterogeneous content.

---

## PART E: Traversal Strategies — Temporal / Time-Series

### T12 — Regex + temporal hybrid (biomarker time series)
Use R5 regex extraction to parse lab values. Build per-biomarker time series:
```
A1c:  [2022-05: 6.0, 2023-12: 6.2, ...]
CRP:  [2023-03: 14.2 (H), ...]
ESR:  [2023-06: 42, ...]
```
Feed as structured data instead of raw prose. **Dramatically denser signal per token.**

### T14 — Flare-cluster detection → inward traversal
First pass: identify temporal clusters of abnormal events (labs flagged H/L, new diagnoses, medication changes all within a 60-day window). Mark as cluster seeds. Second pass: for each cluster, collect all events within ±90 days.

### T18 — Temporal + connascence hybrid window
For each temporal window (T3), expand only via connascence edges from the period's highest-degree node. Intersect temporal window with connascence neighborhood.
**Result**: Context that is both temporally coherent AND graph-connected.

### T34 — Changepoint detection
Apply changepoint detection algorithms to biomarker time series (from T12) to find moments where the underlying distribution shifts.
```python
import ruptures
signal = np.array([v for _, v in a1c_timeseries])
algo = ruptures.Pelt(model="rbf").fit(signal)
changepoints = algo.predict(pen=3)
```
Each changepoint is a candidate "inflection event" — collect surrounding graph events for LLM reasoning.
**Library**: `ruptures` (pip install, CPU-only)

### T35 — Granger causality between biomarker streams
Test whether one biomarker time series (e.g., CRP) Granger-causes another (e.g., joint pain severity). Identifies temporal lead-lag relationships.
```python
from statsmodels.tsa.stattools import grangercausalitytests
data = np.column_stack([crp_series, pain_series])
results = grangercausalitytests(data, maxlag=4)
```
**Use case**: "Does CRP elevation precede symptom flares by N months?" — feed the causal pairs to the LLM for EoH interpretation.

### T36 — Dynamic time warping (DTW) between event sequences
Compare temporal patterns between different event types using DTW. Find which event type sequences most closely mirror each other — reveals hidden co-variation.
```python
from dtaidistance import dtw
distance = dtw.distance(lab_timestamps, medication_timestamps)
```

### T37 — Temporal motif detection
Find recurring temporal patterns: e.g., "lab → diagnosis → medication change" triples that repeat at regular intervals. These are clinical cycles.
```python
# Sliding window over event sequence, extract type-trigrams
trigrams = Counter()
for i in range(len(sorted_events) - 2):
    t = (sorted_events[i].event_type,
         sorted_events[i+1].event_type,
         sorted_events[i+2].event_type)
    trigrams[t] += 1
```

### T38 — Survival analysis / hazard modeling
Model time-to-event (e.g., time-to-next-flare) using Cox proportional hazards with biomarker values as covariates.
```python
from lifelines import CoxPHFitter
cph = CoxPHFitter()
cph.fit(df, duration_col='days_to_flare', event_col='flare_occurred')
# Identify which biomarkers are strongest predictors
hazard_ratios = cph.hazard_ratios_
```
**Use case**: Feed the hazard ratios and risk curves to the LLM as structured evidence for flare probability reasoning (M13).

### T39 — Autocorrelation / periodicity detection
Compute autocorrelation of biomarker time series to detect periodic patterns (e.g., seasonal flares, menstrual cycle correlations).
```python
from statsmodels.tsa.stattools import acf
autocorr = acf(crp_series, nlags=24)  # monthly lags
# Peaks in autocorrelation reveal periodicity
```

---

## PART F: Traversal Strategies — Semantic / NLP

### T13 — Hypothesis-guided beam search
Start with a clinical hypothesis. Score candidate next events for relevance. Expand only top-B branches (beam width B=3).
**Output**: Path through the graph that confirms or contradicts the hypothesis.

### T17 — Named Entity Recognition (NER) pre-pass
Run lightweight medical NER over all previews to extract: conditions, drugs, labs, procedures, body parts.
```python
import spacy
nlp = spacy.load("en_core_sci_sm")
for event in events:
    doc = nlp(event.preview)
    event.entities = [(ent.text, ent.label_) for ent in doc.ents]
```
**Model**: `en_core_sci_sm` (scispaCy, 12 MB) or `d4data/biomedical-ner-all`

### T40 — Topic modeling (LDA / BERTopic)
Discover latent clinical topics across all event previews. Each topic = a clinical theme (e.g., "renal function", "autoimmune markers", "pain management").
```python
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
vectorizer = CountVectorizer(max_df=0.95, min_df=2, stop_words='english')
tf = vectorizer.fit_transform([e.preview for e in events])
lda = LatentDirichletAllocation(n_components=15, random_state=42)
topics = lda.fit_transform(tf)
```
**Use case**: Group events by topic, run one LLM call per topic, synthesize.

### T41 — Entity co-occurrence graph overlay
After NER (T17), build a separate graph where nodes are entities (drug names, conditions, labs) and edges are co-occurrence within the same event or temporal window. This is an abstraction layer above the event graph.
```python
entity_graph = nx.Graph()
for event in events:
    entities = [ent.text for ent in nlp(event.preview).ents]
    for a, b in combinations(entities, 2):
        if entity_graph.has_edge(a, b):
            entity_graph[a][b]['weight'] += 1
        else:
            entity_graph.add_edge(a, b, weight=1)
```
**Use case**: Traverse the entity graph to understand drug-condition-lab triangles without reading thousands of raw events.

### T42 — Embedding clustering (DBSCAN / HDBSCAN)
Cluster event embeddings (from T9) to find natural groupings. Unlike topic modeling, this works in continuous semantic space.
```python
from hdbscan import HDBSCAN
clusterer = HDBSCAN(min_cluster_size=15, metric='cosine')
labels = clusterer.fit_predict(embeddings)
```
Each cluster = a semantically coherent set of events. LLM call per cluster.

### T43 — Node2Vec / DeepWalk graph embeddings
Learn low-dimensional vector representations of nodes from the graph structure alone (no text). Nodes that occupy similar structural positions get similar embeddings.
```python
from node2vec import Node2Vec
n2v = Node2Vec(G, dimensions=64, walk_length=30, num_walks=200, p=1, q=2)
model = n2v.fit(window=10, min_count=1)
# Now use model.wv to find structurally similar nodes
similar = model.wv.most_similar("pdf_p0010_e0000", topn=20)
```
**Use case**: Find events that play the same structural role (e.g., "all events that act as treatment-outcome bridges").

### T44 — UMAP dimensionality reduction + cluster
Project embeddings (T9) or graph embeddings (T43) to 2D via UMAP. Identify visual clusters, label them, use as traversal seeds.
```python
import umap
reducer = umap.UMAP(n_components=2, metric='cosine')
coords = reducer.fit_transform(embeddings)
```
**Side benefit**: Produces a visual map of the entire clinical graph for the operator.

---

## PART G: Traversal Strategies — Dynamical Systems & Simulation

### T45 — Lorenz attractor classification via provenance-engine ★

**This is the centerpiece integration.** `provenance-engine` (pip install) maps PTV events to Lorenz attractor initial conditions, integrates with RK4, and classifies as KEEP / EVICT / REVIEW.

**PTV → provenance-engine mapping:**
```python
from provenance_engine import build_graph, normalize_and_scale, integrate_portal, classify_node

def ptv_to_pe_nodes(graph_index):
    """Convert PTV events to provenance-engine node format."""
    nodes = []
    for eid, event in graph_index.events.items():
        total_edges = sum(len(v) for v in event.connascence.values())
        edge_list = []
        for edge_type, targets in event.connascence.items():
            pe_type = {
                "temporal":   "TEMPORAL",
                "treatment":  "STRUCTURAL",
                "diagnostic": "SUPPORTING",
            }.get(edge_type, "CO_OCCURRENCE")
            for tid in targets:
                edge_list.append({
                    "target": tid,
                    "type": pe_type,
                    "strength": 0.8
                })

        importance = "high" if event.event_type in ("diagnosis", "lab") and total_edges > 3 \
                     else "medium" if total_edges > 0 \
                     else "low"

        nodes.append({
            "id": eid,
            "edges": edge_list,
            "importance": importance,
            "load_bearing": event.event_type == "diagnosis" or total_edges > 10,
            "created_at": parse_to_iso(event.timestamp),
            "metadata": {
                "event_type": event.event_type,
                "preview": event.preview[:200],
            }
        })
    return nodes
```

**Initial conditions mapping (PE internal):**
- **x₀** — structural connectivity (normalized degree)
- **y₀** — connascence strength (weighted mean of edge associations)
- **z₀** — temporal vitality (inverse log decay from last update)

**Classification:**
- `mean_x < -τ` → **KEEP** (left wing: consolidated memory — clinically important)
- `mean_x > τ` → **EVICT** (right wing: decayed — safe to ignore for traversal)
- `|mean_x| ≤ τ` → **REVIEW** (chaotic boundary — interesting edge cases)

**Integration with traversal:**
1. Run `pe scan` on the PTV graph
2. Use KEEP nodes as primary traversal targets (guaranteed high-signal)
3. Use REVIEW nodes as tie-breakers when token budget permits
4. EVICT nodes are never sent to the LLM
5. Run `pe sweep` to find optimal ρ × τ for this specific graph

```bash
pip install provenance-engine
pe init
pe scan --graph norman_ptv_as_pe.jsonl
pe sweep --graph norman_ptv_as_pe.jsonl
pe probe --classification classification_rho28.0_tau2.0.json --graph norman_ptv_as_pe.jsonl
pe gap --probe-report probe_report.json
```

**Why this works for PTV**: The Lorenz attractor naturally separates structurally consolidated nodes (many edges, recent, important) from decayed noise. This is mathematically principled graph reduction — not heuristic filtering.

### T46 — Parameter sweep: ρ × τ grid search for optimal graph compression
Use `pe sweep` to test ρ (eviction pressure) and τ (classification threshold) combinations. Find the governance-stable band where:
- Total eviction rate < 30%
- High-importance eviction rate < 5%
- Zero load-bearing evictions (no diagnoses evicted)

```python
from provenance_engine import sweep_portal
results = sweep_portal(
    nodes=pe_nodes,
    rho_range=(20, 35, 1.0),   # test ρ from 20 to 35
    tau_range=(1.0, 4.0, 0.5), # test τ from 1.0 to 4.0
)
# Find governance-stable band
stable = [r for r in results if r.evict_pct < 0.30 and r.high_evict_pct < 0.05]
```

### T47 — LLM governance via PE probe + gap agents
After Lorenz classification, run `pe probe` (reviews each EVICT candidate with graph context) and `pe gap` (synthesizes into final governance decisions). Uses eoh-llama-lucifer locally.
```bash
PE_MODEL=eoh-llama-lucifer PE_OLLAMA_URL=http://localhost:11434 pe probe --classification ...
```
This turns the graph reduction into a human-in-the-loop (or LLM-in-the-loop) process where no structurally important node gets silently dropped.

### T48 — Heat diffusion simulation on connascence graph
Model information flow as heat diffusion on the graph. Start with "heat" concentrated at seed events (abnormal labs, new diagnoses). After N diffusion steps, highest-temperature nodes are most "reachable" from the clinical signal.
```python
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import expm_multiply

A = nx.adjacency_matrix(G).astype(float)
D = np.diag(np.array(A.sum(axis=1)).flatten())
L = D - A  # Laplacian

# Initial heat: 1.0 on seed nodes, 0.0 elsewhere
heat = np.zeros(len(G))
for seed in seed_nodes:
    heat[node_index[seed]] = 1.0

# Diffuse for time t
diffused = expm_multiply(-L, heat, start=0, stop=1.0, num=10)[-1]
top_heated = np.argsort(diffused)[::-1][:50]
```
**Advantage over BFS**: Heat diffuses proportionally to edge density — multi-path connections naturally accumulate more heat.

### T49 — SIR epidemic spreading model (flare propagation)
Model flare propagation as an epidemic on the connascence graph. "Infect" a seed event (initial flare trigger). SIR dynamics determine which connected events get "infected" (are part of the flare cascade).
```python
import random

def sir_spread(G, seed, beta=0.3, gamma=0.1, steps=50):
    """beta=transmission prob, gamma=recovery prob"""
    S = set(G.nodes()) - {seed}
    I = {seed}
    R = set()
    infected_order = [seed]
    for _ in range(steps):
        new_I = set()
        for node in list(I):
            for neighbor in G.neighbors(node):
                if neighbor in S and random.random() < beta:
                    new_I.add(neighbor)
                    S.discard(neighbor)
                    infected_order.append(neighbor)
            if random.random() < gamma:
                I.discard(node)
                R.add(node)
        I |= new_I
        if not I:
            break
    return infected_order
```
**Use case**: Simulate "if this lab result triggers a cascade, what events are part of it?" Multiple runs with different seeds reveal which events are consistently part of flare cascades.

### T50 — Coupled oscillator synchronization (Kuramoto model)
Model each event as an oscillator with a natural frequency proportional to its clinical activity level. Connected events tend to synchronize. After simulation, highly synchronized clusters represent tightly coupled clinical dynamics.
```python
import numpy as np

def kuramoto_step(phases, natural_freqs, adjacency, coupling=0.5, dt=0.01):
    N = len(phases)
    dphase = np.zeros(N)
    for i in range(N):
        coupling_sum = sum(
            np.sin(phases[j] - phases[i])
            for j in adjacency[i]
        )
        dphase[i] = natural_freqs[i] + (coupling / max(len(adjacency[i]), 1)) * coupling_sum
    return phases + dphase * dt

# Run for 1000 steps, then cluster by final phase
# Nodes with similar phases are synchronization-locked
```
**Interpretation**: Events that synchronize form a clinical "rhythm" — they co-vary in the patient's health trajectory.

### T51 — Lotka-Volterra dynamics (competing condition model)
Model interactions between condition types as predator-prey dynamics. Disease X (e.g., lupus nephritis) and treatment Y (e.g., immunosuppression) interact — when treatment increases, disease activity decreases.
```python
def lotka_volterra(x, y, alpha, beta, delta, gamma, dt=0.01):
    """x=prey(disease), y=predator(treatment)"""
    dx = (alpha * x - beta * x * y) * dt
    dy = (delta * x * y - gamma * y) * dt
    return x + dx, y + dy
```
Parameterize from biomarker time series (T12): disease activity = CRP/ESR trajectory, treatment = medication dosage trajectory. Simulate forward to predict flare risk.

### T52 — Phase space reconstruction from biomarker time series
Apply Takens' embedding theorem to reconstruct the attractor geometry of a single biomarker time series. Reveals hidden dynamics even from univariate data.
```python
def takens_embed(series, dim=3, tau=2):
    """Time-delay embedding: reconstruct phase space from 1D series."""
    N = len(series) - (dim - 1) * tau
    return np.array([series[i:i + dim * tau:tau] for i in range(N)])

embedded = takens_embed(crp_values, dim=3, tau=3)
# Compute Lyapunov exponent to quantify chaos
# Positive → chaotic/unpredictable, zero → periodic, negative → stable
```
**Feed to LLM**: "The CRP time series has a positive Lyapunov exponent of 0.12, indicating chaotic dynamics with a prediction horizon of ~8 days."

### T53 — Allostatic load simulation (M68 ICM)
Directly implement the EoH M68 Inflammatory Capacity Model as a simulation on the graph:
```python
def icm_simulate(events_sorted, ic_max=100, inflow_base=0.1,
                 outflow_rate=0.05, turbulence_threshold=0.7):
    """Three-valve ICM from EoH M68."""
    ic_level = 0
    trajectory = []
    for event in events_sorted:
        inflow = compute_inflow(event)  # from lab values, symptoms
        # Turbulence amplification when load exceeds threshold
        if ic_level / ic_max > turbulence_threshold:
            inflow *= 1 + (ic_level / ic_max - turbulence_threshold) * 5
        outflow = outflow_rate * ic_level
        ic_level = max(0, min(ic_max, ic_level + inflow - outflow))
        trajectory.append({
            "event_id": event.event_id,
            "ic_level": ic_level,
            "ic_pct": ic_level / ic_max,
            "overflow": ic_level >= ic_max,
        })
    return trajectory
```
**This is the most EoH-native simulation.** It directly computes the allostatic headroom at each event. Overflow = flare. Post-overflow hysteresis temporarily reduces IC_max.

---

## PART H: Traversal Strategies — Information-Theoretic

### T54 — Mutual information between event features
Compute MI between event type pairs (e.g., MI between "lab" events and "medication" events in the same temporal window). High MI = strong dependency.
```python
from sklearn.metrics import mutual_info_score
# Discretize: for each month, count events of type A and type B
# MI tells us how much knowing about one type predicts the other
mi = mutual_info_score(type_a_counts, type_b_counts)
```

### T55 — Transfer entropy (causal information flow)
Directional measure: does the lab time series carry information about the future medication time series? Transfer entropy is Granger causality generalized to nonlinear systems.
```python
# Using PyInform or manual computation
from pyinform import transfer_entropy
te = transfer_entropy(source_series, target_series, k=2)
```
**Use case**: Build a directed "information flow" graph between biomarker streams. Feed the flow structure to the LLM.

### T56 — Minimum description length (MDL) graph compression
Find the minimum description of the graph — the smallest set of events + patterns that can reconstruct the full graph. Events that contribute to compression are high-signal; redundant events can be dropped.

### T57 — Shannon entropy of temporal distributions
Compute entropy of event distribution across time bins. Low-entropy periods (events concentrated in a few months) are likely flare clusters. High-entropy periods are baseline.
```python
from scipy.stats import entropy
monthly_counts = [events_per_month.get(m, 0) for m in all_months]
H = entropy(monthly_counts)
# Low H → concentrated → flare period
```

---

## PART I: Traversal Strategies — Clinical / Domain-Specific

### T19 — Type-reduction → temporal sort → semantic rerank
Three-stage pipeline:
1. R1+R2+R3 (type, timestamp, connascence density filters)
2. T3 temporal sort
3. T9 FAISS semantic rerank within each window
**Most sophisticated pre-LLM pipeline. Addresses all three failure modes of the baseline.**

### T58 — ICD/SNOMED ontology-guided traversal
Map extracted diagnoses to ICD-10 codes (via R5 regex). Use ICD-10 hierarchy to group related diagnoses. Traverse the graph organized by ontological proximity rather than temporal or structural proximity.
```python
# Using the icd11_who_loader.py already in the codebase
# Group events by ICD chapter: "Diseases of the musculoskeletal system"
# → all rheumatologic events in one context window
```

### T59 — Drug interaction graph overlay
Build a secondary graph where nodes are medications and edges are known interactions (from a drug interaction database or extracted from events). Overlay on the PTV graph to find potential interaction cascades.
```python
KNOWN_INTERACTIONS = {
    ("methotrexate", "nsaid"): "nephrotoxicity_risk",
    ("prednisone", "metformin"): "glucose_antagonism",
    ...
}
# For each medication pair in the PTV, check for known interactions
# Feed interaction chains to LLM
```

### T60 — Comorbidity co-occurrence matrix
Build a matrix of diagnosis co-occurrences (which conditions appear together in the same temporal windows). The eigenstructure of this matrix reveals latent disease clusters.
```python
import numpy as np
diagnoses = sorted(set(e.annotations.get("dx") for e in events if e.event_type == "diagnosis"))
matrix = np.zeros((len(diagnoses), len(diagnoses)))
# For each temporal window, increment co-occurring diagnosis pairs
# Eigendecompose to find principal comorbidity axes
```

### T61 — Treatment response tracking
For each medication, build a before/after biomarker comparison:
```python
# For each medication start event:
# 1. Collect labs in [-90, 0] days (before)
# 2. Collect labs in [0, +90] days (after)
# 3. Compute delta for each biomarker
# 4. Classify: improved / worsened / unchanged
treatment_responses = []
for med_event in medication_events:
    pre_labs = get_labs_in_window(med_event.timestamp, -90, 0)
    post_labs = get_labs_in_window(med_event.timestamp, 0, 90)
    delta = compute_deltas(pre_labs, post_labs)
    treatment_responses.append({
        "drug": med_event.annotations.get("drug_name"),
        "delta": delta,
        "response": classify_response(delta),
    })
```
**Feed to LLM**: "Methotrexate: CRP dropped 40% in 90 days. Prednisone taper: ESR rebounded 25%."

---

## PART J: Agent-Directed Architecture (the orchestration layer)

### The Core Loop: Agent Asks, System Provides, Simulation Runs Between

This is the master architecture. The LLM agent has access to a tool registry. It decides what it needs. The system provides it. Between iterations, simulations run to update graph state.

```
┌─────────────────────────────────────────────────────────┐
│  AGENT (eoh-llama-lucifer via Ollama)                   │
│                                                          │
│  System prompt: EoH framework + tool descriptions        │
│  The agent emits structured tool_call JSON               │
│  The agent receives tool results as structured JSON      │
│                                                          │
│  "I need all abnormal labs within 90 days of event X"    │
│  "Run a Lorenz scan with ρ=28 on the current subgraph"  │
│  "Compute transfer entropy between CRP and joint_pain"   │
│  "Simulate ICM from event Y forward 30 events"           │
│  "Find bridges in the treatment connascence layer"       │
│  "Run HDBSCAN on embeddings of the last 50 events"      │
└──────────────────────┬──────────────────────────────────┘
                       │ tool_call
                       ▼
┌─────────────────────────────────────────────────────────┐
│  SYSTEM (Python orchestrator)                            │
│                                                          │
│  1. Parse tool_call                                      │
│  2. Execute against graph_index / PE / embeddings        │
│  3. Return structured result (token-budgeted)            │
│  4. [BETWEEN TURNS] Run background simulations:          │
│     - PE classify updated subgraph                       │
│     - ICM tick forward with new evidence                 │
│     - Heat diffusion from latest evidence nodes          │
│  5. Append simulation state to next context              │
└─────────────────────────────────────────────────────────┘
```

### T62 — ReAct tool-using agent
The agent follows Reason-Act-Observe cycles. Each turn:
1. **Reason**: Think about what information is needed
2. **Act**: Call a tool
3. **Observe**: Receive result, update reasoning

```python
TOOLS = {
    # --- Retrieval ---
    "semantic_search":      lambda q, k=20: chart.search(q, top_k=k),
    "keyword_search":       lambda q, k=20: graph_ts_search(vision, q, limit=k),
    "bm25_search":          lambda q, k=20: bm25_retrieve(q, k),
    "hybrid_search":        lambda q, k=20: hybrid_rrf_search(q, k),

    # --- Graph traversal ---
    "bfs_traverse":         lambda seed, depth=2, edge_types=None: graph_traverse(vision, seed, edge_types, depth),
    "dfs_chain":            lambda seed, edge_type, depth=5: dfs_chain(vision, seed, edge_type, depth),
    "zoom_window":          lambda start, end, types=None: graph_zoom(vision, start, end, types),
    "get_event":            lambda eid: vision.events[eid].to_dict() if eid in vision.events else None,
    "get_neighbors":        lambda eid: get_all_neighbors(vision, eid),

    # --- Graph analysis ---
    "centrality":           lambda metric="degree": compute_centrality(G, metric),
    "community_detect":     lambda: detect_communities(G),
    "k_core":               lambda k=3: get_k_core(G, k),
    "bridges":              lambda: find_bridges(G),
    "shortest_path":        lambda a, b: nx.shortest_path(G, a, b),
    "event_type_dist":      lambda: tool_event_type_distribution(vision),
    "edge_density":         lambda: tool_edge_density_by_type(vision),
    "temporal_gaps":        lambda min_days=90: tool_temporal_gaps(vision, min_days),

    # --- Time series ---
    "biomarker_series":     lambda biomarker: extract_biomarker_timeseries(vision, biomarker),
    "changepoints":         lambda series_name: detect_changepoints(vision, series_name),
    "granger_test":         lambda source, target: granger_causality(vision, source, target),
    "periodicity":          lambda series_name: detect_periodicity(vision, series_name),

    # --- Simulation ---
    "lorenz_scan":          lambda rho=28, tau=2.0: run_pe_scan(pe_nodes, rho, tau),
    "icm_simulate":         lambda from_event=None, steps=50: run_icm(vision, from_event, steps),
    "heat_diffuse":         lambda seeds, time=1.0: heat_diffusion(G, seeds, time),
    "sir_spread":           lambda seed, beta=0.3: sir_simulation(G, seed, beta),

    # --- Regex / extraction ---
    "extract_labs":         lambda eid: regex_extract_labs(vision, eid),
    "abnormal_labs_in_window": lambda start, end: get_abnormal_labs(vision, start, end),
    "medication_changes":   lambda drug=None: find_medication_changes(vision, drug),
    "treatment_response":   lambda drug, window=90: compute_treatment_response(vision, drug, window),

    # --- NLP ---
    "ner_extract":          lambda eid: run_ner(vision, eid),
    "topic_for_events":     lambda eids: get_topics(eids),
    "embedding_cluster":    lambda eids: cluster_embeddings(eids),
}
```

### T63 — Multi-agent debate (EoH modules as separate agents)
Run multiple specialized agents, each embodying a different EoH module:
```python
AGENTS = {
    "M13_prognostic": "You are the Trend & Prognostic module. Compute flare probability.",
    "M64_FUDD":       "You are the FUDD detector. Look for functional utilization discordance.",
    "M68_ICM":        "You are the ICM module. Assess allostatic headroom.",
    "M6_escalation":  "You are the Escalation Router. Determine appropriate alert tier.",
}

# Each agent gets the same evidence, produces a structured assessment
# A synthesis agent (M15) consolidates all assessments
```
**Advantage**: Specialized agents reason deeper within their domain. Disagreements between agents surface genuine clinical uncertainty.

### T64 — Socratic probing (agent asks, graph answers)
Invert the typical pattern: the LLM asks clinical questions, the system answers from the graph.
```python
agent_prompt = """You are investigating Norman's health trajectory.
Ask one precise clinical question at a time.
The system will answer from the patient's graph data.
Continue until you can produce a complete EoH assessment."""

# Turn 1: Agent asks "What is the most recent ANA result?"
# System: graph_ts_search("ANA") → returns event
# Turn 2: Agent asks "What medications were active at that time?"
# System: zoom_window(date-30, date+30, types=["medication"])
# ...until agent says "I have enough to assess."
```

### T65 — Hypothesis-refute-revise loop
The agent generates a hypothesis, then actively tries to refute it:
```python
# Round 1: Generate hypothesis
hypothesis = agent("Based on initial evidence, what is your hypothesis?")
# Round 2: Search for counter-evidence
counter = hybrid_search("evidence against: " + hypothesis)
# Round 3: Revise or strengthen
revised = agent(f"Original: {hypothesis}\nCounter-evidence: {counter}\nRevise your assessment.")
```
**Directly implements M67 ARGL mandatory falsification.**

### T66 — Evidence accumulation (Sequential Probability Ratio Test)
Accumulate evidence for/against a clinical hypothesis one event at a time. Stop when confidence crosses a threshold (Wald's SPRT).
```python
import math
def sprt_step(log_ratio, event, hypothesis):
    """Update log-likelihood ratio for hypothesis vs null."""
    p_h1 = score_event_for_hypothesis(event, hypothesis)
    p_h0 = 0.5  # null: random relevance
    log_ratio += math.log(p_h1 / p_h0) if p_h1 > 0 else -2
    return log_ratio

# Stop when log_ratio > A (accept) or log_ratio < B (reject)
A = math.log(19)   # 95% confidence accept
B = math.log(1/19) # 95% confidence reject
```
**Use case**: "Is Norman in a lupus flare?" — accumulate evidence event by event until statistically confident.

### T67 — Simulation-in-the-loop: PE classification between agent turns
After each agent turn, re-run Lorenz classification on the subgraph the agent has touched. Newly classified KEEP/EVICT/REVIEW states inform the next turn's context budget.
```python
for turn in range(max_turns):
    # Agent reasons and calls tools
    response = agent_turn(context)
    touched_events = extract_referenced_events(response)

    # Between turns: run Lorenz on touched subgraph
    subgraph = extract_subgraph(pe_nodes, touched_events, depth=1)
    classification = pe_scan(subgraph, rho=28, tau=2.0)

    # Update context with simulation results
    context.append({
        "simulation": "lorenz",
        "keep": classification["KEEP"],
        "review": classification["REVIEW"],
        "evict": classification["EVICT"],
    })

    # Also run ICM tick
    icm_state = icm_tick(touched_events)
    context.append({"simulation": "icm", "ic_level": icm_state["ic_pct"]})
```

### T68 — Iterative graph enrichment during traversal
The agent can request enrichments as it traverses — filling in missing timestamps, normalizing drug names, adding connascence edges it discovers. The graph improves as the agent works.
```python
ENRICHMENT_TOOLS = {
    "set_timestamp":    lambda eid, ts: set_event_timestamp(vision, eid, ts),
    "add_edge":         lambda src, tgt, etype: add_connascence(vision, src, tgt, etype),
    "set_drug_name":    lambda eid, name: set_annotation(vision, eid, "drug_name", name),
    "mark_abnormal":    lambda eid: set_annotation(vision, eid, "abnormal", True),
}
```
**This is the "living graph" — the graph grows with attention.** Already prototyped in `demo_living_graph.py` Phase 4 (ENRICH).

---

## PART K: Composite Strategies (best combinations)

### C1 — The Full Funnel
```
R1 (drop page) + R3 (drop isolated) + R9 (dedup) + R11 (abnormal labs only)
    → T45 (Lorenz KEEP/EVICT/REVIEW)
    → T8 (centrality sort on KEEP nodes)
    → T11 (hybrid retrieval for query-specific ranking)
    → T29 (cross-encoder rerank top 50)
    → T62 (ReAct agent with remaining budget)
```
Maximum noise reduction → structural prioritization → semantic relevance → agent reasoning.

### C2 — Simulation-First
```
R1 + R3
    → T45 (Lorenz scan)
    → T53 (ICM simulation on KEEP nodes)
    → T48 (heat diffusion from ICM overflow events)
    → T14 (flare cluster detection on heated nodes)
    → T62 (agent with ICM trajectory + flare clusters as priors)
```
Dynamics-driven: the math tells us where to look before the LLM even starts.

### C3 — Evidence Accumulation
```
R1 + R2 + R3
    → T40 (topic model — discover clinical themes)
    → T66 (SPRT for each theme as a hypothesis)
    → T65 (hypothesis-refute-revise on surviving hypotheses)
    → T63 (multi-agent debate on final assessment)
```
Statistical confidence-driven reasoning.

### C4 — Pure Graph Structure (zero NLP)
```
R1 + R3 + R4
    → T21 (k-core decomposition — find dense core)
    → T22 (bridges — find narrative pivots)
    → T23 (personalized PageRank from each bridge)
    → T25 (spectral clustering)
    → T45 (Lorenz classification)
    → Single LLM call with the structural skeleton
```
Test: can graph structure alone surface the clinical story?

### C5 — Time Series + Dynamics
```
R5 (regex extract all labs)
    → T12 (build biomarker time series)
    → T34 (changepoint detection)
    → T35 (Granger causality between streams)
    → T52 (phase space reconstruction)
    → T38 (survival analysis)
    → T53 (ICM simulation)
    → Single LLM call with extracted temporal features
```
No graph traversal at all — pure time series analysis.

---

## Experiment execution plan

Each experiment = one Python script in `server/scripts/graph/`:

```
server/scripts/graph/
  build_index.py              Phase 0 — build and cache graph_index + networkx graph
  ptv_to_pe.py                Convert PTV → provenance-engine JSONL format

  # Part B: Reduction
  run_reduction_benchmark.py  Test R1–R14 individually and combined, report event counts

  # Part C: Sequential
  run_linear.py               T1 baseline
  run_type_partition.py        T2
  run_windowed.py              T3
  run_map_reduce.py            T4

  # Part D: Graph-structural
  run_bfs_anchor.py            T5
  run_dfs_chain.py             T6
  run_centrality.py            T8
  run_community.py             T20
  run_kcore.py                 T21
  run_bridges.py               T22
  run_ppr.py                   T23 (personalized PageRank)
  run_spectral.py              T25

  # Part E: Retrieval
  run_faiss.py                 T9
  run_bm25.py                  T10
  run_hybrid_rrf.py            T11
  run_cross_rerank.py          T29
  run_hyde.py                  T30
  run_query_decomp.py          T31

  # Part F: Temporal
  run_regex_timeseries.py      T12
  run_flare_clusters.py        T14
  run_changepoints.py          T34
  run_granger.py               T35
  run_survival.py              T38
  run_periodicity.py           T39

  # Part G: Dynamical systems
  run_lorenz_scan.py           T45 (provenance-engine)
  run_pe_sweep.py              T46 (ρ × τ grid search)
  run_pe_governance.py         T47 (probe + gap agents)
  run_heat_diffusion.py        T48
  run_sir_spread.py            T49
  run_icm_simulation.py        T53

  # Part H: Semantic / NLP
  run_ner_prepass.py           T17
  run_topic_model.py           T40
  run_entity_cooccurrence.py   T41
  run_embedding_cluster.py     T42
  run_node2vec.py              T43

  # Part I: Information-theoretic
  run_mutual_info.py           T54
  run_transfer_entropy.py      T55
  run_temporal_entropy.py      T57

  # Part J: Agent-directed
  run_react_agent.py           T62
  run_multi_agent.py           T63
  run_socratic.py              T64
  run_hypothesis_loop.py       T65
  run_sprt.py                  T66
  run_sim_in_loop.py           T67

  # Part K: Composites
  run_full_funnel.py           C1
  run_sim_first.py             C2
  run_evidence_accum.py        C3
  run_pure_structure.py        C4
  run_timeseries_dynamics.py   C5
```

Each script:
1. Imports `build_index.py` output
2. Applies its strategy
3. Calls `eoh-llama-lucifer` at `http://localhost:11434/api/chat`
4. Writes output to `artifacts/graph_traversal/<strategy>/<timestamp>.json`
5. Prints: events considered, events sent, token estimate, call count, latency, output quality notes

---

## Evaluation rubric

| Metric | Description |
|--------|-------------|
| **Precision** | Did the context contain what the LLM actually used? |
| **Recall** | Did the LLM miss clinically important events in the graph? |
| **Coherence** | Did the LLM response apply EoH modules correctly? |
| **Token efficiency** | Signal tokens / total tokens sent |
| **Latency** | Seconds per LLM call × number of calls |
| **Scalability** | Would this work on a 10x larger graph? |
| **Reproducibility** | Same result on repeated runs? (important for stochastic methods) |
| **Enrichment yield** | Did the strategy discover graph errors or missing data? |

---

## Dependencies

```bash
# Core (already available)
pip install numpy networkx

# Retrieval
pip install rank_bm25 sentence-transformers faiss-cpu

# NLP
pip install scispacy
python -m spacy download en_core_sci_sm

# Graph
pip install python-louvain node2vec

# Time series
pip install ruptures statsmodels lifelines dtaidistance

# Clustering / ML
pip install hdbscan umap-learn scikit-learn

# Information theory
pip install pyinform

# Dynamical systems / simulation
pip install provenance-engine[all]

# Visualization (optional)
pip install matplotlib seaborn plotly
```

All CPU-compatible. FAISS and sentence-transformers use CPU on Lucifer (GPU reserved for Ollama).

---

## Recommended execution order

### Phase 0: Foundation
1. `build_index.py` — required first
2. `ptv_to_pe.py` — convert PTV to PE format
3. `run_reduction_benchmark.py` — understand the noise floor

### Phase 1: Baselines
4. `run_linear.py` — T1 baseline quality and latency
5. `run_type_partition.py` — T2, quick win
6. `run_regex_timeseries.py` — T12, zero-dependency high signal

### Phase 2: Retrieval
7. `run_bm25.py` — keyword retrieval
8. `run_faiss.py` — semantic retrieval
9. `run_hybrid_rrf.py` — best-of-both

### Phase 3: Graph structure
10. `run_bfs_anchor.py` — first graph-native traversal
11. `run_centrality.py` — structural importance
12. `run_community.py` — emergent clusters
13. `run_kcore.py` — dense core extraction

### Phase 4: Dynamical systems ★
14. `run_lorenz_scan.py` — provenance-engine Lorenz classification
15. `run_pe_sweep.py` — find optimal ρ × τ
16. `run_icm_simulation.py` — EoH M68 allostatic model
17. `run_heat_diffusion.py` — information flow simulation

### Phase 5: Time series
18. `run_changepoints.py` — inflection detection
19. `run_granger.py` — causal biomarker relationships
20. `run_flare_clusters.py` — clinical flare identification

### Phase 6: Agent-directed ★
21. `run_react_agent.py` — full tool-using agent
22. `run_socratic.py` — inverse questioning
23. `run_sim_in_loop.py` — simulation between agent turns

### Phase 7: Composites
24. `run_full_funnel.py` — C1: maximum pipeline
25. `run_sim_first.py` — C2: dynamics-driven
26. `run_pure_structure.py` — C4: zero-NLP graph-only

---

## Strategy count

| Category | Count | Strategies |
|----------|-------|------------|
| Reduction | 14 | R1–R14 |
| Sequential/Temporal | 5 | T1–T4, T16 |
| Graph-Structural | 12 | T5–T8, T15, T20–T28 |
| Retrieval | 5 | T9–T11, T29–T33 |
| Temporal/Time-Series | 8 | T12, T14, T18, T34–T39 |
| Semantic/NLP | 6 | T13, T17, T40–T44 |
| Dynamical Systems | 9 | T45–T53 |
| Information-Theoretic | 4 | T54–T57 |
| Clinical/Domain | 5 | T19, T58–T61 |
| Agent-Directed | 7 | T62–T68 |
| Composites | 5 | C1–C5 |
| **Total** | **80** | |

---

*Filed 2026-04-13 — 2ndOpinionMD Graph Traversal Strategy*
*68 traversal strategies + 14 reduction strategies + 5 composite pipelines = 80 total approaches*
*All runnable on RTX 4050 6GB with eoh-llama-lucifer + provenance-engine*
