#!/usr/bin/env python3
"""
Test database connection for unified ICD loader
"""

import psycopg2
import sys
import os
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

def test_connection():
    """Test database connection"""
    try:
        conn = psycopg2.connect(
            dbname="knowledgegraph",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        print("✅ Database connection successful")
        
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        if cur.fetchone():
            print("✅ pgvector extension is available")
        else:
            print("⚠️  pgvector extension not found - will be created during schema setup")
        
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
