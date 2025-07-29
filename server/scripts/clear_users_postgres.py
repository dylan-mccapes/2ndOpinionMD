#!/usr/bin/env python3
"""
Script to clear the users table in PostgreSQL for 2ndOpinionMD.
This allows for fresh registrations with the fixed email verification system.
"""
import sys
import os
import asyncio
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from models.postgresql.database import async_session
from models.postgresql.models import User, JournalEntry
from sqlalchemy import delete

async def clear_users_table():
    """Clear all users from the PostgreSQL users table."""
    try:
        async with async_session() as session:
            journal_result = await session.execute(delete(JournalEntry))
            journal_count = journal_result.rowcount
            
            user_result = await session.execute(delete(User))
            user_count = user_result.rowcount
            
            await session.commit()
            
            print(f"Successfully deleted {journal_count} journal entry(ies) from the database.")
            print(f"Successfully deleted {user_count} user(s) from the database.")
            return True
    except Exception as e:
        print(f"Error clearing users table: {e}")
        return False

if __name__ == "__main__":
    print("This script will delete ALL users and their journal entries from the PostgreSQL database.")
    print("All users will need to re-register and verify their email addresses.")
    confirmation = input("Are you sure you want to proceed? (yes/no): ")
    
    if confirmation.lower() == "yes":
        asyncio.run(clear_users_table())
        print("Users table cleared. You can now register new users with email verification.")
    else:
        print("Operation cancelled.")
