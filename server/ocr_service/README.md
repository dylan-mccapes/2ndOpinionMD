# 2OPMD OCR Forge

CUDA-accelerated OCR service for image-only PDF pages.

The timeline ingestion pipeline uses `pypdf` to extract text — fast, but it
returns empty strings for scanned/image-only pages. The Forge fills that gap:
it rasterizes the requested pages with `pypdfium2`, runs them through
`EasyOCR` on the GPU, and returns structured text keyed by page number.

Runs as a standalone FastAPI service so it can be hosted on the GPU box and
called over the LAN — same pattern as Ollama.

---

## Quick Start

### 1. One-time setup

From repo root, inside WSL:

```bash
bash server/ocr_service/setup.sh
```

This creates `server/ocr_service/.OcrForge/` (the venv) and installs:

- PyTorch + torchvision (CUDA 12.1 wheels — runs fine on CUDA 12.4 hosts)
- EasyOCR (~200 MB of detection + recognition models download on first use)
- pypdfium2 (PDF rasterizer, pure-pip, no poppler dependency)
- FastAPI + uvicorn + httpx

The script prints CUDA visibility at the end so you know the GPU is usable.

### 2. Launch the service

```bash
bash server/ocr_service/run.sh
```

Default binding: `0.0.0.0:8765` (LAN-accessible, same convention as Ollama).

EasyOCR downloads its models on first request (~200 MB). Subsequent launches
reuse the cached models in `~/.EasyOCR/`.

### 3. Verify

From another terminal:

```bash
curl -s http://localhost:8765/health | jq .
```

Expected when ready:

```json
{
  "status": "ready",
  "device": "cuda",
  "gpu_available": true,
  "gpu_requested": true,
  "languages": ["en"],
  "ready": true,
  "init_error": null
}
```

From the M2 server (or any LAN host):

```bash
curl -s http://192.168.0.245:8765/health
```

---

## Endpoints

| Method | Path                   | Purpose |
|--------|------------------------|---------|
| GET    | `/health`              | Engine status, device, GPU availability |
| POST   | `/ocr/image`           | OCR a single image (multipart `file`) |
| POST   | `/ocr/pdf`             | OCR every page of a PDF |
| POST   | `/ocr/pdf/range`       | OCR a subset of pages (start/end or CSV) |
| POST   | `/ocr/pdf/page_count`  | Return PDF page count (no OCR) |

### `POST /ocr/pdf` example

```bash
curl -s -X POST http://localhost:8765/ocr/pdf \
    -F "file=@data/patient_timelines/NormanEricRoberts_decrypted.pdf" \
    -F "dpi=220" \
    -F "skip_empty=true" | jq '.pages_with_text, .total_seconds'
```

Response shape:

```json
{
  "filename": "NormanEricRoberts_decrypted.pdf",
  "pages": {
    "17": "Patient reports...",
    "42": "CBC: WBC 6.2, HGB 13.1..."
  },
  "page_count_processed": 4223,
  "pages_with_text": 198,
  "total_chars": 88421,
  "ocr_seconds": 182.4,
  "total_seconds": 205.1,
  "device": "cuda",
  "dpi": 220
}
```

### `POST /ocr/pdf/range` example (only OCR the pages pypdf missed)

```bash
curl -s -X POST http://localhost:8765/ocr/pdf/range \
    -F "file=@timeline.pdf" \
    -F "pages_csv=17,42,103,577" \
    -F "dpi=220"
```

---

## Environment variables

| Variable                | Default                   | Meaning |
|-------------------------|---------------------------|---------|
| `OCR_FORGE_HOST`        | `0.0.0.0`                 | Bind host |
| `OCR_FORGE_PORT`        | `8765`                    | Bind port |
| `OCR_FORGE_LANGS`       | `en`                      | Comma-separated EasyOCR languages |
| `OCR_FORGE_GPU`         | `1`                       | `0` to force CPU |
| `OCR_FORGE_MODEL_DIR`   | `~/.EasyOCR/`             | Override EasyOCR model cache |
| `OCR_FORGE_WORKERS`     | `1`                       | Must stay `1` — single GPU-resident engine |
| `TORCH_INDEX_URL`       | `https://download.pytorch.org/whl/cu121` | PyTorch wheel index used by `setup.sh` |

---

## Calling the service from the main 2OPMD server

The `.BeatingHeart` venv already has `httpx`. A thin async client lives at
`server/ocr_service/client.py`:

```python
from server.ocr_service.client import OcrForgeClient

async with OcrForgeClient("http://192.168.0.245:8765") as forge:
    if await forge.health():
        pages = await forge.ocr_pdf_range(
            "data/patient_timelines/NormanEricRoberts_decrypted.pdf",
            pages=[17, 42, 103],
            dpi=220,
        )
        # pages is {17: "...", 42: "...", 103: "..."}
```

Set `OCR_FORGE_URL` in `.env` once the service is stable so callers pick it
up automatically:

```ini
OCR_FORGE_URL=http://192.168.0.245:8765
```

The natural integration point in the ingestion pipeline is
`run_eohd_timeline_pdf.py` / `timeline_summarizer.py` — after the `pypdf`
extract, collect page numbers with empty text and ship them to the forge in
one `ocr_pdf_range` call. The forge returns a `{page_num: text}` map that can
be merged back into the page list before graph extraction.

---

## Performance notes

On an RTX 4090 with `cu121` wheels:

| Workload                     | Latency     | Notes |
|------------------------------|-------------|-------|
| First request (cold)         | 4–6 s       | CUDA kernel JIT |
| 220 DPI A4 page, dense text  | 180–350 ms  | Steady state |
| 220 DPI A4 page, sparse text | 80–150 ms   | Few detections |
| 4,000-page PDF, full OCR     | 15–25 min   | End-to-end |

Raise DPI to 300 for dense forms (labs, structured reports). Drop to 150 for
born-digital scans with clean text. `max_dimension` caps the long edge of
each rasterized page to protect VRAM; 4000 is safe on a 24 GB card.

Only one engine lives in memory at a time — keep `OCR_FORGE_WORKERS=1`. For
higher throughput, run multiple instances on different ports behind a round
robin.

---

## Troubleshooting

- **`cuda available: False`** — PyTorch wheel has no CUDA. Rerun
  `setup.sh`; make sure `TORCH_INDEX_URL` points at a CUDA wheel index, not
  the CPU-only default `pypi.org`.
- **`RuntimeError: CUDA out of memory`** — lower `dpi` (e.g. `dpi=180`) or
  `max_dimension` (e.g. `max_dimension=3000`) in the request.
- **Empty text for a page that is clearly readable** — bump `dpi` to 300;
  handwritten or faded scans may need `easyocr.Reader(..., recognizer="standard")`
  tuning (edit `ocr_engine.py`).
- **Model download hangs on first launch** — EasyOCR fetches ~200 MB from
  S3. Pre-download into `OCR_FORGE_MODEL_DIR` and restart.

---

## File map

```
server/ocr_service/
  __init__.py
  app.py                 FastAPI app (lifespan boot, endpoints)
  ocr_engine.py          EasyOCR wrapper (thread-safe, warmup)
  pdf_utils.py           pypdfium2-based rasterizer
  client.py              Async HTTP client for the main server
  requirements.txt       Service deps (torch installed separately)
  setup.sh               Builds .OcrForge venv + installs deps
  run.sh                 Launches uvicorn on .OcrForge
  README.md              This file
```
