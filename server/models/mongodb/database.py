import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
DATABASE_NAME = os.getenv("MONGO_DB_NAME", "2ndopinionmd")

client = AsyncIOMotorClient(MONGO_URI)
database = client[DATABASE_NAME]

users_collection = database.users
journal_entries_collection = database.journal_entries
reports_collection = database.reports

async def ping_database():
    """Verify database connection is working"""
    try:
        await client.admin.command('ping')
        return True
    except ConnectionFailure:
        return False
