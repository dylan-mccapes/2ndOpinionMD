#!/usr/bin/env python3
"""
Setup HPO Database Schema
Creates the necessary tables and indexes for HPO integration
"""

import psycopg2
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent
env_path = project_root / '.env'
load_dotenv(env_path)

def setup_hpo_schema():
    """Set up HPO database schema"""
    print("🔧 Setting up HPO database schema...")
    
    try:
        conn = psycopg2.connect(
            dbname="2ndopinionmd",
            user="devin",
            password="devin123",
            host="localhost",
            port="5432"
        )
        print("✅ Database connection successful")
        
        cursor = conn.cursor()
        
        schema_file = "database/schemas/setup_hpo_schema.sql"
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        print("📋 Executing HPO schema setup...")
        cursor.execute(schema_sql)
        conn.commit()
        print("✅ HPO schema created successfully")
        
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'ontology' 
            AND table_name IN ('hpo_terms', 'hpo_disease_links')
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"📊 Created tables: {tables}")
        
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='hpo_terms' AND column_name IN ('term_vec', 'term_vec_json')
        """)
        vector_columns = [row[0] for row in cursor.fetchall()]
        print(f"📊 Vector columns: {vector_columns}")
        
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename IN ('hpo_terms', 'hpo_disease_links')
            AND schemaname = 'ontology'
            ORDER BY indexname
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        print(f"📊 Created indexes: {indexes}")
        
        cursor.close()
        conn.close()
        
        print("🎉 HPO database schema setup completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Schema setup failed: {e}")
        return False

if __name__ == "__main__":
    success = setup_hpo_schema()
    sys.exit(0 if success else 1)
