"""
FastAPI app for the 2OPMD OCR Forge service.

Endpoints:
    GET  /health                - engine status + GPU availability
    POST /ocr/image              - OCR a single image file
    POST /ocr/pdf                - OCR all pages of a PDF
    POST /ocr/pdf/range          - OCR a subset of PDF pages
    POST /ocr/pdf/page_count     - just count pages (no OCR)

Run with:
    bash server/ocr_service/run.sh
or directly:
    uvicorn server.ocr_service.app:app --host 0.0.0.0 --port 8765
"""
from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from server.ocr_service.ocr_engine import OcrEngine
from server.ocr_service.pdf_utils import pdf_page_count, rasterize_pdf_pages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ocr_forge")

_engine: Optional[OcrEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _engine
    languages_env = os.getenv("OCR_FORGE_LANGS", "en")
    languages = [x.strip() for x in languages_env.split(",") if x.strip()]
    gpu = os.getenv("OCR_FORGE_GPU", "1") not in ("0", "false", "False")
    model_dir = os.getenv("OCR_FORGE_MODEL_DIR") or None

    logger.info(
        "Starting OCR Forge (langs=%s, gpu=%s, model_dir=%s)",
        languages, gpu, model_dir,
    )
    _engine = OcrEngine(languages=languages, gpu=gpu, model_storage_dir=model_dir)
    try:
        _engine.warmup()
    except Exception as e:
        logger.error("OCR engine warmup failed; service will be degraded: %s", e)

    yield

    _engine = None
    logger.info("OCR Forge shutting down")


app = FastAPI(
    title="2OPMD OCR Forge",
    version="0.1.0",
    description="CUDA-accelerated OCR service for image-only PDFs.",
    lifespan=lifespan,
)


def _require_engine() -> OcrEngine:
    if _engine is None:
        raise HTTPException(status_code=503, detail="OCR engine not initialized")
    return _engine


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    if _engine is None:
        return JSONResponse(status_code=503, content={"status": "starting"})
    return {"status": "ready", **_engine.status()}


# ---------------------------------------------------------------------------
# Image OCR
# ---------------------------------------------------------------------------

@app.post("/ocr/image")
async def ocr_image(file: UploadFile = File(...)) -> Dict[str, Any]:
    engine = _require_engine()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    t0 = time.perf_counter()
    try:
        text = engine.ocr_image_bytes(data)
    except Exception as e:
        logger.exception("OCR image failed")
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

    return {
        "filename": file.filename,
        "text": text,
        "char_count": len(text),
        "elapsed_s": round(time.perf_counter() - t0, 3),
        "device": engine.device,
    }


# ---------------------------------------------------------------------------
# PDF OCR
# ---------------------------------------------------------------------------

def _ocr_pdf_pages(
    engine: OcrEngine,
    pdf_bytes: bytes,
    pages: Optional[List[int]],
    dpi: int,
    max_dimension: int,
    skip_empty: bool,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    results: Dict[int, str] = {}
    rendered_pages = 0
    ocr_seconds = 0.0

    for page_num, pil in rasterize_pdf_pages(
        pdf_bytes, pages=pages, dpi=dpi, max_dimension=max_dimension,
    ):
        rendered_pages += 1
        tp = time.perf_counter()
        text = engine.ocr_pil_image(pil)
        ocr_seconds += time.perf_counter() - tp
        if skip_empty and not text.strip():
            continue
        results[page_num] = text

    total = time.perf_counter() - t0
    return {
        "pages": {str(k): v for k, v in sorted(results.items())},
        "page_count_processed": rendered_pages,
        "pages_with_text": len(results),
        "total_chars": sum(len(v) for v in results.values()),
        "ocr_seconds": round(ocr_seconds, 3),
        "total_seconds": round(total, 3),
        "device": engine.device,
        "dpi": dpi,
    }


@app.post("/ocr/pdf/page_count")
async def pdf_pages(file: UploadFile = File(...)) -> Dict[str, Any]:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    return {"filename": file.filename, "page_count": pdf_page_count(data)}


@app.post("/ocr/pdf")
async def ocr_pdf(
    file: UploadFile = File(...),
    dpi: int = Query(220, ge=72, le=600),
    max_dimension: int = Query(4000, ge=500, le=10000),
    skip_empty: bool = Query(False),
) -> Dict[str, Any]:
    engine = _require_engine()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    try:
        out = _ocr_pdf_pages(
            engine, data, pages=None, dpi=dpi,
            max_dimension=max_dimension, skip_empty=skip_empty,
        )
    except Exception as e:
        logger.exception("OCR pdf failed")
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

    out["filename"] = file.filename
    return out


@app.post("/ocr/pdf/range")
async def ocr_pdf_range(
    file: UploadFile = File(...),
    start_page: int = Form(1),
    end_page: Optional[int] = Form(None),
    dpi: int = Form(220),
    max_dimension: int = Form(4000),
    skip_empty: bool = Form(False),
    pages_csv: Optional[str] = Form(
        None,
        description="Optional comma-separated 1-indexed page list (overrides start/end).",
    ),
) -> Dict[str, Any]:
    engine = _require_engine()
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    if pages_csv:
        try:
            pages = [int(x.strip()) for x in pages_csv.split(",") if x.strip()]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Bad pages_csv: {e}")
    else:
        n_total = pdf_page_count(data)
        end = end_page if end_page is not None else n_total
        start = max(1, start_page)
        end = min(n_total, end)
        if start > end:
            raise HTTPException(status_code=400, detail="start_page > end_page")
        pages = list(range(start, end + 1))

    try:
        out = _ocr_pdf_pages(
            engine, data, pages=pages, dpi=dpi,
            max_dimension=max_dimension, skip_empty=skip_empty,
        )
    except Exception as e:
        logger.exception("OCR pdf range failed")
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

    out["filename"] = file.filename
    out["requested_pages"] = pages
    return out
