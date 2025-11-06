#!/usr/bin/env python3
import sys, os, asyncio
from pathlib import Path

# ✨ Put the REPO ROOT on sys.path (…/2ndOpinionMD-MVP), not …/server
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server.db.session import SessionLocal
from database.models.postgresql.models import User, JournalEntry
from sqlalchemy import delete

async def clear_users_table():
    try:
        async with SessionLocal() as session:
            await session.execute(delete(JournalEntry))
            await session.execute(delete(User))
            await session.commit()
            print("Deleted all users and journal entries.")
            return True
    except Exception as e:
        print(f"Error clearing users table: {e}")
        return False

if __name__ == "__main__":
    print("This deletes ALL users and their journal entries.")
    if input("Proceed? (yes/no): ").strip().lower() == "yes":
        asyncio.run(clear_users_table())
        print("Done.")
    else:
        print("Cancelled.")
