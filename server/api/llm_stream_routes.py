# server/api/llm_stream_routes.py
import json
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

router = APIRouter(prefix="/api/llm")
client = AsyncOpenAI()  # reads OPENAI_API_KEY

def sse(event: str, data: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode()

@router.get("/stream")
async def llm_stream(
    prompt: str = Query(..., alias="q"),
    model: str = "gpt-4o-mini",   # pick your default
    system: str = "You are a careful clinical summarizer."
):
    async def gen():
        yield sse("llm_start", {"model": model})
        stream = await client.chat.completions.create(
            model=model,
            stream=True,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield sse("llm_delta", {"text": delta.content})
        # Optional: finish/usage (if present on last chunk, you can stash it)
        yield sse("llm_end", {"ok": True})
    return StreamingResponse(gen(), media_type="text/event-stream")

@router.get("/stream2")
async def llm_stream2(q: str):
    async def gen():
        yield sse("llm_start", {"model": "gpt-4o-mini"})
        async with client.responses.stream(
            model="gpt-4o-mini",
            input=[{"role":"user","content": q}],
        ) as stream:
            async for event in stream:
                # Common pattern: emit text deltas as they arrive
                if getattr(event, "type", None) in ("text.delta", "response.output_text.delta"):
                    yield sse("llm_delta", {"text": event.delta})
        yield sse("llm_end", {"ok": True})
    return StreamingResponse(gen(), media_type="text/event-stream")