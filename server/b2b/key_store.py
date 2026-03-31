"""
Key store — async DB operations for API keys with an in-memory LRU cache.

The cache avoids a DB round-trip on every request.  Keys are cached for
`_CACHE_TTL` seconds after lookup; a revoke/update invalidates the entry.
"""
from __future__ import annotations

import logging
import time
from typing import Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .api_keys import APIKeyRecord, hash_key

logger = logging.getLogger(__name__)

_CACHE_TTL = 60  # seconds
_cache: dict[str, tuple[APIKeyRecord, float]] = {}


def _cache_get(key_hash: str) -> Optional[APIKeyRecord]:
    entry = _cache.get(key_hash)
    if entry is None:
        return None
    record, ts = entry
    if time.monotonic() - ts > _CACHE_TTL:
        del _cache[key_hash]
        return None
    return record


def _cache_put(key_hash: str, record: APIKeyRecord) -> None:
    _cache[key_hash] = (record, time.monotonic())


def cache_invalidate(key_hash: str) -> None:
    _cache.pop(key_hash, None)


def cache_clear() -> None:
    _cache.clear()


async def lookup_by_raw_key(
    session: AsyncSession,
    raw_key: str,
) -> Optional[APIKeyRecord]:
    """Hash the raw key and look it up.  Returns None if not found."""
    kh = hash_key(raw_key)
    cached = _cache_get(kh)
    if cached is not None:
        return cached

    row = (await session.execute(
        text("""
            SELECT k.id, k.tenant_id, k.key_hash, k.key_prefix, k.key_last4,
                   k.name, k.scopes, k.rate_limit_rpm, k.rate_limit_rpd,
                   k.is_active, k.expires_at, k.created_at, k.last_used_at
            FROM b2b.api_keys k
            JOIN b2b.tenants t ON t.id = k.tenant_id
            WHERE k.key_hash = :kh
              AND t.is_active = TRUE
        """),
        {"kh": kh},
    )).mappings().first()

    if row is None:
        return None

    record = APIKeyRecord(
        id=str(row["id"]),
        tenant_id=str(row["tenant_id"]),
        key_hash=row["key_hash"],
        key_prefix=row["key_prefix"],
        key_last4=row["key_last4"],
        name=row["name"],
        scopes=list(row["scopes"]) if row["scopes"] else [],
        rate_limit_rpm=row["rate_limit_rpm"],
        rate_limit_rpd=row["rate_limit_rpd"],
        is_active=row["is_active"],
        expires_at=row["expires_at"],
        created_at=row["created_at"],
        last_used_at=row["last_used_at"],
    )
    _cache_put(kh, record)

    # Fire-and-forget: touch last_used_at
    try:
        await session.execute(
            text("UPDATE b2b.api_keys SET last_used_at = NOW() WHERE key_hash = :kh"),
            {"kh": kh},
        )
        await session.commit()
    except Exception:
        logger.debug("Failed to touch last_used_at (non-fatal)")

    return record


async def create_key_record(
    session: AsyncSession,
    *,
    tenant_id: str,
    key_hash_val: str,
    prefix: str,
    last4: str,
    name: Optional[str],
    scopes: list[str],
    rate_limit_rpm: int = 60,
    rate_limit_rpd: int = 10000,
) -> str:
    """Insert a new API key row.  Returns the key UUID."""
    result = await session.execute(
        text("""
            INSERT INTO b2b.api_keys
                (tenant_id, key_hash, key_prefix, key_last4, name,
                 scopes, rate_limit_rpm, rate_limit_rpd)
            VALUES
                (:tid, :kh, :pfx, :l4, :name,
                 :scopes, :rpm, :rpd)
            RETURNING id
        """),
        {
            "tid": tenant_id,
            "kh": key_hash_val,
            "pfx": prefix,
            "l4": last4,
            "name": name,
            "scopes": scopes,
            "rpm": rate_limit_rpm,
            "rpd": rate_limit_rpd,
        },
    )
    key_id = str(result.scalar_one())
    await session.commit()
    return key_id


async def revoke_key(session: AsyncSession, key_id: str) -> bool:
    """Set is_active=FALSE.  Returns True if a row was updated."""
    # Grab hash for cache invalidation
    row = (await session.execute(
        text("SELECT key_hash FROM b2b.api_keys WHERE id = :kid"),
        {"kid": key_id},
    )).scalar_one_or_none()

    if row is None:
        return False

    cache_invalidate(row)

    result = await session.execute(
        text("UPDATE b2b.api_keys SET is_active = FALSE WHERE id = :kid"),
        {"kid": key_id},
    )
    await session.commit()
    return result.rowcount > 0


async def create_tenant(
    session: AsyncSession,
    *,
    name: str,
    contact_email: str,
    plan: str = "free",
) -> str:
    """Insert a new tenant row.  Returns the tenant UUID."""
    result = await session.execute(
        text("""
            INSERT INTO b2b.tenants (name, contact_email, plan)
            VALUES (:name, :email, :plan)
            RETURNING id
        """),
        {"name": name, "email": contact_email, "plan": plan},
    )
    tid = str(result.scalar_one())
    await session.commit()
    return tid
