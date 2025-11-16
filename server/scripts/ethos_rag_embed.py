#!/usr/bin/env python3
"""
Ethos of Health → RAG embedding script

Embeds all public.rag_corpus rows where source='ethos_model' and embedding IS NULL
using the same OpenAI embedding model as the main RAG stack.
"""

import os
import sys
import time
from typing import List

import psycopg2
from psycopg2.extras import DictCursor
from dotenv import load_dotenv
from openai import OpenAI

# ---------------------------------------------------------------------------
# Env / config
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(PROJECT_ROOT, ".env")
load_dotenv(ENV_PATH)

EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
SYNC_DATABASE_URL = os.getenv(
    "SYNC_DATABASE_URL",
    "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd",
)

client = OpenAI()


def to_vec_literal(vec: List[float]) -> str:
    """
    Convert Python list[float] to pgvector-compatible text literal: '[0.1,0.2,...]'

    We always cast to ::vector in SQL, so asyncpg/psycopg don't need custom adapters.
    """
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def embed_texts(texts: List[str]) -> List[List[float]]:
    """Call OpenAI embeddings for a batch of texts."""
    if not texts:
        return []

    resp = client.embeddings.create(
        model=EMBED_MODEL,
        input=texts,
    )
    # New client returns .data with embedding attribute
    return [d.embedding for d in resp.data]  # type: ignore[no-any-return]


def main(batch_size: int = 32, dry_run: bool = False) -> None:
    print(f"Connecting to database: {SYNC_DATABASE_URL}")
    conn = psycopg2.connect(SYNC_DATABASE_URL)
    conn.autocommit = False

    pending_sql = """
        SELECT COUNT(*) 
        FROM public.rag_corpus
        WHERE source = 'ethos_model' AND embedding IS NULL;
    """

    with conn, conn.cursor(cursor_factory=DictCursor) as cur:
        cur.execute(pending_sql)
        pending = cur.fetchone()[0]
        print(f"Pending Ethos rows without embeddings: {pending}")

        if pending == 0:
            print("Nothing to do. Exiting.")
            return

        total_updated = 0

        while True:
            cur.execute(
                """
                SELECT id, title, text
                FROM public.rag_corpus
                WHERE source = 'ethos_model'
                  AND embedding IS NULL
                ORDER BY id
                LIMIT %s;
                """,
                (batch_size,),
            )
            rows = cur.fetchall()
            if not rows:
                break

            ids = [r["id"] for r in rows]
            texts = [
                (r["title"] or "") + "\n\n" + (r["text"] or "")
                for r in rows
            ]

            print(f"Embedding batch of {len(rows)} rows: ids={ids}")

            if dry_run:
                # Just show which IDs would be processed
                total_updated += len(rows)
                continue

            embeddings = embed_texts(texts)
            if len(embeddings) != len(rows):
                raise RuntimeError(
                    f"Embedding count mismatch: got {len(embeddings)}, expected {len(rows)}"
                )

            # Update each row with a vector literal
            for row, emb in zip(rows, embeddings):
                vec_literal = to_vec_literal(emb)
                cur.execute(
                    """
                    UPDATE public.rag_corpus
                    SET embedding = %s::vector
                    WHERE id = %s;
                    """,
                    (vec_literal, row["id"]),
                )

            conn.commit()
            total_updated += len(rows)
            print(f"Committed {len(rows)} embeddings (total so far: {total_updated})")

        print(
            f"Ethos embedding completed "
            f"({'dry run' if dry_run else 'real run'}). "
            f"Total rows handled: {total_updated}"
        )

        # Final sanity check
        cur.execute(pending_sql)
        remaining = cur.fetchone()[0]
        print(f"Remaining without embeddings: {remaining}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Embed Ethos of Health docs into public.rag_corpus.embedding"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Max rows per embedding batch (default: 32)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be embedded without updating the database",
    )

    args = parser.parse_args()
    try:
        main(batch_size=args.batch_size, dry_run=args.dry_run)
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.", file=sys.stderr)
        sys.exit(1)

