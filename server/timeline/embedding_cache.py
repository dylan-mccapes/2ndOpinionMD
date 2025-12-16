# server/timeline/embedding_cache.py (recommended new file)

from __future__ import annotations
import re
from typing import Any, Optional, Sequence, List
import asyncpg

def _norm_query(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

async def get_cached_query_embedding(
    pool: Any,
    *,
    model: str,
    input_text: str,
) -> Optional[list[float]]:
    input_norm = _norm_query(input_text)
    if not input_norm:
        return None
    q = """
      SELECT embedding
      FROM ehr.query_embedding_cache
      WHERE model = $1 AND input_norm = $2
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(q, model, input_norm)
    if not row:
        return None
    emb = row["embedding"]
    # asyncpg returns pgvector as list-like already in many setups; if not, adapt.
    return list(emb)

async def put_cached_query_embedding(
    pool: Any,
    *,
    model: str,
    input_text: str,
    embedding: Sequence[float],
) -> None:
    input_raw = (input_text or "").strip()
    input_norm = _norm_query(input_raw)
    if not input_norm:
        return

    q = """
      INSERT INTO ehr.query_embedding_cache (model, input_norm, input_raw, embedding)
      VALUES ($1, $2, $3, $4)
      ON CONFLICT (model, input_norm) DO UPDATE
      SET input_raw = EXCLUDED.input_raw,
          embedding = EXCLUDED.embedding
    """
    async with pool.acquire() as conn:
        await conn.execute(q, model, input_norm, input_raw, embedding)
