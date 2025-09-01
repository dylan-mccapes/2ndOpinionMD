import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi import Request

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://2ndopinionmd@localhost:5432/2ndopinionmd")

if "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("+psycopg", "+asyncpg")

engine = None
SessionLocal: Optional[async_sessionmaker] = None

def init_session_factory(engine_):
    """Called by FastAPI lifespan to bind the async engine."""
    global engine, SessionLocal
    engine = engine_
    SessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)

async def get_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    Preferred path: use the session_maker placed on app.state by lifespan().
    Fallback: if SessionLocal exists (e.g., CLI contexts), use it.
    """
    session_maker = getattr(request.app.state, "session_maker", None) or SessionLocal
    if session_maker is None:
        tmp_engine = create_async_engine(
            DATABASE_URL,
            pool_pre_ping=False,
            pool_recycle=1800,
        )
        init_session_factory(tmp_engine)
        session_maker = SessionLocal
    async with session_maker() as session:
        yield session
