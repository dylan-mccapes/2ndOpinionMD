# Norman graph retrieval sandbox

Deterministic **core-12** graph tools (`server/graph_traversal/agent_tools.py`) against the **norman_eric_roberts** Patient Timeline Vision JSON, plus optional **Ollama** synthesis with **eoh-llama-lucifer** and optional **provenance-engine** classification.

**Dev platforms:** On **Windows**, run these commands in **WSL** with a **venv** and `PYTHONPATH=.` (see repo root `README.md`). **macOS** (including an M2 Ultra Mac Studio as the main server) and **Linux** use the same pattern.

## Python environment (read this on Debian / WSL)

System Python on Debian/Ubuntu is **externally managed** ([PEP 668](https://peps.python.org/pep-0668/)): `pip install -r requirements-dev.txt` will fail with `externally-managed-environment` unless you use a venv or `--break-system-packages` (do not use the latter).

**Recommended — project venv (same as backend):**

```bash
cd /mnt/c/2OPMD/2ndOpinionMD-MVP
python3 -m venv .BeatingHeart
source .BeatingHeart/bin/activate
pip install -U pip
pip install -r requirements-dev.txt
PYTHONPATH=. python sandbox/norman_graph_retrieval/run.py --no-ollama
```

If `.BeatingHeart` already exists from prior work, only `source .BeatingHeart/bin/activate` and `pip install -r requirements-dev.txt` are needed.

**Minimal sandbox-only venv** (if you refuse the canonical name):

```bash
python3 -m venv .venv_graph_sandbox
source .venv_graph_sandbox/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=. python sandbox/norman_graph_retrieval/run.py --no-ollama
```

Always run from the repo root with **`PYTHONPATH=.`** (or `export PYTHONPATH=/mnt/c/2OPMD/2ndOpinionMD-MVP`) so `import server....` resolves.

## Prerequisites

- Python 3.10+ with project deps installed **inside a venv** (`requirements-dev.txt` includes `provenance-engine`).
- **Ollama** running locally with base model pulled:

  ```bash
  ollama pull llama3.1:8b-instruct-q4_K_M
  ```

- Build the Lucifer model from the repo Modelfile (see scripts below).

## Default timeline artifact

`artifacts/timeline_ollama_20260329_1805/patient_timeline_vision_norman_eric_roberts_20260329_195915.json`

Override with `NORMAN_PTV_JSON` or `--ptv path/to/patient_timeline_vision.json`.

## Build `eoh-llama-lucifer`

From repo root (Linux / macOS / WSL):

```bash
./sandbox/norman_graph_retrieval/scripts/build_eoh_lucifer_ollama.sh
```

Windows (PowerShell):

```powershell
.\sandbox\norman_graph_retrieval\scripts\build_eoh_lucifer_ollama.ps1
```

Manual:

```bash
cd /path/to/2ndOpinionMD-MVP
ollama create eoh-llama-lucifer -f server/ollama/eoh-llama3.1-8b-lucifer.Modelfile
```

Verify:

```bash
ollama run eoh-llama-lucifer "Reply in one sentence: what is EoH Stack level?"
```

## Run the sandbox

From repo root with venv activated and `PYTHONPATH` including the repo root:

```bash
export PYTHONPATH=.
python sandbox/norman_graph_retrieval/run.py
python sandbox/norman_graph_retrieval/run.py -q "CRP and joint symptoms over time"
python sandbox/norman_graph_retrieval/run.py --no-ollama
python sandbox/norman_graph_retrieval/run.py --no-semantic    # keyword-only hybrid (faster)
python sandbox/norman_graph_retrieval/run.py --with-centrality  # add structural hubs (optional)
```

The default run uses a **temporal slice** (recent window from the latest corpus date) after structural **graph_reduce**, then **sentence-transformers** hybrid on that corpus, then **multi-seed BFS** restricted to the same set — see `game_plans/STRATEGY_GRAPH_TRAVERSAL.md` v1.1.

Environment:

| Variable | Default |
|----------|---------|
| `NORMAN_PTV_JSON` | path above |
| `OLLAMA_URL` | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | `eoh-llama-lucifer` |

Output JSON is written to `sandbox/norman_graph_retrieval/out/norman_sandbox_<utc>.json` (tool bundles + optional Ollama reply + PE status).

## Per-tool agent harness

`tool_agent_harness.py` runs the **flagship** STRATEGY v1.1 graph rounds: **structural `graph_reduce`** → **temporal `graph_reduce`** (`recent_years` from the latest parseable corpus date by default) → **hybrid** on that corpus → **BFS** (seeds + `restrict_to_event_ids`) → Lorenz → govern → token budget, then a **provenance-engine** cross-check on the working set. After **each** step, it sends a capped **`result_summary`** (from `server/graph_traversal/tool_result_summary.py`) to **Ollama** `eoh-llama-lucifer` for a short operator-facing analysis (omit with `--no-agent`).

```bash
PYTHONPATH=. python sandbox/norman_graph_retrieval/tool_agent_harness.py --no-agent
PYTHONPATH=. python sandbox/norman_graph_retrieval/tool_agent_harness.py -q "CRP and joint symptoms"
```

**Linux / macOS / WSL — deps + run in one step** (uses `.BeatingHeart` or `.venv_graph_sandbox`, runs `pip install -r requirements-dev.txt`, sets `PYTHONPATH`):

```bash
chmod +x sandbox/norman_graph_retrieval/scripts/RUN_TOOL_AGENT_HARNESS.sh
./sandbox/norman_graph_retrieval/scripts/RUN_TOOL_AGENT_HARNESS.sh --no-agent -q "CRP and joint symptoms"
```

Useful flags: `--no-temporal-reduce` (skip the second `graph_reduce`; hybrid/BFS use the structural corpus only), `--temporal-recent-years N` (default `1.0`), `--temporal-anchor latest_in_corpus|utc_now`, `--no-semantic` (keyword hybrid), `--no-agent` (tools only, no `/api/chat` per round), `--max-json-chars` (prompt cap to the model), `--max-context-nodes` / `--context-preview-chars` (how many PTV nodes and how much preview text to attach per round as `context_nodes`), `--full-tool-json` (include raw `result` in the written JSON; default is `result_summary` only to keep files small), `--extra-rounds path.json` (append more `execute_graph_tool` rounds), `--quiet` (suppress the structured `[tool-harness]` emoji logs; still writes JSON), `--skip-ollama-preflight` (skip the fast `GET /api/tags` check; not recommended).

When the agent is **on** (default), the harness **preflights Ollama** before loading the PTV: server must respond at `OLLAMA_URL`, and `OLLAMA_MODEL` must appear in `/api/tags`. That avoids waiting on graph work only to fail on the first LLM call. **WSL:** if Ollama runs on Windows, point `OLLAMA_URL` at the Windows host (often the IP from `/etc/resolv.conf` `nameserver`, port `11434`) or run Ollama inside WSL.

**Semantic hybrid (`sem` hits):** `requirements-dev.txt` does **not** include `sentence-transformers` (keeps the dev image light). If `graph_hybrid_search` shows `semantic_hits=0` and a `note` about skipped semantic, install embeddings support, e.g. `pip install 'sentence-transformers>=3'` (or merge deps from `server/requirements.txt`). Set **`GRAPH_SEMANTIC_VERBOSE=1`** to print a one-line stderr message when the MiniLM model loads on first use.

Logs are **copy/paste friendly**: every line is prefixed with `[tool-harness]`, the session banner lists PTV path and flags, each round shows strategy id, timings, and numeric metrics, and the footer points at the output JSON path.

`--extra-rounds` expects a JSON **array** of objects like `{"step_id": "optional_label", "tool": "graph_snapshot", "args": {}}`. In `args`, you may use string placeholders `__reduced_ids__` (post-temporal corpus when the temporal round runs), `__structural_reduced_ids__`, `__hybrid_ids__`, `__bfs_ids__`, and `__working_ids__` (resolved after the default pipeline). Extra rounds run **after** the built-in sequence and PE step.

Written output: `sandbox/norman_graph_retrieval/out/tool_agent_harness_<utc>.json` plus a matching **`tool_agent_harness_<utc>.log`** — plain text with **full tool JSON** (args + raw results) and **eoh-llama responses** per round for inspection (the JSON file still defaults to `result_summary` unless `--full-tool-json`).

**Final synthesis (when the agent is on):** the JSON bundle includes **`final_synthesis`** with **`response`** (closing operator-facing text), **`suggested_nodes`** (up to 10 of `{event_id, confidence, rationale}` from the hybrid/BFS/working pool), and **`suggested_nodes_with_full_context`** (same rows plus **`ptv_full`** — full PTV `to_dict()` for each id for downstream answer assembly). Use `--no-final-synthesis` to skip this extra LLM call; tune the candidate pool with `--final-synthesis-max-candidates` and `--final-synthesis-preview-chars`.

If final synthesis **throws** (OOM, timeout, etc.), the harness **does not exit**: you get **`ok: false`**, **`status: failed`**, **`receipt: true`**, and **`traceback_excerpt`** while **`rounds`** still contain the full graph + per-round agent output. The `.log` file appends a **FAILURE RECEIPT** section the same way.

### FAQ: `--no-ollama`

Use it when you only need **tool outputs + PE cross-check** in JSON: faster, no Ollama dependency, good for CI or debugging graph code. **Omit the flag** (default) when you want **EoH synthesis** from `eoh-llama-lucifer`.

**Shell tip:** type `--no-ollama` exactly — a trailing `~` (e.g. `--no-ollama~`) is a different argument and argparse will reject it.

## What runs

**Norman sandbox (`run.py`):**

1. `graph_snapshot` — full graph shape (large JSON; same as before).
2. `graph_reduce` — drop `page` + zero-edge isolates (unknown timestamps kept by default).
3. `graph_hybrid_search` — query vs **reduced corpus only**; **semantic on by default** (use `--no-semantic` for keyword-only).
4. `graph_bfs_expand` — **multi-seed** BFS from top hybrid hits, **`restrict_to_event_ids`** = reduced set.
5. `graph_pe_lorenz_classify` + `graph_pe_govern_adjust` on the **working set** (hybrid ∪ BFS, capped).
6. **provenance-engine** cross-check when installed.
7. `graph_token_budget` on hybrid hits for the prompt budget.
8. Optional **Ollama** `/api/chat` synthesis.

With **`--with-centrality`**, an extra `graph_centrality` step runs on the reduced set (exploratory, not required for Q&A).

**Tool agent harness (`tool_agent_harness.py`) — flagship path:** two `graph_reduce` rounds (structural, then temporal window), then hybrid → BFS → Lorenz → govern → token budget → native PE, then optional extras and final synthesis — see the script docstring and session banner.

## Agentic probe harness (question probe → gap → report)

`agentic_probe_harness.py` is a fundamentally different architecture from the fixed-pipeline harness above. The **agent chooses** which tools to call.

1. **Structural reduce** once (shared across all queries).
2. For each query from `grok_20_queries.json` (20 clinically meaningful questions from Grok):
   - **Semantic hybrid search** on the reduced corpus → 20 seed events with `context_nodes`.
   - The agent receives the seeds, the **full tool registry** (all 12 tools), and the query.
   - The agent responds with a `tool_call` JSON or a `final_answer` JSON — up to `--max-rounds` turns (default 6).
   - The harness executes the chosen tool, returns the result, and loops.
   - When the agent emits `final_answer`, it includes `response`, `suggested_nodes`, and `gaps`.
3. After all queries, a **gap report** aggregates: queries with gaps, tools never used, suggested node counts.

```bash
PYTHONPATH=. python sandbox/norman_graph_retrieval/agentic_probe_harness.py --no-agent          # seeds only
PYTHONPATH=. python sandbox/norman_graph_retrieval/agentic_probe_harness.py -n 3                # first 3 queries
PYTHONPATH=. python sandbox/norman_graph_retrieval/agentic_probe_harness.py --query-ids Q01,Q12  # specific queries
PYTHONPATH=. python sandbox/norman_graph_retrieval/agentic_probe_harness.py --max-rounds 8      # more tool calls per query
```

Flags: `--queries path.json` (custom query set), `-n N` (first N only), `--query-ids Q01,Q05` (select), `--max-rounds` (tool calls per query, default 6), `--seed-top-k` (seeds per query, default 20), plus the same `--no-semantic`, `--max-json-chars`, `--max-context-nodes`, `--context-preview-chars`, `--quiet`, `--skip-ollama-preflight` as the fixed harness.

With the agent on and **without** `--quiet`, each probe ends with a **terminal block**: full **QUERY**, **CURATED CONTEXT** (confidence + explanation for the reasoning agent), full **FINAL ANSWER** text, and **GAPS**.

Output: `sandbox/norman_graph_retrieval/out/agentic_probe_<utc>.json` and **`agentic_probe_<utc>.log`**. The JSON includes per-probe **`audit_trail`** (full system prompt, every user/assistant message, **`args_full`/`result_full`** for each tool, **`enriched_tool_document_full`** — the exact context curation sent to the model — and the chat transcript). The **`.log`** repeats the same in plain text (large files are normal).

The model’s **`final_answer`** should include **`curated_context`**: `confidence` (0–1), **`what_this_context_is`**, and **`primary_event_ids`**. The harness normalizes that into **`curated_context_for_reasoning_agent`** with full **`ptv_full`** payloads for downstream reasoning.

The harness **normalizes** common model mistakes: `tool` / `name`+`parameters` instead of `tool_call`+`args`, `connascence_type`→`edge_types` for BFS, and temporal fields mistakenly sent to `graph_pe_lorenz_classify`→`graph_reduce`. After updating `server/ollama/eoh-llama3.1-8b-lucifer.Modelfile`, recreate the Ollama model: `ollama create eoh-llama-lucifer -f server/ollama/eoh-llama3.1-8b-lucifer.Modelfile`.

## See also

- `game_plans/STRATEGY_GRAPH_TRAVERSAL.md` — core 12 strategy IDs.
- `server/graph_traversal/pe_adapter.py` — PTV → provenance-engine node conversion.
