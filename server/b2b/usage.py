"""
Async usage metering — logs every B2B request to b2b.usage_events.

Collects events in a buffer and flushes to Postgres in batches to
avoid per-request INSERT overhead.
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

_FLUSH_INTERVAL = 5.0  # seconds
_FLUSH_BATCH = 100     # max rows per flush


@dataclass
class UsageEvent:
    api_key_id: str
    tenant_id: str
    endpoint: str
    method: str
    status_code: int
    response_ms: int
    tokens_used: int = 0


class UsageMeter:
    """Singleton that buffers usage events and flushes to Postgres."""

    def __init__(self):
        self._buffer: list[UsageEvent] = []
        self._session_maker: Optional[async_sessionmaker] = None
        self._task: Optional[asyncio.Task] = None

    def bind(self, session_maker: async_sessionmaker):
        self._session_maker = session_maker

    def record(self, event: UsageEvent):
        self._buffer.append(event)
        if len(self._buffer) >= _FLUSH_BATCH:
            # Schedule immediate flush
            if self._task is None or self._task.done():
                self._task = asyncio.ensure_future(self.flush())

    async def start(self):
        """Start the periodic flush loop (call from lifespan)."""
        self._task = asyncio.ensure_future(self._loop())

    async def stop(self):
        """Flush remaining and cancel loop."""
        if self._task and not self._task.done():
            self._task.cancel()
        await self.flush()

    async def _loop(self):
        while True:
            await asyncio.sleep(_FLUSH_INTERVAL)
            await self.flush()

    async def flush(self):
        if not self._buffer or self._session_maker is None:
            return

        batch = self._buffer[:_FLUSH_BATCH]
        self._buffer = self._buffer[_FLUSH_BATCH:]

        try:
            async with self._session_maker() as session:
                for evt in batch:
                    await session.execute(
                        text("""
                            INSERT INTO b2b.usage_events
                                (api_key_id, tenant_id, endpoint, method,
                                 status_code, response_ms, tokens_used)
                            VALUES
                                (:kid, :tid, :ep, :method,
                                 :sc, :ms, :tok)
                        """),
                        {
                            "kid": evt.api_key_id,
                            "tid": evt.tenant_id,
                            "ep": evt.endpoint,
                            "method": evt.method,
                            "sc": evt.status_code,
                            "ms": evt.response_ms,
                            "tok": evt.tokens_used,
                        },
                    )
                await session.commit()
            logger.debug("Flushed %d usage events", len(batch))
        except Exception:
            logger.exception("Failed to flush usage events (re-queuing %d)", len(batch))
            self._buffer = batch + self._buffer  # re-queue at front


# Module-level singleton
meter = UsageMeter()
