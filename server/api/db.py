# server/api/db.py
import os
import asyncpg
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

_pool = None  # module-level pool singleton

def _dsn() -> str:
    url = os.getenv("DATABASE_URL", "")
    # Convert SQLAlchemy-style DSN to plain pg for asyncpg
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql://", 1)
    return url

async def init_pool(min_size: int = 1, max_size: int = 8):
    """
    Initialize (or return existing) asyncpg pool using DATABASE_URL.
    """
    global _pool
    if _pool is None:
        dsn = _dsn()
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

# -------- Compatibility helpers expected by older route modules -------- #

async def get_conn():
    """
    Acquire a connection from the pool (caller must call put_conn).
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

# Optional convenience context manager:
@asynccontextmanager
async def connection():
    conn = await get_conn()
    try:
        yield conn
    finally:
        await put_conn(conn)

# Common query helpers (some modules call these)
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

