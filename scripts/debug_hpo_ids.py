#!/usr/bin/env python3
"""
Debug script to investigate HPO ID format mismatch between hpo_terms and phenotype.hpoa
"""

import psycopg2
import sys
from pathlib import Path

def debug_hpo_ids():
    """Debug HPO ID formats"""
    print("🔍 Debugging HPO ID format mismatch...")
    
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
        
        print("📊 HPO IDs in hpo_terms table:")
        for hpo_id in db_hpo_ids:
            print(f"  {repr(hpo_id)}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
    
    print("\n📊 HPO IDs in phenotype.hpoa file:")
    
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
            hpo_id = parts[3]  # HPO ID is typically in column 4
            print(f"  Line {i+1}: {repr(hpo_id)}")
    
    print("\n🔍 Format comparison:")
    if db_hpo_ids and data_lines:
        db_sample = db_hpo_ids[0]
        file_sample = data_lines[0].split('\t')[3] if len(data_lines[0].split('\t')) >= 4 else "N/A"
        
        print(f"  Database format: {repr(db_sample)}")
        print(f"  File format: {repr(file_sample)}")
        
        if db_sample == file_sample:
            print("  ✅ Formats match!")
        else:
            print("  ❌ Formats differ!")
            print(f"  DB length: {len(db_sample)}, File length: {len(file_sample)}")

if __name__ == "__main__":
    debug_hpo_ids()
