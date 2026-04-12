# server/api/graph_query_routes.py
"""
GET  /api/graph/{patient_id}/snapshot    — Graph shape overview
GET  /api/graph/{patient_id}/topology    — Structural analysis (components, hubs, gaps)
GET  /api/graph/{patient_id}/events      — Search/filter events
GET  /api/graph/{patient_id}/event/{eid} — Single event + neighbours
GET  /api/graph/{patient_id}/traverse    — Priority traversal from a seed event
GET  /api/graph/{patient_id}/gaps        — Temporal gaps (periods of silence)
GET  /api/graph/{patient_id}/negative    — Negative space (expected-but-absent patterns)
GET  /api/graph/{patient_id}/arcs        — Clinical arcs
GET  /api/graph/{patient_id}/edges       — Denormalised edge list
POST /api/graph/{patient_id}/ask         — Free-text question → 8B answers from graph context
"""

from __future__ import annotations

import hmac
import json
import logging
import os
import time
import textwrap
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field

from server.eoh.patient_timeline_vision import (
    PatientTimelineVision,
    load_timeline_vision,
    get_default_vision_path,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["graph", "query"])

_FORWARD_TOKEN = os.getenv("FORWARD_API_TOKEN", "")


# ---------------------------------------------------------------------------
# Auth: FORWARD patient IDs require bearer token
# ---------------------------------------------------------------------------

def _check_forward_auth(patient_id: str, authorization: Optional[str]) -> None:
    """If patient_id starts with 'forward_', require a valid bearer token."""
    if not patient_id.startswith("forward_"):
        return
    if not _FORWARD_TOKEN:
        raise HTTPException(500, "FORWARD_API_TOKEN not configured on server")
    if not authorization:
        raise HTTPException(
            401,
            "FORWARD patient graphs require authentication. "
            "Pass: -H 'Authorization: Bearer <token>'",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Expected: Authorization: Bearer <token>")
    if not hmac.compare_digest(token.encode(), _FORWARD_TOKEN.encode()):
        raise HTTPException(403, "Invalid FORWARD API token")


# ---------------------------------------------------------------------------
# Graph loader (file-based for now; PG upgrade is one-line swap)
# ---------------------------------------------------------------------------

def _load_graph(patient_id: str, authorization: Optional[str] = None) -> PatientTimelineVision:
    _check_forward_auth(patient_id, authorization)
    vision = load_timeline_vision(patient_id)
    if not vision.events:
        raise HTTPException(
            status_code=404,
            detail=f"No graph found for patient '{patient_id}'. "
                   f"Run /api/timeline/{patient_id}/infer first.",
        )
    return vision


# ---------------------------------------------------------------------------
# GET /full — complete graph export
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/full")
async def graph_full(patient_id: str, authorization: Optional[str] = Header(None)):
    """Return the complete graph as JSON (all events, edges, arcs, metadata).

    This is the full PatientTimelineVision serialised.  Use /snapshot for
    a lightweight overview; use this when you need the entire dataset for
    downstream analysis, visualisation, or import into another system.
    """
    return _load_graph(patient_id, authorization).to_dict()


# ---------------------------------------------------------------------------
# GET /snapshot — lightweight graph shape
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/snapshot")
async def graph_snapshot(patient_id: str, authorization: Optional[str] = Header(None)):
    """The 'git ls-files' of the patient graph.

    Returns event counts by type, date ranges, and a compact node list.
    This is the first thing to call after an infer run completes.
    """
    return _load_graph(patient_id, authorization).snapshot()


# ---------------------------------------------------------------------------
# GET /topology — structural MRI
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/topology")
async def graph_topology(patient_id: str, authorization: Optional[str] = Header(None)):
    """Structural analysis: connected components, orphan events, hubs,
    temporal gaps (>90 days), edge type distribution, and graph density.
    """
    return _load_graph(patient_id, authorization).topology_scan()


# ---------------------------------------------------------------------------
# GET /events — search & filter
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/events")
async def graph_events(
    patient_id: str,
    event_type: Optional[str] = Query(None, description="Filter by type (lab, medication, diagnosis, etc.)"),
    q: Optional[str] = Query(None, description="Search event previews (case-insensitive substring)"),
    date_from: Optional[str] = Query(None, description="ISO date lower bound (inclusive)"),
    date_to: Optional[str] = Query(None, description="ISO date upper bound (inclusive)"),
    limit: int = Query(200, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    authorization: Optional[str] = Header(None),
):
    """Search and filter events in the patient graph."""
    from server.utils.parse_date import parse_clinical_date

    vision = _load_graph(patient_id, authorization)
    results: List[Dict[str, Any]] = []

    dt_from = parse_clinical_date(date_from) if date_from else None
    dt_to = parse_clinical_date(date_to) if date_to else None
    q_lower = q.lower() if q else None

    for ev in vision.events.values():
        if event_type and ev.event_type != event_type:
            continue
        if q_lower and q_lower not in ev.preview.lower():
            continue
        if dt_from or dt_to:
            ev_dt = parse_clinical_date(ev.timestamp) if ev.timestamp else None
            if ev_dt is None:
                continue
            if dt_from and ev_dt < dt_from:
                continue
            if dt_to and ev_dt > dt_to:
                continue
        results.append(ev.to_dict())

    results.sort(key=lambda e: e.get("timestamp") or "~")
    total = len(results)
    page = results[offset : offset + limit]

    return {
        "patient_id": patient_id,
        "total": total,
        "offset": offset,
        "limit": limit,
        "events": page,
    }


# ---------------------------------------------------------------------------
# GET /event/{eid} — single event + neighbours
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/event/{event_id}")
async def graph_event_detail(patient_id: str, event_id: str, authorization: Optional[str] = Header(None)):
    """Return a single event with all its connascence neighbours."""
    vision = _load_graph(patient_id, authorization)
    ev = vision.events.get(event_id)
    if ev is None:
        raise HTTPException(404, f"Event '{event_id}' not found in graph")

    neighbours: Dict[str, List[Dict[str, Any]]] = {}
    for kind, targets in ev.connascence.items():
        neighbours[kind] = []
        for tid in targets:
            tev = vision.events.get(tid)
            if tev:
                neighbours[kind].append(tev.to_dict())

    return {
        "event": ev.to_dict(),
        "neighbours": neighbours,
        "degree": sum(len(t) for t in ev.connascence.values()),
    }


# ---------------------------------------------------------------------------
# GET /traverse — priority traversal from a seed
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/traverse")
async def graph_traverse(
    patient_id: str,
    seed: str = Query(..., description="Event ID to start from"),
    max_nodes: int = Query(30, ge=1, le=200),
    authorization: Optional[str] = Header(None),
):
    """Priority-weighted graph traversal from a seed event.

    Follows highest-value edges first (caused_by > causal > diagnostic >
    treatment > drug_response > lab_trend > symptom_cluster > temporal).
    """
    vision = _load_graph(patient_id, authorization)
    if seed not in vision.events:
        raise HTTPException(404, f"Seed event '{seed}' not found")

    path_ids = vision.priority_traverse(seed, max_nodes=max_nodes)
    path = []
    for eid in path_ids:
        ev = vision.events.get(eid)
        if ev:
            path.append(ev.to_dict())

    return {
        "seed": seed,
        "traversal_length": len(path),
        "events": path,
    }


# ---------------------------------------------------------------------------
# GET /gaps — temporal gaps
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/gaps")
async def graph_gaps(
    patient_id: str,
    min_gap_days: int = Query(90, ge=1, description="Minimum silence in days"),
    authorization: Optional[str] = Header(None),
):
    """Detect periods of silence in the timeline.

    Gaps often indicate lost-to-follow-up periods, care system transitions,
    or extraction misses.
    """
    vision = _load_graph(patient_id, authorization)
    gaps = vision.detect_temporal_gaps(min_gap_days=min_gap_days)
    return {
        "patient_id": patient_id,
        "min_gap_days": min_gap_days,
        "gaps_found": len(gaps),
        "gaps": gaps,
    }


# ---------------------------------------------------------------------------
# GET /negative — negative space (expected-but-absent patterns)
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/negative")
async def graph_negative_space(patient_id: str, authorization: Optional[str] = Header(None)):
    """Identify expected-but-absent patterns.

    Finds diagnoses without follow-up labs, medications without efficacy
    assessments, and other gaps where diagnostic mysteries often hide.
    """
    vision = _load_graph(patient_id, authorization)
    findings = vision.detect_negative_space()
    return {
        "patient_id": patient_id,
        "findings_count": len(findings),
        "findings": findings,
    }


# ---------------------------------------------------------------------------
# GET /arcs — clinical arcs
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/arcs")
async def graph_arcs(patient_id: str, authorization: Optional[str] = Header(None)):
    """Return all clinical arcs (macro-level threads in the timeline).

    Arcs partition events into clinically coherent threads: organ-system
    stories, treatment arcs, diagnostic threads, etc.
    """
    vision = _load_graph(patient_id, authorization)
    arcs = [a.to_dict() for a in vision.arcs.values()]
    cross_edges = vision.walk_cross_arc_edges()
    return {
        "patient_id": patient_id,
        "arcs_count": len(arcs),
        "arcs": arcs,
        "cross_arc_edges": cross_edges,
    }


# ---------------------------------------------------------------------------
# GET /edges — denormalised edge list
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/edges")
async def graph_edges(
    patient_id: str,
    kind: Optional[str] = Query(None, description="Filter by edge type (temporal, causal, diagnostic, etc.)"),
    limit: int = Query(500, ge=1, le=5000),
    authorization: Optional[str] = Header(None),
):
    """Return denormalised, deduplicated edge list.

    Useful for building adjacency matrices, visualisations, or feeding
    to downstream graph algorithms.
    """
    vision = _load_graph(patient_id, authorization)
    edges = vision.iter_connascence_edges(limit=limit)
    if kind:
        edges = [e for e in edges if e["connascence_type"] == kind]
    return {
        "patient_id": patient_id,
        "total_edges": len(edges),
        "filter_kind": kind,
        "edges": edges,
    }


# ---------------------------------------------------------------------------
# POST /ask — free-text question answered by 8B from graph context
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    model: str = "eoh-llama3.1:8b"
    num_ctx: int = 32_768
    max_context_events: int = Field(60, ge=10, le=200)


@router.post("/{patient_id}/ask")
async def graph_ask(patient_id: str, body: AskRequest, authorization: Optional[str] = Header(None)):
    """Ask a free-text question about this patient's graph.

    Loads the graph, builds a compact context from the most relevant events
    (by type distribution and recency), sends it to 8B with the question,
    and returns the answer.
    """
    import httpx

    vision = _load_graph(patient_id, authorization)

    events_sorted = sorted(
        vision.events.values(),
        key=lambda e: e.timestamp if e.timestamp else "~",
    )
    context_events = events_sorted[: body.max_context_events]

    context_lines = []
    for ev in context_events:
        line = f"[{ev.timestamp or 'unknown'}] {ev.event_type}: {ev.preview}"
        edge_count = sum(len(t) for t in ev.connascence.values())
        if edge_count:
            line += f" ({edge_count} edges)"
        context_lines.append(line)

    snap = vision.snapshot()
    header = (
        f"Patient {patient_id} — {snap['total_events']} events, "
        f"{snap['total_edges']} edges\n"
        f"Types: {json.dumps(snap['types'], default=str)}\n"
    )

    system_prompt = textwrap.dedent("""\
        You are a clinical investigation assistant. You have access to a
        patient's structured knowledge graph. Answer the question using
        ONLY the graph data provided. Be specific — cite event IDs, dates,
        and values. If the graph doesn't contain enough information to
        answer, say so and suggest which event types or date ranges to
        investigate.
    """)

    user_content = (
        f"{header}\n"
        f"--- GRAPH EVENTS ({len(context_lines)} of {snap['total_events']}) ---\n"
        + "\n".join(context_lines)
        + f"\n\n--- QUESTION ---\n{body.question}"
    )

    from server.api.stream_config import OLLAMA_BASE_URL
    host = OLLAMA_BASE_URL.rstrip("/")
    for suffix in ("/v1/chat/completions", "/v1"):
        if host.endswith(suffix):
            host = host[: -len(suffix)]
            break
    endpoint = f"{host}/api/chat"

    ollama_body = {
        "model": body.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
        "options": {
            "temperature": 0.2,
            "num_ctx": body.num_ctx,
            "num_predict": 4096,
        },
    }

    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=30, read=300, write=30, pool=30)) as client:
        resp = await client.post(endpoint, json=ollama_body)

    elapsed = time.perf_counter() - t0

    if resp.status_code != 200:
        raise HTTPException(502, f"Ollama returned HTTP {resp.status_code}")

    data = resp.json()
    answer = data.get("message", {}).get("content", "")

    return {
        "patient_id": patient_id,
        "question": body.question,
        "answer": answer,
        "model": body.model,
        "context_events_used": len(context_lines),
        "graph_total_events": snap["total_events"],
        "graph_total_edges": snap["total_edges"],
        "elapsed_ms": int(elapsed * 1000),
    }
