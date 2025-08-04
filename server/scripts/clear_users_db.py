#!/usr/bin/env python3
"""
Script to clear the users collection in MongoDB for 2ndOpinionMD.
This allows for fresh registrations with the fixed email verification system.
"""
import sys
import os
import asyncio
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from database.models.mongodb.database import users_collection

async def clear_users_collection():
    """Clear all users from the MongoDB collection."""
    try:
        result = await users_collection.delete_many({})
        print(f"Successfully deleted {result.deleted_count} user(s) from the database.")
        return True
    except Exception as e:
        print(f"Error clearing users collection: {e}")
        return False

if __name__ == "__main__":
    print("This script will delete ALL users from the database.")
    print("All users will need to re-register and verify their email addresses.")
    confirmation = input("Are you sure you want to proceed? (yes/no): ")
    
    if confirmation.lower() == "yes":
        asyncio.run(clear_users_collection())
        print("Users collection cleared. You can now register new users with email verification.")
    else:
        print("Operation cancelled.")
