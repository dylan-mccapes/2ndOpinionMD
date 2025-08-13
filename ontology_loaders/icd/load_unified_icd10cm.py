#!/usr/bin/env python3
"""
Unified ICD-10-CM Loader with Vector Embeddings
Loads ICD-10-CM data from fixed-width format into unified ontology.icd table
"""

import asyncio
from openai import OpenAI
import psycopg2
from pathlib import Path
import sys
import os
from dotenv import load_dotenv
import numpy as np
from collections import deque
import json

project_root = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

async def get_embedding(text: str):
    """Generate mock embedding for testing (following existing pattern)"""
    return np.random.random(1536).tolist()

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

def parse_icd10cm_line(line):
    """Parse ICD-10-CM fixed-width line format"""
    if len(line) < 59:
        return None
    
    order = line[0:5].strip()
    code = line[6:14].strip()
    flag = line[15:17].strip()
    short_desc = line[18:58].strip()
    long_desc = line[59:].strip()
    
    return {
        'order': order,
        'code': code,
        'flag': flag,
        'short_desc': short_desc,
        'long_desc': long_desc
    }

def get_hierarchy_level(code):
    """Determine hierarchy level based on code structure"""
    if not code:
        return 0
    
    clean_code = code.replace(".", "")
    
    if len(clean_code) <= 3:
        return 0  # Category level
    elif len(clean_code) == 4:
        return 1  # First subcategory
    elif len(clean_code) == 5:
        return 2  # Second subcategory
    else:
        return 3  # Further subcategories

def find_parent_code(code, existing_codes):
    """Find appropriate parent code that actually exists in the dataset"""
    if not code:
        return None
    
    if '.' in code:
        parent_candidate = code.rsplit('.', 1)[0]
        if parent_candidate in existing_codes:
            return parent_candidate
    
    if len(code) > 3:
        for i in range(len(code) - 1, 2, -1):
            parent_candidate = code[:i]
            if parent_candidate in existing_codes:
                return parent_candidate
    
    return None

async def load_icd10cm_data(file_path):
    """Load ICD-10-CM data with embeddings"""
    print(f"Loading ICD-10-CM data from: {file_path}")
    
    if not Path(file_path).exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Processing {len(lines)} ICD-10-CM lines...")
    
    records = []
    existing_codes = set()
    
    for line_num, line in enumerate(lines, 1):
        parsed = parse_icd10cm_line(line.strip())
        if parsed and parsed['code']:
            existing_codes.add(parsed['code'])
    
    print(f"Found {len(existing_codes)} unique ICD-10-CM codes")
    
    for line_num, line in enumerate(lines, 1):
        parsed = parse_icd10cm_line(line.strip())
        
        if not parsed or not parsed['code']:
            continue
        
        code = parsed['code']
        level = get_hierarchy_level(code)
        parent_code = find_parent_code(code, existing_codes)
        
        search_content = f"ICD-10-CM {code}: {parsed['short_desc']} - {parsed['long_desc']}"
        embedding = await get_embedding(search_content)
        
        path_codes = [code]
        current_parent = parent_code
        while current_parent and current_parent in existing_codes:
            path_codes.insert(0, current_parent)
            current_parent = find_parent_code(current_parent, existing_codes)
        
        record = {
            'code': code,
            'title': parsed['short_desc'],
            'definition': parsed['long_desc'],
            'system': 'ICD-10-CM',
            'version': '2025',
            'parent_code': parent_code,
            'chapter': None,
            'section': None,
            'full_path': path_codes,
            'depth': level,
            'search_content': search_content,
            'foundation_uri': None,
            'linearization_uri': None,
            'class_kind': 'category' if level > 0 else 'chapter',
            'is_residual': False,
            'metadata': {'source': 'icd10cm_fixed_width', 'order': parsed['order'], 'flag': parsed['flag']},
            'term_vector': embedding
        }
        
        records.append(record)
        
        if line_num % 1000 == 0:
            print(f"Processed {line_num} ICD-10-CM lines...")
    
    print(f"Parsed {len(records)} valid ICD-10-CM codes")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        print("Inserting ICD-10-CM data...")
        
        cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='icd' AND column_name='term_vector'")
        has_vector = cur.fetchone() is not None
        
        if has_vector:
            insert_query = """
                INSERT INTO ontology.icd
                (code, title, definition, system, version, parent_code, chapter, section, 
                 full_path, depth, search_content, foundation_uri, linearization_uri, 
                 class_kind, is_residual, metadata, term_vector)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        else:
            insert_query = """
                INSERT INTO ontology.icd
                (code, title, definition, system, version, parent_code, chapter, section, 
                 full_path, depth, search_content, foundation_uri, linearization_uri, 
                 class_kind, is_residual, metadata, term_vector_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
        
        def insert_record(record):
            if has_vector:
                return (
                    record['code'], record['title'], record['definition'], record['system'],
                    record['version'], record['parent_code'], record['chapter'], record['section'],
                    record['full_path'], record['depth'], record['search_content'],
                    record['foundation_uri'], record['linearization_uri'], record['class_kind'],
                    record['is_residual'], json.dumps(record['metadata']), record['term_vector']
                )
            else:
                return (
                    record['code'], record['title'], record['definition'], record['system'],
                    record['version'], record['parent_code'], record['chapter'], record['section'],
                    record['full_path'], record['depth'], record['search_content'],
                    record['foundation_uri'], record['linearization_uri'], record['class_kind'],
                    record['is_residual'], json.dumps(record['metadata']), json.dumps(record['term_vector'])
                )
        
        print("Inserting all ICD-10-CM records...")
        inserted_count = 0
        batch_size = 1000
        
        for i in range(0, len(records), batch_size):
            batch = records[i:i + batch_size]
            for record in batch:
                try:
                    record_copy = record.copy()
                    record_copy['parent_code'] = None
                    cur.execute(insert_query, insert_record(record_copy))
                    inserted_count += 1
                except Exception as e:
                    print(f"Error inserting {record['code']}: {e}")
            
            conn.commit()
            print(f"Inserted batch {i//batch_size + 1}: {len(batch)} records (total: {inserted_count})")
        
        print("Updating parent relationships...")
        updated_count = 0
        for record in records:
            if record['parent_code']:
                try:
                    cur.execute(
                        "UPDATE ontology.icd SET parent_code = %s WHERE code = %s",
                        (record['parent_code'], record['code'])
                    )
                    updated_count += 1
                except Exception as e:
                    print(f"Error updating parent for {record['code']}: {e}")
        
        conn.commit()
        print(f"Updated {updated_count} parent relationships")
        
        print(f"✅ Successfully loaded {inserted_count} ICD-10-CM codes")
        
    except Exception as e:
        print(f"Error during ICD-10-CM database operations: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    file_path = sys.argv[1] if len(sys.argv) > 1 else "~/attachments/70008085-ece6-488f-a112-d08662f67f56/icd10cm-0425.txt"
    file_path = os.path.expanduser(file_path)
    asyncio.run(load_icd10cm_data(file_path))
