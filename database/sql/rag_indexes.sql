# server/scripts/embed_rag_source_async.py
# Loads .env automatically; fixes "DATABASE_URL not set".
#!/usr/bin/env python3
import os, asyncio, argparse
import asyncpg
from openai import AsyncOpenAI
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")
load_dotenv(REPO_ROOT / "server/.env")

EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

async def fetch_pending(conn, source, limit):
    return await conn.fetch(
        """
        SELECT id, coalesce(title,'') || E'\n\n' || coalesce(text,'') AS payload
        FROM public.rag_corpus
        WHERE source = $1 AND embedding IS NULL
        ORDER BY id
        LIMIT $2
        """, source, limit)

async def save_embeddings(conn, rows, vectors):
    await conn.executemany(
        "UPDATE public.rag_corpus SET embedding=$1 WHERE id=$2",
        [(vectors[i], rows[i]["id"]) for i in range(len(rows))]
    )

async def worker(pool, client, batch_q):
    while True:
        rows = await batch_q.get()
        if rows is None: return
        texts = [r["payload"][:7000] for r in rows]
        resp = await client.embeddings.create(model=EMBED_MODEL, input=texts)
        vecs = [d.embedding for d in resp.data]
        async with pool.acquire() as conn:
            await save_embeddings(conn, rows, vecs)
        batch_q.task_done()

async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    db = os.getenv("DATABASE_URL")
    if not db: raise SystemExit("DATABASE_URL not set")
    if not os.getenv("OPENAI_API_KEY"): raise SystemExit("OPENAI_API_KEY not set")

    client = AsyncOpenAI()
    pool = await asyncpg.create_pool(dsn=db)

    async with pool.acquire() as conn:
        pending = await conn.fetchval(
            "SELECT COUNT(*) FROM public.rag_corpus WHERE source=$1 AND embedding IS NULL", args.source)
    print(f"[embed] source={args.source} pending={pending}")

    q = asyncio.Queue()
    workers = [asyncio.create_task(worker(pool, client, q)) for _ in range(args.concurrency)]

    sent = 0
    while sent < pending:
        take = min(args.batch, pending - sent)
        async with pool.acquire() as conn:
            rows = await fetch_pending(conn, args.source, take)
        if not rows: break
        await q.put(rows)
        sent += len(rows)

    for _ in workers: await q.put(None)
    await asyncio.gather(*workers)
    await pool.close()
    print("[embed] done.")

if __name__ == "__main__":
    asyncio.run(main())

