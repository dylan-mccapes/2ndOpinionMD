# Ollama POC Debug Status Report — M2 Ultra
**Date**: 2026-03-27  
**Patient**: NormanEricRoberts (4,223-page PDF, 6.1M chars)  
**Hardware**: Apple M2 Ultra (192 GB unified memory)  
**Model**: `llama3.1:8b` via Ollama `http://localhost:11434/v1`  
**Status**: ❌ PDF event extraction failing on every batch

---

## 1. What the Pipeline Does

```
PDF (4,223 pages)
  └─ pypdf text extract (all pages, sequential)
       └─ PatientTimelineVision.seed (empty graph)
            └─ [FAILING HERE] Batched LLM extraction (71 batches × ~56 pages each)
                 └─ PatientTimelineVision enrichment (temporal, LLM connascence)
                      └─ Gap / synthesis narrative
                           └─ TimelineSummaries → EoHD
```

The PDF event extraction phase is the only piece using the ingestion LLM. Everything upstream (pypdf) and downstream (graph enrichment) is fine. The pipeline completes even on full batch failure — each failed batch falls back to one generic `page` event per input page (no clinical information, just a placeholder).

---

## 2. Current Invocation Command

```bash
python3 -u scripts/run_eohd_timeline_pdf.py \
  ../data/patient_timelines/NormanEricRoberts_decrypted.pdf \
  --llm-backend ollama-full \
  --extraction-mode full \
  --ingestion-model llama3.1:8b \
  --artifact-dir "../artifacts/timeline_ollama_$(date +%Y%m%d_%H%M)" \
  2>&1 | tee "../artifacts/ollama_run_$(date +%Y%m%d_%H%M).log"
```

Key resolved parameters (from `run_eohd_timeline_pdf.py`):
| Parameter | Value |
|---|---|
| `backend` | `ollama-full` |
| `ingestion_model` | `llama3.1:8b` |
| `ollama_url` | `http://localhost:11434/v1` |
| `ingestion_context_tokens` | `32_768` (auto-default for Ollama backends) |
| `extraction_mode` | `full` (all 4,223 pages) |

---

## 3. Batch Sizing Logic

File: `server/eoh/timeline_summarizer.py`, around line 3533.

With `ingestion_context_tokens = 32_768`:

```python
_small_output_reserve = max(2048, 32768 // 4)   # = 8192  (25% for output)
_small_system_reserve = max(512,  32768 // 16)   # = 2048  (6%  for system prompt)
_batch_max_chars = int(
    (32768 - 8192 - 2048) * 4.0                 # = 90112 chars per batch
)
```

**Result**: 4,223 pages → 71 batches, max ~90,112 input chars/batch.  
Each batch is ~56 pages at ~1,600 chars/page = 22,400 chars ≈ 5,600 tokens input.

**Important**: The ingestion model is told to allocate `num_ctx=65_536` via `options` in the Ollama API body — twice the `ingestion_context_tokens` used for batch sizing. This was intended to give Ollama a 65K context while keeping input payloads sized for 32K, providing comfortable generation headroom.

---

## 4. Ollama Client Detection Logic

File: `server/eoh/timeline_summarizer.py`, lines 3437–3441.

```python
_base_url = str(getattr(getattr(_ingestion_client, "_base_url", None), "host", "") or "")
_force_json_format: bool = "localhost" not in _base_url and "127.0.0.1" not in _base_url
_ollama_num_ctx: Optional[int] = None if _force_json_format else 65536
```

For `AsyncOpenAI(base_url="http://localhost:11434/v1")`:
- `_ingestion_client._base_url` is an `httpx.URL` object
- `.host` = `"localhost"`
- `_force_json_format` = `False` ✓
- `_ollama_num_ctx` = `65536` ✓

This correctly routes to the Ollama code path.

---

## 5. The Extraction Function — Current Code

File: `server/eoh/timeline_summarizer.py`, functions `_ollama_chat_direct` and `_extract_events_from_pages_batch`.

### 5a. `_ollama_chat_direct` (new as of today)

```python
async def _ollama_chat_direct(base_url, model, messages, max_tokens=8192,
                               temperature=0.1, num_ctx=None, timeout=600.0) -> str:
    import httpx
    endpoint = base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": model, "messages": messages,
        "max_tokens": max_tokens, "temperature": temperature, "stream": False,
    }
    if num_ctx:
        body["options"] = {"num_ctx": num_ctx}

    async with httpx.AsyncClient(timeout=timeout) as http:
        resp = await http.post(endpoint, json=body,
            headers={"Authorization": "Bearer ollama", "Content-Type": "application/json"})

    raw_bytes = resp.content
    if resp.status_code != 200:
        raise RuntimeError(f"Ollama HTTP {resp.status_code}: {raw_bytes[:300]}")
    if not raw_bytes or not raw_bytes.strip():
        raise ValueError("Ollama returned HTTP 200 with empty body ...")

    data = json.loads(raw_bytes)

    # NEW diagnostic guards (added today after persistent failures):
    if "error" in data:
        raise RuntimeError(f"Ollama returned error in body: {data['error']}")
    choices = data.get("choices") or []
    if not choices:
        logger.warning("Ollama chat: no 'choices' in response body. Keys: %s", list(data.keys()))
        raise ValueError(f"Ollama response missing 'choices' (keys: {list(data.keys())})")

    content = choices[0].get("message", {}).get("content") or ""
    if not content:
        logger.warning("Ollama chat returned empty content. finish_reason=%s | choice: %s",
                       choices[0].get("finish_reason"), choices[0])
    return content
```

### 5b. In `_extract_events_from_pages_batch`

```python
if force_json_format:          # OpenAI path
    resp = await _llm_chat_completion_async(client, model, messages, **call_kwargs)
    raw_content = _safe_get_choice_content(resp) or ""
else:                          # Ollama path — httpx direct
    _ollama_url = str(client.base_url).rstrip("/")
    raw_content = await _ollama_chat_direct(
        base_url=_ollama_url, model=model, messages=...,
        max_tokens=8192, temperature=0.1, num_ctx=ollama_num_ctx,
    )

raw_content = _strip_markdown_fences(raw_content)
if not raw_content.strip():
    raise ValueError("LLM returned empty content after fence-stripping")
parsed = json.loads(raw_content)
```

---

## 6. The Persistent Error

### Observed error (all three runs today)

```
❌ Batched PDF event extraction failed for pages {1..56}: Expecting value: line 1 column 1 (char 0)
```

This is `json.JSONDecodeError` with the canonical "empty string" message.

### Timeline of attempts

| Run | Fix applied | Error |
|---|---|---|
| Run 1 | Baseline (OpenAI SDK + `extra_body={"num_ctx": 65536}`) | `Expecting value: line 1 column 1 (char 0)` |
| Run 2 | Fixed `extra_body` → `{"options": {"num_ctx": 65536}}` | `Expecting value: line 1 column 1 (char 0)` |
| Run 3 | Replaced OpenAI SDK with `httpx` direct call | `Expecting value: line 1 column 1 (char 0)` |

The error is unchanged across all three attempts despite fundamentally different call paths.

### What this means

**The error is NOT coming from our own `json.loads(raw_content)` call** in `_extract_events_from_pages_batch`. That call is guarded by `_safe_get_choice_content(...) or "{}"` (OpenAI path) and a fresh `if not raw_content.strip(): raise ValueError(...)` guard (Ollama path). Neither should produce `Expecting value: line 1 column 1 (char 0)`.

**The error IS coming from `json.loads(raw_bytes)` inside `_ollama_chat_direct`**. Ollama returns HTTP 200 with a non-empty body (takes 3m37s to complete, matching full 8192-token generation at ~40 tok/s), but the body is not JSON — it passes the `raw_bytes.strip()` emptiness check but fails `json.loads`.

The most likely content of `raw_bytes`: a streaming SSE response (`data: {"choices":[...]}\n\ndata: [DONE]\n\n`) even though we send `"stream": false`. Ollama may be defaulting to streaming mode and ignoring `stream=false` in the request body.

Evidence for this:
- Each batch takes 3–4 minutes (matches 8192-token generation time at ~40 tok/s)
- Ollama shows HTTP 200 after the full generation time
- Body is non-empty (passes our `raw_bytes.strip()` check)
- `json.loads(raw_bytes)` fails — SSE format is not JSON

---

## 7. What the Next Run Will Reveal

The NEW diagnostic guards added today (`"error" in data` check, `choices` check, warning logs) will fire for the first time on the next run and reveal one of these scenarios:

### Scenario A — Streaming response  
`json.loads(raw_bytes)` raises `JSONDecodeError`  
→ Error message: `Expecting value: line 1 column 1 (char 0)`  
→ Confirm by logging `raw_bytes[:200]` before `json.loads`

### Scenario B — Ollama error body  
`json.loads(raw_bytes)` succeeds, `"error" in data`  
→ Error message: `Ollama returned error in body: <error text>`  
→ This would reveal the actual Ollama error (e.g., "context limit exceeded")

### Scenario C — Missing choices  
`json.loads(raw_bytes)` succeeds, no `choices` key  
→ Warning: `Ollama chat: no 'choices' in response body. Keys present: [...]`  
→ Reveals unexpected response structure

### Scenario D — Empty content string  
All passes, `content = ""` or `content = None`  
→ Warning: `Ollama chat returned empty content string. finish_reason=...`  
→ `ValueError("LLM returned empty content after fence-stripping")` is raised  
→ The logged `finish_reason` reveals if model stopped early (`stop`, `length`, etc.)

---

## 8. Hypotheses (Ranked by Likelihood)

### H0 — httpx `async with` scope closed before response body was read — **FIXED in latest commit**
`resp.content` was being read **outside** the `async with httpx.AsyncClient()` block. For long chunked responses (3–4 minutes), httpx uses chunked transfer-encoding and buffers the body lazily. Closing the client before reading `resp.content` returns empty bytes — which then causes `json.loads(b"")` → `Expecting value: line 1 column 1 (char 0)`.

**This matches the symptom exactly.** The 3m37s timing confirms the model IS generating the full 8192 tokens; the body was just discarded by the closed client.

**Fix applied**: `raw_bytes = resp.content` and `status_code = resp.status_code` are now read INSIDE the `async with` block.

### H1 — Streaming response despite `stream: false` (MEDIUM)
Ollama may be ignoring `"stream": false` in the request body when sent via direct `httpx.post`. Result: SSE body (`data: {...}\n\n`) which fails `json.loads`.

**Fix**: Add `"Accept": "application/json"` header (not `text/event-stream`).

### H2 — `num_ctx` in `options` not applied on `/v1` endpoint (MEDIUM)
Ollama may only honour `options.num_ctx` on its native `/api/chat`, not on the OpenAI-compatible `/v1/chat/completions`. Result: 16GB KV cache → Metal buffer pressure → silent generation failure.

**Fix**: Use Ollama's native `/api/chat` endpoint.

### H3 — Batch too large for llama3.1:8b (MEDIUM)
56 pages × ~1,600 chars/page ≈ 5,600 input tokens. Output request = 8,192 tokens. Total ≈ 13,800 tokens. Fits in context, but the model may not be able to produce coherent structured JSON for 56 pages.

**Fix**: `--ingestion-context-tokens 8192` → ~14 pages/batch.

---

## 9. Immediate Action Item — One-Line Diagnosis

Add this to `_ollama_chat_direct` before `json.loads(raw_bytes)`:

```python
logger.warning("OLLAMA RAW BYTES (first 500): %r", raw_bytes[:500])
```

Run once and read the log. This will immediately reveal whether it's streaming SSE, an error body, or something else entirely.

---

## 10. Code Locations

| Component | File | Lines |
|---|---|---|
| CLI entry point | `server/scripts/run_eohd_timeline_pdf.py` | 78–291 |
| Ollama client factory | `server/llm/llm_client.py` | 18–36 |
| Ollama detection + batch sizing | `server/eoh/timeline_summarizer.py` | 3429–3574 |
| `_ollama_chat_direct` (httpx bypass) | `server/eoh/timeline_summarizer.py` | 2974–3055 |
| `_extract_events_from_pages_batch` | `server/eoh/timeline_summarizer.py` | 3057–3185 |
| `_strip_markdown_fences` | `server/eoh/timeline_summarizer.py` | 2957–2971 |
| `_safe_get_choice_content` | `server/eoh/timeline_summarizer.py` | 1024–1031 |
| Batch-size iteration | `server/eoh/timeline_summarizer.py` | ~2920–2954 |

---

## 11. Environment

```
Hardware:       Apple M2 Ultra, 192 GB unified memory
OS:             macOS (darwin 24.6.0)
Python:         3.x in .BeatingHeart venv
Ollama version: running at localhost:11434 (version unknown)
Model:          llama3.1:8b (Q4_K_M ≈ 4.7 GB)
KV cache:       intended 65536 ctx → 8 GB Metal buffer
                actual (if H2 correct) 131072 ctx → 16 GB Metal buffer
```

---

## 12. Recommended Next Step for Opus

**Option A (5-minute diagnosis)**: Add `logger.warning("OLLAMA RAW BYTES: %r", raw_bytes[:500])` before `json.loads(raw_bytes)` in `_ollama_chat_direct` and re-run. Read the first warning log line.

**Option B (likely correct fix based on H1)**: Switch from Ollama's OpenAI-compatible `/v1/chat/completions` to the native `/api/chat` endpoint. The native API is more stable, properly handles `options.num_ctx`, and has clearer streaming semantics:

```python
# Native Ollama /api/chat format
body = {
    "model": model,
    "messages": messages,
    "stream": False,
    "options": {"num_ctx": num_ctx, "num_predict": max_tokens},
}
resp = await http.post(f"{ollama_host}/api/chat", json=body)
data = resp.json()
content = data.get("message", {}).get("content", "")
```

Note: the native endpoint's base URL is `http://localhost:11434` (no `/v1` suffix).

**Option C (H3 workaround)**: Reduce batch size drastically:
```bash
--ingestion-context-tokens 8192
```
This gives ~14 pages/batch (500+ total batches) but each call is trivially small for the model.
