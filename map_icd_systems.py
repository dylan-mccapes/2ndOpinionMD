#!/usr/bin/env python3
"""
Cross-System ICD Mapping using Cosine Similarity
Maps ICD-10-CM codes to ICD-11 codes using vector embeddings
"""

import psycopg2
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import sys
import os
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.abspath(__file__))
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

def map_icd_systems(confidence_threshold=0.80):
    """Map ICD-10-CM to ICD-11 using cosine similarity"""
    print(f"Starting cross-system mapping with confidence threshold: {confidence_threshold}")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='icd' AND column_name='term_vector'")
        has_vector = cur.fetchone() is not None
        
        if has_vector:
            print("Loading ICD-10-CM codes and vectors...")
            cur.execute("""
                SELECT code, term_vector, title 
                FROM ontology.icd 
                WHERE system = 'ICD-10-CM' AND term_vector IS NOT NULL
            """)
            icd10cm_data = cur.fetchall()
            print(f"Loaded {len(icd10cm_data)} ICD-10-CM codes with vectors")
            
            print("Loading ICD-11 codes and vectors...")
            cur.execute("""
                SELECT code, term_vector, title 
                FROM ontology.icd 
                WHERE system = 'ICD-11' AND term_vector IS NOT NULL
            """)
            icd11_data = cur.fetchall()
            print(f"Loaded {len(icd11_data)} ICD-11 codes with vectors")
        else:
            import json
            print("Loading ICD-10-CM codes and vectors (JSON fallback)...")
            cur.execute("""
                SELECT code, term_vector_json, title 
                FROM ontology.icd 
                WHERE system = 'ICD-10-CM' AND term_vector_json IS NOT NULL
            """)
            icd10cm_raw = cur.fetchall()
            icd10cm_data = [(code, json.loads(vector_json), title) for code, vector_json, title in icd10cm_raw]
            print(f"Loaded {len(icd10cm_data)} ICD-10-CM codes with vectors")
            
            print("Loading ICD-11 codes and vectors (JSON fallback)...")
            cur.execute("""
                SELECT code, term_vector_json, title 
                FROM ontology.icd 
                WHERE system = 'ICD-11' AND term_vector_json IS NOT NULL
            """)
            icd11_raw = cur.fetchall()
            icd11_data = [(code, json.loads(vector_json), title) for code, vector_json, title in icd11_raw]
            print(f"Loaded {len(icd11_data)} ICD-11 codes with vectors")
        
        if not icd10cm_data or not icd11_data:
            print("Error: No vector data found for one or both systems")
            return
        
        print("Clearing existing cross-reference mappings...")
        cur.execute("DELETE FROM ontology.code_cross_references")
        conn.commit()
        
        mappings_created = 0
        high_confidence_mappings = 0
        
        print("Computing cosine similarities using vectorized operations...")
        
        print("Converting vectors to matrices...")
        icd10cm_codes = []
        icd10cm_vectors = []
        icd10cm_titles = []
        
        for code, vector, title in icd10cm_data:
            if vector:
                if isinstance(vector, str):
                    import json
                    vector = json.loads(vector)
                icd10cm_codes.append(code)
                icd10cm_vectors.append(vector)
                icd10cm_titles.append(title)
        
        icd11_codes = []
        icd11_vectors = []
        icd11_titles = []
        
        for code, vector, title in icd11_data:
            if vector:
                if isinstance(vector, str):
                    import json
                    vector = json.loads(vector)
                icd11_codes.append(code)
                icd11_vectors.append(vector)
                icd11_titles.append(title)
        
        icd10cm_vectors = np.array(icd10cm_vectors)
        icd11_vectors = np.array(icd11_vectors)
        
        print(f"Matrix shapes: ICD-10-CM {icd10cm_vectors.shape}, ICD-11 {icd11_vectors.shape}")
        
        batch_size = 1000
        total_batches = (len(icd10cm_codes) + batch_size - 1) // batch_size
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, len(icd10cm_codes))
            
            print(f"Processing batch {batch_idx + 1}/{total_batches} (codes {start_idx}-{end_idx})")
            
            batch_vectors = icd10cm_vectors[start_idx:end_idx]
            batch_codes = icd10cm_codes[start_idx:end_idx]
            
            similarity_matrix = cosine_similarity(batch_vectors, icd11_vectors)
            
            for i, icd10cm_code in enumerate(batch_codes):
                similarities = similarity_matrix[i]
                
                max_idx = np.argmax(similarities)
                max_similarity = similarities[max_idx]
                
                if max_similarity >= confidence_threshold:
                    icd11_code = icd11_codes[max_idx]
                    
                    cur.execute("""
                        INSERT INTO ontology.code_cross_references
                        (source_table, source_id, target_table, target_id, 
                         relationship_type, confidence, similarity_score)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        'ontology.icd', icd10cm_code, 'ontology.icd', icd11_code,
                        'equivalent', round(float(max_similarity), 2), round(float(max_similarity), 4)
                    ))
                    
                    mappings_created += 1
                    
                    if max_similarity >= 0.80:
                        high_confidence_mappings += 1
            
            conn.commit()
            print(f"Batch {batch_idx + 1} complete: {mappings_created} total mappings, {high_confidence_mappings} high-confidence")
        
        print(f"\n✅ Cross-system mapping completed!")
        print(f"📊 Total mappings created: {mappings_created}")
        print(f"🎯 High-confidence mappings (≥0.80): {high_confidence_mappings}")
        
        cur.execute("""
            SELECT 
                COUNT(*) as total_mappings,
                AVG(confidence) as avg_confidence,
                MIN(confidence) as min_confidence,
                MAX(confidence) as max_confidence,
                COUNT(*) FILTER (WHERE confidence >= 0.90) as very_high_conf,
                COUNT(*) FILTER (WHERE confidence >= 0.80) as high_conf,
                COUNT(*) FILTER (WHERE confidence >= 0.70) as medium_conf
            FROM ontology.code_cross_references
        """)
        
        stats = cur.fetchone()
        if stats:
            total, avg_conf, min_conf, max_conf, very_high, high, medium = stats
            print(f"\n📈 Mapping Statistics:")
            print(f"   Total mappings: {total}")
            print(f"   Average confidence: {avg_conf:.3f}")
            print(f"   Confidence range: {min_conf:.3f} - {max_conf:.3f}")
            print(f"   Very high confidence (≥0.90): {very_high}")
            print(f"   High confidence (≥0.80): {high}")
            print(f"   Medium confidence (≥0.70): {medium}")
        
        if high_confidence_mappings >= 2000:
            print(f"🎉 SUCCESS: Achieved {high_confidence_mappings} high-confidence mappings (target: >2,000)")
        else:
            print(f"⚠️  WARNING: Only {high_confidence_mappings} high-confidence mappings (target: >2,000)")
        
    except Exception as e:
        print(f"Error during mapping: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    confidence_threshold = float(sys.argv[1]) if len(sys.argv) > 1 else 0.75
    map_icd_systems(confidence_threshold)
