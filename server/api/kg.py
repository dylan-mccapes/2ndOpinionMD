import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
import asyncpg
from openai import OpenAI
from dotenv import load_dotenv

# Hybrid retrieval helpers (ANN + BM25 + RRF fuse)
from server.vectordb.hybrid_query import ann_query, bm25_query, fuse

# ----------------------------
# Environment + logging setup
# ----------------------------
logger = logging.getLogger(__name__)

# 1) Load repo root .env first (if present)
REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

# 2) Load server/.env second to allow per-service overrides
SERVER_DIR = Path(__file__).resolve().parent.parent
load_dotenv(SERVER_DIR / ".env")

logger.info("kg.py loaded. OPENAI_API_KEY set: %s",
            "yes" if os.getenv("OPENAI_API_KEY") else "no")

router = APIRouter(prefix="/api/kg", tags=["kg"])

# ----------------------------
# Models
# ----------------------------
class ResolveRAGOptions(BaseModel):
    rag_top_k: Optional[int] = 6
    return_scores: Optional[bool] = True
    use_openai: Optional[bool] = True
    force_rag: Optional[bool] = False
    # Optional filter: restrict to a single RAG source (e.g., 'acr_eular', 'nice')
    source: Optional[str] = None

class ResolveRAGRequest(BaseModel):
    text: str
    labs: Optional[List[Dict[str, Any]]] = None
    options: Optional[ResolveRAGOptions] = None

class ResolveRAGResponse(BaseModel):
    rag_used: bool
    evidence: Dict[str, Any]
    rag_context_preview: Dict[str, Any]
    analysis: Optional[str] = None

# ----------------------------
# Utils
# ----------------------------
def _normalize_db_url(url: Optional[str]) -> str:
    """
    Ensure the URL is acceptable for asyncpg.connect().
    We accept:
      - postgresql+asyncpg://...  -> convert to postgresql://...
      - postgresql://...
      - postgresql:///dbname
    """
    if not url:
        raise HTTPException(500, {"code": "db_not_configured", "message": "DATABASE_URL not configured"})
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url

def _safe_meta(row: Dict[str, Any]) -> Dict[str, Any]:
    # Some query functions name this column "meta", others "metadata"
    if isinstance(row.get("meta"), (dict,)):
        return row["meta"]
    if isinstance(row.get("metadata"), (dict,)):
        return row["metadata"]
    # Try to parse JSON string if needed
    for k in ("meta", "metadata"):
        v = row.get(k)
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                pass
    return {}

def _make_heuristics(text: str, labs: Optional[List[Dict[str, Any]]]) -> str:
    text_lower = (text or "").lower()
    medical_keywords = [
        "pain", "fatigue", "fever", "headache", "nausea", "vomiting", "diarrhea",
        "constipation", "weight", "loss", "gain", "thyroid", "diabetes", "arthritis",
        "joint", "muscle", "skin", "rash", "breathing", "chest", "heart", "blood",
        "ana", "rf", "ccp", "esr", "crp"
    ]
    heur: List[str] = [k for k in medical_keywords if k in text_lower]
    if labs:
        for lab in labs:
            n = (lab.get("name") or "").strip().lower()
            if n:
                heur.append(n)
    # dedupe but keep order a bit stable
    seen = set()
    out = []
    for h in heur:
        if h not in seen:
            out.append(h)
            seen.add(h)
    return " ".join(out) or text

# ----------------------------
# Endpoint
# ----------------------------
@router.post("/resolve_rag", response_model=ResolveRAGResponse)
async def resolve_rag(payload: ResolveRAGRequest = Body(...)):
    """
    RAG + KG hybrid retrieval endpoint with optional source filter and OpenAI analysis.
    """
    try:
        if not payload.text or not payload.text.strip():
            raise HTTPException(400, {"code": "empty_text", "message": "Text is required"})

        options = payload.options or ResolveRAGOptions()

        # ----------------------------
        # Embedding / OpenAI gating
        # ----------------------------
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            if options.use_openai:
                raise HTTPException(500, {"code": "openai_not_configured",
                                          "message": "OPENAI_API_KEY not set in environment. "
                                                     "For uvicorn/systemd, ensure it's exported in the service env."})
            # Proceed without embeddings
            return ResolveRAGResponse(
                rag_used=False,
                evidence={"rag": []},
                rag_context_preview={"gating": {"error": "OpenAI not configured"}},
                analysis="OpenAI API key not configured; embeddings disabled"
            )

        client = OpenAI(api_key=openai_api_key)
        emb_model = os.getenv("EMBED_MODEL", "text-embedding-3-small")

        q_lex = _make_heuristics(payload.text, payload.labs)
        q_vec = f"{payload.text}\n{q_lex}".strip()

        try:
            q_embedding = client.embeddings.create(model=emb_model, input=[q_vec]).data[0].embedding
        except Exception as e:
            if options.force_rag:
                raise HTTPException(500, {"code": "embedding_failed", "message": f"Embedding failed: {e}"})
            return ResolveRAGResponse(
                rag_used=False,
                evidence={"rag": []},
                rag_context_preview={"gating": {"error": f"Embedding failed: {e}"}},
                analysis="Failed to generate embeddings"
            )

        # ----------------------------
        # DB connect + search
        # ----------------------------
        database_url = _normalize_db_url(os.getenv("DATABASE_URL"))
        conn = await asyncpg.connect(dsn=database_url)
        try:
            topk = int(options.rag_top_k or 6)

            dense_items = await ann_query(conn, q_embedding, topk * 3)  # over-fetch for post-filter
            bm25_items  = await bm25_query(conn, q_lex,      topk * 3)
            fused: List[Tuple[int, float, float]] = fuse(dense_items, bm25_items)

            # Build id->row map, allow source filter post-hoc
            id2row: Dict[Any, Dict[str, Any]] = {}
            for r in (dense_items + bm25_items):
                id2row[r["id"]] = r

            rag_items: List[Dict[str, Any]] = []
            for _id, rrf_score, final_score in fused:
                if _id not in id2row:
                    continue
                row = id2row[_id]

                # Optional source filter
                src = row.get("source")
                if options.source and src != options.source:
                    continue

                # Raw component scores
                d_raw = next((r["dense_score"] for r in dense_items if r["id"] == _id), 0.0)
                b_raw = next((r["bm25_score"]  for r in bm25_items  if r["id"] == _id), 0.0)

                rag_items.append({
                    "id": _id,
                    "source": src,
                    "source_id": row.get("source_id"),
                    "title": row.get("title"),
                    "text": row.get("text"),
                    "meta": _safe_meta(row),
                    "scores": {
                        "dense": round(float(d_raw), 4),
                        "bm25":  round(float(b_raw), 4),
                        "rrf":   round(float(rrf_score), 6),
                        "final": round(float(final_score), 4),
                    },
                })
                if len(rag_items) >= topk:
                    break
        finally:
            await conn.close()

        # ----------------------------
        # Optional OpenAI analysis
        # ----------------------------
        analysis = None
        if options.use_openai and rag_items:
            try:
                preview = "\n\n".join([
                    f"Source: {it['source']}  {it['title']}\n{(it['text'] or '')[:600]}..."
                    for it in rag_items[:3]
                ])
                prompt = (
                    "Patient description:\n"
                    f"{payload.text}\n\n"
                    "Relevant context:\n"
                    f"{preview}\n\n"
                    "Provide a concise medical reasoning summary. "
                    "List likely conditions and brief next steps. "
                    "When relevant, mention which source informed a claim."
                )

                # Keep model selectable via env; default to a small, fast model
                chat_model = os.getenv("CHAT_MODEL", "gpt-4o-mini")
                resp = client.chat.completions.create(
                    model=chat_model,
                    messages=[
                        {"role": "system",
                         "content": "You are a careful clinical reasoning assistant. Do not overstate."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=600,
                )
                analysis = resp.choices[0].message.content
            except Exception as e:
                logger.warning("OpenAI analysis failed: %s", e)
                analysis = "Analysis unavailable."

        return ResolveRAGResponse(
            rag_used=len(rag_items) > 0,
            evidence={"rag": rag_items},
            rag_context_preview={
                "gating": {
                    "requested_top_k": options.rag_top_k,
                    "returned": len(rag_items),
                    "source_filter": options.source or "",
                }
            },
            analysis=analysis
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("resolve_rag internal error")
        raise HTTPException(500, {"code": "internal_error", "message": str(e)})

