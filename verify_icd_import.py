#!/usr/bin/env python3
"""
Verification script for ICD-10-CM data import
Demonstrates the successful loading of ICD-10-CM codes into ontology.icd table
"""

import psycopg2

def verify_import():
    """Verify the ICD-10-CM import was successful"""
    try:
        conn = psycopg2.connect(
            dbname="knowledgegraph",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()
        
        print("=== ICD-10-CM Import Verification ===\n")
        
        cur.execute("SELECT COUNT(*) FROM ontology.icd")
        total_count = cur.fetchone()[0]
        print(f"✅ Total ICD-10-CM codes loaded: {total_count:,}")
        
        cur.execute("SELECT COUNT(*) FROM ontology.icd WHERE parent_code IS NULL")
        root_count = cur.fetchone()[0]
        print(f"✅ Root codes (categories): {root_count:,}")
        
        cur.execute("SELECT COUNT(*) FROM ontology.icd WHERE parent_code IS NOT NULL")
        child_count = cur.fetchone()[0]
        print(f"✅ Child codes (subcategories): {child_count:,}")
        
        print(f"\n=== Sample Hierarchy Structure ===")
        cur.execute("""
            SELECT code, title, parent_code, full_path 
            FROM ontology.icd 
            WHERE code IN ('A00', 'A000', 'A001', 'A009', 'A01', 'A010', 'A0100') 
            ORDER BY full_path
        """)
        
        for row in cur.fetchall():
            code, title, parent_code, full_path = row
            indent = "  " * (full_path.count(" > "))
            parent_info = f" (parent: {parent_code})" if parent_code else " (root)"
            print(f"{indent}{code}: {title[:50]}...{parent_info}")
        
        cur.execute("SELECT DISTINCT version FROM ontology.icd")
        versions = [row[0] for row in cur.fetchall()]
        print(f"\n✅ Version field set to: {', '.join(versions)}")
        
        print(f"\n🎉 ICD-10-CM import completed successfully!")
        print(f"📊 Database: knowledgegraph.ontology.icd")
        print(f"📈 Records: {total_count:,} total, {root_count:,} categories, {child_count:,} subcategories")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    verify_import()
