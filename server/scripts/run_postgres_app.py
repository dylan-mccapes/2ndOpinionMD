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
    
    try:
        from database.models.postgresql.database import init_db
        asyncio.run(init_db())
        print("Database connection initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        print("Continuing to start server without database connection...")
    
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
    
    uvicorn.run(app, host=host, port=port, reload=True)

if __name__ == "__main__":
    setup_and_run()
