# STRATEGY — Graph Traversal (Core 12)

**Scope:** Patient Timeline Vision (PTV) graphs — noisy events, typed connascence, long horizons.  
**Implementation:** Python tools in `server/graph_traversal/agent_tools.py` (`graph_*` functions + `execute_graph_tool`).  
**Full research catalog:** `game_plans/GAME_PLAN_GRAPH_TRAVERSAL.md` (80+ strategies).  
**Model guidance:** Ollama Modelfiles (`server/ollama/eoh-llama3.1-8b*.Modelfile`) — concise tool manual only; do not paste this whole file into SYSTEM.

---

## Design principles

1. **Reduce first (routine queries)** — Drop structural noise (`page`, zero-edge isolates, optionally unknown timestamps) so sentence-transformers and traversal run on a **smaller, denser corpus**. This should run **before** embedding every event on **regular user queries**.
2. **Semantic retrieval defines starting nodes** — After reduction, **S11** (`graph_hybrid_search`) with **`semantic: true`** and **`event_ids: <reduced_ids>`** is the default way to get **query-aligned entry points** (initial traversal seeds). Keyword + embedding + RRF stays the fusion layer.
3. **Traverse from seeds** — **S4** (`graph_bfs_expand`) expands connascence neighborhoods from **one or many seeds** (`seed_event_ids`). Use **`restrict_to_event_ids: <reduced_ids>`** so expansion does not pull back discarded junk through edges.
4. **Budget everything** — Orchestrator enforces token caps; tools return bounded JSON.
5. **Structure as enrichment, not the front door** — Centrality / k-core / bridges (**S5–S7**) complement the semantic path when you need hubs, dense cores, or pivot events — e.g. global summaries, audit, or when the query is vague.
6. **Dynamics for governance** — **S8–S10** (Lorenz / PE geometry + sweep + deterministic governance) classify retention on a **working set** (seeds ∪ BFS ∪ top hybrid), not on the raw 7k+ graph.
7. **Receipts** — Each tool returns `tool`, `strategy_id`, `generated_at`, and counts so DerivationChain (M63) can attach provenance.

---

## Primary pipeline — “regular query” (every time)

This is the **default mental model** for a normal clinical question against a large PTV:

```
S2  graph_reduce
      → corpus = reduced event_ids (noise stripped)

S11 graph_hybrid_search
      query = user question
      event_ids = corpus        ← search ONLY within reduced graph
      semantic = true           ← sentence-transformers on subset (fast enough at ~3–4k nodes)
      → seed_candidates = top-K event_ids (RRF-ranked)

S4  graph_bfs_expand
      seed_event_ids = top 5–10 from S11
      restrict_to_event_ids = corpus
      max_depth = 2 (tune 1–3)
      → working_graph = BFS union (connascence-local context around the query)

[ optional S5 / S6 / S7 on `corpus` or `working_graph` when you need structural priors ]

S8  graph_pe_lorenz_classify   (on capped working set: seeds ∪ BFS, deduped)
S10 graph_pe_govern_adjust

S3  graph_token_budget          → pack for LLM / Ollama
```

**S1** (`graph_snapshot`) — Use on **cold start**, new patient export, or debugging; cache or skip on repeat queries in the same session if shape is unchanged.

**S12** (`graph_biomarker_icm`) — Add when the question implicates **labs, inflammatory load, or ICM-style framing** (after S2).

**S9** (`graph_pe_sweep`) — **Offline / once per graph build**, not per query — finds stable ρ×τ band for that export.

---

## Secondary path — “second look” at discarded events (later)

Reduction **intentionally** drops events (pages, isolates, sometimes unknown dates). For **audit, litigation, or recall-oriented** tasks you may need evidence that never survived S2:

- Re-run **S11** with **`event_ids` omitted** (full graph) or with a **minimal** reduce (e.g. only `drop_page`, keep isolates).
- Maintain a **`discarded_ids` list** from S2 output (orchestrator stores `dropped_sample` / full drop list) for targeted re-fetch.
- **Never silently merge** full-graph hits with reduced-graph hits in the same DerivationChain without labeling the corpus scope (`corpus_scope` in S11 output: `subset` vs `full_graph`).

Document this in the orchestrator; the tools already support **subset vs full** via `event_ids` on S11.

---

## The core 12 (strategy ID → role → tool)

| ID | Strategy | Role in default query | Tool name |
|----|-----------|------------------------|-----------|
| **S1** | Graph snapshot | Session / debug / first load | `graph_snapshot` |
| **S2** | Combined reduction | **Step 1** — define routine corpus | `graph_reduce` |
| **S3** | Token budget prune | **Last pack** before LLM | `graph_token_budget` |
| **S4** | Anchor BFS expand | **Step 3** — traverse from semantic seeds | `graph_bfs_expand` |
| **S5** | Centrality-first | Optional enrichment / global view | `graph_centrality` |
| **S6** | k-core decomposition | Optional — dense core | `graph_kcore` |
| **S7** | Bridges / articulation | Optional — narrative pivots | `graph_bridges` |
| **S8** | Lorenz / Portal classify | **Step 4** — governance on working set | `graph_pe_lorenz_classify` |
| **S9** | ρ × τ sweep | **Offline** — tune once per export | `graph_pe_sweep` |
| **S10** | Governance adjust | **Step 4** — safety on S8 | `graph_pe_govern_adjust` |
| **S11** | Hybrid retrieval | **Step 2** — seeds via keyword + **embeddings** | `graph_hybrid_search` |
| **S12** | Biomarker + ICM trace | When query/labs demand it | `graph_biomarker_icm` |

**Note:** S8–S10 align with **provenance-engine** (PyPI). Optional CLI (`pe scan`) can mirror the same geometry; in-repo RK4 + PE `classify_node` stays consistent for tests.

---

## Deprecated default (do not use as the main query path)

The older ordering **snapshot → reduce → centrality → hybrid → PE** treated **structure before semantics**. That is still valid for **exploratory** or **no-query** analytics, but **not** as the default for **question-answering**. For Q&A, **always anchor on S11(seeds) → S4(traverse)** after S2.

---

## Parameter cheat sheet

| Tool | Key arguments |
|------|----------------|
| `graph_reduce` | `drop_page`, `drop_unknown_timestamp`, `drop_isolates`, `status_in` |
| `graph_token_budget` | `event_ids`, `max_tokens`, `query`, `prefer_recent` |
| `graph_bfs_expand` | `seed_event_id` **or** `seed_event_ids`, `max_depth`, `edge_types`, `max_nodes`, **`restrict_to_event_ids`** |
| `graph_centrality` | `event_ids` (subset), `top_k` |
| `graph_kcore` | `event_ids`, `k`, `max_nodes` |
| `graph_bridges` | `event_ids`, `max_bridges` |
| `graph_pe_lorenz_classify` | `event_ids`, `rho`, `tau`, `steps` |
| `graph_pe_sweep` | `sample_nodes`, `rho_values`, `tau_values` |
| `graph_pe_govern_adjust` | `items` (from S8) |
| `graph_hybrid_search` | `query`, `top_k`, **`semantic`** (default true), **`event_ids`** (reduced corpus) |
| `graph_biomarker_icm` | `biomarkers`, `ic_max` |

---

## Sandbox alignment

`sandbox/norman_graph_retrieval/run.py` follows **reduce → hybrid (semantic, reduced corpus) → multi-seed BFS (restricted) → PE → budget** unless flags say otherwise. See that folder’s README.

---

## Version

- **v1.1 — 2026-04-14** — Core 12 frozen; primary pipeline = reduce → S11 subset semantic → S4 restricted BFS.
- **v1.0 — 2026-04-14** — Initial agent tool surface.
