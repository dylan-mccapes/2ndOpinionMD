# Strategy: Graph-Guided Timeline Summarization

**Date:** 2026-03-27  
**Status:** Phase 1 implemented; Phase 2–4 proposed  
**Context:** 2ndOpinionMD-MVP EoHD pipeline — `timeline_summarizer.py`, `patient_timeline_vision.py`

---

## The Problem with Pure Text Chunking

A 4,223-page patient record produces ~6M characters. Map-reduce over raw text has a structural flaw: each chunk is a blind slice through time. The model summarizing chunk 7 has no idea what was established in chunk 2. The reduce step is then handed 9–31 partial summaries and asked to stitch them into a coherent story — but it's working from summaries of summaries, with no provenance.

The enriched graph inverts this. It is a **typed, structured view of the entire timeline** built before the summarization even begins. It knows which diagnosis events link to which lab events. It knows the temporal chain across the full record. It is small (4,226 events + 16 edges → ~60K chars) relative to the raw text (6M chars) and fits cleanly in the reduce step's context.

---

## Phase 1: Graph as Reduce Context (Implemented)

**What was done:**

`_compact_graph_for_reduce(vision)` serializes `PatientTimelineVision` into:
```json
{
  "event_counts": {"diagnosis": 312, "lab": 1840, "note": 980, ...},
  "events_by_type": {
    "diagnosis": [{"ts": "...", "preview": "...", "connascence": {...}}, ...],
    "lab": [...],
    ...
  },
  "edges": [{"from": "evt_123", "to": "evt_456", "type": "temporal"}, ...]
}
```

This is injected as `enriched_graph` into the reduce payload. The reduce prompt instructs the model to:
- Use the graph to cross-check diagnoses and their linked lab/treatment events
- Identify temporal and causal chains not obvious from raw text
- Prefer graph provenance over raw text on conflicts

**Impact:** The reducer now has structured knowledge spanning the full timeline, not just the aggregate of 9 partial summaries. Diagnostic arcs that span multiple chunks become visible.

**Limitation:** The graph edges (connascence) are currently sparse — 16 edges for 4,226 events. The mechanical connascence rules (temporal proximity, same-medication treatment chains) fire reliably; the LLM-based diagnostic/lab_trend connascence requires the gap agent to succeed. As the gap agent matures, this gets significantly richer.

---

## Phase 2: Type-Stratified Parallel Summarization

**The idea:** Instead of chunking by time (blind slices), chunk by **event type** and run parallel summaries. Then synthesize.

```
PatientTimelineVision
    │
    ├── diagnosis events  ──→  LLM: "Diagnostic trajectory summary"
    ├── lab events        ──→  LLM: "Lab trend summary"
    ├── med events        ──→  LLM: "Medication history summary"
    ├── note events       ──→  LLM: "Clinical narrative summary"
    ├── procedure events  ──→  LLM: "Procedure / intervention summary"
    └── visit events      ──→  LLM: "Care utilization summary"
                                        │
                              Synthesize → Final EoHD summary
```

**Why this is better:**
- Each typed call is semantically coherent. The diagnostic trajectory model sees *only* diagnoses, sorted chronologically, with their connascence edges to linked labs and meds. It can tell a clean story.
- Lab trend summarization on just lab events is a solved problem (sorted by analyte, time-series reasoning).
- Parallelism: all 6 typed calls run concurrently → wall clock time drops to the slowest single call.
- The synthesizer gets 6 typed expert summaries instead of 9 time-sliced fragments.

**Implementation sketch:**
```python
async def _summarize_by_event_type(
    client, vision: PatientTimelineVision, question: str
) -> Dict[str, str]:
    type_tasks = {}
    for etype, events in vision.events_by_type().items():
        if not events:
            continue
        type_tasks[etype] = _summarize_typed_events(client, etype, events, question)
    return dict(zip(type_tasks.keys(), await asyncio.gather(*type_tasks.values())))
```

**When to trigger:** When `timeline_vision` is available with sufficient events (e.g., >200 events). Fall back to current map-reduce if graph is absent.

---

## Phase 3: Connascence-Guided Diagnostic Chains

**The idea:** Use the connascence edges to find **diagnostic chains** — sequences of events that are mechanically linked — and summarize the *chain*, not the individual events.

A chain might look like:
```
2019-03 elevated_ESR (lab)
  → 2019-04 autoimmune_workup_ordered (note)
    → 2019-06 anti-CCP positive (lab)
      → 2019-07 RA_diagnosis (diagnosis)
        → 2019-08 methotrexate_started (med)
```

This is the actual diagnostic arc. No chunk-based approach sees this unless the arc happens to fall within one chunk. The connascence graph makes it explicit.

**Implementation:**
1. Graph traversal: find connected components in the connascence edge graph.
2. For each component above a threshold size (e.g., ≥3 events), serialize the chain.
3. Pass top-N chains (by size or centrality) to the summarizer as `diagnostic_chains`.
4. The system prompt instructs the model to anchor its narrative around these chains.

**This is the highest-value upgrade.** It transforms the summary from "here is what happened in each time window" to "here is how the diagnostic story unfolded."

---

## Phase 4: Incremental Graph-First Pipeline

**The idea:** Flip the pipeline. Instead of:
```
raw text → extract events → map-reduce summary → enrich graph
```

Do:
```
raw text → extract events → enrich graph → graph-guided summary
```

The enrichment step (connascence, gap analysis, synthesis) runs *before* the summarizer, and the summarizer treats the graph as its primary input. The raw text is a fallback / evidence source, not the primary signal.

**Why this matters for EoHD:**
The EoH diagnosis system needs to reason about diagnostic axes, flares vs. noise, organ systems at stake. These are *graph properties*, not text properties. A lab flare is visible in the lab trend graph. A treatment divergence is visible in the medication connascence chain. A diagnostic mystery is visible as a high-degree event with no downstream resolution node.

**Architecture:**
```
Phase A (parallel):
  - Extract events from PDF (current batch extraction)
  - Run mechanical connascence (temporal, treatment chains)

Phase B:
  - Run LLM connascence (diagnostic, lab_trend) on extracted graph
  - Run gap agent on enriched graph

Phase C (new):
  - Run type-stratified summaries (Phase 2)
  - Run chain summarization (Phase 3)
  - Synthesize into final EoHD summary
```

---

## Current State vs. Target State

| Dimension | Current (Phase 1) | Target (Phase 4) |
|-----------|------------------|-----------------|
| Chunk count | ~9 (was 31) | 6 typed + 1 synthesis |
| Graph in summary | Yes (reduce context) | Yes (primary input) |
| Diagnostic chains | No | Yes (Phase 3) |
| Parallelism | Sequential map | Parallel by type |
| Connascence density | ~16 edges / 4,226 events | ~10–50x richer with tuned gap agent |
| Summary quality | Chronological story | Causal + typed + chain-anchored |

---

## Immediate Next Steps

1. **Run current Phase 1** and inspect the reduce output — does the graph context measurably change the reducer's output? Look for: more specific diagnostic arc descriptions, lab trends referenced by name, medication chains identified.

2. **Tune gap agent** — the connascence density (currently 16/4226 ≈ 0.4%) is too low. The diagnostic and lab_trend connascence are LLM-based and need prompt tuning to fire more aggressively.

3. **Implement Phase 2** (type-stratified parallel calls) — this is ~100 lines of code and gives the largest quality improvement per line.

4. **Instrument** — after each run, log: chunk count, graph edge density, reduce payload size, and a manual quality score. Build a before/after comparison using the Norman Roberts record.

---

## One-Line Summary

The enriched graph is a compressed, typed, relationship-aware view of the entire patient timeline. Feeding it to the reducer is Phase 1. Replacing raw text chunking with typed graph traversal is the endgame.
