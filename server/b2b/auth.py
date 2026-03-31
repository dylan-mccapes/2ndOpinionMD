"""
B2B API key authentication — FastAPI dependency.

Usage in a router:

    from server.b2b.auth import require_b2b, require_scope, B2BContext

    @router.get("/v1/mkg/snomed/search")
    async def search(ctx: B2BContext = Depends(require_scope("mkg:read"))):
        ...
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_session
from .api_keys import APIKeyRecord, has_scope
from .key_store import lookup_by_raw_key

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


@dataclass
class B2BContext:
    """Attached to every authenticated B2B request."""
    tenant_id: str
    api_key_id: str
    scopes: list[str]
    key_record: APIKeyRecord


async def _resolve_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> B2BContext:
    """
    Core dependency: extract Bearer token, validate against DB, return context.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Pass Authorization: Bearer 2opmd_...",
        )

    raw_key = credentials.credentials

    if not raw_key.startswith("2opmd_"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format.",
        )

    record = await lookup_by_raw_key(session, raw_key)

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or unknown API key.",
        )

    if not record.is_valid:
        reason = "expired" if record.is_expired else "revoked"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"API key is {reason}.",
        )

    ctx = B2BContext(
        tenant_id=record.tenant_id,
        api_key_id=record.id,
        scopes=record.scopes,
        key_record=record,
    )

    # Stash on request.state so the usage middleware can read it
    request.state.b2b = ctx

    return ctx


# Public dependencies ---

require_b2b = _resolve_key  # any valid key, no scope check


def require_scope(scope: str):
    """Return a dependency that requires a specific scope."""

    async def _check(ctx: B2BContext = Depends(_resolve_key)) -> B2BContext:
        if not has_scope(ctx.key_record, scope):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This key lacks the required scope: {scope}",
            )
        return ctx

    return _check
