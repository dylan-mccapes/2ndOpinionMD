from __future__ import annotations
import asyncio
from typing import Any, List

from server.api.db import init_pool  # adapt
from server.llm.llm_client import get_async_openai_client  # adapt
from server.timeline.embedding_cache import put_cached_query_embedding, get_cached_query_embedding
from server.eoh.timeline_summarizer import TIMELINE_ANN_LIBRARY  # or wherever you defined it

EMBED_MODEL = "text-embedding-3-small"  # adapt

async def main() -> None:
    pool = await init_pool()
    client = get_async_openai_client()

    phrases: List[str] = []
    for k, v in TIMELINE_ANN_LIBRARY.items():
        phrases.append(v["query"] if isinstance(v, dict) and "query" in v else str(v))

    # Dedup (normalized)
    seen = set()
    unique = []
    for p in phrases:
        pn = " ".join((p or "").lower().split())
        if pn and pn not in seen:
            unique.append(p)
            seen.add(pn)

    print(f"Seeding {len(unique)} ANN library phrases into ehr.query_embedding_cache...")

    for i, text in enumerate(unique, 1):
        # Skip if already cached
        cached = await get_cached_query_embedding(pool, model=EMBED_MODEL, input_text=text)
        if cached is not None:
            continue

        resp = await client.embeddings.create(model=EMBED_MODEL, input=text)
        vec = resp.data[0].embedding
        await put_cached_query_embedding(pool, model=EMBED_MODEL, input_text=text, embedding=vec)

        if i % 10 == 0:
            print(f"  seeded {i}/{len(unique)}")

    print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
