# server/scripts/embed_timeline_events.py

from __future__ import annotations

import argparse
import asyncio
import os
from typing import List, Optional

import asyncpg
from openai import OpenAI

DEFAULT_MODEL = os.getenv("TIMELINE_EMBED_MODEL", "text-embedding-3-small")


async def fetch_batch(
    conn: asyncpg.Connection,
    batch_size: int,
    patient_like: Optional[str],
) -> List[asyncpg.Record]:
    if patient_like:
        rows = await conn.fetch(
            """
            SELECT id, text
            FROM ehr.patient_timeline
            WHERE embedding IS NULL
              AND patient_id LIKE $2
            ORDER BY id
            LIMIT $1
            """,
            batch_size,
            patient_like,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT id, text
            FROM ehr.patient_timeline
            WHERE embedding IS NULL
            ORDER BY id
            LIMIT $1
            """,
            batch_size,
        )
    return rows


async def embed_batch(
    client: OpenAI,
    model: str,
    rows: List[asyncpg.Record],
) -> List[List[float]]:
    texts = [(r["text"] or "") for r in rows]
    resp = client.embeddings.create(
        model=model,
        input=texts,
    )
    # resp.data is ordered corresponding to input
    return [d.embedding for d in resp.data]


async def write_batch(
    conn: asyncpg.Connection,
    rows: List[asyncpg.Record],
    vectors: List[List[float]],
) -> None:
    assert len(rows) == len(vectors)
    for row, vec in zip(rows, vectors):
        # Convert Python list[float] -> pgvector textual format
        # Example: [0.01, 0.02] -> "[0.01,0.02]"
        vec_str = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
        await conn.execute(
            """
            UPDATE ehr.patient_timeline
            SET embedding = $1::vector
            WHERE id = $2
            """,
            vec_str,
            row["id"],
        )


async def main_async(args: argparse.Namespace) -> None:
    database_url = args.database_url or os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set and --database-url was not provided")

    client = OpenAI()
    conn = await asyncpg.connect(database_url)

    try:
        remaining = args.max_events if args.max_events is not None else None
        total_embedded = 0

        while True:
            batch_size = args.batch_size
            if remaining is not None:
                if remaining <= 0:
                    break
                batch_size = min(batch_size, remaining)

            rows = await fetch_batch(conn, batch_size, args.patient_like)
            if not rows:
                break

            vectors = await embed_batch(client, args.model, rows)
            await write_batch(conn, rows, vectors)

            total_embedded += len(rows)
            if remaining is not None:
                remaining -= len(rows)

            print(f"Embedded {total_embedded} timeline events so far...")

        print(f"Done. Embedded {total_embedded} timeline events.")

    finally:
        await conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed ehr.patient_timeline events with OpenAI and pgvector",
    )
    parser.add_argument(
        "--database-url",
        help="Optional PostgreSQL DATABASE_URL; defaults to $DATABASE_URL",
    )
    parser.add_argument(
        "--patient-like",
        help="Optional patient_id LIKE filter, e.g. 'SCGP_%%'",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Number of events per embedding batch (default: 32)",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        help="Optional maximum number of events to embed (for testing)",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Embedding model name (default: {DEFAULT_MODEL})",
    )

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
