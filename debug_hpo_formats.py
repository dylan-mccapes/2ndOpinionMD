#!/usr/bin/env python3
"""
Debug script to check actual HPO ID formats in database vs file
"""

import psycopg2

def debug_hpo_formats():
    """Debug actual HPO ID formats"""
    print("🔍 Debugging actual HPO ID formats...")
    
    try:
        conn = psycopg2.connect(
            dbname="2ndopinionmd",
            user="devin",
            password="devin123",
            host="localhost",
            port="5432"
        )
        cursor = conn.cursor()
        
        cursor.execute("SELECT hpo_id FROM ontology.hpo_terms LIMIT 10")
        db_hpo_ids = [row[0] for row in cursor.fetchall()]
        
        print("📊 Sample HPO IDs from hpo_terms table:")
        for i, hpo_id in enumerate(db_hpo_ids):
            print(f"  {i+1}: {repr(hpo_id)}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    
    print("\n📊 Sample HPO IDs from phenotype.hpoa file:")
    
    with open("data/hpo/phenotype.hpoa", 'r') as f:
        lines = f.readlines()
    
    data_lines = []
    for line in lines:
        if not line.startswith('#') and line.strip():
            data_lines.append(line.strip())
            if len(data_lines) >= 10:
                break
    
    for i, line in enumerate(data_lines):
        parts = line.split('\t')
        if len(parts) >= 4:
            hpo_id = parts[3]  # HPO ID is in column 4
            print(f"  {i+1}: {repr(hpo_id)}")
    
    print("\n🔍 Format analysis:")
    if db_hpo_ids and data_lines:
        db_sample = db_hpo_ids[0]
        file_sample = data_lines[0].split('\t')[3] if len(data_lines[0].split('\t')) >= 4 else "N/A"
        
        print(f"  Database format: {repr(db_sample)}")
        print(f"  File format: {repr(file_sample)}")
        
        if db_sample == file_sample:
            print("  ✅ Formats match!")
        else:
            print("  ❌ Formats differ!")
            print(f"  DB starts with: {db_sample[:5] if len(db_sample) >= 5 else db_sample}")
            print(f"  File starts with: {file_sample[:5] if len(file_sample) >= 5 else file_sample}")
            
            if file_sample.startswith('HP:'):
                converted = file_sample.replace('HP:', 'HP_')
                print(f"  Converted HP: -> HP_: {repr(converted)}")
                if converted == db_sample:
                    print("  ✅ HP: -> HP_ conversion works!")
                else:
                    print("  ❌ HP: -> HP_ conversion doesn't match")

if __name__ == "__main__":
    debug_hpo_formats()
