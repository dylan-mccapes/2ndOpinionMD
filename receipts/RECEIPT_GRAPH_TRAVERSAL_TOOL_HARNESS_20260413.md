# RECEIPT: Graph Traversal Strategy, Tool Arsenal, and Agent Harness

**Date:** 2026-04-13  
**Scope:** Core-12 graph tools, STRATEGY v1.1 pipeline (reduce → semantic hybrid → BFS → Lorenz → govern → token budget → PE cross-check), Norman sandbox + per-tool **eoh-llama-lucifer** harness, context packaging, final synthesis handoff.  
**Status:** **Work complete** — fully tested harness and tool behavior; **git commit deferred** until a run confirms **final synthesis** completes cleanly (or failure receipt is acceptable for the release cut).

---

## Strategy stance (confirmed)

**Using sentence-transformers inside `graph_hybrid_search` on the reduced corpus, then feeding hybrid hits as BFS seeds (with `restrict_to_event_ids` = reduced set), remains the right default.** Keyword-only hybrid is a fast fallback; the full core-12 toolbox stays available for experiments, ablations, and future orchestrators.

This receipt captures both that opinion and the **fully wired, testable** path so the team can rely on one pipeline while still knowing every strategy ID exists in code.

---

## Deliverables (code + docs)

### Graph tools (`server/graph_traversal/agent_tools.py`)

- **`graph_hybrid_search`:** optional `event_ids` subset (post-reduce semantic search).  
- **`graph_bfs_expand`:** `seed_event_ids` + `restrict_to_event_ids` for multi-seed BFS on the subgraph.  
- **`GRAPH_TOOL_DEFINITIONS`:** aligned with the above.

### Semantic visibility

- **`_semantic_rank`** returns explicit skip reasons when `sentence-transformers` or `numpy` is missing (`requirements-dev.txt` excludes ST by design).  
- Hybrid tool surfaces a **`note`** instead of silently returning `sem=0`.

### Harness (`sandbox/norman_graph_retrieval/tool_agent_harness.py`)

- Default rounds: **S2 → S11 (subset + semantic) → S4 → S8 → S10 → S3** → native **provenance_engine** cross-check.  
- **Per-round Ollama** analysis with bounded JSON + **`context_nodes`** (PTV previews, edges, optional `tool_row` hints).  
- **Structured console logs** (`[tool-harness]`, timings, metrics).  
- **Inspection `.log`:** full tool args + raw results + LLM text per round.  
- **JSON artifacts:** `result_summary` enriched with context nodes; optional `--full-tool-json`.  
- **Ollama preflight** (`GET /api/tags`) when agent is on.  
- **Final synthesis** block: `response`, `suggested_nodes`, `suggested_nodes_with_full_context` (`ptv_full`).  
- **Failure-safe final step:** never crashes the run — **`ok: false`** receipt with `traceback_excerpt`, `candidate_event_ids_sample`, etc.; **graph rounds always saved**.

### Supporting modules

- `server/graph_traversal/ollama_local.py` — chat + **tags/preflight**.  
- `server/graph_traversal/tool_result_summary.py` — cap large lists for prompts.  
- `server/graph_traversal/agent_node_context.py` — resolve **event_ids → compact nodes** for LLM context.  
- `server/eoh/__init__.py` — lazy `eoh_llm_router` to avoid import side effects in sandbox.

### Scripts & docs

- `sandbox/norman_graph_retrieval/scripts/RUN_TOOL_AGENT_HARNESS.sh` — venv + `pip install -r requirements-dev.txt` + `PYTHONPATH` + pass-through args.  
- `sandbox/norman_graph_retrieval/README.md` — env, semantic deps, WSL/Ollama URL, harness flags.  
- `reports/STRATEGY_GRAPH_TRAVERSAL.md` — v1.1 pipeline narrative (referenced during implementation).

---

## Why the “full arsenal” still matters

The harness **exercises one opinionated path** end-to-end. The **same module** still exposes snapshot, centrality, k-core, bridges, biomarker ICM, PE sweep, etc. That gives you:

- Regression targets when changing **reduce** or **hybrid** semantics.  
- Optional steps (`--extra-rounds` JSON) without forking the codebase.  
- A single place to compare **in-repo Lorenz** vs **native provenance-engine** classify.

---

## How to run (canonical)

From repo root, venv active, `PYTHONPATH=.`:

```bash
pip install -r requirements-dev.txt 'sentence-transformers>=3'   # semantic hybrid
python sandbox/norman_graph_retrieval/tool_agent_harness.py \
  -q "YOUR QUERY" \
  --max-json-chars 24000
```

Or: `./sandbox/norman_graph_retrieval/scripts/RUN_TOOL_AGENT_HARNESS.sh -q "YOUR QUERY"`  
(add ST install once if using semantic hybrid).

**Outputs:** `sandbox/norman_graph_retrieval/out/tool_agent_harness_<utc>.json` + matching `.log`.

**Skip LLM entirely:** `--no-agent` (tools + PE only; no final synthesis).

**Skip closing synthesis only:** `--no-final-synthesis` (keeps per-round agent).

---

## Git / release gate (explicit)

- **Hold git** until at least one representative run finishes **final synthesis** successfully *or* the team accepts shipping with **documented failure receipts** only.  
- No further feature work is required for this receipt’s scope; follow-ups are **demo-grade final curation** (weaker model, self-judge of context) on top of `rounds` + `final_synthesis` / receipts.

---

## Sign-off note

The **test harness** is the receipt for **behavior**: logs + JSON prove what ran. The **strategy** receipt is: **semantic hybrid seeds BFS on the reduced graph**; everything else is ammunition in the same arsenal.
