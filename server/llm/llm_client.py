# server/llm/llm_client.py

from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import anyio
from openai import OpenAI

logger = logging.getLogger(__name__)

# --- Global OpenAI client ----------------------------------------------------

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


# --- Global concurrency limiter ---------------------------------------------

# Hard cap concurrent OpenAI calls. Tune as needed:
# 1 = super-safe, 2–3 = moderate, 5+ = aggressive.
_MAX_CONCURRENT = int(os.getenv("OPENAI_MAX_CONCURRENT", "2"))

# anyio.Semaphore works for both asyncio and trio backends
_semaphore = anyio.Semaphore(_MAX_CONCURRENT)


# --- Retry helpers -----------------------------------------------------------

async def _with_backoff(fn, *, max_retries: int = 3, base_delay: float = 0.8):
    """
    Run a sync fn() under concurrency control with simple exponential
    backoff for 429s. Let other errors bubble up.
    """
    delay = base_delay
    for attempt in range(max_retries):
        async with _semaphore:
            try:
                return await anyio.to_thread.run_sync(fn)
            except Exception as e:  # noqa: BLE001
                status = getattr(e, "status_code", None)
                # New OpenAI SDK usually sets status_code=429 on RateLimitError
                if status == 429 and attempt < max_retries - 1:
                    logger.warning(
                        "OpenAI 429 (attempt %s/%s). Sleeping %.1fs before retry.",
                        attempt + 1,
                        max_retries,
                        delay,
                    )
                    await anyio.sleep(delay)
                    delay *= 2.0
                    continue
                # Not a rate-limit or we’re out of retries → re-raise
                raise


# --- Public wrappers ---------------------------------------------------------

def get_async_openai_client() -> OpenAI:
    return _client

async def chat_completion_async(client=_client, max_retries: int = 3, **kwargs: Dict[str, Any]) -> Any:
    """
    Central async wrapper for chat completions.
    All code paths should call this instead of accessing OpenAI directly.
    """
    client = get_client()

    def _fn():
        return client.chat.completions.create(**kwargs)

    return await _with_backoff(_fn, max_retries=max_retries)


async def embedding_async(*, max_retries: int = 3, **kwargs: Dict[str, Any]) -> Any:
    """
    Central async wrapper for embeddings.
    """
    client = get_client()

    def _fn():
        return client.embeddings.create(**kwargs)

    return await _with_backoff(_fn, max_retries=max_retries)
