import os
import sys
import asyncio
import uvicorn
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

async def setup_and_run():
    from scripts.setup_postgres import setup_postgres
    success = await setup_postgres()
    
    if not success:
        print("Failed to set up PostgreSQL database. Exiting.")
        return
    
    try:
        from alembic.config import Config
        from alembic import command
        
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("Database migrations completed successfully")
    except Exception as e:
        print(f"Error running database migrations: {e}")
        return
    
    load_dotenv()
    port = int(os.getenv("PORT", "3001"))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting server on {host}:{port}")
    uvicorn.run("api.app_postgres:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    asyncio.run(setup_and_run())
