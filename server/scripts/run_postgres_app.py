import os
import sys
import uvicorn
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

sys.path.insert(0, project_root)

def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    
    print(f"🚀 Starting FastAPI application on http://{host}:{port}")
    print(f"📚 API documentation available at: http://{host}:{port}/docs")
    print("Database connection will be initialized during FastAPI lifespan startup")
    
    uvicorn.run(
        "server.api.app_postgres:app",
        host=host,
        port=port,
        reload=False,
        workers=1,
        log_level="info",
    )

if __name__ == "__main__":
    main()
