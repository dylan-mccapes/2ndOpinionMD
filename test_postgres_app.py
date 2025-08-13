#!/usr/bin/env python3
import asyncio
import sys
import os

server_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server')
sys.path.insert(0, server_dir)

from database.models.postgresql.database import ping_database
from database.models.postgresql.models import MedicalKnowledge
from database.models.postgresql.database import async_session
from sqlalchemy import func

async def test_database_connection():
    print("Testing PostgreSQL database connection...")
    connected = await ping_database()
    print(f"✅ Database connected: {connected}")
    return connected

async def test_icd10_data():
    print("Testing ICD-10 data count...")
    async with async_session() as session:
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
