# server/timeline/embed_patient_timeline.py
from __future__ import annotations

import argparse
import asyncio
import os
from typing import List, Optional

import asyncpg
from openai import OpenAI

# Reuse the same default model env var as the global timeline embed script
DEFAULT_MODEL = os.getenv("TIMELINE_EMBED_MODEL", "text-embedding-3-small")

SELECT_NEEDS_EMB = """
SELECT id, text
FROM ehr.patient_timeline
WHERE patient_id = $1
  AND embedding IS NULL
ORDER BY ts
LIMIT $2;
"""


async def embed_batch(
    client: OpenAI,
    model: str,
    texts: List[str],
) -> List[List[float]]:
    """
    Safer embedding helper: call the embeddings API one text at a time.

    This avoids any subtle issues with the shape/type of `input`
    (e.g., lists-of-lists, weird objects, etc.) that can trigger
    `'$.input' is invalid` errors.
    """
    vectors: List[List[float]] = []

    for idx, t in enumerate(texts):
        # Make absolutely sure we're sending a plain string
        s = "" if t is None else str(t)

        resp = client.embeddings.create(
            model=model,
            input=s,
        )
        # Single input => single embedding
        vectors.append(resp.data[0].embedding)

    return vectors


async def embed_patient_timeline(
    dsn: str,
    patient_id: str,
    batch_size: int = 256,
    model: str = DEFAULT_MODEL,
) -> int:
    """
    Embed all ehr.patient_timeline events for a single patient_id where
    embedding IS NULL.

    Writes directly into ehr.patient_timeline.embedding (pgvector).
    """
    pool = await asyncpg.create_pool(dsn)
    client = OpenAI()
    total = 0

    async with pool.acquire() as conn:
        while True:
            rows = await conn.fetch(SELECT_NEEDS_EMB, patient_id, batch_size)
            if not rows:
                break

            ids = [r["id"] for r in rows]
            texts = [r["text"] or "" for r in rows]

            vectors = await embed_batch(client, model, texts)
            assert len(ids) == len(vectors)

            # One UPDATE per row, using pgvector textual format "[0.01,0.02,...]"
            async with conn.transaction():
                for rid, vec in zip(ids, vectors):
                    vec_str = "[" + ",".join(f"{x:.8f}" for x in vec) + "]"
                    await conn.execute(
                        """
                        UPDATE ehr.patient_timeline
                        SET embedding = $1::vector
                        WHERE id = $2
                        """,
                        vec_str,
                        rid,
                    )

            total += len(ids)
            print(f"Embedded {total} rows so far for {patient_id}...")

    await pool.close()
    print(f"Finished embeddings for {patient_id}: {total} rows.")
    return total


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Embed timeline events for a single patient_id",
    )
    parser.add_argument(
        "--patient-id",
        type=str,
        required=True,
        help="Exact patient_id in ehr.patient_timeline (e.g., 'MIMIC4_18218042')",
    )
    parser.add_argument(
        "--dsn",
        type=str,
        default=os.getenv(
            "DATABASE_URL",
            "postgresql://2ndopinionmd@localhost/2ndopinionmd",
        ),
        help="PostgreSQL DSN; defaults to $DATABASE_URL or local dev DSN",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=256,
        help="Number of events per embedding batch (default: 256)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"Embedding model name (default: {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    asyncio.run(
        embed_patient_timeline(
            dsn=args.dsn,
            patient_id=args.patient_id,
            batch_size=args.batch_size,
            model=args.model,
        )
    )


if __name__ == "__main__":
    main()