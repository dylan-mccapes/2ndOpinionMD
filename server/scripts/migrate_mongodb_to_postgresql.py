import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from database.models.postgresql.database import async_session, init_db
from database.models.postgresql.models import User, JournalEntry
import os
from dotenv import load_dotenv
from datetime import datetime
import uuid
import json

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

async def migrate_data():
    print("Starting migration from MongoDB to PostgreSQL")
    
    await init_db()
    
    mongo_uri = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
    mongo_db_name = os.getenv("MONGO_DB_NAME", "2ndopinionmd")
    
    print(f"Connecting to MongoDB at {mongo_uri}, database {mongo_db_name}")
    mongo_client = AsyncIOMotorClient(mongo_uri)
    mongo_db = mongo_client[mongo_db_name]
    
    user_id_map = {}
    
    async with async_session() as session:
        print("Migrating users...")
        user_count = 0
        async for user_doc in mongo_db.users.find():
            mongo_id = user_doc.get('id', str(user_doc.get('_id')))
            pg_id = uuid.uuid4()
            user_id_map[mongo_id] = pg_id
            
            pg_user = User(
                id=pg_id,
                email=user_doc['email'],
                full_name=user_doc['full_name'],
                hashed_password=user_doc['hashed_password'],
                birthdate=user_doc.get('birthdate'),
                subscription_tier=user_doc.get('subscription_tier', 'basic'),
                created_at=user_doc.get('created_at', datetime.utcnow()),
                last_login=user_doc.get('last_login'),
                is_verified=user_doc.get('is_verified', False),
                verification_token=user_doc.get('verification_token'),
                verification_token_expires=user_doc.get('verification_token_expires'),
                failed_login_attempts=user_doc.get('failed_login_attempts', 0),
                locked_until=user_doc.get('locked_until'),
                password_reset_token=user_doc.get('password_reset_token'),
                password_reset_token_expires=user_doc.get('password_reset_token_expires')
            )
            session.add(pg_user)
            user_count += 1
            
            if user_count % 10 == 0:
                print(f"Processed {user_count} users")
        
        await session.commit()
        print(f"Migrated {user_count} users")
        
        print("Migrating journal entries...")
        entry_count = 0
        async for entry_doc in mongo_db.journal_entries.find():
            mongo_user_id = entry_doc['user_id']
            pg_user_id = user_id_map.get(mongo_user_id)
            
            if not pg_user_id:
                print(f"Warning: User ID {mongo_user_id} not found in mapping, skipping journal entry")
                continue
            
            pg_entry = JournalEntry(
                id=uuid.uuid4(),
                user_id=pg_user_id,
                date=entry_doc.get('date', datetime.utcnow()),
                symptoms=entry_doc.get('symptoms', []),
                environmental_factors=entry_doc.get('environmental_factors', []),
                stress_level=entry_doc.get('stress_level'),
                diet_notes=entry_doc.get('diet_notes'),
                sleep_quality=entry_doc.get('sleep_quality'),
                notes=entry_doc.get('notes'),
                analysis=entry_doc.get('analysis'),
                pattern_observations=entry_doc.get('patternObservations'),
                ai_analysis=entry_doc.get('ai_analysis'),
                created_at=entry_doc.get('created_at', datetime.utcnow()),
                updated_at=entry_doc.get('updated_at')
            )
            session.add(pg_entry)
            entry_count += 1
            
            if entry_count % 10 == 0:
                print(f"Processed {entry_count} journal entries")
                await session.commit()
        
        await session.commit()
        print(f"Migrated {entry_count} journal entries")
        
        print("Migration completed successfully")

if __name__ == "__main__":
    asyncio.run(migrate_data())
