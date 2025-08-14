import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy import text
from dotenv import load_dotenv
import asyncpg
from pgvector.asyncpg import register_vector
from server.db.session import SessionLocal

load_dotenv()

Base = declarative_base()

async def init_db():
    from server.db.session import engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def ping_database():
    """Verify database connection is working"""
    try:
        from server.db.session import engine
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            return result.scalar() == 1
    except Exception:
        return False
