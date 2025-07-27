from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

from api.journal import router as journal_router
from api.auth_routes_postgres import router as auth_router
from models.postgresql.database import init_db
from api.auth_postgres import get_current_user_postgres

app = FastAPI(title="2ndOpinionMD API")

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(journal_router, prefix="/api", tags=["journal"], dependencies=[Depends(get_current_user_postgres)])

@app.on_event("startup")
async def startup_event():
    await init_db()

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "database": "PostgreSQL"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "3001"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("api.app_postgres:app", host=host, port=port, reload=True)
