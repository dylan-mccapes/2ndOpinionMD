#!/usr/bin/env python3
"""Fill rag_corpus.embedding_local (768-d) using sentence-transformers on GPU/CPU.

Expects SYNC_DATABASE_URL or DATABASE_URL (postgresql://...).

Usage (on 4090, from repo root inside WSL, venv active — Windows hosts: use WSL bash, not PowerShell):
  export SYNC_DATABASE_URL='postgresql://portalnode:PASS@127.0.0.1:5432/portalnode'
  export LOCAL_EMBED_MODEL=BAAI/bge-base-en-v1.5
  python server/scripts/embed_rag_corpus_local_slice.py --batch-size 128

Requires: sentence-transformers, psycopg[binary], pgvector (pip), torch with CUDA optional.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import datetime, timezone
from typing import List, Tuple

import numpy as np
import psycopg
from psycopg.rows import tuple_row


def _dsn() -> str:
    for k in ("SYNC_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL"):
        v = os.environ.get(k)
        if v:
            return v
    print("Set SYNC_DATABASE_URL or DATABASE_URL", file=sys.stderr)
    sys.exit(1)


def ensure_columns(cur) -> None:
    cur.execute(
        """
        ALTER TABLE public.rag_corpus
          ADD COLUMN IF NOT EXISTS embedding_local vector(768);
        ALTER TABLE public.rag_corpus
          ADD COLUMN IF NOT EXISTS embedding_local_model text;
        ALTER TABLE public.rag_corpus
          ADD COLUMN IF NOT EXISTS embedding_local_at timestamptz;
        """
    )


def _trunc(s: str, max_chars: int) -> str:
    if len(s) <= max_chars:
        return s
    return s[: max_chars - 20] + "\n…[truncated]"


def fetch_batch(cur, *, limit: int, offset_id: int | None) -> List[Tuple[int, str]]:
    if offset_id is None:
        cur.execute(
            """
            SELECT id, COALESCE(title, '') || E'\\n\\n' || text AS doc
            FROM public.rag_corpus
            WHERE embedding_local IS NULL
            ORDER BY id
            LIMIT %s
            """,
            (limit,),
        )
    else:
        cur.execute(
            """
            SELECT id, COALESCE(title, '') || E'\\n\\n' || text AS doc
            FROM public.rag_corpus
            WHERE embedding_local IS NULL AND id > %s
            ORDER BY id
            LIMIT %s
            """,
            (offset_id, limit),
        )
    out: List[Tuple[int, str]] = []
    for r in cur.fetchall():
        out.append((r[0], _trunc(r[1], 12000)))
    return out


def _vec_to_pg_literal(row: np.ndarray) -> str:
    return "[" + ",".join(f"{float(x):.8f}" for x in row) + "]"


def apply_batch(cur, ids: List[int], embs: np.ndarray, model_name: str, now) -> None:
    literals = [_vec_to_pg_literal(embs[i]) for i in range(len(ids))]
    cur.execute(
        """
        UPDATE public.rag_corpus AS r
        SET embedding_local = x.emb::vector,
            embedding_local_model = x.m,
            embedding_local_at = x.tt
        FROM (
          SELECT *
          FROM unnest(%s::bigint[], %s::text[], %s::text[], %s::timestamptz[])
            AS u(id, emb, m, tt)
        ) AS x
        WHERE r.id = x.id
        """,
        (ids, literals, [model_name] * len(ids), [now] * len(ids)),
    )


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=os.environ.get("LOCAL_EMBED_MODEL", "BAAI/bge-base-en-v1.5"))
    p.add_argument("--batch-size", type=int, default=128)
    p.add_argument("--max-rows", type=int, default=0, help="stop after this many updates (0 = no limit)")
    args = p.parse_args()

    from sentence_transformers import SentenceTransformer

    dsn = _dsn()
    device = os.environ.get("LOCAL_EMBED_DEVICE")
    if device is None:
        import torch

        device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"model={args.model} device={device}", flush=True)
    model = SentenceTransformer(args.model, device=device)
    model_name = args.model

    updated = 0
    t0 = time.monotonic()
    last_id: int | None = None

    with psycopg.connect(dsn, row_factory=tuple_row) as conn:
        conn.execute("SET statement_timeout = 0;")
        with conn.cursor() as cur:
            ensure_columns(cur)
        conn.commit()

        while True:
            with conn.cursor() as cur:
                rows = fetch_batch(cur, limit=args.batch_size, offset_id=last_id)
            if not rows:
                break
            ids = [r[0] for r in rows]
            texts = [r[1] for r in rows]
            embs = model.encode(
                texts,
                batch_size=min(64, len(texts)),
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            if embs.dtype != np.float32:
                embs = embs.astype(np.float32)
            now = datetime.now(timezone.utc)
            with conn.cursor() as cur:
                apply_batch(cur, ids, embs, model_name, now)
            conn.commit()
            updated += len(ids)
            last_id = ids[-1]
            elapsed = time.monotonic() - t0
            rate = updated / elapsed if elapsed > 0 else 0
            print(f"updated {updated} rows (~{rate:.0f} rows/s) last_id={last_id}", flush=True)
            if args.max_rows and updated >= args.max_rows:
                break

    print(f"done: {updated} rows in {time.monotonic() - t0:.1f}s")


if __name__ == "__main__":
    main()
