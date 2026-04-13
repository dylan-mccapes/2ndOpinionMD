from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from server.mock.fixtures.coding import CODING_RESPONSE
from server.mock.fixtures.streaming import mock_sse_stream

router = APIRouter(tags=["rag"])


@router.post("/api/rag/ask_stream")
async def ask_stream(body: dict = None):
    return StreamingResponse(
        mock_sse_stream(mode="ask"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/rag/eoh_stream")
async def eoh_stream(body: dict = None):
    return StreamingResponse(
        mock_sse_stream(mode="eoh"),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/coding")
async def coding(body: dict = None):
    return CODING_RESPONSE


@router.post("/api/rag/coding")
async def rag_coding(body: dict = None):
    return CODING_RESPONSE
