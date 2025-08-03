import os
from typing import Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    """Unified configuration management"""
    
    DATABASE_TYPE: str = "postgresql"  # postgresql, mongodb, or dual
    POSTGRESQL_URL: Optional[str] = None
    MONGODB_URL: Optional[str] = None
    
    VECTOR_ENGINE: str = "pgvector"  # pgvector or chromadb
    CHROMADB_PATH: str = "./chroma_db"
    
    OPENAI_API_KEY: Optional[str] = None
    MODEL_VERSION: str = "gpt-3.5-turbo"
    
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
