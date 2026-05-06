#!/usr/bin/env python3
"""
Debug script to check actual HPO ID formats in the database
This will help understand why disease links aren't matching
"""

import psycopg2

def debug_database_hpo_ids():
    """Debug actual HPO ID formats in database"""
    print("🔍 Debugging HPO ID formats in database...")
    
    try:
        conn = psycopg2.connect(
            dbname="2ndopinionmd",
            user="devin",
            password="devin123",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()
        
        cursor.execute("SELECT hpo_id FROM ontology.hpo_terms ORDER BY hpo_id LIMIT 20")
        db_hpo_ids = [row[0] for row in cursor.fetchall()]
        
        print("📊 Sample HPO IDs from hpo_terms table (first 20):")
        for i, hpo_id in enumerate(db_hpo_ids):
            print(f"  {i+1:2d}: {repr(hpo_id)}")
        
        test_ids = ['HP_0011097', 'HP_0002187', 'HP_0001518', 'HP_0032792', 'HP_0011451']
        print(f"\n🔍 Checking if converted HPO IDs exist in database:")
        for test_id in test_ids:
            cursor.execute("SELECT COUNT(*) FROM ontology.hpo_terms WHERE hpo_id = %s", (test_id,))
            count = cursor.fetchone()[0]
            print(f"  {test_id}: {'✅ EXISTS' if count > 0 else '❌ NOT FOUND'}")
        
        print(f"\n🔍 Searching for similar HPO IDs:")
        for test_id in test_ids:
            formats_to_try = [
                test_id,  # HP_0011097
                test_id.replace('HP_', 'HP:'),  # HP:0011097
                test_id.replace('HP_', 'http://purl.obolibrary.org/obo/HP_'),  # Full URL
                test_id.replace('HP_', 'HP_'),  # Same format
            ]
            
            for format_attempt in formats_to_try:
                cursor.execute("SELECT hpo_id FROM ontology.hpo_terms WHERE hpo_id = %s", (format_attempt,))
                result = cursor.fetchone()
                if result:
                    print(f"  Found {test_id} as: {repr(result[0])}")
                    break
            else:
                cursor.execute("SELECT hpo_id FROM ontology.hpo_terms WHERE hpo_id LIKE %s LIMIT 1", (f'%{test_id[-7:]}%',))
                result = cursor.fetchone()
                if result:
                    print(f"  Partial match for {test_id}: {repr(result[0])}")
        
        cursor.execute("SELECT COUNT(*) FROM ontology.hpo_terms")
        total_terms = cursor.fetchone()[0]
        print(f"\n📊 Total HPO terms in database: {total_terms}")
        
        cursor.execute("SELECT DISTINCT substring(hpo_id from 1 for 10) as prefix, COUNT(*) FROM ontology.hpo_terms GROUP BY prefix ORDER BY prefix LIMIT 10")
        prefixes = cursor.fetchall()
        print(f"\n📊 HPO ID prefix patterns:")
        for prefix, count in prefixes:
            print(f"  {repr(prefix)}: {count} terms")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("This script needs to be run where the database is accessible")

if __name__ == "__main__":
    debug_database_hpo_ids()
