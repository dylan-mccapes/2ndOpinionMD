import os
import sys
import asyncio
import uvicorn
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def setup_and_run():
    """Setup database and run the FastAPI application"""
    load_dotenv()
    
    try:
        from models.postgresql.database import init_db
        asyncio.run(init_db())
        print("Database connection initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        return
    
    try:
        from api.app_postgres import app
    except ImportError as e:
        print(f"Error importing FastAPI app: {e}")
        return
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting FastAPI application on http://{host}:{port}")
    print(f"📚 API documentation available at: http://{host}:{port}/docs")
    
    uvicorn.run("api.app_postgres:app", host=host, port=port, reload=True)

if __name__ == "__main__":
    setup_and_run()
