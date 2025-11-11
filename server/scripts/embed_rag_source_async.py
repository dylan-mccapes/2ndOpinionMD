#!/usr/bin/env python3
from __future__ import annotations
import os, re, asyncio, math, random
import asyncpg
from typing import Sequence, Tuple, List
from openai import AsyncOpenAI
from openai import RateLimitError

EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
SOURCE      = os.getenv("RAG_SOURCE")  # optional override
BATCH       = int(os.getenv("RAG_BATCH", "64"))        # <=64 is safer for TPM
CONC        = int(os.getenv("RAG_CONCURRENCY", "2"))   # 1–4; start small

def dsn_from_env() -> str:
    dburl = (os.getenv("ASYNC_DATABASE_URL")
             or os.getenv("DATABASE_URL")
             or "postgresql://localhost/2ndopinionmd")
    # asyncpg expects 'postgresql://' or 'postgres://'
    return dburl.replace("postgresql+asyncpg://", "postgresql://").replace("postgres+asyncpg://", "postgres://")

def vec_text(v: Sequence[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in v) + "]"

async def fetch_pending(conn: asyncpg.Connection, source: str, limit: int) -> List[asyncpg.Record]:
    sql = """
    SELECT id, title, text
    FROM public.rag_corpus
    WHERE source=$1 AND embedding IS NULL
    ORDER BY id
    LIMIT $2
    """
    return await conn.fetch(sql, source, limit)

async def save_embeddings(conn: asyncpg.Connection, rows: Sequence[asyncpg.Record], vectors: Sequence[Sequence[float]]):
    pairs: List[Tuple[str, int]] = [(vec_text(v), int(r["id"])) for r, v in zip(rows, vectors)]
    await conn.executemany("UPDATE public.rag_corpus SET embedding=$1::vector WHERE id=$2", pairs)

def approx_tokens(texts: Sequence[str]) -> int:
    # quick heuristic ~4 chars/token, guard only
    return sum(max(1, len(t)//4) for t in texts)

async def embed_batch(client: AsyncOpenAI, texts: Sequence[str]) -> List[List[float]]:
    while True:
        try:
            resp = await client.embeddings.create(model=EMBED_MODEL, input=list(texts))
            return [d.embedding for d in resp.data]
        except RateLimitError as e:
            # parse "Try again in X.Ys"
            m = re.search(r"try again in (\d+(\.\d+)?)s", str(e), re.I)
            sleep = float(m.group(1)) if m else 3.0
            # jitter and cap
            sleep = min(15.0, sleep + random.random()*1.5)
            await asyncio.sleep(sleep)
        except Exception as e:
            # transient network errors → small backoff
            await asyncio.sleep(2.0)

async def worker(pool: asyncpg.Pool, client: AsyncOpenAI, source: str, wid: int):
    while True:
        async with pool.acquire() as conn:
            rows = await fetch_pending(conn, source, BATCH)
            if not rows:
                return
            texts = [(r["title"] or "") + "\n" + (r["text"] or "") for r in rows]
        # crude TPM guard: keep batch small; add small per-batch pause
        tks = approx_tokens(texts)
        if tks > 120_000:  # ~120k tokens per call guard
            # split batch if needed (rare with BATCH<=64)
            half = len(texts)//2 or 1
            await worker(pool, client, source, wid)
            continue

        vecs = await embed_batch(client, texts)

        async with pool.acquire() as conn:
            await save_embeddings(conn, rows, vecs)

        # small pacing to smooth RPM/TPM
        await asyncio.sleep(0.5 + random.random()*0.5)

async def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=SOURCE or "", help="rag_corpus.source to embed")
    ap.add_argument("--batch", type=int, default=BATCH)
    ap.add_argument("--concurrency", type=int, default=CONC)
    args = ap.parse_args()

    if not args.source:
        raise SystemExit("Provide --source")
    dsn = dsn_from_env()
    print(f"[embed] source={args.source} batch={args.batch} conc={args.concurrency} dsn={dsn}")

    pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=max(2, args.concurrency))
    client = AsyncOpenAI()

    # quick pending count
    async with pool.acquire() as conn:
        n = await conn.fetchval("SELECT COUNT(*) FROM public.rag_corpus WHERE source=$1 AND embedding IS NULL", args.source)
        print(f"[embed] pending={n}")

    sem = asyncio.Semaphore(args.concurrency)
    async def run_one(wid:int):
        async with sem:
            await worker(pool, client, args.source, wid)

    await asyncio.gather(*[run_one(i) for i in range(args.concurrency)])
    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
