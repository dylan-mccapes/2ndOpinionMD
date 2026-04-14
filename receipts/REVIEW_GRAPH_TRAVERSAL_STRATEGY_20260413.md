# REVIEW: Graph Traversal Strategy — Nascent Harness Findings

**Date:** 2026-04-13  
**Author:** Architecture review (automated)  
**Scope:** Evaluation of the reduce → temporal reduce → semantic seeds → BFS core pipeline and the agentic probe harness, based on the nascent `tool_agent_harness` run against Norman's 7,705-event PTV and the Grok-20 query set design.  
**Hardware baseline:** RTX 4050 laptop (Lucifer), eoh-llama3.1-8b q4_K_M, 6 GB VRAM  
**Target:** RTX 40909 fleet (8B agents), 70B reasoning agent (on-prem RISE study)

---

## 1. The Flagship Pipeline

The core traversal strategy that emerged from iterative development is:

```
structural reduce  →  temporal reduce  →  semantic hybrid search  →  BFS expand
     (S2)                (S2+temporal)         (S11)                   (S4)
```

This four-step spine handles the vast majority of clinical questions against a large PTV graph. Everything after it — Lorenz classification, governance adjustment, token budgeting, PE cross-check — is curation and packaging, not discovery.

### 1.1 Structural Reduce (S2)

**What it does:** Drops structural noise — page-break artifacts, zero-edge isolates, optionally events with unparseable timestamps. On Norman's graph: 7,705 → 3,705 events (52% noise removal).

**Verdict:** Non-negotiable first step. The 4,000 dropped events are page separators and orphaned PDF artifacts that would poison every downstream operation. This runs in under 5 ms and should never be skipped. The reduced corpus becomes the universe for all subsequent work.

**Observation from the nascent run:** The 52/48 signal-to-noise ratio is typical for PDF-ingested medical records. Expect similar or worse ratios on longer timelines. The fact that half the events are structural garbage validates reduce-first as the only sane default.

### 1.2 Temporal Reduce (S2 + temporal window)

**What it does:** Applies a time window on top of structural reduce. In the nascent run: `recent_years=1.0`, `anchor=latest_in_corpus` → 3,705 → 146 events. A 96% further reduction.

**Verdict:** This is the single highest-leverage step in the pipeline. Going from 3,705 to 146 events means hybrid search and BFS operate on a focused, manageable corpus. The embedding comparisons are faster, the BFS neighborhoods are tighter, and the LLM context stays within budget.

**Prediction: temporal will be requested on the majority of the Grok-20 queries.** Looking at the query set:

| Queries that naturally demand temporal windowing | Count |
|--------------------------------------------------|-------|
| Q04 — "major flare periods in the last 15 years" | explicit window |
| Q09 — "changepoints that precede worsening" | recent chapter focus |
| Q11 — "before and after starting major RA medications" | two-window comparison |
| Q12 — "highest stability vs instability periods" | multi-window sweep |
| Q16 — "longest gaps in laboratory monitoring" | temporal gap detection |
| Q18 — "A1c trended over time" | longitudinal with recency bias |
| Q20 — "signal vs noise across 39-year record" | full span, but temporal chunking helps |

At least 7 of 20 queries (35%) have an explicit temporal dimension. Several more (Q01, Q03, Q05, Q15) implicitly benefit from temporal focus even though they don't name a window. An agent that can call `graph_reduce` with `recent_years` has a massive advantage over one that searches the full 3,705-node corpus blind.

**On the 4090 fleet:** With faster inference, the agent can afford to call temporal reduce more than once — e.g., a 5-year window for context, then a 1-year window for recent events, comparing the two. This two-pass temporal strategy is infeasible on the 4050 at ~60s per LLM round but becomes practical at 4090 speeds.

### 1.3 Semantic Hybrid Search (S11)

**What it does:** sentence-transformers (MiniLM-L6-v2) embeddings + keyword matching, RRF-fused, restricted to the reduced corpus. In the nascent run: 146 events → 30 merged hits (5 keyword, 30 semantic).

**Verdict:** The semantic component is doing the heavy lifting. Keyword matching found only 5 hits for "CRP and joint symptoms"; the embedding model found 30. Without semantic search, the BFS seeds would be sparse and keyword-biased. The RRF fusion ensures that exact-match terminology (lab codes, medication names) still surfaces even when the embedding model can't distinguish them from generic clinical language.

**Critical design decision confirmed:** Running hybrid search on the *reduced* corpus (not the full 7,705) is correct. The first run loaded sentence-transformers in ~7.5s (cold start with HF weight download). On a warm cache with 146 events, embedding + ranking is negligible. On 3,705 events it would still be fast, but the temporal reduce makes every subsequent hit more relevant.

**The 30-seed count is generous.** For BFS expansion from a 146-event corpus, even 10–15 seeds would likely cover the relevant neighborhoods. The harness defaults to `top_k=20` in the agentic probe; this is a reasonable sweet spot. The agent can always request more seeds by calling hybrid search again with different terms.

### 1.4 BFS Expand (S4)

**What it does:** Multi-seed breadth-first search through connascence edges, restricted to the reduced corpus. In the nascent run: 30 seeds → 87 expanded events (depth 2).

**Verdict:** BFS is the connascence-aware step — it follows typed edges (temporal, causal, medication-symptom, lab-diagnosis) to pull in the *neighborhood* around seed events. The `restrict_to_event_ids` parameter is critical: without it, BFS would re-introduce the 4,000 noise events through edge traversal.

**87 events from 30 seeds is a healthy expansion ratio (~2.9x).** This means the average seed has 2–3 connascence neighbors within the reduced corpus. The working set of 87 events is small enough for Lorenz classification (milliseconds) and rich enough to contain the clinical narrative around each seed.

**Edge type filtering matters for the agentic harness.** The agent can call BFS with `edge_types: ["temporal"]` to trace the timeline forward/backward from a seed, or with no filter to explore all connascence types. This gives the agent genuine strategic choice — follow time, follow causality, or follow everything.

---

## 2. Pipeline Performance (Nascent Run)

| Step | Tool time | LLM time | Events in → out |
|------|-----------|----------|-----------------|
| Structural reduce | 4.8 ms | 65.0 s | 7,705 → 3,705 |
| Temporal reduce | 49.3 ms | 61.4 s | 3,705 → 146 |
| Hybrid search | 7,537 ms | 62.6 s | 146 → 30 seeds |
| BFS expand | 0.3 ms | 53.5 s | 30 → 87 |
| Lorenz classify | 1,080 ms | 84.2 s | 87 → 99 classified |
| Govern adjust | 0.2 ms | 71.0 s | 99 → 99 governed |
| Token budget | 0.6 ms | 43.3 s | 99 → 30 packed |
| PE cross-check | 220.2 ms | 78.7 s | 99 → 99 cross-checked |
| **Total** | **~8.9 s** | **~519 s** | |

**The bottleneck is entirely LLM inference.** Deterministic graph operations take under 9 seconds total (7.5s of which is cold-loading sentence-transformers). The 8B model on a 4050 averages ~65s per round. The pipeline itself is essentially free.

**On the 40909 fleet:** Even a conservative 5x inference speedup would bring per-round LLM time to ~13s, making a full 8-round pipeline complete in ~2 minutes instead of ~9.5. The agentic harness with 6 tool rounds per query would take ~1.5 minutes per query, making the full Grok-20 suite feasible in ~30 minutes.

**On the 70B reasoning agent:** The curated context handoff from the 8B agents is designed for exactly this split. The 8B agents do the graph traversal — cheap, parallelizable, query-specific. The 70B agent receives a confidence-scored bundle of 10–30 primary event IDs with full PTV rows and an explanation of what the evidence contains. The 70B never touches the raw graph.

---

## 3. The Agentic Probe Architecture

The agentic harness (`agentic_probe_harness.py`) represents a significant architectural advancement over the fixed pipeline. Instead of executing a predetermined sequence, the LLM agent dynamically selects tools based on the query and accumulated evidence.

### 3.1 What Works Well

**Iterative evidence accumulation.** Each round, the agent sees:
- The original clinical query (persisted across turns)
- The latest tool result with enriched context nodes (preview text, connascence counts, Lorenz classifications)
- A running inventory of all event IDs collected so far
- A round budget with strategic nudging

This gives the agent genuine agency. For Q07 ("highest degree centrality hubs"), the agent can skip hybrid search entirely and go straight to `graph_centrality`. For Q04 ("flare periods in the last 15 years"), it can call temporal reduce with `recent_years=15`, then hybrid search, then BFS — a pipeline that the fixed harness cannot express.

**Robust JSON normalization.** The `normalize_agent_tool_json` function handles the reality that 8B models emit varied JSON formats. It silently corrects `connascence_type` → `edge_types`, strips temporal args from Lorenz calls, and accepts OpenAI-style function wrappers. This is not a hack — it is a necessary adapter layer between a probabilistic text generator and a deterministic tool executor.

**Curated context handoff.** The `final_answer` structure with `curated_context` (confidence, explanation, primary_event_ids) is the right abstraction for the 8B → 70B handoff. The 8B agent's job is to navigate the graph and select evidence; the 70B agent's job is to reason clinically over that evidence. The confidence score and explanation give the 70B agent calibration metadata that raw event IDs cannot provide.

### 3.2 Predicted Agent Behavior on the Grok-20

For most queries, the agent will likely converge on a variant of the flagship pipeline:

**High-frequency pattern (estimated 12–14 of 20 queries):**
```
graph_reduce (temporal window)  →  graph_hybrid_search  →  graph_bfs_expand  →  final_answer
```

This covers: Q01, Q02, Q03, Q04, Q05, Q09, Q10, Q11, Q15, Q16, Q17, Q18.

**Structural exploration pattern (estimated 4–5 queries):**
```
graph_centrality / graph_kcore / graph_bridges  →  graph_bfs_expand  →  final_answer
```

This covers: Q06, Q07, Q13, Q14.

**Provenance/governance pattern (estimated 2–3 queries):**
```
graph_reduce  →  graph_pe_lorenz_classify  →  graph_pe_govern_adjust  →  final_answer
```

This covers: Q12, Q19, Q20.

**Biomarker-specific (estimated 1–2 queries):**
```
graph_reduce  →  graph_biomarker_icm  →  graph_hybrid_search  →  final_answer
```

This covers: Q08, Q09.

### 3.3 Where the 8B Model Will Struggle

**Multi-step temporal comparison queries.** Q11 ("Compare treatment response patterns before and after starting major RA medications") requires the agent to: (1) identify when methotrexate/prednisone started, (2) run temporal reduce for the pre-period, (3) run temporal reduce for the post-period, (4) compare results. An 8B model may collapse this into a single hybrid search and miss the comparative structure.

**Queries requiring negative evidence.** Q16 ("longest gaps in laboratory monitoring") asks the agent to find *absence* of events — periods where labs were *not* ordered. The graph tools return what exists, not what is missing. The agent needs to infer gaps from timestamp distributions, which requires multi-step reasoning that may exceed the 8B's capacity.

**Lorenz parameter sensitivity.** Q20 ("What does Lorenz classification reveal about signal versus noise?") requires the agent to interpret KEEP/EVICT/REVIEW distributions meaningfully. The 8B model in the nascent run produced serviceable but shallow analysis of Lorenz output ("8 EVICT, 35 KEEP, 56 REVIEW"). A 70B model would provide more nuanced interpretation of what the classification geometry reveals about the patient's record quality.

---

## 4. Hardware Scaling Expectations

### 4.1 RTX 40909 (8B agents)

The 40909 represents approximately a 5–10x inference throughput improvement over the 4050 for q4_K_M 8B models, depending on batch size and context length. Expected per-round latency: 8–15 seconds (vs 43–84s on the 4050).

**Implications:**
- Full Grok-20 suite with agents: ~25–40 minutes (vs ~3+ hours on the 4050)
- Agent can afford more rounds per query (8–10 instead of 4–6)
- Multi-pass temporal strategies become practical
- The normalization layer becomes less critical as the model has more capacity for correct JSON output (though should be retained as defense-in-depth)

### 4.2 70B Reasoning Agent (RISE Study)

The curated context handoff is sized correctly for a 70B model:
- Primary event IDs: 10–30 events with full PTV rows
- Each PTV row: ~200–500 tokens (preview text + metadata)
- Total context per query: ~3,000–15,000 tokens
- 70B context window: 128K tokens (llama 3.1 70B)

This leaves massive headroom for the 70B to receive context from multiple 8B probes, cross-reference them, and produce a comprehensive clinical assessment. The confidence scores from each 8B probe give the 70B a reliability prior: a probe with confidence 0.85 on "CRP-joint correlation" and 0.4 on "dietary triggers" tells the 70B where to focus its reasoning.

---

## 5. Strategic Recommendations

### 5.1 Confirmed Defaults

1. **Structural reduce is mandatory.** Never skip it. The cost is negligible (5 ms) and the noise reduction is essential.
2. **Temporal reduce should be the default second step** for any query with a temporal dimension (estimated 60–70% of real clinical questions). Default to `recent_years=2.0` unless the query specifies otherwise. The agent should be encouraged to call it proactively.
3. **Semantic hybrid search is the correct seed generator.** Keyword-only is insufficient for clinical language variability. The MiniLM embedding model is fast enough on reduced corpora.
4. **BFS with `restrict_to_event_ids` is the correct expansion strategy.** Unrestricted BFS would re-introduce noise. The connascence edges in the PTV provide typed relationships that BFS can follow selectively.

### 5.2 Areas for Investment

1. **Temporal reduce parameter tuning.** The current default of `recent_years=1.0` is aggressive for a 39-year record. Consider a tiered default: 2 years for "current status" queries, 5 years for "trend" queries, full span for "historical" queries. The agent should be taught to choose based on query semantics.
2. **Two-pass temporal for comparative queries.** For "before/after" questions (Q11), the agent should be coached to run reduce twice with different windows and compare working sets. This is the biggest gap between the fixed pipeline and what a smart agent could do.
3. **Negative evidence detection.** The current tool surface has no explicit "find gaps" tool. Consider adding a `graph_temporal_gaps` tool that identifies periods without events of a specified type (e.g., "lab results" or "clinic visits"). This would directly serve Q16 and similar monitoring-gap queries.
4. **Confidence calibration.** The 8B model's confidence scores in `curated_context` are currently uncalibrated — the model guesses a number. On the 40909 fleet, consider running multiple probes per query with different strategies and using agreement as a confidence signal.

### 5.3 What Not to Change

1. **Do not merge structural tools into the agent's decision loop.** Structural reduce is infrastructure, not strategy. It should remain a pre-processing step that runs once per session.
2. **Do not increase `max_context_nodes` beyond 48.** The 8B model's attention degrades with more than ~50 context entries. Better to have 48 well-chosen nodes than 200 poorly attended ones.
3. **Do not remove the normalization layer.** Even when the 40909 models produce better JSON, the normalization layer is cheap insurance against prompt drift, model updates, and edge-case outputs.

---

## 6. Verdict

The reduce → temporal reduce → semantic seeds → BFS pipeline is the right default for clinical Q&A against large PTV graphs. It is fast (under 10 seconds for all deterministic operations), effective (transforms 7,705 noisy events into 30–87 focused, connascence-linked clinical events), and composable (the agentic harness can call each step conditionally based on query semantics).

The nascent run on Norman's graph confirms that the pipeline produces clinically relevant output: CRP lab results, joint symptom events, medication changes, and their connascence neighborhoods — exactly what a downstream reasoning agent needs to answer "CRP and joint symptoms."

The agentic probe harness, with its iterative tool selection, working set tracking, and curated context handoff, is ready for the Grok-20 evaluation. The 40909 fleet will make it fast enough for production-scale probing. The 70B reasoning agent will receive well-structured, confidence-scored evidence bundles that respect its context window and give it the provenance metadata to reason transparently.

**The strategy is sound. Ship it.**

---

## Appendix: File Inventory

| File | Role |
|------|------|
| `server/graph_traversal/agent_tools.py` | Core-12 tool implementations |
| `server/graph_traversal/agent_node_context.py` | PTV node → compact context for LLM prompts |
| `server/graph_traversal/tool_result_summary.py` | Cap tool output size for prompt budget |
| `server/graph_traversal/ollama_local.py` | Ollama chat (single-turn + multi-turn) |
| `server/ollama/eoh-llama3.1-8b-lucifer.Modelfile` | 8B model persona + tool contract |
| `sandbox/norman_graph_retrieval/tool_agent_harness.py` | Fixed-pipeline harness (flagship v1.1) |
| `sandbox/norman_graph_retrieval/agentic_probe_harness.py` | Agentic probe harness (dynamic tool selection) |
| `sandbox/norman_graph_retrieval/grok_20_queries.json` | 20 clinically meaningful evaluation queries |
| `game_plans/STRATEGY_GRAPH_TRAVERSAL.md` | Strategy document (Core-12, primary pipeline) |
| `receipts/TOOL_ANGENT_HARNESS_NASCENT_RUN.sh` | Nascent run output + executive summary |
| `receipts/RECEIPT_GRAPH_TRAVERSAL_TOOL_HARNESS_20260413.md` | Tool harness delivery receipt |
