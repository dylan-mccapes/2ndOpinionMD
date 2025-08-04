#!/usr/bin/env python3
"""
HPO Import Verification Script
Verifies that HPO terms and disease associations were loaded correctly
"""

import psycopg2
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent
env_path = project_root / '.env'
load_dotenv(env_path)

def get_db_connection():
    """Create database connection"""
    try:
        conn = psycopg2.connect(
            dbname="2ndopinionmd",
            user="devin",
            password="devin123",
            host="localhost",
            port="5432"
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        sys.exit(1)

def verify_hpo_import():
    """Verify the HPO import was successful"""
    print("🔍 Verifying HPO import...")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'ontology' 
            AND table_name IN ('hpo_terms', 'hpo_disease_links')
            ORDER BY table_name
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        if 'hpo_terms' not in tables:
            print("❌ Error: ontology.hpo_terms table not found")
            return False
        
        if 'hpo_disease_links' not in tables:
            print("❌ Error: ontology.hpo_disease_links table not found")
            return False
        
        print("✅ Required tables found")
        
        cursor.execute("SELECT COUNT(*) FROM ontology.hpo_terms")
        terms_count = cursor.fetchone()[0]
        
        print(f"📊 HPO terms loaded: {terms_count:,}")
        
        if terms_count < 18000:
            print(f"⚠️ Warning: Expected >18,000 terms, found {terms_count}")
        else:
            print("✅ HPO terms count meets requirement (>18,000)")
        
        cursor.execute("SELECT COUNT(*) FROM ontology.hpo_disease_links")
        links_count = cursor.fetchone()[0]
        
        print(f"📊 Disease-phenotype associations loaded: {links_count:,}")
        
        cursor.execute("""
            SELECT COUNT(*) FROM ontology.hpo_disease_links 
            WHERE LOWER(disease_name) LIKE '%als%' 
            OR LOWER(disease_name) LIKE '%amyotrophic%'
            OR LOWER(disease_name) LIKE '%motor neuron%'
        """)
        als_count = cursor.fetchone()[0]
        
        print(f"📊 ALS-related disease associations: {als_count}")
        
        if als_count > 0:
            print("✅ ALS disease links found")
            
            cursor.execute("""
                SELECT database_id, disease_name, hpo_id 
                FROM ontology.hpo_disease_links 
                WHERE LOWER(disease_name) LIKE '%als%' 
                OR LOWER(disease_name) LIKE '%amyotrophic%'
                OR LOWER(disease_name) LIKE '%motor neuron%'
                LIMIT 5
            """)
            
            print("📋 Sample ALS entries:")
            for row in cursor.fetchall():
                print(f"   {row[0]}: {row[1]} -> {row[2]}")
        else:
            print("⚠️ Warning: No ALS-related disease links found")
        
        cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='hpo_terms' AND column_name IN ('term_vec', 'term_vec_json')
        """)
        vector_columns = [row[0] for row in cursor.fetchall()]
        
        if 'term_vec' in vector_columns:
            cursor.execute("SELECT COUNT(*) FROM ontology.hpo_terms WHERE term_vec IS NOT NULL")
            embedded_count = cursor.fetchone()[0]
            print(f"📊 Terms with vector embeddings: {embedded_count:,}")
        elif 'term_vec_json' in vector_columns:
            cursor.execute("SELECT COUNT(*) FROM ontology.hpo_terms WHERE term_vec_json IS NOT NULL")
            embedded_count = cursor.fetchone()[0]
            print(f"📊 Terms with JSON embeddings: {embedded_count:,}")
        else:
            embedded_count = 0
            print("⚠️ Warning: No embedding columns found")
        
        if embedded_count > 0:
            print("✅ Embeddings generated successfully")
        else:
            print("❌ Error: No embeddings found")
        
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename IN ('hpo_terms', 'hpo_disease_links')
            AND schemaname = 'ontology'
            ORDER BY indexname
        """)
        indexes = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 Database indexes created: {len(indexes)}")
        for idx in indexes:
            print(f"   - {idx}")
        
        if 'term_vec' in vector_columns:
            print("\n🔍 Testing vector similarity search...")
            try:
                cursor.execute("""
                    SELECT hpo_id, name, term_vec <=> (
                        SELECT term_vec FROM ontology.hpo_terms 
                        WHERE hpo_id = 'HP:0000001' LIMIT 1
                    ) AS similarity
                    FROM ontology.hpo_terms 
                    WHERE term_vec IS NOT NULL
                    ORDER BY similarity
                    LIMIT 5
                """)
                
                print("📋 Sample similarity search results:")
                for row in cursor.fetchall():
                    similarity_str = f"{row[2]:.4f}" if row[2] is not None else "N/A"
                    print(f"   {row[0]}: {row[1]} (similarity: {similarity_str})")
                
                print("✅ Vector similarity search working")
                
            except Exception as e:
                print(f"⚠️ Vector similarity search test failed: {e}")
        
        print(f"\n📈 Import Verification Summary:")
        print(f"   ✅ Tables created: {len(tables)}/2")
        print(f"   ✅ HPO terms: {terms_count:,} ({'✅' if terms_count >= 18000 else '⚠️'})")
        print(f"   ✅ Disease links: {links_count:,}")
        print(f"   ✅ ALS entries: {als_count} ({'✅' if als_count > 0 else '⚠️'})")
        print(f"   ✅ Embeddings: {embedded_count:,} ({'✅' if embedded_count > 0 else '❌'})")
        print(f"   ✅ Indexes: {len(indexes)}")
        
        success = (
            len(tables) == 2 and
            terms_count >= 18000 and
            links_count > 0 and
            als_count > 0 and
            embedded_count > 0
        )
        
        if success:
            print("\n🎉 HPO import verification PASSED!")
        else:
            print("\n❌ HPO import verification FAILED!")
        
        return success
        
    except Exception as e:
        print(f"❌ Error during verification: {e}")
        return False
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    success = verify_hpo_import()
    sys.exit(0 if success else 1)
