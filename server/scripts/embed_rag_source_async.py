#!/usr/bin/env python3
import os, asyncio, json, time, math, argparse
from typing import List
import aiohttp
import psycopg2, psycopg2.extras

DSN   = (os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL") or "").strip()
MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
BATCH = int((os.getenv("BATCH") or "256").strip())
CONC  = int((os.getenv("CONC")  or "8").strip())
CHUNK = int(os.getenv("CHUNK", "96"))
APIKEY= os.getenv("OPENAI_API_KEY")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "6"))
BACKOFF = float(os.getenv("BACKOFF", "1.8"))

assert APIKEY, "OPENAI_API_KEY not set"
EMBED_URL = "https://api.openai.com/v1/embeddings"

def db():
    return psycopg2.connect(DSN)

async def embed_inputs(session: aiohttp.ClientSession, texts: List[str]) -> List[list]:
    # retry per-request (helps with sporadic 400 TransferEncodingError)
    attempt = 0
    while True:
        try:
            payload = {"model": MODEL, "input": texts}
            async with session.post(
                EMBED_URL,
                headers={"Authorization": f"Bearer {APIKEY}", "Content-Type":"application/json"},
                data=json.dumps(payload),
            ) as r:
                r.raise_for_status()
                data = await r.json()
                return [item["embedding"] for item in data["data"]]
        except Exception as e:
            attempt += 1
            if attempt >= MAX_RETRIES:
                raise
            await asyncio.sleep(BACKOFF * (2 ** (attempt-1)))

async def worker(name: str, http_session: aiohttp.ClientSession, source: str):
    while True:
        # 1) pull a locked batch
        with db() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("""
                SELECT id, COALESCE(content, text) AS body
                FROM public.rag_corpus
                WHERE source=%s AND COALESCE(content, text) IS NOT NULL AND embedding IS NULL
                ORDER BY id
                FOR UPDATE SKIP LOCKED
                LIMIT %s
            """, (source, BATCH))
            rows = cur.fetchall()
            if not rows:
                return
            ids   = [r["id"] for r in rows]
            texts = [r["body"] or "" for r in rows]

        # 2) embed in sub-chunks
        out: List[list] = []
        for i in range(0, len(texts), CHUNK):
            out.extend(await embed_inputs(http_session, texts[i:i+CHUNK]))

        # 3) write back
        with db() as conn, conn.cursor() as cur:
            psycopg2.extras.execute_values(
                cur,
                "UPDATE public.rag_corpus AS t "
                "SET embedding = data.embedding "
                "FROM (VALUES %s) AS data(id, embedding) "
                "WHERE t.id = data.id",
                [(ids[i], out[i]) for i in range(len(ids))],
                template="(%s, %s::vector)",
            )
        print(f"[{name}] embedded {len(ids)} rows")

async def main():
    parser = argparse.ArgumentParser(description="Embed RAG corpus rows for a given source")
    parser.add_argument("--source", type=str, default=None, help="Source to embed (overrides SOURCE env var)")
    args = parser.parse_args()
    
    source = args.source or "loinc"
    print(f"Embedding source: {source}")
    
    timeout = aiohttp.ClientTimeout(total=180)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [asyncio.create_task(worker(f"W{i+1}", session, source)) for i in range(CONC)]
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
