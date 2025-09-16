import asyncpg
from typing import List, Dict, Any

def rrf_score(ranks: List[int], k: float = 60.0) -> float:
    return float(sum(1.0 / (k + r) for r in ranks))

async def ann_query(conn, emb: list, top_k: int):
    emb_str = '[' + ','.join(map(str, emb)) + ']'
    rows = await conn.fetch("""
      SELECT id, source, source_id, title, text, metadata,
             1 - (embedding <#> $1::vector) AS dense_score
      FROM public.rag_corpus
      ORDER BY embedding <#> $1::vector
      LIMIT $2
    """, emb_str, top_k)
    return [dict(r) for r in rows]

async def bm25_query(conn, q: str, top_k: int):
    rows = await conn.fetch("""
      SELECT id, source, source_id, title, text, metadata,
             ts_rank(ts, plainto_tsquery('english',$1)) AS bm25_score
      FROM public.rag_corpus
      WHERE ts @@ plainto_tsquery('english',$1)
      ORDER BY bm25_score DESC
      LIMIT $2
    """, q, top_k)
    return [dict(r) for r in rows]

def fuse(dense_items, bm25_items, ann_w=0.7, bm25_w=0.3):
    d_rank = {r["id"]: i+1 for i, r in enumerate(dense_items)}
    b_rank = {r["id"]: i+1 for i, r in enumerate(bm25_items)}
    all_ids = set(d_rank) | set(b_rank)
    fused = []
    for _id in all_ids:
        rr = rrf_score([d_rank.get(_id, 9999), b_rank.get(_id, 9999)])
        d_raw = next((r["dense_score"] for r in dense_items if r["id"] == _id), 0.0)
        b_raw = next((r["bm25_score"] for r in bm25_items if r["id"] == _id), 0.0)
        final = ann_w * float(d_raw) + bm25_w * float(b_raw)
        fused.append((_id, rr, final))
    fused.sort(key=lambda x: (x[2], x[1]), reverse=True)
    return fused
