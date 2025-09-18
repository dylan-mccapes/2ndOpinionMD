import os
import json
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel
import asyncpg
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

from server.vectordb.hybrid_query import ann_query, bm25_query, fuse

load_dotenv()
logger = logging.getLogger(__name__)
logger.info("OPENAI_API_KEY prefix: %r", (os.getenv("OPENAI_API_KEY") or "")[:10])

server_dir = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=server_dir / ".env")

router = APIRouter()

class ResolveRAGOptions(BaseModel):
    rag_top_k: Optional[int] = 6
    return_scores: Optional[bool] = True
    use_openai: Optional[bool] = True
    force_rag: Optional[bool] = False

class ResolveRAGRequest(BaseModel):
    text: str
    labs: Optional[List[Dict[str, Any]]] = None
    options: Optional[ResolveRAGOptions] = None

class ResolveRAGResponse(BaseModel):
    rag_used: bool
    evidence: Dict[str, Any]
    rag_context_preview: Dict[str, Any]
    analysis: Optional[str] = None

@router.post("/api/kg/resolve_rag", response_model=ResolveRAGResponse)
async def resolve_rag(payload: ResolveRAGRequest = Body(...)):
    """
    RAG + KG hybrid retrieval endpoint with scoring
    """
    try:
        logger.info("RAG resolve request: text_len=%d labs=%d", 
                   len(payload.text) if payload.text else 0,
                   len(payload.labs) if payload.labs else 0)

        if not payload.text or not payload.text.strip():
            raise HTTPException(400, {"code": "empty_text", "message": "Text is required"})

        options = payload.options or ResolveRAGOptions()
        
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key or openai_api_key.startswith("sk-placeholder"):
            if options.use_openai:
                raise HTTPException(500, {"code": "openai_not_configured", "message": "OpenAI API key not configured"})
            else:
                logger.warning("OpenAI not configured, proceeding without embeddings")
                return ResolveRAGResponse(
                    rag_used=False,
                    evidence={"rag": []},
                    rag_context_preview={"gating": {"error": "OpenAI not configured"}},
                    analysis="OpenAI API key not configured for analysis"
                )

        client = OpenAI(api_key=openai_api_key)
        emb_model = os.getenv("EMBED_MODEL", "text-embedding-3-small")
        
        heuristic_terms = []
        text_lower = payload.text.lower()
        
        medical_keywords = [
            "pain", "fatigue", "fever", "headache", "nausea", "vomiting", "diarrhea",
            "constipation", "weight", "loss", "gain", "thyroid", "diabetes", "arthritis",
            "joint", "muscle", "skin", "rash", "breathing", "chest", "heart", "blood"
        ]
        
        for keyword in medical_keywords:
            if keyword in text_lower:
                heuristic_terms.append(keyword)
        
        if payload.labs:
            for lab in payload.labs:
                if lab.get("name"):
                    heuristic_terms.append(lab["name"].lower())
        
        q_lex = " ".join(sorted(set(heuristic_terms))) or payload.text
        q_vec = payload.text + " " + q_lex
        
        try:
            q_embedding = client.embeddings.create(model=emb_model, input=[q_vec]).data[0].embedding
        except Exception as e:
            logger.error("Failed to get embedding: %s", e)
            if options.force_rag:
                raise HTTPException(500, {"code": "embedding_failed", "message": f"Failed to get embedding: {e}"})
            return ResolveRAGResponse(
                rag_used=False,
                evidence={"rag": []},
                rag_context_preview={"gating": {"error": f"Embedding failed: {e}"}},
                analysis="Failed to generate embeddings for analysis"
            )
        
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(500, {"code": "db_not_configured", "message": "DATABASE_URL not configured"})
        
        asyncpg_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
        conn = await asyncpg.connect(dsn=asyncpg_url)
        try:
            topk = options.rag_top_k or 6
            
            dense_items = await ann_query(conn, q_embedding, topk)
            bm25_items = await bm25_query(conn, q_lex, topk)
            fused = fuse(dense_items, bm25_items)
            
            id2row = {r["id"]: r for r in (dense_items + bm25_items)}
            rag_items = []
            
            for _id, rrf_score, final in fused[:topk]:
                if _id not in id2row:
                    continue
                    
                row = id2row[_id]
                d_raw = next((r["dense_score"] for r in dense_items if r["id"] == _id), 0.0)
                b_raw = next((r["bm25_score"] for r in bm25_items if r["id"] == _id), 0.0)
                
                rag_items.append({
                    "id": _id,
                    "source": row["source"],
                    "source_id": row["source_id"],
                    "title": row["title"],
                    "text": row["text"],
                    "metadata": row["metadata"],
                    "scores": {
                        "dense": round(float(d_raw), 4),
                        "bm25": round(float(b_raw), 4),
                        "rrf": round(float(rrf_score), 6),
                        "final": round(float(final), 4)
                    }
                })
        finally:
            await conn.close()
        
        analysis = None
        if options.use_openai and rag_items:
            try:
                context_text = "\n\n".join([
                    f"Source: {item['source']} - {item['title']}\n{item['text'][:500]}..."
                    for item in rag_items[:3]
                ])
                
                prompt = f"""
                Based on the patient's description: "{payload.text}"
                
                And the following medical knowledge:
                {context_text}
                
                Provide a brief medical analysis focusing on potential conditions and recommendations.
                Be concise and reference the sources when relevant.
                """
                
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a medical AI assistant providing analysis based on retrieved medical knowledge."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                analysis = response.choices[0].message.content
            except Exception as e:
                logger.warning("Failed to generate OpenAI analysis: %s", e)
                analysis = "Analysis generation failed"
        
        return ResolveRAGResponse(
            rag_used=len(rag_items) > 0,
            evidence={"rag": rag_items},
            rag_context_preview={
                "gating": {
                    "requested_top_k": topk,
                    "fused_candidates": len(fused),
                    "returned": len(rag_items),
                    "dense_results": len(dense_items),
                    "bm25_results": len(bm25_items)
                }
            },
            analysis=analysis
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in resolve_rag: %s", str(e))
        raise HTTPException(500, {"code": "internal_error", "message": f"Internal error: {str(e)}"})
