#!/usr/bin/env python3
"""
Test script to verify PostgreSQL migration functionality
"""
import asyncio
import sys
import os
sys.path.append('/home/ubuntu/repos/2ndOpinionMD-MVP/server')

from server.db.session import SessionLocal
from database.models.postgresql.models import User, JournalEntry, MedicalKnowledge
from nlp_engines.vector_stores.postgresql_query_engine import PostgreSQLMedicalQueryEngine
from sqlalchemy import select, func
import uuid
from datetime import datetime

async def test_database_connection():
    """Test basic database connectivity"""
    print("Testing database connection...")
    try:
        async with SessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        connected = True
    except Exception:
        connected = False
    if connected:
        print("✅ Database connection successful")
        return True
    else:
        print("❌ Database connection failed")
        return False

async def test_medical_knowledge():
    """Test medical knowledge data and vector search"""
    print("\nTesting medical knowledge data...")
    
    async with SessionLocal() as session:
        result = await session.execute(select(func.count(MedicalKnowledge.id)))
        total = result.scalar()
        print(f"✅ Found {total} medical knowledge entries")
        
        query_engine = PostgreSQLMedicalQueryEngine()
        results = await query_engine.query_medical_knowledge("headache fever", top_k=3)
        
        if results:
            print(f"✅ Vector search working - found {len(results)} results")
            for result in results[:2]:
                print(f"  - {result['title']} (confidence: {result['confidence']}%)")
        else:
            print("⚠️ Vector search returned no results")

async def test_user_operations():
    """Test user creation and retrieval"""
    print("\nTesting user operations...")
    
    test_user_id = uuid.uuid4()
    test_email = f"test_{int(datetime.now().timestamp())}@example.com"
    
    async with SessionLocal() as session:
        test_user = User(
            id=test_user_id,
            email=test_email,
            full_name="Test User",
            hashed_password="hashed_password_here",
            is_verified=True
        )
        session.add(test_user)
        await session.commit()
        print(f"✅ Created test user: {test_email}")
        
        result = await session.execute(select(User).where(User.email == test_email))
        retrieved_user = result.scalar_one_or_none()
        
        if retrieved_user:
            print(f"✅ Retrieved user: {retrieved_user.full_name}")
        else:
            print("❌ Failed to retrieve user")
            return False
        
        await session.delete(retrieved_user)
        await session.commit()
        print("✅ Cleaned up test user")
        
    return True

async def test_journal_operations():
    """Test journal entry operations"""
    print("\nTesting journal operations...")
    
    test_user_id = uuid.uuid4()
    test_email = f"journal_test_{int(datetime.now().timestamp())}@example.com"
    
    async with SessionLocal() as session:
        test_user = User(
            id=test_user_id,
            email=test_email,
            full_name="Journal Test User",
            hashed_password="hashed_password_here",
            is_verified=True
        )
        session.add(test_user)
        await session.commit()
        
        test_entry = JournalEntry(
            user_id=test_user_id,
            symptoms=[{"name": "headache", "severity": 7}],
            environmental_factors=[{"factor": "stress", "level": 8}],
            stress_level=8,
            notes="Test journal entry"
        )
        session.add(test_entry)
        await session.commit()
        print("✅ Created test journal entry")
        
        result = await session.execute(
            select(JournalEntry).where(JournalEntry.user_id == test_user_id)
        )
        retrieved_entry = result.scalar_one_or_none()
        
        if retrieved_entry:
            print(f"✅ Retrieved journal entry with {len(retrieved_entry.symptoms)} symptoms")
        else:
            print("❌ Failed to retrieve journal entry")
            return False
        
        await session.delete(retrieved_entry)
        await session.delete(test_user)
        await session.commit()
        print("✅ Cleaned up test data")
        
    return True

async def main():
    """Run all tests"""
    print("🚀 Starting PostgreSQL Migration Tests\n")
    
    tests = [
        test_database_connection,
        test_medical_knowledge,
        test_user_operations,
        test_journal_operations
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! PostgreSQL migration is working correctly.")
        return True
    else:
        print("⚠️ Some tests failed. Please check the issues above.")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
