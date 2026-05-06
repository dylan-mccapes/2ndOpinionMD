#!/usr/bin/env python3
import asyncio
import sys
import os

repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
server_dir = os.path.join(repo_root, "server")
sys.path.insert(0, repo_root)
sys.path.insert(0, server_dir)

from server.db.session import SessionLocal
from database.models.postgresql.models import MedicalKnowledge
from sqlalchemy import func

async def test_database_connection():
    print("Testing PostgreSQL database connection...")
    try:
        async with SessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        connected = True
    except Exception:
        connected = False
    print(f"✅ Database connected: {connected}")
    return connected

async def test_icd10_data():
    print("Testing ICD-10 data count...")
    async with SessionLocal() as session:
        result = await session.execute(func.count(MedicalKnowledge.id))
        count = result.scalar()
    print(f"✅ ICD-10 entries loaded: {count}")
    return count > 0

async def main():
    print("🔧 Testing PostgreSQL App Components")
    print("=" * 40)
    
    db_ok = await test_database_connection()
    data_ok = await test_icd10_data()
    
    if db_ok and data_ok:
        print("\n🎉 All tests passed! PostgreSQL app is ready.")
        return True
    else:
        print("\n❌ Some tests failed.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
