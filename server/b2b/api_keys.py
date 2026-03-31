"""
API key generation, hashing, and validation.

Key format:  2opmd_{env}_{32 hex chars}
             e.g.  2opmd_live_a1b2c3d4e5f6...

The full key is returned exactly once at creation.  Only the SHA-256 hash
is stored in the database; lookups go through the hash.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


_KEY_BYTES = 16  # 16 bytes → 32 hex chars


@dataclass(frozen=True)
class APIKeyRecord:
    id: str
    tenant_id: str
    key_hash: str
    key_prefix: str
    key_last4: str
    name: Optional[str]
    scopes: list[str]
    rate_limit_rpm: int
    rate_limit_rpd: int
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    last_used_at: Optional[datetime]

    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() >= self.expires_at

    @property
    def is_valid(self) -> bool:
        return self.is_active and not self.is_expired


def generate_raw_key(env: str = "live") -> str:
    """Return a new random raw API key string (shown once to the user)."""
    if env not in ("live", "test"):
        raise ValueError("env must be 'live' or 'test'")
    token = secrets.token_hex(_KEY_BYTES)
    return f"2opmd_{env}_{token}"


def hash_key(raw_key: str) -> str:
    """Deterministic SHA-256 hash used for DB storage and lookup."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def key_prefix(raw_key: str) -> str:
    """Extract the prefix portion (e.g. '2opmd_live_')."""
    parts = raw_key.split("_", 2)
    if len(parts) < 3:
        raise ValueError("Malformed API key")
    return f"{parts[0]}_{parts[1]}_"


def key_last4(raw_key: str) -> str:
    return raw_key[-4:]


# ---------------------------------------------------------------------------
# Scope helpers
# ---------------------------------------------------------------------------

ALL_SCOPES = frozenset({
    "mkg:read",
    "mkg:evidence",
    "ptv:extract",
    "ptv:read",
    "admin",
})


def validate_scopes(scopes: list[str]) -> list[str]:
    bad = set(scopes) - ALL_SCOPES
    if bad:
        raise ValueError(f"Unknown scopes: {bad}")
    return sorted(set(scopes))


def has_scope(record: APIKeyRecord, required: str) -> bool:
    """Check if a key record has a required scope (admin grants everything)."""
    return "admin" in record.scopes or required in record.scopes
