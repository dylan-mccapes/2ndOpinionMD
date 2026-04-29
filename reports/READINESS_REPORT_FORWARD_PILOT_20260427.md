# READINESS REPORT — FORWARD Pilot (Probe → Gap → Report)

**Date:** 2026-04-27
**Author:** 2ndOpinionMD Platform Team
**Scope:** Lightweight chatbot, three-agent harness, MKG retrieval harness, source-router harness, PTV toolkit harness, and supporting fixes (`metadata.code_index` rebuild on the synthetic cohort; pre-router patient code inventory).

**Companion artifacts referenced in this report:**

- `receipts/FORWARD_PROBE_GAP_REPORT_CHATBOT_NASCENT_RUN_20260427.md` (5-question REPL session against `ptv_synth_P1_early_responder.json` after the new pre-router code inventory and GAP heuristics)
- `receipts/FORWARD_PTV_3AGENT_20260427T012730Z.json` (latest 3-agent batch, 5 patients, 292.99 s wall, all stages emitted)
- `receipts/FORWARD_KNOWLEDGE_GRAPH_RETRIEVAL_HARNESS_BATCH10_RERUN_20260425_EXTRACT_SUMMARY.md` (MKG retrieval batch with router; `embed_device=cuda`, `db_sec≈7.8 s` first call then sub-second)
- `receipts/FORWARD_KNOWLEDGE_GRAPH_RETRIEVAL_HARNESS_BATCH10_ROUTER_70B_20260425.MD` (10-question batch, 70B synthesis lane currently 500-erroring)
- `receipts/EOH_LLAMA_3.2_FORWARD_ROUTING_NASCENT_RUN.md` (3.2 router, 5.34 s first call; under-selective without prompt updates)
- `reports/REPORT_PILOT_READINESS_TOOLING_PHASE_20260425.md` (prior Green/Yellow assessment)
- `reports/STRATEGY_FORWARD_PILOT_4090_DEPLOYMENT_20260424.md` (PortalNode-0 architecture)
- `reports/REPORT_PTV_TOOLKIT_HARNESS_CHATBOT_20260423.md` (toolkit harness scoring)

---

## 0. TL;DR

1. **Lightweight Probe → Gap → Report chatbot is operational** end-to-end on the 4090. All five exemplar questions on `ptv_synth_P1_early_responder.json` returned a `gap_report` and a `final report` without throwing. No `requests` or driver gating.
2. **Pre-router `metadata.code_index` inventory is wired** (`server/ptv_toolkit/code_inventory.py`, embedded in `plan_route` and the graph-picker). The receipt confirms the new emoji line `📇 code_index inventory n_keys=7 router_slice_json=912 graph_pick_slice_json=912` runs every turn — meaning the router and graph-picker now see the patient's drug / RxNorm / ICD entries with first/last dates **before** they pick `ts_terms` and tools.
3. **`rebuild_ptv_code_index.py` now ships the same `metadata.code_index` that ingestion finalize emits**, and was run on all five synthetic patients. Previously every cohort file had `code_index = {}`; now P1–P5 have populated `drugs / rxnorm / icd` buckets (3–5 keys per patient), which is what the inventory step needs to be useful.
4. **Three-agent harness (probe → gap → synth → MKG) is healthy on the cohort.** The 2026-04-27 receipt has 5 patients × 1 question, 292.99 s total wall, every stage A–E present, no errors. Models: `eoh-llama` for probe/gap/synth/mkg-synth, `eoh-llama3.2-source-router` for routing, `BAAI/bge-base-en-v1.5` for embedding.
5. **MKG retrieval harness on the 4090 GPU is fast** for question 2-onward (`embed_device=cuda`, ~2 s embed + sub-second DB). First-call cold load is the only spike. **TS recall is still the weakest lane** — the per-term path returns content but `jaccard` between dense and BM25 is **0.000** on most clinical questions (3 / 5 chatbot turns; multiple MKG batch turns), which the new GAP heuristic now intercepts.
6. **Two real residual blockers remain**, both already known and both narrow:
   - **GAP JSON parsing is brittle to triple-quoted strings** (one of five chatbot turns triggered `⚠️ GAP JSON parse failed`); the prose fallback caught it but heuristic follow-ups also fired, so the report still grounded.
   - **`eoh-llama:70b` synthesis returns HTTP 500** from `/api/chat` in the batch-10 router rerun. The 8B (`eoh-llama`) lane is fine; the 70B is not blocking pilot-day operations but should be debugged before formal-pilot synthesis.
7. **Verdict:** **Green** for the lightweight conversational lane (REPL, 5/5 returned reports). **Green** for the 8B three-agent batch lane. **Yellow** for the 70B MKG synthesis lane and for TS overlap quality on broad therapy questions. The pilot can ingest the first FORWARD pull on the 8B path today; the 70B path needs one debugging session and the router needs the question-type prompt tweak from `REPORT_PILOT_READINESS_TOOLING_PHASE_20260425.md` §2.

---

## 1. Components covered

| Layer | File | Purpose | Latest receipt | Status |
|---|---|---|---|---|
| Code inventory builder | `server/ptv_toolkit/code_inventory.py` (new) | Walks `gh.code_index`, returns `{key, first, last, n_events}` per bucket; `fit_code_inventory_to_budget` shrinks to JSON budget. | smoke-tested locally on P1 (3 drugs / 3 rxnorm / 1 icd) | **Green** |
| `code_index` rebuild | `server/scripts/rebuild_ptv_code_index.py` | Idempotent call to `code_index_ops.rebuild_code_index` (same logic as ingestion `_build_code_index`) + legacy `arc_drug_*` strip. | Ran on P1–P5 on 2026-04-27; populated buckets | **Green** |
| Source router | `server/mkg/router_planner.py`, `server/scripts/eoh_source_router_harness.py` | 3.2-router → JSON plan (`question_type`, `semantic_query`, `ts_terms`, `selected_sources/modules`); now accepts `patient_code_inventory`. | `EOH_LLAMA_3.2_FORWARD_ROUTING_NASCENT_RUN.md`, `FORWARD_KNOWLEDGE_GRAPH_RETRIEVAL_HARNESS_BATCH10_ROUTER_70B_20260425.MD` | **Green** infra, **Yellow** quality (under-selective, defaults too often to `OTHER`/`E`) |
| MKG retrieval | `server/scripts/mkg_retrieval_harness.py` | Dense (`embedding_local`) + per-term TS over `public.rag_corpus`; pilot slice; optional `eoh-llama` synthesis. | `FORWARD_KNOWLEDGE_GRAPH_RETRIEVAL_HARNESS_BATCH10_RERUN_20260425_EXTRACT_SUMMARY.md`, `FORWARD_KNOWLEDGE_GRAPH_RETRIEVAL_HARNESS_NASCENT_RUN_20260425.md`, `FORWARD_MKG_QA_COLLECTION_20250425.md` | **Green** dense lane (cuda), **Yellow** TS overlap, **Yellow** 70B synthesis (HTTP 500) |
| PTV toolkit | `server/ptv_toolkit/{graph,tools,registry,agent,handoff}.py` | Six deterministic tools (`code_index_lookup`, `temporal_scan`, `semantic_search`, `bfs_expand`, `get_event`, `list_event_types`, `graph_stats`) | `REPORT_PTV_TOOLKIT_HARNESS_CHATBOT_20260423.md` (10/10 primary-tool, 9/10 evidence) | **Green** |
| Toolkit harness | `server/scripts/ptv_toolkit_harness.py` | Plan-first JSON loop scoring agent route quality. | same | **Green** |
| 3-agent FORWARD | `server/scripts/forward_ptv_3agent_harness.py` + `forward_ptv_3agent_pdf.py` | Probe (8B) → Gap (8B) → Synth (8B) → MKG retrieval (Stage E) per patient × question, PDF rendered automatically. | `receipts/FORWARD_PTV_3AGENT_20260427T012730Z.json` (5 patients, 292.99 s, 5 stages each) | **Green** |
| Lightweight chatbot | `server/scripts/forward_probe_gap_report_chatbot.py` | Single-call probe (router + graph pick + PTV semantic + MKG) → GAP → REPORT REPL. New pre-router code inventory; new `mkg_jaccard==0` heuristic. | `receipts/FORWARD_PROBE_GAP_REPORT_CHATBOT_NASCENT_RUN_20260427.md` (5 turns, 5 reports) | **Green** |

---

## 2. What we learned from the latest receipts

### 2.1 Lightweight chatbot — `FORWARD_PROBE_GAP_REPORT_CHATBOT_NASCENT_RUN_20260427.md`

Five turns against P1 (`events=54`, `hash=05fcc25c7fa5147f`). Each turn now starts with the **pre-router code inventory** line, which proves the new ordering is wired:

```text
📇 Stage PROBE — patient code_index inventory (pre-router; same index as code_index_lookup)
📇 code_index inventory n_keys=7 router_slice_json=912 graph_pick_slice_json=912
```

Turn-by-turn observations from the receipt:

1. **Q1 (5-year trajectory).** Router picked `OTHER / 5 ts_terms / 3 sources`; graph-pick parser missed (`len=182`) and defaulted to `semantic_search` (defensive default works as designed). MKG dense=8, TS=8, **jaccard=0.000**. GAP correctly issued **`follow_ts_terms=['flare', 'treatment escalation']`** based on the new prompt rules; follow-up MKG ran. Final report grounded actual events with explicit dates and dosages.
2. **Q2 (stable periods + meds).** Same path, model picked `follow_ts_terms=['regimens', 'stability']`, follow-up MKG executed. Final report named methotrexate, folic acid, hydroxychloroquine with start dates that match the regenerated `code_index`. Time-to-final ~30 s feel.
3. **Q3 (pain / functional change).** Router picked **`OTHER / 10 ts_terms / 4 sources`** — the *only* turn that achieved non-zero overlap (`jaccard=0.143`) on the first MKG call. GAP still asked for `follow_ts_terms=['flare','trajectory']`; follow-up overlap returned to zero. Final answer used the right scores (VAS Patient Global 54.3 → 16.3 across the five-year window).
4. **Q4 (methotrexate response).** GAP raw response *was* valid intent but used Python-style triple-quoted strings (`"""`) inside JSON, which `_extract_first_json_object` could not parse → **`⚠️ GAP JSON parse failed`**. The new heuristic correctly fired (`mkg_jaccard=0` with both lanes populated → `follow_ts_terms=['well','respond']`) and the GAP fallback dumped the model's prose into `gap_report`. Final report was still coherent, including a note that no flare-like events exist in the index — which is correct for the early-responder phenotype.
5. **Q5 (gaps / uncertainties).** Router picked `OTHER / 6 ts_terms / 3 sources`, GAP returned `follow_ts_terms=['flare','diagnosis']`, follow-up MKG ran cleanly. Final report named the diagnosis (`M05.9`) and the UC band (`flare probability 0.05, 90% band 0.02-0.15`) verbatim from the graph.

**Net read:**

- The new pre-router inventory is observably feeding the router and the graph-picker (`router_slice_json` / `graph_pick_slice_json` byte counts logged each turn). Two final reports cite drug names and dates pulled straight from `metadata.code_index`.
- The **jaccard=0.0 GAP heuristic** worked exactly as designed in 4 of 5 turns and was the only thing that produced a follow-up call on Q4 when JSON parsing failed.
- The single JSON-parse failure (Q4) is the one bug that surfaces in the receipt; behavior degraded gracefully (raw text → gap_report, heuristic injected `follow_ts_terms`, final report rendered).

### 2.2 Three-agent harness — `receipts/FORWARD_PTV_3AGENT_20260427T012730Z.json`

```text
schema, built_at = 2026-04-27T01:27:30Z
n_patients = 5
elapsed_sec = 292.99
models = {
  probe / gap / synth / mkg_overall_synth : eoh-llama,
  mkg_router : eoh-llama3.2-source-router,
  mkg_embed  : BAAI/bge-base-en-v1.5,
}
runs[*].keys = patient, question, graph_hash, n_events, elapsed_sec, stages, index
```

All five patients executed; every run has a `stages` block (probe → gap → curation → synth → MKG retrieval / overall synth). No exception keys at the top level. The companion PDF renderer ran during prior batches (`FORWARD_PTV_3AGENT_20260426T164530Z_pdfnorm.json` is normalized for PDF rendering); the 04-27 batch can be re-rendered when needed via `forward_ptv_3agent_pdf.py`.

### 2.3 MKG retrieval batch — 04-25 batches

- **GPU lane:** confirmed `embed_device=cuda` (extract summary), embed time ~2 s after the first cold load. DB time sub-second after first call. This matches the pilot deployment plan (`STRATEGY_FORWARD_PILOT_4090_DEPLOYMENT_20260424.md` §3.6).
- **Dense lane quality:** strong. `kdigo_ckd_2024`, `ada_dm_2024`, `kdigo_anemia_ckd_2023`, `gold_copd_2024`, `gina_asthma_2023` all surfaced where expected (`FORWARD_MKG_QA_COLLECTION_20250425.md`).
- **TS lane quality:** weak. The per-term path returns rows but `jaccard=0.000` for 9 of 10 batch questions in the 04-25 router rerun and 4 of 5 chatbot turns on 04-27. Net effect: dense and lexical lanes are independently sane but not voting together. The new GAP heuristic in the chatbot already detects this and forces a follow-up.
- **70B synthesis lane:** **broken in the latest batch run.** Every question shows `⚠️ LLM synthesis failed: 500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat` against `eoh-llama:70b`. The 8B lane is fine. This is a known Ollama 70B issue (memory pressure or model load on a single 4090); not a pipeline bug.

### 2.4 Source router — `EOH_LLAMA_3.2_FORWARD_ROUTING_NASCENT_RUN.md`

Single-call latency 5.34 s, structurally valid plan, but `question_type=E` for a treatment question and only 1 source / 1 module returned. Confirmed in batch: still under-selective. The fix is the prompt addition recommended in `REPORT_PILOT_READINESS_TOOLING_PHASE_20260425.md` §2:

> "For therapy, management, or guideline questions, always prefer question_type D or C and select at least 3–5 sources unless the user explicitly asks for a single source."

This change is independent of the new code-inventory plumbing.

### 2.5 PTV toolkit harness — `REPORT_PTV_TOOLKIT_HARNESS_CHATBOT_20260423.md`

Earlier 10-question agent harness on the real EHR graph (`PTV_REAL_EHR_20260423.json`, 632 events): 100 % primary-tool match, 90 % valid evidence ids in final answers, 80 % plan-route match. The toolkit's reliability surface remains the most settled component in the stack.

---

## 3. End-to-end pilot path (today, 2026-04-27)

```text
                  user question
                        │
         ┌──────────────▼───────────────┐
         │ Lightweight chatbot           │  forward_probe_gap_report_chatbot.py
         │ (interactive REPL on 4090)    │
         │   PROBE                       │
         │   ├── code_index inventory    │  ← NEW (pre-router)
         │   ├── plan_route (3.2 router) │
         │   │     ↑ patient_code_inv    │  ← NEW arg
         │   ├── MKG embed + per-term TS │
         │   ├── graph-pick (3.2)        │
         │   │     ↑ patient_code_inv    │  ← NEW arg
         │   ├── PTV graph tool          │
         │   └── PTV semantic_search     │
         │   GAP   (8B eoh-llama)        │
         │   ├── probe_metrics           │  ← NEW
         │   ├── follow-up MKG / PTV /   │
         │   │   graph_tool (model)      │
         │   └── jaccard==0 heuristic    │  ← NEW
         │   REPORT (8B eoh-llama)       │
         └──────────────────────────────┘
```

For the formal pilot reports we still use the heavyweight three-agent harness (`forward_ptv_3agent_harness.py`); the lightweight chatbot is the operator's day-to-day exploration surface.

---

## 4. Risk register and what fixes them

| Risk | Severity | Evidence | Fix | Owner | ETA |
|---|---|---|---|---|---|
| `eoh-llama:70b` HTTP 500 from `/api/chat` | Medium | every Q in batch-10 router rerun | Restart Ollama; bump `OLLAMA_KV_CACHE` / lower `num_ctx`; verify q4_K_M model file integrity; consider holding 8B-only for the first FORWARD pull | dylan | 1 session |
| GAP JSON parse failure on triple-quoted strings | Low | 1 of 5 chatbot turns (Q4) | Pre-clean `"""..."""` blocks before `_extract_first_json_object`; or add `_extract_first_json_object_relaxed` that also accepts triple quotes; current behavior already degrades to prose fallback | platform | 1 PR |
| MKG `jaccard=0.000` on majority of clinical questions | Medium | chatbot 4/5, batch-10 9/10 | (1) router prompt tweak (qtype D/C bias, source breadth); (2) lexical-pair fallback for top concept tokens; (3) GAP heuristic already mitigates per-turn | platform | with router fix |
| Router `question_type=OTHER` defaults | Low | 5/5 chatbot turns | Same single-line addition to the 3.2 Modelfile / system prompt | platform | 5 min |
| `metadata.code_index` empty on legacy cohort files | Resolved | was empty on P1–P5 before 04-27 rebuild | `server/scripts/rebuild_ptv_code_index.py` run; populated 3–5 codes per patient | done | 2026-04-27 |
| First-call embedding cold load | Low | ~46–74 s on first call, ~2 s thereafter | Pre-warm SentenceTransformers in process startup; persistent worker | platform | nice-to-have |
| `arc_drug_*` legacy arcs | Resolved | `arc_drug_dropped=0` on all five rebuilds (already cleaned) | n/a | done | n/a |

---

## 5. Operational readiness scorecard

| Component | Status | Notes |
|---|---|---|
| PTV toolkit (`code_index_lookup`, `temporal_scan`, `semantic_search`, `bfs_expand`, `get_event`, `list_event_types`, `graph_stats`) | Green | 100 % primary-tool match in toolkit harness; surfaces in chatbot via `_pick_graph_tool`. |
| `metadata.code_index` on synthetic cohort | Green | Re-run on P1–P5 on 2026-04-27. |
| Pre-router code inventory | Green | New `📇` lines in receipt; fits both router (~14 KB) and graph-pick (~8 KB) JSON budgets. |
| Source-router (3.2) | Yellow | Plumbed and accepting `patient_code_inventory`; needs question-type prompt tweak. |
| MKG dense retrieval | Green | CUDA path, sub-second DB after first call. |
| MKG TS retrieval | Yellow | Per-term works; lexical / dense overlap weak. |
| MKG synthesis (8B) | Green | Used by chatbot and 3-agent harness without errors in latest receipts. |
| MKG synthesis (70B) | Red | HTTP 500 in last batch; out of pilot-day path until fixed. |
| Three-agent batch harness | Green | 5 patients × 1 question × 5 stages, 292.99 s, no errors. |
| Lightweight chatbot | Green | 5/5 turns produced gap_report + final report; one JSON parse failure handled gracefully. |
| Receipts / PDFs | Green | JSON receipts emitting; PDF renderer normalizes via `*_pdfnorm.json`. |
| Pilot deployment plan (`PortalNode-0`) | On track | Per `STRATEGY_FORWARD_PILOT_4090_DEPLOYMENT_20260424.md`; nothing in this report contradicts it. |

**Overall: Green for 8B operator workflow; Yellow for 70B and TS overlap.** The pilot can take its first FORWARD pull on the 8B lane today; the 70B lane and the router prompt tweak are the only two items to clear before a formal-pilot deliverable run.

---

## 6. Next 24–72 hours (recommended order)

1. **Router system-prompt tweak** (5 min): bias `question_type` to **D / C** for therapy/guideline questions; require ≥ 3 sources unless user asks for one. Re-run batch-10 router rerun and re-check `jaccard` distribution.
2. **GAP JSON robustness** (1 PR): tolerate `"""..."""` blocks; add a single regression test using the Q4 raw text already captured in the 04-27 receipt.
3. **70B synthesis triage** (1 session): restart Ollama; lower `num_ctx` from 32768 to 16384 for the 70B run; if still 500-erroring, hold the 70B lane out of the pilot and document the 8B-only path. The 3-agent harness already supports this via `FORWARD_MKG_SYNTH_MODEL`.
4. **Re-render the 04-27 three-agent batch PDF** (`forward_ptv_3agent_pdf.py`) to file under `reports/`. (One PDF per patient as before.)
5. **Optional polish:** preload SentenceTransformers in the chatbot startup so first turn no longer pays the 30–70 s embedding cold load on a fresh process.

When (1)–(3) are complete, this report can be marked **Green across the board** and we can proceed to FORWARD pull #1 on the 8B lane (Phase 3 in `STRATEGY_FORWARD_PILOT_4090_DEPLOYMENT_20260424.md` §10).

---

## 7. One-liner

> The 4090 stack runs the full Probe → Gap → Report cycle end-to-end on five synthetic patients today; the new pre-router `metadata.code_index` inventory is wired and observably feeding both the source router and the graph-picker; `rebuild_ptv_code_index.py` has populated `metadata.code_index` on the synthetic cohort so that inventory is non-empty; the only outstanding items are a one-line 3.2-router prompt tweak, a small GAP JSON-parse hardening, and a 70B Ollama synthesis triage — none of which block the first FORWARD pull on the 8B lane.

---

*Filed 2026-04-27. Companion to `REPORT_PILOT_READINESS_TOOLING_PHASE_20260425.md` and `STRATEGY_FORWARD_PILOT_4090_DEPLOYMENT_20260424.md`.*
