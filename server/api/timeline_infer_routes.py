# server/api/timeline_infer_routes.py
"""
POST /api/timeline/{patient_id}/infer

Primary intake for patient timelines.  Accepts:
  1. PDF upload  (default — the normal case; patients receive PDFs)
  2. JSON upload (structured EHR export — set format=json)
  3. No file     (load existing events from ehr.patient_timeline)

Pipeline (PDF path):
  1. pypdf text extraction
  2. Heuristic pre-scan (regex dates, meds, labs, dx, ICD codes — ~0.5ms/page)
  3. Pre-scan events added to graph + temporal connascence auto-linked
  4. Batched LLM inference (8B corrects/supplements the skeleton)
  5. LLM events merged into graph + final temporal connascence pass

SSE event catalogue:
    accepted     { patient_id, model, format, ... }
    status       { phase, message, ... }
    pdf_read     { pages, pages_with_text, total_chars }
    pre_scan_done { events, dates, meds, labs, dx, temporal_edges }
    infer_start  { patient_id, total_batches, model, ... }
    batch_start  { batch, total, pages_in_batch, chars }
    batch_done   { batch, extracted, stored, elapsed_ms }
    graph_update { total_events, total_edges }
    batch_error  { batch, message }
    complete     { batches_processed, events_extracted, ... }
"""

from __future__ import annotations

import asyncio
import json
import logging
import textwrap
import time
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from server.api.stream_config import OLLAMA_BASE_URL
from server.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/timeline", tags=["timeline", "infer"])

# ---------------------------------------------------------------------------
# Inference lock — Ollama serves one request at a time on the GPU.
# A second caller gets an immediate 409 instead of hanging or crashing.
# ---------------------------------------------------------------------------
_infer_lock = asyncio.Lock()
_infer_active: Dict[str, Any] = {}  # metadata about the running job

# ---------------------------------------------------------------------------
# Constants tuned for eoh-llama 8B (32k context)
# ---------------------------------------------------------------------------
_DEFAULT_MODEL = "eoh-llama3.1:8b"
_DEFAULT_NUM_CTX = 32_768
_OUTPUT_RESERVE_RATIO = 0.50
_SYSTEM_PROMPT_TOKENS = 4_000
_CHARS_PER_TOKEN = 4
_OLLAMA_MAX_PAGES_PER_BATCH = 10  # char budget is the real constraint; this is a safety ceiling

_BATCH_MAX_INPUT_CHARS = int(
    (
        _DEFAULT_NUM_CTX * (1 - _OUTPUT_RESERVE_RATIO)
        - _SYSTEM_PROMPT_TOKENS
    )
    * _CHARS_PER_TOKEN
)

# Large-PDF limits
_MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB


# ---------------------------------------------------------------------------
# System prompt for structured extraction via 8B
# ---------------------------------------------------------------------------

_INFER_SYSTEM_PROMPT = textwrap.dedent("""\
    You are a precise medical event extraction agent running on a local
    eoh-llama 8B model.  Your task is to extract structured medical timeline
    events from patient clinical data.

    A HEURISTIC PRE-SCAN has already run over the raw text.  When a
    "--- PRE-SCAN SKELETON ---" block is present, it shows what regex
    extraction already found (dates, medications, labs, diagnoses, ICD codes).
    Your job:
      1. VERIFY the pre-scan findings (correct any errors)
      2. SUPPLEMENT with events the regex missed (symptoms, flares,
         treatment responses, clinical reasoning, visit context)
      3. ADD EDGES — when two events are clinically related, note the
         relationship type (causal, diagnostic, treatment, drug_response,
         lab_trend, symptom_cluster)

    For EACH clinically significant event, output a JSON object with:
    - "event_id": a short unique slug (e.g. "lab_crp_20240115")
    - "ts": ISO-8601 timestamp (best estimate; use "unknown" if absent)
    - "event_type": one of lab | symptom | medication | imaging | flare |
      visit | procedure | diagnosis | note
    - "text": brief narrative (1-2 sentences)
    - "structured": object with extracted values (lab values, med doses, etc.)
    - "confidence": 0.0-1.0

    Do NOT repeat pre-scan events verbatim unless you are correcting them.
    Focus your output tokens on what the regex COULD NOT find.

    Output a JSON array of event objects.  No markdown fences.  No commentary
    outside the JSON array.
""")


# ---------------------------------------------------------------------------
# PDF extraction (runs in thread pool for large files)
# ---------------------------------------------------------------------------

def _extract_pdf_pages(pdf_bytes: bytes, password: Optional[str] = None) -> List[Tuple[int, str]]:
    """
    Extract text from every page of a PDF.
    Returns [(page_num_1based, text), ...] for pages that have text.
    """
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(pdf_bytes))
    if reader.is_encrypted:
        if not password:
            raise ValueError("PDF is encrypted; provide the password field")
        if reader.decrypt(password) == 0:
            raise ValueError("Incorrect PDF password")

    pages: List[Tuple[int, str]] = []
    for idx, page in enumerate(reader.pages):
        text = (page.extract_text() or "").strip().replace("\x00", "")
        if text:
            pages.append((idx + 1, text))
    return pages


# ---------------------------------------------------------------------------
# JSON EHR parsing
# ---------------------------------------------------------------------------

class _TimelineEvent(BaseModel):
    ts: Optional[str] = None
    event_type: str = "note"
    source: str = "EHR"
    text: str = ""
    structured: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None


def _parse_json_ehr(raw: bytes) -> List[_TimelineEvent]:
    """
    Parse a structured EHR JSON upload.
    Accepts either a bare array of events or {"events": [...]}.
    """
    data = json.loads(raw)
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("events") or data.get("records") or data.get("timeline") or [data]
    else:
        raise ValueError("JSON must be an array of events or an object with an events key")
    return [_TimelineEvent(**item) if isinstance(item, dict) else item for item in items]


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------

def _chunk_pages(
    pages: List[Tuple[int, str]],
    max_chars: int = _BATCH_MAX_INPUT_CHARS,
    max_pages: int = _OLLAMA_MAX_PAGES_PER_BATCH,
) -> List[List[Tuple[int, str]]]:
    """
    Group PDF pages into batches respecting both char budget and page cap.
    Mirrors the batching strategy in timeline_summarizer for Ollama.
    """
    batches: List[List[Tuple[int, str]]] = []
    current: List[Tuple[int, str]] = []
    current_chars = 0

    for page_num, text in pages:
        page_chars = len(text) + 20  # overhead for "=== Page N ===" header
        would_exceed_chars = current and (current_chars + page_chars > max_chars)
        would_exceed_pages = len(current) >= max_pages

        if would_exceed_chars or would_exceed_pages:
            batches.append(current)
            current = []
            current_chars = 0

        current.append((page_num, text))
        current_chars += page_chars

    if current:
        batches.append(current)
    return batches


def _events_to_text_blocks(events: List[_TimelineEvent]) -> List[str]:
    blocks: List[str] = []
    for i, ev in enumerate(events, 1):
        parts = [f"=== Event {i} ==="]
        if ev.ts:
            parts.append(f"Date: {ev.ts}")
        parts.append(f"Type: {ev.event_type}  Source: {ev.source}")
        if ev.text:
            parts.append(ev.text)
        if ev.structured:
            parts.append(f"Structured: {json.dumps(ev.structured, default=str)}")
        blocks.append("\n".join(parts))
    return blocks


def _chunk_blocks(
    blocks: List[str],
    max_chars: int = _BATCH_MAX_INPUT_CHARS,
) -> List[List[str]]:
    batches: List[List[str]] = []
    current: List[str] = []
    current_chars = 0

    for block in blocks:
        block_chars = len(block) + 2
        if current and current_chars + block_chars > max_chars:
            batches.append(current)
            current = []
            current_chars = 0
        current.append(block)
        current_chars += block_chars

    if current:
        batches.append(current)
    return batches


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------

def _sse(event: str, data: Dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()


# ---------------------------------------------------------------------------
# Ollama connection (single persistent client, reused across all batches)
# ---------------------------------------------------------------------------

def _ollama_endpoint() -> str:
    host = OLLAMA_BASE_URL.rstrip("/")
    for suffix in ("/v1/chat/completions", "/v1"):
        if host.endswith(suffix):
            host = host[: -len(suffix)]
            break
    return f"{host}/api/chat"


import httpx as _httpx

_OLLAMA_POOL_LIMITS = _httpx.Limits(
    max_connections=4,
    max_keepalive_connections=2,
    keepalive_expiry=300,
)
_OLLAMA_TIMEOUT = _httpx.Timeout(connect=30.0, read=900.0, write=60.0, pool=30.0)

_MAX_RETRIES = 3
_RETRY_BACKOFF_BASE = 2.0  # seconds: 2, 4, 8


async def _call_ollama_8b(
    http: _httpx.AsyncClient,
    batch_text: str,
    question: str,
    model: str,
    num_ctx: int,
) -> Tuple[str, float]:
    """
    Send a single batch to Ollama via native /api/chat.
    Accepts a shared httpx client to avoid port exhaustion on large runs.
    Retries transient connection errors with exponential backoff.
    """
    endpoint = _ollama_endpoint()
    max_tokens = min(16_384, num_ctx // 2)

    messages = [
        {"role": "system", "content": _INFER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": json.dumps(
                {"question": question, "timeline_data": batch_text},
                ensure_ascii=False,
            ),
        },
    ]

    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_ctx": num_ctx,
            "num_predict": max_tokens,
        },
    }

    last_exc: Optional[Exception] = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            t0 = time.perf_counter()
            resp = await http.post(endpoint, json=body)
            elapsed = time.perf_counter() - t0
            break
        except (_httpx.ConnectError, _httpx.PoolTimeout, OSError) as exc:
            last_exc = exc
            if attempt < _MAX_RETRIES:
                wait = _RETRY_BACKOFF_BASE ** attempt
                logger.warning(
                    "Ollama connect attempt %d/%d failed (%s), retrying in %.1fs",
                    attempt, _MAX_RETRIES, exc, wait,
                )
                await asyncio.sleep(wait)
            else:
                raise RuntimeError(
                    f"Ollama unreachable after {_MAX_RETRIES} attempts: {last_exc}"
                ) from last_exc

    if resp.status_code != 200:
        snippet = resp.content[:500].decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP {resp.status_code}: {snippet}")

    raw = resp.content
    if not raw or not raw.strip():
        raise ValueError("Ollama returned empty body")

    data = json.loads(raw)
    if "error" in data:
        raise RuntimeError(f"Ollama error: {data['error']}")

    msg = data.get("message", {})
    return msg.get("content", ""), elapsed


# ---------------------------------------------------------------------------
# Parse 8B response
# ---------------------------------------------------------------------------

def _parse_extraction_response(raw: str) -> List[Dict[str, Any]]:
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
    if text.endswith("```"):
        text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "events" in parsed:
            return parsed["events"]
        return [parsed]
    except json.JSONDecodeError:
        bracket = text.find("[")
        if bracket >= 0:
            candidate = text[bracket:]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        logger.warning("Could not parse 8B response as JSON; wrapping as note")
        return [{"event_id": "parse_fallback", "text": text[:2000], "event_type": "note"}]


# ---------------------------------------------------------------------------
# Store extracted events in DB
# ---------------------------------------------------------------------------

async def _store_extracted_events(
    db: AsyncSession,
    patient_id: str,
    extracted: List[Dict[str, Any]],
    batch_idx: int,
    model: str,
    artifact_id: Optional[str] = None,
) -> int:
    """
    Persist extracted events to ehr.patient_timeline.

    Uses ON CONFLICT DO NOTHING on the (patient_id, event_type, content_sha)
    partial unique index (migration 007) so re-importing a document
    never duplicates rows. ``content_sha`` is a sha256 of the canonical
    event coordinate so it is stable across runs.
    """
    from sqlalchemy import text as sa_text
    from server.eoh.event_dedup import canonical_event_id
    import hashlib

    stored = 0
    for ev in extracted:
        ts_raw = ev.get("ts")
        if not ts_raw or ts_raw == "unknown":
            continue
        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        event_type = ev.get("event_type", "note")
        text_val = ev.get("text", "")
        structured = ev.get("structured", {})
        ann_for_sha = dict(structured) if isinstance(structured, dict) else {}

        # Compute stable content_sha using the same canonical coordinate as PTV
        canonical_id = canonical_event_id(
            patient_id=patient_id,
            event_type=event_type,
            timestamp=ts_raw,
            text=text_val,
            annotations=ann_for_sha,
        )
        content_sha = hashlib.sha256(canonical_id.encode()).hexdigest()[:64]

        meta_dict: Dict[str, Any] = {
            "confidence": ev.get("confidence"),
            "batch": batch_idx,
            "model": model,
        }
        if artifact_id:
            meta_dict["artifact_id"] = artifact_id

        result = await db.execute(
            sa_text(
                """
                INSERT INTO ehr.patient_timeline
                    (patient_id, ts, event_type, source, structured, text, meta, content_sha)
                VALUES
                    (:patient_id, :ts, :event_type, :source, :structured, :text, :meta, :content_sha)
                ON CONFLICT (patient_id, event_type, content_sha)
                    WHERE content_sha IS NOT NULL
                DO NOTHING
                """
            ),
            {
                "patient_id":  patient_id,
                "ts":          ts,
                "event_type":  event_type,
                "source":      "eoh-llama-8b-infer",
                "structured":  json.dumps(structured, default=str),
                "text":        text_val,
                "meta":        json.dumps(meta_dict, default=str),
                "content_sha": content_sha,
            },
        )
        if getattr(result, "rowcount", None) == 1:
            stored += 1
    await db.commit()
    return stored


# ---------------------------------------------------------------------------
# POST /api/timeline/{patient_id}/infer
# ---------------------------------------------------------------------------

@router.post("/{patient_id}/infer")
async def timeline_infer(
    patient_id: str,
    file: Optional[UploadFile] = File(None),
    format: str = Form("pdf"),
    question: str = Form(
        "Perform a comprehensive diagnostic investigation. "
        "Focus on major clinical arcs, diagnostic mysteries, treatment "
        "divergences, and internal contradictions."
    ),
    password: Optional[str] = Form(None),
    model: str = Form(_DEFAULT_MODEL),
    num_ctx: int = Form(_DEFAULT_NUM_CTX),
    store_results: bool = Form(True),
    build_graph: bool = Form(True),
    db: AsyncSession = Depends(get_session),
):
    """
    Accept a patient timeline and run it through eoh-llama 8B inference.

    Upload modes (set via `format` form field):
      - **pdf**  (default): Upload a PDF file.  Text is extracted server-side.
      - **json**: Upload a structured EHR JSON file (array of event objects).
      - If no file is attached, existing events for the patient are loaded
        from ehr.patient_timeline.

    Returns an SSE stream with per-batch progress.  The first event is
    emitted immediately so the caller knows the request was accepted.
    """

    # ── Reject if another inference is already running ────────────
    if _infer_lock.locked():
        active = _infer_active.copy()
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Inference already in progress",
                "active_job": active,
                "hint": "The GPU can only serve one inference at a time. Wait for the current job to finish or cancel it.",
            },
        )

    # Read file bytes eagerly (fast — just moves bytes from the socket
    # into memory).  All heavy work happens inside the SSE generator.
    raw_bytes: Optional[bytes] = None
    file_name: Optional[str] = None
    if file is not None:
        raw_bytes = await file.read()
        file_name = file.filename or "upload"
        if len(raw_bytes) > _MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds {_MAX_UPLOAD_BYTES // (1024*1024)} MB limit",
            )

    # Everything else runs inside the generator so the client gets SSE
    # events the moment the connection opens.

    async def _generate():
        async with _infer_lock:
            _infer_active.update({
                "patient_id": patient_id,
                "model": model,
                "format": format,
                "file": file_name,
                "started_at": datetime.now().isoformat(),
            })

            try:
                async for event in _run_inference():
                    yield event
            finally:
                _infer_active.clear()

    async def _run_inference():
        page_batches: Optional[List[List[Tuple[int, str]]]] = None
        block_batches: Optional[List[List[str]]] = None
        input_source: str = "database"
        total_batches: int = 0
        _prescan_by_page: Dict[int, Any] = {}
        prescan_vision: Optional[Any] = None
        known_names: Optional[List[str]] = None

        # ── Immediate acknowledgement ──────────────────────────────
        yield _sse("accepted", {
            "patient_id": patient_id,
            "model": model,
            "format": format,
            "file": file_name,
            "file_bytes": len(raw_bytes) if raw_bytes else 0,
            "ts": datetime.now().isoformat(),
        })

        # ── 1. Ingest input ────────────────────────────────────────
        try:
            if raw_bytes is not None and format == "json":
                yield _sse("status", {"phase": "parsing_json", "message": "Parsing structured EHR JSON..."})
                events = _parse_json_ehr(raw_bytes)

                from server.utils.pii_scrub import scrub_pii
                for ev in events:
                    if ev.text:
                        ev.text = scrub_pii(ev.text)

                blocks = _events_to_text_blocks(events)
                block_batches = _chunk_blocks(blocks)
                input_source = "json_ehr"
                yield _sse("status", {"phase": "json_parsed", "events": len(events)})

            elif raw_bytes is not None:
                # ── PDF extraction (the slow part) ──
                file_mb = len(raw_bytes) / (1024 * 1024)
                yield _sse("status", {
                    "phase": "pdf_extracting",
                    "message": f"Extracting text from PDF ({file_mb:.1f} MB)... this may take a while for large records",
                })

                loop = asyncio.get_running_loop()
                try:
                    pages = await loop.run_in_executor(
                        None, _extract_pdf_pages, raw_bytes, password,
                    )
                except ValueError as e:
                    yield _sse("error", {"message": str(e)})
                    return
                except Exception as e:
                    yield _sse("error", {"message": f"PDF extraction failed: {e}"})
                    return

                if not pages:
                    yield _sse("error", {"message": "No text could be extracted from PDF"})
                    return

                total_chars = sum(len(t) for _, t in pages)
                max_page = max(pn for pn, _ in pages)

                yield _sse("pdf_read", {
                    "total_pages": max_page,
                    "pages_with_text": len(pages),
                    "total_chars": total_chars,
                    "avg_chars_per_page": total_chars // max(len(pages), 1),
                })

                # ── PII scrub (before anything else sees the text) ─
                yield _sse("status", {
                    "phase": "pii_scrub",
                    "message": "Scrubbing PII from extracted text...",
                })

                from server.utils.pii_scrub import (
                    scrub_pages,
                    extract_patient_names_from_header,
                )

                known_names = await loop.run_in_executor(
                    None, extract_patient_names_from_header, pages,
                )
                pages = await loop.run_in_executor(
                    None, scrub_pages, pages, known_names,
                )

                chars_after = sum(len(t) for _, t in pages)
                chars_scrubbed = total_chars - chars_after

                yield _sse("pii_scrub_done", {
                    "names_detected": len(known_names),
                    "chars_before": total_chars,
                    "chars_after": chars_after,
                    "chars_scrubbed": chars_scrubbed,
                })

                # ── Heuristic pre-scan (fast, ~0.5ms/page) ────────
                yield _sse("status", {
                    "phase": "pre_scan",
                    "message": f"Running heuristic pre-scan on {len(pages)} pages...",
                })

                from server.eoh.heuristic_page_extract import (
                    heuristic_extract_batch,
                    skeleton_for_llm,
                    HeuristicPageResult,
                )
                from server.eoh.patient_timeline_vision import (
                    PatientTimelineVision,
                    add_events_from_pdf_page,
                    _infer_temporal_connascence,
                )

                prescan_results = await loop.run_in_executor(
                    None, heuristic_extract_batch, pages,
                )

                prescan_events_total = 0
                prescan_dates_total = 0
                prescan_meds = 0
                prescan_labs = 0
                prescan_dx = 0
                for pr in prescan_results.values():
                    prescan_events_total += len(pr.events)
                    prescan_dates_total += len(pr.all_dates)
                    for ev in pr.events:
                        if ev.event_type == "medication":
                            prescan_meds += 1
                        elif ev.event_type == "lab":
                            prescan_labs += 1
                        elif ev.event_type == "diagnosis":
                            prescan_dx += 1

                # Build graph early from pre-scan so temporal edges
                # exist before the LLM ever sees the data.
                prescan_vision: Optional[PatientTimelineVision] = None
                prescan_temporal_edges = 0
                if build_graph:
                    prescan_vision = PatientTimelineVision(
                        patient_id=patient_id,
                        built_at=datetime.now().isoformat(),
                        session_only=True,
                        metadata={
                            "source": "heuristic_pre_scan",
                            "model": model,
                        },
                    )
                    for pn, pr in prescan_results.items():
                        if pr.events:
                            add_events_from_pdf_page(
                                prescan_vision,
                                page_num=pn,
                                events=[e.to_dict() for e in pr.events],
                            )
                    edges_before = prescan_vision.count_edges()
                    _infer_temporal_connascence(prescan_vision, window_days=7)
                    prescan_temporal_edges = prescan_vision.count_edges() - edges_before

                yield _sse("pre_scan_done", {
                    "events": prescan_events_total,
                    "dates": prescan_dates_total,
                    "meds": prescan_meds,
                    "labs": prescan_labs,
                    "dx": prescan_dx,
                    "temporal_edges": prescan_temporal_edges,
                    "graph_events": len(prescan_vision.events) if prescan_vision else 0,
                })

                # Store pre-scan results keyed by page number so we can
                # build per-batch skeletons during inference.
                _prescan_by_page: Dict[int, HeuristicPageResult] = prescan_results

                page_batches = _chunk_pages(pages)
                input_source = "pdf"

            else:
                # ── No file: load from database ──
                yield _sse("status", {
                    "phase": "db_loading",
                    "message": f"Loading existing timeline for {patient_id} from database...",
                })

                from sqlalchemy import text as sa_text

                rows_q = await db.execute(
                    sa_text(
                        """
                        SELECT ts, event_type, source, structured, text, meta
                        FROM ehr.patient_timeline
                        WHERE patient_id = :pid
                        ORDER BY ts ASC
                        """
                    ),
                    {"pid": patient_id},
                )
                rows = rows_q.mappings().all()
                if not rows:
                    yield _sse("error", {"message": "No timeline data for patient"})
                    return

                events = [
                    _TimelineEvent(
                        ts=row["ts"].isoformat() if row["ts"] else None,
                        event_type=row["event_type"] or "note",
                        source=row["source"] or "EHR",
                        text=row["text"] or "",
                        structured=row["structured"],
                        meta=row["meta"],
                    )
                    for row in rows
                ]
                blocks = _events_to_text_blocks(events)
                block_batches = _chunk_blocks(blocks)
                yield _sse("status", {
                    "phase": "db_loaded",
                    "events_loaded": len(rows),
                })

        except Exception as exc:
            yield _sse("error", {"message": f"Ingestion failed: {exc}"})
            return

        # ── Determine batch count ──────────────────────────────────
        if page_batches is not None:
            total_batches = len(page_batches)
        elif block_batches is not None:
            total_batches = len(block_batches)

        if total_batches == 0:
            yield _sse("error", {"message": "No timeline content to process"})
            return

        # ── 2. Build graph container ───────────────────────────────
        all_extracted: List[Dict[str, Any]] = []
        total_elapsed = 0.0
        vision = None

        if build_graph:
            from server.eoh.patient_timeline_vision import PatientTimelineVision

            # If pre-scan already built a vision graph, promote it
            # from session_only to durable so LLM events merge in.
            if input_source == "pdf" and prescan_vision is not None:
                vision = prescan_vision
                vision.session_only = False
                vision.metadata["source"] = f"timeline_infer_{input_source}"
                vision.metadata["model"] = model
            else:
                vision = PatientTimelineVision(
                    patient_id=patient_id,
                    built_at=datetime.now().isoformat(),
                    session_only=False,
                    metadata={
                        "source": f"timeline_infer_{input_source}",
                        "model": model,
                    },
                )

        yield _sse("infer_start", {
            "patient_id": patient_id,
            "total_batches": total_batches,
            "model": model,
            "num_ctx": num_ctx,
            "input_source": input_source,
        })

        # ── 3. Batch inference loop ────────────────────────────────
        # One persistent HTTP client for the entire run — avoids port
        # exhaustion on large PDFs (Norman's 845 batches was burning
        # through ephemeral ports with a new connection per batch).
        async with _httpx.AsyncClient(
            limits=_OLLAMA_POOL_LIMITS,
            timeout=_OLLAMA_TIMEOUT,
        ) as http:
            for batch_idx in range(1, total_batches + 1):
                if page_batches is not None:
                    batch_pages = page_batches[batch_idx - 1]

                    # Build per-page text with pre-scan skeleton injected
                    page_sections = []
                    for pn, txt in batch_pages:
                        section = f"=== Page {pn} ===\n{txt}"
                        if input_source == "pdf" and _prescan_by_page:
                            pr = _prescan_by_page.get(pn)
                            if pr is not None:
                                from server.eoh.heuristic_page_extract import skeleton_for_llm
                                skel = skeleton_for_llm(pn, txt, pr)
                                if skel:
                                    section += f"\n\n--- PRE-SCAN SKELETON (page {pn}) ---\n{skel}"
                        page_sections.append(section)

                    batch_text = "\n\n".join(page_sections)
                    page_range = f"{batch_pages[0][0]}-{batch_pages[-1][0]}"
                    pages_in_batch = len(batch_pages)
                else:
                    assert block_batches is not None
                    batch_blocks = block_batches[batch_idx - 1]
                    batch_text = "\n\n".join(batch_blocks)
                    page_range = None
                    pages_in_batch = None

                batch_chars = len(batch_text)

                yield _sse("batch_start", {
                    "batch": batch_idx,
                    "total": total_batches,
                    "chars": batch_chars,
                    "page_range": page_range,
                    "pages_in_batch": pages_in_batch,
                })

                try:
                    raw_response, elapsed = await _call_ollama_8b(
                        http=http,
                        batch_text=batch_text,
                        question=question,
                        model=model,
                        num_ctx=num_ctx,
                    )
                    total_elapsed += elapsed

                    extracted = _parse_extraction_response(raw_response)

                    from server.utils.pii_scrub import scrub_pii as _scrub
                    for ev in extracted:
                        ev["_batch"] = batch_idx
                        ev["_model"] = model
                        if page_range:
                            ev["_page_range"] = page_range
                        if ev.get("text"):
                            ev["text"] = _scrub(ev["text"], known_names=known_names if input_source == "pdf" else None)
                        if ev.get("preview"):
                            ev["preview"] = _scrub(ev["preview"], known_names=known_names if input_source == "pdf" else None)

                    all_extracted.extend(extracted)

                    stored_count = 0
                    if store_results:
                        stored_count = await _store_extracted_events(
                            db, patient_id, extracted, batch_idx, model,
                        )

                    if vision is not None:
                        from server.eoh.patient_timeline_vision import (
                            add_events_from_pdf_page,
                        )
                        try:
                            add_events_from_pdf_page(
                                vision,
                                page_num=batch_pages[0][0] if page_batches else batch_idx,
                                events=extracted,
                            )
                        except Exception as ge:
                            logger.warning("Graph add failed: %s", ge)

                    yield _sse("batch_done", {
                        "batch": batch_idx,
                        "extracted": len(extracted),
                        "stored": stored_count,
                        "elapsed_ms": int(elapsed * 1000),
                        "page_range": page_range,
                    })

                    if vision is not None:
                        yield _sse("graph_update", {
                            "total_events": len(vision.events),
                            "total_edges": vision.count_edges(),
                        })

                except Exception as e:
                    logger.exception("Batch %d failed: %s", batch_idx, e)
                    yield _sse("batch_error", {
                        "batch": batch_idx,
                        "message": str(e),
                    })

        # ── 4. Finalize graph ──────────────────────────────────────
        if vision is not None:
            try:
                from server.eoh.patient_timeline_vision import (
                    _infer_temporal_connascence,
                    save_timeline_vision,
                )
                _infer_temporal_connascence(vision, window_days=7)
                save_timeline_vision(vision)
            except Exception as e:
                logger.warning("Graph finalization failed: %s", e)

        yield _sse("complete", {
            "patient_id": patient_id,
            "batches_processed": total_batches,
            "events_extracted": len(all_extracted),
            "total_elapsed_ms": int(total_elapsed * 1000),
            "model": model,
            "input_source": input_source,
            "graph_events": len(vision.events) if vision else None,
            "graph_edges": vision.count_edges() if vision else None,
        })

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/infer/status")
async def infer_status():
    """Check whether an inference job is currently running."""
    if _infer_lock.locked():
        return {"busy": True, "active_job": _infer_active.copy()}
    return {"busy": False}


# ---------------------------------------------------------------------------
# FORWARD bearer token auth — separate router (no B2B deps; own auth)
# ---------------------------------------------------------------------------

import os as _os
from fastapi import Header

_FORWARD_TOKEN = _os.getenv("FORWARD_API_TOKEN", "")


def _verify_forward_token(authorization: str = Header(...)) -> None:
    """Validate Bearer token for FORWARD endpoints."""
    if not _FORWARD_TOKEN:
        raise HTTPException(500, "FORWARD_API_TOKEN not configured on server")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Expected: Authorization: Bearer <token>")
    if not _hmac_compare(token, _FORWARD_TOKEN):
        raise HTTPException(403, "Invalid FORWARD API token")


def _hmac_compare(a: str, b: str) -> bool:
    """Constant-time comparison to prevent timing attacks."""
    import hmac
    return hmac.compare_digest(a.encode(), b.encode())


forward_router = APIRouter(
    prefix="/api/timeline",
    tags=["timeline", "forward"],
    dependencies=[Depends(_verify_forward_token)],
)


@forward_router.post("/forward/upload")
async def forward_upload(
    file: UploadFile = File(...),
    format: str = Form("pdf"),
    password: Optional[str] = Form(None),
    model: str = Form(_DEFAULT_MODEL),
    num_ctx: int = Form(_DEFAULT_NUM_CTX),
    store_results: bool = Form(True),
    build_graph: bool = Form(True),
    db: AsyncSession = Depends(get_session),
):
    """
    Convenience endpoint for FORWARD registry uploads.

    Requires: Authorization: Bearer <FORWARD_API_TOKEN>

    Identical to POST /{patient_id}/infer but uses a fixed de-identified
    patient ID (forward_patient_00142) so the caller doesn't need to
    supply one.  Intended for Dr. Michaud's initial integration testing.
    """
    return await timeline_infer(
        patient_id="forward_patient_00142",
        file=file,
        format=format,
        question=(
            "Perform a comprehensive diagnostic investigation of this "
            "rheumatoid arthritis patient. Focus on major clinical arcs, "
            "treatment response patterns, flare triggers, biologic switches, "
            "and disease activity trajectories."
        ),
        password=password,
        model=model,
        num_ctx=num_ctx,
        store_results=store_results,
        build_graph=build_graph,
        db=db,
    )
