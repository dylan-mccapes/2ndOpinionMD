#!/usr/bin/env python3
import os, asyncio, logging, hashlib, time, math, random
from typing import List, Tuple, Dict
import psycopg
from psycopg.rows import tuple_row
from openai import AsyncOpenAI

# -------- Defaults (env-overridable) --------
DSN_DEFAULT         = os.getenv("POSTGRES_DSN", "postgresql://localhost/2ndopinionmd")
MODEL_DEFAULT       = os.getenv("EMBED_MODEL", "text-embedding-3-small")  # 1536 dims
SOURCE_DEFAULT      = os.getenv("EMBED_SOURCE", "mimic4_note")
BATCH_DEFAULT       = int(os.getenv("BATCH", "256"))        # rows to lock per DB batch
CONCURRENCY_DEFAULT = int(os.getenv("CONCURRENCY", "6"))    # workers (keep modest with RPM)
REQ_BATCH_DEFAULT   = int(os.getenv("REQ_BATCH", "128"))    # texts per API call (adapts down)
MAX_CHARS_DEFAULT   = int(os.getenv("EMBED_MAX_CHARS", "4000"))
LOG_EVERY_DEFAULT   = int(os.getenv("LOG_EVERY", "10"))

# OpenAI org limits (tune if your account differs)
TPM_DEFAULT         = int(os.getenv("OPENAI_TPM", "1000000"))  # text-embedding-3-small typical
RPM_DEFAULT         = int(os.getenv("OPENAI_RPM", "1000"))     # conservative default

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

try:
    import tiktoken
    _enc = tiktoken.get_encoding("o200k_base")
    def estimate_tokens(s: str) -> int: return len(_enc.encode(s))
except Exception:
    def estimate_tokens(s: str) -> int: return max(1, round(len(s)/4))

class TokenBucket:
    """Generic async token bucket (units/min)."""
    def __init__(self, units_per_min:int, headroom:float=0.9):
        self.capacity = max(1, int(units_per_min * headroom))
        self.tokens = float(self.capacity)
        self.rate = self.capacity / 60.0  # units per sec
        self.ts = time.perf_counter()
        self.lock = asyncio.Lock()

    async def acquire(self, cost:int):
        async with self.lock:
            now = time.perf_counter()
            elapsed = now - self.ts
            self.ts = now
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            need = cost - self.tokens
            if need > 0:
                await asyncio.sleep(need / self.rate)
                self.tokens = 0.0
            else:
                self.tokens -= cost

def clamp_text(s: str, max_chars: int) -> str:
    s = s or ""
    return s if len(s) <= max_chars else s[:max_chars]

def content_hash(title: str, text: str) -> str:
    h = hashlib.sha1()
    h.update((title or "").encode("utf-8")); h.update(b"\n"); h.update((text or "").encode("utf-8"))
    return h.hexdigest()

async def embed_batch(client: AsyncOpenAI, model: str,
                      chunks: List[str],
                      rpm_bucket: TokenBucket,
                      tpm_bucket: TokenBucket):
    # Request cost: 1 request + token cost
    req_tokens = sum(estimate_tokens(x) for x in chunks)
    await rpm_bucket.acquire(1)
    await tpm_bucket.acquire(req_tokens)
    return await client.embeddings.create(model=model, input=chunks)

async def embed_many(client: AsyncOpenAI, model: str, texts: List[str],
                     req_batch: int,
                     rpm_bucket: TokenBucket,
                     tpm_bucket: TokenBucket) -> List[List[float]]:
    """
    Embed a list of texts with adaptive batching + robust retry.
    Shrinks batch on repeated 429s; expands slowly on success.
    """
    out: List[List[float]] = []
    i = 0
    cur_batch = max(8, req_batch)
    success_streak = 0

    while i < len(texts):
        chunk = texts[i:i+cur_batch]
        attempt = 0
        while True:
            try:
                # jitter to desynchronize workers a bit
                if attempt == 0 and cur_batch >= 64:
                    await asyncio.sleep(random.uniform(0.0, 0.15))
                r = await embed_batch(client, model, chunk, rpm_bucket, tpm_bucket)
                out.extend([d.embedding for d in r.data])
                success_streak += 1
                # gentle restore of batch size
                if success_streak >= 4 and cur_batch < req_batch:
                    cur_batch = min(req_batch, cur_batch * 2)
                    success_streak = 0
                break
            except Exception as e:
                msg = str(e).lower()
                # Hard stop on budget exhaustion
                if "insufficient_quota" in msg:
                    logging.error("OpenAI quota exhausted (insufficient_quota). Aborting this worker.")
                    raise
                # Retryable buckets: rate, 429, timeout, 5xx/unavailable
                retryable = any(k in msg for k in [
                    "rate", "429", "timeout", "temporarily", "unavailable", "server error", "bad gateway"
                ])
                if not retryable or attempt >= 7:
                    logging.exception("Embed failed (giving up). batch=%d attempt=%d", len(chunk), attempt)
                    raise
                # Backoff with jitter; also shrink batch to reduce tokens/request
                delay = min(60.0, (2 ** attempt)) * (1.0 + random.uniform(0, 0.25))
                logging.warning("429/Rate/Transient error. backoff %.2fs (attempt %d). Shrinking batch %d -> %d",
                                delay, attempt+1, cur_batch, max(8, cur_batch // 2))
                cur_batch = max(8, cur_batch // 2)
                success_streak = 0
                await asyncio.sleep(delay)
                attempt += 1
                continue
        i += len(chunk)
    return out

async def fetch_batch(cur: psycopg.AsyncCursor, source: str, limit: int):
    await cur.execute("""
        WITH cte AS (
          SELECT id, COALESCE(title,'') AS title, COALESCE(text,'') AS text
          FROM rag_corpus
          WHERE source = %s AND embedding IS NULL
          ORDER BY id
          LIMIT %s
          FOR UPDATE SKIP LOCKED
        )
        SELECT id, title, text FROM cte;
    """, (source, limit))
    return await cur.fetchall()

async def write_batch(conn: psycopg.AsyncConnection, pairs: List[Tuple[int, list]]):
    """Bulk update via temp table; one commit per batch."""
    if not pairs:
        return
    try:
        async with conn.cursor() as cur:
            await cur.execute("SET LOCAL synchronous_commit=off")
            await cur.execute("""
                CREATE TEMP TABLE IF NOT EXISTS _emb (
                  id BIGINT PRIMARY KEY,
                  v  vector(1536)
                ) ON COMMIT DROP
            """)
            await cur.executemany(
                "INSERT INTO _emb (id, v) VALUES (%s, %s) ON CONFLICT (id) DO UPDATE SET v = EXCLUDED.v",
                pairs
            )
            await cur.execute("""
                UPDATE rag_corpus r
                   SET embedding = e.v
                  FROM _emb e
                 WHERE r.id = e.id
            """)
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise

async def upsert_cache(conn: psycopg.AsyncConnection, items: List[Tuple[str, list]]):
    if not items:
        return
    async with conn.cursor() as cur:
        await cur.executemany(
            "INSERT INTO embedding_cache (content_hash, embedding) VALUES (%s,%s) ON CONFLICT (content_hash) DO NOTHING",
            items
        )
    # ok to leave to outer commit

async def worker(worker_id: int, *, dsn: str, model: str, source: str,
                 batch: int, req_batch: int, max_chars: int, log_every: int,
                 tpm:int, rpm:int):
    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

    # Per-process buckets (shared by coroutine only); you can share globally with a Manager if desired
    rpm_bucket = TokenBucket(units_per_min=rpm, headroom=0.90)
    tpm_bucket = TokenBucket(units_per_min=tpm, headroom=0.88)

    async with await psycopg.AsyncConnection.connect(dsn) as conn:
        total = 0
        batches = 0
        while True:
            async with conn.cursor(row_factory=tuple_row) as cur:
                rows = await fetch_batch(cur, source, batch)

            if not rows:
                logging.info("[w%02d] done (total=%d)", worker_id, total)
                return

            ids, texts, hashes = [], [], []
            for (rid, title, text) in rows:
                t = clamp_text(text, max_chars)
                ids.append(rid)
                texts.append(t)
                hashes.append(content_hash(title, t))

            # Cache lookup
            async with conn.cursor(row_factory=tuple_row) as cur:
                await cur.execute(
                    "SELECT content_hash, embedding FROM embedding_cache WHERE content_hash = ANY(%s)",
                    (hashes,)
                )
                hit_rows = await cur.fetchall()
            hit_map: Dict[str, list] = {h: emb for (h, emb) in hit_rows}

            miss_indices = [i for i, h in enumerate(hashes) if h not in hit_map]
            miss_texts   = [texts[i] for i in miss_indices]

            id_vec_pairs: List[Tuple[int, list]] = []
            new_cache_items: List[Tuple[str, list]] = []

            # hits
            for i, h in enumerate(hashes):
                if h in hit_map:
                    id_vec_pairs.append((ids[i], hit_map[h]))

            # misses
            if miss_texts:
                embs = await embed_many(client, model, miss_texts, req_batch, rpm_bucket, tpm_bucket)
                for j, idx in enumerate(miss_indices):
                    vec = embs[j]; h = hashes[idx]
                    id_vec_pairs.append((ids[idx], vec))
                    new_cache_items.append((h, vec))
                # dedupe cache insert
                seen = set(); new_cache_items = [(h,v) for (h,v) in new_cache_items if not (h in seen or seen.add(h))]

            t0 = time.time()
            await write_batch(conn, id_vec_pairs)
            if new_cache_items:
                await upsert_cache(conn, new_cache_items)
            dt = time.time() - t0

            total += len(rows); batches += 1
            if batches % log_every == 0 or len(rows) < batch:
                logging.info(
                    "[w%02d] wrote=%d (this batch=%d in %.2fs) cache_hits=%d cache_miss=%d",
                    worker_id, total, len(rows), dt, len(rows) - len(miss_indices), len(miss_indices)
                )

async def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default=DSN_DEFAULT)
    ap.add_argument("--model", default=MODEL_DEFAULT)
    ap.add_argument("--source", default=SOURCE_DEFAULT)
    ap.add_argument("--batch", type=int, default=BATCH_DEFAULT)
    ap.add_argument("--concurrency", type=int, default=CONCURRENCY_DEFAULT)
    ap.add_argument("--req-batch", type=int, default=REQ_BATCH_DEFAULT)
    ap.add_argument("--max-chars", type=int, default=MAX_CHARS_DEFAULT)
    ap.add_argument("--log-every", type=int, default=LOG_EVERY_DEFAULT)
    ap.add_argument("--tpm", type=int, default=TPM_DEFAULT)
    ap.add_argument("--rpm", type=int, default=RPM_DEFAULT)
    args = ap.parse_args()

    logging.info(
        "Embedding source=%s batch=%d concurrency=%d req_batch=%d max_chars=%d model=%s dsn=%s",
        args.source, args.batch, args.concurrency, args.req_batch, args.max_chars, args.model, args.dsn
    )

    async with asyncio.TaskGroup() as tg:
        for wid in range(args.concurrency):
            tg.create_task(worker(
                wid, dsn=args.dsn, model=args.model, source=args.source,
                batch=args.batch, req_batch=args.req_batch, max_chars=args.max_chars, log_every=args.log_every,
                tpm=args.tpm, rpm=args.rpm,
            ))

if __name__ == "__main__":
    asyncio.run(main())
