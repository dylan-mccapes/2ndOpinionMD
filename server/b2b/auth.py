"""
B2B API key authentication — FastAPI dependency.

Usage in a router:

    from server.b2b.auth import require_b2b, require_scope, B2BContext

    @router.get("/v1/mkg/snomed/search")
    async def search(ctx: B2BContext = Depends(require_scope("mkg:read"))):
        ...

Dev bypass:
    Set DEV_AUTH_BYPASS=true in .env (only honoured when APP_ENV != production).
    All scope checks are skipped; a synthetic admin context is injected.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_session
from .api_keys import APIKeyRecord, has_scope
from .key_store import lookup_by_raw_key

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Dev bypass — active only when DEV_AUTH_BYPASS=true AND APP_ENV != production
# ---------------------------------------------------------------------------
_DEV_BYPASS_ACTIVE = (
    os.getenv("DEV_AUTH_BYPASS", "").lower() == "true"
    and os.getenv("APP_ENV", "local") != "production"
)

if _DEV_BYPASS_ACTIVE:
    logger.warning(
        "DEV_AUTH_BYPASS=true — B2B API key auth is DISABLED. "
        "Never set this in production."
    )

_DEV_KEY_RECORD = APIKeyRecord(
    id="dev-bypass",
    tenant_id="dev",
    key_hash="dev",
    key_prefix="2opmd_dev_",
    key_last4="byps",
    name="Dev Bypass (local only)",
    scopes=["admin"],          # admin grants all scopes via has_scope()
    rate_limit_rpm=9999,
    rate_limit_rpd=999_999,
    is_active=True,
    expires_at=None,
    created_at=datetime.utcnow(),
    last_used_at=None,
)

_DEV_B2B_CONTEXT: "B2BContext | None" = None  # populated after class definition

_bearer = HTTPBearer(auto_error=False)


@dataclass
class B2BContext:
    """Attached to every authenticated B2B request."""
    tenant_id: str
    api_key_id: str
    scopes: list[str]
    key_record: APIKeyRecord


# Finish wiring the dev sentinel now that B2BContext is defined.
_DEV_B2B_CONTEXT = B2BContext(
    tenant_id="dev",
    api_key_id="dev-bypass",
    scopes=["admin"],
    key_record=_DEV_KEY_RECORD,
)


async def _resolve_key(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> B2BContext:
    """
    Core dependency: extract Bearer token, validate against DB, return context.
    """
    if _DEV_BYPASS_ACTIVE:
        request.state.b2b = _DEV_B2B_CONTEXT
        return _DEV_B2B_CONTEXT  # type: ignore[return-value]

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
