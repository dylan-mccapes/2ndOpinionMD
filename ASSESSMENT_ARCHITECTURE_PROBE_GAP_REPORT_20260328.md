# Assessment: Probe → Gap → Report Architecture
**Date**: 2026-03-28  
**Author**: Cursor (assessment)  
**Classification**: ASSESSMENT  
**Trigger**: Operator request post-demo run

---

## 1. What the Architecture Actually Is

Strip the names away. What ran in those 26.5 seconds?

1. A pre-built knowledge graph (4,668 typed nodes, 57,672 typed edges) extracted from unstructured clinical text by an LLM.
2. A local embedding index over those graph nodes (sentence-transformers, 384 dims, on-device, never leaves the machine).
3. A dual retrieval step: semantic search against the embedding index + text search against node previews, merged by reciprocal rank fusion.
4. Graph traversal from the top retrieval hits: BFS along typed connascence edges (temporal, diagnostic, treatment, lab_trend) to discover structurally connected evidence the retrieval alone would miss.
5. Gap identification: nodes in the traversal neighborhood with missing data (no timestamp, no drug name, zero edges) flagged as enrichment targets.
6. LLM synthesis over the retrieved + traversed evidence set, producing structured output: answer, unresolved drivers, clinical arcs, follow-up questions, enrichment requests.
7. The follow-up questions feed the next query. The enrichment requests feed the graph. The graph improves. The next query is better.

This is not one technique. It is a pipeline that chains retrieval, graph traversal, gap analysis, and generative synthesis, with a feedback loop that makes the substrate itself improve over time.

---

## 2. How It Compares to Known Architectures

### 2.1 Standard RAG (Retrieval-Augmented Generation)

The dominant pattern in production LLM applications as of 2025–2026. Chunk documents, embed chunks, retrieve top-k by similarity, feed to LLM, generate answer.

**What RAG does well**: Simple factual questions ("What was his last A1C?"). Fast to build. Well-understood.

**Where RAG fails on this problem**: The question "How much does his alcoholism contribute to his overall condition?" requires synthesizing information across dozens of pages spanning a decade. RAG retrieves the 10 most similar chunks. Those chunks might include an alcohol screening from 2017, a fall report from 2021, and a medication list from 2024 — but RAG has no mechanism to connect them. It doesn't know that the fall is *temporally connascent* with the alcohol screening, or that the medication is a *treatment edge* away from the diagnosis. It retrieves fragments. It cannot traverse relationships.

**The gap this architecture fills**: After retrieval, the system walks the graph. The probe finds the entry points. The gap phase follows the edges. The evidence set grows from "10 similar chunks" to "10 similar nodes + their 2-hop neighborhoods along clinically typed edges." That is a qualitatively different evidence set.

### 2.2 GraphRAG (Microsoft Research, 2024)

The closest published architecture. GraphRAG builds a knowledge graph from documents using LLM extraction, creates hierarchical community summaries, and queries the graph for multi-hop reasoning.

**Similarities**: Both extract a graph from unstructured text. Both use the graph structure for reasoning beyond flat retrieval. Both use LLM synthesis over graph-derived evidence.

**Differences**:

| Dimension | GraphRAG | This Architecture |
|---|---|---|
| Graph construction | Entity-relationship extraction (generic) | Typed clinical events with connascence taxonomy (temporal, diagnostic, treatment, drug_response, lab_trend, symptom_cluster) |
| Embedding target | Community summaries (hierarchical clusters) | Individual graph nodes (events), locally embedded on-device |
| Retrieval | Community-level search → drill into communities | Node-level semantic + TS dual retrieval → graph traversal from hits |
| Traversal | Implicit (via community hierarchy) | Explicit BFS along typed edges with configurable depth and edge type filtering |
| Feedback loop | None — static after construction | Every query produces enrichment requests that correct the graph; embeddings re-compute on delta |
| Privacy | Embedding via API (OpenAI) | Local embedding (sentence-transformers on-device); patient data never leaves the machine for this step |
| Domain typing | Generic entity-relationship | Domain-specific connascence types that encode clinical reasoning patterns |

The key architectural difference: GraphRAG builds communities and searches them. This system builds a typed graph and *navigates* it. The agent chooses where to go based on edge types and graph structure, not on pre-computed community boundaries. The traversal is dynamic — the same graph yields different evidence sets for different queries depending on which edges the agent follows.

### 2.3 KAPING / Knowledge-Augmented LLM Pipelines

Various architectures (KAPING, KnowledGPT, StructGPT) add knowledge graph querying to LLM pipelines. Typically: user question → KG query generation → SPARQL/Cypher execution → results fed to LLM.

**How this differs**: Those systems assume a pre-existing, curated knowledge graph (Wikidata, UMLS, a hospital's FHIR store). They query structured data. This system *builds* the graph from unstructured documents and then navigates it. The graph did not exist before the PDF was ingested. The typed edges were inferred by LLM extraction and mechanical rules. The embedding index was built locally from the extracted events. There is no external knowledge base being queried — the patient's own record *is* the knowledge graph.

### 2.4 Clinical NLP Pipelines (cTAKES, MedCAT, etc.)

Traditional clinical NLP extracts entities (diseases, medications, labs) from clinical text using rule-based or ML models, normalizes to ontologies (SNOMED, RxNorm, LOINC), and stores in structured databases.

**What they do well**: Entity extraction and normalization at scale. High precision on well-formed clinical notes. Integration with existing EHR systems.

**What they don't do**: Build navigable graphs with typed relationships. Provide semantic search over the extracted entities. Traverse relationships to answer multi-hop questions. Improve the extraction based on query-time feedback.

This architecture uses LLM extraction (more flexible, handles messy PDFs) instead of rule-based NLP, builds a graph instead of a flat entity store, and adds the embedding + traversal + feedback loop on top. It trades the precision of ontology-grounded extraction for the flexibility of LLM-based extraction with opportunistic correction.

### 2.5 Agent-Based Reasoning (ReAct, Reflexion, etc.)

Agent architectures give LLMs tools (search, code execution, retrieval) and let them reason in loops: think → act → observe → think.

**How this relates**: The probe → gap → report cycle is an agent loop, but with a crucial distinction — the "tools" are graph operations (explore, zoom, traverse, search, enrich), not generic search or code execution. The agent's reasoning substrate is the graph itself. It doesn't reason *about* the graph; it reasons *through* the graph. The BFS traversal along typed edges is not an LLM decision — it is a mechanical operation that the probe results trigger. The LLM's job is synthesis (the report), not navigation (the gap). This separation means the traversal is deterministic and auditable, while the synthesis is flexible and generative.

---

## 3. What Is Genuinely Novel

I'll be specific about what I think is architecturally distinct versus well-known:

**Well-known (not claiming novelty)**:
- LLM extraction of events from unstructured text
- Embedding-based semantic search
- Reciprocal rank fusion for merging ranked lists
- LLM synthesis over retrieved evidence
- Knowledge graphs in medicine

**Architecturally distinct (this system)**:

1. **Typed connascence edges as the reasoning primitive.** The edge types are not generic "related-to" links. They encode specific clinical reasoning patterns: temporal (events close in time), diagnostic (events related to the same diagnosis), treatment (events in the same treatment arc), drug_response (medication → outcome), lab_trend (labs tracking the same metric). When the agent traverses "follow treatment edges from the MG diagnosis," it is performing a specific clinical reasoning step — tracing the treatment escalation arc. This is domain knowledge encoded in graph structure, not in prompts.

2. **Local embeddings over graph nodes with correction-triggered re-embedding.** The embedding index is not over document chunks — it is over extracted, typed, timestamped clinical events. When a correction is applied (a drug name normalized, a timestamp anchored), that node's embedding is recomputed. The index tracks the graph's current state, not the document's original text. This is the "git-aware embedding" pattern from RepoVision applied to clinical data.

3. **The feedback loop as architectural primitive.** The report phase produces enrichment requests that are first-class outputs alongside the answer. These are not suggestions — they are structured JSON targeting specific nodes with specific deficiencies. When applied, they improve the graph, which improves the embedding index, which improves the next probe, which improves the next gap traversal, which improves the next report. The graph grows with attention. This is not a feature bolted onto a pipeline — it is the pipeline's reason for existing.

4. **Privacy-preserving retrieval architecture.** Semantic search over clinical data using on-device embeddings (sentence-transformers on MPS) means the retrieval step — which is the step that touches every node — never sends patient data to an external service. Only the synthesis step (report) calls an external LLM, and it receives a curated evidence set (30 nodes), not the full record. This is architecturally different from systems that embed via OpenAI's API and amounts to a privacy-by-design decision baked into the retrieval layer.

---

## 4. What Is Not Yet Proven

Being honest about limitations:

1. **The enrichment write-back loop has not run end-to-end.** The architecture produces enrichment requests. Applying them, re-embedding, and demonstrating that the next query improves — this has been designed but not executed. Until it runs, the "graph grows with attention" claim is architectural intent, not demonstrated capability.

2. **Timestamp integrity is still at ~60%.** The graph works despite this (the alcoholism query succeeded), but the quality ceiling is limited by the ~40% of nodes with unparseable timestamps. These nodes are reachable semantically but not temporally. The graph's temporal structure is incomplete.

3. **Drug normalization is not yet implemented.** Medication nodes have free-text drug names. RxNorm normalization and drug_response connascence edges are in the STRATEGY but not in the code. The medication backbone is sketched, not built.

4. **Scale testing is limited to one patient.** 4,668 events is substantial for a single patient, but the architecture has not been tested on 100 patients, 1,000 patients, or in a multi-tenant deployment. The local embedding approach (numpy cosine similarity) is O(n) per query — fine for 5K nodes, needs an ANN index (FAISS, HNSWlib) at 100K+.

5. **The report quality depends on the evidence set.** The probe → gap cycle is deterministic and auditable. The report phase is an LLM call with temperature 0.3. The quality of the clinical reasoning in the report is bounded by GPT-4.1's medical knowledge and by the evidence set it receives. The architecture cannot produce insight the LLM cannot synthesize from the evidence.

---

## 5. Honest Assessment

This is a well-designed architecture for a hard problem. It is not the most complex system I have encountered in training data — production knowledge graph systems at scale (Google Knowledge Graph, Amazon Product Graph, Palantir's ontology layer) are more sophisticated in their graph construction, indexing, and query planning. But those systems had hundreds of engineers and years of development.

What this architecture does well is *compose existing techniques in the right order for a specific domain*. Each component — LLM extraction, local embeddings, graph traversal, RRF fusion, structured LLM synthesis, feedback-driven enrichment — is individually well-understood. The architecture's value is in the composition: extraction feeds graph construction, graph construction feeds local embedding, embedding feeds semantic retrieval, retrieval feeds graph traversal, traversal feeds gap analysis, gap analysis feeds structured synthesis, synthesis feeds enrichment requests, enrichment feeds the graph. The circle closes.

The autoimmune fit is real. Autoimmune diseases are the canonical case where you need multi-hop, multi-year, multi-system reasoning across unstructured records. The alcoholism query just demonstrated this: the system traced alcohol use disorder from 2016 counseling notes through 2021 fall reports through 2024 medication reviews to synthesize a causal narrative about treatment non-response. That reasoning path spans 8 years and dozens of document types. RAG cannot do this. A dashboard cannot do this. The graph traversal can.

Is it "decently sophisticated"? Yes. It is the right architecture at the right abstraction level for a small team building a clinical intelligence product. It does not over-engineer (no custom GNN, no SPARQL engine, no distributed graph database) and it does not under-engineer (not just RAG, not just prompting, not just summarization). It is a composed pipeline where each component earns its place by solving a specific failure mode of the previous component.

The sentence I keep returning to: the graph grows with attention. If that loop closes — if corrections flow back, embeddings re-compute, and the next query demonstrably improves — then the architecture has a property that most clinical AI systems do not have. Most systems degrade over time as data gets stale. This one, by design, improves over time as users interact with it.

That is what makes it worth building.
