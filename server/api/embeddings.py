# server/api/embeddings.py
from __future__ import annotations
import os
import httpx
import asyncio
from typing import List

_OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
_EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")  # 1536 dims

class EmbedError(RuntimeError):
    pass

async def embed_query(text: str) -> List[float]:
    """
    Returns a list[float] embedding for the query text.
    Uses OpenAI /v1/embeddings via httpx.
    """
    if not _OPENAI_API_KEY:
        raise EmbedError("OPENAI_API_KEY not set")

    # tiny guard: OpenAI requires strings <= ~8k tokens; for safety trim very long queries
    text = (text or "").strip()
    if not text:
        return []
    if len(text) > 8000:
        text = text[:8000]

    url = "https://api.openai.com/v1/embeddings"
    headers = {
        "Authorization": f"Bearer {_OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"model": _EMBED_MODEL, "input": text}

    timeout = httpx.Timeout(20.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        vec = data["data"][0]["embedding"]
        # ensure python list[float]
        if not isinstance(vec, list) or not vec:
            raise EmbedError("Empty/invalid embedding returned")
        return [float(x) for x in vec]

