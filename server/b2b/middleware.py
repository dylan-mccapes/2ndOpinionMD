"""
B2B middleware — usage logging for /v1/ requests.

Attaches as FastAPI middleware.  After each /v1/ request completes,
records endpoint, status, and latency to the UsageMeter buffer.
"""
from __future__ import annotations

import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from .usage import meter, UsageEvent


class B2BUsageMiddleware(BaseHTTPMiddleware):
    """Logs usage for all /v1/ requests that passed B2B auth."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not request.url.path.startswith("/v1/"):
            return await call_next(request)

        t0 = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = int((time.perf_counter() - t0) * 1000)

        ctx = getattr(request.state, "b2b", None)
        if ctx is not None:
            meter.record(UsageEvent(
                api_key_id=ctx.api_key_id,
                tenant_id=ctx.tenant_id,
                endpoint=request.url.path,
                method=request.method,
                status_code=response.status_code,
                response_ms=elapsed_ms,
            ))

        return response
