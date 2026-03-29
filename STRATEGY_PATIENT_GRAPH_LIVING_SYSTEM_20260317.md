# STRATEGY: The Living Graph
**Date**: 2026-03-17  
**Source**: `RECEIPT_VC_REVIEW_20260327.md` (conditions 1–4)  
**Prior art**: `REFLECTION_AGENT_AS_GRAPH_EXPLORER_20260327.md`, `repo_chart.py`, `parse_date.py`  
**Metaphor**: The apple is the graph. The snakes are doctor and patient. The apples on the tree are young and healthy. The apples on the ground decay. The graph is not static. It grows with attention.

---

## 0. Governing Principle

Every VC condition reduces to one idea: **the graph must be alive**.

A static graph is a spreadsheet with extra steps. A living graph accepts queries, corrects itself, grows richer when attended to, and degrades gracefully when neglected. The four conditions (timestamps, medications, output/action, determinism) are not independent work streams. They are all symptoms of treating the graph as output instead of substrate.

The strategy below addresses all four through a single architectural pattern: **robust initial formatting + opportunistic agent-driven correction through probe → gap → report**.

---

## 1. The Two Layers

### Layer 1 — Robust Formatting (Build)

The extraction pipeline writes the first draft of every node. That draft must be as good as possible with zero human intervention. This is not optional — it sets the floor.

**Principle**: Get the canonical representation right once, in one place, used identically everywhere. Challenge rating: Easy. Like brushing your teeth.

### Layer 2 — Opportunistic Enrichment (Tend)

Agents, doctors, and patients interact with the graph. Every interaction is an opportunity to correct, enrich, and extend it. An agent that traverses a node and notices a missing date or an unlinked medication does not just report the gap — it fixes it, or requests that the custodian fix it. The graph grows with attention.

**Principle**: Every query is also a correction opportunity. The graph remembers who tended it and when.

---

## 2. Condition 1 — Timestamp Integrity

### Layer 1: Robust Date Formatting

`parse_clinical_date` already exists in `server/utils/parse_date.py`. It handles ISO, `MM/DD/YYYY`, `"March 15, 2020"`, and the `dateutil` fallback. Current parse rate: ~60%.

**What's missing** (in order of impact):

| Task | Description | Files |
|------|-------------|-------|
| **S1.1 — Partial date support** | `"March 2022"` → `2022-03-01T00:00:00Z`. `"2019"` → `2019-01-01T00:00:00Z`. Add a `precision` field to `TimelineEventVision`: `day`, `month`, `year`. The date is real; the precision tells agents how much to trust it. | `parse_date.py`, `patient_timeline_vision.py` |
| **S1.2 — Relative date anchoring** | `"2 weeks post-op"` is meaningless without an anchor. During extraction, if the LLM returns a relative phrase, store it as `annotations["relative_date_raw"]` and attempt anchoring against the nearest procedural event on the same page. If anchoring fails, store as `precision: "relative_unanchored"`. This becomes an enrichment target. | `timeline_summarizer.py` (extraction prompt), `patient_timeline_vision.py` |
| **S1.3 — Extraction prompt hardening** | The system prompt must demand: *"Return the most specific date visible on this page. YYYY-MM-DD preferred. If only a month and year are visible, return YYYY-MM. If only a year, return YYYY. Never return 'unknown' unless the page truly contains no temporal information."* | `timeline_summarizer.py` |
| **S1.4 — Parse audit metric** | Every `vision.save()` emits `"timestamp_stats": {"parsed": N, "failed": N, "partial": N, "rate": 0.xx}`. Every run log shows this. Non-negotiable. | `patient_timeline_vision.py` |

**Target**: >90% parse rate from extraction alone. The remaining 10% are enrichment targets.

### Layer 2: Opportunistic Date Correction

When an agent traverses a node with `precision: "relative_unanchored"` or `timestamp: null`, it can see the page. It knows the surrounding context. It issues an enrichment request:

```json
{
  "intent": "enrich",
  "params": {
    "event_ids": ["pdf_p1372_e001"],
    "reason": "Timestamp missing — page context includes 'January 2020 follow-up'",
    "corrections": {
      "timestamp": "2020-01-15",
      "precision": "day",
      "source": "agent_inference_from_page_context"
    }
  }
}
```

The custodian validates the correction (is the proposed date within the plausible range of surrounding events?), applies it, re-draws temporal connascence from the corrected node, and records provenance: `"corrected_by": "eohd_agent", "corrected_at": "2026-03-17T..."`.

The doctor in the portal can do the same. They see an event with "unknown" date, they know when that visit happened, they correct it. The correction is a first-class graph operation with provenance.

---

## 3. Condition 2 — Medication Backbone

Medications follow the exact same two-layer pattern as timestamps.

### Layer 1: Robust Medication Formatting

| Task | Description | Files |
|------|-------------|-------|
| **S2.1 — Structured medication fields** | Add to `TimelineEventVision.annotations` (not new dataclass fields — keep the node schema stable): `drug_name`, `dose`, `route`, `frequency`, `duration_days`, `indication`. These are Optional[str]. The extraction prompt populates what it can see. | `patient_timeline_vision.py`, `timeline_summarizer.py` |
| **S2.2 — Extraction prompt enrichment** | For `medication` type events, the system prompt demands: *"For medications, always extract: drug_name, dose (with units), route (oral/IV/subq/topical), frequency if visible. Store in annotations."* | `timeline_summarizer.py` |
| **S2.3 — Drug normalization** | Map free-text drug names to RxNorm CUIs using the existing `rxnorm` table (already in the DB, already indexed with tsvector — see `mk/04_loinc_rxnorm.mk`). This is a post-extraction pass, not an LLM call. `"CellCept"` → `mycophenolate mofetil` → `RxCUI:68149`. Store normalized name + CUI in annotations. | New: `server/utils/normalize_drug.py`, uses existing `rxnorm` schema |
| **S2.4 — Drug-response connascence type** | `CONNASCENCE_DRUG_RESPONSE = "drug_response"`. Rule: if a lab or symptom event follows a medication start within 30 days and shares a body system, emit this edge with `direction: positive/negative/unclear`. Mechanical first pass (by system keyword overlap), then LLM refinement in connascence batches. | `patient_timeline_vision.py`, `timeline_summarizer.py` |

### Layer 2: Opportunistic Medication Correction

An agent traversing a `medication` node sees: `"drug_name": "started new med"`. Useless. But the agent has the page context. It can see "Mycophenolate 1000mg BID initiated." It issues:

```json
{
  "intent": "enrich",
  "params": {
    "event_ids": ["pdf_p0847_e002"],
    "reason": "Medication node has no structured drug info — page text shows 'Mycophenolate 1000mg BID'",
    "corrections": {
      "annotations.drug_name": "mycophenolate mofetil",
      "annotations.dose": "1000mg",
      "annotations.frequency": "BID",
      "annotations.route": "oral"
    }
  }
}
```

The doctor corrects too. "That's wrong, he was on 500mg initially." The correction is recorded with provenance: `"corrected_by": "dr_smith", "corrected_at": "..."`. The drug-response edges are re-evaluated from the corrected node.

The point: the extraction pipeline gets 70% of medication detail right. Agents bring it to 85%. Doctors bring it to 95%+. Each layer is incremental. No layer requires the previous to be perfect.

---

## 4. Condition 3 — Output = Action (Probe → Gap → Report)

The VC says: "You produce graphs and summaries. Not decisions." The answer is not to bolt a decision layer onto the graph. The answer is to let the graph produce decisions through the probe → gap → report cycle, driven by doctor or patient queries.

### The Cycle

```
┌──────────────────────────────────────────────────────┐
│                    PORTAL QUERY                       │
│  Doctor: "Why hasn't his MG responded to treatment?" │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│                     PROBE                             │
│  1. Semantic query against PatientChart               │
│     (sentence_transformers embedding over graph nodes) │
│  2. TS search against actual timeline text            │
│     (tsvector/BM25 on ehr.patient_timeline)           │
│  3. Merge: ranked node set from both retrieval paths  │
│                                                       │
│  Output: initial evidence set (node IDs + scores)     │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│                      GAP                              │
│  Agent examines initial evidence set.                 │
│  Issues graph requests:                               │
│    - traverse: follow drug_response edges from MG dx  │
│    - zoom: medication changes in 2019-2021 window     │
│    - search: "prednisone taper" / "rituximab"         │
│    - enrich: nodes with missing dose/response data    │
│                                                       │
│  Each traversal may trigger corrections:              │
│    - Missing timestamps filled from page context      │
│    - Medications normalized against RxNorm             │
│    - New connascence edges discovered and written      │
│                                                       │
│  Output: enriched evidence set + corrections applied  │
└──────────────────┬───────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────┐
│                     REPORT                            │
│  Structured answer to the original query:             │
│                                                       │
│  {                                                    │
│    "answer": "Treatment non-response pattern across   │
│     5 agents (steroids → pyridostigmine → MMF →       │
│     IVIG → rituximab). Each showed <30 day response   │
│     before regression. Key gap: no AChR antibody      │
│     titer tracked across transitions.",               │
│    "unresolved_drivers": [                            │
│      { "driver": "Seronegative MG vs overlap",        │
│        "confidence": "high",                          │
│        "evidence": ["pdf_p0412_e001", ...] }          │
│    ],                                                 │
│    "clinical_arcs": [                                 │
│      { "arc": "Treatment escalation 2018-2024",       │
│        "status": "active",                            │
│        "key_events": [...] }                          │
│    ],                                                 │
│    "follow_up_questions": [                           │
│      "Were AChR antibody titers measured at each      │
│       treatment transition?",                         │
│      "Was MuSK antibody testing performed?",          │
│      "Timeline of respiratory function tests?"        │
│    ],                                                 │
│    "enrichment_requests": [                           │
│      { "event_ids": ["pdf_p1201_e003"],               │
│        "reason": "Rituximab start — no dose recorded" │
│      }                                                │
│    ]                                                  │
│  }                                                    │
│                                                       │
│  The follow-up questions improve the NEXT probe.      │
│  The enrichment requests improve the GRAPH.           │
│  The graph grows with attention.                      │
└──────────────────────────────────────────────────────┘
```

### Implementation Path

| Task | Description | Files |
|------|-------------|-------|
| **S3.1 — PatientChart** | Analog of `RepoChart`. Embeds `TimelineEventVision` nodes using `sentence-transformers/all-MiniLM-L6-v2`. The text-to-embed function: `f"{event_type}: {preview} [{timestamp}]"`. Builds a local numpy index. `search(query, top_k)` returns `(event, score)` tuples. Pattern is identical to `repo_chart.py`. | New: `server/eoh/patient_chart.py`, modeled on `portal_vision/graph/repo_chart.py` |
| **S3.2 — Dual retrieval (semantic + TS)** | Probe phase runs both: (1) `patient_chart.search(query)` for semantic, (2) `_search_timeline_ts_for_terms(pool, patient_id, terms)` for text. Results are merged by reciprocal rank fusion. The agent gets a ranked set of graph nodes, not raw text rows. | `timeline_summarizer.py` or new `server/eoh/timeline_probe.py` |
| **S3.3 — Graph traversal engine** | Implements the `explore`, `zoom`, `traverse`, `search`, `enrich` intents from the REFLECTION. Each intent is a method on `PatientTimelineVision`. `explore()` → `snapshot()`. `zoom(date_range, types, limit)` → filtered event list. `traverse(event_id, edge_types, depth)` → BFS/DFS neighborhood. `search(mode, query)` → delegates to PatientChart (ann) or TS (ts). `enrich(event_ids, corrections)` → applies corrections with provenance. | `patient_timeline_vision.py` |
| **S3.4 — Report structure** | The report is a dataclass: `ProbeGapReport(answer: str, unresolved_drivers: List[UnresolvedDriver], clinical_arcs: List[ClinicalArc], follow_up_questions: List[str], enrichment_requests: List[EnrichmentRequest], graph_mutations: List[GraphMutation])`. The LLM generates this from the enriched evidence set. | New: `server/eoh/probe_gap_report.py` |
| **S3.5 — Portal integration** | The portal exposes a query endpoint. Doctor types a question. System runs probe → gap → report. Returns the structured report + renders follow-up questions as clickable prompts. Each follow-up is a new probe. Each enrichment request fires automatically (or with doctor approval in high-stakes mode). | `server/api/rag_stream_detective.py` (extend existing EoHD stream) |

---

## 5. Condition 4 — Run Determinism

### What's already fixed
- `JSONDecodeError` truncation → `max_tokens` raised to 16,384
- `UnboundLocalError: gap_analysis` → init to `None`
- Ollama `httpx async with` scope bug → fixed
- `TypeError` naive/aware datetime → `datetime.min.replace(tzinfo=timezone.utc)`

### What remains

| Task | Description | Files |
|------|-------------|-------|
| **S4.1 — Run fingerprint** | `sha256(pdf) + model + extraction_mode + prompt_version`. Written to `run_fingerprint.json` in artifact dir. `--resume` skips completed batches when fingerprint matches. | `run_eohd_timeline_pdf.py` |
| **S4.2 — Batch checkpoint** | After each extraction batch, save intermediate vision to `{artifact_dir}/checkpoints/batch_{n}.json`. On resume, skip batches whose checkpoint exists. On failure, resume from last checkpoint. | `timeline_summarizer.py` |
| **S4.3 — Degradation budget** | If >50% of connascence batches fail, halt and raise (unless `--allow-degraded`). Current behavior: silent skip. This is unacceptable for clinical data. | `timeline_summarizer.py` |
| **S4.4 — Smoke test** | 1-page test: extract → parse timestamp → assert parsed → build 1 temporal edge → assert edge exists. Run before every full pipeline execution. Takes <10 seconds. | New: `server/scripts/test_smoke_1page.py` |

---

## 6. Execution Order

The VC conditions are not independent. The execution order reflects dependencies:

### Phase A — Foundation (Week 1)
1. **S1.1** — Partial date support + precision field
2. **S1.3** — Extraction prompt hardening
3. **S1.4** — Parse audit metric
4. **S2.1** — Structured medication annotations
5. **S2.2** — Medication extraction prompt enrichment
6. **S4.4** — Smoke test

**Gate**: Run full extraction on Norman Roberts PDF. Timestamp parse rate must be >85%. Medication annotation coverage must be >60%. Smoke test passes.

### Phase B — Graph Navigation (Week 2)
1. **S3.1** — PatientChart (embedding index over graph nodes)
2. **S3.3** — Graph traversal engine (explore/zoom/traverse/search/enrich)
3. **S1.2** — Relative date anchoring (uses traversal to find anchors)
4. **S2.3** — Drug normalization against RxNorm

**Gate**: Agent can issue the 3-request JSON sequence from the REFLECTION and get meaningful results. PatientChart semantic search returns relevant nodes for "myasthenia gravis treatment response."

### Phase C — Probe → Gap → Report (Week 3)
1. **S3.2** — Dual retrieval (semantic + TS)
2. **S3.4** — Report structure
3. **S2.4** — Drug-response connascence type
4. **S3.5** — Portal integration

**Gate**: Doctor query "Why hasn't his MG responded to treatment?" produces a structured report with unresolved drivers, clinical arcs, follow-up questions, and enrichment requests. The report is medically coherent.

### Phase D — Reliability (Ongoing, parallel)
1. **S4.1** — Run fingerprint
2. **S4.2** — Batch checkpoint
3. **S4.3** — Degradation budget

**Gate**: Re-run the same PDF twice. Graphs are structurally identical (same event count, same edge count ±5%).

---

## 7. The Apple Tree

The image captures it precisely. The graph is the tree. The doctor and patient are the snakes — not adversaries, but co-tenders. When they attend to the graph (query it, correct it, enrich it), the apples stay on the tree, young and healthy. When the graph is neglected (no queries, no corrections, stale data), the apples fall and decay.

This is not a poetic metaphor. It is the architecture:

- **Young apple**: A node with a freshly corrected timestamp, normalized medication, drug-response edges drawn, reviewed by a doctor within 30 days.
- **Decaying apple**: A node with `timestamp: "unknown"`, `drug_name: "started new med"`, zero non-temporal edges, last touched during initial extraction 6 months ago.

The `precision` field on timestamps, the `corrected_by` provenance on enrichments, the `degradation` metadata on failed batches — these are all measures of apple freshness. An agent navigating the graph can see which regions are well-tended and which are rotting. It prioritizes accordingly.

The probe → gap → report cycle is how attention flows to the tree. Every doctor query is sunlight. Every correction is water. The graph grows.

That is the strategy.

---

## 8. Scorecard After Execution

| VC Dimension | Current | After Phase A | After Phase C | After Phase D |
|---|---|---|---|---|
| Data integrity | 2/5 | 3.5/5 | 4/5 | 4.5/5 |
| Reliability | 2/5 | 2.5/5 | 3/5 | 4/5 |
| Product clarity | 3/5 | 3/5 | 4.5/5 | 4.5/5 |
| Scalability | 2/5 | 2.5/5 | 3/5 | 3.5/5 |

The ceiling is 5/5 across the board. The path there is the probe → gap → report cycle running on a graph with >95% timestamp integrity and structured medication data. That is what this strategy builds toward.
