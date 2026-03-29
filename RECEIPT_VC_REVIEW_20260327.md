# Receipt: VC-Style Review → Engineering Action Plan
**Date**: 2026-03-27  
**Source review**: GPT-4.1 baseline run (`artifacts/timeline_full_20260327_1717`)  
**Reviewer lens**: a16z Bio + Lux Capital + General Catalyst Health

---

## Actual Run Stats (GPT-4.1 Baseline)

| Metric | Value |
|---|---|
| Input | 4,223 pages, 6,098,806 chars |
| Events extracted | 4,668 raw → 4,675 after enrichment |
| Edges final | 57,682 (post connascence + temporal) |
| LLM batches | 24 extraction + 7 connascence |
| Batch failures | 1 (connascence diagnostic batch 1/4 — `JSONDecodeError` truncation) |
| Artifact write failure | 1 (`_run_timeline_enrichment_gap_synthesis_connascence` UnboundLocalError, fixed) |
| Run duration | ~51 minutes (17:17 → ~18:08) |
| Timestamp parse failures | ~40% (~1,946 of 4,817 events had `"unknown"` timestamp) |

> **Note**: The VC review cites 4,817 events / 97,160 edges from an earlier run with wider temporal windows (30/90-day). This run reflects the tightened 7/14-day cap and MAX_TEMPORAL_NEIGHBORS=10. Edge counts are now domain-signal rather than combinatorial noise.

---

## VC Verdict Summary

> *"Would I invest? Yes — with conditions."*

**Conditions filed:**

1. Fix timestamp integrity (existential — the core axis is time)
2. Build medication backbone (causal inference is broken without it)
3. Add an output/action layer (graphs are not decisions)
4. Achieve run determinism (infra risk kills deals)

---

## Engineering Action Plan (Filed as Receipt)

### Priority 1 — Timestamp Integrity (NON-NEGOTIABLE)
**VC quote**: *"You are building a GPS. 40% of coordinates are wrong."*

**Root cause**: LLM-extracted events use free-text date strings. The pipeline stores whatever the LLM outputs. `_parse_ts()` in `patient_timeline_vision.py` is the only downstream guard, and it silently marks failures as `None`.

**Current state**:
- ~1,946 events have `timestamp = "unknown"` 
- These events still exist in the graph and receive temporal edges — they just cluster at the graph periphery
- `_infer_temporal_connascence` uses `_parse_ts()` and skips `None` → these events get zero temporal edges

**Tasks**:

- [ ] **T1.1 — Multi-format timestamp parser** (`patient_timeline_vision.py`, `_parse_ts`)  
  Support: `MM/DD/YYYY`, `Month DD YYYY`, `DD-Mon-YYYY`, `YYYY-MM`, relative phrases (`"2 weeks post-op"`), and partial dates (`"March 2022"` → `2022-03-01`). Use `dateutil.parser` with fallback regex. Target: **>95% parse success**.

- [ ] **T1.2 — LLM extraction prompt hardening** (`timeline_summarizer.py`, `_extract_events_from_pages_batch`, system prompt)  
  Add explicit instruction: *"Timestamp MUST be the most specific date visible in this exact page's text. Acceptable formats: YYYY-MM-DD, MM/DD/YYYY, Month YYYY. Never return 'unknown' if any date appears in the text, even a year alone."*

- [ ] **T1.3 — Timestamp audit metric in output artifacts**  
  Add to `PatientTimelineVision.save()` output: `"timestamp_stats": {"parse_ok": N, "parse_fail": N, "parse_rate": 0.xx}`. Surface this in the run log so every run shows the parse rate.

- [ ] **T1.4 — Post-extraction timestamp repair pass**  
  After all 71 batches complete, collect all events with `timestamp = "unknown"`. Make a single batched LLM call with surrounding page context to attempt date recovery. Feasible because the timeline text is already in memory.

---

### Priority 2 — Medication Backbone
**VC quote**: *"meds = causality backbone. Without this, graph = incomplete causal system."*

**Current state**:
- `medication` is one of the 6 event types extracted by the LLM, but medications are treated identically to diagnoses in the graph — no structured schema for dose, duration, route, adherence
- The run summary explicitly flagged *"Medication exposures are poorly documented"*
- No `drug → temporal alignment` edges exist (only generic temporal proximity)

**Tasks**:

- [ ] **T2.1 — Structured medication schema** (`patient_timeline_vision.py`, `TimelineEvent`)  
  Add optional fields: `drug_name: Optional[str]`, `dose: Optional[str]`, `route: Optional[str]`, `duration_days: Optional[int]`, `adherence_flag: Optional[bool]`. These should be populated by the extraction LLM when visible in the page text.

- [ ] **T2.2 — Medication extraction prompt enrichment** (`timeline_summarizer.py`, system prompt)  
  Extend the `medication` event schema in the extraction prompt to include: `"drug_name"`, `"dose"`, `"route"`, `"duration_days"`. The LLM already sees this information — we're just not capturing it.

- [ ] **T2.3 — Drug-outcome connascence type** (`patient_timeline_vision.py`, `CONNASCENCE_*` constants)  
  Add `CONNASCENCE_DRUG_RESPONSE = "drug_response"`. In the connascence rubric, define: if a lab or symptom event follows a medication start within 30 days AND is clinically related (same system), emit a `drug_response` edge with `direction` = `"positive"` / `"negative"` / `"unclear"`.

- [ ] **T2.4 — Medication timeline view**  
  Add a `get_medication_timeline()` method to `PatientTimelineVision` that returns chronological medication events with their dose/duration, enabling a standalone meds-only summary.

---

### Priority 3 — Output = Action
**VC quote**: *"You produce graphs and summaries. Not decisions."*

**Current state**:
- The pipeline ends at `TimelineSummaries` (narrative text + graph JSON)
- There is no structured output that says "here are the 3 unresolved clinical drivers"
- The EoHD question is answered narratively, not structurally

**Tasks**:

- [ ] **T3.1 — Top-N unresolved drivers output** (`timeline_enrichment_synthesis_agent.py`)  
  After enrichment synthesis, add a final structured LLM pass: *"Given this patient graph, identify the top 3 unresolved clinical drivers that most explain current trajectory. For each: driver name, supporting evidence (event IDs), confidence score (low/med/high)."*  
  Output: `TimelineSummaries.unresolved_drivers: List[UnresolvedDriver]`

- [ ] **T3.2 — Diagnostic confidence score per event cluster**  
  For each connected component of `diagnostic` connascence edges, compute: (a) event count, (b) date span, (c) avg edge weight → output as `diagnostic_clusters` in the graph metadata.

- [ ] **T3.3 — Clinical arc summary** (new field in `TimelineSummaries`)  
  A structured JSON object: `{"arcs": [{"arc_name": "...", "start": "...", "end": "...", "resolution": "resolved|active|uncertain", "key_events": [...]}]}`. This is the "GPS with 95%+ coordinates" view of the patient.

---

### Priority 4 — Run Determinism
**VC quote**: *"Kill truncation, repair hacks, partial failures. You need repeatable graphs."*

**Current state** (from this run):
- Connascence batch 1/4 failed with `JSONDecodeError` (truncated JSON, `max_tokens=4096` was too small → fixed to `16_384`)
- `UnboundLocalError: gap_analysis` fired in session mode (→ fixed with `None` init)
- Ollama integration: 3 runs, 3 identical failures until httpx `async with` scope bug was identified today
- No run-to-run fingerprint / reproducibility check

**Tasks** (most already fixed, remaining):

- [ ] **T4.1 — Idempotent run fingerprint**  
  At the start of each run, hash the PDF (sha256) + extraction mode + model. Write `run_fingerprint.json` to artifact dir. On next run with same fingerprint, allow `--resume` to skip already-completed batches using the cached vision snapshot.

- [ ] **T4.2 — Connascence partial-failure recovery** (already improved with degradation tracking)  
  Currently: failed batch is logged in `vision.metadata["degradation"]` but silently skipped. Add: if `>50%` of batches fail, raise `RuntimeError` instead of producing a degraded graph. Add `--allow-degraded` flag to override.

- [ ] **T4.3 — Ollama production readiness** (in progress)  
  Current blocker: `httpx async with` scope bug fixed today. Remaining validation:
  - Confirm `options.num_ctx=65536` is actually applied (check Ollama logs for `Metal KV buffer size = 8192.00 MiB`)
  - Validate first 3 batches produce non-empty JSON responses
  - Add `--trace-http` flag to pipeline for request/response debugging (already in CLI, propagate to `_ollama_chat_direct`)

- [ ] **T4.4 — Streaming validation test**  
  Add a 1-page smoke-test script: `scripts/test_ollama_smoke.py` that sends a single 1-page batch and asserts `len(events) >= 1` and `timestamp != "unknown"`. Run before each full pipeline execution.

---

## Scorecard → Engineering Targets

| VC Dimension | Current Score | Target | Blocking Task |
|---|---|---|---|
| Vision | ⭐⭐⭐⭐⭐ | — | — |
| Technical ambition | ⭐⭐⭐⭐⭐ | — | — |
| Differentiation | ⭐⭐⭐⭐⭐ | — | — |
| Data integrity | ⭐⭐☆☆☆ | ⭐⭐⭐⭐☆ | T1.1–T1.4 |
| Reliability | ⭐⭐☆☆☆ | ⭐⭐⭐⭐☆ | T4.1–T4.4 |
| Product clarity | ⭐⭐⭐☆☆ | ⭐⭐⭐⭐☆ | T3.1–T3.3 |
| Scalability | ⭐⭐☆☆☆ | ⭐⭐⭐☆☆ | T4.1 + Ollama |

---

## What Was Actually Proved (The Signal That Survives)

Even at 60% timestamp integrity and with 1 batch failure:

- **MG + ILD co-occurrence** identified automatically from raw pages
- **Diagnostic ambiguity** (seropositive MG with atypical EMG, no unifying diagnosis) surfaced
- **Multisystem arc** (neuro → pulm → hepatic) reconstructed across a decade of records
- **Treatment non-response** (steroids, pyridostigmine, mycophenolate, IVIG, rituximab — all with limited/inconsistent response) detected as a graph pattern

> *"Signal survives noise. That is what investors look for."*

The VC is right. The graph is already producing medical insight at P1 quality despite P3 data integrity. The ceiling is extraordinary once P1 (timestamps) is fixed.

---

## Immediate Next Run Target

Fix T1.2 (prompt hardening) + T1.3 (audit metric) first — these are changes to the extraction prompt and artifact output, zero infrastructure risk. Run a new GPT-4.1 baseline and check if timestamp parse rate improves from ~60% to >85% with prompt alone before investing in the multi-format parser (T1.1).

```bash
# After T1.2 + T1.3 are implemented:
python3 -u scripts/run_eohd_timeline_pdf.py \
  ../data/patient_timelines/NormanEricRoberts_decrypted.pdf \
  --extraction-mode full \
  --artifact-dir "../artifacts/timeline_ts_fix_$(date +%Y%m%d_%H%M)" \
  2>&1 | tee "../artifacts/ts_fix_run_$(date +%Y%m%d_%H%M).log"
# Check: grep "timestamp_stats" artifacts/ts_fix_*/patient_timeline_vision_*.json
```
