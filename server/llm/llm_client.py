# server/llm/llm_client.py

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import anyio
from openai import AsyncOpenAI, OpenAI

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Claude (Anthropic) client
# ---------------------------------------------------------------------------

CLAUDE_SYNTHESIS_MODEL = os.getenv("CLAUDE_SYNTHESIS_MODEL", "claude-opus-4-20250514")

PREFER_CLAUDE_SYNTHESIS = os.getenv("PREFER_CLAUDE_SYNTHESIS", "false").lower() in ("1", "true", "yes")

_anthropic_client = None


def get_anthropic_client():
    """Lazy-init Anthropic client. Returns None if no API key is set."""
    global _anthropic_client
    if _anthropic_client is not None:
        return _anthropic_client
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        _anthropic_client = anthropic.Anthropic(api_key=api_key)
        logger.info("Anthropic client initialized (model: %s)", CLAUDE_SYNTHESIS_MODEL)
        return _anthropic_client
    except Exception:
        logger.warning("Failed to initialize Anthropic client", exc_info=True)
        return None


def should_prefer_claude() -> bool:
    """True only when PREFER_CLAUDE_SYNTHESIS=true AND the Anthropic client is available.

    Having ANTHROPIC_API_KEY set is not enough — Opus must be explicitly
    opted-in via PREFER_CLAUDE_SYNTHESIS.  Without this gate, every call
    site that checks ``get_anthropic_client() is not None`` silently
    routes to Opus, burning ~10× the cost of GPT-4.1 for comparable work.
    """
    return PREFER_CLAUDE_SYNTHESIS and get_anthropic_client() is not None


async def claude_chat_async(
    *,
    messages: List[Dict[str, str]],
    system: str = "",
    model: Optional[str] = None,
    max_tokens: int = 8192,
    temperature: float = 0.2,
) -> str:
    """Call Claude via the Anthropic SDK. Returns the text content.

    Messages should be in OpenAI format [{"role": "user/assistant", "content": "..."}].
    The system prompt is passed separately (Anthropic API convention).
    """
    client = get_anthropic_client()
    if client is None:
        raise RuntimeError(
            "Anthropic client not available — set ANTHROPIC_API_KEY in .env"
        )

    _model = model or CLAUDE_SYNTHESIS_MODEL

    def _call():
        with client.messages.stream(
            model=_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        ) as stream:
            return stream.get_final_text()

    return await anyio.to_thread.run_sync(_call)

# ---------------------------------------------------------------------------
# Ollama client factory
# ---------------------------------------------------------------------------

def get_ollama_client(
    base_url: str = "http://localhost:11434/v1",
    api_key: str = "ollama",
) -> AsyncOpenAI:
    """
    Return an AsyncOpenAI client pointed at a local Ollama inference server.

    Ollama exposes an OpenAI-compatible API at /v1, so the standard SDK works
    as a drop-in.  The api_key value is ignored by Ollama but required by the
    SDK constructor.

    Usage:
        client = get_ollama_client()           # default localhost
        client = get_ollama_client("http://gpu-box:11434/v1")

    Model names must match what Ollama has pulled locally, e.g.:
        "llama3.1:8b", "mistral-nemo", "llama3.3:70b", "phi4"
    """
    return AsyncOpenAI(base_url=base_url, api_key=api_key)

# --- Global OpenAI client ----------------------------------------------------

_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI()
    return _client


# --- Global concurrency limiter ---------------------------------------------

_MAX_CONCURRENT = int(os.getenv("OPENAI_MAX_CONCURRENT", "2"))
_semaphore = anyio.Semaphore(_MAX_CONCURRENT)


# --- Retry helpers -----------------------------------------------------------

async def _with_backoff(fn, *, max_retries: int = 3, base_delay: float = 0.8):
    delay = base_delay
    for attempt in range(max_retries):
        async with _semaphore:
            try:
                return await anyio.to_thread.run_sync(fn)
            except Exception as e:  # noqa: BLE001
                if getattr(e, "status_code", None) == 429 and attempt < max_retries - 1:
                    logger.warning("OpenAI 429 (attempt %s/%s). Sleeping %.1fs.", attempt + 1, max_retries, delay)
                    await anyio.sleep(delay)
                    delay *= 2.0
                    continue
                raise


async def _with_backoff_async(fn_async, *, max_retries: int = 3, base_delay: float = 0.8):
    delay = base_delay
    for attempt in range(max_retries):
        async with _semaphore:
            try:
                return await fn_async()
            except Exception as e:  # noqa: BLE001
                if getattr(e, "status_code", None) == 429 and attempt < max_retries - 1:
                    logger.warning("OpenAI 429 (attempt %s/%s). Sleeping %.1fs.", attempt + 1, max_retries, delay)
                    await anyio.sleep(delay)
                    delay *= 2.0
                    continue
                raise


# --- Public wrappers ---------------------------------------------------------

def get_async_openai_client() -> AsyncOpenAI:
    return AsyncOpenAI()


async def chat_completion_async(client: Any = None, max_retries: int = 3, **kwargs: Dict[str, Any]) -> Any:
    explicit = kwargs.pop("client", client)

    if isinstance(explicit, AsyncOpenAI):
        async def _fn_async():
            return await explicit.chat.completions.create(**kwargs)
        return await _with_backoff_async(_fn_async, max_retries=max_retries)

    oai = get_client()

    def _fn():
        return oai.chat.completions.create(**kwargs)

    return await _with_backoff(_fn, max_retries=max_retries)


async def embedding_async(*, max_retries: int = 3, **kwargs: Dict[str, Any]) -> Any:
    client = get_client()

    def _fn():
        return client.embeddings.create(**kwargs)

    return await _with_backoff(_fn, max_retries=max_retries)
