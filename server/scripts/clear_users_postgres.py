#!/usr/bin/env python3
import sys
import os
import asyncio
from pathlib import Path

# ✨ Put the REPO ROOT on sys.path (…/2ndOpinionMD-MVP), not …/server
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server.db import session as db_session
from sqlalchemy.ext.asyncio import create_async_engine
from database.models.postgresql.models import User, JournalEntry, DoctorPatientInvite
from sqlalchemy import delete, text, update

def _ensure_session_local():
    """When run standalone, SessionLocal may be None; init engine from DATABASE_URL."""
    if db_session.SessionLocal is None:
        url = os.getenv("DATABASE_URL", "postgresql+asyncpg://2ndopinionmd@localhost:5432/2ndopinionmd")
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        engine = create_async_engine(url, pool_pre_ping=False, pool_recycle=1800)
        db_session.init_session_factory(engine)

async def clear_users_table():
    _ensure_session_local()
    try:
        async with db_session.SessionLocal() as session:
            await session.execute(
                text(
                    "DELETE FROM ehr.patient_graph_chart WHERE patient_id IN (SELECT id::text FROM public.users)"
                )
            )
            await session.execute(
                text(
                    "DELETE FROM ehr.patient_graph_status WHERE patient_id IN (SELECT id::text FROM public.users)"
                )
            )
            await session.execute(
                text(
                    "DELETE FROM ehr.patient_graph_vision WHERE patient_id IN (SELECT id::text FROM public.users)"
                )
            )
            await session.execute(delete(DoctorPatientInvite))
            await session.execute(update(User).values(doctor_id=None))
            await session.execute(delete(JournalEntry))
            await session.execute(delete(User))
            await session.commit()
            print("Deleted invites, ehr graph rows for app users, journal entries, and all users.")
            return True
    except Exception as e:
        print(f"Error clearing users table: {e}")
        return False

if __name__ == "__main__":
    print("This deletes ALL users, journal entries, doctor invites, and ehr graph rows keyed by user UUIDs.")
    if input("Proceed? (yes/no): ").strip().lower() == "yes":
        asyncio.run(clear_users_table())
        print("Done.")
    else:
        print("Cancelled.")
