#!/usr/bin/env python3
"""
Test remote database connection to 2ndopinionmd.ai
"""

import psycopg2
import sys

def test_remote_connection():
    """Test connection to remote database"""
    print("🔍 Testing remote database connection...")
    
    try:
        conn = psycopg2.connect(
            dbname="2ndopinionmd",
            user="devin",
            password="devin123",
            host="2ndopinionmd.ai",
            port="5432"
        )
        print("✅ Remote database connection successful!")
        
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"PostgreSQL version: {version}")
        
        cursor.execute("""
            SELECT schema_name FROM information_schema.schemata 
            WHERE schema_name = 'ontology'
        """)
        ontology_exists = cursor.fetchone() is not None
        print(f"Ontology schema exists: {ontology_exists}")
        
        if not ontology_exists:
            print("Creating ontology schema...")
            cursor.execute("CREATE SCHEMA IF NOT EXISTS ontology")
            conn.commit()
            print("✅ Ontology schema created")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Remote database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_remote_connection()
    sys.exit(0 if success else 1)
