#!/usr/bin/env python3
"""
Audit script to detect schema misalignments between database and SQLAlchemy models
Run from repo root: PYTHONPATH=. python server/scripts/audit_nullables.py
"""
import asyncio
import sys
import os

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from sqlalchemy import inspect
from server.db.session import engine

async def main():
    """Print potential mismatches between DB schema and expected nullability"""
    try:
        insp = inspect(engine.sync_engine)
        
        print("=== Auditing nullable fields across schemas ===")
        
        for schema in ("public", "ontology", "ehr", "text", "molecular", "guidelines"):
            try:
                tables = insp.get_table_names(schema=schema)
                if not tables:
                    continue
                    
                print(f"\n--- Schema: {schema} ---")
                for table in tables:
                    cols = insp.get_columns(table, schema=schema)
                    problematic_cols = []
                    
                    for c in cols:
                        if not c.get("nullable", True) and c.get("default") is None:
                            problematic_cols.append(c["name"])
                    
                    if problematic_cols:
                        print(f"  {table}: {', '.join(problematic_cols)} (NOT NULL, no default)")
                        
            except Exception as e:
                print(f"  Error inspecting schema {schema}: {e}")
                
        print("\n=== Users table detailed analysis ===")
        try:
            user_cols = insp.get_columns("users", schema="public")
            for c in user_cols:
                nullable = "NULL" if c.get("nullable", True) else "NOT NULL"
                default = f" DEFAULT {c.get('default')}" if c.get("default") else ""
                print(f"  {c['name']}: {c['type']} {nullable}{default}")
        except Exception as e:
            print(f"  Error inspecting users table: {e}")
            
    except Exception as e:
        print(f"❌ Database inspection failed: {e}")
        print("Note: This is expected if database is not running locally")

if __name__ == "__main__":
    asyncio.run(main())
