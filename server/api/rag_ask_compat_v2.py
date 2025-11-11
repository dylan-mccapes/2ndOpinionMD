# server/api/rag_ask_compat_v2.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Query, Request
from fastapi.responses import Response
import json
from .rag_routes import _handle_rag_ask
from .citation_governance import now_iso

router = APIRouter(prefix="/api/rag", tags=["ask-compat-v2"])

def _pretty(d: Dict[str,Any], indent: Optional[int]) -> str:
    return json.dumps(d, indent=indent)

# --- Ethos of Health (Modules 1 & 2) lightweight scaffold ---

def _eoh_module1_baseline(patient_history: List[str]) -> Dict[str,Any]:
    score = 100
    for tag in patient_history:
        t = tag.lower()
        if "diabetes" in t or "dm2" in t: score -= 20
        if "hypertension" in t or "htn" in t: score -= 15
        if "mi" in t or "infarct" in t: score -= 30
    zone = "Healthy Baseline" if score >= 90 else "Partially Compromised" if score >= 60 else "Baseline Lost"
    stack_level = 0 if score >= 90 else (0 if score >= 60 else 1)
    return {"baseline_integrity_score": max(0,score), "zone": zone, "stack_level": stack_level}

def _eoh_module2_deviation(current: List[str], baseline: List[str]) -> Dict[str,Any]:
    dev = 0
    for t in current:
        if any(k in t.lower() for k in ["pain 7/10","fever","elevated","worse","acute","st depression","st-depression","st depressions"]):
            dev += 10
    zone = "Chronic Baseline Stable" if dev == 0 else ("Borderline Shift" if dev <= 10 else "Out-of-Baseline")
    stack_level = 1 if dev == 0 else 2
    return {"deviation_score": dev, "zone": zone, "stack_level": stack_level}

@router.post("/ask2")
async def ask2(request: Request, payload: Dict[str,Any] = Body(...),
               format: str = Query("json", pattern="^(json)$"),
               pretty: int = Query(0)):
    note = (payload.get("note") or payload.get("q") or payload.get("question") or "").strip()
    sources = payload.get("sources")
    limit = int(payload.get("limit") or 30)
    eoh_enabled = bool(payload.get("eoh_enabled") or True)

    rag = await _handle_rag_ask(q=note, k=limit, sources_csv=sources, debug=0)
    matches = rag.get("matches") or []

    eoh = None
    if eoh_enabled:
        # allow caller to pass explicit tags; otherwise infer a few basics from the note
        hist = payload.get("eoh",{}).get("history_tags") or (["dm2","htn"] if (("DM2" in note) or ("HTN" in note)) else [])
        current = payload.get("eoh",{}).get("current_tags") or []
        if ("NSTEMI" in note.upper()) or ("ACS" in note.upper()) or ("ST DEPRESSION" in note.upper()):
            current += ["st depression","troponin elevated"]
        m1 = _eoh_module1_baseline(hist)
        m2 = _eoh_module2_deviation(current, hist)
        eoh = {"module1": m1, "module2": m2, "provenance": {"time": now_iso()}}

    out = {"note": note, "matches": matches, "eoh": eoh}
    return Response(content=_pretty(out, 2 if pretty else None), media_type="application/json")

# Safe alias for legacy clients; include this router BEFORE any strict /ask route to avoid 422
@router.post("/ask")
async def ask_alias(request: Request, payload: Dict[str,Any] = Body(...),
                    format: str = Query("json", pattern="^(json)$"),
                    pretty: int = Query(0)):
    return await ask2(request, payload, format, pretty)

