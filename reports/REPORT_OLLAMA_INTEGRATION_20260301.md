# Ollama Integration Report

**Date:** 2026-03-01  
**Status:** Implementation complete — ready to run  
**Relates to:** `REPORT_PATIENT_TIMELINE_VISION_ARCHITECTURE_APPENSION_20260327.md` §5, §P0

---

## What Was Done

All code changes are already merged. This report documents what was implemented, why, and how to operate it.

### Changes made in this session

| File | Change |
|------|--------|
| `server/llm/llm_client.py` | Added `get_ollama_client(base_url, api_key)` factory |
| `server/api/stream_config.py` | Added `INGESTION_MODEL` and `OLLAMA_BASE_URL` env-var-backed constants |
| `server/eoh/timeline_summarizer.py` | Added `model` param to `_extract_events_from_pages_batch`, `_enrich_timeline_vision_connascence`, `_infer_llm_connascence_batched`; added `ingestion_client` + `ingestion_model` to `summarize_timeline_from_pdf`; fixed `augmented_rows` → `current_context` bug in `_run_eoh_gap_retrieval_for_timeline` |
| `server/scripts/run_eohd_timeline_pdf.py` | Added `--llm-backend`, `--ollama-url`, `--ingestion-model` CLI flags; made `OPENAI_API_KEY` conditional on backend |

---

## Architecture: Dual-Client Pattern

The pipeline splits into two logical tiers with independent clients:

```
PDF
  │
  ├─ INGESTION CLIENT (can be Ollama)
  │     Event extraction: _extract_events_from_pages_batch
  │     Connascence rules: _infer_llm_connascence_batched
  │     (structured JSON parsing, pattern matching — no frontier reasoning needed)
  │
  └─ SUMMARY CLIENT (stays on OpenAI gpt-4.1)
        Hierarchical map chunks: summarize_timeline_for_eoh
        Final reduce: _hierarchical_reduce
        (clinical narrative synthesis — quality-critical, justify the cost)
```

When `--llm-backend ollama`, ingestion client = Ollama local model, summary client = OpenAI.  
When `--llm-backend ollama-full`, both clients point at Ollama.  
When `--llm-backend openai` (default), both clients are OpenAI — zero behaviour change.

The `ingestion_client=None` default in `summarize_timeline_from_pdf` falls back to the main `client`, so all existing callers outside the CLI work unchanged.

---

## How to Run

### Prerequisites

```bash
# Install Ollama (macOS)
brew install ollama

# Start the server (background daemon)
ollama serve &

# Pull the ingestion model (one-time, ~4.7GB)
ollama pull llama3.1:8b

# Verify it's running
curl http://localhost:11434/api/tags
```

### Run with Ollama ingestion (recommended — saves ~80-90% of token cost)

```bash
cd 2ndOpinionMD-MVP/server

python3 -u scripts/run_eohd_timeline_pdf.py \
    "../data/patient_timelines/NormanEricRoberts_decrypted.pdf" \
    --artifact-dir "$OUT" \
    --extraction-mode full \
    --llm-backend ollama \
    --ingestion-model llama3.1:8b
```

OPENAI_API_KEY is still required — it's used for the narrative summarization (9 map chunks + 1 reduce). Everything else runs locally.

### Run entirely without OpenAI (blocked on credits)

```bash
python3 -u scripts/run_eohd_timeline_pdf.py \
    "../data/patient_timelines/NormanEricRoberts_decrypted.pdf" \
    --artifact-dir "$OUT" \
    --extraction-mode full \
    --llm-backend ollama-full \
    --ingestion-model llama3.1:8b
```

No `OPENAI_API_KEY` needed. Summary quality will be lower than gpt-4.1 but the graph will be fully built. Use this while the card situation resolves.

### Custom Ollama host (GPU box, Docker, etc.)

```bash
python3 -u scripts/run_eohd_timeline_pdf.py ... \
    --llm-backend ollama \
    --ollama-url http://192.168.1.42:11434/v1 \
    --ingestion-model llama3.3:70b
```

### Environment variable equivalents (no CLI flags needed)

```bash
# .env or shell export
INGESTION_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434/v1
```

Set these and pass `--llm-backend ollama` — no `--ingestion-model` or `--ollama-url` needed.

---

## Model Selection Guide

### For ingestion (event extraction + connascence)

These calls do structured JSON parsing and pattern matching. They don't need frontier reasoning. Speed and JSON reliability matter more than intelligence.

| Model | Size | Speed | JSON quality | Notes |
|-------|------|-------|-------------|-------|
| `llama3.1:8b` | 4.7GB | Fast | Good | **Recommended default.** Fast enough to handle 23 batches in reasonable time. Reliably follows JSON format instructions. |
| `mistral-nemo` | 7.1GB | Fast | Very good | Excellent instruction following. Good alternative to llama3.1:8b. |
| `phi4` | 9.1GB | Moderate | Very good | Strong at structured output. Good for connascence reasoning. |
| `llama3.3:70b` | 43GB | Slow | Excellent | Use for connascence if quality is disappointing with 8b. Requires 48GB+ VRAM or fast NVMe offload. |
| `llama3.1:8b-instruct-q4_K_M` | 4.4GB | Fast | Good | Quantized — slightly smaller, same speed, very minor quality drop. |

### For summarization (`ollama-full` mode only)

The narrative summarization step generates the clinical summary from 6M chars of text across 9 map chunks + 1 reduce. This is where quality matters most.

| Model | Size | Notes |
|-------|------|-------|
| `llama3.3:70b` | 43GB | Best local option. Acceptable narrative quality for clinical text. |
| `llama3.1:70b` | 40GB | Slightly older, similar quality. |
| `mistral-large` | 69GB | Good clinical reasoning. |
| `gpt-4.1` (OpenAI) | — | **Keep this for production summarization.** The quality gap is real for complex clinical narratives. |

**Recommendation:** Use `--llm-backend ollama` (not `ollama-full`) for production. Local for ingestion, OpenAI for the summary.

---

## What Each Call Does in Ollama Mode

### Event extraction (`_extract_events_from_pages_batch`)

- **Input:** JSON payload of ~180 pages with raw PDF text per page
- **Output:** `{"pages": [{"page_num": N, "events": [{event_type, timestamp, preview}]}]}`
- **Why local is fine:** This is structured information extraction. The model is given explicit field names and types. `llama3.1:8b` reliably produces this format with `response_format={"type": "json_object"}`.
- **Calls per full run:** ~23 (full mode), ~4-5 (lite mode)

### Connascence LLM inference (`_infer_llm_connascence_batched`)

- **Input:** Batch of 300 events with event_id, type, timestamp, preview + the rubric
- **Output:** `{"edges": [{event_a_id, event_b_id, type, reasoning}]}`
- **Why local is fine:** Pattern matching against well-defined rubric criteria. The model compares pairs of events and decides if they describe the same condition (diagnostic) or the same lab test over time (lab_trend). `llama3.1:8b` handles this well.
- **Calls per full run:** 2-8 (depending on event type distribution)

### Narrative summarization (stays on OpenAI by default)

- **Map:** 9 × ~700K char chunks → individual clinical summaries
- **Reduce:** Combine 9 summaries + enriched graph → final comprehensive summary
- **Why OpenAI stays:** This is the product deliverable. The narrative quality, clinical depth, and diagnostic reasoning in the final summary directly impact clinical utility. The cost of 10 gpt-4.1 calls is justified.

---

## `response_format` Compatibility with Ollama

Ollama models support `response_format={"type": "json_object"}` for models that have been fine-tuned for instruction following. For `llama3.1:8b` and `mistral-nemo`, this works reliably.

**If a model ignores the format parameter** (older or unquantized versions), the pipeline falls back gracefully: `_extract_events_from_pages_batch` has a keyword-based `_reclassify_event_types` post-pass that rescues badly-typed events, and the JSON parsing is wrapped in `try/except` at every call site.

**Important:** Ollama does not support `response_format` with `stream=True`. The pipeline does not use streaming for extraction or connascence, so this is not an issue.

---

## Cost Analysis

### Current cost for Norman Roberts (4,223 pages) — OpenAI only

| Step | Model | Input tokens (est.) | Output tokens (est.) | Cost (est.) |
|------|-------|---------------------|----------------------|-------------|
| Event extraction × 23 batches | gpt-4.1 | ~2.2M × 23 ≈ 50M | 32K × 23 ≈ 736K | ~$10-15 |
| Connascence LLM × 4 batches | gpt-4.1 | ~50K × 4 ≈ 200K | 4K × 4 ≈ 16K | ~$0.50 |
| Map summarization × 9 chunks | gpt-4.1 | 700K × 9 ≈ 6.3M | 4K × 9 ≈ 36K | ~$2-3 |
| Final reduce | gpt-4.1 | ~200K | ~8K | ~$0.50 |
| **Total** | | | | **~$13-19 per run** |

### Cost with `--llm-backend ollama`

| Step | Backend | Cost |
|------|---------|------|
| Event extraction × 23 batches | Ollama local | **$0** |
| Connascence LLM × 4 batches | Ollama local | **$0** |
| Map summarization × 9 chunks | OpenAI gpt-4.1 | ~$2-3 |
| Final reduce | OpenAI gpt-4.1 | ~$0.50 |
| **Total** | | **~$2.50-3.50 per run** |

**~85% cost reduction.** The remaining cost is the part where quality matters most.

---

## Upgrading: Other Models to Consider

### `nomic-embed-text` for future `TimelineChart` embeddings

When `TimelineChart` is built (next priority per the appension), local embeddings replace OpenAI's `text-embedding-3-small`:

```bash
ollama pull nomic-embed-text
```

This is not wired yet — it belongs in `timeline_chart.py`. Note: as stated in the architecture report, `sentence-transformers/all-MiniLM-L6-v2` (already a dependency via `RepoChart`) is preferred over Ollama for embeddings because it runs in-process with no HTTP overhead.

### `phi4` for better connascence reasoning

If `llama3.1:8b` produces sparse connascence edges after the first full run, try `phi4`:

```bash
ollama pull phi4
python3 -u scripts/run_eohd_timeline_pdf.py ... --llm-backend ollama --ingestion-model phi4
```

Phi-4 has stronger reasoning for relationship inference tasks within the 9B parameter class.

---

## Files Changed

```
server/llm/llm_client.py
  + get_ollama_client(base_url, api_key) → AsyncOpenAI

server/api/stream_config.py
  + INGESTION_MODEL = os.getenv("INGESTION_MODEL", EOH_TIMELINE_SUMMARIZER_MODEL)
  + OLLAMA_BASE_URL  = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")

server/eoh/timeline_summarizer.py
  + import INGESTION_MODEL, OLLAMA_BASE_URL from stream_config
  + _extract_events_from_pages_batch(client, pages, model=INGESTION_MODEL)
  + _enrich_timeline_vision_connascence(vision, client, question, model=INGESTION_MODEL)
  + _infer_llm_connascence_batched(..., model=INGESTION_MODEL)
  + _run_timeline_enrichment_gap_synthesis_connascence(..., ingestion_client, ingestion_model)
  + summarize_timeline_from_pdf(..., ingestion_client=None, ingestion_model=INGESTION_MODEL)
  FIX: augmented_rows → current_context in _run_eoh_gap_retrieval_for_timeline

server/scripts/run_eohd_timeline_pdf.py
  + --llm-backend {openai,ollama,ollama-full}  (default: openai)
  + --ollama-url URL
  + --ingestion-model MODEL
  + OPENAI_API_KEY check conditional on backend
  + dual-client construction (summary_client vs ingestion_client)
```

---

## Immediate Next Step

```bash
# Pull the model
ollama pull llama3.1:8b

# Run the first full extraction — all 4,223 pages, zero API cost for ingestion
cd 2ndOpinionMD-MVP/server
python3 -u scripts/run_eohd_timeline_pdf.py \
    "../data/patient_timelines/NormanEricRoberts_decrypted.pdf" \
    --artifact-dir "$OUT" \
    --extraction-mode full \
    --llm-backend ollama \
    --ingestion-model llama3.1:8b \
    -v
```

Watch for: `Connascence RULE 1 complete: N temporal edges` — if N is in the hundreds, the extraction + classification is working. If N is still in the teens, the event type reclassification pass needs attention (timestamps or type coverage).

---

*Report generated 2026-03-01. All code changes are already committed to the working tree.*
