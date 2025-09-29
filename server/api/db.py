# server/api/db.py
import os
from contextlib import asynccontextmanager

import asyncpg
import psycopg2
from psycopg2.extras import RealDictCursor

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from dotenv import load_dotenv

# Load .env from project if present
load_dotenv()

# =====================================================================================
# DSN helpers
# =====================================================================================

def _dsn_asyncpg() -> str:
    """
    Return a DSN suitable for asyncpg connections.
    Converts 'postgresql+asyncpg://' to 'postgresql://'.
    """
    url = os.getenv("DATABASE_URL", "")
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url

def _dsn_sqlalchemy_async() -> str:
    """
    Return a DSN suitable for SQLAlchemy async engine.
    Ensures '+asyncpg' is present.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url if "+asyncpg" in url else url.replace("postgresql://", "postgresql+asyncpg://", 1)
    # Fallback default
    return "postgresql+asyncpg://2ndopinionmd@localhost:5432/2ndopinionmd"

def _dsn_sync() -> str:
    """
    Prefer SYNC_DATABASE_URL; otherwise fall back to DATABASE_URL
    (stripping +asyncpg if present).
    """
    dsn = os.getenv("SYNC_DATABASE_URL")
    if dsn:
        return dsn
    dburl = os.getenv("DATABASE_URL", "")
    if dburl:
        return dburl.replace("+asyncpg", "")
    # Fallback default
    return "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"

# =====================================================================================
# asyncpg pool (kept for modules that use direct asyncpg)
# =====================================================================================

_pool = None  # module-level pool singleton

async def init_pool(min_size: int = 1, max_size: int = 8):
    """
    Initialize (or return existing) asyncpg pool using DATABASE_URL.
    """
    global _pool
    if _pool is None:
        dsn = _dsn_asyncpg()
        if not dsn:
            raise RuntimeError("DATABASE_URL is not set")
        _pool = await asyncpg.create_pool(dsn=dsn, min_size=min_size, max_size=max_size)
    return _pool

def get_pool():
    return _pool

async def close_pool():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

async def get_conn():
    """
    Acquire a connection from the asyncpg pool (caller must call put_conn).
    """
    pool = await init_pool()
    return await pool.acquire()

async def put_conn(conn):
    """
    Release a previously acquired connection back to the pool.
    """
    pool = get_pool()
    if pool is not None and conn is not None:
        await pool.release(conn)

@asynccontextmanager
async def connection():
    conn = await get_conn()
    try:
        yield conn
    finally:
        await put_conn(conn)

# Convenience helpers (some modules call these)
async def fetch(sql: str, *args):
    pool = await init_pool()
    async with pool.acquire() as conn:
        return await conn.fetch(sql, *args)

async def fetchrow(sql: str, *args):
    pool = await init_pool()
    async with pool.acquire() as conn:
        return await conn.fetchrow(sql, *args)

async def execute(sql: str, *args):
    pool = await init_pool()
    async with pool.acquire() as conn:
        return await conn.execute(sql, *args)

# =====================================================================================
# SQLAlchemy Async engine + session (for FastAPI routers)
# =====================================================================================

SQLALCHEMY_DATABASE_URL = _dsn_sqlalchemy_async()

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

# FastAPI dependency expected by routers
async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# Back-compat alias if some imports use a different name
get_session = get_async_session

# =====================================================================================
# Sync helper for quick reads (psycopg2)
# =====================================================================================

def pg_read(sql: str, params: tuple | None = None):
    """
    Run a read-only query and return a list[dict].
    Uses SYNC_DATABASE_URL if set; otherwise uses DATABASE_URL without '+asyncpg'.
    """
    dsn = _dsn_sync()
    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params or ())
            return cur.fetchall()

