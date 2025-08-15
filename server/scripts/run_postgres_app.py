import os
import sys
import asyncio
import uvicorn
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

sys.path.insert(0, project_root)

def setup_and_run():
    """Setup database and run the FastAPI application"""
    
    async def test_db():
        try:
            from server.db.session import SessionLocal
            async with SessionLocal() as session:
                from sqlalchemy import text
                await session.execute(text("SELECT 1"))
            print("Database connection initialized successfully")
        except Exception as e:
            print(f"Error initializing database: {e}")
            print("Continuing to start server without database connection...")
    
    try:
        asyncio.run(test_db())
    except Exception as e:
        print(f"Error testing database: {e}")
    
    try:
        import sys
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from server.api.app_postgres import app
    except ImportError as e:
        print(f"Error importing FastAPI app: {e}")
        return
    
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"🚀 Starting FastAPI application on http://{host}:{port}")
    print(f"📚 API documentation available at: http://{host}:{port}/docs")
    
    uvicorn.run("server.api.app_postgres:app", host=host, port=port, reload=False)

if __name__ == "__main__":
    setup_and_run()
