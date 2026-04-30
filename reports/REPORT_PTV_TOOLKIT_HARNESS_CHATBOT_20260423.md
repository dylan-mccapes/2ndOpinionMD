# REPORT — PTV Toolkit, Harness Results, and Chatbot

**Date:** 2026-04-23  
**Model:** `eoh-llama-lucifer` (8B probe)  
**Graph:** `artifacts/forward_kaleb_package_20260423/PTV_REAL_EHR_20260423.json` (632 events)

## 1) Scope

This report covers:

- PTV toolkit architecture (`server/ptv_toolkit/`)
- Harness execution and measured results (`run_20260423T223250Z_eoh-llama-lucifer`)
- Interactive chatbot implementation for WSL + PowerShell (`ptv_chatbot_wsl.py`, `ptv_chatbot.ps1`)
- Pilot readiness assessment and next actions

## 2) Toolkit Delivered

The toolkit exposes deterministic, JSON-safe retrieval tools for the 8B probe agent:

- `code_index_lookup` — flat index lookups (drugs, rxnorm, icd, labs, loinc)
- `temporal_scan` — date-window and event-type retrieval
- `semantic_search` — sentence-transformer similarity retrieval (with rerank mode)
- `bfs_expand` — graph neighborhood expansion over selected edge kinds
- `get_event` — full event details for specific `event_id`
- `list_event_types`, `graph_stats` — orientation and inventory tools

Supporting components:

- `graph.py` — load and index graph in-memory
- `embeddings.py` — cached event embeddings (`all-MiniLM-L6-v2`) with cache versioning
- `agent.py` — strict plan-first JSON protocol + tool loop over Ollama
- `handoff.py` — 8B probe handoff package for 70B gap/reviewer
- `registry.py` — schemas + dispatch table

## 3) Harness Design

Harness script: `server/scripts/ptv_toolkit_harness.py`

- Loads one indexed graph and a 10-question probe suite
- Forces plan-first behavior (`plan.route` then `tool_call` then `final_answer`)
- Scores routing and evidence quality
- Emits artifacts:
  - `turns.jsonl`
  - `summary.json`
  - `summary.md`
  - `handoffs/*.handoff.json`

Question set (`server/scripts/ptv_toolkit_questions.json`) spans code lookup, temporal windows, free-text semantic retrieval, BFS workup, and graph orientation.

## 4) Harness Results (Nascent Run)

Run artifact folder:
`artifacts/ptv_toolkit_runs/run_20260423T223250Z_eoh-llama-lucifer`

Aggregate metrics from `summary.json`:

| Metric | Result |
|---|---:|
| Questions | 10 |
| Elapsed | 932.17s |
| Plan emitted | 10/10 (100%) |
| Plan-route match | 8/10 (80%) |
| Expanded query present | 3/10 |
| Primary-tool match | 10/10 (100%) |
| Any-tool match | 10/10 (100%) |
| Valid evidence IDs in final answer | 9/10 (90%) |
| Keyword match | 7/10 (70%) |

### Interpretation

- **Key win:** first substantive tool selection was correct in every probe.
- **Evidence grounding:** strong overall; one run (`q05_rxnorm_lookup`) hit turn budget before final answer.
- **Route mismatches:** 2 route-label misses (`orient` vs `list_event_types`/`graph_stats`) were semantic labeling issues, not tool failure.

## 5) Chatbot for Interactive Use

Implemented scripts:

- `server/scripts/ptv_chatbot_wsl.py` — interactive REPL using the same `run_agent()` loop as the harness
- `server/scripts/ptv_chatbot.ps1` — PowerShell launcher with Windows defaults

### Behavior

- Loads graph once, then processes natural-language questions in a loop.
- Prints tool trace, stop reason, answer, and cited `evidence_event_ids`.
- Optional handoff/transcript writing for audit and replay.

### Connectivity hardening

For WSL, `127.0.0.1` may not target Windows-hosted Ollama. The chatbot now includes:

- `--wsl-host` (resolve Windows host IP automatically)
- `--auto-wsl-host` (fallback if initial URL fails)
- startup probe (`/api/tags`) + targeted guidance on connection failure

For PowerShell on Windows, use `http://127.0.0.1:11434` directly via launcher script.

## 6) Test Chatbot Status

- **Code-level validation:** script compiles and CLI help renders successfully.
- **Operational validation:** WSL connection-refused path reproduced and then addressed with explicit host-routing options.
- **PowerShell path:** launcher script added for straightforward local execution.

Suggested operator command (PowerShell):

```powershell
cd C:\2OPMD\2ndOpinionMD-MVP
.\server\scripts\ptv_chatbot.ps1 -Verbose
```

## 7) Pilot Readiness

Current state is **pilot-ready for retrieval and evidence curation**:

- deterministic tool interface is stable
- harness coverage is broad and measurable
- chatbot enables interactive operator testing against real indexed graph artifacts

Known gaps before wider rollout:

1. add guardrails for forced `final_answer` after single decisive tool calls
2. tighten evidence ID hygiene before final synthesis
3. widen accepted route labels for orientation-class prompts in scoring

## 8) Recommended Next Steps

1. Run daily/PR harness regression with frozen question suite.
2. Add 3 Bayesian probes once `bayesian_update_uc` tool lands.
3. Add optional “strict mode” in chatbot (`final_answer` required in N turns).
4. Keep 70B gap/reviewer pass as final synthesis and citation validator.

---

**Primary references**

- `receipts/RECEIPT_PTV_TOOLKIT_HARNESS_EOH_LLAMA_LUCIFER_20260423.md`
- `artifacts/ptv_toolkit_runs/run_20260423T223250Z_eoh-llama-lucifer/summary.json`
- `server/scripts/ptv_toolkit_harness.py`
- `server/scripts/ptv_chatbot_wsl.py`
- `server/scripts/ptv_chatbot.ps1`
