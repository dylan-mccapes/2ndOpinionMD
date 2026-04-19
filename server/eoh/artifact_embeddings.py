"""
artifact_embeddings.py — sentence-transformers embedding store for patient artifacts.

Each patient has ONE embeddings file stored in the database (ehr.patient_artifact_embeddings)
as a JSON BLOB. The design is intentionally simple: no vector DB required; cosine similarity
in Python is fast enough for the expected artifact count (<1000 per patient).

Schema of the stored JSON:
{
  "model": "all-MiniLM-L6-v2",
  "artifacts": {
    "<artifact_id>": {
      "artifact_id": "...",
      "filename": "...",
      "document_type": "...",
      "document_date": "...",
      "snippet": "...",        # first 400 chars of text_content
      "embedding": [...]       # float32 list, len 384
    }
  }
}
"""
from __future__ import annotations

import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Lazy-loaded model
_MODEL = None
_MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model():
    global _MODEL
    if _MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _MODEL = SentenceTransformer(_MODEL_NAME)
            logger.info("sentence-transformers model '%s' loaded", _MODEL_NAME)
        except Exception as exc:
            logger.warning("Could not load sentence-transformers model: %s", exc)
            _MODEL = None
    return _MODEL


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS ehr.patient_artifact_embeddings (
    patient_id  TEXT PRIMARY KEY,
    embeddings  JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
"""


async def ensure_embeddings_table(pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(_DDL)


async def load_embeddings_store(pool, patient_id: str) -> Dict[str, Any]:
    try:
        row = await pool.fetchrow(
            "SELECT embeddings FROM ehr.patient_artifact_embeddings WHERE patient_id = $1",
            patient_id,
        )
        if row:
            raw = row["embeddings"]
            if isinstance(raw, str):
                return json.loads(raw)
            return dict(raw)
    except Exception as exc:
        logger.warning("load_embeddings_store failed: %s", exc)
    return {"model": _MODEL_NAME, "artifacts": {}}


async def save_embeddings_store(pool, patient_id: str, store: Dict[str, Any]) -> None:
    payload = json.dumps(store)
    try:
        await pool.execute(
            """
            INSERT INTO ehr.patient_artifact_embeddings (patient_id, embeddings, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (patient_id) DO UPDATE
              SET embeddings = $2::jsonb,
                  updated_at = NOW()
            """,
            patient_id,
            payload,
        )
    except Exception as exc:
        logger.error("save_embeddings_store failed: %s", exc)


# ---------------------------------------------------------------------------
# Embed helpers
# ---------------------------------------------------------------------------

def _embed_text(text: str) -> Optional[List[float]]:
    model = _get_model()
    if model is None:
        return None
    try:
        vec = model.encode(text, normalize_embeddings=True)
        return vec.tolist()
    except Exception as exc:
        logger.warning("embed_text failed: %s", exc)
        return None


def _cosine(a: List[float], b: List[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    # Vectors are already L2-normalized by sentence-transformers (normalize_embeddings=True)
    return dot


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def embed_and_store_artifact(
    pool,
    patient_id: str,
    artifact_id: str,
    filename: str,
    document_type: str,
    document_date: Optional[str],
    text_content: Optional[str],
) -> None:
    """
    Embed the artifact text (or filename as fallback) and persist into the
    patient's embedding store.  Non-fatal: logs on failure, never raises.
    """
    if not text_content and not filename:
        return
    text_for_embed = (text_content or "")[:4000] or filename
    embedding = await _run_in_thread(_embed_text, text_for_embed)
    if embedding is None:
        logger.debug("embed_and_store_artifact: skipping %s — model unavailable", artifact_id)
        return

    try:
        await ensure_embeddings_table(pool)
        store = await load_embeddings_store(pool, patient_id)
        store.setdefault("model", _MODEL_NAME)
        store.setdefault("artifacts", {})[artifact_id] = {
            "artifact_id": artifact_id,
            "filename": filename,
            "document_type": document_type or "",
            "document_date": document_date or "",
            "snippet": (text_content or "")[:400],
            "embedding": embedding,
        }
        await save_embeddings_store(pool, patient_id, store)
    except Exception as exc:
        logger.warning("embed_and_store_artifact failed for %s: %s", artifact_id, exc)


async def semantic_search(
    pool,
    patient_id: str,
    query: str,
    top_k: int = 16,
) -> List[Dict[str, Any]]:
    """
    Embed `query` and return the top_k artifacts ranked by cosine similarity.
    Returns list of dicts: { artifact_id, filename, document_type, document_date,
                              snippet, score }
    """
    embedding = await _run_in_thread(_embed_text, query)
    if embedding is None:
        return []

    try:
        await ensure_embeddings_table(pool)
        store = await load_embeddings_store(pool, patient_id)
        artifacts = store.get("artifacts", {})
        if not artifacts:
            return []

        scored: List[Tuple[float, Dict[str, Any]]] = []
        for art in artifacts.values():
            art_emb = art.get("embedding")
            if not art_emb:
                continue
            score = _cosine(embedding, art_emb)
            scored.append((score, art))

        scored.sort(key=lambda x: -x[0])
        results = []
        for score, art in scored[:top_k]:
            results.append({
                "artifact_id": art["artifact_id"],
                "filename": art["filename"],
                "document_type": art.get("document_type", ""),
                "document_date": art.get("document_date", ""),
                "snippet": art.get("snippet", ""),
                "score": round(float(score), 4),
            })
        return results

    except Exception as exc:
        logger.warning("semantic_search failed: %s", exc)
        return []


# ---------------------------------------------------------------------------
# Thread executor helper (keep async event loop free during CPU work)
# ---------------------------------------------------------------------------

async def _run_in_thread(fn, *args):
    import asyncio
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, fn, *args)
