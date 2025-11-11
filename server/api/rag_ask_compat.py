# server/api/rag_ask_compat.py
from __future__ import annotations
import json, os
from typing import Any, Dict
from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import Response
from .rag_routes import _handle_rag_ask
from .citation_utils import split_matches_by_role

router = APIRouter(prefix="/api/rag", tags=["ask"])

@router.post("/ask")
async def ask(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    format: str = Query("json", regex="^(json)$"),
    pretty: int = Query(0),
):
    """
    Tolerant /api/rag/ask that accepts either {q: "..."} or {note: "..."}.
    Optional: sources, limit, eoh_enabled.
    Returns ai_response stub + matches grouped by source role (authoritative/guideline/lexical).
    """
    q = (payload.get("q") or payload.get("note") or "").strip()
    if not q:
        # be tolerant: empty response structure instead of 422
        body = {
            "ai_response": {"text": None, "model": None, "supporting_documents_by_source": {}},
            "matches": [],
            "eoh": {"status": "disabled_or_missing_input"},
        }
        txt = json.dumps(body, indent=(2 if pretty else None))
        return Response(content=txt, media_type="application/json")

    sources = payload.get("sources")
    limit   = int(payload.get("limit") or 40)
    eoh_on  = bool(payload.get("eoh_enabled", False))

    rag = await _handle_rag_ask(q=q, k=limit, sources_csv=sources, debug=0)
    matches = rag.get("matches") or []
    grouped = split_matches_by_role(matches)

    # If _handle_rag_ask provided text/model, pass through; else stub
    ai_text  = rag.get("ai_response", {}).get("text") or rag.get("text") or None
    ai_model = rag.get("ai_response", {}).get("model") or rag.get("ai_model") or os.getenv("CHAT_MODEL")

    body: Dict[str, Any] = {
        "ai_response": {
            "text": ai_text,
            "model": ai_model,
            "supporting_documents_by_source": grouped,
        },
        "matches": matches,
    }

    if eoh_on:
        # Minimal EoH scaffold so clients can render without special-casing
        body["eoh"] = {
            "module1_original_baseline": {"score": None, "zone": None, "stack_level": None, "status": "not_evaluated_here"},
            "module2_chronic_baseline_mode": {"deviation_score": None, "zone": None, "stack_level": None, "status": "not_evaluated_here"},
        }

    txt = json.dumps(body, indent=(2 if pretty else None))
    return Response(content=txt, media_type="application/json")
