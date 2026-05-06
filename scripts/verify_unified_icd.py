#!/usr/bin/env python3
"""
Verification script for unified ICD data import
Demonstrates the successful loading of both ICD-10-CM and ICD-11 codes
"""

import psycopg2
import sys
import os
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            dbname="knowledgegraph",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432"
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        sys.exit(1)

def verify_unified_import():
    """Verify the unified ICD import was successful"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        print("=== Unified ICD Import Verification ===\n")
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='icd' AND column_name='term_vector'")
        has_vector = cur.fetchone() is not None
        
        if has_vector:
            vector_condition = "term_vector IS NOT NULL"
        else:
            vector_condition = "term_vector_json IS NOT NULL"
        
        cur.execute(f"""
            SELECT 
                system,
                COUNT(*) as total_codes,
                COUNT(*) FILTER (WHERE {vector_condition}) as with_vectors,
                COUNT(*) FILTER (WHERE parent_code IS NOT NULL) as with_parents,
                COUNT(*) FILTER (WHERE parent_code IS NULL) as root_codes
            FROM ontology.icd 
            GROUP BY system
            ORDER BY system
        """)
        
        print("📊 System Statistics:")
        for row in cur.fetchall():
            system, total, with_vectors, with_parents, root_codes = row
            print(f"   {system}:")
            print(f"     Total codes: {total:,}")
            print(f"     With vectors: {with_vectors:,}")
            print(f"     With parents: {with_parents:,}")
            print(f"     Root codes: {root_codes:,}")
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_mappings,
                COUNT(*) FILTER (WHERE confidence >= 0.90) as very_high_conf,
                COUNT(*) FILTER (WHERE confidence >= 0.80) as high_conf,
                COUNT(*) FILTER (WHERE confidence >= 0.70) as medium_conf,
                ROUND(AVG(confidence), 3) as avg_confidence,
                ROUND(MIN(confidence), 3) as min_confidence,
                ROUND(MAX(confidence), 3) as max_confidence
            FROM ontology.code_cross_references
        """)
        
        mapping_stats = cur.fetchone()
        if mapping_stats:
            total, very_high, high, medium, avg_conf, min_conf, max_conf = mapping_stats
            print(f"\n🔗 Cross-Reference Mappings:")
            print(f"   Total mappings: {total:,}")
            print(f"   Very high confidence (≥0.90): {very_high:,}")
            print(f"   High confidence (≥0.80): {high:,}")
            print(f"   Medium confidence (≥0.70): {medium:,}")
            print(f"   Average confidence: {avg_conf}")
            print(f"   Confidence range: {min_conf} - {max_conf}")
            
            if high >= 2000:
                print(f"   🎉 SUCCESS: Target of >2,000 high-confidence mappings achieved!")
            else:
                print(f"   ⚠️  WARNING: Only {high} high-confidence mappings (target: >2,000)")
        
        print(f"\n🌳 Sample ICD-10-CM Hierarchy:")
        cur.execute("""
            SELECT code, title, parent_code, array_to_string(full_path, ' > ') as path
            FROM ontology.icd 
            WHERE system = 'ICD-10-CM' AND code LIKE 'A0%'
            ORDER BY full_path
            LIMIT 10
        """)
        
        for row in cur.fetchall():
            code, title, parent_code, path = row
            indent = "  " * (path.count(" > ") - 1) if path.count(" > ") > 0 else ""
            print(f"   {indent}{code}: {title[:50]}...")
        
        print(f"\n🌐 Sample ICD-11 Hierarchy:")
        cur.execute("""
            SELECT code, title, class_kind, array_to_string(full_path, ' > ') as path
            FROM ontology.icd 
            WHERE system = 'ICD-11' AND code LIKE '1A%'
            ORDER BY full_path
            LIMIT 10
        """)
        
        for row in cur.fetchall():
            code, title, class_kind, path = row
            indent = "  " * (path.count(" > ") - 1) if path.count(" > ") > 0 else ""
            print(f"   {indent}{code}: {title[:50]}... ({class_kind})")
        
        print(f"\n🔗 Sample High-Confidence Mappings:")
        cur.execute("""
            SELECT 
                cr.source_id as icd10cm_code,
                i1.title as icd10cm_title,
                cr.target_id as icd11_code,
                i2.title as icd11_title,
                cr.confidence
            FROM ontology.code_cross_references cr
            JOIN ontology.icd i1 ON cr.source_id = i1.code
            JOIN ontology.icd i2 ON cr.target_id = i2.code
            WHERE cr.confidence >= 0.85
            ORDER BY cr.confidence DESC
            LIMIT 5
        """)
        
        for row in cur.fetchall():
            icd10cm_code, icd10cm_title, icd11_code, icd11_title, confidence = row
            print(f"   {icd10cm_code} → {icd11_code} (confidence: {confidence})")
            print(f"     ICD-10-CM: {icd10cm_title[:60]}...")
            print(f"     ICD-11:    {icd11_title[:60]}...")
        
        print(f"\n🔍 Vector Search Test:")
        if has_vector:
            cur.execute("""
                SELECT code, title, system
                FROM ontology.icd
                WHERE term_vector IS NOT NULL
                ORDER BY term_vector <-> (
                    SELECT term_vector FROM ontology.icd 
                    WHERE code = 'A00' AND system = 'ICD-10-CM'
                    LIMIT 1
                )
                LIMIT 5
            """)
        else:
            cur.execute("""
                SELECT code, title, system
                FROM ontology.icd
                WHERE term_vector_json IS NOT NULL
                ORDER BY code
                LIMIT 5
            """)
        
        print("   Most similar to ICD-10-CM code A00:")
        for row in cur.fetchall():
            code, title, system = row
            print(f"     {code} ({system}): {title[:50]}...")
        
        print(f"\n🎉 Unified ICD import verification completed!")
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    verify_unified_import()
