from __future__ import annotations

import asyncio, json, httpx, asyncpg, os
import logging
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

router = APIRouter(prefix="/api/rag", tags=["rag"])
log = logging.getLogger(__name__)


PG_DSN = os.getenv("SYNC_DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

async def _embed_query(text: str) -> list[float]:
    if not OPENAI_API_KEY:
        return []
    async with httpx.AsyncClient(timeout=30.0) as cx:
        r = await cx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"model": EMBED_MODEL, "input": text},
        )
        r.raise_for_status()
        return r.json()["data"][0]["embedding"]

async def _pg_rag_search(q: str, source: str, k: int) -> list[dict]:
    """Fallback to Postgres (BM25 + vector) if KG returns nothing."""
    emb = await _embed_query(q)
    sql = """
    WITH q AS (
      SELECT
        plainto_tsquery('english', $1) AS tsq,
        $2::vector AS qvec
    )
    SELECT id, source, source_id, title, text, meta,
           1.0/(1.0 + (embedding <-> q.qvec)) AS dense,
           ts_rank(ts, q.tsq) AS bm25
    FROM public.rag_corpus, q
    WHERE source = $3
      AND (q.tsq @@ ts OR $2::vector IS NOT NULL)
    ORDER BY (0.7 * (CASE WHEN $2::vector IS NULL THEN 0 ELSE 1.0/(1.0 + (embedding <-> q.qvec)) END)
             + 0.3 * ts_rank(ts, q.tsq)) DESC
    LIMIT $4
    """
    conn = await asyncpg.connect(PG_DSN)
    try:
        rows = await conn.fetch(sql, q, emb if emb else None, source, k)
        out = []
        for r in rows:
            out.append({
                "id": r["id"],
                "source": r["source"],
                "source_id": r["source_id"],
                "title": r["title"],
                "text": r["text"],
                "meta": r["meta"],
                "scores": {"dense": float(r["dense"]), "bm25": float(r["bm25"])},
            })
        return out
    finally:
        await conn.close()

def _to_dict(obj: Any) -> Dict[str, Any]:
    try:
        return obj.model_dump()
    except Exception:
        try:
            return obj.dict()
        except Exception:
            pass
    return obj if isinstance(obj, dict) else {}

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
        src = (it.get("source") or "unknown").lower()
        meta = it.get("meta") or {}
        doc_key = meta.get("doc_key") or it.get("source_id") or it.get("id")
        url = meta.get("url") or meta.get("source_url") or meta.get("doc_url") or it.get("url") or ""
        out.setdefault(src, []).append({
            "rank": i,
            "doc_key": doc_key,
            "title": it.get("title"),
            "url": url,
            "scores": it.get("scores"),
        })
    return out

async def _resolve_rag(q: str, k: int, source_for_kg: Optional[str]) -> Dict[str, Any]:
    try:
        from .kg import ResolveRAGRequest, ResolveRAGOptions, resolve_rag as _kg_resolve
    except Exception as e:
        raise HTTPException(500, detail={"code": "kg_import_failed", "message": str(e)})

    opts = ResolveRAGOptions(
        rag_top_k=int(k or 6),
        return_scores=True,
        use_openai=False,
        force_rag=False,
        source=source_for_kg,  # pydantic expects str|None (not list)
    )
    req = ResolveRAGRequest(text=q, options=opts)
    return _to_dict(await _kg_resolve(req))

def _filter_sources(items: List[Dict[str, Any]], sources_csv: Optional[str]) -> List[Dict[str, Any]]:
    if not sources_csv:
        return items
    wanted: Set[str] = {s.strip().lower() for s in sources_csv.split(",") if s.strip()}
    return [it for it in items if (it.get("source") or "").lower() in wanted] if wanted else items

async def _handle_rag_ask(q: str, k: int, sources_csv: Optional[str], debug: int) -> Dict[str, Any]:
    kgd = await _resolve_rag(q=q, k=k, source_for_kg=source_for_kg)
    rag_items: List[Dict[str, Any]] = _safe_get(kgd, "evidence", "rag", default=[]) or []
    rag_items = _filter_sources(rag_items, sources_csv)

    # For KG, pass a single source (if exactly one), else None (search all)
    srcs = [s.strip() for s in (sources_csv or "").split(",") if s.strip()]
    if not rag_items and len(srcs) == 1:
        try:
            rag_items = await _pg_rag_search(q, srcs[0], k)
        except Exception as e:
            log.warning("Fallback pg RAG failed: %s", e)
    source_for_kg = srcs[0] if len(srcs) == 1 else None
    
    ai_text: Optional[str] = None
    model_used: Optional[str] = None
    if rag_items and os.getenv("OPENAI_API_KEY"):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            preview = "\n\n".join(
                f"[{i+1}] {(it.get('source') or 'unknown')} — {(it.get('title') or 'Untitled')[:160]}\n{(it.get('text') or '')[:700]}..."
                for i, it in enumerate(rag_items[:6])
            )
            prompt = (
                f"Question:\n{q}\n\nEvidence snippets:\n{preview}\n\n"
                "Write a concise, clinically useful answer for a physician. "
                "Prioritize guideline-backed recommendations and practical next steps. "
                "Avoid hallucinations."
            )
            model_used = os.getenv("CHAT_MODEL", "gpt-4o-mini")
            resp = client.chat.completions.create(
                model=model_used,
                messages=[
                    {"role": "system", "content": "You are a careful clinical assistant."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=700,
            )
            ai_text = resp.choices[0].message.content
        except Exception as e:
            log.warning("AI synthesis failed: %s", e)

    return {
        "ai_response": {
            "text": ai_text,
            "model": model_used,
            "supporting_documents_by_source": _mk_supporting_by_source(rag_items),
        },
        "matches": rag_items,
        **({"debug": {"items_returned": len(rag_items), "kg_preview": kgd.get("rag_context_preview")}} if debug else {}),
    }

class AskPayload(BaseModel):
    q: str
    k: Optional[int] = 6
    debug: Optional[int] = 0
    sources: Optional[str] = None  # csv e.g. "icd10cm,icd11"

@router.get("/ask")
async def ask_get(
    q: str = Query(..., min_length=1),
    k: int = Query(6, ge=1, le=50),
    sources: Optional[str] = Query(None, description="csv: e.g. icd10cm,icd11"),
    debug: int = Query(0),
):
    return await _handle_rag_ask(q=q, k=k, sources_csv=sources, debug=debug)

@router.post("/ask")
async def ask_post(payload: AskPayload = Body(...)):
    return await _handle_rag_ask(q=payload.q, k=int(payload.k or 6), sources_csv=payload.sources, debug=int(payload.debug or 0))
