from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

# Exported router (app_postgres imports this symbol)
router = APIRouter(prefix="/api/rag", tags=["rag"])

log = logging.getLogger(__name__)

# --------------------------
# Helpers
# --------------------------
def _to_dict(obj: Any) -> Dict[str, Any]:
    try:
        return obj.model_dump()
    except Exception:
        try:
            return obj.dict()
        except Exception:
            pass
    if isinstance(obj, dict):
        return obj
    return {}

def _safe_get(d: Dict[str, Any], *path, default=None):
    cur: Any = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default

def _mk_supporting_by_source(items: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    for i, it in enumerate(items, 1):
        src = it.get("source") or "unknown"
        meta = it.get("meta") or {}
        doc_key = meta.get("doc_key") or it.get("source_id") or it.get("id")
        url = (
            meta.get("url")
            or meta.get("source_url")
            or meta.get("doc_url")
            or it.get("url")
            or ""
        )
        entry = {
            "rank": i,
            "doc_key": doc_key,
            "title": it.get("title"),
            "url": url,
            "scores": it.get("scores"),
        }
        out.setdefault(src, []).append(entry)
    return out

async def _handle_rag_ask(q: str, k: int, debug: int) -> Dict[str, Any]:
    # Lazy import KG pieces here to avoid any chance of circular imports
    try:
        from .kg import ResolveRAGRequest, ResolveRAGOptions, resolve_rag as _kg_resolve
    except Exception as e:
        raise HTTPException(500, detail={"code": "kg_import_failed", "message": str(e)})

    # Build KG request (search across all sources the vector DB has)
    opts = ResolveRAGOptions(
        rag_top_k=int(k or 6),
        return_scores=True,
        use_openai=False,   # we will do the model synthesis below
        force_rag=False,
        source=None,        # do NOT filter; allow multi-database results
    )
    req = ResolveRAGRequest(text=q, options=opts)

    kg_res = await _kg_resolve(req)
    kgd = _to_dict(kg_res)
    rag_items: List[Dict[str, Any]] = _safe_get(kgd, "evidence", "rag", default=[]) or []

    # Compose AI "organic" response using OpenAI if available and we have evidence
    ai_text: Optional[str] = None
    model_used: Optional[str] = None
    if rag_items:
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                from openai import OpenAI  # v1 client, already used elsewhere
                client = OpenAI(api_key=api_key)
                preview = "\n\n".join(
                    [
                        f"[{i+1}] {(it.get('source') or 'unknown')} — {(it.get('title') or 'Untitled')[:160]}"
                        f"\n{(it.get('text') or '')[:700]}..."
                        for i, it in enumerate(rag_items[:6])
                    ]
                )
                prompt = (
                    "Question:\n"
                    f"{q}\n\n"
                    "Evidence snippets from multiple databases (e.g., NICE, ACR/EULAR, internal DBs):\n"
                    f"{preview}\n\n"
                    "Write a concise, clinically useful answer for a physician.\n"
                    "Prioritize guideline-backed recommendations and practical next steps.\n"
                    "Where applicable, reconcile differences and note key caveats.\n"
                    "Avoid hedging and avoid hallucinations."
                )
                model_used = os.getenv("CHAT_MODEL", "gpt-4o-mini")
                resp = client.chat.completions.create(
                    model=model_used,
                    messages=[
                        {"role": "system", "content": "You are a careful clinical assistant. Be specific, safe, and concise."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=700,
                )
                ai_text = resp.choices[0].message.content
            except Exception as e:
                log.warning("AI synthesis failed: %s", e)
                ai_text = f"AI response unavailable: {e}"
        else:
            ai_text = None  # key not set; leave null

    by_source = _mk_supporting_by_source(rag_items)

    out: Dict[str, Any] = {
        "ai_response": {
            "text": ai_text,
            "model": model_used,
            "supporting_documents_by_source": by_source,
        },
        "matches": rag_items,
    }
    if debug:
        out["debug"] = {
            "kg_preview": kgd.get("rag_context_preview"),
            "items_returned": len(rag_items),
        }
    return out

# --------------------------
# Schemas for POST
# --------------------------
class AskPayload(BaseModel):
    q: str
    k: Optional[int] = 6
    alpha: Optional[float] = 0.5  # kept for backward compatibility; not used in new flow
    debug: Optional[int] = 0

# --------------------------
# Routes
# --------------------------
@router.get("/ask")
async def ask_get(
    q: str = Query(..., min_length=1),
    k: int = Query(6, ge=1, le=50),
    alpha: float = Query(0.5),  # compatibility only
    debug: int = Query(0),
):
    return await _handle_rag_ask(q=q, k=k, debug=debug)

@router.post("/ask")
async def ask_post(payload: AskPayload = Body(...)):
    return await _handle_rag_ask(q=payload.q, k=int(payload.k or 6), debug=int(payload.debug or 0))
