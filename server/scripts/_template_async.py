import asyncio
from sqlalchemy import text
from server.db.session import SessionLocal

async def main():
    async with SessionLocal() as session:
        res = await session.execute(text("select 1"))
        print("db_ok:", res.scalar() == 1)

if __name__ == "__main__":
    asyncio.run(main())
