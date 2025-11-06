from __future__ import annotations

import os, logging, httpx, asyncpg
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel

router = APIRouter(prefix="/api/rag", tags=["rag"])
log = logging.getLogger(__name__)

PG_DSN = os.getenv("SYNC_DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Defaults include orphanet; all lists normalized to lowercase.
_DEF = os.getenv("RAG_DEFAULT_SOURCES", "hpo,icd10cm,icd11,loinc,rxnorm,orphanet,chv")
DEFAULT_SOURCES: List[str] = [s.strip().lower() for s in _DEF.split(",") if s.strip()]
_ALLOWED = os.getenv("RAG_ALLOWED_SOURCES", _DEF)
ALLOWED_SOURCES: Set[str] = {s.strip().lower() for s in _ALLOWED.split(",") if s.strip()}

def _to_vec_literal(vals: List[float] | None) -> Optional[str]:
    if not vals:
        return None
    return "[" + ",".join(f"{v:.6g}" for v in vals) + "]"


# ---------------- Embedding ----------------
async def _embed_query(text: str) -> List[float]:
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

# ---------------- PG fallback (per-source) ----------------
async def _pg_rag_search(q: str, source: str, k: int) -> List[dict]:
    """
    Orphanet (or any single-source) fallback from public.rag_corpus.
    Stage A: hybrid vector+BM25 (vector-first).
    Stage B: BM25 on-the-fly (in case stored ts is missing).
    Stage C: ILIKE title/text.
    """
    emb = await _embed_query(q)
    emb_lit = _to_vec_literal(emb)  # vector literal for asyncpg

    conn = await asyncpg.connect(PG_DSN)
    try:
        # --- Stage A: vector + stored ts (fast path) ---
        sql_a = """
        WITH q AS (
        SELECT plainto_tsquery('english', :q) AS tsq
        ),
        ranked AS (
        SELECT
            r.id, r.source, r.source_id, r.title, r.text, r.meta,
            /* dense: cosine similarity */
            (1 - (r.embedding <=> :qvec))                   AS dense,
            /* bm25: use stored ts or compute on the fly */
            ts_rank(
            COALESCE(r.ts, to_tsvector('english', r.title || ' ' || r.text)),
            q.tsq
            )                                               AS bm25
        FROM public.rag_corpus r, q
        WHERE r.source = 'chv'
        )
        SELECT * FROM ranked
        ORDER BY dense DESC, bm25 DESC
        LIMIT :k
        """
        rows = await conn.fetch(sql_a, q, emb_lit, source, k)
        if rows:
            out = []
            for r in rows:
                out.append({
                    "id": r["id"], "source": r["source"], "source_id": r["source_id"],
                    "title": r["title"], "text": r["text"], "meta": r["meta"],
                    "scores": {
                        "dense": float(r["dense"]) if r["dense"] is not None else None,
                        "bm25": float(r["bm25"]) if r["bm25"] is not None else None,
                    },
                })
            return out

        # --- Stage B: BM25 recompute on the fly (if stored ts is blank) ---
        sql_b = """
        WITH q AS ( SELECT plainto_tsquery('english', $1) AS tsq )
        SELECT id, source, source_id, title, text, meta,
               NULL::float AS dense,
               ts_rank(
                 to_tsvector('english',
                     regexp_replace(COALESCE(title,'')||' '||COALESCE(text,''), '\s+', ' ', 'g')
                 ),
                 q.tsq
               ) AS bm25
        FROM public.rag_corpus rc, q
        WHERE rc.source = $2
          AND to_tsvector('english',
                regexp_replace(COALESCE(title,'')||' '||COALESCE(text,''), '\s+', ' ', 'g')
              ) @@ q.tsq
        ORDER BY bm25 DESC, title NULLS LAST
        LIMIT $3
        """
        rows = await conn.fetch(sql_b, q, source, k)
        if rows:
            return [{
                "id": r["id"], "source": r["source"], "source_id": r["source_id"],
                "title": r["title"], "text": r["text"], "meta": r["meta"],
                "scores": {"dense": None, "bm25": float(r["bm25"]) if r["bm25"] is not None else None},
            } for r in rows]

        # --- Stage C: last-ditch ILIKE ---
        sql_c = """
        SELECT id, source, source_id, title, text, meta,
               NULL::float AS dense, NULL::float AS bm25
        FROM public.rag_corpus
        WHERE source = $1
          AND (title ILIKE $2 OR text ILIKE $2)
        ORDER BY title NULLS LAST
        LIMIT $3
        """
        rows = await conn.fetch(sql_c, source, f"%{q}%", k)
        return [{
            "id": r["id"], "source": r["source"], "source_id": r["source_id"],
            "title": r["title"], "text": r["text"], "meta": r["meta"],
            "scores": {"dense": None, "bm25": None},
        } for r in rows]
    finally:
        await conn.close()

# ---------------- helpers ----------------
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

def _parse_sources_csv(sources_csv: Optional[str]) -> List[str]:
    if not sources_csv:
        return []
    return [s.strip().lower() for s in sources_csv.split(",") if s.strip()]

# ---------------- KG resolver adapter ----------------
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
        source=source_for_kg,  # single source or None (search all)
    )
    req = ResolveRAGRequest(text=q, options=opts)
    return _to_dict(await _kg_resolve(req))

def _filter_sources(items: List[Dict[str, Any]], sources_csv: Optional[str]) -> List[Dict[str, Any]]:
    if not sources_csv:
        return items
    wanted: Set[str] = {s.strip().lower() for s in sources_csv.split(",") if s.strip()}
    return [it for it in items if (it.get("source") or "").lower() in wanted] if wanted else items

# ---------------- main handler ----------------
async def _handle_rag_ask(q: str, k: int, sources_csv: Optional[str], debug: int) -> Dict[str, Any]:
    # compute desired source for KG *first*
    srcs = [s.strip() for s in (sources_csv or "").split(",") if s.strip()]
    source_for_kg = srcs[0] if len(srcs) == 1 else None

    # KG resolve (may or may not cover 'orphanet')
    kgd = await _resolve_rag(q=q, k=k, source_for_kg=source_for_kg)
    rag_items: List[Dict[str, Any]] = _safe_get(kgd, "evidence", "rag", default=[]) or []
    rag_items = _filter_sources(rag_items, sources_csv)

    # If caller pinned a single source and KG returned nothing from it, hit PG directly
    if (not rag_items) and source_for_kg:
        try:
            rag_items = await _pg_rag_search(q, source_for_kg, k)
        except Exception as e:
            log.warning("Fallback pg RAG failed: %s", e)
            rag_items = []

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

# ---------------- request models & routes ----------------
class AskPayload(BaseModel):
    q: str
    k: Optional[int] = 6
    debug: Optional[int] = 0
    sources: Optional[str] = None  # csv e.g. "icd10cm,icd11,orphanet"

@router.get("/ask")
async def ask_get(
    q: str = Query(..., min_length=1),
    k: int = Query(6, ge=1, le=50),
    sources: Optional[str] = Query(None, description=f"csv: e.g. {','.join(DEFAULT_SOURCES)}"),
    debug: int = Query(0),
):
    return await _handle_rag_ask(q=q, k=k, sources_csv=sources, debug=debug)

@router.post("/ask")
async def ask_post(payload: AskPayload = Body(...)):
    return await _handle_rag_ask(
        q=payload.q,
        k=int(payload.k or 6),
        sources_csv=payload.sources,
        debug=int(payload.debug or 0),
    )

# ---------------- convenience endpoints ----------------
@router.get("/sources")
async def rag_sources():
    """List distinct sources present in rag_corpus with coverage."""
    sql = """
    SELECT
      source,
      COUNT(*) AS total,
      COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS embedded,
      COUNT(*) FILTER (WHERE embedding IS NULL)     AS pending
    FROM public.rag_corpus
    GROUP BY source
    ORDER BY source
    """
    conn = await asyncpg.connect(PG_DSN)
    try:
        rows = await conn.fetch(sql)
        return [
            {"source": r["source"], "total": r["total"], "embedded": r["embedded"], "pending": r["pending"]}
            for r in rows
        ]
    finally:
        await conn.close()

@router.get("/smoke")
async def rag_smoke():
    """
    Quick e2e probe:
      - show sources present
      - run an orphanet-only query ('krabbe') if orphanet exists
      - otherwise run default mixed query
    """
    try:
        srcs = await rag_sources()
        have_orphanet = any(s["source"] == "orphanet" and s["total"] > 0 for s in srcs)
        probe_q = "krabbe"
        probe = await _handle_rag_ask(
            q=probe_q, k=5,
            sources_csv=("orphanet" if have_orphanet else ",".join(DEFAULT_SOURCES)),
            debug=0,
        )
        sample = None
        if probe.get("matches"):
            top = probe["matches"][0]
            sample = {"source": top.get("source"), "title": top.get("title"), "source_id": top.get("source_id")}
        return {"sources": srcs, "probe_q": probe_q, "sample": sample}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail={"code": "rag_smoke_failed", "message": str(e)})
