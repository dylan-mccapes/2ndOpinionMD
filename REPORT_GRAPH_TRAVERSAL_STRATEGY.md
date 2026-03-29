# Graph Traversal Strategy for PatientTimelineVision

**Date:** 2026-03-29
**Context:** Agent-driven investigation of a 4,223-page patient timeline graph
**Status:** Phase 1-3 IMPLEMENTED — topology primitives, ClinicalArc, traversal primitives, agent manifest

---

## 1. Problem Statement

The PatientTimelineVision graph, once built from a multi-thousand-page medical record, contains hundreds or thousands of clinical events connected by connascence edges (temporal, causal, diagnostic, treatment, lab_trend, symptom_cluster, caused_by, confounded_by). The detective stream needs to systematically investigate this graph to surface diagnostic mysteries, treatment contradictions, and missed connections.

The current traversal strategy is **reactive retrieval**: per detective step, semantic search + text search + BFS from top results. This answers "what in the graph is relevant to this question?" but does not answer "what in the graph has nobody looked at yet?" or "what is the shape of this patient's clinical story?"

The graph needs a **strategic traversal protocol** — one that maps the territory before exploring it, tracks what's been explored, and leaves a continuation manifest so the next agent invocation picks up where the last one left off.

---

## 2. Current Architecture

### 2.1 Graph Structure (`patient_timeline_vision.py`)

```
PatientTimelineVision
├── patient_id: str
├── events: Dict[str, TimelineEventVision]
│   └── TimelineEventVision
│       ├── event_id: str
│       ├── event_type: diagnosis | lab | medication | procedure | symptom | visit | imaging | flare | note
│       ├── timestamp: str (ISO or clinical date)
│       ├── preview: str (1-2 sentence summary)
│       ├── discovered_by: List[str] (provenance chain)
│       ├── status: included | excluded | uncertain
│       ├── connascence: Dict[str, List[str]]  (edge_type → [target_event_ids])
│       └── annotations: Dict[str, Any]  (flexible metadata incl. causal_mechanisms, confounders, edge_provenance)
└── metadata: Dict[str, Any]
```

### 2.2 Current Traversal (`patient_timeline_chart.py`)

**Embedding model:** `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions).
Each graph node is embedded as `event_type | timestamp | preview | drug:{name}`.
Embeddings are stored in-memory (numpy) or Postgres (`ehr.patient_graph_chart`, pgvector).

Per detective step, `build_graph_context_docs()`:

1. **Semantic search** — `chart.search(step_q, top_k=15)` — cosine similarity against all embedded nodes
2. **Text search** — `graph_ts_search(vision, step_q, limit=15)` — brute-force term-match over `preview + event_type`
3. **Reciprocal rank fusion** — `reciprocal_rank_fusion(sem_ids, ts_ids, k=60)` — merge both ranked lists, take top 15
4. **BFS expansion** — `graph_traverse(vision, eid, depth=2)` from top 5 merged results, filtered by edge types (diagnostic, treatment, drug_response, lab_trend, temporal, causal, symptom_cluster)
5. Cap at 25 nodes, group by `event_type` → inject as individually citable structured context docs with event counts, edge counts, and up to 10 chronologically sorted events per type

**Key property:** The 384d embeddings encode node *content* (what it says), not node *topology* (where it sits in the graph). Two nodes with identical clinical text but in different arcs will be near-neighbors in embedding space. Semantic search is content-aware but structure-blind.

### 2.3 Enrichment (`graph_enrichment.py`)

- **Ingestion enrichment**: heavy, per PDF batch during ingest — extracts events + edges
- **Opportunistic enrichment**: lighter, per detective step — adds new events, edges, causal annotations, confounder annotations

### 2.4 What Exists That's Good

- `snapshot()` — lightweight graph shape (type counts, date ranges, median gaps, per-node edge summaries)
- `iter_connascence_edges()` — denormalized edge list for LLM agents
- `get_connascent_events()` — single-hop neighborhood by kind
- `graph_traverse()` — BFS with edge-type filtering and depth control
- `reciprocal_rank_fusion()` — multi-signal merge
- Bidirectional edges with provenance (`add_edge()` with `discovered_by` + `metadata`)
- Causal and confounder annotation protocol (opportunistic enrichment)

---

## 3. What's Missing

### 3.1 The Graph Has No Shape (No Hierarchy)

A diagnosis event and a routine lab draw have the same structural weight. There is no concept of "clinical arc" — a named subgraph that represents a diagnostic thread (e.g., "RA diagnostic journey," "cardiac events," "hepatic function monitoring"). The events exist but the macro structure is invisible.

**Impact:** The agent can't see the forest. Every investigation starts from scratch, re-discovering the same arcs via expensive LLM calls.

### 3.2 No Strategic Traversal

The current approach is question-driven: each detective step retrieves what's locally relevant. There is no protocol for:

- **Territory mapping** — what are the major clinical arcs in this graph?
- **Coverage tracking** — which arcs have been explored and which haven't?
- **Systematic cross-arc analysis** — where do treatment decisions in arc A produce symptoms in arc B?
- **Gap hunting** — where are the silences in the record?

**Impact:** The detective stream may spend all its steps in the densest part of the graph and never touch the sparse regions where diagnostic mysteries often hide.

### 3.3 No Continuation Protocol

When a chat completion ends, the agent's working state evaporates. Opportunistic enrichment writes new events/edges, but there is no structured record of:

- What the agent explored and concluded
- What hypotheses were formed
- What questions remain open
- What the next agent invocation should prioritize

**Impact:** Each detective run starts from zero strategic context. The graph grows (events + edges) but the investigation state doesn't persist.

### 3.4 BFS Is the Only Traversal Primitive

BFS from a seed node is good for local neighborhood exploration. But a diagnostic investigation also needs:

- **DFS along a temporal spine** — trace a single clinical thread from first event to last
- **Cross-arc edge walking** — systematically follow edges that bridge different clinical arcs
- **Priority-weighted traversal** — follow causal edges before temporal edges
- **Negative-space detection** — identify expected events that don't exist

---

## 4. Proposed Architecture

### 4.1 New Data Structures

#### Clinical Arcs

Add to `PatientTimelineVision`:

```python
@dataclass
class ClinicalArc:
    arc_id: str                          # e.g., "ra_journey", "cardiac", "hepatic"
    name: str                            # Human-readable: "RA Diagnostic Journey"
    event_ids: List[str]                 # Member events
    date_range: Tuple[str, str]          # (first_date, last_date)
    summary: str                         # 2-3 sentence arc summary
    status: str                          # "unexplored" | "partial" | "complete"
    open_questions: List[str]            # Unanswered questions about this arc
    cross_arc_edges: List[Dict[str, Any]]  # Edges that connect to other arcs
```

#### Agent Manifest

Add to `PatientTimelineVision.metadata`:

```python
agent_manifest = {
    "last_updated": "ISO timestamp",
    "arcs_identified": int,
    "exploration_state": {
        "arc_id": {
            "status": "unexplored | partial | complete",
            "explored_through": "date or event_id",
            "summary_so_far": "what the agent learned",
            "open_questions": ["..."],
        }
    },
    "cross_arc_findings": [
        {
            "from_arc": "arc_id",
            "to_arc": "arc_id",
            "finding": "description",
            "confidence": 0.0-1.0,
            "evidence_event_ids": ["..."],
        }
    ],
    "frontier": [
        "Natural-language description of what to explore next",
    ],
    "hypotheses": [
        {
            "hypothesis": "description",
            "supporting_event_ids": ["..."],
            "contradicting_event_ids": ["..."],
            "confidence": 0.0-1.0,
            "status": "active | confirmed | refuted | superseded",
        }
    ],
    "next_traversal_strategy": "description of recommended approach for next invocation",
}
```

### 4.2 New Graph Algorithms (Pure Python, No LLM)

These are topology operations that run on the graph structure itself. They should be cheap enough to run at the start of every detective stream invocation.

#### 4.2.1 Topology Scan

```python
def topology_scan(vision: PatientTimelineVision) -> Dict[str, Any]:
    """
    The 'MRI' of the graph. Runs before any LLM call.
    
    Returns:
        - connected_components: list of component sizes + sample event_ids
        - orphan_events: events with zero connascence edges (suspicious)
        - hub_events: top-20 events by degree (clinical pivots)
        - temporal_gaps: date ranges > N days with no events (record silences)
        - edge_type_distribution: counts by connascence type
        - density: edges / (nodes * (nodes-1))
    """
```

#### 4.2.2 Temporal Gap Detection

```python
def detect_temporal_gaps(
    vision: PatientTimelineVision,
    min_gap_days: int = 90,
) -> List[Dict[str, Any]]:
    """
    Find silences in the timeline.
    
    Returns list of gaps:
        - gap_start: last event before gap
        - gap_end: first event after gap
        - gap_days: duration
        - surrounding_context: events immediately before/after
    """
```

#### 4.2.3 Connected Component Analysis

```python
def connected_components(vision: PatientTimelineVision) -> List[List[str]]:
    """
    Find disconnected subgraphs.
    
    Isolated components may indicate:
        - Events from a separate care system not yet linked
        - A clinical thread that was never connected to the main narrative
        - Orphan data from PDF extraction errors
    """
```

#### 4.2.4 Hub Detection

```python
def find_hubs(
    vision: PatientTimelineVision,
    top_k: int = 20,
) -> List[Tuple[str, int, Dict[str, int]]]:
    """
    Find highest-degree events (most connascence edges).
    
    High-degree events are clinical pivots:
        - A diagnosis that connects to dozens of labs, meds, and symptoms
        - A hospitalization that links multiple arcs
        - A medication change that cascades across the timeline
    
    Returns: (event_id, total_degree, {edge_type: count})
    """
```

### 4.3 Arc Extraction (One LLM Call)

After the topology scan, one LLM call partitions the graph into named clinical arcs. Input: the topology scan results + `snapshot()` + the top-50 hub nodes with previews. Output: a list of `ClinicalArc` objects.

This is **graph coarsening** — contracting clusters of events into named super-nodes. Instead of traversing 800 events, the planner works with 8-12 arcs.

```python
async def extract_clinical_arcs(
    vision: PatientTimelineVision,
    topology: Dict[str, Any],
) -> List[ClinicalArc]:
    """
    LLM-powered arc extraction.
    
    Prompt pattern:
        "Given this graph topology and these hub events, partition the
         timeline into named clinical arcs. Each arc represents a
         diagnostic thread, treatment journey, or organ-system story."
    
    Single call. Result cached on the graph as vision.arcs.
    """
```

### 4.4 Traversal Primitives

#### 4.4.1 DFS Along Temporal Spine

```python
def dfs_temporal_spine(
    vision: PatientTimelineVision,
    arc: ClinicalArc,
) -> List[TimelineEventVision]:
    """
    Trace an arc's events in chronological order.
    
    Unlike BFS (which radiates outward from a seed), this follows the
    temporal thread of a single clinical story from start to finish.
    
    The agent uses this to build a narrative: "First this happened,
    then this, then this diverged..."
    """
```

#### 4.4.2 Cross-Arc Edge Walking

```python
def walk_cross_arc_edges(
    vision: PatientTimelineVision,
    arcs: List[ClinicalArc],
) -> List[Dict[str, Any]]:
    """
    Find all edges that connect events in different arcs.
    
    These are the highest-value edges in the graph:
        - Treatment in arc A → side effect attributed to arc B
        - Lab trend in arc A deteriorates when arc B treatment escalates
        - Diagnosis in arc A shares symptoms with arc C
    
    Returns: list of cross-arc edges with arc labels and edge metadata.
    """
```

#### 4.4.3 Priority-Weighted Traversal

```python
def priority_traverse(
    vision: PatientTimelineVision,
    seed_event_id: str,
    max_nodes: int = 30,
) -> List[str]:
    """
    Traverse from a seed, following highest-value edges first.
    
    Priority order:
        1. caused_by / confounded_by  (causal signal — most valuable)
        2. diagnostic                  (supports/contradicts a diagnosis)
        3. treatment / drug_response   (treatment-outcome link)
        4. lab_trend                   (longitudinal measurement)
        5. symptom_cluster             (pattern grouping)
        6. temporal                    (proximity — least specific)
    
    This ensures the agent follows the most clinically meaningful
    paths first, not just the closest-in-time events.
    """
```

#### 4.4.4 Negative-Space Detection

```python
def detect_negative_space(
    vision: PatientTimelineVision,
    arcs: List[ClinicalArc],
) -> List[Dict[str, Any]]:
    """
    Identify expected-but-absent patterns.
    
    Heuristics:
        - Diagnosis event with no follow-up labs within 90 days
        - Medication started with no efficacy assessment within 6 months
        - Abnormal lab with no repeat or clinical response
        - Referral mentioned in a note with no corresponding visit
        - Arc that goes silent for >6 months then reappears
    
    These are the gaps where diagnostic mysteries often live.
    """
```

### 4.5 Continuation Protocol

At the end of every detective stream invocation, the agent writes a structured **agent manifest** back to the graph:

```python
async def write_agent_manifest(
    vision: PatientTimelineVision,
    manifest: Dict[str, Any],
) -> None:
    """
    Write the continuation state to vision.metadata["agent_manifest"].
    
    The manifest records:
        1. Which arcs were explored and their status
        2. What hypotheses were formed (with supporting/contradicting evidence)
        3. What cross-arc findings were made
        4. What questions remain unanswered (the frontier)
        5. What traversal strategy the next invocation should use
    
    The graph is the agent's persistent working memory.
    The manifest is the tape head position.
    """
```

At the start of every invocation:

```python
async def read_agent_manifest(
    vision: PatientTimelineVision,
) -> Optional[Dict[str, Any]]:
    """
    Read the continuation state from the previous invocation.
    
    If present, the planner uses this instead of starting from scratch:
        - Skip arc extraction if arcs are already identified
        - Resume from the frontier instead of re-mapping territory
        - Prioritize open questions over general exploration
    """
```

### 4.6 Modified Detective Stream Flow

```
CURRENT:
  load graph → snapshot → plan steps → per-step: (semantic search + BFS) → answer → enrichment

PROPOSED:
  load graph → read manifest → topology scan
    ├── first run: extract arcs → write manifest
    └── subsequent: read arcs from manifest
  → plan steps (arc-aware, frontier-aware)
  → per-step:
      ├── choose traversal strategy (DFS spine / cross-arc / priority / BFS)
      ├── retrieve graph context via chosen strategy
      ├── answer with graph evidence
      └── enrichment (events + edges + causal + confounders)
  → update manifest (exploration state, hypotheses, frontier)
  → write manifest back to graph
  → save graph to Postgres
```

---

## 5. Implementation Plan

### Phase 1: Topology Primitives (no LLM, no schema changes)

Add to `patient_timeline_vision.py`:

| Function | Complexity | Dependencies |
|----------|-----------|--------------|
| `topology_scan()` | O(V+E) | None |
| `detect_temporal_gaps()` | O(V log V) | `parse_clinical_date` |
| `connected_components()` | O(V+E) | None (BFS) |
| `find_hubs()` | O(V+E) | None |

These are pure graph algorithms. They can ship immediately and start providing value in logging/diagnostics even before the detective stream uses them.

### Phase 2: Arc Structure + Extraction

Add `ClinicalArc` dataclass and `arcs` field to `PatientTimelineVision`. Add `extract_clinical_arcs()` — one LLM call. Modify `snapshot()` to include arc summary when arcs exist.

### Phase 3: New Traversal Primitives

Add to `patient_timeline_chart.py`:

| Function | Purpose |
|----------|---------|
| `dfs_temporal_spine()` | Trace an arc chronologically |
| `walk_cross_arc_edges()` | Find inter-arc connections |
| `priority_traverse()` | Follow highest-value edges first |
| `detect_negative_space()` | Find expected-but-absent patterns |

### Phase 4: Agent Manifest + Continuation Protocol

Add manifest read/write to `PatientTimelineVision`. Modify `eoh_detective_stream_event_generator` to:
- Read manifest at start
- Choose traversal strategy based on manifest state
- Write manifest at end

### Phase 5: Planner Integration

Modify `eoh_detective_planner` to accept arc summaries and manifest frontier as input (instead of raw snapshot). The planner becomes arc-aware: it plans steps that systematically cover unexplored arcs and prioritize the frontier.

---

## 6. Design Principles

1. **The graph is the agent's working memory, not just its input.** The agent reads from and writes to the graph. Investigation state persists across context windows.

2. **Map before you explore.** Topology scan + arc extraction before any clinical reasoning. Know the shape of the territory before walking it.

3. **Arcs are the unit of clinical reasoning.** Individual events are too granular. The whole graph is too coarse. Arcs are the right abstraction for both the agent and the clinician.

4. **Cross-arc edges are the highest-value signal.** Within an arc, the clinical story is usually coherent. The diagnostic mysteries live in the interactions *between* arcs — where treatment for condition A produces symptoms attributed to condition B.

5. **Negative space is evidence.** The absence of expected follow-up, the silence in the record, the test that was never ordered — these are often more informative than what's present.

6. **Every traversal adds to the graph.** The agent doesn't just read the graph and produce text. It writes back: arc labels, exploration state, hypotheses, questions. The graph only grows toward better clinical understanding.

7. **Continuation over repetition.** The manifest means the second detective run doesn't repeat the first. It picks up the frontier and pushes further. Each run is additive.

---

## 7. Relationship to Existing Code

| Existing | Proposed | Relationship |
|----------|----------|-------------|
| `snapshot()` | `topology_scan()` | Topology scan extends snapshot with structural analysis |
| `graph_traverse()` (BFS) | `dfs_temporal_spine()`, `priority_traverse()` | New traversal primitives alongside BFS |
| `build_graph_context_docs()` | Arc-aware context builder | Reads arc structure to choose traversal strategy |
| `enrich_graph_opportunistic()` | + manifest writing | Enrichment continues; manifest adds investigation state |
| `eoh_detective_planner()` | + arc/manifest input | Planner sees arcs and frontier instead of raw events |
| `PatientTimelineVision.metadata` | + `agent_manifest`, `arcs` | New fields on existing structure |

No existing code is replaced. Every proposed addition extends what's already there. The current reactive retrieval path remains as a fallback and as one tool in the traversal toolkit.

---

## 8. Implementation Status

### Phase 1-3: IMPLEMENTED (2026-03-29)

All proposed primitives are now live in the codebase. Here is what was added:

#### `patient_timeline_vision.py` — new structures and graph algorithms

| Addition | Type | Description |
|----------|------|-------------|
| `EDGE_PRIORITY` | Module constant | Priority ranking for edge types (caused_by=100 → temporal=10) |
| `ClinicalArc` | Dataclass | Named subgraph: arc_id, name, event_ids, date_range, summary, status, open_questions, cross_arc_edges |
| `PatientTimelineVision.arcs` | Field | `Dict[str, ClinicalArc]` — persisted with to_dict/from_dict |
| `topology_scan()` | Method | Structural MRI — components, orphans, hubs, temporal gaps, density, edge distribution |
| `connected_components()` | Method | BFS-based component detection, sorted largest-first |
| `find_hubs(top_k)` | Method | Top-k highest-degree events with per-edge-type breakdown |
| `detect_temporal_gaps(min_gap_days)` | Method | Find record silences with before/after context |
| `dfs_temporal_spine(event_ids)` | Method | Chronological traversal of an arc's events |
| `priority_traverse(seed, max_nodes)` | Method | Follow highest-value edges first (causal before temporal) |
| `walk_cross_arc_edges()` | Method | Find all edges that cross arc boundaries |
| `detect_negative_space()` | Method | Identify dx-without-labs, meds-without-response, and other expected-but-absent patterns |
| `read_agent_manifest()` | Method | Read continuation state from metadata |
| `write_agent_manifest(manifest)` | Method | Write investigation state to graph metadata |
| `set_arc(arc)` | Method | Add/replace a clinical arc |
| `event_arc_map()` | Method | Event→arc mapping dict |

#### `patient_timeline_chart.py` — new strategic retrieval

| Addition | Type | Description |
|----------|------|-------------|
| `build_arc_context_docs(vision, arc)` | Function | Build context docs for a single arc's DFS temporal spine |
| `build_cross_arc_context_docs(vision)` | Function | Build context docs from cross-arc edge analysis |
| `build_priority_context_docs(vision, seed_id)` | Function | Build context docs via priority-weighted traversal from a seed event |

#### Backward compatibility

- `PatientTimelineVision.arcs` defaults to `{}` — existing graphs load fine
- `from_dict` / `to_dict` handle missing `arcs` key gracefully
- All existing functions (`build_graph_context_docs`, `graph_traverse`, etc.) unchanged
- New functions are additive — nothing replaced, nothing broken

### Phase 4: TODO — Wire into detective stream

Next step: update `rag_stream_detective.py` to:
1. Call `topology_scan()` at detective start → include in planner context
2. Run `detect_negative_space()` → feed gaps as investigation targets
3. Use `build_arc_context_docs()` / `build_priority_context_docs()` when step question targets a specific arc or event
4. Call `write_agent_manifest()` after each step to persist exploration state
5. Read `read_agent_manifest()` at start to support continuation across sessions

### Phase 5: TODO — LLM-powered arc extraction

Add `extract_clinical_arcs()` — an LLM call that reads the topology scan and snapshot, then produces `ClinicalArc` instances. This is the bridge from structure to meaning. Requires a prompt template and integration into the ingestion pipeline after graph building completes.

---

*"The graph only grows toward better clinical understanding."*
