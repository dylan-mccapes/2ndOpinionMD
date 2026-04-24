# RECEIPT — PTV toolkit harness (nascent run)

**Date (UTC):** 2026-04-23  
**Status:** Success — first full 10-question end-to-end run completed.

**Narrative receipt (pilot readout):** `receipts/RECEIPT_PTV_TOOLKIT_HARNESS_EOH_LLAMA_LUCIFER_20260423.md`

This receipt records the outcome of the new **PTV probe toolkit** plus **agent harness** against the indexed, no-arcs real EHR graph bundled for FORWARD (`PTV_REAL_EHR_20260423.json`). It is a **nascent** baseline: metrics are useful for trend comparison, not for claiming production readiness.

---

## What was exercised

| Layer | Description |
|-------|-------------|
| **Graph** | `artifacts/forward_kaleb_package_20260423/PTV_REAL_EHR_20260423.json` — 632 events, `graph_hash` **f159af9f39d05b6b** |
| **Model** | `eoh-llama-lucifer` (Ollama, Llama 3.1 8B instruct q4_K_M, Modelfile `server/ollama/eoh-llama3.1-8b-lucifer.Modelfile`) |
| **Tools** | `graph_stats`, `list_event_types`, `code_index_lookup`, `semantic_search` (sentence-transformers `all-MiniLM-L6-v2`), `bfs_expand`, `temporal_scan`, `get_event` |
| **Protocol** | PLAN-first JSON turns → tool calls → `final_answer` with `evidence_event_ids` |
| **Outputs** | Per-question transcripts, aggregate summary, per-question **handoff** JSON for a future 70B gap agent |

---

## Run directory (authoritative artifacts)

All machine-readable results live here:

`artifacts/ptv_toolkit_runs/run_20260423T223250Z_eoh-llama-lucifer/`

| File / folder | Purpose |
|---------------|---------|
| `turns.jsonl` | One JSON object per question: question, score rubric, full `agent` trace |
| `summary.json` | Header + aggregate metrics + embedded per-question rows |
| `summary.md` | Human-readable table + answer excerpts |
| `handoffs/*.handoff.json` | Curated working set + top events + probe trace for **70B gap** consumption (`schema`: `ptv_toolkit.handoff.v1`) |

---

## Command used (PowerShell)

```powershell
cd C:\2OPMD\2ndOpinionMD-MVP; python server\scripts\ptv_toolkit_harness.py --graph artifacts\forward_kaleb_package_20260423\PTV_REAL_EHR_20260423.json --questions server\scripts\ptv_toolkit_questions.json --model eoh-llama-lucifer --ollama-url http://localhost:11434 --out-dir artifacts\ptv_toolkit_runs --max-turns 6
```

---

## Aggregate metrics (from `summary.json`)

| Metric | Result | Notes |
|--------|--------|--------|
| **Wall time** | **932.17 s** (~15.5 min) | Dominated by Ollama turns + first full-graph ST encode on early `semantic_search` |
| **Plan emitted** | **10 / 10** (100%) | PLAN-first discipline held for every question |
| **Plan `route` match (rubric)** | **8 / 10** (80%) | Two “mismatches” are **enum naming**, not wrong tools (see below) |
| **`expanded_query` present** | **3 / 10** | Expected: only `semantic_then_bfs` plans should populate it |
| **Primary tool match** | **10 / 10** (100%) | First substantive tool matched the gold **primary** for every question |
| **Any tool match** | **10 / 10** (100%) | Expected tool appeared somewhere in the trace |
| **Valid `evidence_event_ids`** | **9 / 10** (90%) | One question never reached `final_answer` |
| **Keyword match (rubric)** | **7 / 10** (70%) | String checks on final prose; strict and partly cosmetic |

---

## Per-question highlights (console log)

| ID | Route rubric | Primary tool | Wall (s) | Notes |
|----|--------------|--------------|----------|-------|
| q01 | ✅ `code_lookup` | ✅ `code_index_lookup` | 116.87 | Correct opener; agent still chained `semantic_search` + `bfs_expand` + `get_event` (extra cost / first ST cold path) |
| q02 | ✅ | ✅ | 100.06 | Solid code-first path |
| q03 | ✅ `temporal` | ✅ `temporal_scan` | 112.36 | Window + type routing worked |
| q04 | ✅ `semantic_then_bfs` | ✅ `semantic_search` | 180.50 | Longest single question; semantic + context expansion |
| q05 | ✅ | ✅ | 58.54 | **Failure mode:** `reason_stopped` = **`max_turns_reached`**, **`final_answer`: null** — tool result consumed turns but model did not emit closing JSON in time |
| q06 | ✅ | ✅ `bfs_expand` (with precursors allowed) | 79.43 | `semantic_then_bfs` → semantic seeds → BFS as intended |
| q07 | ✅ | ✅ | 61.87 | Clean temporal scan |
| q08 | ⚠️ plan `route` = **`list_event_types`** vs gold **`orient`** | ✅ `list_event_types` | 83.16 | **Rubric gap:** behavior is correct; enum should accept `list_event_types` as an `orient` alias or gold should be updated |
| q09 | ✅ | ✅ | 66.23 | Free-text → semantic path |
| q10 | ⚠️ plan `route` = **`graph_stats`** vs gold **`orient`** | ✅ `graph_stats` | 73.12 | Same as q08 — **synonym** of orientation |

---

## Interpretation (honest)

1. **Tool routing quality is strong.** Ten-for-ten on the **first substantive tool** is the signal we cared about for the 8B probe layer: the model is choosing `code_index_lookup`, `temporal_scan`, and `semantic_search` in the right situations.

2. **The 80% “plan route” score understates quality.** Two misses are **label mismatch** (`list_event_types` / `graph_stats` vs canonical `orient`). The harness gold file can be relaxed or the Modelfile enum extended — no change to Python tools required for that.

3. **One real harness failure: q05 (RxNorm).** The probe called `code_index_lookup` correctly but **never produced `final_answer`** before the turn budget. Transcript shows repeated **JSON parse errors** on `get_event` payloads (truncated / malformed assistant JSON). Action items: raise `--max-turns` for RxNorm-style single-tool questions, tighten the probe prompt on **exactly one JSON object with balanced braces**, or add a **host-side JSON repair** for common truncation patterns.

4. **First `semantic_search` is expensive.** Wall time includes MiniLM load + full-graph embedding cache build (632 events). Subsequent questions reuse the NPZ cache under `artifacts/ptv_toolkit_embeddings/` — expect much faster repeats on the same graph hash + text revision.

5. **Keyword rubric (7/10)** is intentionally dumb (substring match on final answer). Treat it as a lint check, not a clinical grade.

---

## Handoff blobs

Each `handoffs/<question_id>.handoff.json` packages:

- probe `plan`, tool trace, and `final_answer` (when present)
- **`working_set.event_ids`** — ranked union of ids seen in tool payloads + boosted final citations
- **`top_events`** — compact cards for the 70B gap agent’s default scope

This is the intended wire format for **8B probe → 70B gap → 70B report** without Lorenz or ProvenanceEngine in the loop.

---

## Suggested next iteration (short list)

1. **Harness gold:** map `list_event_types` and `graph_stats` plan routes to **`orient`** for scoring, or add them to the allowed enum in questions JSON.
2. **q05 class:** increase `--max-turns` to 8–10 **or** add a “single-tool answer” fast path when `code_index_lookup` alone suffices.
3. **JSON robustness:** log raw assistant text on parse failure (already in `turns` previews); consider a **repair** pass for missing closing `}` on `tool_call`.
4. **Cost:** prompt nudge — after a successful `code_index_lookup` that fully answers the question, **skip** `semantic_search` unless the user asked for narrative context (q01 over-called tools).
5. **REPORT:** fold this receipt into `REPORT_PTV_TOOLKIT.md` when that document is written.

---

## Sign-off

This run establishes a **reproducible baseline** for the PTV indexed-graph agent toolkit on real scrubbed EHR-shaped data, with artifacts suitable for downstream 70B gap work. The harness and handoff schema are **fit for continued iteration**; the rubric and turn budget should be tuned next, not the core tool design.
