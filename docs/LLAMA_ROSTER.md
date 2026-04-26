# LLAMA ROSTER — EoH Model Fleet

**Date:** 2026-04-13  
**Scope:** All Llama models used or planned across the 2ndOpinionMD / Ethos-of-Health stack, from edge prototyping through on-prem clinical reasoning.

---

## Hardware Fleet

| Machine | Alias | GPU | VRAM | Memory Bus | Role | Status |
|---------|-------|-----|------|------------|------|--------|
| ASUS laptop | **Lucifer** | RTX 4050 Mobile | 6 GB GDDR6 | 96-bit | Dev/sandbox, prototype runs, nascent harness testing | **Active** |
| Mac Studio | — | M2 Ultra (76-core GPU) | 192 GB unified | — | Primary server, macOS development, CPU inference, PostgreSQL | **Active** |
| RISE on-prem | — | 1 x RTX 4090 | 24 GB GDDR6X | 384-bit | 8B production agent — bearer-token protected API (timeline upload + <100 MB endpoint) | **Active** |
| RISE on-prem (planned) | — | 2 x RTX 4090 | 48 GB GDDR6X | 384-bit each | 70B reasoning agent (clinical synthesis, final reports) | Planned |

---

## Model Roster

### Llama 3.2 — Edge / Lightweight

| Variant | Parameters | Native Context | Quantization | Model Size | VRAM (inference) | Status |
|---------|-----------|----------------|--------------|------------|------------------|--------|
| `llama3.2:1b` | 1.23 B | 128K | q4_K_M | ~0.75 GB | ~1–2 GB | Available, not yet deployed |
| `llama3.2:3b` | 3.21 B | 128K | q4_K_M | ~1.75 GB | ~3–4 GB | Available, not yet deployed |

**Architecture:** Dense transformer, Grouped Query Attention (GQA). Knowledge-distilled from Llama 3.1 8B and 70B.

**Intended use:** Lightweight extraction tasks — PDF event parsing, connascence pattern matching, gap query generation. These run comfortably on Lucifer alongside the 8B model or standalone on CPU. Not intended for clinical reasoning or agentic tool selection.

**EoH fit:**
- PDF event extraction (structured JSON, no reasoning needed)
- Connascence LLM (pattern matching against rubric, small context)
- Gap agent (generates query terms, doesn't need deep reasoning)
- Pre-screening / triage before escalation to 8B

---

### Llama 3.1 8B — Workhorse Agent

Two Modelfile configurations exist in the repo:

#### `eoh-llama3.1-8b-lucifer` (Lucifer build — primary)

| Field | Value |
|-------|-------|
| **Base** | `llama3.1:8b-instruct-q4_K_M` |
| **Parameters** | 8.03 B |
| **Quantization** | q4_K_M (4-bit, mixed precision) |
| **Model file size** | ~4.9 GB |
| **VRAM (model weights)** | ~4.7 GB |
| **VRAM (+ 16K context KV cache)** | ~5.5–6.0 GB |
| **Context window** | 16,384 tokens (`PARAMETER num_ctx 16384`) — fits RTX 4050 6 GB |
| **Temperature** | 0.2 |
| **top_p** | 0.9 |
| **Modelfile** | `server/ollama/eoh-llama3.1-8b-lucifer.Modelfile` |
| **Ollama name** | `eoh-llama-lucifer` |
| **Hardware** | RTX 4050 6 GB (local dev / PTV harness); full MKG source legend lives on **eoh-llama** (4090) Modelfile |

**Observed performance (nascent run, Lucifer):**

| Metric | Value |
|--------|-------|
| Per-round LLM latency | 43–84 s (avg ~65 s) |
| Full 8-round pipeline | ~9.5 minutes |
| JSON output quality | Serviceable; requires normalization layer |
| Clinical analysis depth | Shallow but directionally correct |

#### `eoh-llama3.1-8b` (Full-precision build)

| Field | Value |
|-------|-------|
| **Base** | `llama3.1:8b-instruct-q8_0` |
| **Parameters** | 8.03 B |
| **Quantization** | q8_0 (8-bit) |
| **Model file size** | ~8.5 GB |
| **VRAM (model weights)** | ~8.5 GB |
| **VRAM (+ 32K context KV cache)** | ~12–14 GB |
| **Context window** | 32,768 tokens (full native) |
| **Temperature** | 0.2 |
| **top_p** | 0.9 |
| **Modelfile** | `server/ollama/eoh-llama3.1-8b.Modelfile` |
| **Ollama name** | `eoh-llama` (default) |
| **Hardware** | RTX 4090 24 GB (room to spare) |
| **API** | Bearer-token protected timeline upload endpoint + sub-100 MB endpoint |
| **Deployment** | **Live** — RISE on-prem |

**Expected performance (RTX 4090):**

| Metric | Estimated |
|--------|-----------|
| Per-round LLM latency | 8–15 s |
| Full 8-round pipeline | ~1.5–2 minutes |
| Grok-20 agentic suite | ~25–40 minutes |
| JSON output quality | Better than q4_K_M; fewer normalization corrections expected |
| Clinical analysis depth | Same architecture, higher fidelity from q8 weights + full 32K context |

**EoH fit (both builds):**
- Graph traversal agent (agentic probe harness — iterative tool selection)
- Per-round tool analysis (fixed-pipeline harness)
- Hierarchical map-chunk summarization (parallelizable)
- PTV event extraction and connascence assignment
- Curated context assembly for handoff to 70B reasoning agent

**Key differences:**

| | Lucifer (q4_K_M) | Full (q8_0) |
|--|-------------------|-------------|
| Fits on | 6 GB (4050) | 24 GB (4090) |
| Context | 16K (4050 local) | 32K (4090 timeline ingest) |
| Inference speed | ~65 s/round on 4050 | ~10 s/round on 4090 |
| Weight fidelity | 4-bit mixed, minor quality loss | 8-bit, near-lossless |
| Use case | Dev/prototype | Production agent fleet |

---

### Llama 3.1 70B — Reasoning Agent

| Field | Value |
|-------|-------|
| **Base** | `llama3.1:70b-instruct-q4_K_M` |
| **Parameters** | 70.6 B |
| **Quantization** | q4_K_M (4-bit, mixed precision) |
| **Model file size** | ~40 GB |
| **VRAM (model weights)** | ~42 GB |
| **VRAM (+ 16K context KV cache)** | ~44–46 GB |
| **Context window** | 16,384 tokens (`PARAMETER num_ctx 16384`) — leaner ctx since 70B is synthesis-only |
| **Hardware** | 2 x RTX 4090 (48 GB combined, tensor parallel) — currently runs with CPU offload elsewhere |
| **Modelfile** | `server/ollama/eoh-llama3.1-70b.Modelfile` |
| **Ollama name** | `eoh-llama:70b` (synthesis tag for `mkg_retrieval_harness.py --synth-model`) |

**Expected performance (2x RTX 4090):**

| Metric | Estimated |
|--------|-----------|
| Per-turn latency | 15–30 s (tensor parallel across 2 GPUs) |
| Context capacity | ~128K tokens (massive headroom for multi-probe bundles) |
| Clinical reasoning | Deep, nuanced, multi-condition synthesis |
| JSON compliance | Significantly better structured output than 8B |

**EoH fit:**
- **Downstream reasoning agent** — receives curated context bundles from 8B graph traversal agents
- Clinical synthesis (final patient reports, treatment response analysis)
- Multi-probe cross-referencing (combine evidence from multiple 8B probes per patient)
- Complex comparative queries ("before/after treatment X", multi-period trend analysis)
- The "money shot" — final reduce step where quality matters most
- **MKG harness final synthesis** — when `mkg_retrieval_harness.py` is run with
  `--synth-model eoh-llama:70b` (or `MKG_SYNTH_MODEL=eoh-llama:70b` via the wrapper),
  the dual-lane retrieval bundle and router_plan are handed off to the 70B build for
  the markdown synthesis pass. The 8B model still does router-driven planning + ANN
  scoring; the 70B handles only the final reasoning step.

**Handoff budget (8B → 70B):**

| Component | Size |
|-----------|------|
| Primary event IDs | 10–30 events |
| Full PTV row per event | ~200–500 tokens |
| Curated context payload | ~3,000–15,000 tokens |
| 70B context window | 128K tokens |
| **Headroom** | ~90%+ available for reasoning, instructions, multi-probe input |

---

## Model Lineage and Roles

```
Llama 3.2 1B ──── edge extraction, triage, gap queries
     │
Llama 3.2 3B ──── structured extraction, connascence matching
     │
Llama 3.1 8B ──── graph traversal agents (agentic probe + fixed pipeline)
     │              ├── q4_K_M on 4050 (Lucifer — dev/sandbox)
     │              └── q8_0 on 4090 (RISE — production agent fleet)
     │
     │         curated context handoff (confidence + explanation + primary event IDs + full PTV rows)
     │
     ▼
Llama 3.1 70B ─── clinical reasoning agent (RISE — synthesis, final reports)
                   q4_K_M on 2x4090 (tensor parallel)
```

---

## Quantization Reference

| Quant | Bits | Quality | Size (8B) | Size (70B) | Notes |
|-------|------|---------|-----------|------------|-------|
| FP16 | 16 | Baseline | ~16 GB | ~140 GB | Reference; impractical for consumer GPUs at 70B |
| q8_0 | 8 | Near-lossless | ~8.5 GB | ~75 GB | Best quality-per-bit; fits 8B on 4090 comfortably |
| q4_K_M | 4 | Good | ~4.9 GB | ~40 GB | Standard for constrained VRAM; the Lucifer default |
| q4_0 | 4 | Acceptable | ~4.4 GB | ~38 GB | Slightly worse than K_M; marginal size savings |

**Rule of thumb:** q4_K_M is the floor for clinical reasoning. Below q4 the model starts hallucinating tool names and producing structurally invalid JSON at higher rates.

---

## Deployment Summary

| Tier | Model | Quant | GPU | VRAM Used | Context | Role | Status |
|------|-------|-------|-----|-----------|---------|------|--------|
| **Dev** | 8B Lucifer | q4_K_M | 1x 4050 (6 GB) | ~5.5 GB | 16K | Local PTV harness, operator probes | **Active** |
| **4090 / prod** | 8B eoh-llama | q8_0 | 1x 4090 (24 GB) | ~12 GB | 32K | Timeline/PDF ingest, MKG source legend in Modelfile, graph fleet, API | **Active** |
| **Production Reasoning** | 70B | q4_K_M | 2x 4090 (48 GB) | ~46 GB | 128K | Clinical synthesis, final reasoning | Planned |
| **Edge (planned)** | 3.2 3B | q4_K_M | CPU or 4050 | ~3 GB | 8–128K | Extraction, triage | Planned |
| **Edge (planned)** | 3.2 1B | q4_K_M | CPU | ~1 GB | 8–128K | Minimal extraction | Planned |

---

## Ollama Commands

```bash
# Pull base models
ollama pull llama3.2:1b
ollama pull llama3.2:3b
ollama pull llama3.1:8b-instruct-q4_K_M
ollama pull llama3.1:8b-instruct-q8_0
ollama pull llama3.1:70b-instruct-q4_K_M

# Create EoH-customized models (with SYSTEM prompt, parameters, guardrails)
ollama create eoh-llama-lucifer            -f server/ollama/eoh-llama3.1-8b-lucifer.Modelfile
ollama create eoh-llama                    -f server/ollama/eoh-llama3.1-8b.Modelfile
ollama create eoh-llama3.2-source-router   -f server/ollama/eoh-llama3.2-source-router.Modelfile
ollama create eoh-llama:70b                -f server/ollama/eoh-llama3.1-70b.Modelfile

# Verify
ollama list
```

---

## Version History

- **2026-04-25** — **eoh-llama:70b** Modelfile (`server/ollama/eoh-llama3.1-70b.Modelfile`) added: lean synthesis-only profile, 16K ctx. `mkg_retrieval_harness.py` now wires the **eoh-llama3.2-source-router** in front of retrieval (TS-term expansion + semantic_query rewrite mirrors `/ask_stream`'s `extract_qna_terms` -> `search_source_ts_for_terms`) and accepts `--synth-model` (or `MKG_SYNTH_MODEL` via `portalnode4090_mkg_harness.sh`) so the final markdown synthesis can be served by **eoh-llama:70b** while the 8B model continues to handle planning and ANN scoring.
- **2026-04-24** — **eoh-llama** (q8_0, 4090) Modelfile: timeline ingest framing, full PTV toolkit + MKG pilot `source` dictionary, 32K. **eoh-llama-lucifer** (4050): 16K, PTV toolkit, MKG pointer to Python + main Modelfile. `OLLAMA_NUM_CTX` defaults 16K in PTV agent / harness unless set (4090 `portalnode4090_mkg_harness.sh` forces 32K + `eoh-llama`).
- **2026-04-13** — Initial roster. 8B Lucifer build tested end-to-end (nascent run, 9.5 min, 8 rounds). 8B q8_0 and 70B q4_K_M builds planned for RISE on-prem deployment.
