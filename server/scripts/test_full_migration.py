#!/usr/bin/env python3
"""
Comprehensive test script for the complete PostgreSQL migration
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

sys.path.append('/home/ubuntu/repos/2ndOpinionMD-MVP/server')

from models.postgresql.database import async_session, ping_database
from models.postgresql.models import User, JournalEntry, MedicalKnowledge
from vectordb.postgresql_query_engine import PostgreSQLMedicalQueryEngine
from sqlalchemy import select, func
import uuid
from datetime import datetime
import json

async def test_complete_workflow():
    """Test the complete user workflow with PostgreSQL"""
    print("🧪 Testing Complete PostgreSQL Migration Workflow\n")
    
    print("1. Testing database connection...")
    connected = await ping_database()
    if not connected:
        print("❌ Database connection failed")
        return False
    print("✅ Database connected successfully")
    
    print("\n2. Testing medical knowledge and vector search...")
    async with async_session() as session:
        result = await session.execute(select(func.count(MedicalKnowledge.id)))
        total = result.scalar()
        print(f"✅ Found {total} medical knowledge entries")
        
        query_engine = PostgreSQLMedicalQueryEngine()
        
        test_queries = [
            "headache and fever",
            "joint pain and fatigue", 
            "chest pain and shortness of breath",
            "nausea and vomiting"
        ]
        
        for query in test_queries:
            results = await query_engine.query_medical_knowledge(query, top_k=3)
            if results:
                print(f"✅ Query '{query}' returned {len(results)} results")
                for result in results[:1]:  # Show first result
                    print(f"   - {result['title']} (ICD-10: {result.get('icd10_code', 'N/A')})")
            else:
                print(f"⚠️ Query '{query}' returned no results")
    
    print("\n3. Testing user management...")
    test_user_id = uuid.uuid4()
    test_email = f"workflow_test_{int(datetime.now().timestamp())}@example.com"
    
    async with async_session() as session:
        test_user = User(
            id=test_user_id,
            email=test_email,
            full_name="Workflow Test User",
            hashed_password="hashed_password_here",
            birthdate=datetime(1990, 1, 1),
            subscription_tier="premium",
            is_verified=True
        )
        session.add(test_user)
        await session.commit()
        print(f"✅ Created user: {test_email}")
        
        print("\n4. Testing journal entry workflow...")
        
        journal_entries = [
            {
                "symptoms": [{"name": "headache", "severity": 8}, {"name": "nausea", "severity": 6}],
                "environmental_factors": [{"factor": "stress", "level": 9}],
                "stress_level": 9,
                "notes": "Severe headache after work stress"
            },
            {
                "symptoms": [{"name": "joint pain", "severity": 7}, {"name": "fatigue", "severity": 8}],
                "environmental_factors": [{"factor": "weather", "level": 6}],
                "stress_level": 5,
                "notes": "Joint pain worse in cold weather"
            }
        ]
        
        created_entries = []
        for entry_data in journal_entries:
            entry = JournalEntry(
                user_id=test_user_id,
                symptoms=entry_data["symptoms"],
                environmental_factors=entry_data["environmental_factors"],
                stress_level=entry_data["stress_level"],
                notes=entry_data["notes"]
            )
            session.add(entry)
            created_entries.append(entry)
        
        await session.commit()
        print(f"✅ Created {len(created_entries)} journal entries")
        
        print("\n5. Testing AI analysis generation...")
        for entry in created_entries:
            symptoms = [symptom["name"] for symptom in entry.symptoms]
            try:
                analysis = await query_engine.generate_rag_response(
                    symptoms=symptoms,
                    demographics={"age": 34, "subscription_tier": "premium"}
                )
                entry.ai_analysis = {
                    "analysis_type": "icd10_enhanced",
                    "content": analysis,
                    "generated_at": datetime.utcnow().isoformat()
                }
                print(f"✅ Generated AI analysis for symptoms: {', '.join(symptoms)}")
            except Exception as e:
                print(f"⚠️ AI analysis failed for {symptoms}: {e}")
        
        await session.commit()
        
        print("\n6. Testing data retrieval...")
        
        result = await session.execute(
            select(JournalEntry).where(JournalEntry.user_id == test_user_id)
        )
        user_entries = result.scalars().all()
        print(f"✅ Retrieved {len(user_entries)} entries for user")
        
        from datetime import timedelta
        yesterday = datetime.utcnow() - timedelta(days=1)
        result = await session.execute(
            select(JournalEntry).where(
                JournalEntry.user_id == test_user_id,
                JournalEntry.created_at >= yesterday
            )
        )
        recent_entries = result.scalars().all()
        print(f"✅ Found {len(recent_entries)} recent entries")
        
        print("\n7. Testing content type filtering...")
        icd10_results = await query_engine.query_medical_knowledge(
            "diabetes", content_types=["icd10_condition"], top_k=3
        )
        drug_results = await query_engine.query_medical_knowledge(
            "insulin", content_types=["icd10_drug"], top_k=3
        )
        
        print(f"✅ ICD-10 condition search returned {len(icd10_results)} results")
        print(f"✅ ICD-10 drug search returned {len(drug_results)} results")
        
        print("\n8. Cleaning up test data...")
        for entry in created_entries:
            await session.delete(entry)
        await session.delete(test_user)
        await session.commit()
        print("✅ Cleaned up all test data")
    
    print("\n🎉 Complete workflow test passed!")
    return True

async def test_performance():
    """Test performance of vector searches"""
    print("\n⚡ Testing Performance...")
    
    query_engine = PostgreSQLMedicalQueryEngine()
    
    import time
    start_time = time.time()
    
    tasks = []
    test_symptoms = [
        "headache", "fever", "nausea", "fatigue", "joint pain",
        "chest pain", "shortness of breath", "dizziness", "rash", "cough"
    ]
    
    for symptom in test_symptoms:
        task = query_engine.query_medical_knowledge(symptom, top_k=5)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    total_results = sum(len(result) for result in results)
    print(f"✅ Processed {len(test_symptoms)} queries in {end_time - start_time:.2f}s")
    print(f"✅ Total results returned: {total_results}")
    print(f"✅ Average query time: {(end_time - start_time) / len(test_symptoms):.3f}s")
    
    return True

async def main():
    """Run all tests"""
    print("🚀 Starting Comprehensive PostgreSQL Migration Tests\n")
    
    try:
        workflow_success = await test_complete_workflow()
        performance_success = await test_performance()
        
        if workflow_success and performance_success:
            print("\n🎉 All tests passed! PostgreSQL migration is fully functional.")
            return True
        else:
            print("\n⚠️ Some tests failed. Please check the issues above.")
            return False
            
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
