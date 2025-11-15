# server/api/embeddings.py
import os
from typing import List
from openai import AsyncOpenAI

_client = AsyncOpenAI()
_MODEL = os.getenv("EMBED_MODEL_QUERY", os.getenv("EMBED_MODEL", "text-embedding-3-small"))

async def embed_text(text: str) -> List[float]:
    # Keep it simple: one vector per query
    resp = await _client.embeddings.create(model=_MODEL, input=[text or ""])
    return resp.data[0].embedding

