# RECEIPT: PTV Toolkit Harness Run — eoh-llama-lucifer (8B, 4-bit, 16K ctx)

**Graph:** Indexed real EHR sample (`PTV_REAL_EHR_20260423.json`, 632 events; patient id UUID in artifact; historically the Norman Eric Roberts sample path in internal docs).

**Date:** 2026-04-23

**Run:** 10-probe test suite (drug lookup, ICD count, labs 2016, free-text kidney trouble, RxNorm, BFS workup, meds window, event types, overview, etc.)

**Artifacts (machine-readable):**  
`artifacts/ptv_toolkit_runs/run_20260423T223250Z_eoh-llama-lucifer/` — `turns.jsonl`, `summary.json`, `summary.md`, `handoffs/*.handoff.json`

**Companion (technical index):**  
`receipts/RECEIPT_PTV_TOOLKIT_HARNESS_20260423.md`

---

## Overall score: **Strong / pilot-ready**

The local 8B Llama **performed very well** — better than expected for a quantized on-box model on real, messy EHR-shaped data and a strict JSON tool loop.

| Metric | Result | Notes |
|--------|--------|--------|
| Plans emitted | 10/10 (100%) | Protocol held: plan first, then tools, then `final_answer` |
| **Primary tool match** | **10/10 (100%)** | **Key success metric** — correct first tool every time |
| Any tool used correctly | 10/10 (100%) | Full toolkit exercised across the suite |
| Final answer with **valid** `evidence_event_ids` | 9/10 (90%) | One question did not emit `final_answer` before turn cap (q05); see weaknesses |
| Keyword match in final answer | 7/10 (70%) | Rubric is substring-based; also reflects synthesis drift |
| Plan `route` match (vs gold enum) | 8/10 (80%) | Two “misses” are **label** mismatch (`list_event_types` / `graph_stats` vs canonical `orient`), not wrong tools |

**Wall time:** ~932 s for the full suite (first full-graph sentence-transformer encode + Ollama turns); repeat runs on the same graph hash reuse the embedding cache.

---

## Honest breakdown

### Strengths (impressive at 8B)

- **Tool selection was excellent.** It reliably opened with `code_index_lookup` for drugs/ICDs/RxNorm, `temporal_scan` for date windows, and `semantic_search` + `bfs_expand` for free-text clinical questions.
- **Retrieval was solid** for many probes: hydrocodone administrations, I10 events, 2016 labs, chronic low back pain context, kidney-related surfacing — aligned with the indexed `metadata.code_index` and event text.
- **Deterministic loop worked.** Plan → tool → evidence → `final_answer` structure held for **nine** of ten questions end-to-end.
- **Indexed graph paid off.** Flat `code_index` (drugs / rxnorm / icd / labs / loinc) plus no noisy arcs made lookups predictable — the design goal for the 8B retrieval layer.

### Weaknesses (fixable / expected at 8B)

- **Synthesis drift** (keyword rubric ~70%). Some finals mixed in narrative not asked for (e.g. orientation or type-count questions bleeding in unrelated themes). Typical small-model “helpfulness” when compressing tool payloads.
- **Two plan-route enum mismatches** (q08, q10): model used `list_event_types` / `graph_stats` as `plan.route` instead of gold `orient`. Tools and answers were still sensible; tighten gold or widen allowed route labels.
- **q05 (RxNorm 857002):** `code_index_lookup` ran correctly but the run ended at **`max_turns_reached`** with **`final_answer`: null** — not merely parse noise on a recovered path. Mitigations: raise `--max-turns`, stricter “one JSON object, balanced braces” in the probe prompt, or host-side JSON repair for truncated `tool_call` lines.
- **Evidence id hygiene:** some cited ids in prose are malformed (`*_generic`, truncated `pdf_p…_e00` patterns). Harness scoring only checks membership in the graph’s real `event_id` set; a **70B gap** pass should reject or rewrite bogus ids before the report agent.

---

## Bottom line

**The 8B is good enough for the pilot probe layer:** it exercised every major toolkit component (`code_index_lookup`, `temporal_scan`, `semantic_search`, `bfs_expand`, `graph_stats`, `list_event_types`, `get_event`) and, when it finished, usually tied answers to real event ids. That is **strong** for a local 4-bit 8B on a Victus-class GPU.

Remaining gaps — **q05 closure**, **synthesis polish**, **strict evidence ids** — are exactly what a **70B gap / report** stack is for. FORWARD/RISE-style pilots can treat this 8B layer as **retrieval + curation**, not the final clinical voice.

---

## Recommendations (next steps)

1. **Keep this harness + handoff schema** for regression runs when the graph builder or Modelfile changes.
2. **70B as final synthesizer** — consume `handoffs/*.handoff.json` working sets; validate ids; strip drift.
3. **Quick engineering wins**
   - Bump `--max-turns` for short factual code questions (or branch: if a single tool result fully answers the question, force `final_answer` next).
   - Relax plan-route gold for `orient` ↔ `graph_stats` / `list_event_types`.
   - Optional packaging polish from earlier notes: metadata/indexes wrapper, long-preview truncation at export.

---

*Filed as the narrative receipt for the successful nascent run summarized in `summary.md` / `summary.json` under `run_20260423T223250Z_eoh-llama-lucifer`.*
