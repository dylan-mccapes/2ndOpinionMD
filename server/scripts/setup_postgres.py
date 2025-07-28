import asyncio
import os
import sys
from dotenv import load_dotenv
import asyncpg
from pgvector.asyncpg import register_vector

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

async def setup_postgres():
    """
    Set up PostgreSQL database with pgvector extension
    """
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://devin:devin123@localhost:5432/2ndopinionmd")
    
    parts = db_url.replace("postgresql+asyncpg://", "").split("/")
    dbname = parts[1]
    auth_host = parts[0].split("@")
    host_port = auth_host[1].split(":")
    user_pass = auth_host[0].split(":")
    
    user = user_pass[0]
    password = user_pass[1] if len(user_pass) > 1 else ""
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 5432
    
    print(f"Setting up PostgreSQL database: {dbname} on {host}:{port}")
    
    try:
        conn = await asyncpg.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database='postgres'
        )
        
        exists = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM pg_database WHERE datname = $1)",
            dbname
        )
        
        if not exists:
            print(f"Creating database {dbname}")
            await conn.execute(f'CREATE DATABASE "{dbname}"')
        else:
            print(f"Database {dbname} already exists")
        
        await conn.close()
        
        conn = await asyncpg.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=dbname
        )
        
        await register_vector(conn)
        
        await conn.execute('CREATE EXTENSION IF NOT EXISTS vector')
        
        print("PostgreSQL setup completed successfully")
        await conn.close()
        
        return True
    except Exception as e:
        print(f"Error setting up PostgreSQL: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(setup_postgres())
    sys.exit(0 if success else 1)
