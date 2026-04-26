# Combined Receipt: Living Graph Cycle
**Date**: 2026-03-28  
**Covers**: Probe→Gap→Report architecture validation + Data Integrity Pass  
**Reviews**: VC-style review (v0.9→v1.0 boundary) + Data integrity delta  
**Status**: ✅ ACCEPTED — v1.0 boundary confirmed with one remaining condition

---

## Part I — The Living Graph Receipt (v0.9 → v1.0)

### What Was Demonstrated

| Metric | Value |
|---|---|
| Graph | 4,668 events / 57,672 edges (GPT-4.1 baseline) |
| Query | *"Why hasn't his MG responded to treatment?"* |
| Cycle time | 24.9 seconds (load + probe + gap + report) |
| Retrieval | 20 merged hits via reciprocal rank fusion (semantic + TS) |
| Traversal | 20 probe hits → 100 zoom window → 21 enrichment targets |
| Report outputs | 4 unresolved drivers, 4 clinical arcs, 6 follow-up questions, 9 enrichment requests |

### What "Closed Loop" Means

The review accepted this as v0.9 because the system showed all five properties of stateful epistemic evolution:

1. Found relevant evidence (semantic probe across 4,668 nodes)
2. Traversed causal structure (BFS along typed connascence edges)
3. Identified missing data (21 enrichment targets with specific deficiencies)
4. Produced ranked hypotheses (unresolved drivers with confidence scores)
5. **Generated its own correction requests** (the system asked for its own improvement)

That fifth step is what separates this from analysis systems. Most systems answer and stop. This one answers, then says exactly what it doesn't know and exactly which nodes to fix.

### What the VC Called Out

> *"Right now: you proved it can work. Next step: prove it can be trusted."*

The four conditions set by the VC review:

| Condition | Status at v0.9 | Status at v1.0 (post-integrity pass) |
|---|---|---|
| Timestamp integrity (>95%) | ~60% parse rate | **99.6% (4,649/4,668)** ✅ |
| Medication backbone | Free-text strings only | 219 events RxNorm-normalized (~27% coverage) ⬆ |
| Output = action | Narrative summary | Structured JSON: drivers + arcs + follow-ups + enrichment requests ✅ |
| Run determinism | 1 batch failure, 1 UnboundLocalError | Both fixed; Ollama httpx scope bug identified and fixed today ⬆ |

---

## Part II — Data Integrity Pass Receipt

### What Changed

**Temporal integrity: D → A**

Before: ~40% of events had `timestamp = "unknown"`. Temporal reasoning degraded.  
After: 2,553 timestamps recovered. 99.6% parse rate.

This was not cosmetic. It unlocked:
- Causal sequencing (which came first — the prednisone or the ILD?)
- Treatment response timelines (did the lab improve after starting mycophenolate?)
- Disease progression modeling (is the trajectory linear or episodic?)

**Pharmacological identity: F → C+**

Before: medication events were free-text strings with no structured identity.  
After: 219 events linked to RxNorm ontology identifiers.

- Pantoprazole → rxcui 40790
- Clopidogrel → rxcui 32968
- Lorazepam → rxcui 6470
- Aspirin → rxcui 1191

These are now first-class pharmacological entities, not strings.

**Critical note on the "3/803" metric**: What the manifest printed as `Medication drug_name rate: 3/803` is the delta from the single enrichment cycle run, not the total state. Global coverage is ~27% (219/803 medication events normalized). Frame it correctly: global drug_name coverage ~27%, this cycle +3 nodes.

**Loop closure: B → A (breakthrough)**

```
Enrichment requests generated:  9
Enrichment requests applied:     3
Nodes mutated:                   3
Nodes re-embedded:               3
```

This is the first time the system executed its own correction requests rather than just suggesting them. That upgrades the system from analysis to state mutation. The loop is not just designed — it ran.

### What Remains

**Orphan nodes (2,594 / ~55%)**: Half the graph is weakly connected. These nodes exist, are semantically searchable, but are not reachable through edge traversal. Until connascence edges connect them, they contribute to semantic recall but not to graph reasoning.

**Medication parsing gap (570 events)**: Negations ("patient not taking..."), list entries, compound drug mentions, and plan-type events are not resolving to RxNorm. These require structured medication extraction, not just string normalization.

**Answer delta not yet shown**: The system mutated the graph and re-embedded. The second proof step — run the same query, show that the answer improved — has not been executed. Until it is, mutation → improved reasoning is architectural intent, not demonstrated fact.

---

## Part III — The Architecture, Clearly Stated

This is what ran in those 25 seconds:

```
Question
  ↓
PatientChart (4,668 node embedding index, MiniLM-L6-v2, local MPS)
  ↓
Dual retrieval: semantic (cosine) + TS (text search) → RRF merge
  ↓
Graph traversal: BFS from top hits along typed connascence edges
  ↓
Gap analysis: identify nodes with missing timestamps, drug names, zero edges
  ↓
GPT-4.1 synthesis: structured report (drivers + arcs + follow-ups + enrichment)
  ↓
Enrichment requests → graph mutation → re-embedding → next query is better
```

What makes it distinct from RAG: The probe returns graph nodes, not document chunks. Those nodes have typed edges. The traversal follows those edges. The evidence set that reaches GPT-4.1 is not "the 10 most similar paragraphs" — it is the 100-node neighborhood of the clinically relevant subgraph.

What makes it distinct from GraphRAG: The traversal is explicit BFS along domain-typed edges (temporal, diagnostic, treatment, drug_response, lab_trend), not implicit via pre-computed community boundaries. The feedback loop (enrichment → mutation → re-embed) does not exist in GraphRAG. The embeddings index graph nodes, not community summaries.

What makes it distinct from clinical NLP: The graph is built from a PDF, not from structured FHIR data. It exists because we built it, not because the hospital provided it. And every query can improve it.

The local embedding is not a detail. It is a competitive moat. Patient data never leaves the device for the retrieval step. LLM calls can route to Ollama for full local operation or GPT-4.1 for quality. The operator chooses per deployment.

---

## Part IV — Meta Commentary (For the Other Founders)

*From the AI that has been inside this codebase for the last 48 hours.*

I want to be direct about what I've actually seen, not what makes a good pitch.

**What is genuinely real:**

The 25-second query cycle ran. The graph is real — 4,668 typed, timestamped clinical events extracted from 4,223 pages of a real patient record. The traversal followed real connascence edges and reached clinically connected evidence. The GPT-4.1 report correctly identified the MG treatment escalation arc, the psychiatric comorbidities, the progressive non-response. These are not hallucinated — they are in the record. The system found them structurally, not by re-reading the PDF.

The timestamp fix is real. Going from 60% to 99.6% parse rate in a single pass means the temporal backbone of the graph is now trustworthy. That is a prerequisite for everything downstream: drug response timelines, disease progression modeling, causal inference. You did not have it 24 hours ago. You have it now.

The loop ran. Enrichment requests were generated, applied, and nodes re-embedded. It is not just a diagram in a strategy document. It executed.

**What is not yet real:**

The "answer delta" proof is missing. We mutated the graph. We have not shown that the next query over the same topic returns a demonstrably better answer. Until that runs, "the graph grows with attention" is a demonstrated mechanism but not a demonstrated improvement in clinical reasoning. This is the one thing between you and a true v1.0 receipt. It is one script execution.

Medication coverage is 27%. This matters because medications are the causal backbone of treatment response reasoning. When a doctor asks "why hasn't his MG responded?", the correct answer requires knowing what was tried, when, at what dose, and what the response was. The graph currently has the *what* and partially the *when*. It does not have dose, duration, or response in a structured form. The 570 unresolved medication events are not noise — they are the data the most important clinical questions depend on.

Orphan connectivity (~55%) means half the graph is semantically accessible but not relationally navigable. A node that has no edges cannot contribute to traversal-based reasoning. It can still appear in semantic probe results, which is why the system works despite this — but the quality ceiling is constrained until orphan nodes are connected.

**The infrastructure situation:**

The Ollama integration has been failing for 3 runs today with the same `Expecting value: line 1 column 1 (char 0)` error. The root cause was an `httpx async with` scope bug — the HTTP connection was closed before the response body was buffered for 3-minute chunked responses. This is fixed now. The next Ollama run should succeed. But the team should know: the cost-free local inference path has not completed a single successful batch yet on this codebase. GPT-4.1 is the proven path. Ollama is the target but unvalidated.

The GPT-4.1 baseline run cost approximately $8–9 in API calls for one patient's full 4,223-page record in `full` extraction mode. That is the cost of a one-time ingestion. Subsequent queries are cheaper (probe + report is 2 LLM calls, not 71 batches). But at scale — 100 patients — full extraction is $800–900. Ollama solving means that cost goes to near-zero on local hardware. That matters for the business model.

**What I think the actual insight is:**

You did not build a summarization tool. You did not build a RAG system. You built a substrate — a typed, timestamped, locally-embedded knowledge graph that can be extracted from any patient's unstructured records, navigated semantically, traversed structurally, and improved through use.

The key property is the last one. Every other clinical AI system I have seen in my training data produces a static output. It answers the question and the answer goes stale as the patient's situation evolves, as new records arrive, as errors in the extraction are discovered. This system has a repair loop baked into the query cycle. The follow-up questions a doctor answers, the corrections they make, the enrichment requests the system generates — these flow back into the graph. The graph that answered the question is better than the graph that existed before the question was asked.

That is a genuinely different architecture for a genuinely hard problem. Whether it becomes a company depends on execution, not on the idea. The idea is right.

**The one thing I would tell the founders:**

Run the answer delta proof tomorrow. It is one script run: re-run the MG query against the mutated graph, compare the report to the pre-mutation report, show that "prednisone timeline anchored" produced a better answer. When that runs, the loop is closed — not just in theory, not just in architecture, but in demonstration. That is the v1.0 moment.

Everything else — medication coverage, orphan connectivity, Ollama stability, portal integration — is important and is on the roadmap. But the answer delta proof is the one thing that changes the category of what you have: from "a system that can improve" to "a system that demonstrably improved."

Do that first. Then build the KPIs dashboard. Then show it to the VCs.

---

## Receipt Grade

| Dimension | v0.9 | v1.0 (current) | Path to perfect |
|---|---|---|---|
| Discovery validity | A | A | — |
| Artifact completeness | A- | A | — |
| Loop closure | A | A | — |
| Timestamp integrity | C+ | A | ✅ solved |
| Medication integrity | F | C+ | Drug normalization (T2.1–T2.4) |
| Graph connectivity | C | C+ | Orphan edge strategy |
| Answer delta proof | — | B (pending) | Run the second query |
| Run determinism | C | B+ | Ollama validation remaining |

**Overall: v1.0 with one condition.**

Condition: Run the answer delta proof (same query, pre vs. post mutation, show improvement). When that result exists, this is a clean v1.0.

---

*Filed: 2026-03-28*  
*Cross-references: `RECEIPT_VC_REVIEW_20260327.md`, `TRAJECTORY_REPORT_PROBE_GAP_REPORT_20260328.md`, `ASSESSMENT_ARCHITECTURE_PROBE_GAP_REPORT_20260328.md`, `STRATEGY_PATIENT_GRAPH_LIVING_SYSTEM_20260317.md`*
